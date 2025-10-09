"""
Helper functions for PyInstaller spec files to locate and bundle Rust extensions.

This module provides a common way for all spec files to find Rust extensions,
checking the local build directory first before falling back to site-packages.

Architecture Overview (as of 2025-10-08):
-----------------------------------------
The Rust workspace follows a separated architecture with business logic in *-core
crates (pure Rust, no PyO3) and Python bindings in *-py crates (thin PyO3 adapters).

Rust Crate Structure → Python Modules:
- classic-shared (foundation) → classic_shared.pyd
- classic-yaml-py (bindings) → classic_yaml.pyd
  - Depends on: classic-yaml-core (business logic)
- classic-database-py (bindings) → classic_database.pyd
  - Depends on: classic-database-core (business logic)
- classic-file-io-py (bindings) → classic_file_io.pyd
  - Depends on: classic-file-io-core (business logic)
- classic-scanlog-py (bindings) → classic_scanlog.pyd
  - Depends on: classic-scanlog-core (business logic)
- classic-config-py (bindings) → classic_config.pyd
  - Depends on: config-core (business logic)
- classic-core (facade) → classic_core.pyd
  - Re-exports Phase 1 components for Python

Note: Only the *-py crates produce .pyd files. The *-core crates are rlib only
and provide pure Rust business logic that can be used by CLI/TUI applications.

Performance: These Rust extensions provide 10-150x speedups for:
- Log parsing (10x), FormID analysis (25x), Pattern matching (20x)
- File I/O (10x), DDS processing (40x), Record scanning (40x)
"""

from pathlib import Path
import site


# All Rust Python modules to bundle (.pyd files from *-py crates)
# These are the standalone Python extension modules that PyInstaller needs to include
RUST_MODULES = [
    "classic_shared",      # Foundation layer (runtime, errors, utilities)
    "classic_yaml",        # YAML operations (from classic-yaml-py)
    "classic_database",    # SQLite operations (from classic-database-py)
    "classic_file_io",     # File I/O operations (from classic-file-io-py)
    "classic_scanlog",     # Log parsing (from classic-scanlog-py)
    "classic_config",      # Configuration (from classic-config-py)
    "classic_core"         # Facade re-exporting Phase 1 components
]


def find_rust_extensions(project_root: Path) -> tuple[list, list, bool]:
    """
    Find Rust extensions for bundling in PyInstaller.

    Checks in order:
    1. Local rust_extensions/ directory (created by build_all.ps1)
    2. Site-packages (installed via pip/uv)

    Args:
        project_root: Path to the project root directory (from SPECPATH)

    Returns:
        Tuple of (binaries, datas, found):
        - binaries: List of (source, dest) tuples for .pyd files
        - datas: List of (source, dest) tuples for __init__.py and other data
        - found: Boolean indicating if Rust extensions were found
    """
    binaries = []
    datas = []
    modules_found = []

    # Check local directory first (from build_all.ps1)
    local_rust_dir = project_root / "rust_extensions"
    if local_rust_dir.exists():
        print(f"✓ Found Rust extensions in local build directory: {local_rust_dir}")

        for module_name in RUST_MODULES:
            module_dir = local_rust_dir / module_name
            if module_dir.exists():
                # Add all .pyd files
                pyd_files = list(module_dir.glob("*.pyd"))
                if pyd_files:
                    modules_found.append(module_name)
                    for pyd_file in pyd_files:
                        binaries.append((str(pyd_file), module_name))
                        print(f"  - {module_name}: {pyd_file.name}")

                # Add __init__.py if it exists
                init_file = module_dir / "__init__.py"
                if init_file.exists():
                    datas.append((str(init_file), module_name))

                # Add .pyi stub files if they exist
                for pyi_file in module_dir.glob("*.pyi"):
                    datas.append((str(pyi_file), module_name))

        # Add MANIFEST.txt if it exists
        manifest_file = local_rust_dir / "MANIFEST.txt"
        if manifest_file.exists():
            datas.append((str(manifest_file), "."))

        if modules_found:
            print(f"  Total modules bundled: {len(modules_found)}/{len(RUST_MODULES)}")
            return binaries, datas, True

    # Fall back to site-packages
    site_packages = Path(site.getsitepackages()[0])
    print(f"✓ Checking site-packages: {site_packages}")

    for module_name in RUST_MODULES:
        module_dir = site_packages / module_name
        if module_dir.exists():
            # Add all .pyd files
            pyd_files = list(module_dir.glob("*.pyd"))
            if pyd_files:
                modules_found.append(module_name)
                for pyd_file in pyd_files:
                    binaries.append((str(pyd_file), module_name))
                    print(f"  - {module_name}: {pyd_file.name}")

            # Add __init__.py if it exists
            init_file = module_dir / "__init__.py"
            if init_file.exists():
                datas.append((str(init_file), module_name))

            # Add .pyi stub files if they exist
            for pyi_file in module_dir.glob("*.pyi"):
                datas.append((str(pyi_file), module_name))

    if modules_found:
        print(f"  Total modules bundled from site-packages: {len(modules_found)}/{len(RUST_MODULES)}")
        print("  Note: Using installed versions. Run build_all.ps1 to use local builds.")
        return binaries, datas, True

    # No Rust extensions found
    print("⚠ WARNING: No Rust extensions found!")
    print("  Checked:")
    print(f"    - Local build: {local_rust_dir}")
    print(f"    - Site-packages: {site_packages}")
    print("  The executable will work but without Rust performance optimizations.")
    print("  To build Rust extensions, run:")
    print("    .\\build_all.ps1")
    print("  Or for development:")
    print("    .\\rebuild_rust.ps1")

    return binaries, datas, False
