# -*- mode: python ; coding: utf-8 -*-
# AutoDBAudit PyInstaller Spec File
# Build command: pyinstaller packaging/autodbaudit.spec

block_cipher = None

# Use absolute paths computed at spec-parse time
# Note: SPECPATH in PyInstaller is the directory containing the spec file
import os

# SPECPATH is already the packaging directory - parent is project root
project_root = os.path.dirname(SPECPATH)
src_path = os.path.join(project_root, 'src')
assets_path = os.path.join(project_root, 'assets')
icon_file = os.path.join(assets_path, 'sql_audit_icon.ico')

# Debug print to verify paths during build
print(f"[SPEC] Project Root: {project_root}")
print(f"[SPEC] Source Path: {src_path}")
print(f"[SPEC] Icon File: {icon_file}")
print(f"[SPEC] Icon Exists: {os.path.exists(icon_file)}")

# Fallback if ico doesn't exist, try png
if not os.path.exists(icon_file):
    icon_file = os.path.join(assets_path, 'sql_audit_icon.png')
    print(f"[SPEC] Using PNG fallback: {icon_file}")

a = Analysis(
    [os.path.join(src_path, 'main.py')],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=[
        'rich.console',
        'rich.panel', 
        'rich.table',
        'rich.text',
        'rich.box',
        'rich.markup',
    ],
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
