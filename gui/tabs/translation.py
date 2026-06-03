from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QCheckBox, QTextEdit, QPushButton, 
                             QProgressBar, QGroupBox, QSplitter, QApplication, QLineEdit)
from PyQt6.QtCore import Qt
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from workers.ai_worker import TranslationWorker
from gui.components.searchable_combo import SearchableComboBox

class TranslationTab(QWidget):
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
        settings_group = QGroupBox("翻译设置")
        settings_layout = QVBoxLayout()
        
        # Languages
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("原语言:"))
        self.source_lang_combo = SearchableComboBox(fallback_text="自动识别")
        self.source_lang_combo.addItems(["自动识别", "大陆简体", "香港特别行政区繁体", "台湾省繁体", "新马简体", "英式英文", "美式英文", "法文", "俄文", "西班牙西语", "拉美西语", "阿拉伯语", "日文", "德文", "朝鲜族语", "朝鲜语", "韩国语", "意大利语", "葡萄牙葡萄牙语", "巴西葡萄牙语", "荷兰语", "瑞典语", "丹麦语", "挪威语", "芬兰语", "冰岛语", "波兰语", "捷克语", "斯洛伐克语", "匈牙利语", "罗马尼亚语", "保加利亚语", "塞尔维亚语", "克罗地亚语", "波斯尼亚语", "斯洛文尼亚语", "马其顿语", "阿尔巴尼亚语", "希腊语", "乌克兰语", "白俄罗斯语", "爱沙尼亚语", "拉脱维亚语", "立陶宛语", "爱尔兰语", "马耳他语", "加泰罗尼亚语", "藏文", "维吾尔语", "西里尔蒙古文", "传统蒙古文", "阿拉伯字母哈萨克文", "壮文", "彝文", "泰文", "高棉文", "缅甸文", "老挝文", "越南文", "印尼文", "马来文", "文莱马来语", "他加禄语", "西里尔哈萨克文", "拉丁哈萨克文", "西里尔乌兹别克文", "拉丁乌兹别克文", "吉尔吉斯文", "塔吉克文", "土库曼文", "波斯语", "希伯来语", "土耳其语", "阿塞拜疆语", "格鲁吉亚语", "亚美尼亚语"])
        lang_layout.addWidget(self.source_lang_combo)
        
        lang_layout.addWidget(QLabel("目标语言:"))
        self.target_lang_combo = SearchableComboBox(fallback_text="自定义")
        self.target_lang_combo.addItems(["大陆简体", "香港特别行政区繁体", "台湾省繁体", "新马简体", "英式英文", "美式英文", "法文", "俄文", "西班牙西语", "拉美西语", "阿拉伯语", "日文", "德文", "朝鲜族语", "朝鲜语", "韩国语", "意大利语", "葡萄牙葡萄牙语", "巴西葡萄牙语", "荷兰语", "瑞典语", "丹麦语", "挪威语", "芬兰语", "冰岛语", "波兰语", "捷克语", "斯洛伐克语", "匈牙利语", "罗马尼亚语", "保加利亚语", "塞尔维亚语", "克罗地亚语", "波斯尼亚语", "斯洛文尼亚语", "马其顿语", "阿尔巴尼亚语", "希腊语", "乌克兰语", "白俄罗斯语", "爱沙尼亚语", "拉脱维亚语", "立陶宛语", "爱尔兰语", "马耳他语", "加泰罗尼亚语", "藏文", "维吾尔语", "西里尔蒙古文", "传统蒙古文", "阿拉伯字母哈萨克文", "壮文", "彝文", "泰文", "高棉文", "缅甸文", "老挝文", "越南文", "印尼文", "马来文", "文莱马来语", "他加禄语", "西里尔哈萨克文", "拉丁哈萨克文", "西里尔乌兹别克文", "拉丁乌兹别克文", "吉尔吉斯文", "塔吉克文", "土库曼文", "波斯语", "希伯来语", "土耳其语", "阿塞拜疆语", "格鲁吉亚语", "亚美尼亚语", "自定义"])
        self.target_lang_combo.currentTextChanged.connect(self.on_target_lang_changed)
        lang_layout.addWidget(self.target_lang_combo)
        lang_layout.addStretch()
        settings_layout.addLayout(lang_layout)

        # Custom Language Inputs (Hidden by default)
        self.custom_lang_widget = QWidget()
        custom_lang_layout = QHBoxLayout(self.custom_lang_widget)
        custom_lang_layout.setContentsMargins(0, 0, 0, 0)
        
        # Language Name
        lang_name_layout = QVBoxLayout()
        lang_name_layout.addWidget(QLabel("语种名称:"))
        self.custom_lang_name = QLineEdit()
        lang_name_layout.addWidget(self.custom_lang_name)
        lang_name_note = QLabel("<font color='#888888' size='2'>#列表中无所需语言时可使用此项</font>")
        lang_name_layout.addWidget(lang_name_note)
        custom_lang_layout.addLayout(lang_name_layout)
        
        # Region
        region_layout = QVBoxLayout()
        region_layout.addWidget(QLabel("国家或地区:"))
        self.custom_region = QLineEdit()
        region_layout.addWidget(self.custom_region)
        region_note = QLabel("<font color='#888888' size='2'>#可书写名称或代号，翻译器会自动匹配语言习惯。</font>")
        region_layout.addWidget(region_note)
        custom_lang_layout.addLayout(region_layout)
        
        self.custom_lang_widget.setVisible(False)
        settings_layout.addWidget(self.custom_lang_widget)

        # Checkboxes
        self.keep_abbr_cb = QCheckBox("保留通用简称")
        self.keep_abbr_cb.setToolTip("勾选后，翻译在遇到如AI、MCP、CN、HK时不予翻译")
        
        self.auto_correct_cb = QCheckBox("自动纠错")
        self.auto_correct_cb.setToolTip("勾选后AI会自动纠正部分可能错误的语句或选择符合语境的称谓，否则直接直译")
        
        self.keep_format_cb = QCheckBox("格式保留")
        self.keep_format_cb.setToolTip("勾选后缩进、换行等等格式将被保留，否则由AI自行决定")

        self.politics_cb = QCheckBox("政治遵循")
        self.politics_cb.setToolTip("勾选后，涉及地名/领土/政治称谓时严格遵循原文国籍的官方表述")

        # Add small notes next to checkboxes
        cb_layout1 = QHBoxLayout()
        cb_layout1.addWidget(self.keep_abbr_cb)
        note1 = QLabel(" <font color='#888888' size='2'>#勾选后，翻译在遇到如AI、MCP、CN、HK时不予翻译</font>")
        cb_layout1.addWidget(note1)
        cb_layout1.addStretch()
        
        cb_layout2 = QHBoxLayout()
        cb_layout2.addWidget(self.auto_correct_cb)
        note2 = QLabel(" <font color='#888888' size='2'>#勾选后AI会自动纠正部分可能错误的语句或选择符合语境的称谓，否则直接直译</font>")
        cb_layout2.addWidget(note2)
        cb_layout2.addStretch()
        
        cb_layout3 = QHBoxLayout()
        cb_layout3.addWidget(self.keep_format_cb)
        note3 = QLabel(" <font color='#888888' size='2'>#勾选后缩进、换行等等格式将被保留，否则由AI自行决定</font>")
        cb_layout3.addWidget(note3)
        cb_layout3.addStretch()

        settings_layout.addLayout(cb_layout1)
        settings_layout.addLayout(cb_layout2)
        settings_layout.addLayout(cb_layout3)

        cb_layout4 = QHBoxLayout()
        cb_layout4.addWidget(self.politics_cb)
        note4 = QLabel(" <font color='#888888' size='2'>#勾选后，涉及地名/领土/政治称谓时严格遵循原文国籍的官方表述（如钓鱼岛不会翻成尖阁诸岛）</font>")
        cb_layout4.addWidget(note4)
        cb_layout4.addStretch()
        settings_layout.addLayout(cb_layout4)
        
        # Save settings button
        save_settings_btn = QPushButton("保存翻译设置")
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
        self.input_text.setPlaceholderText("在此输入需要翻译的文本...")
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
        self.output_text.setPlaceholderText("翻译结果将显示在这里...")
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
        self.translate_btn = QPushButton("开始翻译")
        self.translate_btn.setMinimumHeight(40)
        self.translate_btn.clicked.connect(self.start_translation)
        main_layout.addWidget(self.translate_btn)

    def on_target_lang_changed(self, text):
        if text == "自定义":
            self.custom_lang_widget.setVisible(True)
        else:
            self.custom_lang_widget.setVisible(False)

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
        # Restore previous selection
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
                self.config.set("translation", "active_model_id", mid)
            else:
                self.config.set("translation", "active_model_id", "")

    def load_settings(self):
        trans_cfg = self.config.get_section("translation")
        self.source_lang_combo.setCurrentText(trans_cfg.get("source_lang", "自动识别"))
        self.target_lang_combo.setCurrentText(trans_cfg.get("target_lang", "大陆简体"))
        self.custom_lang_name.setText(trans_cfg.get("custom_lang_name", ""))
        self.custom_region.setText(trans_cfg.get("custom_region", ""))
        self.keep_abbr_cb.setChecked(trans_cfg.get("keep_abbr", False))
        self.auto_correct_cb.setChecked(trans_cfg.get("auto_correct", False))
        self.keep_format_cb.setChecked(trans_cfg.get("keep_format", True))
        self.politics_cb.setChecked(trans_cfg.get("politics_follow", False))

        # Load model list and restore selection
        self.refresh_model_list()
        aid = trans_cfg.get("active_model_id", "")
        if aid:
            idx = self.model_combo.findData(aid)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

        self.on_target_lang_changed(self.target_lang_combo.currentText())

    def save_settings(self):
        self.config.set("translation", "source_lang", self.source_lang_combo.currentText())
        self.config.set("translation", "target_lang", self.target_lang_combo.currentText())
        self.config.set("translation", "custom_lang_name", self.custom_lang_name.text().strip())
        self.config.set("translation", "custom_region", self.custom_region.text().strip())
        self.config.set("translation", "keep_abbr", self.keep_abbr_cb.isChecked())
        self.config.set("translation", "auto_correct", self.auto_correct_cb.isChecked())
        self.config.set("translation", "keep_format", self.keep_format_cb.isChecked())
        self.config.set("translation", "politics_follow", self.politics_cb.isChecked())
        self.status_label.setText("设置已保存")

    def start_translation(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            self.status_label.setText("请输入需要翻译的文本")
            return

        # Save settings before translating to ensure latest are used
        self.save_settings()

        self.translate_btn.setEnabled(False)
        self.output_text.clear()
        self.progress_bar.setValue(0)
        
        self.worker = TranslationWorker(text)
        self.worker.status_changed.connect(self.update_status)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()

    def update_status(self, status):
        self.status_label.setText(status)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_translation_finished(self, result_text):
        self.output_text.setPlainText(result_text)
        self.translate_btn.setEnabled(True)

    def on_translation_error(self, error_msg):
        self.output_text.setPlainText(f"发生错误:\n{error_msg}")
        self.translate_btn.setEnabled(True)

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_label.setText("已复制到剪贴板")

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.input_text.setPlainText(clipboard.text())
        self.status_label.setText("已粘贴")
