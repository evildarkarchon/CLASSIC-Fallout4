# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a Python tool for analyzing Fallout 4 crash logs from Buffout 4 and providing diagnostic information. The project uses async I/O for performance and supports both GUI (PySide6) and CLI interfaces.

## Essential Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=lcov:lcov.info --cov-report=term

# Run specific test file
pytest tests/test_scan_logs.py

# Run by marker (unit, integration, thread, slow)
pytest -m unit
pytest -m "not slow"
```

### Code Quality
```bash
# Lint and auto-fix
ruff check . --fix
ruff format .

# Type checking
mypy .
```

### Building
```bash
# Build GUI executable
pyinstaller CLASSIC.spec

# Build CLI executable  
pyinstaller CLASSIC-CLI.spec
```

### Dependencies
```bash
# Using Poetry (recommended)
poetry install
poetry install --with gui,cli,dev

# Alternative (without Poetry)
python install_requirements.py --all
```

## Architecture Overview

### Core Structure
- **CLASSIC_Main.py**: Entry point, initializes the application
- **CLASSIC_Interface.py**: GUI implementation using PySide6
- **CLASSIC_ScanLogs.py**: Crash log scanning functionality and Command Line Interface.
- **CLASSIC_ScanGame.py**: Game file scanning functionality
- **ClassicLib/**: Core library modules
  - `ScanLog/`: Async log scanning components
  - `ScanGame/`: Game file analysis
  - `Interface/`: GUI components
  - `GlobalRegistry.py`: Centralized configuration registry

### Key Patterns
1. **Async Pipeline**: Heavy use of async/await for I/O operations (aiohttp, aiofiles)
2. **Global Registry**: `ClassicLib/GlobalRegistry.py` manages all configuration state
3. **Message Handler**: Abstracted messaging system for GUI/CLI compatibility
4. **YAML Configuration**: Settings and data stored in YAML format with caching
5. **FormID Database**: Cached database for fast mod lookups

### Important Considerations
- **Python 3.12+** required
- **Type hints** used throughout - maintain them
- **Line length**: 140 characters (ruff/black config)
- **Test markers**: unit, integration, thread, slow
- **Main branch**: classic-next
- The project uses both GUI (PySide6) and CLI (tqdm) interfaces - ensure compatibility
- FormID database operations are performance-critical - use caching
- Async operations should use the utilities in `ClassicLib/AsyncUtil.py`

### Development Workflow
1. Make changes following existing code patterns
2. Run `ruff check . --fix` and `ruff format .`
3. Run `mypy .` to check types
4. Run `pytest` to ensure tests pass
5. Build with `pyinstaller` when ready to test executables

