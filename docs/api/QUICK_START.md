# CLASSIC Quick Start Guide

> Get up and running with CLASSIC development in 5 minutes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running CLASSIC](#running-classic)
4. [Development Workflow](#development-workflow)
5. [Common Tasks](#common-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **uv** - Fast Python package manager
- **Git** - Version control

### Optional (for Rust acceleration)

- **Rust 1.75+** - [Install via rustup](https://rustup.rs/)
- **maturin** - Python/Rust build tool

### Install uv

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
```

### 2. Install Dependencies

```bash
# Install all dependencies including dev tools
uv sync --all-extras
```

### 3. Build Rust Extensions (Optional but Recommended)

```powershell
# Windows PowerShell - Build all Rust modules
./rebuild_rust.ps1

# Or build specific modules
./rebuild_rust.ps1 yaml
./rebuild_rust.ps1 scanlog
```

### 4. Verify Installation

```bash
# Check Python environment
uv run python -c "import ClassicLib; print('ClassicLib imported successfully')"

# Check Rust acceleration
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

---

## Running CLASSIC

### GUI Mode

```bash
uv run python CLASSIC_Interface.py
```

### CLI Mode

```bash
# Basic scan
uv run python CLASSIC_ScanLogs.py

# With options
uv run python CLASSIC_ScanLogs.py --fcx-mode --show-fid-values
uv run python CLASSIC_ScanLogs.py --scan-path "C:\CrashLogs" --simplify-logs
```

### Game Scanner

```bash
uv run python CLASSIC_ScanGame.py
```

---

## Development Workflow

### Running Tests

```bash
# All tests (parallel)
uv run pytest -n auto

# Quick unit tests only
uv run pytest -n auto -m "unit and not slow"

# Integration tests
uv run pytest -n auto -m "integration"

# Rust integration tests
uv run pytest tests/rust_integration/ -v

# Single test file
uv run pytest tests/path/to/test_file.py -v

# Single test function
uv run pytest tests/path/to/test_file.py::test_function -v
```

### Linting and Formatting

```bash
# Check code style
uv run ruff check .

# Auto-format code
uv run ruff format .

# Type checking
uv run mypy ClassicLib
```

### Rust Development

```bash
# Build all Rust crates
cd rust
cargo build --release

# Run Rust tests
cargo test --workspace

# Check Rust linting
cargo clippy --workspace -- -D warnings

# Format Rust code
cargo fmt --all
```

---

## Common Tasks

### 1. Add a New YAML Setting

```python
from ClassicLib.YamlSettings import yaml_settings, classic_settings
from ClassicLib.Constants import YAML

# Read a setting
version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
fcx_mode = classic_settings(bool, "FCX Mode")

# Write a setting
yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.My New Setting", True)
```

### 2. Output Messages

```python
from ClassicLib.MessageHandler import (
    msg_info, msg_warning, msg_error, msg_debug, msg_success,
    msg_progress_context
)

# Simple messages
msg_info("Processing started...")
msg_warning("Plugin may be outdated")
msg_error("Failed to parse log", details="Line 42: Invalid format")
msg_success("Analysis complete!")

# Progress tracking
with msg_progress_context("Analyzing logs", total=100) as progress:
    for i in range(100):
        do_work()
        progress.update(1)
```

### 3. Use AsyncBridge (GUI Only)

```python
from ClassicLib.AsyncBridge import AsyncBridge, run_async

# In Qt worker threads
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Convenience function
result = run_async(async_function())

# With timeout
result = bridge.run_async_with_timeout(long_operation(), timeout=30.0)
```

### 4. Use GlobalRegistry

```python
from ClassicLib import GlobalRegistry
from ClassicLib.GlobalRegistry import Keys

# Register a value
GlobalRegistry.register(Keys.GAME_PATH, Path("/path/to/game"))

# Get a value
game_path = GlobalRegistry.get(Keys.GAME_PATH)

# Check mode
if GlobalRegistry.is_gui_mode():
    # GUI-specific code
    pass
```

### 5. Check Rust Acceleration

```python
from ClassicLib import RUST_YAML_AVAILABLE, RUST_SETTINGS_AVAILABLE
from ClassicLib.integration.status import print_rust_status

# Check individual components
if RUST_YAML_AVAILABLE:
    print("Rust YAML acceleration active (15-30x faster)")

# Print full status
print_rust_status()
```

### 6. Create a Test

```python
# tests/my_module/test_my_feature_unit.py
import pytest
from ClassicLib import msg_info

@pytest.mark.unit
def test_my_feature():
    """Test description."""
    result = my_function()
    assert result == expected

@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_feature():
    """Test async function."""
    result = await async_function()
    assert result is not None

@pytest.mark.integration
def test_with_files(tmp_path):
    """Integration test with file I/O."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # ... test logic
```

---

## Troubleshooting

### Python Issues

#### "Module not found" errors

```bash
# Reinstall dependencies
uv sync --all-extras --reinstall
```

#### "Rust module not available"

```bash
# Rebuild Rust extensions
./rebuild_rust.ps1

# Or with pip install
uv pip install -e . --force-reinstall
```

### Rust Issues

#### Build failures

```bash
# Clean and rebuild
cd rust
cargo clean
cargo build --release
```

#### Linking errors on Windows

```bash
# Install Visual Studio Build Tools
# Then restart terminal and rebuild
./rebuild_rust.ps1 -Clean
```

### Test Issues

#### Tests freeze

Always run tests from terminal, not VS Code test tool:

```bash
uv run pytest -n auto -x
```

#### Singleton pollution between tests

```python
# Use fixture for cleanup
@pytest.fixture(autouse=True)
def clean_state():
    from ClassicLib import GlobalRegistry
    from ClassicLib.MessageHandler import _reset_handler
    GlobalRegistry.clear()
    _reset_handler()
    yield
    GlobalRegistry.clear()
```

### Common Error Messages

| Error | Solution |
|-------|----------|
| `RuntimeError: Cannot use AsyncBridge.run_async() from async context` | Use `await` directly instead of `run_async()` |
| `TypeError: Registry key must be a string` | Pass string key to GlobalRegistry |
| `RuntimeError: GlobalRegistry.clear() only allowed in testing` | Only call `clear()` in pytest fixtures |

---

## Next Steps

- Read the [API Reference](API_REFERENCE.md) for complete API documentation
- Study the [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md) for system design
- Check [Testing Guide](../testing/TESTING_GUIDE_INDEX.md) for testing best practices
- Review [Async Development Guide](../development/async_development_guide.md) for async patterns

---

## Getting Help

- Check existing [documentation](../README.md)
- Search [GitHub Issues](https://github.com/evildarkarchon/CLASSIC-Fallout4/issues)
- Review [.claude/rules/](../../.claude/rules/) for project standards

---

*Last updated: December 2025*
