# GitHub Copilot Instructions for CLASSIC-Fallout4

## Project Overview

CLASSIC is a hybrid Python-Rust desktop application for analyzing Bethesda game crash logs (Fallout 4/Skyrim). It provides three interfaces: GUI (PySide6), TUI (Textual), and CLI. The project achieves 10-150x performance gains through strategic Rust acceleration while maintaining full Python compatibility.

## Architecture Patterns

### Hybrid Python-Rust Design
- **Python Layer**: UI logic, coordination, high-level operations in `ClassicLib/`
- **Rust Layer**: Performance-critical operations with automatic fallback
- **Integration**: Transparent acceleration via `ClassicLib.integration.factory` module
- **Fallback**: Full Python implementations ensure compatibility when Rust unavailable

### Rust Architecture (Separated Business Logic - 2025)
```
Business Logic (*-core crates): Pure Rust, rlib only, NO PyO3
  ├── classic-yaml-core, classic-database-core, classic-file-io-core
  └── classic-scanlog-core, classic-config-core

Python Bindings (*-py crates): Thin PyO3 adapters, cdylib output
  ├── classic-yaml-py, classic-database-py, classic-file-io-py
  └── classic-scanlog-py, classic-config-py

Facade: classic-core (re-exports all Python modules)
```

**Critical Rule**: Business logic MUST be in `-core` crates (no PyO3), bindings MUST be in `-py` crates (thin adapters only).

### Async Patterns
- **AsyncBridge**: Singleton for sync/async bridging - use `AsyncBridge.get_instance().run_async()`
- **Native async solution**: No PyO3-asyncio dependency
- **ONE RUNTIME RULE**: All Rust crates share global Tokio runtime via `classic_shared::get_runtime()`

## Development Workflow

### Environment Setup
```bash
# Clone and setup
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
uv sync --all-extras

# Run application
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_TUI.py        # TUI  
uv run python CLASSIC_ScanLogs.py   # CLI
```

### Rust Development
```bash
# Method 1: Build wheel (MOST RELIABLE)
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall

# Method 2: Editable install (development)
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old first
uv pip install -e . --force-reinstall

# Verify acceleration
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

### Testing
```bash
# Run tests (use terminal, not VS Code test tool)
uv run pytest -n auto               # All tests, parallel
uv run pytest -n 4 -m "unit and not slow"  # Quick unit tests
uv run pytest tests/rust_integration/ -v   # Rust integration tests
```

## Code Quality Standards

### Development Rules
1. **No print()** - Use `MessageHandler` (`msg_info()`, `msg_warning()`, `msg_error()`)
2. **Use pathlib.Path** - Never string paths
3. **Async-first** - Use `AsyncBridge` for sync contexts
4. **Type annotations** - Complete Python 3.12+ syntax required
5. **Test markers** - All tests need `@pytest.mark.unit/.integration/.rust` etc.
6. **Deprecated APIs = ERRORS** - Zero tolerance for deprecation warnings

### Common Patterns
```python
# Rust acceleration (automatic with fallback)
from ClassicLib.integration.factory import get_parser, get_formid_analyzer
parser = get_parser()  # Uses RustLogParser if available

# File I/O
from ClassicLib.FileIOCore import FileIOCore
io_core = FileIOCore()
content = await io_core.read_file(path)

# Settings
from ClassicLib.YamlSettingsCache import yaml_cache
values = yaml_cache.batch_get_settings([
    (str, YAML.Settings, "key1"),
    (bool, YAML.Settings, "key2")
])

# Messaging
from ClassicLib.MessageHandler import msg_info, msg_warning, msg_error
msg_info("Operation completed")
```

### Anti-Patterns to Avoid
- ❌ `asyncio.run()` in sync contexts → ✅ `AsyncBridge.run_async()`
- ❌ Production YAML in tests → ✅ `YAML.TEST` or mocks
- ❌ String paths → ✅ `pathlib.Path`
- ❌ Missing test markers → ✅ `@pytest.mark.unit` etc.
- ❌ Deprecated APIs → ✅ Update to current APIs immediately

## Project Structure

### Entry Points
- `CLASSIC_Interface.py` - GUI (PySide6/Qt)
- `CLASSIC_TUI.py` - Terminal UI (Textual)
- `CLASSIC_ScanLogs.py` - CLI scanner

### Core Components (`ClassicLib/`)
- **AsyncBridge** - Sync/async coordination
- **MessageHandler/** - Central messaging system
- **integration/** - Rust acceleration with Python fallback
- **Interface/** - GUI components (modular mixins)
- **ScanLog/** - Log parsing with Rust acceleration
- **FileIO/** - File operations with encoding detection
- **TUI/** - Terminal UI screens and widgets

### Configuration
- **uv** package manager (not pip/poetry)
- **Python 3.12+** required
- **Dependencies**: PySide6, Textual, aiohttp, ruamel-yaml
- **Build**: PyInstaller for executables

## Testing Guidelines

### Test Organization
- **Domain directories**: `tests/async_resources/`, `tests/io/`, `tests/rust_integration/`
- **File naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Required markers**: `@pytest.mark.unit`, `.integration`, `.rust`, `.slow`, `.gui`

### Critical Rules
1. **NEVER modify production YAML** - Use `YAML.TEST` or mocks
2. **NEVER add backward compatibility** to fix tests - Update tests to current API
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Test Rust integration** with `@pytest.mark.rust` for accelerated components

## Performance Monitoring

### Rust Status Checking
```python
# Check component status
from ClassicLib.integration.status import get_rust_component_status, print_rust_status
status = get_rust_component_status()
if status["acceleration_active"]:
    print(f"🚀 {status['active_count']}/{status['total_count']} components accelerated")

# Force Python fallback (debugging)
import os
os.environ["CLASSIC_DISABLE_RUST"] = "1"
```

### Performance Gains
| Component | Python Time | Rust Time | Speedup |
|-----------|-------------|-----------|---------|
| Log Parsing | 2-3 seconds | 200-300ms | 10x |
| FormID Analysis | 250ms/1000 IDs | 10ms/1000 IDs | 25x |
| Pattern Matching | 100ms/scan | 5ms/scan | 20x |
| File I/O | 50ms/file | 5ms/file | 10x |

## Build and Distribution

### Development Build
```bash
# Build Rust components
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall

# Build executable
uv run pyinstaller --clean .\CLASSIC.spec
```

### Distribution Methods
1. **PyInstaller executables** - Primary distribution (no Python needed)
2. **uvx from GitHub** - `uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic`
3. **NOT pip install** - Not published to PyPI

## Key Files to Understand
- `ClassicLib/AsyncBridge.py` - Async/sync coordination patterns
- `ClassicLib/integration/factory.py` - Rust acceleration factory
- `ClassicLib/MessageHandler/` - Centralized messaging
- `build_all.ps1` - Complete build workflow
- `rebuild_rust.ps1` - Rust build and install script
- `pyproject.toml` - Project configuration and entry points
- `Cargo.toml` - Rust workspace with separated architecture