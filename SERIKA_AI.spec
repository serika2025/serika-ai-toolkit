# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SERIKA AI简易工具箱
Build command:
    pyinstaller "SERIKA AI.spec"

Output: dist/SERIKA AI简易工具箱/  —— 文件夹内为exe+dll，无需Python环境
"""
import sys
import os
from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[
        # Include ffmpeg binaries for audio conversion
        (str(root / 'ffmpeg_bin' / 'ffmpeg.exe'), 'ffmpeg_bin'),
        (str(root / 'ffmpeg_bin' / 'ffprobe.exe'), 'ffmpeg_bin'),
    ],
    datas=[
        (str(root / 'icon.ico'), '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'openai',
        'requests',
        'psutil',
        'pydub',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'config.config_manager',
        'config.model_manager',
        'gui.main_window',
        'gui.settings_window',
        'gui.model_settings_window',
        'gui.tabs.translation',
        'gui.tabs.audio_tab',
        'gui.tabs.expand_tab',
        'gui.tabs.polish_tab',
        'gui.tabs.placeholders',
        'gui.components.searchable_combo',
        'workers.ai_worker',
        'workers.audio_worker',
        'workers.expand_worker',
        'workers.polish_worker',
        'utils.prompts',
        'utils.theme',
        'utils.audio_converter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SERIKA_AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SERIKA AI简易工具箱',
)
