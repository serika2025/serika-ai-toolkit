from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QCheckBox, QTextEdit, QPushButton,
                             QProgressBar, QGroupBox, QSplitter, QApplication,
                             QLineEdit, QSpinBox)
from PyQt6.QtCore import Qt
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from workers.expand_worker import ExpandWorker, count_text


class ExpandTab(QWidget):
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
        settings_group = QGroupBox("扩写设置")
        settings_layout = QVBoxLayout()

        # Row 1: 字数要求 / 容差 / 最大打回次数
        row1 = QHBoxLayout()

        # 字数要求
        wc_section = QVBoxLayout()
        wc_label = QLabel("字数要求：")
        self.target_count_spin = QSpinBox()
        self.target_count_spin.setRange(1, 100000)
        self.target_count_spin.setValue(800)
        wc_note = QLabel(
            "<font color='#888888' size='2'>"
            "#中文、日文、韩文等方块字为字数，英文、西语等检查单词数<br>"
            "#字数要求高于原文时为扩写，低于原文时为精简</font>"
        )
        wc_note.setWordWrap(True)
        wc_section.addWidget(wc_label)
        wc_section.addWidget(self.target_count_spin)
        wc_section.addWidget(wc_note)
        row1.addLayout(wc_section)

        # 容差
        tol_section = QVBoxLayout()
        tol_label = QLabel("容差：")
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 10000)
        self.tolerance_spin.setValue(50)
        tol_note = QLabel(
            "<font color='#888888' size='2'>"
            "#填写容差的字数或单词数，不算标点符号<br>"
            "#当AI生成文本超出[要求-容差, 要求+容差]范围时自动打回重做</font>"
        )
        tol_note.setWordWrap(True)
        tol_section.addWidget(tol_label)
        tol_section.addWidget(self.tolerance_spin)
        tol_section.addWidget(tol_note)
        row1.addLayout(tol_section)

        # 最大打回次数
        retry_section = QVBoxLayout()
        retry_label = QLabel("最大打回次数：")
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 20)
        self.max_retries_spin.setValue(3)
        retry_note = QLabel(
            "<font color='#888888' size='2'>"
            "#生成文本的去标点字数/单词数超过容差则会被打回<br>"
            "#提高打回次数可能会增加等待时间以及token消耗</font>"
        )
        retry_note.setWordWrap(True)
        retry_section.addWidget(retry_label)
        retry_section.addWidget(self.max_retries_spin)
        retry_section.addWidget(retry_note)
        row1.addLayout(retry_section)

        row1.addStretch()
        settings_layout.addLayout(row1)

        # Row 2: 契合原文 / 政治遵循
        row2 = QHBoxLayout()

        self.fit_original_cb = QCheckBox("契合原文")
        fit_note = QLabel(
            "<font color='#888888' size='2'>"
            "#开启后，不允许模型随意编造事例用于扩写，"
            "只能通过添加修饰或更换长文本词汇进行扩写或精简</font>"
        )
        fit_note.setWordWrap(True)
        row2.addWidget(self.fit_original_cb)
        row2.addWidget(fit_note, 1)

        self.politics_cb = QCheckBox("政治遵循")
        politics_note = QLabel(
            "<font color='#888888' size='2'>"
            "#开启后，模型会自动识别该稿件写作者国籍并在扩写中选择符合叙事要求的内容</font>"
        )
        politics_note.setWordWrap(True)
        row2.addWidget(self.politics_cb)
        row2.addWidget(politics_note, 1)
        settings_layout.addLayout(row2)

        # Row 3: 性质
        row3 = QHBoxLayout()
        nature_label = QLabel("性质：")
        self.nature_input = QLineEdit()
        self.nature_input.setPlaceholderText("例如：新闻稿、小说、论文、公告等")
        nature_note = QLabel(
            "<font color='#888888' size='2'>"
            "#可以填写给AI的较短的附言，例如指明这是新闻稿还是小说还是什么什么</font>"
        )
        nature_note.setWordWrap(True)
        row3.addWidget(nature_label)
        row3.addWidget(self.nature_input, 1)
        row3.addWidget(nature_note, 1)
        settings_layout.addLayout(row3)

        # Save settings
        save_settings_btn = QPushButton("保存扩写设置")
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
        self.input_text.setPlaceholderText("在此输入需要扩写/精简的文本...")
        self.input_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_text.textChanged.connect(self.on_input_changed)

        self.input_count_label = QLabel("")
        self.input_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.paste_btn = QPushButton("粘贴")
        self.paste_btn.clicked.connect(self.paste_text)

        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.input_count_label)
        input_layout.addWidget(self.paste_btn)

        # Output Area
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("扩写/精简结果将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.output_count_label = QLabel("")
        self.output_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copy_text)

        output_layout.addWidget(self.output_text)
        output_layout.addWidget(self.output_count_label)
        output_layout.addWidget(self.copy_btn)

        splitter.addWidget(input_widget)
        splitter.addWidget(output_widget)
        main_layout.addWidget(splitter)

        # --- Action Button ---
        self.expand_btn = QPushButton("开始扩写/精简")
        self.expand_btn.setMinimumHeight(40)
        self.expand_btn.clicked.connect(self.start_expand)
        main_layout.addWidget(self.expand_btn)

    def on_input_changed(self):
        text = self.input_text.toPlainText()
        if not text.strip():
            self.input_count_label.setText("")
            return
        cnt, unit = count_text(text)
        self.input_count_label.setText(f"原文: {cnt} {'字' if unit == 'char' else '个单词'}")

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
                self.config.set("expand", "active_model_id", mid)
            else:
                self.config.set("expand", "active_model_id", "")

    def load_settings(self):
        cfg = self.config.get_section("expand")
        self.target_count_spin.setValue(cfg.get("target_count", 800))
        self.tolerance_spin.setValue(cfg.get("tolerance", 50))
        self.max_retries_spin.setValue(cfg.get("max_retries", 3))
        self.fit_original_cb.setChecked(cfg.get("fit_original", True))
        self.politics_cb.setChecked(cfg.get("politics_follow", False))
        self.nature_input.setText(cfg.get("text_nature", ""))

        self.refresh_model_list()
        aid = cfg.get("active_model_id", "")
        if aid:
            idx = self.model_combo.findData(aid)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

        self.on_input_changed()

    def save_settings(self):
        self.config.set("expand", "target_count", self.target_count_spin.value())
        self.config.set("expand", "tolerance", self.tolerance_spin.value())
        self.config.set("expand", "max_retries", self.max_retries_spin.value())
        self.config.set("expand", "fit_original", self.fit_original_cb.isChecked())
        self.config.set("expand", "politics_follow", self.politics_cb.isChecked())
        self.config.set("expand", "text_nature", self.nature_input.text().strip())
        self.status_label.setText("设置已保存")

    def start_expand(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请输入需要扩写/精简的文本")
            return

        self.save_settings()

        self.expand_btn.setEnabled(False)
        self.output_text.clear()
        self.output_count_label.setText("")
        self.progress_bar.setValue(0)

        self.worker = ExpandWorker(
            text=text,
            target_count=self.target_count_spin.value(),
            tolerance=self.tolerance_spin.value(),
            max_retries=self.max_retries_spin.value(),
            fit_original=self.fit_original_cb.isChecked(),
            politics_follow=self.politics_cb.isChecked(),
            text_nature=self.nature_input.text().strip(),
        )
        self.worker.status_changed.connect(self.update_status)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.retry_occurred.connect(self.on_retry)
        self.worker.start()

    def update_status(self, status):
        self.status_label.setText(status)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_retry(self, current, max_retries):
        self.progress_bar.setValue(0)

    def on_finished(self, result_text):
        self.output_text.setPlainText(result_text)
        self.expand_btn.setEnabled(True)
        # Show output count
        cnt, unit = count_text(result_text)
        self.output_count_label.setText(f"输出: {cnt} {'字' if unit == 'char' else '个单词'}")

    def on_error(self, error_msg):
        self.output_text.setPlainText(f"发生错误:\n{error_msg}")
        self.expand_btn.setEnabled(True)

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_label.setText("已复制到剪贴板")

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.input_text.setPlainText(clipboard.text())
        self.status_label.setText("已粘贴")
