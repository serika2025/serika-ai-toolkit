import base64
import os
import tempfile
import requests as http_requests
from PyQt6.QtCore import QThread, pyqtSignal
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from utils.prompts import get_audio_prompt
from utils.audio_converter import is_ffmpeg_available, convert_to_mp3, find_ffmpeg


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


class AudioWorker(QThread):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    usage_updated = pyqtSignal(int, int, int)
    ffmpeg_missing = pyqtSignal()

    def __init__(self, audio_path, languages="", regions=""):
        super().__init__()
        self.audio_path = os.path.abspath(audio_path)
        self.languages = languages
        self.regions = regions
        self.config = ConfigManager()

    def run(self):
        try:
            if not is_ffmpeg_available():
                self.status_changed.emit("缺少依赖")
                self.ffmpeg_missing.emit()
                return
            fp, _ = find_ffmpeg()
            if fp:
                os.environ["PATH"] = os.path.dirname(fp) + os.pathsep + os.environ.get("PATH", "")

            self.status_changed.emit("转换音频...")
            self.progress_changed.emit(10)
            td = tempfile.mkdtemp(prefix="aitok_audio_")
            mp3 = os.path.join(td, "audio.mp3")
            convert_to_mp3(self.audio_path, mp3,
                           progress_callback=lambda p: self.progress_changed.emit(p))
            self.progress_changed.emit(25)

            eu, ak, mn, fmt = _resolve_model("audio")
            self.status_changed.emit("连接中...")
            self.progress_changed.emit(28)

            pt = get_audio_prompt(self.languages, self.regions)

            if fmt == "Gemini":
                r = self._gemini(eu, ak, mn, mp3, pt)
            elif fmt == "OpenAI(多模态)":
                r = self._multimodal(eu, ak, mn, mp3, pt)
            else:
                r = self._openai(eu, ak, mn, mp3, pt)

            self.status_changed.emit("输出中...")
            self.progress_changed.emit(90)
            self.progress_changed.emit(100)
            self.status_changed.emit("完成")
            self.finished.emit(r)
            try:
                os.remove(mp3)
                os.rmdir(td)
            except Exception:
                pass
        except Exception as e:
            self.error.emit(str(e))
            self.status_changed.emit("错误")
            self.progress_changed.emit(0)

    # ---------- OpenAI /audio/transcriptions ----------
    def _openai(self, eu, ak, mn, mp3, pt):
        url = f"{eu.rstrip('/')}/audio/transcriptions"
        self.status_changed.emit("思考中...")
        self.progress_changed.emit(40)
        self.status_changed.emit("听力中...")
        self.progress_changed.emit(60)

        data = {"model": mn}
        if pt:
            data["prompt"] = pt

        with open(mp3, "rb") as f:
            resp = http_requests.post(
                url,
                headers={"Authorization": f"Bearer {ak}"},
                files={"file": ("audio.mp3", f, "audio/mpeg")},
                data=data,
                timeout=120,
            )

        if resp.status_code == 200:
            return resp.json().get("text", "")

        # Retry without prompt
        if pt:
            data.pop("prompt", None)
            with open(mp3, "rb") as f:
                resp2 = http_requests.post(
                    url,
                    headers={"Authorization": f"Bearer {ak}"},
                    files={"file": ("audio.mp3", f, "audio/mpeg")},
                    data=data,
                    timeout=120,
                )
            if resp2.status_code == 200:
                return resp2.json().get("text", "")

        if resp.status_code == 404:
            _audio_404(url, mn)
        raise RuntimeError(
            f"音频转写失败 ({resp.status_code})\n"
            f"URL: {url}\n模型: {mn}\n{resp.text[:300]}"
        )

    # ---------- Gemini ----------
    def _gemini(self, eu, ak, mn, mp3, pt):
        with open(mp3, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ins = (pt + "\n\n" if pt else "") + (
            "Please transcribe this audio verbatim. "
            "Return ONLY the transcribed text, nothing else."
        )
        body = {"contents": [{"parts": [
            {"text": ins},
            {"inline_data": {"mime_type": "audio/mp3", "data": b64}},
        ]}]}
        self.status_changed.emit("思考中...")
        self.progress_changed.emit(40)
        self.status_changed.emit("听力中...")
        self.progress_changed.emit(60)

        base = eu.rstrip("/")
        for ver in ("v1beta", "v1"):
            url = f"{base}/{ver}/models/{mn}:generateContent"
            r = http_requests.post(
                url, params={"key": ak},
                headers={"Content-Type": "application/json"},
                json=body, timeout=120,
            )
            if r.status_code == 200:
                cand = r.json().get("candidates", [])
                if not cand:
                    raise RuntimeError("Gemini 无返回（安全过滤）。")
                pts = cand[0]["content"]["parts"]
                return "".join(p.get("text", "") for p in pts).strip()
            if r.status_code == 404:
                if ver == "v1beta":
                    continue
                _gemini_404(base, mn)
            if r.status_code in (401, 403):
                raise RuntimeError(
                    f"Gemini 认证失败 ({r.status_code})\n"
                    f"URL: {url}\n"
                    "需要 Google AI Studio 原生 Key: https://aistudio.google.com/apikey"
                )
            if ver == "v1beta":
                continue
            raise RuntimeError(f"Gemini 错误 ({r.status_code}): {r.text[:300]}")

    # ---------- 多模态（百炼 DashScope / OpenAI 原生多模态）----------
    def _multimodal(self, eu, ak, mn, mp3, pt):
        ins = (pt + "\n\n" if pt else "") + "请完整转写这段音频，只输出转写文本。"
        self.status_changed.emit("编码音频...")
        self.progress_changed.emit(40)

        with open(mp3, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        data_uri = f"data:audio/mp3;base64,{b64}"

        self.status_changed.emit("思考中...")
        self.status_changed.emit("听力中...")
        self.progress_changed.emit(60)

        base = eu.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {ak}",
            "Content-Type": "application/json",
        }

        # 尝试多种格式，按顺序：audio_url (Omni) → input_audio (ASR)
        formats = [
            (
                [{"type": "text", "text": ins},
                 {"type": "audio_url", "audio_url": {"url": data_uri}}],
                "audio_url"
            ),
            (
                [{"type": "text", "text": ins},
                 {"type": "input_audio", "input_audio": {"data": data_uri, "format": "mp3"}}],
                "input_audio"
            ),
        ]

        last_msg = ""
        for content, fmt_name in formats:
            resp = http_requests.post(
                url, headers=headers,
                json={
                    "model": mn,
                    "messages": [{"role": "user", "content": content}],
                    "stream": False,
                },
                timeout=120,
            )
            if resp.status_code == 404:
                _audio_404(url, mn)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            last_msg = resp.text[:500]
            # 如果是格式不支持的错误，尝试下一种格式
            if "InvalidParameter" in last_msg or "invalid" in last_msg.lower():
                continue
            # 其他错误（401/403等）直接抛出
            break

        # 所有格式都失败
        hint = (
            "\n\n⚠️ 已尝试 audio_url 和 input_audio 两种格式均失败。\n"
            "百炼可用音频模型:\n"
            "  Omni系列(用audio_url): qwen-omni-turbo / qwen3.5-omni-flash\n"
            "  ASR系列(用input_audio): qwen3-asr-flash\n"
            "  Audio系列(原生格式): qwen-audio-turbo\n"
            "当前模型: {mn}".format(mn=mn)
        )
        raise RuntimeError(
            f"多模态音频转写失败 (400)\n"
            f"URL: {url}\n"
            f"模型: {mn}\n{last_msg}{hint}"
        )


def _audio_404(url, model_name):
    raise RuntimeError(
        f"音频端点 404\nURL: {url}\n模型: {model_name}\n\n"
        "该服务商不支持此音频端点。\n\n"
        "=== 国内可直接使用 ===\n"
        "硅基流动 (OpenAI格式)\n"
        "  端点: https://api.siliconflow.cn/v1\n"
        "  模型: FunAudioLLM/SenseVoiceSmall\n\n"
        "百炼多模态 (OpenAI(多模态)格式)\n"
        "  端点: https://dashscope.aliyuncs.com/compatible-mode/v1\n"
        "  模型: qwen-audio-turbo\n\n"
        "Gemini原生 (Gemini格式)\n"
        "  端点: https://generativelanguage.googleapis.com\n"
        "  模型: gemini-1.5-flash\n\n"
        "=== 海外 ===\n"
        "Groq  https://api.groq.com/openai/v1  whisper-large-v3-turbo\n"
        "OpenAI  https://api.openai.com/v1  whisper-1"
    )


def _gemini_404(base, model_name):
    raise RuntimeError(
        f"Gemini 模型 '{model_name}' 404\n"
        f"尝试: {base}/v1beta/models/{model_name}:generateContent\n"
        f"      {base}/v1/models/{model_name}:generateContent\n\n"
        "正确模型名: gemini-1.5-flash / gemini-2.0-flash\n"
        "端点不用加 /v1 或 /v1beta"
    )
