# CLASSIC-Fallout4 Copilot Instructions

## Project Overview
Hybrid Python-Rust desktop app for analyzing Bethesda game crash logs.
- **Core**: Python (PySide6 GUI, CLI) + Rust (Performance critical ops).
- **Package Managers**: `uv` (Python), `cargo` (Rust).

## Architecture & Patterns
- **Hybrid Structure**: 
  - **Python**: `ClassicLib` (Logic), `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI).
  - **Rust**: 3-Layer Architecture in `rust/`:
    1. **Foundation**: `classic-shared` (Runtime, Errors).
    2. **Business Logic**: `*-core` crates (Pure Rust, NO PyO3).
    3. **Bindings**: `*-py` crates (PyO3 adapters, depends on `-core`).
- **One Runtime Rule**: All Rust crates share a single global Tokio runtime via `classic_shared::get_runtime()`.
- **Async Strategy**: 
  - **Python**: Async-first. Use `AsyncBridge.run_async()` for sync contexts (GUI).
  - **Rust**: Native async.
- **Integration**: Transparent acceleration. Python falls back to pure Python impl if Rust module missing.

## Critical Workflows
- **Setup**: `uv sync --all-extras` (Python), `cargo build --workspace` (Rust).
- **Run**: `uv run python CLASSIC_Interface.py` (GUI), `uv run python CLASSIC_ScanLogs.py` (CLI).
- **Rebuild Bindings**: `.\rebuild_rust.ps1` (Windows) or `maturin build`. **Required after Rust changes.**
- **Testing**: `uv run python -m pytest -n auto` (Terminal only). **VS Code Test Explorer freezes.**
  - Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.rust`.

## Coding Conventions
- **Python**:
  - **No `print()`**: Use `ClassicLib.MessageHandler` (`msg_info`, `msg_error`).
  - **Paths**: Always use `pathlib.Path`.
  - **Docs**: Google-style docstrings required.
  - **Types**: Python 3.12+ type hints mandatory.
- **Rust**:
  - **Stubs**: `.pyi` files mandatory for all `-py` crates.
  - **Exceptions**: Map Rust errors to Python exceptions in `-py` crates.
  - **Docs**: `///` doc comments required for all public items.

## Key Files
- `CLASSIC_Interface.py`: Main GUI Entry.
- `ClassicLib/AsyncBridge.py`: Sync/Async bridge.
- `rust/Cargo.toml`: Workspace definition.
- `rebuild_rust.ps1`: Rust build script.
