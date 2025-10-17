# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides three interfaces: GUI (PySide6/Qt), TUI (Textual), and CLI.

**🚀 Rust Acceleration**: CLASSIC uses Rust for performance-critical operations, achieving 10-150x speedups while maintaining full Python compatibility.

## Quick Start

### Installation & Distribution
- **DO NOT use `pip install`** for normal use (not published to PyPI)
- **Exception**: `uv pip install -e . --force-reinstall` for Rust development only
- **Supported methods**:
  1. PyInstaller executables for end users
  2. `uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic` for developers

### Development Setup
```bash
# Setup
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
uv sync --all-extras

# Run application
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_TUI.py        # TUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing (use terminal, not VS Code test tool)
uv run pytest -n auto               # All tests, parallel
uv run pytest -n 4 -m "unit and not slow"  # Quick unit tests
uv run pytest -n 4 -m "integration"        # Integration tests
uv run pytest tests/rust_integration/ -v   # Rust integration tests

# Linting
uv run ruff check .
uv run ruff format .

# Build executable (Windows)
uv run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec
```

### Rust Extension Development
```bash
# Method 1: Build wheel (MOST RELIABLE - RECOMMENDED)
# Note: Build from project root where Cargo.toml is located
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall

# Method 2: Editable install (DEVELOPMENT)
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old FIRST
uv pip install -e . --force-reinstall

# Verify Rust acceleration is working
uv run python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"

# Build Rust without installing (for testing)
cargo build --release --workspace
cargo test --all-features --workspace
```

## Architecture

### Hybrid Python-Rust Architecture
- **Python**: UI, high-level logic, and coordination in `src/classic/` and `ClassicLib/`
- **Rust**: Three-layer modular architecture delivering 10-150x performance gains
  - **Foundation Layer**: `classic-shared` (runtime, errors, utilities)
  - **Business Logic Layer** (Pure Rust - no PyO3):
    - `classic-yaml-core` - YAML operations (yaml-rust2)
    - `classic-database-core` - SQLite operations with connection pooling
    - `classic-file-io-core` - File I/O, encoding detection, DDS parsing
    - `classic-scanlog-core` - Log parsing, FormID analysis, pattern matching
  - **Python Bindings Layer** (PyO3 adapters):
    - `classic-yaml-py` - Python bindings for yaml-core
    - `classic-database-py` - Python bindings for database-core
    - `classic-file-io-py` - Python bindings for file-io-core
    - `classic-scanlog-py` - Python bindings for scanlog-core
    - `classic-config-py` - Python bindings for classic-config-core
  - **Facade Layer**: `classic-core` (re-exports all Python modules)
  - **Legacy Crates**: `classic-yaml`, `classic-database`, `classic-file-io`, `classic-scanlog` (being phased out)
- **Integration**: PyO3 0.26.0 bindings with native async solution (no PyO3-asyncio dependency)
- **Fallback**: Full Python implementations ensure compatibility when Rust unavailable
- **Transparent**: Automatic acceleration - no API changes required
- **Architecture Rules**:
  - **ONE RUNTIME RULE**: Single global Tokio runtime shared across all crates
  - **SEPARATION OF CONCERNS**: Business logic in `-core` crates, PyO3 bindings in `-py` crates
  - **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate

#### Rust Performance Benefits
| Component | Python Time | Rust Time | Speedup |
|-----------|-------------|-----------|---------|
| Log Parsing | 2-3 seconds | 200-300ms | 10x |
| FormID Analysis | 250ms/1000 IDs | 10ms/1000 IDs | 25x |
| Pattern Matching | 100ms/scan | 5ms/scan | 20x |
| File I/O | 50ms/file | 5ms/file | 10x |
| DDS Processing | 20ms/file | 0.5ms/file | 40x |
| Record Scanning | 150ms/scan | 3-4ms/scan | 40x |

### Core Components
- **Entry Points**: `CLASSIC_Interface.py` (GUI), `CLASSIC_TUI.py` (TUI), `CLASSIC_ScanLogs.py` (CLI)
- **AsyncBridge**: Singleton for async/sync bridging (replaces deprecated AsyncCore)
- **MessageHandler**: Central messaging system for all output modes
- **YamlSettingsCache**: Configuration management with batch loading
- **FileIOCore**: Unified async-first file I/O with Rust acceleration (10x faster)
- **OrchestratorCore**: Async-first log scanning orchestration with Rust components
- **integration.factory**: Automatic Rust acceleration with Python fallback

### Async Patterns
```python
# Use AsyncBridge for sync contexts
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Use FileIOCore for file operations
from ClassicLib.FileIOCore import FileIOCore
io_core = FileIOCore()
content = await io_core.read_file(path)

# Batch load settings for performance
from ClassicLib.YamlSettingsCache import yaml_cache
values = yaml_cache.batch_get_settings([
    (str, YAML.Settings, "key1"),
    (bool, YAML.Settings, "key2")
])
```

### Rust Acceleration Patterns
```python
# Transparent acceleration - automatic Rust usage
from ClassicLib.ScanLog.Parser import find_segments  # Uses Rust LogParser if available
from ClassicLib.FileIOCore import FileIOCore  # Uses RustFileIOCore if available

# Check Rust status programmatically
from ClassicLib.integration.status import get_rust_component_status, print_rust_status
status = get_rust_component_status()
if status["acceleration_active"]:
    print(f"🚀 {status['active_count']}/{status['total_count']} components accelerated")

# Force Python fallback (for debugging/testing)
import os
os.environ["CLASSIC_DISABLE_RUST"] = "1"

# Use integration factory functions
from ClassicLib.integration.factory import get_parser, get_formid_analyzer
parser = get_parser()  # RustLogParser with automatic fallback
analyzer = get_formid_analyzer(yamldata, show_values, db_exists)
```

#### Native Async Solution (No PyO3-asyncio)
CLASSIC uses a native async solution that's more reliable and performant. The ONE RUNTIME RULE ensures all crates share a single global Tokio runtime to prevent deadlocks:

```rust
// In classic-shared/src/runtime.rs - shared across all crates
pub(crate) static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    let worker_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(worker_threads)
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime")
});

pub fn get_runtime() -> &'static Runtime {
    &RUNTIME
}

// In other crates - use classic_shared::get_runtime()
#[pyfunction]
fn process_data(data: String) -> PyResult<String> {
    classic_shared::get_runtime().block_on(async move {
        // Full async Rust operations here
        async_operation(data).await
    })
}
```

## Slint GUI Development

CLASSIC includes a pure Rust GUI application built with Slint (`classic-gui-slint`). The GUI uses modern Fluent Design System styling and provides a native desktop experience.

### Dual Event Loop Architecture

The Slint GUI must coordinate between **two separate event loops**:

1. **Slint Event Loop** - Runs on the main thread, handles UI rendering and user interactions
2. **Tokio Runtime** - Shared multi-threaded async runtime for I/O operations (ONE RUNTIME RULE)

**Challenge**: Slint callbacks run on the main thread and are synchronous, but many operations (file I/O, scanning, backups) are async. We need to bridge between these two worlds without blocking the UI.

### AsyncBridge Pattern

The `AsyncBridge` module in `classic-shared` solves this coordination problem, inspired by Python's AsyncBridge pattern:

```rust
use classic_shared::AsyncBridge;

// In a Slint button callback:
main_window.on_scan_crash_logs({
    let window_weak = main_window.as_weak();
    let state = app_state.clone();
    move || {
        // Set loading state immediately (runs on UI thread)
        if let Some(w) = window_weak.upgrade() {
            w.set_scan_in_progress(true);
        }

        // Execute async operation via AsyncBridge
        AsyncBridge::run_with_ui_update(
            perform_scan(state),  // Runs on Tokio runtime
            move |result| {       // Runs on Slint event loop
                // Update UI with result
                if let Some(w) = window_weak.upgrade() {
                    w.set_scan_in_progress(false);
                    match result {
                        Ok(data) => w.show_success(&data),
                        Err(e) => w.show_error(&e.to_string()),
                    }
                }
            }
        );
    }
});
```

### AsyncBridge API

#### `run_with_ui_update<F, R, C>(operation: F, on_complete: C)`
Execute an async operation and invoke a callback on the Slint event loop.

- **Use when**: You need to run async work and update UI with results
- **Pattern**: Background thread → Tokio runtime → UI callback
- **Thread safety**: Both operation and callback must be `Send + 'static`

```rust
AsyncBridge::run_with_ui_update(
    async { tokio::fs::read_to_string("file.txt").await },
    |result| {
        // Update UI here
        window.set_text(result.unwrap().into());
    }
);
```

#### `spawn_background<F>(operation: F)`
Execute an async operation without a callback (fire-and-forget).

- **Use when**: Background tasks that don't need UI updates (logging, analytics)
- **Pattern**: Background thread → Tokio runtime

```rust
AsyncBridge::spawn_background(async {
    log_user_action("button_clicked").await;
});
```

#### `invoke_on_ui_thread<F>(f: F)`
Invoke a function directly on the Slint event loop.

- **Use when**: You're already in an async context and need to update UI
- **Pattern**: Any thread → Slint event loop

```rust
AsyncBridge::invoke_on_ui_thread(|| {
    window.set_status("Ready".into());
});
```

#### `run_with_loading<F, R, L, C>(set_loading: L, operation: F, on_complete: C)`
Higher-level convenience method with automatic loading state management.

- **Use when**: Operations that should show loading indicators
- **Pattern**: Auto-manages loading flag before/after operation

```rust
AsyncBridge::run_with_loading(
    |loading| window.set_loading(loading),
    fetch_data(),
    |result| display_result(result)
);
```

### Development Guidelines

#### ✅ DO: Use AsyncBridge for Async Operations
```rust
// ✅ CORRECT - Uses AsyncBridge
main_window.on_backup_xse({
    let window = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            perform_backup(),
            |result| { /* update UI */ }
        );
    }
});
```

#### ❌ DON'T: Block the Slint Event Loop
```rust
// ❌ WRONG - Blocks UI thread
main_window.on_backup_xse({
    move || {
        // This blocks the entire UI!
        let result = classic_shared::get_runtime().block_on(perform_backup());
        window.set_result(result);
    }
});
```

#### ✅ DO: Use slint::spawn_local for Slint-Aware Async
When you need more control or want to use Slint's built-in async support:

```rust
main_window.on_scan_logs({
    let window = main_window.as_weak();
    move || {
        slint::spawn_local(async move {
            if let Some(w) = window.upgrade() {
                w.set_loading(true);
            }

            let result = handlers::scan::handle_scan().await;

            if let Some(w) = window.upgrade() {
                w.set_loading(false);
                w.display_result(result);
            }
        }).unwrap();
    }
});
```

**Note**: `slint::spawn_local` runs the async block on Slint's event loop, so you can freely call UI methods within it. However, for CPU-intensive or blocking operations, prefer `AsyncBridge` to avoid blocking the UI.

#### ❌ DON'T: Forget to Handle Window Upgrades
```rust
// ❌ WRONG - Doesn't check if window still exists
AsyncBridge::run_with_ui_update(
    perform_backup(),
    |result| {
        window.set_result(result);  // May panic if window closed!
    }
);
```

```rust
// ✅ CORRECT - Always check window upgrade
AsyncBridge::run_with_ui_update(
    perform_backup(),
    move |result| {
        if let Some(w) = window_weak.upgrade() {
            w.set_result(result);
        }
    }
);
```

#### ✅ DO: Clone Data Before Moving into Closures
```rust
// ✅ CORRECT - Clone what you need
main_window.on_backup_xse({
    let window = main_window.as_weak();
    let state = app_state.clone();  // Clone Arc
    move || {
        AsyncBridge::run_with_ui_update(
            perform_backup(state.clone()),
            move |result| { /* ... */ }
        );
    }
});
```

### Common Patterns

#### Pattern 1: Simple Async Operation with UI Update
```rust
main_window.on_button_clicked({
    let window = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            async_operation(),
            move |result| {
                if let Some(w) = window.upgrade() {
                    w.handle_result(result);
                }
            }
        );
    }
});
```

#### Pattern 2: Operation with Loading State
```rust
main_window.on_button_clicked({
    let window = main_window.as_weak();
    move || {
        // Set loading immediately
        if let Some(w) = window.upgrade() {
            w.set_loading(true);
        }

        AsyncBridge::run_with_ui_update(
            async_operation(),
            move |result| {
                if let Some(w) = window.upgrade() {
                    w.set_loading(false);
                    w.handle_result(result);
                }
            }
        );
    }
});
```

#### Pattern 3: Multiple Parallel Operations
```rust
AsyncBridge::run_with_ui_update(
    async {
        // Run multiple operations in parallel
        let (result1, result2, result3) = tokio::join!(
            operation1(),
            operation2(),
            operation3()
        );
        (result1, result2, result3)
    },
    move |results| {
        if let Some(w) = window.upgrade() {
            w.display_results(results);
        }
    }
);
```

#### Pattern 4: Macro for Reducing Boilerplate
```rust
// Define once for repetitive operations
macro_rules! setup_backup_operation {
    ($window:expr, $callback:ident, $operation:expr) => {
        $window.$callback({
            let window = $window.as_weak();
            move || {
                AsyncBridge::run_with_ui_update(
                    $operation,
                    move |result| {
                        if let Some(w) = window.upgrade() {
                            w.handle_backup_result(result);
                        }
                    }
                );
            }
        });
    };
}

// Use for multiple similar operations
setup_backup_operation!(main_window, on_backup_xse, perform_xse_backup());
setup_backup_operation!(main_window, on_backup_enb, perform_enb_backup());
```

### Building and Running

```bash
# Build and run Slint GUI
cargo run -p classic-gui-slint

# Build release version
cargo build -p classic-gui-slint --release

# Enable GUI bridge feature in classic-shared
# (automatically enabled by classic-gui-slint dependency)
```

### Troubleshooting

#### Issue: UI freezes during operation
**Cause**: Blocking the Slint event loop
**Solution**: Ensure all long-running operations use `AsyncBridge` or `slint::spawn_local`

#### Issue: "Failed to invoke callback on Slint event loop"
**Cause**: Slint event loop may have exited
**Solution**: Check that window still exists before invoking callbacks

#### Issue: Nested runtime errors
**Cause**: Using `get_runtime().block_on()` from within an async context
**Solution**: Use `AsyncBridge::run_with_ui_update()` which properly coordinates threads

#### Issue: Data race or shared state corruption
**Cause**: Modifying shared state from multiple threads without synchronization
**Solution**: Use `Arc<RwLock<T>>` for shared state (see `SharedAppState` pattern)

### Key Differences from Python AsyncBridge

The Rust `AsyncBridge` in `classic-shared` is conceptually similar to Python's `AsyncBridge` but adapted for Rust's ownership model and Slint's event loop:

| Python AsyncBridge | Rust AsyncBridge |
|-------------------|------------------|
| `asyncio.run()` in thread pool | `get_runtime().block_on()` in background thread |
| Python's GIL for thread safety | Rust's `Send + 'static` bounds |
| Direct callback invocation | `slint::invoke_from_event_loop()` |
| Weak references | `Weak<SlintComponent>` |

Both follow the same pattern: **spawn background thread → run async on runtime → callback on UI thread**.

## Testing Standards

### Test Organization
- **Structure**: Domain-driven directories in `tests/`
  - `async_resources/`, `io/`, `concurrency/`, `performance/`
  - `backup/`, `documents/`, `game/`, `mods/`, `settings/`
  - `gui/`, `tui/`, `setup/`
  - `rust_integration/` - Rust-Python integration tests
- **File Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Markers**: Required - `@pytest.mark.unit`, `.integration`, `.asyncio`, `.slow`, `.gui`, `.performance`, `.rust`

### Critical Rules
1. **NEVER modify production YAML** in tests (use `YAML.TEST` or mocks)
2. **NEVER add backward compatibility** to fix tests (update tests to match new API)
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Test Rust integration** with `@pytest.mark.rust` for components that use acceleration
6. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones
   - No tests for deprecated APIs
   - Update existing tests to use current APIs
   - Remove redundant tests if equivalent test exists with current API

### Test-Driven Development
Follow Red-Green-Refactor cycle:
1. Write failing test first
2. Write minimal code to pass
3. Refactor for quality

### Testing Guides
See `docs/` for detailed guides on:
- `testing_async_bridge.md` - Async/sync mocking
- `testing_global_registry.md` - Singleton isolation
- `testing_yaml_cache.md` - Config testing
- `test_pollution_guide.md` - Master pollution prevention guide
- `rust_usage_guide.md` - Using Rust components
- `performance_monitoring.md` - Monitoring Rust performance
- `troubleshooting_rust.md` - Debugging Rust issues

## Code Quality Standards

### File Organization
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** (use dict mapping, match statements, or extract methods)
- **Complete type annotations** (Python 3.12+ syntax)

### Development Rules
1. **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
2. **Use pathlib.Path** - Never string paths
3. **UTF-8 encoding** with `errors="ignore"` for file ops
4. **Async-first** - Use AsyncBridge for sync contexts
5. **Batch operations** - Load multiple YAML settings together
6. **Test markers** - All tests must have appropriate markers
7. **Deprecated APIs = ERRORS** - Treat all deprecated warnings as compilation errors
   - Python: Never use deprecated APIs, update immediately
   - Rust: Never use deprecated PyO3/crate APIs, fix warnings immediately
   - Zero tolerance for deprecation warnings in CI/CD
8. **API Stability Rules** - Production code maintains backward compatibility
   - Tests are exempt from API stability (always use current APIs)
   - Deprecated code ONLY used in tests or `__init__.py` can be deleted
   - If code is marked deprecated AND has no production usage → DELETE IT
   - Update tests to use current APIs when deleting deprecated code

### Common Anti-Patterns to Avoid
- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Production YAML in tests → ✅ `YAML.TEST` or mocks
- ❌ String paths → ✅ `pathlib.Path`
- ❌ Direct print → ✅ MessageHandler
- ❌ Missing type hints → ✅ Complete annotations
- ❌ Manual event loops → ✅ AsyncBridge
- ❌ Deprecated APIs (Python/Rust) → ✅ Use current APIs immediately
- ❌ `prepare_freethreaded_python()` → ✅ `Python::initialize()`
- ❌ `Python::with_gil()` → ✅ `Python::attach()`

## File Structure

### ClassicLib Organization (Refactored)
Modular one-class-per-file structure with subdirectories:
- **MessageHandler/** - Messaging components
- **Utils/** - Utility functions by category
- **FileIO/** - File operations and encoding
- **ScanLog/** - Log scanning with fragments/, models/, pipeline/
- **TUI/** - Terminal UI with screens/, widgets/, handlers/
- **Interface/** - GUI components and settings

All maintain backward compatibility through re-exports.

## Rust Acceleration & Troubleshooting

### Performance Monitoring
```python
# Check Rust status
from ClassicLib.integration.status import print_rust_status
print_rust_status()  # Detailed component status

# Programmatic status check
from ClassicLib.integration.status import get_rust_component_status
status = get_rust_component_status()
print(f"Active: {status['active_count']}/{status['total_count']}")

# Check specific component
from ClassicLib.integration.status import is_rust_accelerated
if is_rust_accelerated("parser"):
    print("🚀 Parser using Rust acceleration")
```

### Environment Configuration
```bash
# Enable Rust debugging
export RUST_LOG=debug
export RUST_BACKTRACE=1

# Force Python fallback (for testing/debugging)
export CLASSIC_DISABLE_RUST=1

# Check if Rust is available without running app
python -c "import classic_core; print('Rust available')"
```

### PyO3 Module Registration Patterns

**CRITICAL**: PyO3 `#[pyclass]` types are ONLY exported when registered in a `#[pymodule]` function of a **standalone cdylib** module.

**Pattern 1: Standalone Module (REQUIRED for #[pyclass] export)**
```toml
# Cargo.toml
[lib]
crate-type = ["cdylib", "rlib"]  # Both cdylib AND rlib
```
```rust
// lib.rs
#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MyClass>()?;  // This registers the class
    Ok(())
}
```
**Result**: Classes are accessible from Python as `import my_module; my_module.MyClass()`

**Pattern 2: Library-only Module (DOES NOT export #[pyclass])**
```toml
# Cargo.toml
[lib]
crate-type = ["rlib"]  # Only rlib
```
**Result**: `#[pyclass]` types are NOT accessible from Python, even if registered in a `#[pymodule]` function!

**Architecture Rule**: Each Rust crate that exports Python classes MUST be:
1. Built as BOTH `cdylib` and `rlib`
2. Have its own `#[pymodule]` function
3. Be installed as a separate Python module

**Example**:
- ✅ `classic_config-py` - standalone module with YamlData
- ✅ `classic_scanlog-py` - standalone module with RustOrchestrator, AnalysisConfig, AnalysisResult
- ✅ `classic_core-py` - standalone module re-exporting from other crates
- ✅ `classic-yaml-py` - standalone module with PyYamlOperations

### Common Issues
1. **Module not found**: Use build method 1 (recommended) to update .pyd
   ```bash
   maturin build --release --out classic-core/dist
   uv pip install classic-core/dist/classic-*.whl --force-reinstall
   ```

2. **Classes not exported from module**: Ensure crate is built as `cdylib` (not just `rlib`)
   ```toml
   [lib]
   crate-type = ["cdylib", "rlib"]  # Need BOTH!
   ```

3. **Old .pyd loads**: Remove from site-packages before editable install
   ```bash
   rm .venv/Lib/site-packages/classic_core.pyd
   uv pip install -e . --force-reinstall
   ```

4. **PyO3 conversion errors**: Use direct attribute access or pre-convert
   - Rust components expect specific data types
   - Check logs for conversion errors

5. **Changes not reflected**: Use `--force-reinstall` and verify timestamp
   ```python
   import classic_core
   print(f"Version: {classic_core.__version__}")
   ```

6. **Performance not improving**: Check component status
   ```python
   from ClassicLib.integration.status import RUST_AVAILABLE
   print(f"Available components: {RUST_AVAILABLE}")
   ```

7. **Build failures**: Common causes and solutions
   ```bash
   # Update Rust toolchain
   rustup update

   # Clear Cargo cache
   cargo clean

   # Reinstall maturin
   uv pip install --upgrade maturin
   ```

8. **Nested runtime errors** ("Cannot start a runtime from within a runtime"):
   - Use `py.detach()` to release GIL before parallel work
   - Use `Python::attach()` to reacquire GIL in worker threads
   - Avoid `get_runtime().block_on()` when already in a Python context
   - Use synchronous I/O for now in contexts where async causes conflicts

## Important Notes
- **Python 3.12+ required**
- **uv** package manager (faster than poetry)
- **Terminal for tests** (VS Code test tool freezes)
- **API compatibility priority** with deprecation warnings (production code only - tests always use current APIs)
- **Rust acceleration** automatic and transparent (10-150x speedups)
- **Native async solution** - no PyO3-asyncio dependency
- **No proactive doc creation** unless requested

## Rust Workspace Structure

### Architecture Rules (NEW - 2025-10-08)

**CRITICAL**: All new Rust code MUST follow the separated architecture pattern:

1. **Business Logic Crates** (`*-core`):
   - `crate-type = ["rlib"]` - Pure Rust library only
   - **NO PyO3 dependency** - Must compile without PyO3
   - Contains all algorithms, data structures, and logic
   - Can be used by CLI/TUI applications directly
   - Example: `classic-yaml-core`, `classic-scanlog-core`

2. **Python Binding Crates** (`*-py`):
   - `crate-type = ["cdylib"]` - Python extension only
   - Depends on corresponding `-core` crate
   - Thin adapter layer converting Python ↔ Rust types
   - Should be **minimal** - only type conversions and `#[pyclass]`/`#[pymethods]` wrappers
   - No business logic - all algorithms/data structures belong in `-core`
   - Example: `classic-yaml-py`, `classic-scanlog-py`

3. **Naming Convention**:
   - Business logic: `classic-{name}-core`
   - Python bindings: `classic-{name}-py`
   - Python module name: `classic_{name}` (in Cargo.toml `[lib]` section)

4. **Migration Status**:
   - ✅ **New crates created**: All `-core` and `-py` crates exist as of Phase 0
   - 🔄 **Legacy crates**: `classic-yaml`, `classic-database`, `classic-file-io`, `classic-scanlog` being phased out

**Example Structure**:
```toml
# classic-yaml-core/Cargo.toml (Business Logic)
[lib]
crate-type = ["rlib"]  # Pure Rust

[dependencies]
classic-shared = { path = "../classic-shared" }
yaml-rust2 = { workspace = true }
# NO pyo3!

# classic-yaml-py/Cargo.toml (Python Bindings)
[lib]
name = "classic_yaml"  # Python module name
crate-type = ["cdylib"]

[dependencies]
classic-yaml-core = { path = "../classic-yaml-core" }
pyo3 = { workspace = true }
```

CLASSIC uses a modular Cargo workspace with separated business logic and Python bindings:

```
.
├── Cargo.toml                       # Workspace root with shared dependencies
│
├── classic-shared/                  # Foundation (runtime, errors, utilities)
│   └── src/runtime.rs              # Global Tokio runtime (ONE RUNTIME RULE)
│
├── classic-yaml-core/               # YAML business logic (pure Rust)
│   └── src/lib.rs                  # YamlOperations
├── classic-yaml-py/                 # YAML Python bindings (PyO3)
│   └── src/lib.rs                  # PyYamlOperations wrapper
│
├── classic-database-core/           # Database business logic (pure Rust)
│   └── src/lib.rs                  # DatabasePool, FormID lookups
├── classic-database-py/             # Database Python bindings (PyO3)
│   └── src/lib.rs                  # PyDatabasePool wrapper
│
├── classic-file-io-core/            # File I/O business logic (pure Rust)
│   └── src/lib.rs                  # FileIOCore, encoding, DDS
├── classic-file-io-py/              # File I/O Python bindings (PyO3)
│   └── src/lib.rs                  # RustFileIOCore wrapper
│
├── classic-scanlog-core/            # Scanlog business logic (pure Rust)
│   └── src/lib.rs                  # LogParser, FormIDAnalyzer, etc.
├── classic-scanlog-py/              # Scanlog Python bindings (PyO3)
│   └── src/lib.rs                  # Rust*Parser wrappers
│
├── classic-config-py/               # Config Python bindings (PyO3)
│   └── src/lib.rs                  # YamlData wrapper
├── classic-config-core/             # Config business logic (pure Rust)
│   └── src/lib.rs                  # Configuration management
│
├── classic-core/                    # Facade (re-exports all -py modules)
│   └── src/lib.rs                  # Python entry point
│
└── [Legacy crates being phased out]
    ├── classic-yaml/                # To be replaced by classic-yaml-py
    ├── classic-database/            # To be replaced by classic-database-py
    ├── classic-file-io/             # To be replaced by classic-file-io-py
    └── classic-scanlog/             # To be replaced by classic-scanlog-py
```

### Dependency Hierarchy (New Architecture)
```
┌─────────────────────────────────────────────┐
│  Python Application Layer                   │
│  - Python imports classic_core              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Python Bindings Layer (-py crates)        │
│  classic-yaml-py, classic-database-py       │
│  classic-file-io-py, classic-scanlog-py    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Business Logic Layer (-core crates)       │
│  classic-yaml-core, classic-database-core   │
│  classic-file-io-core, classic-scanlog-core│
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Foundation Layer                           │
│  classic-shared (runtime, errors)          │
└─────────────────────────────────────────────┘
```

**Key Rules:**
- **NO circular dependencies** between crates
- **ONE RUNTIME RULE**: All crates use `classic_shared::get_runtime()`
- **SEPARATION OF CONCERNS**: `-core` crates have NO PyO3, `-py` crates are thin adapters
- **Workspace dependencies**: Centralized in root `Cargo.toml`
- **CLI/TUI applications**: Use `-core` crates directly (bypass Python bindings)

## Rust Documentation
For comprehensive Rust documentation, see:
- **[Rust Documentation Index](docs/RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust docs
- **[Rust Usage Guide](docs/rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](docs/performance_monitoring.md)** - Monitor Rust performance
- **[Troubleshooting Guide](docs/troubleshooting_rust.md)** - Debug Rust issues
- **[Development Guide](docs/development_with_rust.md)** - Develop with Rust components
- **[Full Backend Migration Plan](docs/rust_full_backend_migration_plan.md)** - Complete backend migration strategy

### YAML Operations (yaml-rust2)
- **Library**: yaml-rust2 v0.10.4 (YAML 1.2 compliant, pure Rust, owned types)
- **Previous**: serde_yaml (deprecated), saphyr (lifetime complexity)
- **Migration**: Completed 2025-10-02
- **Import**: `from classic_core import yaml; ops = yaml.RustYamlOperations()` (standard PyO3 pattern for all classic_core submodules)
- **Features**:
  - Multi-document support
  - Anchor/alias resolution
  - Insertion order preservation (LinkedHashMap)
  - Pure Rust safety (no unsafe FFI)
  - PyO3-friendly (no lifetime parameters)
  - 15-30x performance vs ruamel.yaml

### PyO3 0.26.0 Documentation (Current)
- **[PyO3 0.26.0 Migration Guide](docs/pyo3_0.26_migration_guide.md)** - Detailed migration from 0.22 to 0.26.0
- **[PyO3 Quick Reference](docs/pyo3_quick_reference.md)** - Quick reference for common patterns
- **[Official PyO3 Docs](https://pyo3.rs/v0.26.0/)** - Official PyO3 documentation

## Memories
- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings
- **classic_core import pattern**: Always use `from classic_core import <module>` NOT `from classic_core.<module> import <class>` (applies to all submodules: yaml, database, file_io, scanlog, utils, etc. - this is a PyO3 packaging pattern)
- **Workspace modularization complete**: classic-rust renamed to classic-core as thin facade (2025-10-06)
- **ONE RUNTIME RULE**: All Rust crates use `classic_shared::get_runtime()` to share global Tokio runtime
- **PyO3 module registration**: `#[pyclass]` types ONLY export from standalone cdylib modules - rlib-only crates cannot export classes to Python (discovered 2025-10-07)
- **Standalone module pattern**: Each Rust crate exporting Python classes must have `crate-type = ["cdylib", "rlib"]` AND be installed as separate Python module (like classic_config, classic_scanlog)
- **GIL handling for parallel work**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in worker threads (PyO3 0.26)
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context - use synchronous I/O or proper async patterns
- **Business logic separation** (2025-10-08): ALL new Rust code MUST separate business logic (`-core` crates, no PyO3) from Python bindings (`-py` crates, thin adapters). Phase 0 complete - 9 new crates created. See [Business Logic Separation Plan](docs/rust_business_logic_separation_plan.md)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate - this is a fundamental architectural rule going forward
- **Slint AsyncBridge pattern** (2025-10-11): ALWAYS use `AsyncBridge::run_with_ui_update()` for async operations in Slint GUI to bridge between Tokio runtime and Slint event loop. NEVER block Slint event loop with `get_runtime().block_on()`. Use `slint::spawn_local()` for Slint-aware async when UI updates are needed within the async block.
