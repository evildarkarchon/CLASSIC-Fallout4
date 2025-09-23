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

# Collect all PySide6 data and binaries for GUI support
datas = []
binaries = []
hiddenimports = []

# Bundle Rust extensions (NO pip installation required!)
# These are built locally and committed to the repo
rust_extensions_dir = PROJECT_ROOT / "rust_extensions"
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

# Add the rust_loader module to hidden imports
hiddenimports.append("ClassicLib.rust_loader")

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
    'pkg_resources',
    'appdirs',
    'yaml',
    'ruamel.yaml',
    'importlib.metadata',
    'importlib.resources',
]

# Bundle CLASSIC Data directory with all its contents
classic_data_path = PROJECT_ROOT / "CLASSIC Data"
if classic_data_path.exists():
    # Add the entire CLASSIC Data directory tree
    datas.append((str(classic_data_path), "CLASSIC Data"))
else:
    print(f"WARNING: CLASSIC Data directory not found at {classic_data_path}")
    print("The test executable will not have bundled data files!")

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
    upx=False,  # Don't use UPX compression for debugging
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for debug output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'CLASSIC Data' / 'graphics' / 'CLASSIC.ico'),
)
