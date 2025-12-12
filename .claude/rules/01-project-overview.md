# Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides two Python interfaces: GUI (PySide6/Qt) and CLI. A Rust-based TUI (Ratatui) is also available as a separate application.

**Rust Acceleration**: CLASSIC uses Rust for performance-critical operations, achieving 10-150x speedups while maintaining full Python compatibility.

## Quick Start

### Installation & Distribution
- **DO NOT use `pip install`** for normal use (not published to PyPI)
- **Exception**: `uv pip install -e . --force-reinstall` for Rust development only

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
uv run pytest -n auto -m "unit and not slow"  # Quick unit tests
uv run pytest -n auto -m "integration"        # Integration tests
uv run pytest tests/rust_integration/ -v   # Rust integration tests
uv run pytest tests/path/to/test_file.py::test_function -v  # Single test

# Linting
uv run ruff check .
uv run ruff format .

# Build executable (Windows)
uv run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec
```

### Rust Extension Development
```bash
# Method 1: Build wheel (MOST RELIABLE - RECOMMENDED)
# Build individual modules (Manual):
cd rust/python-bindings/classic-yaml-py && maturin build --release --out dist && cd ../../..
uv pip install rust/python-bindings/classic-yaml-py/dist/classic_yaml_py-*.whl --force-reinstall

# Or use rebuild_rust.ps1 (Unified Script):
./rebuild_rust.ps1              # Build all (incremental)
./rebuild_rust.ps1 yaml         # Build specific crate
./rebuild_rust.ps1 -Clean       # Clean build

# Method 2: Editable install (DEVELOPMENT)
uv pip install -e . --force-reinstall

# Verify Rust acceleration
uv run python -c "import classic_yaml; print(f'Rust YAML version: {classic_yaml.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

**Detailed Guide**: See [PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)

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
- **Import**: `import classic_yaml; ops = classic_yaml.RustYamlOperations()`
- **Performance**: 15-30x faster than ruamel.yaml
- **Features**: Multi-document, anchor/alias, insertion order, pure Rust safety
