# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides two Python interfaces: GUI (PySide6/Qt) and CLI. A Rust-based TUI (Ratatui) is also available as a separate application.

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
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall

# Method 2: Editable install (DEVELOPMENT)
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old FIRST
uv pip install -e . --force-reinstall

# Verify Rust acceleration
uv run python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

**📚 Detailed Guide**: See [PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)

## Architecture

### Hybrid Python-Rust Architecture
- **Python**: UI, high-level logic, and coordination in `src/classic/` and `ClassicLib/`
- **Rust**: Three-layer modular architecture delivering 10-150x performance gains
  - **Foundation Layer**: `classic-shared` (runtime, errors, utilities)
  - **Business Logic Layer** (Pure Rust - no PyO3): `-core` crates
  - **Python Bindings Layer** (PyO3 adapters): `-py` crates
  - **Facade Layer**: `classic-core` (re-exports all Python modules)
- **Integration**: PyO3 0.26.0 bindings with native async solution
- **Fallback**: Full Python implementations ensure compatibility
- **Transparent**: Automatic acceleration - no API changes required

**Architecture Rules**:
- **ONE RUNTIME RULE**: Single global Tokio runtime shared across all crates
- **SEPARATION OF CONCERNS**: Business logic in `-core` crates, PyO3 bindings in `-py` crates
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate

**📚 Deep Dive**: See [Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)

### Core Components
- **Entry Points**: `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI)
- **AsyncBridge**: Singleton for async/sync bridging (replaces deprecated AsyncCore)
- **MessageHandler**: Central messaging system for all output modes
- **YamlSettingsCache**: Configuration management with batch loading
- **FileIOCore**: Unified async-first file I/O with Rust acceleration (10x faster)
- **OrchestratorCore**: Async-first log scanning orchestration with Rust components

### Essential Patterns

```python
# Use AsyncBridge for sync contexts
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Transparent Rust acceleration
from ClassicLib.ScanLog.Parser import find_segments  # Uses Rust if available
from ClassicLib.integration.factory import get_parser  # Automatic fallback
```

**📚 Complete Guide**: See [Async Development Guide](docs/development/async_development_guide.md)

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

**📚 Complete Guide**: See [Slint GUI Development](docs/development/slint_gui_development.md)

## Testing Standards

### Test Organization
- **Structure**: Domain-driven directories in `tests/`
- **File Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Markers**: Required - `@pytest.mark.unit`, `.integration`, `.asyncio`, `.slow`, `.gui`, `.performance`, `.rust`

### Critical Rules
1. **NEVER modify production YAML** in tests (use `YAML.TEST` or mocks)
2. **NEVER add backward compatibility** to fix tests (update tests to match new API)
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Test Rust integration** with `@pytest.mark.rust` for components that use acceleration
6. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones

### Testing Guides
See `docs/` for detailed guides:
- `testing/testing_async_bridge.md` - Async/sync mocking
- `testing/testing_global_registry.md` - Singleton isolation
- `testing/testing_yaml_cache.md` - Config testing
- `testing/test_pollution_guide.md` - Master pollution prevention guide

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
8. **API Stability Rules** - Production code maintains backward compatibility
   - Tests are exempt from API stability (always use current APIs)
   - Deprecated code ONLY used in tests or `__init__.py` can be deleted

### Rust Documentation Standards

**CRITICAL**: All new Rust code MUST be fully documented according to Rust documentation standards. Missing documentation warnings are treated as errors.

**Requirements**:
- All `pub struct`, `pub enum`, `pub fn`, `pub mod` require `///` doc comments
- All public struct fields and enum variants require documentation
- Crate-level documentation with `//!` at top of `lib.rs` or `main.rs`
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html)
- Only suppress `missing_docs` for generated code (e.g., Slint UI)

**📚 Complete Guide**: See [Rust Documentation Standards](docs/development/rust_documentation_standards.md) in CLAUDE.md (lines 574-706)

### Common Anti-Patterns to Avoid
- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Production YAML in tests → ✅ `YAML.TEST` or mocks
- ❌ String paths → ✅ `pathlib.Path`
- ❌ Direct print → ✅ MessageHandler
- ❌ Missing type hints → ✅ Complete annotations
- ❌ Manual event loops → ✅ AsyncBridge
- ❌ Deprecated APIs (Python/Rust) → ✅ Use current APIs immediately
- ❌ Multiple Tokio runtimes → ✅ `classic_shared::get_runtime()`

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

## Important Notes
- **Python 3.12+ required**
- **uv** package manager (faster than poetry)
- **Terminal for tests** (VS Code test tool freezes)
- **API compatibility priority** with deprecation warnings (production code only - tests always use current APIs)
- **Rust acceleration** automatic and transparent (10-150x speedups)
- **Native async solution** - no PyO3-asyncio dependency
- **No proactive doc creation** unless requested

## YAML Operations (yaml-rust2)
- **Library**: yaml-rust2 v0.10.4 (YAML 1.2 compliant, pure Rust, owned types)
- **Import**: `from classic_core import yaml; ops = yaml.RustYamlOperations()`
- **Performance**: 15-30x faster than ruamel.yaml
- **Features**: Multi-document, anchor/alias, insertion order, pure Rust safety

## Memories
- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings
- **classic_core import pattern**: Always use `from classic_core import <module>` NOT `from classic_core.<module> import <class>`
- **Workspace modularization complete**: classic-rust renamed to classic-core as thin facade (2025-10-06)
- **ONE RUNTIME RULE**: All Rust crates use `classic_shared::get_runtime()` to share global Tokio runtime
- **PyO3 module registration**: `#[pyclass]` types ONLY export from standalone cdylib modules
- **Standalone module pattern**: Each Rust crate exporting Python classes must have `crate-type = ["cdylib", "rlib"]`
- **GIL handling for parallel work**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in worker threads (PyO3 0.26)
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context
- **Business logic separation** (2025-10-08): ALL new Rust code MUST separate business logic (`-core` crates) from Python bindings (`-py` crates)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
- **Slint AsyncBridge pattern** (2025-10-11): ALWAYS use `AsyncBridge::run_with_ui_update()` for async operations in Slint GUI
- **Rust documentation requirement** (2025-10-23): ALL new Rust code MUST be fully documented. Missing documentation warnings are treated as errors.