# Architecture

## Hybrid Python-Rust Architecture
- **Python**: UI, high-level logic, and coordination in `src/classic/` and `ClassicLib/`
- **Rust**: Three-layer modular architecture delivering 10-150x performance gains
  - **Foundation Layer**: `classic-shared` (runtime, errors, utilities)
  - **Business Logic Layer** (Pure Rust - no PyO3): `-core` crates
  - **Python Bindings Layer** (PyO3 adapters): `-py` crates
- **Integration**: PyO3 0.26.0 bindings with native async solution
- **Direct Imports**: Python imports individual modules (e.g., `import classic_yaml`)
- **Fallback**: Full Python implementations ensure compatibility
- **Transparent**: Automatic acceleration - no API changes required

**Architecture Rules**:
- **ONE RUNTIME RULE**: Single global Tokio runtime shared across all crates
- **SEPARATION OF CONCERNS**: Business logic in `-core` crates, PyO3 bindings in `-py` crates
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate

**Deep Dive**: See [Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)

## Rust Directory Structure

**IMPORTANT**: All Rust crates are organized in the `rust/` directory with subdirectories by layer. The authoritative list is in `rust/Cargo.toml`.

```
rust/
├── Cargo.toml                        # Workspace manifest (authoritative crate list)
├── Cargo.lock                        # Dependency lock file
├── foundation/                       # Foundation Layer
│   ├── classic-shared-core/         # Core runtime, errors, utilities
│   └── classic-shared-py/           # PyO3 bindings for shared components
├── business-logic/                   # Business Logic Layer (Pure Rust - NO PyO3)
│   └── classic-*-core/              # All business logic crates (yaml, database, scanlog, config, etc.)
├── python-bindings/                  # Python Bindings Layer (PyO3 adapters)
│   └── classic-*-py/                # All Python binding crates (one per -core crate)
└── ui-applications/                  # UI Applications
    ├── classic-cli/                 # Command-line interface
    ├── classic-tui/                 # Terminal UI (Ratatui)
    ├── classic-gui-slint/           # Slint GUI
    └── classic-ui-shared/           # Shared UI components
```

**Current crates** (see `rust/Cargo.toml` for full list): yaml, database, file-io, scanlog, config, scangame, registry, perf, pybridge, settings, message, path, constants, version, resource, xse, web, update

## Creating New Crates

1. **Business Logic** (`-core` crate): Create in `rust/business-logic/`
   - Pure Rust, NO PyO3 dependencies
   - `Cargo.toml`: `crate-type = ["rlib"]`
   - Add to workspace in `rust/Cargo.toml` under `# Business Logic`

2. **Python Bindings** (`-py` crate): Create in `rust/python-bindings/`
   - Depends on corresponding `-core` crate
   - `Cargo.toml`: `crate-type = ["cdylib", "rlib"]`
   - Add PyO3 dependency: `pyo3.workspace = true`
   - Add to workspace in `rust/Cargo.toml` under `# Python Bindings`
   - Add to `rebuild_rust.ps1` and `build_all.ps1`
   - **MUST create/update `.pyi` stub file** for type hints and IDE support

3. **UI Applications**: Create in `rust/ui-applications/`
   - Standalone applications (CLI/TUI/GUI)
   - Add to workspace in `rust/Cargo.toml` under `# Native Applications`

**Build System Updates**:
- Always update `rust/Cargo.toml` workspace members when adding crates
- Update `rebuild_rust.ps1` for Python binding crates
- Update `build_all.ps1` for PyInstaller bundling

## Core Components
- **Entry Points**: `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI)
- **AsyncBridge**: Singleton for async/sync bridging (replaces deprecated AsyncCore)
- **MessageHandler**: Central messaging system for all output modes
- **YamlSettingsCache**: Configuration management with batch loading
- **FileIOCore**: Unified async-first file I/O with Rust acceleration (10x faster)
- **OrchestratorCore**: Async-first log scanning orchestration with Rust components

## Essential Patterns

```python
# Use AsyncBridge for sync contexts
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Transparent Rust acceleration
from ClassicLib.ScanLog.Parser import find_segments  # Uses Rust if available
from ClassicLib.integration.factory import get_parser  # Automatic fallback
```

**Complete Guide**: See [Async Development Guide](docs/development/async_development_guide.md)

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

## Slint GUI Development

**Key Rule**: Always use `AsyncBridge::run_with_ui_update()` for async operations in Slint callbacks.

```rust
use classic_shared::AsyncBridge;

main_window.on_scan_crash_logs({
    let window_weak = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            perform_scan(),
            move |result| {
                if let Some(w) = window_weak.upgrade() {
                    w.handle_result(result);
                }
            }
        );
    }
});
```

**Complete Guide**: See [Slint GUI Development](docs/development/slint_gui_development.md)
