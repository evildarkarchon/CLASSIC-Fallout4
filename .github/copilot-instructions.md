# CLASSIC AI Development Guide

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a **hybrid Python-Rust desktop application** that analyzes crash logs from Bethesda games (Fallout 4, Skyrim). It provides GUI (PySide6), CLI, and TUI interfaces with **10-150x performance gains** from Rust acceleration.

**Critical Context**: This is production code with end users. All changes must maintain backward compatibility and API stability.

## Core Architecture

### Hybrid Python-Rust Design

```
┌─────────────────────────────────────────────────────┐
│ Python Layer (ClassicLib/, src/)                    │
│ • UI (GUI/CLI/TUI) and high-level coordination      │
│ • Full Python fallbacks for all Rust components     │
└─────────────────────────────────────────────────────┘
                       ↕ PyO3 Bindings
┌─────────────────────────────────────────────────────┐
│ Rust Layer (rust/)                                  │
│ • foundation/      - Runtime, errors, shared utils  │
│ • business-logic/  - Pure Rust (-core crates)       │
│ • python-bindings/ - PyO3 adapters (-py crates)     │
│ • ui-applications/ - Native CLI/TUI/GUI apps        │
└─────────────────────────────────────────────────────┘
```

**ONE RUNTIME RULE**: All Rust code shares a single Tokio runtime via `classic_shared::get_runtime()`. Never create multiple runtimes.

**SEPARATION OF CONCERNS**: Business logic in `-core` crates (pure Rust), Python bindings in `-py` crates (PyO3). Never mix them.

### Entry Points
- **GUI**: `CLASSIC_Interface.py` - Uses AsyncBridge for Qt thread safety
- **CLI**: `CLASSIC_ScanLogs.py` - Async-first with single `asyncio.run()` at entry
- **Game Scanner**: `CLASSIC_ScanGame.py` - File integrity checker

### Singleton Architecture

Three critical singletons require careful handling:

1. **GlobalRegistry** (`ClassicLib.GlobalRegistry`) - Thread-safe object sharing across modules
2. **YamlSettingsCache** (`ClassicLib.YamlSettingsCache`) - Configuration with batch loading
3. **MessageHandler** (`ClassicLib.MessageHandler`) - Centralized output to GUI/CLI/logs

**Testing Rule**: Always clear singletons between tests to prevent pollution:
```python
@pytest.fixture(autouse=True)
def isolate_global_state():
    yield
    GlobalRegistry._registry.clear()
    MessageHandler.reset()
    YamlSettingsCache._cache.clear()
```

## Development Workflows

### Setup & Installation

```bash
# First-time setup (installs uv automatically)
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
uv sync --all-extras  # Creates .venv and installs everything

# Running the application
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing (ALWAYS use terminal, not VS Code test runner - it freezes)
uv run pytest -n auto               # All tests, parallel
uv run pytest -n 4 -m "unit and not slow"  # Fast unit tests
uv run pytest -n 4 -m "integration"        # Integration tests
```

### Building Executables

```bash
# Build with PyInstaller (Windows)
uv run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec

# Or use VS Code Run & Debug (Ctrl+Shift+D)
```

### Rust Development

```powershell
# Rebuild all Rust modules (use PowerShell)
./rebuild_rust.ps1

# Build individual module (example: YAML)
cd rust/python-bindings/classic-yaml-py
maturin build --release --out dist
uv pip install dist/classic_yaml_py-*.whl --force-reinstall
cd ../../..

# Verify Rust acceleration
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

**Adding New Rust Crates**:
1. **Business Logic**: Create in `rust/business-logic/classic-newfeature-core/`
   - `Cargo.toml`: `crate-type = ["rlib"]`
   - Pure Rust, NO PyO3 dependencies
2. **Python Bindings**: Create in `rust/python-bindings/classic-newfeature-py/`
   - `Cargo.toml`: `crate-type = ["cdylib", "rlib"]`, add `pyo3.workspace = true`
   - Import from `-core` crate, wrap with PyO3
3. **Update**: `rust/Cargo.toml` workspace members, `rebuild_rust.ps1`, `build_all.ps1`

## Critical Patterns & Conventions

### Async/Sync Bridge Pattern

**GUI Mode** (Qt threads): Use AsyncBridge
```python
from ClassicLib.AsyncBridge import AsyncBridge

# In QThread or slot handlers
bridge = AsyncBridge.get_instance()
result = bridge.run_async(my_async_function())
```

**CLI/TUI Mode** (async-first): Use native async
```python
async def main():
    result = await my_async_function()  # Direct async

if __name__ == "__main__":
    asyncio.run(main())  # Single event loop at entry
```

**Testing**: Mock AsyncBridge, not underlying async functions
```python
with patch("module.AsyncBridge") as mock_bridge_class:
    mock_bridge = MagicMock()
    mock_bridge_class.get_instance.return_value = mock_bridge
    mock_bridge.run_async.return_value = "expected"
    # Test sync wrapper
```

### Rust Integration Pattern

```python
# Automatic fallback with factory
from ClassicLib.integration.factory import get_parser

parser = get_parser()  # Uses Rust if available, Python otherwise
result = parser.find_segments(data, ...)  # Identical interface

# Direct import for performance-critical code
try:
    import classic_yaml
    yaml_ops = classic_yaml.RustYamlOperations()
    logger.debug("Using Rust YAML (15-30x faster)")
except ImportError:
    # Fall back to Python (ruamel.yaml)
    yaml_ops = None
```

### File I/O Pattern

```python
from ClassicLib.integration.factory import get_file_io

# Singleton with Rust acceleration (10-20x faster)
file_io = get_file_io(encoding="utf-8", errors="ignore")
content = await file_io.read_file_async(path)  # Async preferred
content = file_io.read_file(path)              # Sync fallback
```

### Message Handling

**Never use `print()`** - Always use MessageHandler:
```python
from ClassicLib.MessageHandler import msg_info, msg_warning, msg_error

msg_info("Processing complete")      # Logs + GUI/CLI display
msg_warning("Missing optional file") # Yellow warning
msg_error("Fatal error occurred")    # Red error
```

### YAML Settings

```python
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Read settings (cached)
fcx_mode = classic_settings(bool, "FCX Mode")
scan_path = classic_settings(str, "SCAN Custom Path")

# Write settings (updates cache + file)
yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", True)

# Batch loading for performance
keys = ["FCX Mode", "Show FormID Values", "Move Unsolved Logs"]
settings = YamlSettingsCache.batch_load(keys)
```

### Path Handling

```python
from pathlib import Path

# ALWAYS use pathlib.Path, never string paths
game_path = Path("C:/Games/Fallout4")
log_file = game_path / "Crash Logs" / "crash-2024-11-01.log"

# Rust acceleration available for validation
from ClassicLib.integration.factory import get_path_validator
if validator := get_path_validator():
    is_valid = validator.is_valid_path(str(path))
```

## Testing Standards

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Multi-component tests
├── rust_integration/  # Rust acceleration tests
└── stress/           # Performance tests
```

### Required Markers

```python
@pytest.mark.unit           # Fast, isolated
@pytest.mark.integration    # Multi-component
@pytest.mark.asyncio        # Uses async/await
@pytest.mark.slow           # >1 second
@pytest.mark.gui            # Requires Qt
@pytest.mark.rust           # Tests Rust integration
```

### Critical Rules

1. **NEVER modify production YAML** - Use `YAML.TEST` or mocks
2. **NEVER add backward compatibility to fix tests** - Update tests to match new API
3. **Always clear singletons** between tests
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Tests are exempt from API stability** - Always use current APIs

### Test Pollution Prevention

```python
@pytest.fixture(autouse=True)
def cleanup_environment(tmp_path, monkeypatch):
    """Isolate test environment."""
    # Redirect all file operations to tmp_path
    monkeypatch.setattr(GlobalRegistry, "get_local_dir", lambda: tmp_path)
    
    yield
    
    # Clean up singletons
    GlobalRegistry._registry.clear()
    YamlSettingsCache._cache.clear()
    MessageHandler.reset()
```

## Code Quality Requirements

### Documentation
- **All code requires Google-style docstrings** (treat missing docs as errors)
- **Modules**: Brief summary and overview
- **Classes**: Purpose, attributes, examples
- **Functions**: Args, Returns, Raises, Examples for complex logic

```python
def scan_log_async(log_path: Path, *, max_errors: int | None = None) -> ScanResult:
    """Asynchronously scan a crash log file.

    This function performs async I/O to read and parse crash logs
    without blocking the event loop.

    Args:
        log_path: Path to the crash log file to scan.
        max_errors: Maximum errors to collect (None = unlimited).

    Returns:
        A ScanResult object containing parsed diagnostic information.

    Raises:
        FileNotFoundError: If log_path does not exist.
        asyncio.TimeoutError: If scan exceeds timeout.

    Example:
        >>> result = await scan_log_async(Path("crash.log"))
        >>> print(f"Found {result.error_count} errors")
    """
```

### Rust Documentation
- **All public items require `///` doc comments**
- **Missing docs = compilation error**
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html)

```rust
/// Parses crash log segments and extracts version information.
///
/// # Arguments
///
/// * `crash_data` - Lines of crash log content
/// * `crashgen_name` - Name of the crash logger (e.g., "Buffout 4")
///
/// # Returns
///
/// A tuple of (game_version, crashgen_version, error_message, segments)
pub fn find_segments(
    crash_data: &[String],
    crashgen_name: &str,
) -> (String, String, String, Vec<Vec<String>>)
```

### Code Structure
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** - Use dict mapping or extract methods
- **Complete type annotations** (Python 3.12+ syntax)
- **UTF-8 encoding** with `errors="ignore"` for all file operations

### Anti-Patterns to Avoid

❌ `asyncio.run()` in production CLI loop → ✅ Single `asyncio.run()` at entry point  
❌ Production YAML in tests → ✅ `YAML.TEST` or mocks  
❌ String paths → ✅ `pathlib.Path`  
❌ Direct `print()` → ✅ MessageHandler functions  
❌ Missing type hints → ✅ Complete annotations  
❌ Missing docstrings → ✅ Google-style docs  
❌ Multiple Tokio runtimes → ✅ `classic_shared::get_runtime()`  
❌ Deprecated APIs in production → ✅ Use current APIs immediately  

## Project-Specific Knowledge

### Dependency Management
- **Package manager**: `uv` (10-100x faster than pip/poetry)
- **Never use `pip install`** - Use `uv pip install` or `uv sync`
- **Updating deps**: `uv lock --upgrade` or `uv lock --upgrade-package pyside6`

### Build System
- **PyInstaller** for executables (see `CLASSIC.spec`)
- **UPX compression** optional (smaller files, slower startup)
- **VS Code integration**: Run & Debug sidebar (Ctrl+Shift+D)

### Performance Monitoring

```python
from ClassicLib.integration.factory import get_perf_monitor

# Track Rust acceleration usage
perf = get_perf_monitor()
perf.start_operation("yaml_parse")
# ... operation ...
perf.end_operation("yaml_parse")
metrics = perf.get_metrics()  # Check Rust vs Python usage
```

### FCX Mode (Read-Only Configuration Checker)
FCX mode **detects** configuration issues but **never modifies** files. All detected issues are reported with current vs. recommended values. Use detection functions only:
- `detect_ini_issue_async()` - Detect single issue
- `detect_all_ini_issues_async()` - Detect all issues
- Auto-fix functions removed (2025-10-29)

### Available Rust Modules (Direct Imports)

```python
import classic_yaml          # YAML operations (15-30x faster)
import classic_database      # Database pool (25x faster)
import classic_file_io       # File I/O (10-20x faster)
import classic_scanlog       # Log parsing (150x faster)
import classic_config        # Configuration management
import classic_constants     # Game constants and enums
import classic_version       # Version parsing and comparison
import classic_resource      # Resource file detection
import classic_xse           # Script Extender detection
import classic_web           # URL validation, user agents
```

## Documentation References

### Core Guides (docs/development/)
- `async_development_guide.md` - Async patterns and AsyncBridge usage
- `rust_workspace_architecture.md` - Rust crate structure and dependencies
- `pyo3_integration_patterns.md` - PyO3 module registration and troubleshooting
- `slint_gui_development.md` - Slint GUI patterns (native Rust GUI)

### Testing Guides (docs/testing/)
- `test_pollution_guide.md` - Master guide for preventing test pollution
- `testing_async_bridge.md` - Mocking async/sync patterns
- `testing_global_registry.md` - Singleton isolation
- `testing_yaml_cache.md` - Configuration testing

### Complete Documentation
- `docs/RUST_DOCUMENTATION_INDEX.md` - Complete index of all Rust docs
- `CLAUDE.md` - Comprehensive AI development guide (this is the source!)

## Quick Reference

### Common Commands
```bash
uv sync --all-extras              # Install deps
uv run python CLASSIC_Interface.py  # Run GUI
uv run pytest -n auto             # Run tests
./rebuild_rust.ps1                # Rebuild Rust
uv lock --upgrade                 # Update deps
```

### Environment Variables
- `CLASSIC_DISABLE_RUST=1` - Disable Rust acceleration for testing

### VS Code Extensions (Recommended)
Search `@recommended` in Extensions sidebar for project-specific extensions:
- Ruff (linter/formatter)
- Pyright (type checker)
- rust-analyzer (Rust LSP)
- Even Better TOML
- Maturin (Rust-Python builds)

## When in Doubt

1. **Check CLAUDE.md first** - Comprehensive patterns and anti-patterns
2. **Look at existing code** - Patterns are consistent across the codebase
3. **Test in terminal** - VS Code test runner freezes for async tests
4. **Verify Rust acceleration** - Use `print_rust_status()` to confirm modules loaded
5. **Read the docs** - Extensive guides in `docs/` directory

---

**Remember**: Production code with real users. Maintain backward compatibility, write comprehensive tests, and document everything.
