import requests as http_requests
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from utils.prompts import get_polish_prompt


def _resolve_model(section):
    config = ConfigManager()
    mgr = ModelManager()
    cfg = config.get_section(section)
    model_id = cfg.get("active_model_id", "")
    if not model_id:
        raise RuntimeError("未选择模型。请在页面顶部选择一个模型。")
    eu, ak, mn, fmt = mgr.get_model_full(model_id)
    if not eu or not ak or not mn:
        config.set(section, "active_model_id", "")
        raise RuntimeError("模型数据不完整，请重新选择模型。")
    return eu, ak, mn, fmt or "OpenAI"


class PolishWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    usage_updated = pyqtSignal(int, int, int)

    def __init__(self, text, style, custom_style, fix_errors,
                 term_convert, term_region, politics_follow):
        super().__init__()
        self.text = text
        self.style = style
        self.custom_style = custom_style
        self.fix_errors = fix_errors
        self.term_convert = term_convert
        self.term_region = term_region
        self.politics_follow = politics_follow
        self.config = ConfigManager()

    def run(self):
        try:
            self.status_changed.emit("连接中...")
            self.progress_changed.emit(10)

            eu, ak, mn, fmt = _resolve_model("polish")
            self.status_changed.emit("思考中...")
            self.progress_changed.emit(30)

            system_prompt = get_polish_prompt(
                style=self.style,
                custom_style=self.custom_style,
                fix_errors=self.fix_errors,
                term_convert=self.term_convert,
                term_region=self.term_region,
                politics_follow=self.politics_follow,
            )

            if fmt == "Gemini":
                result_text, usage = self._call_gemini(
                    eu, ak, mn, system_prompt, self.text
                )
            else:
                result_text, usage = self._call_openai(
                    eu, ak, mn, system_prompt, self.text
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

    def _call_openai(self, eu, ak, mn, system_prompt, user_text):
        client = OpenAI(api_key=ak, base_url=eu)
        self.status_changed.emit("编辑中...")
        self.progress_changed.emit(60)
        response = client.chat.completions.create(
            model=mn,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            stream=False,
        )
        self.progress_changed.emit(85)
        result_text = response.choices[0].message.content.strip()
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = (
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )
        return result_text, usage

    def _call_gemini(self, eu, ak, mn, system_prompt, user_text):
        base = eu.rstrip("/")
        parts = [{"text": user_text}]
        body = {"contents": [{"parts": parts}]}
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        self.status_changed.emit("编辑中...")
        self.progress_changed.emit(60)

        for api_ver in ("v1beta", "v1"):
            url = f"{base}/{api_ver}/models/{mn}:generateContent"
            resp = http_requests.post(
                url, params={"key": ak},
                headers={"Content-Type": "application/json"},
                json=body, timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.progress_changed.emit(85)
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini 未返回结果。")
                parts_out = candidates[0].get("content", {}).get("parts", [])
                result = "".join(p.get("text", "") for p in parts_out).strip()
                usage = None
                um = data.get("usageMetadata", {})
                if um:
                    usage = (
                        um.get("promptTokenCount", 0),
                        um.get("candidatesTokenCount", 0),
                        um.get("totalTokenCount", 0),
                    )
                return result, usage
            if resp.status_code == 404:
                if api_ver == "v1beta":
                    continue
                raise RuntimeError(f"Gemini 404 — 模型 '{mn}' 不存在。")
            if resp.status_code in (401, 403):
                raise RuntimeError(f"Gemini 认证失败 ({resp.status_code})。")
            if api_ver == "v1beta":
                continue
            raise RuntimeError(f"Gemini API 错误 ({resp.status_code}): {resp.text[:500]}")
