# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 GUI (Single File Version)

This creates a single executable file that includes all dependencies and data.
The exe extracts to a temporary directory when run.

Build with:
    uv run pyinstaller --clean CLASSIC-GUI-OneFile.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Project paths - use SPECPATH provided by PyInstaller
PROJECT_ROOT = Path(SPECPATH).resolve()

# Add project root to sys.path so we can import the helper
import sys
sys.path.insert(0, str(PROJECT_ROOT))

CLASSIC_DATA_PATH = PROJECT_ROOT / "CLASSIC Data"

# Verify data directory exists
if not CLASSIC_DATA_PATH.exists():
    print(f"Warning: CLASSIC Data directory not found at {CLASSIC_DATA_PATH}")
    print("Creating empty directory for build...")
    CLASSIC_DATA_PATH.mkdir(exist_ok=True)

# Bundle Rust extensions - checks local build directory first, then site-packages
from pyinstaller_rust_helper import find_rust_extensions

binaries, datas, rust_found = find_rust_extensions(PROJECT_ROOT)

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
    "ClassicLib.FileIOCore",
    "ClassicLib.YamlSettingsCache",
    "ClassicLib.AsyncBridge",

    # Rust integration
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

    # GUI specific
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
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

    # Windows specific (optional)
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
    ["CLASSIC_Interface.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "tkinter",
        "test",
        "unittest",
        "xml",
        "pydoc",
        "doctest",
        "pytest",
        "IPython",
        "jupyter",
        # Exclude TUI components
        "textual",
        "rich",
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
    name="CLASSIC-GUI-OneFile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled to avoid antivirus false positives
    runtime_tmpdir=None,
    console=False,  # No console window for GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt" if Path("version_info.txt").exists() else None,
    icon=str(PROJECT_ROOT / "Resources" / "CLASSIC_Box.ico")
    if (PROJECT_ROOT / "Resources" / "CLASSIC_Box.ico").exists()
    else None,
)

# Print build info
print("\n" + "=" * 60)
print("Building CLASSIC GUI (Single File)")
print("=" * 60)
print(f"Project Root: {PROJECT_ROOT}")
print(f"Data Path: {CLASSIC_DATA_PATH}")
print(f"Data exists: {CLASSIC_DATA_PATH.exists()}")
print(f"Output: dist/CLASSIC-GUI-OneFile.exe")
print("=" * 60 + "\n")
