import json
import os
import sys
import uuid

def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LLM_DIR = os.path.join(_app_dir(), "llm")

def _ensure_dir():
    os.makedirs(LLM_DIR, exist_ok=True)

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            _ensure_dir()
        return cls._instance

    def list_models(self):
        models = []
        if not os.path.isdir(LLM_DIR):
            return models
        for fname in sorted(os.listdir(LLM_DIR)):
            if fname.endswith(".json"):
                path = os.path.join(LLM_DIR, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    models.append(m)
                except Exception:
                    pass
        return models

    def get_model(self, model_id):
        path = os.path.join(LLM_DIR, f"{model_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_model(self, model_data):
        mid = model_data.get("id")
        if not mid:
            mid = str(uuid.uuid4())
            model_data["id"] = mid
        path = os.path.join(LLM_DIR, f"{mid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(model_data, f, indent=4, ensure_ascii=False)
        return mid

    def delete_model(self, model_id):
        path = os.path.join(LLM_DIR, f"{model_id}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_model_full(self, model_id):
        """Return (endpoint_url, api_key, model_name, ai_format)."""
        m = self.get_model(model_id)
        if not m:
            return None, None, None, None
        return (
            m.get("endpoint_url", ""),
            m.get("api_key", ""),
            m.get("model_name", ""),
            m.get("ai_format", "OpenAI"),
        )

    def get_short_name(self, model_id):
        m = self.get_model(model_id)
        if not m:
            return model_id
        return m.get("short_name", "") or m.get("model_name", "") or model_id

    def to_display_label(self, model_id):
        short = self.get_short_name(model_id)
        return f"{short} ({model_id[:8]})"


# Presets: name -> (endpoint_url, ai_format)
# 🎤 = has /audio/transcriptions endpoint (OpenAI-compatible Whisper)
# 🔊 = has native audio via multimodal/file-upload (not /audio/transcriptions)
PRESETS = {
    # === OpenAI 兼容，有 Whisper 端点 ===
    "🎤 OpenAI":             ("https://api.openai.com/v1",                    "OpenAI"),
    "🎤 Groq":               ("https://api.groq.com/openai/v1",              "OpenAI"),
    "🎤 硅基流动 (SenseVoice)": ("https://api.siliconflow.cn/v1",               "OpenAI"),
    "🎤 Together AI":        ("https://api.together.xyz/v1",                 "OpenAI"),
    # === Gemini 原生 API（音频走 File API + generateContent）===
    "🔊 Gemini (原生音频)":   ("https://generativelanguage.googleapis.com",     "Gemini"),
    # === 多模态 Chat（音频走文件上传 + Chat Completions）===
    "🔊 百炼 (多模态音频)":    ("https://dashscope.aliyuncs.com/compatible-mode/v1", "OpenAI(多模态)"),
    # === 通用聊天（无音频能力）===
    "DeepSeek":              ("https://api.deepseek.com/v1",                 "OpenAI"),
    "Qwen (通义千问)":        ("https://dashscope.aliyuncs.com/compatible-mode/v1", "OpenAI"),
    "MiniMax":               ("https://api.minimax.chat/v1",                 "OpenAI"),
    "Moonshot (月之暗面)":    ("https://api.moonshot.cn/v1",                   "OpenAI"),
    "智谱 (GLM)":            ("https://open.bigmodel.cn/api/paas/v4",        "OpenAI"),
    "百川 (Baichuan)":       ("https://api.baichuan-ai.com/v1",              "OpenAI"),
    "零一万物":               ("https://api.lingyiwanwu.com/v1",              "OpenAI"),
    "Gemini (OpenAI兼容-仅聊天)": ("https://generativelanguage.googleapis.com/v1beta/openai/", "OpenAI"),
    "Azure OpenAI":          ("https://YOUR_RESOURCE.openai.azure.com/",     "OpenAI"),
}

# Audio model name hints per preset
AUDIO_MODEL_HINTS = {
    "https://api.openai.com/v1":                    "whisper-1",
    "https://api.groq.com/openai/v1":               "whisper-large-v3-turbo",
    "https://api.siliconflow.cn/v1":                "FunAudioLLM/SenseVoiceSmall",
    "https://api.together.xyz/v1":                  "whisper-large-v3-turbo",
    "https://generativelanguage.googleapis.com":     "gemini-1.5-flash (或 gemini-1.5-pro)",
    "https://dashscope.aliyuncs.com/compatible-mode/v1": "qwen-audio-turbo / qwen3.5-omni-flash / qwen-omni-turbo",
}
