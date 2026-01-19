# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Список файлів/папок для додавання: (звідки, куди)
added_files = [
    ('bin/ffmpeg.exe', 'bin'),
]

a = Analysis(
    ['main.py'],  # Вкажіть ім'я вашого головного скрипта
    pathex=[],
    binaries=[],
    datas=added_files,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoTrimmer',  # Назва вашого .exe файлу
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Вимикає консоль (чорне вікно)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)