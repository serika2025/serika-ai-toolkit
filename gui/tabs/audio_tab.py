import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextEdit, QPushButton, QProgressBar, QGroupBox,
                             QLineEdit, QFileDialog, QApplication, QMessageBox, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QEvent
from config.config_manager import ConfigManager
from config.model_manager import ModelManager
from workers.audio_worker import AudioWorker
from utils.audio_converter import FfmpegDownloadWorker, get_supported_formats

class AudioTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.worker = None
        self.ffmpeg_worker = None
        self.audio_path = None
        self.init_ui()

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

        model_hint = QLabel(
            "<font color='#888888' size='2'>"
            "# 国内推荐: 硅基流动 — ai_format=OpenAI, 端点 https://api.siliconflow.cn/v1, 模型 FunAudioLLM/SenseVoiceSmall<br>"
            "# 也可使用: 百炼多模态(ai_format=OpenAI(多模态), 模型 qwen-audio-turbo) 或 Gemini(ai_format=Gemini, 模型 gemini-1.5-flash)</font>"
        )
        model_hint.setWordWrap(True)
        main_layout.addWidget(model_hint)

        # --- Settings Group ---
        settings_group = QGroupBox("听力设置")
        settings_layout = QVBoxLayout()

        # Language and Region inputs
        hint_layout = QHBoxLayout()

        lang_section = QVBoxLayout()
        lang_label = QLabel("请输入可能出现的语言：")
        self.lang_input = QLineEdit()
        self.lang_input.setPlaceholderText("用逗号分隔，例如：中文, 英文, 日文")
        lang_note = QLabel("<font color='#888888' size='2'>#留空则由模型自动判断</font>")
        lang_section.addWidget(lang_label)
        lang_section.addWidget(self.lang_input)
        lang_section.addWidget(lang_note)

        region_section = QVBoxLayout()
        region_label = QLabel("涉及的国家或地区：")
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("用逗号分隔，例如：CN, TW, HK, JP")
        region_note = QLabel("<font color='#888888' size='2'>#留空则由模型自动判断，填写可帮助区分方言和用语习惯</font>")
        region_section.addWidget(region_label)
        region_section.addWidget(self.region_input)
        region_section.addWidget(region_note)

        hint_layout.addLayout(lang_section)
        hint_layout.addLayout(region_section)
        settings_layout.addLayout(hint_layout)

        # Auto line break
        self.auto_wrap_cb = QCheckBox("自动换行")
        self.auto_wrap_cb.setToolTip("#开启后，模型会根据音频自动进行换行，便于阅读，但有些情况下他可能不应该开启")
        settings_layout.addWidget(self.auto_wrap_cb)

        # File upload area (supports drag-drop)
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("音频文件:"))

        self.file_label = QLabel("拖拽音频文件到此处，或点击右侧按钮")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setMinimumHeight(36)
        self.file_label.setStyleSheet(
            "QLabel { border: 2px dashed #888888; border-radius: 6px; "
            "padding: 6px; color: #888888; }"
        )
        self.file_label.setAcceptDrops(True)
        self.file_label.installEventFilter(self)
        file_layout.addWidget(self.file_label, 1)

        self.browse_btn = QPushButton("选择音频文件")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(file_layout)

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

        # --- Output Area ---
        output_group = QGroupBox("转写结果")
        output_layout = QVBoxLayout()

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("转写的文本将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        output_layout.addWidget(self.output_text)

        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.copy_text)
        output_layout.addWidget(self.copy_btn)

        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # --- Action Button ---
        self.transcribe_btn = QPushButton("开始转写")
        self.transcribe_btn.setMinimumHeight(40)
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.transcribe_btn.setEnabled(False)
        main_layout.addWidget(self.transcribe_btn)

        self.load_settings()

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
            # Verify model exists before saving
            mgr = ModelManager()
            m = mgr.get_model(mid)
            if m and m.get("endpoint_url") and m.get("api_key") and m.get("model_name"):
                self.config.set("audio", "active_model_id", mid)
            else:
                # Model is broken, clear selection
                self.config.set("audio", "active_model_id", "")

    def load_settings(self):
        audio_cfg = self.config.get_section("audio")
        self.lang_input.setText(audio_cfg.get("languages", ""))
        self.region_input.setText(audio_cfg.get("regions", ""))
        self.auto_wrap_cb.setChecked(audio_cfg.get("auto_line_break", False))

        self.refresh_model_list()
        aid = audio_cfg.get("active_model_id", "")
        if aid:
            idx = self.model_combo.findData(aid)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    # ---------------- Drag & Drop -----------------
    def eventFilter(self, obj, event):
        if obj is self.file_label:
            if event.type() == QEvent.Type.DragEnter:
                self.dragEnterEvent(event)
                return True
            elif event.type() == QEvent.Type.Drop:
                self.dropEvent(event)
                return True
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                path = urls[0].toLocalFile().lower()
                exts = ('.wav', '.mp3', '.m4a', '.ogg', '.flac', '.wma', '.aac', '.aiff', '.webm')
                if any(path.endswith(ext) for ext in exts):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                self.set_audio_file(path)

    # ---------------- File Selection ----------------
    def browse_file(self):
        # Build filter string that actually works on all platforms
        fmts = get_supported_formats()  # "*.wav *.mp3 *.m4a ..."
        file_filter = f"音频文件 ({fmts});;所有文件 (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", file_filter
        )
        if file_path:
            self.set_audio_file(file_path)

    def set_audio_file(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            return
        self.audio_path = os.path.abspath(file_path)
        self.file_label.setText(os.path.basename(file_path))
        self.file_label.setStyleSheet(
            "QLabel { border: 2px solid #4CAF50; border-radius: 6px; "
            "padding: 6px; color: inherit; font-weight: bold; }"
        )
        self.transcribe_btn.setEnabled(True)
        self.status_label.setText(f"已选择: {os.path.basename(file_path)}")

    # ---------------- Transcription ----------------
    def start_transcription(self):
        if not self.audio_path:
            self.status_label.setText("请先选择音频文件")
            return

        self.transcribe_btn.setEnabled(False)
        self.output_text.clear()
        self.progress_bar.setValue(0)

        self.worker = AudioWorker(
            audio_path=self.audio_path,
            languages=self.lang_input.text().strip(),
            regions=self.region_input.text().strip(),
            auto_line_break=self.auto_wrap_cb.isChecked()
        )
        self.worker.status_changed.connect(self.update_status)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished.connect(self.on_transcription_finished)
        self.worker.error.connect(self.on_transcription_error)
        self.worker.ffmpeg_missing.connect(self.on_ffmpeg_missing)
        self.worker.start()

    def update_status(self, status):
        self.status_label.setText(status)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_transcription_finished(self, result_text):
        self.output_text.setPlainText(result_text)
        self.transcribe_btn.setEnabled(True)

    def on_transcription_error(self, error_msg):
        self.output_text.setPlainText(f"发生错误:\n{error_msg}")
        self.transcribe_btn.setEnabled(True)

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.status_label.setText("已复制到剪贴板")

    # ---------------- ffmpeg download ----------------
    def on_ffmpeg_missing(self):
        reply = QMessageBox.question(
            self, "下载 ffmpeg",
            "未检测到 ffmpeg，是否自动下载？\n（约 30MB，下载后程序将自动重启）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            self.transcribe_btn.setEnabled(True)
            return

        # Start download worker - shows progress on the bar immediately
        self.ffmpeg_worker = FfmpegDownloadWorker()
        self.ffmpeg_worker.status_changed.connect(self.update_status)
        self.ffmpeg_worker.progress_changed.connect(self.update_progress)
        self.ffmpeg_worker.finished.connect(self.on_ffmpeg_download_done)
        self.ffmpeg_worker.error.connect(self.on_ffmpeg_download_error)
        self.ffmpeg_worker.start()

    def on_ffmpeg_download_done(self, success):
        if success:
            # Restart the application
            import sys
            QMessageBox.information(self, "完成", "ffmpeg 下载完成，程序即将重启。")
            if getattr(sys, 'frozen', False):
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            self.transcribe_btn.setEnabled(True)

    def on_ffmpeg_download_error(self, err_msg):
        QMessageBox.critical(
            self, "下载失败",
            f"ffmpeg 下载失败：{err_msg}\n\n"
            "请手动下载 ffmpeg：https://ffmpeg.org/download.html\n"
            "并将 ffmpeg.exe 放置到程序目录下的 ffmpeg_bin 文件夹中。"
        )
        self.transcribe_btn.setEnabled(True)
