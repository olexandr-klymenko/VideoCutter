# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None
project_root = os.path.abspath(os.getcwd())

# Читаємо версію, щоб визначити, чи це бета
version_file = os.path.join(project_root, 'version.txt')
try:
    with open(version_file, 'r') as f:
        version_str = f.read().strip()
except:
    version_str = "1.0.0"

# Визначаємо назву папки на основі версії
is_beta = 'beta' in version_str.lower()
app_output_name = 'ProVideoTrimmer Beta' if is_beta else 'ProVideoTrimmer'

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('bin/ffmpeg.exe', 'bin'),
        ('version.txt', '.'),
        ('icon.ico', '.'),
        ('locales/*.json', 'locales'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProVideoTrimmer', # Назва самого .exe файлу (краще лишити без змін)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProVideoTrimmer', # Завжди одна назва для PyInstaller
)