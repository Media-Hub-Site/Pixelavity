# -*- mode: python ; coding: utf-8 -*-
import os

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
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

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
    excludes=[
        'tkinter', 'matplotlib', 'pygame', 'PySide6', 'PIL', 'numpy',
        'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebChannel',
        'PyQt6.QtQuick', 'PyQt6.QtQml', 'PyQt6.QtMultimedia', 'PyQt6.QtPdf',
        'PyQt6.Qt3DCore', 'PyQt6.QtDesigner', 'PyQt6.QtSql', 'PyQt6.QtBluetooth',
        'PyQt6.QtNfc', 'PyQt6.QtPositioning', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
        'PyQt6.QtTest', 'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'PyQt6.QtSvg',
        'PyQt6.QtNetwork', 'PyQt6.QtPrintSupport', 'PyQt6.QtHelp', 'PyQt6.QtXml',
    ],
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
