import re
import requests as http_requests
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from utils.prompts import get_expand_prompt


# CJK characters: Chinese, Japanese kanji/kana, Korean
_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'
                     r'\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')


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
        raise RuntimeError(f"模型数据不完整，请重新选择模型。")
    return eu, ak, mn, fmt or "OpenAI"


def count_text(text):
    """Count characters or words in text, excluding punctuation.
    Returns (count, unit) where unit is 'char' or 'word'.
    Auto-detects: if CJK proportion > 50%, use char count; else word count.
    """
    # Strip punctuation, spaces, digits but keep letters and CJK
    # Count CJK chars
    cjk_chars = len(_CJK_RE.findall(text))
    # Count alphabetic words (sequences of letters)
    words = re.findall(r'[a-zA-Z\u00c0-\u024f\u1e00-\u1eff]+', text)
    word_count = len(words)
    # If CJK is dominant, report chars
    if cjk_chars > word_count:
        return cjk_chars, "char"
    else:
        return word_count if word_count > 0 else len(text), "word"


def count_unit(text):
    """Return dict with both char and word counts."""
    cjk_chars = len(_CJK_RE.findall(text))
    words = re.findall(r'[a-zA-Z\u00c0-\u024f\u1e00-\u1eff]+', text)
    return {"char": cjk_chars, "word": len(words)}


class ExpandWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    usage_updated = pyqtSignal(int, int, int)
    retry_occurred = pyqtSignal(int, int)  # current_retry, max_retries

    def __init__(self, text, target_count, tolerance, max_retries,
                 fit_original, politics_follow=False, text_nature=""):
        super().__init__()
        self.text = text
        self.target_count = target_count
        self.tolerance = tolerance
        self.max_retries = max_retries
        self.fit_original = fit_original
        self.politics_follow = politics_follow
        self.text_nature = text_nature
        self.config = ConfigManager()

    def run(self):
        try:
            self.status_changed.emit("统计字数...")
            self.progress_changed.emit(5)

            # Count original text to determine unit
            count_result, unit = count_text(self.text)
            self.status_changed.emit(f"原文 {count_result} {'字' if unit == 'char' else '单词'}，目标 {self.target_count}")

            self.progress_changed.emit(10)

            eu, ak, mn, fmt = _resolve_model("expand")
            self.status_changed.emit("连接中...")
            self.progress_changed.emit(15)

            # Build prompt once (it doesn't change across retries)
            system_prompt = get_expand_prompt(
                count_result, self.target_count, unit,
                self.tolerance, self.fit_original, self.politics_follow,
                self.text_nature
            )

            for attempt in range(self.max_retries + 1):
                if attempt > 0:
                    self.retry_occurred.emit(attempt, self.max_retries)
                    self.status_changed.emit(
                        f"字数不符，第 {attempt}/{self.max_retries} 次重试..."
                    )
                    self.progress_changed.emit(20)
                    # Slightly vary the prompt to avoid same result
                    user_msg = (
                        f"上一版输出的{ '字数' if unit == 'char' else '单词数' }不在允许范围内。"
                        f"请严格按照要求重新{direction_hint(self.text, self.target_count, count_text(self.text)[0])}，"
                        f"使去标点{ '字数' if unit == 'char' else '单词数' }恰好为 {self.target_count}。\n\n"
                        f"原文：\n{self.text}"
                    )
                else:
                    user_msg = self.text

                self.status_changed.emit("思考中...")
                self.progress_changed.emit(40)

                # Call API
                if fmt == "Gemini":
                    result_text, usage = self._call_gemini(
                        eu, ak, mn, system_prompt, user_msg
                    )
                else:
                    result_text, usage = self._call_openai(
                        eu, ak, mn, system_prompt, user_msg
                    )

                self.status_changed.emit("统计结果字数...")
                self.progress_changed.emit(85)

                # Count result
                out_counts = count_unit(result_text)
                out_count = out_counts[unit]

                if self.target_count - self.tolerance <= out_count <= self.target_count + self.tolerance:
                    self.progress_changed.emit(100)
                    self.status_changed.emit(
                        f"完成 ({out_count} {unit})"
                    )
                    if usage:
                        self.config.add_usage(*usage)
                        self.usage_updated.emit(*usage)
                    self.finished.emit(result_text)
                    return
                else:
                    # Out of tolerance — will retry if attempts remaining
                    self.status_changed.emit(
                        f"输出 {out_count} {unit}，不在 [{self.target_count - self.tolerance}, "
                        f"{self.target_count + self.tolerance}] 范围内"
                    )

            # Exhausted all retries
            raise RuntimeError(
                f"打回次数过多，可能代表该模型指令遵循度或文学造诣不高，请尝试更换模型。\n"
                f"共尝试 {self.max_retries + 1} 次，均未能满足字数要求。\n"
                f"目标: {self.target_count} {unit}，容差: ±{self.tolerance}。"
            )

        except Exception as e:
            self.error.emit(str(e))
            self.status_changed.emit("错误")
            self.progress_changed.emit(0)

    def _call_openai(self, eu, ak, mn, system_prompt, user_text):
        client = OpenAI(api_key=ak, base_url=eu)
        self.progress_changed.emit(50)
        response = client.chat.completions.create(
            model=mn,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            stream=False,
        )
        self.status_changed.emit("编辑中...")
        self.progress_changed.emit(75)
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

        self.progress_changed.emit(50)

        for api_ver in ("v1beta", "v1"):
            url = f"{base}/{api_ver}/models/{mn}:generateContent"
            resp = http_requests.post(
                url, params={"key": ak},
                headers={"Content-Type": "application/json"},
                json=body, timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.status_changed.emit("编辑中...")
                self.progress_changed.emit(75)
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
                raise RuntimeError(
                    f"Gemini 404 — 模型 '{mn}' 不存在。"
                )
            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"Gemini 认证失败 ({resp.status_code})。"
                )
            if api_ver == "v1beta":
                continue
            raise RuntimeError(f"Gemini API 错误 ({resp.status_code}): {resp.text[:500]}")


def direction_hint(text, target, orig):
    if target > orig:
        return "扩写"
    elif target < orig:
        return "精简"
    return "改写"
