# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a Python desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It uses PySide6 for the GUI interface and implements an async orchestrator pattern for efficient log processing.

## Essential Commands

### Development
```bash
# Install dependencies
poetry install

# Run the application
python CLASSIC_Interface.py                  # GUI mode
python CLASSIC_ScanLogs.py           # CLI mode

# Run tests
python -m pytest tests/ -v              # All tests with verbose output
python -m pytest tests/ -q              # Quick run with summary only
python -m pytest tests/test_crash_log_processing.py -v  # Specific test file

# Build executable (Windows)
pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\CLASSIC.spec
```

### Linting and Type Checking
```bash
# Run Ruff linter
ruff check .
ruff format .

# Type checking
mypy .
pyright
```

## Architecture Overview

### Entry Points
- `CLASSIC_Main.py` - Initial setup and startup functions
- `CLASSIC_Interface.py` - PySide6 GUI application
- `CLASSIC_ScanLogs.py` - Core log scanning functionality and Command Line Interface
- `CLASSIC_ScanGame.py` - Game file integrity checking

### Core Architecture Pattern
The project uses an **orchestrator pattern** for log scanning:
- `ClassicLib/ScanLog/Orchestrator.py` coordinates async components
- Specialized analyzers (FormIDAnalyzer, RecordScanner, PluginAnalyzer) process specific aspects
- MessageHandler abstracts output for both GUI and CLI modes

### Key Components
1. **MessageHandler** - Central messaging system that routes to GUI dialogs or CLI output
2. **YamlSettingsCache** - Manages all YAML configuration files
3. **Async Pipeline** - Log processing uses async/await for performance
4. **FormID Database** - Identifies mods from crash data

### Testing Patterns
When writing tests:
```python
# Always initialize MessageHandler for tests
@pytest.fixture
def init_message_handler_fixture():
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None

# Access components through orchestrator
scanner = ClassicScanLogs()
if hasattr(scanner.orchestrator, '_formid_analyzer'):
    scanner.orchestrator._formid_analyzer.formid_match(formids, plugins, report)
```

## Important Notes

1. **Python 3.12+ Required** - Uses modern Python features
2. **Async Architecture** - Heavy use of asyncio for performance
3. **GUI Framework** - PySide6 (Qt) for all UI components
4. **Build System** - PyInstaller with custom spec file for Windows executables
5. **Test Coverage** - Comprehensive test suite (62 tests, 100% passing)
6. **Configuration** - YAML files in `CLASSIC Data/` for settings and mod databases

## File Organization
- Main scripts at root level (CLASSIC_*.py)
- Core library in `ClassicLib/` with modular components
- Tests in `tests/` directory
- Sample crash logs in `Crash Logs/`
- Configuration and assets in `CLASSIC Data/`
- Built executables in `Release/`

## Development Workflow
1. Changes should maintain the modular architecture
2. Use MessageHandler for all user communication
3. Follow async patterns in ScanLog components
4. Write tests for new functionality
5. Run linter and type checker before committing
