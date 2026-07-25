# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Shared Clipboard Service.

Build (run from the repo root, on the target OS — PyInstaller does not
cross-compile):

    pip install -e ".[build]"
    pyinstaller packaging/cbs.spec

Produces a single onefile executable under dist/.
"""
import os

block_cipher = None

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SharedClipboardService",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
