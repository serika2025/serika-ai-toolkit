import sys
import os
import subprocess
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow
from config.config_manager import ConfigManager, _app_dir
from utils.theme import apply_theme


def _get_icon_path():
    """Return path to icon.ico, works in both dev and frozen mode."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "icon.ico")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

def global_exception_handler(exc_type, exc_value, exc_traceback):
    # Write exception to crash.log (in app dir when frozen)
    crash_log = os.path.join(_app_dir(), "crash.log")
    with open(crash_log, "w", encoding="utf-8") as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler

def main():
    app_dir = _app_dir()
    crash_log = os.path.join(app_dir, "crash.log")

    # Clean up old crash log
    if os.path.exists(crash_log):
        try:
            os.remove(crash_log)
        except:
            pass

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(_get_icon_path()))

    # Load config and apply theme
    config = ConfigManager()
    theme = config.get("global", "theme", "System")
    apply_theme(app, theme)
    
    # Launch crash reporter if enabled (only in dev mode, not frozen)
    if config.get("global", "enable_crash_reporter", True) and not getattr(sys, 'frozen', False):
        try:
            crash_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_reporter.py")
            subprocess.Popen(
                [sys.executable, crash_script, str(os.getpid())],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception as e:
            print(f"Failed to start crash reporter: {e}")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
