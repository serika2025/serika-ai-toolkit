from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QToolBar, QMessageBox
from PyQt6.QtGui import QAction
from gui.tabs.translation import TranslationTab
from gui.tabs.expand_tab import ExpandTab
from gui.tabs.polish_tab import PolishTab
from gui.tabs.audio_tab import AudioTab
from gui.settings_window import SettingsWindow
from gui.model_settings_window import ModelSettingsWindow
from config.config_manager import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 专业任务助手")
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)

        settings_action = QAction("全局设置", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        model_action = QAction("模型设置", self)
        model_action.triggered.connect(self.open_model_settings)
        toolbar.addAction(model_action)

        usage_action = QAction("消耗记录", self)
        usage_action.triggered.connect(self.show_usage)
        toolbar.addAction(usage_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()

        self.translation_tab = TranslationTab()
        self.tabs.addTab(self.translation_tab, "翻译")

        self.expansion_tab = ExpandTab()
        self.tabs.addTab(self.expansion_tab, "扩写")

        self.polish_tab = PolishTab()
        self.tabs.addTab(self.polish_tab, "润色")

        self.audio_tab = AudioTab()
        self.tabs.addTab(self.audio_tab, "听力")

        layout.addWidget(self.tabs)

    def open_settings(self):
        dialog = SettingsWindow(self)
        dialog.exec()

    def open_model_settings(self):
        dialog = ModelSettingsWindow(self)
        dialog.exec()
        # Refresh model selectors in all tabs after editing
        self.translation_tab.refresh_model_list()
        self.audio_tab.refresh_model_list()
        self.expansion_tab.refresh_model_list()
        self.polish_tab.refresh_model_list()

    def show_usage(self):
        config = ConfigManager()
        usage = config.get_usage()
        prompt_tokens = usage.get("total_prompt_tokens", 0)
        completion_tokens = usage.get("total_completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        msg = f"软件总消耗记录：\n\n" \
              f"提示词 Token (Prompt): {prompt_tokens}\n" \
              f"补全 Token (Completion): {completion_tokens}\n" \
              f"总计 Token (Total): {total_tokens}"

        QMessageBox.information(self, "消耗记录", msg)
