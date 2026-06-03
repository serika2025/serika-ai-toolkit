import sys
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QPushButton, QFormLayout,
                             QMessageBox, QCheckBox, QInputDialog, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from config.config_manager import ConfigManager
from utils.theme import apply_theme


def _icon_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "icon.ico")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.ico")


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("全局设置")
        self.setWindowIcon(QIcon(_icon_path()))
        self.setMinimumWidth(400)
        self.config = ConfigManager()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        form_layout.addRow("主题设置:", self.theme_combo)

        # Crash Reporter
        self.crash_reporter_cb = QCheckBox("崩溃显示")
        self.crash_reporter_cb.setToolTip("开启后，程序崩溃时将弹出错误报告窗口")
        form_layout.addRow("高级选项:", self.crash_reporter_cb)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def load_settings(self):
        global_cfg = self.config.get_section("global")
        self.theme_combo.setCurrentText(global_cfg.get("theme", "System"))
        self.crash_reporter_cb.setChecked(global_cfg.get("enable_crash_reporter", True))

    def save_settings(self):
        self.config.set("global", "theme", self.theme_combo.currentText())
        self.config.set("global", "enable_crash_reporter", self.crash_reporter_cb.isChecked())

        apply_theme(QApplication.instance(), self.theme_combo.currentText())

        QMessageBox.information(self, "成功", "设置已保存！主题已自动更新。")
        self.accept()
