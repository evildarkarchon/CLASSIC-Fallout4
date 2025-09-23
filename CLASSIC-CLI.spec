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

# Initialize collections
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
    'pkg_resources',
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
    upx=True,
    upx_exclude=[
        '*.pyd',  # Python extension modules
        'python*.dll',  # Python DLL
    ],
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
