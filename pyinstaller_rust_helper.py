"""Helper functions for PyInstaller spec files to locate and bundle Rust extensions.

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
...and so on.

Note: Only the *-py crates produce .pyd files. The *-core crates are rlib only
and provide pure Rust business logic that can be used by CLI/TUI applications.
Python imports these modules directly (e.g., import classic_yaml) for transparent
Rust acceleration.

Performance: These Rust extensions provide 10-150x speedups.
"""

import site
from pathlib import Path


def _process_module_file(
    pyd_path: Path,
    binaries: list,
    datas: list,
) -> str:
    """Process a single .pyd file and its associated artifacts.

    Args:
        pyd_path: Path to the .pyd file
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        Module name (import name)

    """
    module_name = pyd_path.stem
    # The destination path is relative to the bundle root. By specifying the
    # filename, we place the .pyd file in the root, making it importable.
    binaries.append((str(pyd_path), pyd_path.name))
    print(f"  - {module_name}: {pyd_path.name} -> ./{pyd_path.name}")

    parent = pyd_path.parent

    # NOTE: The logic for handling __init__.py files has been removed.
    # The original implementation created a directory with the same name as the
    # binary, causing a file/directory conflict during the PyInstaller build.
    # The .pyd files are self-contained modules and should not require this.

    # Check for .pyi stub files and bundle them in the root alongside the .pyd
    pyi_file = parent / f"{module_name}.pyi"
    if pyi_file.exists():
        datas.append((str(pyi_file), pyi_file.name))
        print(f"    (stub): {pyi_file.name} -> ./{pyi_file.name}")

    return module_name


def _try_local_rust_dir(
    project_root: Path,
    binaries: list,
    datas: list,
) -> list[str]:
    """Try to find Rust extensions in the local rust_extensions directory.
    Scans for ANY .pyd file in the directory.

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

    modules_found = []
    pyd_files = list(local_rust_dir.glob("*.pyd"))

    for pyd_file in pyd_files:
        module_name = _process_module_file(pyd_file, binaries, datas)
        modules_found.append(module_name)

    # Add MANIFEST.txt if it exists
    manifest_file = local_rust_dir / "MANIFEST.txt"
    if manifest_file.exists():
        datas.append((str(manifest_file), "."))

    if modules_found:
        print(f"  Total modules bundled: {len(modules_found)}")

    return modules_found


def _try_site_packages(
    binaries: list,
    datas: list,
) -> list[str]:
    """Try to find Rust extensions in site-packages.
    Scans for classic_*.pyd files.

    Args:
        binaries: List to append binary tuples to
        datas: List to append data file tuples to

    Returns:
        List of module names that were found and processed

    """
    site_packages = Path(site.getsitepackages()[0])
    print(f"✓ Checking site-packages: {site_packages}")

    modules_found = []

    # Strategy 1: Look for classic_*.pyd directly in site-packages (top-level modules)
    pyd_files = list(site_packages.glob("classic_*.pyd"))

    # Strategy 2: Look for classic_* directories containing .pyd files
    # (This catches packages that are directories)
    for pkg_dir in site_packages.glob("classic_*"):
        if pkg_dir.is_dir():
            # If it's a directory, look for .pyd files inside, but usually
            # PyO3 modules are either single .pyd or .pyd inside a package.
            # If the package name matches the module name, we might find it.
            # But for now, let's stick to top-level .pyd or standard package structure.

            # If it is a python package, it might have an __init__.py
            # and maybe a .pyd file with the same name or _classic_something.
            pass

    # Process found .pyd files
    for pyd_file in pyd_files:
        # Exclude classic_ tools if they aren't the extension modules
        # But usually classic_* pyd files ARE the extensions.

        module_name = pyd_file.stem
        binaries.append((str(pyd_file), module_name))
        print(f"  - {module_name}: {pyd_file.name}")
        modules_found.append(module_name)

        # Check for .pyi in site-packages (usually next to .pyd)
        pyi_file = pyd_file.with_suffix(".pyi")
        if pyi_file.exists():
            datas.append((str(pyi_file), module_name))

    if modules_found:
        print(f"  Total modules bundled from site-packages: {len(modules_found)}")
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
    print("    .\build_all.ps1")
    print("  Or for development:")
    print("    .\rebuild_rust.ps1")


def find_rust_extensions(project_root: Path) -> tuple[list, list, list, bool]:
    """Find Rust extensions for bundling in PyInstaller.

    Checks in order:
    1. Local rust_extensions/ directory (created by build_all.ps1/bat - flattened structure)
       - All .pyd files extracted directly to rust_extensions/
    2. Site-packages (installed via pip/uv) - looks for classic_*.pyd

    Args:
        project_root: Path to the project root directory (from SPECPATH)

    Returns:
        Tuple of (binaries, datas, hidden_imports, found):
        - binaries: List of (source, dest) tuples for .pyd files
        - datas: List of (source, dest) tuples for __init__.py and other data
        - hidden_imports: List of module names to be added to hiddenimports
        - found: Boolean indicating if Rust extensions were found

    """
    binaries: list[tuple[str, str]] = []
    datas: list[tuple[str, str]] = []

    # Try local directory first
    modules_found = _try_local_rust_dir(project_root, binaries, datas)
    if modules_found:
        return binaries, datas, modules_found, True

    # Fall back to site-packages
    modules_found = _try_site_packages(binaries, datas)
    if modules_found:
        return binaries, datas, modules_found, True

    # No Rust extensions found
    _print_not_found_warning(project_root)
    return binaries, datas, [], False
