from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QCheckBox, QTextEdit, QPushButton,
                             QProgressBar, QGroupBox, QSplitter, QApplication,
                             QLineEdit)
from PyQt6.QtCore import Qt
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from workers.polish_worker import PolishWorker

STYLE_PRESETS = [
    "自定义",
    "商务",
    "学术",
    "日常",
    "口语",
    "文学",
    "新闻",
    "法律",
    "技术",
    "广告文案",
    "社交平台",
    "正式书信",
]


class PolishTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.worker = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Model Selector at top ---
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("选择模型:"))
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_row.addWidget(self.model_combo, 1)
        model_row.addStretch()
        main_layout.addLayout(model_row)

        # --- Settings Group ---
        settings_group = QGroupBox("润色设置")
        settings_layout = QVBoxLayout()

        # Row 1: 目标风格
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("目标风格:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(STYLE_PRESETS)
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        row1.addWidget(self.style_combo)

        self.custom_style_input = QLineEdit()
        self.custom_style_input.setPlaceholderText("请填写自定义风格要求...")
        self.custom_style_input.setVisible(False)
        row1.addWidget(self.custom_style_input, 1)
        row1.addStretch()
        settings_layout.addLayout(row1)

        # Row 2: 错词纠正 / 用辞纠正
        row2 = QHBoxLayout()

        self.fix_errors_cb = QCheckBox("错词纠正")
        fix_errors_note = QLabel(
            "<font color='#888888' size='2'>"
            "#勾选后，AI会纠正可能错误的词汇<br>"
            "#不勾选则禁止修改错误的词汇并继续沿用，防止谐音梗等失活</font>"
        )
        fix_errors_note.setWordWrap(True)
        row2.addWidget(self.fix_errors_cb)
        row2.addWidget(fix_errors_note, 1)

        self.term_convert_cb = QCheckBox("用辞纠正")
        self.term_convert_cb.toggled.connect(self.on_term_convert_toggled)
        row2.addWidget(self.term_convert_cb)

        term_convert_label = QLabel("地区:")
        self.term_region_input = QLineEdit()
        self.term_region_input.setPlaceholderText("例如：中国台湾、中国香港、日本...")
        self.term_region_input.setMaximumWidth(180)
        self.term_region_input.setVisible(False)
        term_convert_label.setVisible(False)

        term_note = QLabel(
            "<font color='#888888' size='2'>"
            "#开启后将按目标地区习惯转换用辞<br>"
            "#例如中国台湾：软件→软体，飞行员→飞官</font>"
        )
        term_note.setWordWrap(True)
        row2.addWidget(term_convert_label)
        row2.addWidget(self.term_region_input)
        row2.addWidget(term_note, 1)
        settings_layout.addLayout(row2)

        # Store refs for toggle visibility
        self._term_label = term_convert_label
        self._term_note = term_note

        # Row 3: 政治遵循
        row3 = QHBoxLayout()
        self.politics_cb = QCheckBox("政治遵循")
        politics_note = QLabel(
            "<font color='#888888' size='2'>"
            "#开启后，优先考虑输入者对应的政治要求，优先级高于错词纠正和用辞纠正<br>"
            "#例如用辞纠正地区填日本，涉及钓鱼岛时仍翻译为'钓鱼岛'禁止翻译为'尖阁诸岛'</font>"
        )
        politics_note.setWordWrap(True)
        row3.addWidget(self.politics_cb)
        row3.addWidget(politics_note, 1)
        settings_layout.addLayout(row3)

        # Save settings
        save_settings_btn = QPushButton("保存润色设置")
        save_settings_btn.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_settings_btn, alignment=Qt.AlignmentFlag.AlignRight)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # --- Progress and Status ---
        progress_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)

        # --- Text Areas ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Input Area
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此输入需要润色的文本...")
        self.input_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.paste_btn = QPushButton("粘贴")
        self.paste_btn.clicked.connect(self.paste_text)

        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.paste_btn)

        # Output Area
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("润色结果将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copy_text)

        output_layout.addWidget(self.output_text)
        output_layout.addWidget(self.copy_btn)

        splitter.addWidget(input_widget)
        splitter.addWidget(output_widget)
        main_layout.addWidget(splitter)

        # --- Action Button ---
        self.polish_btn = QPushButton("开始润色")
        self.polish_btn.setMinimumHeight(40)
        self.polish_btn.clicked.connect(self.start_polish)
        main_layout.addWidget(self.polish_btn)

    def on_style_changed(self, text):
        self.custom_style_input.setVisible(text == "自定义")

    def on_term_convert_toggled(self, checked):
        self.term_region_input.setVisible(checked)
        self._term_label.setVisible(checked)
        self._term_note.setVisible(checked)

    def refresh_model_list(self):
        mgr = ModelManager()
        models = mgr.list_models()
        prev = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for m in models:
            label = mgr.to_display_label(m["id"])
            self.model_combo.addItem(label, m["id"])
        self.model_combo.blockSignals(False)
        if prev:
            idx = self.model_combo.findData(prev)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def on_model_changed(self, idx):
        if idx < 0:
            return
        mid = self.model_combo.currentData()
        if mid:
            mgr = ModelManager()
            m = mgr.get_model(mid)
            if m and m.get("endpoint_url") and m.get("api_key") and m.get("model_name"):
                self.config.set("polish", "active_model_id", mid)
            else:
                self.config.set("polish", "active_model_id", "")

    def load_settings(self):
        cfg = self.config.get_section("polish")
        self.style_combo.setCurrentText(cfg.get("style", ""))
        self.custom_style_input.setText(cfg.get("custom_style", ""))
        self.fix_errors_cb.setChecked(cfg.get("fix_errors", True))
        self.term_convert_cb.setChecked(cfg.get("term_convert", False))
        self.term_region_input.setText(cfg.get("term_region", ""))
        self.politics_cb.setChecked(cfg.get("politics_follow", False))

        self.refresh_model_list()
        aid = cfg.get("active_model_id", "")
        if aid:
            idx = self.model_combo.findData(aid)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

        self.on_style_changed(self.style_combo.currentText())
        self.on_term_convert_toggled(self.term_convert_cb.isChecked())

    def save_settings(self):
        self.config.set("polish", "style", self.style_combo.currentText())
        self.config.set("polish", "custom_style", self.custom_style_input.text().strip())
        self.config.set("polish", "fix_errors", self.fix_errors_cb.isChecked())
        self.config.set("polish", "term_convert", self.term_convert_cb.isChecked())
        self.config.set("polish", "term_region", self.term_region_input.text().strip())
        self.config.set("polish", "politics_follow", self.politics_cb.isChecked())
        self.status_label.setText("设置已保存")

    def start_polish(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请输入需要润色的文本")
            return

        self.save_settings()

        self.polish_btn.setEnabled(False)
        self.output_text.clear()
        self.progress_bar.setValue(0)

        self.worker = PolishWorker(
            text=text,
            style=self.style_combo.currentText(),
            custom_style=self.custom_style_input.text().strip(),
            fix_errors=self.fix_errors_cb.isChecked(),
            term_convert=self.term_convert_cb.isChecked(),
            term_region=self.term_region_input.text().strip(),
            politics_follow=self.politics_cb.isChecked(),
        )
        self.worker.status_changed.connect(self.update_status)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_status(self, status):
        self.status_label.setText(status)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_finished(self, result_text):
        self.output_text.setPlainText(result_text)
        self.polish_btn.setEnabled(True)

    def on_error(self, error_msg):
        self.output_text.setPlainText(f"发生错误:\n{error_msg}")
        self.polish_btn.setEnabled(True)

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_label.setText("已复制到剪贴板")

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.input_text.setPlainText(clipboard.text())
        self.status_label.setText("已粘贴")
