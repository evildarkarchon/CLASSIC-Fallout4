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
cd classic-rust
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall

# Method 2: Editable install (DEVELOPMENT)
cd classic-rust
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old FIRST
uv pip install -e . --force-reinstall

# Verify Rust acceleration is working
python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"
python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"

# Build Rust without installing (for testing)
cd classic-rust
cargo build --release
cargo test
```

## Architecture

### Hybrid Python-Rust Architecture
- **Python**: UI, high-level logic, and coordination in `src/classic/` and `ClassicLib/`
- **Rust**: CPU-intensive operations in `classic-rust/src/` with 10-150x performance gains
- **Integration**: PyO3 bindings with native async solution (no PyO3-asyncio dependency)
- **Fallback**: Full Python implementations ensure compatibility when Rust unavailable
- **Transparent**: Automatic acceleration - no API changes required

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
CLASSIC uses a native async solution that's more reliable and performant:
```rust
// Single global Tokio runtime
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create Tokio runtime")
});

// Sync API to Python, async internally
#[pyfunction]
fn process_data(data: String) -> PyResult<String> {
    RUNTIME.block_on(async move {
        // Full async Rust operations here
        async_operation(data).await
    })
}
```

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

### Common Anti-Patterns to Avoid
- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Production YAML in tests → ✅ `YAML.TEST` or mocks
- ❌ String paths → ✅ `pathlib.Path`
- ❌ Direct print → ✅ MessageHandler
- ❌ Missing type hints → ✅ Complete annotations
- ❌ Manual event loops → ✅ AsyncBridge

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

### Common Issues
1. **Module not found**: Use build method 1 (recommended) to update .pyd
   ```bash
   cd classic-rust && maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

2. **Old .pyd loads**: Remove from site-packages before editable install
   ```bash
   rm .venv/Lib/site-packages/classic_core.pyd
   uv pip install -e classic-rust --force-reinstall
   ```

3. **PyO3 conversion errors**: Use direct attribute access or pre-convert
   - Rust components expect specific data types
   - Check logs for conversion errors

4. **Changes not reflected**: Use `--force-reinstall` and verify timestamp
   ```python
   import classic_core
   print(f"Version: {classic_core.__version__}")
   ```

5. **Performance not improving**: Check component status
   ```python
   from ClassicLib.integration.status import RUST_AVAILABLE
   print(f"Available components: {RUST_AVAILABLE}")
   ```

6. **Build failures**: Common causes and solutions
   ```bash
   # Update Rust toolchain
   rustup update

   # Clear Cargo cache
   cargo clean

   # Reinstall maturin
   uv pip install --upgrade maturin
   ```

## Pre-commit Hooks
```bash
uv run pre-commit install                    # Install hooks
uv run pre-commit run --all-files           # Run manually
```

## Important Notes
- **Python 3.12+ required**
- **uv** package manager (faster than poetry)
- **Terminal for tests** (VS Code test tool freezes)
- **API compatibility priority** with deprecation warnings
- **Rust acceleration** automatic and transparent (10-150x speedups)
- **Native async solution** - no PyO3-asyncio dependency
- **No proactive doc creation** unless requested

## Rust Documentation
For comprehensive Rust documentation, see:
- **[Rust Documentation Index](docs/RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust docs
- **[Rust Usage Guide](docs/rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](docs/performance_monitoring.md)** - Monitor Rust performance
- **[Troubleshooting Guide](docs/troubleshooting_rust.md)** - Debug Rust issues
- **[Development Guide](docs/development_with_rust.md)** - Develop with Rust components
- **[Migration Plan](RUST_MIGRATION_PLAN.md)** - Complete migration strategy

## Memories
- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings
