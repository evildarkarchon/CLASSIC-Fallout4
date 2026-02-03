# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 GUI application.

This spec file bundles the main GUI application with all required data files
including YAML configurations, databases, and graphics resources.
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
])

# Add found Rust modules to hidden imports
hiddenimports.extend(rust_hidden_imports)

# Collect PySide6 dependencies
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
datas += pyside6_datas
binaries += pyside6_binaries
hiddenimports += pyside6_hiddenimports

# Add textual for TUI support (even though this is GUI, some shared modules use it)
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
datas += textual_datas
binaries += textual_binaries
hiddenimports += textual_hiddenimports

# Additional hidden imports for common dependencies
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
    pathex=[str(PROJECT_ROOT)],  # Add project root to path
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Exclude if not needed for GUI
        'numpy',  # Exclude heavy scientific packages if not used
        'pandas',  # Exclude unless specifically needed
        'scipy',
        'scikit-learn',
        'PIL',  # Unless you need image processing
        'cv2',  # OpenCV not needed
        'test',
        'tests',
        'pytest',
        '_pytest',
    ],
    noarchive=False,
    optimize=2,  # Optimization level (0, 1, or 2)
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],  # Remove duplicate OPTION entries
    exclude_binaries=True,
    name='CLASSIC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "CLASSIC Data" / "graphics" / "CLASSIC.ico")
    if (PROJECT_ROOT / "CLASSIC Data" / "graphics" / "CLASSIC.ico").exists()
    else None,
    version_file=None,  # Add version info if needed
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    name='CLASSIC',
)
