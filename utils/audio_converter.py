import os
import sys
import subprocess
import shutil
import zipfile
import urllib.request
import tempfile

from PyQt6.QtCore import QThread, pyqtSignal

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_ffmpeg_bin_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        candidates = [
            os.path.join(sys._MEIPASS, "ffmpeg_bin"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg_bin"),
        ]
    else:
        candidates = [
            os.path.join(_app_dir(), "ffmpeg_bin"),
            os.path.join(base, "ffmpeg_bin"),
        ]
    for d in candidates:
        if os.path.isdir(d):
            return d
    return None


def find_ffmpeg():
    bundled = get_ffmpeg_bin_dir()
    if bundled:
        exe = os.path.join(bundled, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.exists(exe):
            return exe, True
    for name in ("ffmpeg.exe", "ffmpeg"):
        path = shutil.which(name)
        if path:
            return path, False
    return None, False


def is_ffmpeg_available():
    path, _ = find_ffmpeg()
    if not path:
        return False
    try:
        subprocess.run([path, "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


class FfmpegDownloadWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(bool)  # True = success, False = failed/cancelled
    error = pyqtSignal(str)

    def run(self):
        if os.name != "nt":
            self.error.emit("当前系统不支持自动下载 ffmpeg，请手动安装。")
            self.finished.emit(False)
            return

        target_dir = os.path.join(_app_dir(), "ffmpeg_bin")
        os.makedirs(target_dir, exist_ok=True)

        try:
            self.status_changed.emit("下载 ffmpeg...")
            self.progress_changed.emit(5)

            zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg_temp.zip")
            
            # Download with progress callback
            def report(block_num, block_size, total_size):
                if total_size > 0:
                    pct = 5 + int(70 * (block_num * block_size) / total_size)
                    if pct > 75:
                        pct = 75
                    self.progress_changed.emit(pct)

            urllib.request.urlretrieve(FFMPEG_URL, zip_path, reporthook=report)

            self.status_changed.emit("解压 ffmpeg...")
            self.progress_changed.emit(80)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                bin_files = [n for n in zf.namelist()
                             if '/bin/' in n and os.path.splitext(n)[1] in ('.exe', '.dll')]
                total = len(bin_files)
                for i, name in enumerate(bin_files):
                    basename = os.path.basename(name)
                    with zf.open(name) as src:
                        with open(os.path.join(target_dir, basename), 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                    if total > 0:
                        self.progress_changed.emit(80 + int(15 * (i + 1) / total))

            os.remove(zip_path)

            ffmpeg_path = os.path.join(target_dir, "ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                self.progress_changed.emit(100)
                self.status_changed.emit("ffmpeg 就绪，正在重启...")
                self.finished.emit(True)
            else:
                raise RuntimeError("ffmpeg.exe not found in downloaded archive")
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)


def convert_to_mp3(input_path, output_path=None, progress_callback=None):
    """
    Convert an audio file to MP3.
    If output_path is not given, it is derived from input_path.
    If progress_callback(pct) is provided, it will be called with 10..25 as progress.
    Returns the path to the converted MP3 file.
    """
    ffmpeg_path, _ = find_ffmpeg()
    if ffmpeg_path:
        os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_path
        # Also set ffprobe for robust file reading
    else:
        from pydub import AudioSegment

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".mp3"

    if progress_callback:
        progress_callback(12)

    if input_path.lower().endswith(".mp3"):
        if os.path.abspath(input_path) != os.path.abspath(output_path):
            shutil.copy2(input_path, output_path)
        if progress_callback:
            progress_callback(25)
        return output_path

    audio = AudioSegment.from_file(input_path)
    if progress_callback:
        progress_callback(18)
    audio.export(output_path, format="mp3")
    if progress_callback:
        progress_callback(25)
    return output_path


def get_supported_formats():
    return "*.wav *.mp3 *.m4a *.ogg *.flac *.wma *.aac *.aiff *.webm"
