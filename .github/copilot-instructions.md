# CLASSIC-Fallout4 Copilot Instructions

## Project Overview
CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a hybrid Python-Rust desktop application for analyzing Bethesda game crash logs.
- **Core**: Python (PySide6 GUI, CLI) + Rust (Performance critical ops).
- **Goal**: High performance (Rust) with ease of use (Python).
- **Package Manager**: `uv` (Python), `cargo` (Rust).

## Architecture & "Big Picture"
The project uses a strict layered architecture to separate concerns and maximize performance.

### Rust Layer (`rust/`)
- **Foundation** (`rust/foundation/`): Shared runtime, errors, utilities.
- **Business Logic** (`rust/business-logic/`): **Pure Rust** crates (`-core`). NO PyO3 dependencies. Contains all logic/algorithms.
- **Python Bindings** (`rust/python-bindings/`): **PyO3 adapters** (`-py`). Thin wrappers around `-core` crates.
- **UI Applications** (`rust/ui-applications/`): Standalone Rust apps (CLI, TUI, Slint GUI).

**Critical Rules**:
- **One Runtime Rule**: All crates share a single global Tokio runtime via `classic_shared::get_runtime()`.
- **Separation of Concerns**: Never mix business logic and PyO3 bindings in the same crate.
- **Standalone Modules**: Python binding crates must be `cdylib` + `rlib` and have their own `#[pymodule]`.

### Python Layer (`src/`, `ClassicLib/`)
- **Entry Points**: `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI).
- **ClassicLib**: Main Python library structure.
    - `AsyncBridge`: Singleton for bridging sync (GUI) and async (IO) worlds.
    - `MessageHandler`: Centralized logging/output (replaces `print`).
    - `integration`: Handles Rust acceleration with automatic Python fallback.

## Developer Workflows

### Environment Setup
- **Python**: `uv sync --all-extras` (creates `.venv`).
- **Rust**: `cargo build --workspace` (in `rust/` folder).

### Building & Running
- **Run GUI**: `uv run python CLASSIC_Interface.py`
- **Run CLI**: `uv run python CLASSIC_ScanLogs.py`
- **Rebuild Rust Bindings**: `.\rebuild_rust.ps1` (Windows) or `maturin build` manually.
- **Build Exe**: `uv run pyinstaller --clean .\CLASSIC.spec`

### Testing
- **Python**: `uv run pytest -n auto` (Parallel execution).
    - **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.rust`.
    - **Note**: Use terminal for tests, VS Code test explorer may freeze.
- **Rust**: `cargo test --workspace` (in `rust/` folder).

## Coding Conventions & Patterns

### Python
- **Async-First**: Use `async`/`await` for I/O. Use `AsyncBridge.run_async()` to call from sync GUI context.
- **No `print()`**: Use `ClassicLib.MessageHandler` (`msg_info`, `msg_warning`, `msg_error`).
- **Paths**: Always use `pathlib.Path`, never string paths.
- **Type Hints**: Mandatory (Python 3.12+ syntax).
- **Docstrings**: Google-style required for all modules, classes, and functions.
- **Imports**: Absolute imports preferred.

### Rust
- **Async**: Use `classic_shared::get_runtime()` for async tasks.
- **Error Handling**: Map Rust errors to Python exceptions in `-py` crates.
- **Documentation**: All public items must have `///` doc comments.

### Integration Patterns
- **Transparent Acceleration**:
  ```python
  from ClassicLib.integration.factory import get_parser
  # Returns Rust parser if available, else Python fallback
  parser = get_parser() 
  ```
- **AsyncBridge Usage**:
  ```python
  from ClassicLib.AsyncBridge import AsyncBridge
  bridge = AsyncBridge.get_instance()
  # Run async function from sync context (e.g., Qt slot)
  result = bridge.run_async(my_async_function())
  ```

## Key Files
- `CLASSIC_Interface.py`: Main GUI entry point.
- `ClassicLib/AsyncBridge.py`: Core async/sync coordination.
- `rust/Cargo.toml`: Rust workspace definition.
- `pyproject.toml`: Python dependencies and tool config.
- `rebuild_rust.ps1`: Script to rebuild and install Rust extensions.

## Miscellaneous
- For reasons unknown, PyTest can only reliably be run with the `python -m` method. Trying to run pytest directly results in a `Failed to canonicalize script path` error. Always use `uv run python -m pytest ...` to run Python tests.