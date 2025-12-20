# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 Test/Debug build.

This spec file is for testing and debugging purposes with no optimization
and full debug information included.
"""

from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import os

# Get the project root directory
PROJECT_ROOT = Path(os.path.abspath(SPECPATH))

# Add project root to sys.path so we can import the helper
import sys
sys.path.insert(0, str(PROJECT_ROOT))

# Collect all PySide6 data and binaries for GUI support
datas = []
binaries = []
hiddenimports = []

# Bundle Rust extensions - checks local build directory first, then site-packages
from pyinstaller_rust_helper import find_rust_extensions

rust_binaries, rust_datas, rust_hidden_imports, rust_found = find_rust_extensions(PROJECT_ROOT)
binaries.extend(rust_binaries)
datas.extend(rust_datas)

# Add Rust integration modules to hidden imports
hiddenimports.extend([
    "ClassicLib.rust_loader",
    "ClassicLib.integration",
    "ClassicLib.integration.factory",
    "ClassicLib.integration.config",
    "ClassicLib.integration.status",
    "ClassicLib.integration.detector",
])

# Add found Rust modules to hidden imports
hiddenimports.extend(rust_hidden_imports)

# Collect PySide6 dependencies
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
datas += pyside6_datas
binaries += pyside6_binaries
hiddenimports += pyside6_hiddenimports

# Add textual for TUI support
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
datas += textual_datas
binaries += textual_binaries
hiddenimports += textual_hiddenimports

# Additional hidden imports
hiddenimports += [
    'aiosqlite',
    'aiofiles',
    'rich',
    'tqdm',
    'markdown',
    'appdirs',
    'yaml',
    'ruamel.yaml',
    'importlib.metadata',
    'importlib.resources',
]

# NOTE: CLASSIC Data is NOT bundled in the executable
# The distribution zip includes CLASSIC Data folder alongside the executable
# This keeps the executable smaller and allows easy updates to data files
# README.md and LICENSE are also provided in the distribution zip
print("INFO: CLASSIC Data will NOT be bundled (provided in distribution zip)")

a = Analysis(
    ['CLASSIC_Interface.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],  # Don't exclude anything for testing
    noarchive=False,
    optimize=0,  # No optimization for debugging
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CLASSIC-Test',
    debug=True,  # Enable debug mode for testing
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled for debugging and to avoid antivirus false positives
    runtime_tmpdir=None,
    console=True,  # Show console for debug output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "CLASSIC Data" / "graphics" / "CLASSIC.ico")
    if (PROJECT_ROOT / "CLASSIC Data" / "graphics" / "CLASSIC.ico").exists()
    else None,
)
