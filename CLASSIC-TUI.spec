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

# Initialize collections
datas = []
binaries = []
hiddenimports = []

# Bundle Rust extensions from site-packages
# Rust modules are installed via maturin build + pip install
import site
site_packages = Path(site.getsitepackages()[0])
rust_package_dir = site_packages / "classic_core"

if rust_package_dir.exists():
    print(f"Bundling Rust extensions from {rust_package_dir}")
    # Add the entire classic_core package
    for pyd_file in rust_package_dir.glob("*.pyd"):
        binaries.append((str(pyd_file), "classic_core"))
        print(f"  - Adding extension: {pyd_file.name}")

    # Add __init__.py
    init_file = rust_package_dir / "__init__.py"
    if init_file.exists():
        datas.append((str(init_file), "classic_core"))
else:
    print(f"WARNING: Rust extensions not found at {rust_package_dir}")
    print("The executable will work but without Rust performance optimizations!")
    print("Run: maturin build --release --out classic-rust/dist")
    print("Then: uv pip install classic-rust/dist/classic-*.whl --force-reinstall")

# Add Rust integration modules to hidden imports
hiddenimports.extend([
    "ClassicLib.rust_loader",
    "ClassicLib.integration",
    "ClassicLib.integration.factory",
    "ClassicLib.integration.config",
    "ClassicLib.integration.status",
    "ClassicLib.integration.detector",
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
    'pkg_resources',
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
    upx=True,
    upx_exclude=[
        '*.pyd',  # Python extension modules
        'python*.dll',  # Python DLL
    ],
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
