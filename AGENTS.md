# AGENTS.md

This file provides guidance to GitHub Copilot and other AI coding agents when working with code in this repository.

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
cargo build -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml           # Build only the Rust TUI
```

### Rust Python Bindings (PyO3 via maturin)
```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1                      # Build + install all PyO3 bindings into venv
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 classic_yaml         # Build + install a single binding
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Clean               # Clean rebuild
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -BuildOnly           # Build wheels without installing
```

### C++ Build (classic-cli and classic-gui)

**IMPORTANT: C++ builds require the MSVC toolchain (cl.exe, link.exe, Windows SDK headers/libs).** These tools are NOT on PATH by default. You MUST either use the build scripts (which auto-initialize the environment) or manually initialize VS Dev Shell before running any cmake commands. Without this, cmake will fail to find a C++ compiler and the build will error out immediately.

**Prerequisites:**
- Visual Studio with C++ Desktop workload (currently VS 2026 v18)
- `VCPKG_ROOT` environment variable set (currently `C:\vcpkg`)
- Ninja build system (included with VS Dev Shell initialization)

#### Option 1: Build Scripts (Recommended -- handles everything automatically)
The build scripts auto-detect VS via `vswhere.exe`, initialize the MSVC environment, and run cmake. **Always prefer these over raw cmake commands.**

Since Claude Code runs bash, invoke PowerShell 7 explicitly:
```bash
# Build classic-cli
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1

# Build classic-gui (Qt 6)
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1

# Build + run tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test

# Clean rebuild
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean
```

#### Option 2: Manual cmake (requires VS Dev Shell initialized first)
If you need to run cmake commands directly (e.g., building a specific target), you must initialize VS Dev Shell in the **same shell session**. The environment variables it sets (PATH, INCLUDE, LIB, etc.) are session-scoped and do not persist across separate commands.

**This means you CANNOT run VS Dev Shell init as one bash command and cmake as another -- they must be in the same PowerShell invocation.**

```bash
# Single PowerShell invocation that inits VS Dev Shell + runs cmake:
pwsh -ExecutionPolicy Bypass -Command '
  $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath 2>$null
  if (-not $vsPath) { $vsPath = "C:\Program Files\Microsoft Visual Studio\18\Community" }
  & (Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1") -Arch amd64 -SkipAutomaticLocation | Out-Null
  Write-Host "cl.exe: $(Get-Command cl.exe | Select-Object -ExpandProperty Source)"
  cd classic-cli   # or classic-gui
  cmake --preset default
  cmake --build build
'
```

**Why this complexity?** The MSVC compiler (`cl.exe`), linker (`link.exe`), and Windows SDK headers/libs are installed by Visual Studio but not added to the system PATH. `Launch-VsDevShell.ps1` sets ~15 environment variables (PATH, INCLUDE, LIB, LIBPATH, etc.) that cmake needs to locate the compiler and SDK. These are process-scoped, so each new shell/process starts without them.

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

# C++ tests (Catch2 v3 via CTest) -- requires VS Dev Shell (use build script)
# Recommended: use the build script with -Test flag (handles VS Dev Shell automatically):
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test

# Manual approach (must run in a single PowerShell session with VS Dev Shell):
pwsh -ExecutionPolicy Bypass -Command '
  $vsPath = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath 2>$null
  if (-not $vsPath) { $vsPath = "C:\Program Files\Microsoft Visual Studio\18\Community" }
  & (Join-Path $vsPath "Common7\Tools\Launch-VsDevShell.ps1") -Arch amd64 -SkipAutomaticLocation | Out-Null
  cd classic-cli
  cmake --preset default
  cmake --build build --target classic-cli-tests
  ctest --test-dir build --output-on-failure
'

# C++ integration tests (PowerShell, requires built classic-cli.exe)
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
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
pwsh -ExecutionPolicy Bypass -File build_all.ps1                   # Build all exe variants
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
   - **Exception**: `classic-pybridge-py` has no `-core` counterpart -- its bridge metrics and runtime helpers live directly in the binding crate, since the functionality is exclusively Python-facing and doesn't warrant a separate intermediate crate.
   - Python imports them directly: `import classic_yaml`, `import classic_scanlog`
   - `classic-node`: NAPI-RS bindings for Node.js/Bun (tested in CI with Bun)
   - `classic-cpp-bridge`: CXX bridge exposing Rust core crates to C++ (staticlib)
   - `classic-cli`: C++ CLI scanner built with CMake + vcpkg + Corrosion (fmt, CLI11, Catch2)

4. **UI Applications** (`ClassicLib-rs/ui-applications/`)
   - `classic-tui`: Pure Rust terminal UI using Ratatui

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

## Key Conventions

### ONE RUNTIME RULE
A single Tokio runtime is shared across the entire application via `classic_shared::get_runtime()`. Never create additional Tokio runtimes.

### AsyncBridge (Optional UI-Tokio coordination)
- `run_with_ui_update()`, `run_with_timeout()`, `run_cancellable()` bridge async Tokio work to a UI thread
- `EventLoopDispatcher` trait abstracts event-loop dispatching for testability
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
- CMake 3.25+ with vcpkg + Corrosion (Ninja generator required -- NOT VS multi-config)
- **VS Dev Shell is mandatory** for any C++ build/test command. Use the build scripts (`build_cli.ps1` / `build_gui.ps1`) which auto-initialize it via `vswhere.exe` + `Launch-VsDevShell.ps1`. See the "C++ Build" section above for details on manual initialization.
- Catch2 v3 for unit tests (bridge-free components: ThreadPool, Progress, CliArgs)
- Unit test tags: `[thread_pool]`, `[progress]`, `[cli_args]`
- Integration tests via `test_cli.ps1` (full binary exercising Rust CXX bridge)
- Test source: `classic-cli/tests/`

### Test Isolation (Python)
- An autouse `reset_all_singletons` fixture clears all caches/singletons between tests
- An autouse `prevent_manual_input` fixture mocks `builtins.input` to prevent CI hangs
- Tests use organized fixtures from `tests/fixtures/` (imported via conftest.py)

### Test Markers (Python)
Key markers: `unit`, `integration`, `slow`, `stress`, `performance`, `network`, `gui`, `rust`, `parity`, `tui`, `snapshot`. Custom CLI flags: `--skip-slow`, `--skip-network`, `--skip-performance`, `--skip-stress`.

### Windows-Specific
- **Never write to `NUL` or `nul`** -- on Windows this creates an undeletable file on the system drive. Use platform-appropriate alternatives.
- CI runs on `windows-latest` exclusively
- PySide6 uses `QT_QPA_PLATFORM=offscreen` for headless testing

## CI Pipeline

GitHub Actions on `windows-latest`, split into per-language workflows for independent notifications:

1. **`ci-rust.yml`** — Rust: format (rustfmt) → lint (clippy) → build → test (with all features)
2. **`ci-python.yml`** — Python: format (ruff) → lint (ruff) → dead code (vulture) → build Rust → build PyO3 bindings (maturin) → pytest (unit, integration, rust-integration)
3. **`ci-typescript.yml`** — TypeScript: build NAPI-RS binary → Bun tests
4. **`benchmarks.yml`** — Benchmarks: separate workflow for performance tracking

## Node API Parity Contributor Checklist

When a PR changes Rust public APIs or Node binding exports, parity updates are required in the same PR.

Trigger paths (minimum):
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/node-bindings/classic-node/src/`
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts`

Checklist:
1. Classify affected APIs as Tier-1 or Tier-2 using `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`.
2. If promoting to Tier-1, update `docs/implementation/node_api_parity/baseline/parity_contract.json`.
3. Regenerate and commit `ClassicLib-rs/node-bindings/classic-node/index.d.ts`.
4. Run from `ClassicLib-rs/node-bindings/classic-node`:
   - `bun run parity:gate:local`
   - `bun run test:bun`
   - `bun run test:node`
5. Confirm CI `ci-typescript.yml` passes parity jobs before merge.

Release gate policy:
- Do not tag a release unless Tier-1 parity gate passes and `index.d.ts` freshness gate passes in CI.

## Cursor Cloud specific instructions

### Platform notes

This project's CI runs exclusively on `windows-latest`. On the Linux Cloud Agent VM:

- **`classic-path-core`** has Linux-specific compilation fixes applied (unused import, `.map_err()` type mismatch, dead code warnings). These are minimal `cfg_attr`/`allow` changes.
- **`classic-scangame-core`** and **`classic-resource-core`** depend on `ba2` -> `directxtex` (DirectX), which cannot build on Linux. Exclude them: `--exclude classic-scangame-core --exclude classic-resource-core`.
- **`classic-tui`** (Rust TUI) requires `wayland-client` dev headers (`libwayland-dev`). Not installed by default; the Python TUI (`ClassicLib.TUI`) is the simpler alternative.
- **C++ targets** (`classic-cli`, `classic-gui`) require MSVC and cannot build on Linux.

### Running services

- **PySide6 GUI**: Requires `QT_QPA_PLATFORM=offscreen` and `libegl1 libopengl0` system packages. Launch with minimal registry init (see setup session) since `SetupCoordinator.initialize_application()` prompts for game paths interactively on Linux (no Fallout 4/Skyrim installed).
- **CLI scanner** (`CLASSIC_ScanLogs.py`): Has pre-existing sync-in-async-context bugs that prevent execution (`yaml_settings()` called from async context in `executor.py` and `util_legacy.py`). These are code issues, not environment issues.

### Quick reference

Standard commands from AGENTS.md/CLAUDE.md apply. Key Linux-specific adjustments:

| Task | Command |
|---|---|
| Python deps | `uv sync --all-extras` |
| Python lint | `uv run ruff check .` and `uv run ruff format --check .` |
| Python tests | `QT_QPA_PLATFORM=offscreen uv run pytest -m unit --skip-slow --skip-network --skip-performance --skip-stress --no-cov --ignore=tests/integration/test_rust_scanners_integration.py --ignore=tests/integration/test_scangame_factory_integration.py` |
| Rust build | `cargo build --workspace --exclude classic-scangame-core --exclude classic-resource-core --exclude classic-tui --exclude classic-node --exclude classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` (excludes Windows/wayland-dependent crates) |
| Rust lint | `cargo clippy -p <crate> --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` |
| Rust tests | `cargo test -p <crate> --manifest-path ClassicLib-rs/Cargo.toml` (test individual core crates; PyO3 binding crate tests fail to link without Python shared lib) |
| Build PyO3 bindings | From each binding crate dir: `maturin build --release --out dist` then `uv pip install dist/*.whl --force-reinstall` (the `.venv/bin/maturin` path must be used) |

### PyO3 binding installation

The `rebuild_rust.ps1` script is Windows-only. On Linux, build each binding crate individually:

```bash
cd ClassicLib-rs/python-bindings/<crate-name>  # or foundation/<crate-name>
/workspace/.venv/bin/maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
```

There are 18 binding crates total (1 foundation + 17 python-bindings). Crates depending on `classic-scangame-core` or `classic-resource-core` (`classic-scangame-py`, `classic-resource-py`) cannot build on Linux.
