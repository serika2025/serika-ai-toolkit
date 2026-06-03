import uuid
import sys
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QPushButton, QFormLayout,
                             QMessageBox, QListWidget, QListWidgetItem, QInputDialog,
                             QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from config.model_manager import ModelManager, PRESETS, AUDIO_MODEL_HINTS
import requests


def _icon_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "icon.ico")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.ico")


class ModelSettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型设置")
        self.setWindowIcon(QIcon(_icon_path()))
        self.resize(700, 500)
        self.mgr = ModelManager()
        self.current_model_id = None
        self.init_ui()
        self.load_models()

    def init_ui(self):
        layout = QHBoxLayout(self)

        # --- Left: model list ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("已添加的模型:"))

        self.model_list = QListWidget()
        self.model_list.currentItemChanged.connect(self.on_model_selected)
        left_layout.addWidget(self.model_list)

        add_btn = QPushButton("添加模型")
        add_btn.clicked.connect(self.add_model)
        left_layout.addWidget(add_btn)

        del_btn = QPushButton("删除模型")
        del_btn.clicked.connect(self.delete_model)
        left_layout.addWidget(del_btn)

        layout.addLayout(left_layout, 1)

        # --- Right: edit form ---
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("模型详情:"))

        self.form_layout = QFormLayout()

        # Short name
        self.short_name_input = QLineEdit()
        self.short_name_input.setPlaceholderText("不填则默认使用模型ID")
        self.form_layout.addRow("简称:", self.short_name_input)

        # Quick presets
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["（快捷预设）"] + list(PRESETS.keys()))
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        self.form_layout.addRow("快捷预设:", preset_layout)

        # AI Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["OpenAI", "Gemini", "OpenAI(多模态)"])
        self.form_layout.addRow("AI 格式:", self.format_combo)

        # Endpoint URL
        self.url_input = QLineEdit()
        self.form_layout.addRow("端点 URL:", self.url_input)

        # API Key with eye toggle
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.key_input)
        self.eye_btn = QPushButton("👁")
        self.eye_btn.setFixedWidth(30)
        self.eye_btn.setCheckable(True)
        self.eye_btn.toggled.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.eye_btn)
        self.form_layout.addRow("API Key:", key_layout)

        # Model name with fetch button
        model_name_layout = QHBoxLayout()
        self.model_name_input = QLineEdit()
        model_name_layout.addWidget(self.model_name_input)
        fetch_btn = QPushButton("获取可用模型")
        fetch_btn.clicked.connect(self.fetch_models)
        model_name_layout.addWidget(fetch_btn)
        self.form_layout.addRow("模型名称:", model_name_layout)

        # Audio model hint (shown when 🎤 preset selected)
        self.model_hint_label = QLabel("")
        self.model_hint_label.setWordWrap(True)
        self.model_hint_label.setVisible(False)
        self.form_layout.addRow("", self.model_hint_label)

        right_layout.addLayout(self.form_layout)

        # Save button
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_current_model)
        right_layout.addWidget(save_btn)

        right_layout.addStretch()
        layout.addLayout(right_layout, 2)

    def on_preset_changed(self, idx):
        if idx <= 0:
            self.model_hint_label.setVisible(False)
            return
        name = list(PRESETS.keys())[idx - 1]
        url, fmt = PRESETS[name]
        self.url_input.setText(url)
        self.format_combo.setCurrentText(fmt)
        # Show audio model hint if applicable
        hint = AUDIO_MODEL_HINTS.get(url)
        if hint:
            self.model_hint_label.setText(
                f"<font color='#888888' size='2'>推荐模型名称: {hint}</font>"
            )
            self.model_hint_label.setVisible(True)
        else:
            self.model_hint_label.setVisible(False)

    def toggle_key_visibility(self, checked):
        if checked:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText("🙈")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setText("👁")

    def load_models(self):
        self.model_list.blockSignals(True)
        self.model_list.clear()
        for m in self.mgr.list_models():
            display = self.mgr.to_display_label(m["id"])
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.model_list.addItem(item)
        self.model_list.blockSignals(False)
        self.clear_form()

    def clear_form(self):
        self.current_model_id = None
        self.short_name_input.clear()
        self.preset_combo.setCurrentIndex(0)
        self.format_combo.setCurrentIndex(0)
        self.url_input.clear()
        self.key_input.clear()
        self.model_name_input.clear()
        self.eye_btn.setChecked(False)
        self.model_hint_label.setVisible(False)

    def on_model_selected(self, current, previous):
        if not current:
            self.clear_form()
            return
        mid = current.data(Qt.ItemDataRole.UserRole)
        m = self.mgr.get_model(mid)
        if not m:
            self.clear_form()
            return
        self.current_model_id = mid
        self.short_name_input.setText(m.get("short_name", ""))
        self.format_combo.setCurrentText(m.get("ai_format", "OpenAI"))
        self.url_input.setText(m.get("endpoint_url", ""))
        self.key_input.setText(m.get("api_key", ""))
        self.model_name_input.setText(m.get("model_name", ""))
        self.eye_btn.setChecked(False)

    def add_model(self):
        self.clear_form()
        self.current_model_id = None
        # Focus on the form

    def delete_model(self):
        if not self.current_model_id:
            QMessageBox.warning(self, "提示", "请先选择一个模型")
            return
        reply = QMessageBox.question(self, "确认删除",
            f"确定要删除模型 \"{self.mgr.get_short_name(self.current_model_id)}\" 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.mgr.delete_model(self.current_model_id)
            self.load_models()

    def save_current_model(self):
        url = self.url_input.text().strip()
        key = self.key_input.text().strip()
        model_name = self.model_name_input.text().strip()

        if not url:
            QMessageBox.warning(self, "提示", "请填写端点 URL")
            return
        if not key:
            QMessageBox.warning(self, "提示", "请填写 API Key")
            return
        if not model_name:
            QMessageBox.warning(self, "提示", "请填写模型名称")
            return

        data = {
            "id": self.current_model_id or str(uuid.uuid4()),
            "short_name": self.short_name_input.text().strip(),
            "ai_format": self.format_combo.currentText(),
            "endpoint_url": url,
            "api_key": key,
            "model_name": model_name,
        }
        self.mgr.save_model(data)
        self.load_models()

    def fetch_models(self):
        url = self.url_input.text().strip()
        key = self.key_input.text().strip()
        fmt = self.format_combo.currentText()
        if not url or not key:
            QMessageBox.warning(self, "错误", "请先填写端点 URL 和 API Key")
            return

        if fmt == "Gemini":
            self._fetch_gemini_models(url, key)
            return

        self._fetch_openai_models(url, key)

    def _fetch_gemini_models(self, url, key):
        """Gemini: GET /v1beta/models?key={KEY}"""
        base = url.rstrip("/")
        models_url = f"{base}/v1beta/models"

        try:
            resp = requests.get(
                models_url, params={"key": key},
                timeout=10
            )
            if resp.status_code != 200:
                # Try v1 if v1beta fails
                models_url2 = f"{base}/v1/models"
                resp2 = requests.get(
                    models_url2, params={"key": key},
                    timeout=10
                )
                if resp2.status_code != 200:
                    raise RuntimeError(
                        f"获取 Gemini 模型列表失败。\n"
                        f"v1beta: {resp.status_code} {resp.text[:200]}\n"
                        f"v1: {resp2.status_code} {resp2.text[:200]}"
                    )
                resp = resp2
                models_url = models_url2

            data = resp.json()
            raw = data.get("models", [])
            if not raw:
                QMessageBox.warning(self, "提示",
                    f"端点 {models_url} 返回了空模型列表。\n"
                    "请检查 API Key 是否正确。")
                return

            # Extract display names + model IDs
            entries = []
            for m in raw:
                name = m.get("name", "")
                # Format: "models/gemini-1.5-flash"
                mid = name.split("/")[-1] if "/" in name else name
                label = m.get("displayName", mid)
                entries.append((label, mid))

            entries.sort(key=lambda x: x[0].lower())

            # Use a simple dialog with the list
            models = [f"{label}  [{mid}]" for (label, mid) in entries]
            model, ok = QInputDialog.getItem(
                self, f"选择模型 ({len(models)} 个可用)",
                "请选择:", models, 0, False
            )
            if ok and model:
                # Extract model ID from the "label  [id]" format
                bracket = model.rfind("[")
                if bracket > 0:
                    selected_id = model[bracket + 1:].rstrip("]")
                    self.model_name_input.setText(selected_id)
                else:
                    self.model_name_input.setText(model)

        except Exception as e:
            QMessageBox.critical(self, "错误",
                f"获取 Gemini 模型列表失败:\n{str(e)}\n\n"
                f"请求 URL: {models_url}\n\n"
                "请确认:\n"
                "1. 端点 URL 为 https://generativelanguage.googleapis.com\n"
                "2. API Key 从 https://aistudio.google.com/apikey 获取")

    def _fetch_openai_models(self, url, key):
        """OpenAI / OpenAI(多模态): GET /v1/models"""
        base = url.rstrip("/")
        models_url = base + "/models" if not base.endswith("/models") else base

        try:
            headers = {"Authorization": f"Bearer {key}"}
            resp = requests.get(models_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"获取模型列表失败 ({resp.status_code})\n"
                    f"URL: {models_url}\n{resp.text[:300]}"
                )
            data = resp.json()

            models = []
            if "data" in data:
                models = [m.get("id", "") for m in data["data"] if m.get("id")]
            elif isinstance(data, list):
                models = [m.get("id", "") for m in data if isinstance(m, dict) and m.get("id")]

            if not models:
                QMessageBox.warning(self, "提示",
                    f"端点 {models_url} 返回了空模型列表。\n"
                    "请手动输入模型名称，或检查 API Key。")
                return

            models.sort()
            model, ok = QInputDialog.getItem(
                self, f"选择模型 ({len(models)} 个可用)",
                "请选择:", models, 0, False
            )
            if ok and model:
                self.model_name_input.setText(model)

        except Exception as e:
            QMessageBox.critical(self, "错误",
                f"获取模型列表失败:\n{str(e)}\n\n"
                f"请求 URL: {models_url}"
            )
