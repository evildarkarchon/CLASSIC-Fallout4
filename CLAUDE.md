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
- `CLASSIC_Interface.py` - PySide6 GUI application (main entry point)
- `CLASSIC_ScanLogs.py` - Core log scanning functionality and Command Line Interface
- `CLASSIC_ScanGame.py` - Game file integrity checking

### Setup and Initialization
The application uses a modular architecture with `ClassicLib/SetupCoordinator.py` managing initialization:
- **SetupCoordinator** - Coordinates all setup tasks (file generation, integrity checks, backups)
- **FileGeneration** - Handles YAML configuration file generation
- **GameIntegrity** - Validates game installation and file integrity
- **BackupManager** - Manages automatic game file backups
- **DocumentsChecker** - Validates document folders and INI files
- **PathValidator** - Validates and cleans settings paths

### Core Architecture Pattern
The project uses an **async-first orchestrator pattern** for log scanning:
- `ClassicLib/ScanLog/OrchestratorCore.py` - Async-first implementation
- `ClassicLib/ScanLog/Orchestrator.py` - Sync adapter for backwards compatibility
- Specialized analyzers (FormIDAnalyzer, RecordScanner, PluginAnalyzer) process specific aspects
- MessageHandler abstracts output for both GUI and CLI modes

### Async-First Architecture
The codebase follows an async-first design pattern:
- **Core implementations** are async (e.g., `ScanGameCore`, `FormIDAnalyzerCore`, `FileIOCore`)
- **Sync adapters** provide backwards compatibility using `asyncio.run()`
- **No feature flags** - async is always used internally for better performance
- **Unified file I/O** - All file operations go through `FileIOCore`

### Key Components
1. **MessageHandler** - Central messaging system that routes to GUI dialogs or CLI output
2. **YamlSettingsCache** - Manages all YAML configuration files
3. **FileIOCore** - Unified async-first file I/O operations with automatic encoding detection
4. **Async Pipeline** - Log processing uses async/await for performance
5. **FormID Database** - Identifies mods from crash data

### Async Development Patterns
When working with async code:
```python
# Use FileIOCore for all file operations
from ClassicLib.FileIOCore import FileIOCore

async def process_files():
    io_core = FileIOCore()
    content = await io_core.read_file(path)
    await io_core.write_file(output_path, processed_content)

# Sync adapter usage (for backwards compatibility)
from ClassicLib.FileIOCore import read_file_sync
content = read_file_sync(path)
```

### Testing Patterns
When writing tests:
```python
# Always initialize MessageHandler for tests
@pytest.fixture
def init_message_handler_fixture():
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None

# Test async components
@pytest.mark.asyncio
async def test_async_operation():
    core = ScanGameCore()
    result = await core.check_log_errors(path)
    assert result == expected

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

## Memories
- Output test output to a file to avoid truncation.
- Do not make additions to the `MainWindow` class in `CLASSIC_Interface.py` unless absolutely necessary. Use Mixin classes with TYPE_CHECKING stubs instead.