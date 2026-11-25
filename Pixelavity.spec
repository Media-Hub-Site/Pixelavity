# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

datas = [
    ('assets', 'assets'),
    ('web', 'web'),
]

binaries = []
hiddenimports = [
    'core',
    'core.watcher',
    'core.server',
    'app_qt',
]

tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
vc_dlls = [
    "msvcp140.dll", "msvcp140_1.dll",
    "vcruntime140.dll", "vcruntime140_1.dll",
]
for dll in vc_dlls:
    dll_path = os.path.join(sys32, dll)
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pygame', 'PySide6'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pixelavity',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Pixelavity',
)
