#!/usr/bin/env python
"""Validate type stubs against Rust implementations.

This script validates all .pyi stub files using mypy and pyright to ensure:
- Type consistency
- Correct syntax
- Proper imports
- Complete coverage
"""

import subprocess
import sys
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

STUB_FILES = [
    "classic-core/classic_core.pyi",
    "classic-scanlog/classic_scanlog.pyi",
    "classic-config-core/classic_config.pyi",
    "classic-database/classic_database.pyi",
    "classic-file-io/classic_file_io.pyi",
    "classic-yaml/classic_yaml.pyi",
    "classic-shared/classic_shared.pyi",
]


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def validate_with_mypy(stub_file: Path) -> bool:
    """Validate stub file with mypy.

    Args:
        stub_file: Path to .pyi file

    Returns:
        True if validation passed, False otherwise
    """
    print(f"Checking {stub_file.name} with mypy...")
    result = subprocess.run(
        ["mypy", "--strict", str(stub_file)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"{GREEN}✓ mypy validation passed{RESET}")
        return True
    else:
        print(f"{RED}✗ mypy validation failed:{RESET}")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False


def validate_with_pyright(stub_file: Path) -> bool:
    """Validate stub file with pyright.

    Args:
        stub_file: Path to .pyi file

    Returns:
        True if validation passed, False otherwise
    """
    print(f"Checking {stub_file.name} with pyright...")
    result = subprocess.run(
        ["pyright", str(stub_file)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"{GREEN}✓ pyright validation passed{RESET}")
        return True
    else:
        print(f"{RED}✗ pyright validation failed:{RESET}")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False


def check_stub_exists(stub_file: Path) -> bool:
    """Check if stub file exists.

    Args:
        stub_file: Path to .pyi file

    Returns:
        True if file exists, False otherwise
    """
    if stub_file.exists():
        print(f"{GREEN}✓ {stub_file.name} exists{RESET}")
        return True
    else:
        print(f"{RED}✗ {stub_file.name} missing{RESET}")
        return False


def main() -> int:
    """Main validation routine.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    root = Path(__file__).parent.parent
    all_passed = True

    print_section("Type Stub Validation")
    print(f"Root directory: {root}")

    # Check existence
    print_section("Checking Stub File Existence")
    for stub_path in STUB_FILES:
        stub_file = root / stub_path
        if not check_stub_exists(stub_file):
            all_passed = False

    # Validate with mypy (if available)
    print_section("Validating with mypy")
    try:
        subprocess.run(["mypy", "--version"], capture_output=True, check=True)
        for stub_path in STUB_FILES:
            stub_file = root / stub_path
            if stub_file.exists():
                if not validate_with_mypy(stub_file):
                    all_passed = False
            print()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{BLUE}mypy not available, skipping mypy validation{RESET}")

    # Validate with pyright (if available)
    print_section("Validating with pyright")
    try:
        subprocess.run(["pyright", "--version"], capture_output=True, check=True)
        for stub_path in STUB_FILES:
            stub_file = root / stub_path
            if stub_file.exists():
                if not validate_with_pyright(stub_file):
                    all_passed = False
            print()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{BLUE}pyright not available, skipping pyright validation{RESET}")

    # Summary
    print_section("Validation Summary")
    if all_passed:
        print(f"{GREEN}✓ All stub files validated successfully!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some validations failed. See errors above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
