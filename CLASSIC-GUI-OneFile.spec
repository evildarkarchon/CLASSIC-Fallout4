# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CLASSIC-Fallout4 GUI (Single File Version)

This creates a single executable file that includes all dependencies and data.
The exe extracts to a temporary directory when run.

Build with:
    uv run pyinstaller --clean CLASSIC-GUI-OneFile.spec

Or with UPX compression:
    uv run pyinstaller --clean --upx-dir "C:\\Path\\to\\UPX" CLASSIC-GUI-OneFile.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Project paths
PROJECT_ROOT = Path(__file__).parent.resolve()
CLASSIC_DATA_PATH = PROJECT_ROOT / "CLASSIC Data"

# Verify data directory exists
if not CLASSIC_DATA_PATH.exists():
    print(f"Warning: CLASSIC Data directory not found at {CLASSIC_DATA_PATH}")
    print("Creating empty directory for build...")
    CLASSIC_DATA_PATH.mkdir(exist_ok=True)

# Bundle Rust extensions (NO pip installation required!)
# These are built locally and committed to the repo
rust_extensions_dir = PROJECT_ROOT / "rust_extensions"
binaries = []
datas = []

if rust_extensions_dir.exists():
    print(f"Bundling Rust extensions from {rust_extensions_dir}")
    # Add all .pyd and .dll files from rust_extensions to _internal
    for ext_file in rust_extensions_dir.glob("*.pyd"):
        binaries.append((str(ext_file), "_internal/rust_extensions"))
        print(f"  - Adding extension: {ext_file.name}")

    for dll_file in rust_extensions_dir.glob("*.dll"):
        # Skip Python DLLs as they're provided by the Python runtime
        if "python" not in dll_file.name.lower():
            binaries.append((str(dll_file), "_internal/rust_extensions"))
            print(f"  - Adding dependency: {dll_file.name}")

    # Also add the manifest file for debugging
    manifest_file = rust_extensions_dir / "MANIFEST.txt"
    if manifest_file.exists():
        datas.append((str(manifest_file), "_internal/rust_extensions"))
else:
    print(f"WARNING: Rust extensions not found at {rust_extensions_dir}")
    print("The executable will work but without Rust performance optimizations!")
    print("Run build_rust_local.bat first to build the extensions.")

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

    # GUI specific
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",

    # Standard library
    "encodings",
    "importlib.metadata",
    "pkg_resources",

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
datas += [
    # Bundle entire CLASSIC Data directory with all configs
    (CLASSIC_DATA_PATH, "CLASSIC Data"),

    # Include README and documentation
    (PROJECT_ROOT / "README.md", "."),
    (PROJECT_ROOT / "LICENSE", "."),
    (PROJECT_ROOT / "CLASSIC - Readme.pdf", "."),
] + pyside6_datas

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
    upx=True,  # Enable UPX compression
    upx_exclude=[
        # Don't compress these files as it may cause issues
        "vcruntime*.dll",
        "ucrtbase.dll",
        "api-ms-*.dll",
        "python*.dll",
        "Qt*.dll",
        "qwindows.dll",
        "qwindowsvistastyle.dll",
    ],
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
