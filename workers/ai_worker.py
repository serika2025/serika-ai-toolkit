import base64
import requests as http_requests
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from utils.prompts import get_translation_prompt


def _resolve_model(section):
    """Returns (endpoint_url, api_key, model_name, ai_format) or raises RuntimeError."""
    config = ConfigManager()
    mgr = ModelManager()
    cfg = config.get_section(section)
    model_id = cfg.get("active_model_id", "")

    if not model_id:
        raise RuntimeError(
            f"未选择模型。请在页面顶部的模型选择器中选择一个模型。\n"
            f"如果列表为空，请先通过工具栏【模型设置】添加模型。"
        )

    eu, ak, mn, fmt = mgr.get_model_full(model_id)
    if not eu or not ak or not mn:
        config.set(section, "active_model_id", "")
        raise RuntimeError(
            f"模型记录丢失或配置不完整（id: {model_id[:8]}...）。\n"
            f"请重新在模型选择器中选择一个有效的模型。"
        )

    return eu, ak, mn, fmt or "OpenAI"


class TranslationWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    usage_updated = pyqtSignal(int, int, int)

    def __init__(self, text_to_translate):
        super().__init__()
        self.text_to_translate = text_to_translate
        self.config = ConfigManager()

    def run(self):
        try:
            self.status_changed.emit("连接中...")
            self.progress_changed.emit(10)

            trans_cfg = self.config.get_section("translation")
            endpoint_url, api_key, model_name, ai_format = _resolve_model("translation")

            system_prompt = get_translation_prompt(
                source_lang=trans_cfg.get("source_lang", "自动识别"),
                target_lang=trans_cfg.get("target_lang", "中文"),
                keep_abbr=trans_cfg.get("keep_abbr", False),
                auto_correct=trans_cfg.get("auto_correct", False),
                keep_format=trans_cfg.get("keep_format", True),
                politics_follow=trans_cfg.get("politics_follow", False),
                custom_lang_name=trans_cfg.get("custom_lang_name", ""),
                custom_region=trans_cfg.get("custom_region", "")
            )

            self.status_changed.emit("思考中...")
            self.progress_changed.emit(30)

            if ai_format == "Gemini":
                result_text, usage = self._call_gemini(
                    endpoint_url, api_key, model_name,
                    system_prompt, self.text_to_translate
                )
            else:
                client = OpenAI(api_key=api_key, base_url=endpoint_url)
                self.progress_changed.emit(50)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": self.text_to_translate}
                    ],
                    stream=False
                )
                self.status_changed.emit("编辑中...")
                self.progress_changed.emit(80)
                result_text = response.choices[0].message.content.strip()
                usage = None
                if hasattr(response, 'usage') and response.usage:
                    usage = (
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                        response.usage.total_tokens
                    )

            if usage:
                self.config.add_usage(*usage)
                self.usage_updated.emit(*usage)

            self.progress_changed.emit(100)
            self.status_changed.emit("完成")
            self.finished.emit(result_text)

        except Exception as e:
            self.error.emit(str(e))
            self.status_changed.emit("错误")
            self.progress_changed.emit(0)

    def _call_gemini(self, endpoint_url, api_key, model_name, system_prompt, user_text):
        base = endpoint_url.rstrip("/")

        parts = [{"text": user_text}]
        body = {"contents": [{"parts": parts}]}
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        self.progress_changed.emit(50)

        # Try v1beta first, then v1
        for api_ver in ("v1beta", "v1"):
            url = f"{base}/{api_ver}/models/{model_name}:generateContent"
            resp = http_requests.post(
                url, params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body, timeout=120
            )

            if resp.status_code == 200:
                data = resp.json()
                self.status_changed.emit("编辑中...")
                self.progress_changed.emit(80)

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini 未返回结果。")
                content = candidates[0].get("content", {})
                parts_out = content.get("parts", [])
                result = "".join(p.get("text", "") for p in parts_out).strip()

                usage = None
                usage_meta = data.get("usageMetadata", {})
                if usage_meta:
                    usage = (
                        usage_meta.get("promptTokenCount", 0),
                        usage_meta.get("candidatesTokenCount", 0),
                        usage_meta.get("totalTokenCount", 0),
                    )
                return result, usage

            if resp.status_code == 404:
                if api_ver == "v1beta":
                    continue
                raise RuntimeError(
                    f"Gemini 404 — 模型 '{model_name}' 不存在。\n"
                    f"请检查模型名称是否正确（如 gemini-1.5-flash, gemini-2.0-flash-001）"
                )

            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"Gemini 认证失败 ({resp.status_code})。\n"
                    f"请求 URL: {url}\n"
                    "请使用 Google AI Studio 原生 API Key: https://aistudio.google.com/apikey"
                )

            if api_ver == "v1beta":
                continue

            raise RuntimeError(
                f"Gemini API 错误 ({resp.status_code}): {resp.text[:500]}"
            )
