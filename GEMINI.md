# CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application designed to analyze crash logs from Bethesda games (Fallout 4 and Skyrim). It detects mod conflicts, setting errors, and integrity issues.

**Key Characteristics:**
- **Hybrid Architecture:** Python handles the UI (PySide6/Qt) and high-level orchestration, while Rust (`classic-core` and related crates) handles performance-critical tasks (log parsing, file I/O, YAML operations) via PyO3 bindings.
- **Performance:** Rust acceleration provides 10-150x speedups over pure Python implementations.
- **Dual Interface:** 
  - **GUI:** `CLASSIC_Interface.py` (PySide6/Slint)
  - **CLI:** `CLASSIC_ScanLogs.py`
- **Package Management:** Uses `uv` for Python and `cargo` for Rust.

## Directory Structure

### Root Level
- `CLASSIC_Interface.py`: Main entry point for the GUI application.
- `CLASSIC_ScanLogs.py`: Main entry point for the CLI application.
- `ClassicLib/`: Python source code library.
- `rust/`: Root directory for all Rust code.
- `tests/`: Python test suite.
- `pyproject.toml`: Python project configuration (dependencies, tools).
- `build_all.ps1`: Powershell script for building the PyInstaller executables.
- `rebuild_rust.ps1`: Powershell script for cleaning, rebuilding and reinstalling all of the Rust extensions.

### Rust Structure (`rust/`)
**Workspace Root:** `rust/` (This is where the workspace `Cargo.toml` resides. Always run cargo commands from here or use `--manifest-path rust/Cargo.toml`).

The Rust codebase follows a strict modular layered architecture:

1.  **Foundation Layer (`rust/foundation/`)**:
    -   `classic-shared-core`: Runtime, errors, and utilities.
    -   `classic-shared-py`: PyO3 bindings for shared components.

2.  **Business Logic Layer (`rust/business-logic/`)**:
    -   **Pure Rust Only.** NO PyO3 dependencies allowed here.
    -   Includes core logic for YAML, Database, File I/O, Log Scanning, Config, Registry, etc.
    -   Example: `classic-yaml-core`, `classic-scanlog-core`.

3.  **Python Bindings Layer (`rust/python-bindings/`)**:
    -   PyO3 adapters that expose Business Logic to Python.
    -   Depends on corresponding `-core` crates.
    -   Must have `.pyi` stub files for type hints.
    -   Example: `classic-yaml-py`, `classic-scanlog-py`.

4.  **UI Applications (`rust/ui-applications/`)**:
    -   Standalone Rust apps (CLI, TUI, Slint GUI).
    -   Example: `classic-cli`, `classic-gui-slint`.

## Development & Usage

### Prerequisites
- **Python 3.12+**
- **uv** (Python package manager)
- **Rust** (latest stable)

### Setup & Installation
```bash
# Clone and sync dependencies
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
uv sync --all-extras
```

### Running the Application
```bash
# Run GUI
uv run python CLASSIC_Interface.py

# Run CLI
uv run python CLASSIC_ScanLogs.py
```

### Testing
**Crucial:** Use the terminal for testing. VS Code's test explorer may freeze due to the hybrid runtime.

```bash
# Run all tests (parallel)
uv run pytest -n auto

# Run unit tests only (fast)
uv run pytest -n auto -m "unit and not slow"

# Run integration tests
uv run pytest -n auto -m "integration"

# Run Rust integration tests
uv run pytest tests/rust_integration/ -v
```

### Building & Distribution

**Python Applications (PyInstaller):**
`build_all.ps1` is used to create the final distribution builds for the Python-based applications (Classic GUI/CLI) and bundles the Rust extensions.
```powershell
# Build Python distribution
./build_all.ps1
```

**Rust Applications (Standalone):**
To build the standalone pure Rust applications (like `classic-gui` or `classic-tui`), use Cargo from the `rust/` directory.
```bash
cd rust
cargo build --release --workspace
```

### Rebuilding Rust Bindings (Development)
If you modify Rust code for the Python apps, you must rebuild the bindings.

**Using the unified script (Recommended):**
```powershell
# Rebuild ALL modules (incremental, fast)
./rebuild_rust.ps1

# Rebuild specific module(s) by name
./rebuild_rust.ps1 yaml
./rebuild_rust.ps1 scanlog config

# Force a clean rebuild (slower, fixes stale artifacts)
./rebuild_rust.ps1 -Clean
```

**Manual Method (Specific Module):**
```bash
cd rust/python-bindings/classic-yaml-py
maturin build --release --out dist
uv pip install dist/classic_yaml_py-*.whl --force-reinstall
```

## Core Architectural Rules

1.  **One Runtime Rule:** A single global Tokio runtime is shared across all Rust crates via `classic_shared::get_runtime()`. Never start a new runtime.
2.  **Separation of Concerns:**
    -   **Business Logic** goes in `-core` crates (Pure Rust).
    -   **Python Bindings** go in `-py` crates (PyO3).
    -   **Never mix them.**
3.  **Async/Sync Bridge:**
    -   Use `ClassicLib.AsyncBridge` for all async/sync coordination.
    -   In Slint GUI, always use `AsyncBridge::run_with_ui_update()` for async callbacks.
    -   In Python, use `bridge.run_async()` to call async functions from sync contexts.
4.  **Documentation:**
    -   **Python:** Google-style docstrings are mandatory for all modules, classes, and functions.
    -   **Rust:** `///` doc comments are mandatory for all public items. Missing docs are treated as errors.
5.  **Testing:**
    -   Never modify production YAML files in tests; use mocks or `YAML.TEST`.
    -   Always clear singletons (`GlobalRegistry`) between tests.
    -   Use `@pytest.mark.rust` for tests involving Rust acceleration.

## Code Style & Linting

-   **Python:** Follows PEP 8. Checked via `ruff`.
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```
-   **Rust:** Checked via `clippy` and `rustfmt`.
    ```bash
    cargo fmt --all --manifest-path rust/Cargo.toml -- --check
    cargo clippy --workspace --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings
    ```

## Critical Context for AI Agent

-   **Modification Protocol:** When asked to change functionality that involves performance-critical paths (Log Scanning, File I/O, YAML), check if the logic resides in Rust (`rust/business-logic/`). If so, modifications must happen there first, then be exposed via `-py` bindings, and finally updated in the Python `ClassicLib` wrappers.
-   **PyO3 Stubs:** When modifying Rust bindings (`-py` crates), **YOU MUST** update or create the corresponding `.pyi` file in the same directory to ensure Python type checking works.
-   **Deprecation:** Do not remove deprecated APIs immediately. Mark them as deprecated in Python but ensure tests use the *new* API.
-   **Quirk:** For reasons unknown, my virtal environment can not run pytest directly or via `uv run pytest`. Always use `uv run python -m pytest ...` or to execute tests.

## Rust Development Guides

### Core Guides
- **[Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)** - Crate structure and dependency hierarchy
- **[Rust 2024 Edition Guide](docs/development/rust_2024_edition_guide.md)** - Modern Rust features and best practices
- **[Async Development Guide](docs/development/async_development_guide.md)** - Async patterns for Python and Rust
- **[PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)** - PyO3 module registration and troubleshooting
- **[Rust Acceleration Guide](docs/development/rust_acceleration_guide.md)** - Performance monitoring and debugging
- **[Slint GUI Development](docs/development/slint_gui_development.md)** - Slint GUI patterns and AsyncBridge usage

### Reference Documentation
- **[Rust Documentation Index](docs/RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust docs
- **[Rust Usage Guide](docs/rust/rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](docs/performance/performance_monitoring.md)** - Monitor Rust performance
- **[Troubleshooting Guide](docs/rust/troubleshooting_rust.md)** - Debug Rust issues
- **[Development Guide](docs/rust/development_with_rust.md)** - Develop with Rust components

### PyO3 0.26.0 Documentation
- **[PyO3 0.26.0 Migration Guide](docs/rust/pyo3_0.26_migration_guide.md)** - Migration from 0.22 to 0.26.0
- **[PyO3 Quick Reference](docs/rust/pyo3_quick_reference.md)** - Quick reference for common patterns
- **[Official PyO3 Docs](https://pyo3.rs/v0.26.0/)** - Official PyO3 documentation