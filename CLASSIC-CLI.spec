# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 CLI application.

This spec file bundles the command-line interface version with all required
data files but excludes GUI dependencies for a smaller executable.
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
    # All Rust Python modules (.pyd files from separated architecture)
    # Architecture: *-core crates (pure Rust business logic) + *-py crates (PyO3 bindings)
    "classic_shared",      # Foundation (runtime, errors, utilities)
    "classic_yaml",        # From classic-yaml-py (bindings for yaml-rust2 operations)
    "classic_database",    # From classic-database-py (bindings for SQLite operations)
    "classic_file_io",     # From classic-file-io-py (bindings for file I/O + DDS parsing)
    "classic_scanlog",     # From classic-scanlog-py (bindings for log parsing + analysis)
    "classic_config",      # From classic-config-py (bindings for YamlData configuration)
    "classic_core",        # Facade re-exporting Phase 1 components
])

# Add textual for TUI support (CLI may use some TUI components)
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
datas += textual_datas
binaries += textual_binaries
hiddenimports += textual_hiddenimports

# Add rich for better console output
rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')
datas += rich_datas
binaries += rich_binaries
hiddenimports += rich_hiddenimports

# Additional hidden imports for CLI dependencies
hiddenimports += [
    'aiosqlite',
    'aiofiles',
    'tqdm',
    'appdirs',
    'yaml',
    'ruamel.yaml',
    'importlib.metadata',
    'importlib.resources',
]

# Bundle CLASSIC Data directory with all its contents
# This is essential for both GUI and CLI versions
classic_data_path = PROJECT_ROOT / "CLASSIC Data"
if classic_data_path.exists():
    # Add the entire CLASSIC Data directory tree
    datas.append((str(classic_data_path), "CLASSIC Data"))
else:
    print(f"WARNING: CLASSIC Data directory not found at {classic_data_path}")
    print("The CLI executable will not have bundled data files!")

# Add any additional data files that might be needed
additional_files = [
    "README.md",
    "LICENSE",
]

for file in additional_files:
    file_path = PROJECT_ROOT / file
    if file_path.exists():
        datas.append((str(file_path), "."))

a = Analysis(
    ['CLASSIC_ScanLogs.py'],
    pathex=[str(PROJECT_ROOT)],  # Add project root to path
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6',  # Exclude GUI framework for CLI version
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

# Single-file executable for CLI (more convenient for command-line usage)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],  # No extra options
    name='CLASSIC-CLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    runtime_tmpdir=None,
    console=True,  # CLI application needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # CLI doesn't need an icon, but we can add one if desired
    # icon=str(PROJECT_ROOT / 'CLASSIC Data' / 'graphics' / 'CLASSIC.ico'),
)
