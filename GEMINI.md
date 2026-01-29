# Project Context: CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker)

## Project Overview

**CLASSIC** is a tool designed to analyze crash logs for *Fallout 4* and *Skyrim* (with planned *Starfield* support). It helps users diagnose crashes by scanning logs, detecting mod conflicts, and verifying game file integrity.

The project is a hybrid application using **Python** for the main logic and user interfaces (CLI & GUI), and **Rust** for performance-critical components and specialized bindings.

### Key Technologies
*   **Python:** Core application logic, GUI (`PySide6`), and CLI.
*   **Rust:** Performance-optimized modules (located in `rust/`), integrated via `pyo3` and `maturin`.
*   **Build System:** `uv` (Python dependency management) and `maturin` (Rust extensions).
*   **Packaging:** `PyInstaller` for generating standalone Windows executables.

## Building and Running

### Prerequisites
*   Python 3.12+
*   `uv` (Universal Python Package Manager)
*   Rust toolchain (Cargo/Rustc) - *Required for rebuilding Rust extensions*

### Dependency Management
This project uses `uv` for managing Python dependencies.

```powershell
# Install all dependencies (including dev and optional extras)
uv sync --all-extras
```

### Running the Application
You can run the application directly from the source using `uv`.

*   **GUI Mode:**
    ```powershell
    uv run python CLASSIC_Interface.py
    # OR
    uv run classic
    ```

*   **CLI Mode (Crash Log Scanner):**
    ```powershell
    uv run python CLASSIC_ScanLogs.py
    # OR
    uv run classic-cli
    ```

*   **Game Integrity Scanner:**
    ```powershell
    uv run python CLASSIC_ScanGame.py
    # OR
    uv run classic-scan
    ```

* always use `uv run` to run Python scripts so that it uses the virtual environment properly.

### Rebuilding Rust Extensions
If you modify code in the `rust/` directory, you must rebuild the Python bindings.

```powershell
# Rebuilds all Rust modules and installs them into the venv
.\rebuild_rust.ps1
```

*   **Options:**
    *   `-Clean`: Clean old builds before building.
    *   `build_all.ps1`: Packaging script for building all versions of CLASSIC.

### Building the Executable
To create a standalone `.exe` for distribution, use the `build_all.ps1` script.

## Project Structure

*   `ClassicLib/`: Main Python library containing the core logic.
*   `rust/`: Source code for Rust extensions (PyO3 bindings).
*   `CLASSIC Data/`: Configuration files, databases, and assets.
*   `tests/`: Python test suite (`pytest`).
*   `CLASSIC_Interface.py`: Entry point for the GUI application.
*   `CLASSIC_ScanLogs.py`: Entry point for the CLI crash log scanner.
*   `CLASSIC_ScanGame.py`: Entry point for the game file integrity scanner.
*   `pyproject.toml`: Project configuration, dependencies, and build settings.
*   `rebuild_rust.ps1`: PowerShell script to build and install Rust extensions.

## Development Conventions

*   **Linting & Formatting:**
    *   **Ruff:** Used for linting and formatting Python code. Configured in `pyproject.toml`.
    *   **MyPy / Pyright:** Used for static type checking.
    *   **Rust:** Standard `cargo fmt` and `clippy`.
*   **Testing:**
    *   Run tests with `uv run pytest`.
*   **Architecture:**
    *   The GUI (`CLASSIC_Interface.py`) follows a composition-based pattern, delegating tasks to controllers (e.g., `ScanController`, `BackupManager`) in `ClassicLib/Interface/controllers`.
    *   Rust extensions are exposed as Python modules (pyd files) in the virtual environment.

## Key Files to Reference
*   `README.md`: General user usage and installation.
*   `pyproject.toml`: Dependencies and tool configurations.
*   `rebuild_rust.ps1`: Understanding the Rust-Python bridge build process.

## Testing
*   When not running the full test suite, use the `--no-cov` flag to avoid unnecessary coverage calculations and prevent "exit 1" errors due to "missing coverage" for files that are not being tested.
*   After modifying the TUI, use `uv run pytest --snapshot-update` to update the snapshots and `uv run pytest` to run the tests.
