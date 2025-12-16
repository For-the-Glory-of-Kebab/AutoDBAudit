# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
import os

SPECPATH = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = os.path.dirname(SPECPATH)
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')

block_cipher = None

# Hidden imports to ensure all dependencies are caught
hidden_imports = [
    'pyodbc',
    'pkg_resources',
    'autodbaudit',
    'autodbaudit.infrastructure.sqlite.schema',
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[SRC_PATH],
    binaries=[],
    datas=[
        # Embed example configs as defaults if needed (though we ship them externally usually)
        # Snytax: (Source, Dest in MEIPASS)
        (os.path.join(PROJECT_ROOT, 'config', '*.example.json'), 'config'),
        (os.path.join(PROJECT_ROOT, 'assets'), 'assets'),
    ],
    hiddenimports=hidden_imports,
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
    name='AutoDBAudit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements=None,
    icon='..\\assets\\sql_audit_icon.png'
)
