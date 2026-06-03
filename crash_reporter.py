import sys
import os
import time
import psutil
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QPushButton, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class CrashReporterDialog(QDialog):
    def __init__(self, log_content):
        super().__init__()
        self.setWindowTitle("程序崩溃报告")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")))
        self.resize(600, 400)
        self.log_content = log_content
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Analyze reason
        reason = "遇到了一个无法识别的错误"
        if "ModuleNotFoundError" in self.log_content or "ImportError" in self.log_content:
            reason = "依赖库不全或缺失"
        elif "SyntaxError" in self.log_content or "IndentationError" in self.log_content:
            reason = "程序代码损坏或存在语法错误"
        elif "PermissionError" in self.log_content:
            reason = "权限不足，无法读写文件"

        reason_label = QLabel(f"<b>崩溃原因：</b>{reason}")
        reason_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(reason_label)

        solution_label = QLabel(
            "<b>处理方法：</b>如果想对开发者反映该问题或下载源代码后自行处理问题，"
            "请选择导出错误报告或复制错误信息，而不是只发送这个窗口的截图。"
        )
        solution_label.setTextFormat(Qt.TextFormat.RichText)
        solution_label.setWordWrap(True)
        layout.addWidget(solution_label)

        layout.addWidget(QLabel("系统输出日志:"))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlainText(self.log_content)
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制错误信息")
        copy_btn.clicked.connect(self.copy_log)
        
        export_btn = QPushButton("导出错误报告")
        export_btn.clicked.connect(self.export_log)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_content)
        QMessageBox.information(self, "提示", "错误信息已复制到剪贴板")

    def export_log(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "导出错误报告", "crash_report.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_content)
                QMessageBox.information(self, "提示", "错误报告已导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python crash_reporter.py <main_pid>")
        sys.exit(1)

    main_pid = int(sys.argv[1])
    
    # Wait for the main process to exit
    try:
        main_process = psutil.Process(main_pid)
        main_process.wait()
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(f"Error monitoring process: {e}")

    # Check if crash.log exists and has content
    crash_log_path = os.path.join(_app_dir(), "crash.log")
    if os.path.exists(crash_log_path):
        with open(crash_log_path, 'r', encoding='utf-8') as f:
            log_content = f.read().strip()
            
        if log_content:
            app = QApplication(sys.argv)
            dialog = CrashReporterDialog(log_content)
            dialog.exec()
            
        # Clean up the log file after showing or if empty
        try:
            os.remove(crash_log_path)
        except:
            pass

if __name__ == "__main__":
    main()
