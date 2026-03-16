# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=['C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python310\\Lib\\site-packages\\win32', 'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python310\\Lib\\site-packages\\win32\\lib'],
    binaries=[],
    datas=[('version.txt', '.'), ('config.ini', '.'), ('logo.ico', '.')],
    hiddenimports=['win32com', 'win32com.client', 'pythoncom', 'pywintypes', 'win32gui', 'win32api', 'win32process', 'win32event', 'win32con', 'win32gui_struct', 'win32clipboard', 'win32file', 'win32security', 'win32pipe', 'win32net', 'win32console', 'win32timezone', 'commctrl', 'winerror', 'winnt', 'six', '_socket', 'socket', 'select', 'selectors', 'subprocess', 'shutil', 'zipfile', 'tempfile', 'configparser', 'json', 'urllib', 'urllib.request', 'urllib.parse', 'urllib.error', 'http', 'http.client', 'email', 'ssl', '_ssl', 'platform', 'difflib', 'ctypes.wintypes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pywinauto', 'comtypes'],
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
    name='DoGiaKD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DoGiaKD',
)
