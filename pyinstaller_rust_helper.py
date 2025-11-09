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
  - Depends on: classic-config-core (business logic)

Note: Only the *-py crates produce .pyd files. The *-core crates are rlib only
and provide pure Rust business logic that can be used by CLI/TUI applications.
Python imports these modules directly (e.g., import classic_yaml) for transparent
Rust acceleration.

Performance: These Rust extensions provide 10-150x speedups for:
- Log parsing (10x), FormID analysis (25x), Pattern matching (20x)
- File I/O (10x), DDS processing (40x), Record scanning (40x)
"""

import site
from pathlib import Path

# All Rust Python modules to bundle (.pyd files from *-py crates)
# These are the standalone Python extension modules that PyInstaller needs to include
RUST_MODULES = [
    # Foundation Layer
    "classic_shared",  # Foundation layer (runtime, errors, utilities)
    # Business Logic - Core Operations
    "classic_config",  # Configuration (from classic-config-py)
    "classic_database",  # SQLite operations (from classic-database-py)
    "classic_file_io",  # File I/O operations (from classic-file-io-py)
    "classic_message",  # Message handling (from classic-message-py)
    "classic_path",  # Path management (from classic-path-py) - NEW: 10-20x speedup
    "classic_perf",  # Performance monitoring (from classic-perf-py)
    "classic_pybridge",  # Async Python bridge (from classic-pybridge-py)
    "classic_registry",  # Windows registry (from classic-registry-py)
    "classic_scangame",  # Game scanning (from classic-scangame-py)
    "classic_scanlog",  # Log parsing (from classic-scanlog-py)
    "classic_settings",  # Settings cache (from classic-settings-py)
    "classic_yaml",  # YAML operations (from classic-yaml-py)
    # Phase 4 - Constants and Utilities
    "classic_constants",  # Game constants (from classic-constants-py)
    "classic_version",  # Version parsing (from classic-version-py)
    "classic_resource",  # Resource detection (from classic-resource-py)
    "classic_xse",  # Script Extender (from classic-xse-py)
    "classic_web",  # Web utilities (from classic-web-py)
    # Phase 5 - Application Coordination
    "classic_update",  # Auto-update system (from classic-update-py)
]


def _process_local_module(
    module_name: str,
    local_rust_dir: Path,
    binaries: list,
    datas: list,
) -> bool:
    """
    Process a single module from the local rust_extensions directory.

    Args:
        module_name: Name of the Rust module to process
        local_rust_dir: Path to the rust_extensions directory
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        True if module was found and processed, False otherwise
    """
    pyd_file = local_rust_dir / f"{module_name}.pyd"
    if not pyd_file.exists():
        return False

    binaries.append((str(pyd_file), module_name))
    print(f"  - {module_name}: {pyd_file.name}")

    # Check for corresponding __init__.py (stored as {module_name}__init__.py)
    init_file = local_rust_dir / f"{module_name}__init__.py"
    if init_file.exists():
        datas.append((str(init_file), module_name))

    # Check for .pyi stub files
    pyi_file = local_rust_dir / f"{module_name}.pyi"
    if pyi_file.exists():
        datas.append((str(pyi_file), module_name))

    return True


def _process_sitepackages_module(
    module_name: str,
    site_packages: Path,
    binaries: list,
    datas: list,
) -> bool:
    """
    Process a single module from site-packages.

    Args:
        module_name: Name of the Rust module to process
        site_packages: Path to the site-packages directory
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        True if module was found and processed, False otherwise
    """
    module_dir = site_packages / module_name
    if not module_dir.exists():
        return False

    # Add all .pyd files
    pyd_files = list(module_dir.glob("*.pyd"))
    if not pyd_files:
        return False

    for pyd_file in pyd_files:
        binaries.append((str(pyd_file), module_name))
        print(f"  - {module_name}: {pyd_file.name}")

    # Add __init__.py if it exists
    init_file = module_dir / "__init__.py"
    if init_file.exists():
        datas.append((str(init_file), module_name))

    # Add .pyi stub files if they exist
    datas.extend((str(pyi_file), module_name) for pyi_file in module_dir.glob("*.pyi"))

    return True


def _try_local_rust_dir(
    project_root: Path,
    binaries: list,
    datas: list,
) -> list[str]:
    """
    Try to find Rust extensions in the local rust_extensions directory.

    Args:
        project_root: Path to the project root directory
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        List of module names that were found and processed
    """
    local_rust_dir = project_root / "rust_extensions"
    if not local_rust_dir.exists():
        return []

    print(f"✓ Found Rust extensions in local build directory (flattened): {local_rust_dir}")

    modules_found = [module_name for module_name in RUST_MODULES if _process_local_module(module_name, local_rust_dir, binaries, datas)]

    # Add MANIFEST.txt if it exists
    manifest_file = local_rust_dir / "MANIFEST.txt"
    if manifest_file.exists():
        datas.append((str(manifest_file), "."))

    if modules_found:
        print(f"  Total modules bundled: {len(modules_found)}/{len(RUST_MODULES)}")

    return modules_found


def _try_site_packages(
    binaries: list,
    datas: list,
) -> list[str]:
    """
    Try to find Rust extensions in site-packages.

    Args:
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        List of module names that were found and processed
    """
    site_packages = Path(site.getsitepackages()[0])
    print(f"✓ Checking site-packages: {site_packages}")

    modules_found = [
        module_name for module_name in RUST_MODULES if _process_sitepackages_module(module_name, site_packages, binaries, datas)
    ]

    if modules_found:
        print(f"  Total modules bundled from site-packages: {len(modules_found)}/{len(RUST_MODULES)}")
        print("  Note: Using installed versions. Run build_all.ps1 to use local builds.")

    return modules_found


def _print_not_found_warning(project_root: Path) -> None:
    """Print warning message when no Rust extensions are found."""
    local_rust_dir = project_root / "rust_extensions"
    site_packages = Path(site.getsitepackages()[0])

    print("⚠ WARNING: No Rust extensions found!")
    print("  Checked:")
    print(f"    - Local build: {local_rust_dir}")
    print(f"    - Site-packages: {site_packages}")
    print("  The executable will work but without Rust performance optimizations.")
    print("  To build Rust extensions, run:")
    print("    .\\build_all.ps1")
    print("  Or for development:")
    print("    .\\rebuild_rust.ps1")


def find_rust_extensions(project_root: Path) -> tuple[list, list, bool]:
    """
    Find Rust extensions for bundling in PyInstaller.

    Checks in order:
    1. Local rust_extensions/ directory (created by build_all.ps1/bat - flattened structure)
       - All .pyd files extracted directly to rust_extensions/ (no subdirectories)
       - Wheels are built to project_root/dist-rust/ before extraction
    2. Site-packages (installed via pip/uv)

    Args:
        project_root: Path to the project root directory (from SPECPATH)

    Returns:
        Tuple of (binaries, datas, found):
        - binaries: List of (source, dest) tuples for .pyd files
        - datas: List of (source, dest) tuples for __init__.py and other data
        - found: Boolean indicating if Rust extensions were found

    Note:
        build_all.ps1 and build_all.bat now output all wheels to a single
        dist-rust/ directory in the project root (not rust/python-bindings/dist-rust/
        or rust/foundation/dist-rust/) to ensure all modules are discovered.
    """
    binaries = []
    datas = []

    # Try local directory first
    modules_found = _try_local_rust_dir(project_root, binaries, datas)
    if modules_found:
        return binaries, datas, True

    # Fall back to site-packages
    modules_found = _try_site_packages(binaries, datas)
    if modules_found:
        return binaries, datas, True

    # No Rust extensions found
    _print_not_found_warning(project_root)
    return binaries, datas, False
