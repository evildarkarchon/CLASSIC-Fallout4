# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 QML GUI (Single File Version)

This creates a single executable file that includes all dependencies and data.
The exe extracts to a temporary directory when run.

Build with:
    uv run pyinstaller --clean CLASSIC-QML.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Project paths - use SPECPATH provided by PyInstaller
PROJECT_ROOT = Path(SPECPATH).resolve()

# Add project root to sys.path so we can import the helper
import sys
sys.path.insert(0, str(PROJECT_ROOT))

# NOTE: CLASSIC Data is NOT bundled in the executable
# The distribution zip includes CLASSIC Data folder alongside the executable
# This keeps the executable smaller and allows easy updates to data files
print("INFO: CLASSIC Data will NOT be bundled (provided in distribution zip)")

# Bundle Rust extensions - checks local build directory first, then site-packages
from pyinstaller_rust_helper import find_rust_extensions

binaries, datas, rust_found = find_rust_extensions(PROJECT_ROOT)

# Add QML files to datas
# Bundle the entire 'qml' directory into 'qml' inside the bundle
datas.append(('qml', 'qml'))

# Collect all PySide6 components (required for GUI)
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

# Hidden imports for various components
hiddenimports = [
    # Core modules
    "ClassicLib",
    "ClassicLib.ResourceLoader",
    "ClassicLib.rust_loader",
    "ClassicLib.MessageHandler",
    "ClassicLib.GlobalRegistry",
    "ClassicLib.FileIO",
    "ClassicLib.YamlSettingsCache",
    "ClassicLib.AsyncBridge",

    # Rust integration
    "ClassicLib.integration",
    "ClassicLib.integration.factory",
    "ClassicLib.integration.config",
    "ClassicLib.integration.status",
    "ClassicLib.integration.detector",
    # All Rust Python modules (.pyd files from separated architecture)
    "classic_shared",      # Foundation
    "classic_config",      # YamlData configuration
    "classic_database",    # SQLite operations
    "classic_file_io",     # File I/O + DDS parsing
    "classic_message",     # Message handling
    "classic_path",        # Path management
    "classic_perf",        # Performance monitoring
    "classic_pybridge",    # Async Python bridge
    "classic_registry",    # Windows registry operations
    "classic_scangame",    # Game scanning + validation
    "classic_scanlog",     # Log parsing + analysis
    "classic_settings",    # Settings cache management
    "classic_yaml",        # YAML operations
    "classic_constants",   # Game constants
    "classic_version",     # Version parsing
    "classic_resource",    # Resource detection
    "classic_xse",         # XSE utilities
    "classic_web",         # Web utilities
    "classic_update",      # Auto-update

    # GUI specific
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",

    # Standard library
    "encodings",
    "importlib.metadata",
    "importlib.resources",

    # Third-party
    "aiohttp",
    "aiofiles",
    "aiosqlite",
    "appdirs",
    "beautifulsoup4",
    "bs4",
    "chardet",
    "markdown2",
    "packaging",
    "pefile",
    "regex",
    "requests",
    "ruamel.yaml",
    "setuptools",
    "tomlkit",
    "urllib3",
    "qasync",

    # Windows specific
    "win32api",
    "win32con",
    "win32gui",
    "pywintypes",
] + pyside6_hiddenimports

# Data files to bundle (combine with already created datas list)
datas += pyside6_datas

# Binary files (combine with already created binaries list)
binaries += pyside6_binaries

# Analysis configuration
a = Analysis(
    ["CLASSIC_Interface_QML.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy", "PIL", "tkinter", "test", "unittest", "xml", "pydoc", "doctest", "pytest", "IPython", "jupyter", "textual", "rich",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# Create single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CLASSIC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt" if Path("version_info.txt").exists() else None,
    icon=str(PROJECT_ROOT / "CLASSIC Data/graphics/CLASSIC.ico")
)

print("\n" + "=" * 60)
print("Building CLASSIC QML GUI (Single File)")
print("=" * 60)
print(f"Project Root: {PROJECT_ROOT}")
print(f"Output: dist/CLASSIC.exe")
print("Note: CLASSIC Data must be provided in distribution zip")
print("=" * 60 + "\n")
