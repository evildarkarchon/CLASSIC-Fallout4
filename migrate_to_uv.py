#!/usr/bin/env python
"""CLASSIC-Fallout4 Poetry to uv Migration Script.

This script automates the migration from Poetry to uv package manager.
Run this script to transition your development environment to use uv.
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


class Colors:
    """Terminal color codes for pretty output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
    print(f"  {message}")
    print(f"{'=' * 60}{Colors.ENDC}\n")


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  {message}")


def run_command(command: list[str], check: bool = True) -> tuple[bool, str]:
    """Run a shell command and return success status and output.

    Args:
        command: Command and arguments as list
        check: Whether to raise exception on failure

    Returns:
        Tuple of (success, output)

    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=check)
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, f"Command not found: {command[0]}"
    else:
        return True, result.stdout


def check_uv_installed() -> bool:
    """Check if uv is already installed."""
    success, _ = run_command(["uv", "--version"], check=False)
    return success


def install_uv() -> bool:
    """Install uv using the appropriate method for the platform."""
    print_header("Installing uv Package Manager")

    if check_uv_installed():
        print_success("uv is already installed")
        return True

    system = platform.system()

    if system == "Windows":
        print_info("Installing uv for Windows...")
        # Try PowerShell installer first
        ps_command = ["powershell", "-ExecutionPolicy", "ByPass", "-c", "irm https://astral.sh/uv/install.ps1 | iex"]
        success, _ = run_command(ps_command, check=False)

        if not success:
            # Fallback to pip
            print_warning("PowerShell installation failed, trying pip...")
            success, _ = run_command([sys.executable, "-m", "pip", "install", "uv"])

    else:  # macOS/Linux
        print_info("Installing uv for Unix-like system...")
        # Try curl installer first
        curl_command = ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
        success, _ = run_command(curl_command, check=False)

        if not success:
            # Fallback to pip
            print_warning("curl installation failed, trying pip...")
            success, _ = run_command([sys.executable, "-m", "pip", "install", "uv"])

    if check_uv_installed():
        print_success("uv installed successfully")
        return True
    print_error("Failed to install uv. Please install manually from: https://docs.astral.sh/uv/")
    return False


def check_poetry_environment() -> tuple[bool, Path | None]:
    """Check if Poetry environment exists and return its path."""
    # Check for .venv in project root
    venv_path = Path(".venv")
    if venv_path.exists():
        return True, venv_path

    # Check for poetry.lock
    if Path("poetry.lock").exists():
        return True, None

    return False, None


def backup_poetry_environment() -> bool:
    """Create a backup of the Poetry environment if it exists."""
    print_header("Backing Up Existing Environment")

    has_poetry, venv_path = check_poetry_environment()

    if not has_poetry:
        print_info("No Poetry environment found, skipping backup")
        return True

    # Backup poetry.lock
    if Path("poetry.lock").exists():
        backup_path = Path("poetry.lock.backup")
        if not backup_path.exists():
            shutil.copy2("poetry.lock", backup_path)
            print_success("Backed up poetry.lock to poetry.lock.backup")
        else:
            print_info("Backup of poetry.lock already exists")

    # Backup .venv if it exists
    if venv_path and venv_path.exists():
        backup_path = Path(".venv.poetry-backup")
        if not backup_path.exists():
            print_info("Backing up .venv directory (this may take a moment)...")
            shutil.copytree(venv_path, backup_path)
            print_success("Backed up .venv to .venv.poetry-backup")
        else:
            print_info("Backup of .venv already exists")

    return True


def remove_poetry_environment() -> bool:
    """Remove Poetry virtual environment and lock file."""
    print_header("Removing Poetry Environment")

    removed_something = False

    # Remove .venv if it exists
    venv_path = Path(".venv")
    if venv_path.exists():
        print_info("Removing .venv directory...")
        shutil.rmtree(venv_path)
        print_success("Removed .venv directory")
        removed_something = True

    # Remove .poetry directory if it exists
    poetry_dir = Path(".poetry")
    if poetry_dir.exists():
        print_info("Removing .poetry directory...")
        shutil.rmtree(poetry_dir)
        print_success("Removed .poetry directory")
        removed_something = True

    if not removed_something:
        print_info("No Poetry environment to remove")

    return True


def setup_uv_environment() -> bool:
    """Set up the uv environment and install dependencies."""
    print_header("Setting Up uv Environment")

    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        print_error("pyproject.toml not found. Are you in the project root?")
        return False

    # Check if uv.lock exists
    if not Path("uv.lock").exists():
        print_info("Creating uv.lock file...")
        success, output = run_command(["uv", "lock"], check=False)
        if not success:
            print_error(f"Failed to create lock file: {output}")
            return False
        print_success("Created uv.lock file")
    else:
        print_info("uv.lock already exists")

    # Sync dependencies with all extras
    print_info("Installing dependencies (this may take a moment)...")
    success, output = run_command(["uv", "sync", "--all-extras"], check=False)
    if not success:
        print_error(f"Failed to install dependencies: {output}")
        return False

    print_success("Dependencies installed successfully")
    return True


def verify_installation() -> bool:
    """Verify that the migration was successful."""
    print_header("Verifying Installation")

    checks_passed = True

    # Check uv is available
    if check_uv_installed():
        print_success("uv is installed and accessible")
    else:
        print_error("uv is not accessible")
        checks_passed = False

    # Check .venv exists
    if Path(".venv").exists():
        print_success("Virtual environment created")
    else:
        print_error("Virtual environment not found")
        checks_passed = False

    # Check uv.lock exists
    if Path("uv.lock").exists():
        print_success("uv.lock file present")
    else:
        print_error("uv.lock file not found")
        checks_passed = False

    # Try to run a simple Python command in the environment
    success, output = run_command(["uv", "run", "python", "-c", "print('Hello from uv!')"], check=False)
    if success and "Hello from uv!" in output:
        print_success("Python environment is functional")
    else:
        print_error("Python environment test failed")
        checks_passed = False

    return checks_passed


def print_next_steps() -> None:
    """Print instructions for next steps after migration."""
    print_header("Migration Complete!")

    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}\n")

    print("1. Update your IDE to use the new virtual environment:")
    print("   • VS Code: Should auto-detect .venv")
    print("   • PyCharm: Point interpreter to .venv/Scripts/python.exe (Windows) or .venv/bin/python (Unix)\n")

    print("2. Common uv commands:")
    print("   • Run the application:     uv run python CLASSIC_Interface.py")
    print("   • Run tests:               uv run pytest")
    print("   • Add a package:           uv add package-name")
    print("   • Update dependencies:     uv lock --upgrade")
    print("   • Install specific extra:  uv sync --extra tui\n")

    print("3. If you need to rollback to Poetry:")
    print("   • Restore from backup:     mv poetry.lock.backup poetry.lock")
    print("   • Restore venv:            rm -rf .venv && mv .venv.poetry-backup .venv")
    print("   • Install Poetry deps:     poetry install\n")

    print(f"{Colors.GREEN}For more information, see: docs/uv_deployment_guide.md{Colors.ENDC}")


def main() -> int:
    """Serve as main migration function."""
    print(f"\n{Colors.BOLD}CLASSIC-Fallout4 Poetry → uv Migration Tool{Colors.ENDC}")
    print("This script will help you migrate from Poetry to uv package manager.\n")

    # Check if we're in the right directory
    if not Path("CLASSIC_Interface.py").exists():
        print_error("This script must be run from the CLASSIC-Fallout4 project root directory.")
        return 1

    # Confirm with user
    response = input("Do you want to proceed with the migration? (y/n): ").lower()
    if response != "y":
        print_info("Migration cancelled.")
        return 0

    try:
        # Step 1: Install uv
        if not install_uv():
            return 1

        # Step 2: Backup existing environment
        if not backup_poetry_environment():
            return 1

        # Step 3: Remove Poetry environment
        if not remove_poetry_environment():
            return 1

        # Step 4: Set up uv environment
        if not setup_uv_environment():
            return 1

        # Step 5: Verify installation
        if not verify_installation():
            print_warning("Some checks failed, but migration may still be successful.")
            print_info("Try running: uv run python CLASSIC_Interface.py")

        # Step 6: Print next steps
        print_next_steps()

    except KeyboardInterrupt:
        print_error("\nMigration interrupted by user.")
        return 1
    except Exception as e:  # noqa: BLE001
        print_error(f"Unexpected error: {e}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
