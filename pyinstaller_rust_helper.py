"""
Helper functions for PyInstaller spec files to locate and bundle Rust extensions.

This module provides a common way for all spec files to find Rust extensions,
checking the local build directory first before falling back to site-packages.
"""

from pathlib import Path
import site


def find_rust_extensions(project_root: Path) -> tuple[list, list, bool]:
    """
    Find Rust extensions for bundling in PyInstaller.

    Checks in order:
    1. Local classic_core/ directory (created by build_all.bat)
    2. Site-packages classic_core/ (installed via pip)

    Args:
        project_root: Path to the project root directory (from SPECPATH)

    Returns:
        Tuple of (binaries, datas, found):
        - binaries: List of (source, dest) tuples for .pyd files
        - datas: List of (source, dest) tuples for __init__.py
        - found: Boolean indicating if Rust extensions were found
    """
    binaries = []
    datas = []

    # Check local directory first (from build_all.bat)
    local_rust_dir = project_root / "classic_core"
    if local_rust_dir.exists() and list(local_rust_dir.glob("*.pyd")):
        print(f"✓ Found Rust extensions in local build directory: {local_rust_dir}")

        # Add all .pyd files
        for pyd_file in local_rust_dir.glob("*.pyd"):
            binaries.append((str(pyd_file), "classic_core"))
            print(f"  - Adding extension: {pyd_file.name}")

        # Add __init__.py
        init_file = local_rust_dir / "__init__.py"
        if init_file.exists():
            datas.append((str(init_file), "classic_core"))

        # Add MANIFEST.txt if it exists
        manifest_file = local_rust_dir / "MANIFEST.txt"
        if manifest_file.exists():
            datas.append((str(manifest_file), "classic_core"))

        return binaries, datas, True

    # Fall back to site-packages
    site_packages = Path(site.getsitepackages()[0])
    site_rust_dir = site_packages / "classic_core"

    if site_rust_dir.exists() and list(site_rust_dir.glob("*.pyd")):
        print(f"✓ Found Rust extensions in site-packages: {site_rust_dir}")
        print("  Note: Using installed version. Run build_all.bat to use local build.")

        # Add all .pyd files
        for pyd_file in site_rust_dir.glob("*.pyd"):
            binaries.append((str(pyd_file), "classic_core"))
            print(f"  - Adding extension: {pyd_file.name}")

        # Add __init__.py
        init_file = site_rust_dir / "__init__.py"
        if init_file.exists():
            datas.append((str(init_file), "classic_core"))

        return binaries, datas, True

    # No Rust extensions found
    print("⚠ WARNING: Rust extensions not found!")
    print("  Checked:")
    print(f"    - Local build: {local_rust_dir}")
    print(f"    - Site-packages: {site_rust_dir}")
    print("  The executable will work but without Rust performance optimizations.")
    print("  To build Rust extensions, run:")
    print("    1. cd classic-rust")
    print("    2. maturin build --release --out ../dist-rust")
    print("    3. cd ..")
    print("  Or run build_all.bat which handles this automatically.")

    return binaries, datas, False
