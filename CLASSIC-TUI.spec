# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 TUI (Terminal UI) application.

This spec file bundles the Terminal UI version with all required data files
and textual framework dependencies.
"""

from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import os

# Get the project root directory
PROJECT_ROOT = Path(os.path.abspath(SPECPATH))

# Add project root to sys.path so we can import the helper
import sys
sys.path.insert(0, str(PROJECT_ROOT))

# Initialize collections
datas = []
binaries = []
hiddenimports = []

# Bundle Rust extensions - checks local build directory first, then site-packages
from pyinstaller_rust_helper import find_rust_extensions

rust_binaries, rust_datas, rust_found = find_rust_extensions(PROJECT_ROOT)
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
    # All Rust Python modules
    "classic_shared",
    "classic_yaml",
    "classic_database",
    "classic_file_io",
    "classic_scanlog",
    "classic_config",
    "classic_core",
])

# Add textual for TUI support (primary framework for this version)
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
datas += textual_datas
binaries += textual_binaries
hiddenimports += textual_hiddenimports

# Add rich for enhanced terminal output
rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')
datas += rich_datas
binaries += rich_binaries
hiddenimports += rich_hiddenimports

# Additional hidden imports for TUI dependencies
hiddenimports += [
    'aiosqlite',
    'aiofiles',
    'tqdm',
    'markdown',
    'appdirs',
    'yaml',
    'ruamel.yaml',
    'importlib.metadata',
    'importlib.resources',
    'asyncio',
]

# Bundle CLASSIC Data directory with all its contents
classic_data_path = PROJECT_ROOT / "CLASSIC Data"
if classic_data_path.exists():
    # Add the entire CLASSIC Data directory tree
    datas.append((str(classic_data_path), "CLASSIC Data"))
else:
    print(f"WARNING: CLASSIC Data directory not found at {classic_data_path}")
    print("The TUI executable will not have bundled data files!")

# Add any additional data files
additional_files = [
    "README.md",
    "LICENSE",
]

for file in additional_files:
    file_path = PROJECT_ROOT / file
    if file_path.exists():
        datas.append((str(file_path), "."))

a = Analysis(
    ['CLASSIC_TUI.py'],
    pathex=[str(PROJECT_ROOT)],  # Add project root to path
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6',  # Exclude GUI frameworks
        'PyQt5',
        'PyQt6',
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'scikit-learn',
        'PIL',
        'cv2',
        'test',
        'tests',
        'pytest',
        '_pytest',
    ],
    noarchive=False,
    optimize=2,  # Optimization level
)

pyz = PYZ(a.pure)

# Single-file executable for TUI
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],  # No extra options
    name='CLASSIC-TUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    runtime_tmpdir=None,
    console=True,  # TUI application needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # TUI can have an icon for Windows Explorer
    icon=str(PROJECT_ROOT / 'CLASSIC Data' / 'graphics' / 'CLASSIC.ico'),
)
