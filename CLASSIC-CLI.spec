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
    # Foundation Layer
    "classic_shared",      # Foundation (runtime, errors, utilities)
    # Business Logic - Core Operations
    "classic_config",      # YamlData configuration
    "classic_database",    # SQLite operations
    "classic_file_io",     # File I/O + DDS parsing
    "classic_message",     # Message handling
    "classic_path",        # Path management (10-20x speedup)
    "classic_perf",        # Performance monitoring
    "classic_pybridge",    # Async Python bridge
    "classic_registry",    # Windows registry operations
    "classic_scangame",    # Game scanning + validation
    "classic_scanlog",     # Log parsing + analysis
    "classic_settings",    # Settings cache management
    "classic_yaml",        # YAML operations (yaml-rust2)
    # Phase 4 - Constants and Utilities
    "classic_constants",   # Game constants and enumerations
    "classic_version",     # Version parsing and comparison
    "classic_resource",    # Resource file detection
    "classic_xse",         # Script Extender (XSE) utilities
    "classic_web",         # Web utilities and URL validation
    # Phase 5 - Application Coordination
    "classic_update",      # Auto-update system (GitHub + Nexus)
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

# NOTE: CLASSIC Data is NOT bundled in the executable
# The distribution zip includes CLASSIC Data folder alongside the executable
# This keeps the executable smaller and allows easy updates to data files
# README.md and LICENSE are also provided in the distribution zip
print("INFO: CLASSIC Data will NOT be bundled (provided in distribution zip)")

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
