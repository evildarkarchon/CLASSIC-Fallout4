# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a hybrid Python/Rust application that scans crash logs from Buffout 4 (Fallout 4) and Crash Logger (Skyrim). It provides ~250 automated checks for crashes, mod conflicts, and setup issues.

## Build & Development Commands

### Python Setup
```powershell
uv sync --all-extras              # Install all Python dependencies
uv run python CLASSIC_Interface.py  # Run GUI (PySide6)
uv run python CLASSIC_ScanLogs.py   # Run CLI crash log scanner
```

### Rust Build
```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml              # Build all Rust crates
cargo build --workspace --release --manifest-path ClassicLib-rs/Cargo.toml    # Release build
cargo build -p classic-gui --manifest-path ClassicLib-rs/Cargo.toml           # Build only the Slint GUI
```

### Rust Python Bindings (PyO3 via maturin)
```powershell
.\rebuild_rust.ps1                      # Build + install all PyO3 bindings into venv
.\rebuild_rust.ps1 classic_yaml         # Build + install a single binding
.\rebuild_rust.ps1 -Clean               # Clean rebuild
.\rebuild_rust.ps1 -BuildOnly           # Build wheels without installing
```

### C++ Build (classic-cli and classic-gui)
The C++ projects require the MSVC toolchain. Either use the provided build scripts (which initialize the VS Dev environment automatically) or manually open a VS Developer PowerShell / Command Prompt before running CMake commands.
```powershell
# Option 1: Use the build scripts (recommended -- handles VS Dev Shell init)
.\classic-cli\build_cli.ps1                # Build classic-cli
.\classic-gui\build_gui.ps1                # Build classic-gui (Qt 6)

# Option 2: Manual build (requires VS Dev Shell already initialized)
cmake --preset default                     # Configure (vcpkg + Ninja + Corrosion)
cmake --build build                        # Build
```

### Testing
```powershell
# Python tests
uv run pytest                                    # Full suite (default: --cov enabled)
uv run pytest tests/test_scan_logs.py            # Single test file
uv run pytest tests/test_scan_logs.py::TestClass::test_method  # Single test
uv run pytest -m unit                            # By marker
uv run pytest -m "unit and not slow"             # Exclude slow
uv run pytest --skip-slow --skip-network --skip-performance --skip-stress  # CI-like run
uv run pytest --no-cov                           # Disable coverage for faster iteration

# Rust tests
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture  # With output
cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml     # Single crate

# C++ tests (Catch2 v3 via CTest) -- run from classic-cli/ (requires VS Dev Shell)
cmake --preset default                                               # Configure (vcpkg + Ninja + Corrosion)
cmake --build build --target classic-cli-tests                       # Build test executable
ctest --test-dir build --output-on-failure                           # Run all tests via CTest
.\build\classic-cli-tests.exe [thread_pool]                          # Run by tag
.\build\classic-cli-tests.exe -s                                     # Verbose with SECTION names

# C++ integration tests (PowerShell, requires built classic-cli.exe)
.\test_cli.ps1                                                       # Full CLI integration suite
```

### Linting & Formatting
```powershell
# Python
uv run ruff check .               # Lint
uv run ruff format --check .      # Format check
uv run ruff format .              # Auto-format
uv run vulture ClassicLib/ vulture_whitelist.py --min-confidence 80  # Dead code

# Rust
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

### PyInstaller Executables
```powershell
.\build_all.ps1                   # Build all exe variants
uv run pyinstaller --clean .\CLASSIC.spec  # Build single spec
```

## Architecture

### Three-Layer Rust Workspace (`ClassicLib-rs/`)

The Rust workspace under `ClassicLib-rs/` follows a strict three-layer separation:

1. **Foundation** (`ClassicLib-rs/foundation/`) - Shared utilities used by all other crates
   - `classic-shared-core`: Runtime management, string interning, error types, caching primitives
   - `classic-shared-py`: PyO3 bindings for shared utilities

2. **Business Logic** (`ClassicLib-rs/business-logic/`) - Pure Rust crates (`rlib` only, NO PyO3)
   - `classic-scanlog-core`: Crash log parsing and analysis
   - `classic-yaml-core`: YAML settings loading/caching
   - `classic-database-core`: SQLite database operations
   - `classic-file-io-core`: File I/O with encoding detection
   - `classic-config-core`: Configuration management
   - Plus ~14 more domain crates (constants, path, registry, settings, web, etc.)

3. **Bindings** (`ClassicLib-rs/python-bindings/`, `ClassicLib-rs/node-bindings/`, `ClassicLib-rs/cpp-bindings/`) - Thin PyO3/NAPI-RS/CXX adapters
   - Each `*-py` crate wraps its corresponding `*-core` crate as a `cdylib`
   - Python imports them directly: `import classic_yaml`, `import classic_scanlog`
   - `classic-node`: NAPI-RS bindings for Node.js/Bun (tested in CI with Bun)
   - `classic-cpp-bridge`: CXX bridge exposing Rust core crates to C++ (staticlib)
   - `classic-cli`: C++ CLI scanner built with CMake + vcpkg + Corrosion (fmt, CLI11, Catch2)

4. **UI Applications** (`ClassicLib-rs/ui-applications/`)
   - `classic-gui`: Pure Rust GUI using Slint framework (v9.0.0)

### Python Library (`ClassicLib/`)

Python code organized into subpackages:
- `core/` - Constants, logger, registry, async bridge, performance monitoring
- `integration/` - Factory pattern for Rust/Python implementation selection
- `integration/rust/` - Rust-specific wrapper modules
- `io/` - File I/O and YAML operations
- `messaging/` - Message routing system
- `scanning/` - Crash log scanning logic
- `support/` - Version registry, XSE checks
- `Utils/` - File, path, string, version, web utilities
- `Interface/` - PySide6 GUI components
- `TUI/` - Textual-based terminal UI (entry point: `classic-tui`)
- `_async_utils/` - Async utility helpers
- `acceleration/` - Rust acceleration utilities

### Rust Acceleration Pattern

The `ClassicLib/integration/factory.py` module provides `detect_component()` which tries to import a Rust module and returns `(available: bool, module)`. If Rust is unavailable, Python fallbacks are used automatically. Check availability via flags like `RUST_PERF_AVAILABLE`. Note: `classic_registry` is mandatory (no fallback).

### Slint GUI Architecture (`ClassicLib-rs/ui-applications/classic-gui/`)

- `.slint` files in `ui/` define the UI (main.slint + widgets/)
- Shared types live in `ui/widgets/types.slint` to avoid circular imports
- `src/` contains Rust modules: main, state, scan, worker, settings, results, dialogs, markdown, logging
- Uses `classic-shared-core` with `gui-bridge` feature for AsyncBridge

## Key Conventions

### ONE RUNTIME RULE
A single Tokio runtime is shared across the entire application via `classic_shared::get_runtime()`. Never create additional Tokio runtimes.

### AsyncBridge (Slint-Tokio coordination)
- `run_with_ui_update()`, `run_with_timeout()`, `run_cancellable()` bridge async Tokio work to Slint's UI thread
- `EventLoopDispatcher` trait abstracts `slint::invoke_from_event_loop` for testability
- `BridgeError` enum: Timeout/Cancelled/DispatchFailed -- log-and-drop on dispatch failures (no `.expect()`)

### Rust Edition & Lints
- Rust 2024 edition, MSRV 1.85.0
- `unsafe_code = "deny"` on all crates
- `deprecated = "deny"`, `unused = "deny"` workspace-wide
- PyO3 0.27.x with `abi3-py312` (stable ABI targeting Python 3.12+)

### Python Style
- Python 3.12+, line length 140
- Ruff for linting and formatting (replaces black/flake8)
- Pyright strict mode for type checking
- `ban-relative-imports = "all"` -- always use absolute imports
- pytest-asyncio with `asyncio_mode = "auto"`

### C++ Style
- C++20, MSVC on Windows (`/utf-8 /W4`)
- CMake 3.25+ with vcpkg + Corrosion (Ninja generator)
- **Requires VS Dev Shell or the project build scripts** (`build_cli.ps1` / `build_gui.ps1`) which initialize it automatically
- Catch2 v3 for unit tests (bridge-free components: ThreadPool, Progress, CliArgs)
- Unit test tags: `[thread_pool]`, `[progress]`, `[cli_args]`
- Integration tests via `test_cli.ps1` (full binary exercising Rust CXX bridge)
- Test source: `classic-cli/tests/`

### Test Isolation
- An autouse `reset_all_singletons` fixture clears all caches/singletons between tests
- An autouse `prevent_manual_input` fixture mocks `builtins.input` to prevent CI hangs
- Tests use organized fixtures from `tests/fixtures/` (imported via conftest.py)

### Test Markers
Key markers: `unit`, `integration`, `slow`, `stress`, `performance`, `network`, `gui`, `rust`, `parity`, `tui`, `snapshot`. Custom CLI flags: `--skip-slow`, `--skip-network`, `--skip-performance`, `--skip-stress`.

### Windows-Specific
- **Never write to `NUL` or `nul`** -- on Windows this creates an undeletable file on the system drive. Use platform-appropriate alternatives.
- CI runs on `windows-latest` exclusively
- PySide6 uses `QT_QPA_PLATFORM=offscreen` for headless testing

### Slint UI Gotchas
- No CSS-style font-family fallback lists; use a single font name (Consolas on Windows)
- Don't reference `root.width` inside `clamp()` -- causes binding loops; use fixed max values
- Shared types between .slint files go in `widgets/types.slint`
- Negative progress (-1.0) means indeterminate; 0-100 means determinate percentage

## CI Pipeline

GitHub Actions on `windows-latest`, split into per-language workflows for independent notifications:

1. **`ci-rust.yml`** — Rust: format (rustfmt) → lint (clippy) → build → test (with all features)
2. **`ci-python.yml`** — Python: format (ruff) → lint (ruff) → dead code (vulture) → build Rust → build PyO3 bindings (maturin) → pytest (unit, integration, rust-integration)
3. **`ci-typescript.yml`** — TypeScript: build NAPI-RS binary → Bun tests
4. **`benchmarks.yml`** — Benchmarks: separate workflow for performance tracking
