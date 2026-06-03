import json
import os
import sys

def _app_dir():
    """Return the directory where the application resides (writable)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = os.path.join(_app_dir(), "config_data")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
USAGE_FILE = os.path.join(CONFIG_DIR, "usage.json")

DEFAULT_CONFIG = {
    "global": {
        "theme": "System",
        "enable_crash_reporter": True
    },
    "translation": {
        "source_lang": "自动识别",
        "target_lang": "中文",
        "keep_abbr": False,
        "auto_correct": False,
        "keep_format": True,
        "politics_follow": False,
        "custom_lang_name": "",
        "custom_region": "",
        "active_model_id": ""
    },
    "audio": {
        "languages": "",
        "regions": "",
        "active_model_id": ""
    },
    "expand": {
        "target_count": 800,
        "tolerance": 50,
        "max_retries": 3,
        "fit_original": True,
        "politics_follow": False,
        "text_nature": "",
        "active_model_id": ""
    },
    "polish": {
        "style": "",
        "custom_style": "",
        "fix_errors": True,
        "term_convert": False,
        "term_region": "",
        "politics_follow": False,
        "active_model_id": ""
    }
}

DEFAULT_USAGE = {
    "tokens": {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0
    }
}

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)
            cls._instance.config = DEFAULT_CONFIG.copy()
            cls._instance.usage = DEFAULT_USAGE.copy()
            cls._instance.load_all()
        return cls._instance

    def load_all(self):
        self.config = self._load_file(CONFIG_FILE, DEFAULT_CONFIG)
        self.usage = self._load_file(USAGE_FILE, DEFAULT_USAGE)

    def _load_file(self, filepath, default_data):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Merge with default to ensure all keys exist
                    for section, values in default_data.items():
                        if section not in loaded_data:
                            loaded_data[section] = values
                        else:
                            for key, val in values.items():
                                if key not in loaded_data[section]:
                                    loaded_data[section][key] = val
                    return loaded_data
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                return default_data.copy()
        else:
            self._save_file(filepath, default_data)
            return default_data.copy()

    def _save_file(self, filepath, data):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")

    def save_config(self):
        self._save_file(CONFIG_FILE, self.config)

    def save_usage(self):
        self._save_file(USAGE_FILE, self.usage)

    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()

    def get_section(self, section):
        return self.config.get(section, {})

    def add_usage(self, prompt_tokens, completion_tokens, total_tokens):
        self.usage["tokens"]["total_prompt_tokens"] += prompt_tokens
        self.usage["tokens"]["total_completion_tokens"] += completion_tokens
        self.usage["tokens"]["total_tokens"] += total_tokens
        self.save_usage()

    def get_usage(self):
        return self.usage.get("tokens", {})
