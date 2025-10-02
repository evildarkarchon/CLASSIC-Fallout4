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
