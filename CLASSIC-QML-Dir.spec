# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 QML GUI (Directory Version)

This creates a directory containing the executable and all dependencies.
The executable runs directly from this directory without extraction.

Build with:
    uv run pyinstaller --clean CLASSIC-QML-Dir.spec
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

binaries, datas, rust_hidden_imports, rust_found = find_rust_extensions(PROJECT_ROOT)

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
] + pyside6_hiddenimports + rust_hidden_imports

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

# Create executable (Directory mode: exclude binaries and data from EXE)
exe = EXE(
    pyz,
    a.scripts,
    [],  # No binaries or data in EXE for onedir
    exclude_binaries=True,
    name="CLASSIC-QML",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt" if Path("version_info.txt").exists() else None,
    icon=str(PROJECT_ROOT / "CLASSIC Data" / "graphics" / "CLASSIC.ico"),
)

# Collect everything into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CLASSIC-QML',
)

print("\n" + "=" * 60)
print("Building CLASSIC QML GUI (Directory)")
print("=" * 60)
print(f"Project Root: {PROJECT_ROOT}")
print(f"Output: dist/CLASSIC/")
print("Note: CLASSIC Data must be provided in distribution zip")
print("=" * 60 + "\n")
