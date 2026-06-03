from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_theme(app, theme_name):
    if theme_name == "Dark":
        app.setStyle("Fusion")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 43))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(dark_palette)

        app.setStyleSheet("""
            QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
            QGroupBox { border: 1px solid #555555; border-radius: 5px; margin-top: 1.5ex; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #ffffff; }
            QTabWidget::pane { border: 1px solid #555555; }
            QTabBar::tab { background-color: #3b3b3b; color: #aaaaaa; border: 1px solid #555555; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #2b2b2b; color: #ffffff; border-bottom-color: #2b2b2b; }
            QTabBar::tab:hover:!selected { background-color: #4b4b4b; color: #ffffff; }
            QSplitter::handle { background-color: #555555; margin: 2px; }
            QCheckBox::indicator:checked { background-color: #2a82da; border: 1px solid #2a82da; }
            QProgressBar { border: 1px solid #555555; text-align: center; color: white; background-color: #3b3b3b; }
            QProgressBar::chunk { background-color: #2a82da; }
        """)
    elif theme_name == "Light":
        app.setStyle("Fusion")
        # Build an explicit light palette - do NOT rely on standardPalette() which may be stale
        light_palette = QPalette()
        light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        light_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        light_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 200))
        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        app.setPalette(light_palette)

        # Clear stylesheet explicitly to remove dark QSS
        app.setStyleSheet("")
    else:
        # System default
        app.setStyle("Fusion")
        # Build an explicit light-neutral palette as baseline
        sys_palette = QPalette()
        sys_palette.setColor(QPalette.ColorRole.Window, QColor(239, 239, 239))
        sys_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        sys_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        sys_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        sys_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        sys_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        sys_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        sys_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        sys_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        app.setPalette(sys_palette)
        app.setStyleSheet("")
