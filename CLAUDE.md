# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a Python desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides three different interfaces:
- **GUI**: PySide6 (Qt) based graphical interface
- **TUI**: Textual-based terminal user interface (rich terminal UI)
- **CLI**: Command-line interface for automation

## Essential Commands

### Development
```bash
# Install dependencies
poetry install

# Run the application
poetry run python CLASSIC_Interface.py          # GUI mode
poetry run python CLASSIC_TUI.py                # TUI mode (Terminal UI)
poetry run python CLASSIC_ScanLogs.py           # CLI mode

# Run tests (use terminal, VS Code test tool has freezing issues)
poetry run python -m pytest tests/ -n 4 -v              # All tests with verbose output
poetry run python -m pytest tests/ -n 4 -q              # Quick run with summary only
poetry run python -m pytest tests/test_crash_log_processing.py -n 4 -v  # Specific test file

# Performance-optimized test execution
poetry run python -m pytest -n auto                # Parallel execution (auto-detect CPU cores)
poetry run python -m pytest -n 4                   # Parallel execution with 4 workers
poetry run python -m pytest -n 4 -m "unit and not slow" --maxfail=3     # Quick feedback (unit tests only)
poetry run python -m pytest -n 4 -m "integration and not slow"          # Integration tests
poetry run python -m pytest -n 4 -m "not performance"   # All tests except performance regression tests
poetry run python -m pytest -n 4 -m "performance"       # Performance regression tests only
poetry run python -m pytest -n 4 -m "gui"               # GUI-dependent tests only
poetry run python -m pytest -n 4 -m "async_test"        # Async pattern tests only

# Build executable (Windows)
poetry run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec
```

### Linting and Type Checking
```bash
# Run Ruff linter
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy .
poetry run pyright
```

## Architecture Overview

### Entry Points
- `CLASSIC_Interface.py` - PySide6 GUI application (main entry point)
- `CLASSIC_TUI.py` - Textual-based Terminal UI application
- `CLASSIC_ScanLogs.py` - Core log scanning functionality and CLI
- `CLASSIC_ScanGame.py` - Game file integrity checking

### Setup and Initialization
The application uses a modular architecture with `ClassicLib/SetupCoordinator.py` managing initialization:
- **SetupCoordinator** - Coordinates all setup tasks (file generation, integrity checks, backups)
- **FileGeneration** - Handles YAML configuration file generation (now with async support)
- **GameIntegrity** - Validates game installation and file integrity
- **BackupManager** - Manages automatic game file backups
- **DocumentsChecker** - Validates document folders and INI files
- **PathValidator** - Validates and cleans settings paths

### Core Architecture Pattern
The project uses an **async-first orchestrator pattern** for log scanning:
- `ClassicLib/ScanLog/OrchestratorCore.py` - Async-first implementation
- `ClassicLib/ScanLog/AsyncScanOrchestrator.py` - High-level async orchestrator
- Specialized analyzers (FormIDAnalyzer, RecordScanner, PluginAnalyzer) process specific aspects
- MessageHandler abstracts output for GUI, TUI, and CLI modes

### Async-First Architecture
The codebase follows an async-first design pattern:
- **Core implementations** are async (e.g., `ScanGameCore`, `FormIDAnalyzerCore`, `FileIOCore`)
- **Sync adapters** provide backwards compatibility using `asyncio.run()`
- **AsyncBridge** manages async operations in sync contexts without creating new event loops
- **No feature flags** - async is always used internally for better performance
- **Unified file I/O** - All file operations go through `FileIOCore`

### Key Components
1. **MessageHandler** - Central messaging system that routes to GUI dialogs, TUI widgets, or CLI output
2. **YamlSettingsCache** - Manages all YAML configuration files with caching and batch operations
3. **FileIOCore** - Unified async-first file I/O operations with automatic encoding detection
4. **AsyncDatabasePool** - Connection pooling for FormID database operations
5. **ThreadSafeLogCache** - Thread-safe caching for crash log data
6. **PerformanceMonitor** - Performance tracking decorators and utilities
7. **AsyncBridge** - Singleton bridge for running async code in sync contexts

### Performance Optimizations

The codebase uses several performance optimization patterns:

- **Batch loading** - YamlSettingsCache supports `batch_get_settings()` for loading multiple settings at once
- **Performance monitoring** - `PerformanceMonitor` module provides decorators and context managers
- **Concurrent operations** - File generation and other I/O operations use `asyncio.gather()`
- **Connection pooling** - Database operations use `AsyncDatabasePool` for efficient FormID lookups

### TUI Architecture (Terminal UI)
The TUI uses Textual framework with these components:
- `ClassicLib/TUI/app.py` - Main TUI application controller
- `ClassicLib/TUI/screens/` - Full-screen interfaces (main, help, settings, papyrus)
- `ClassicLib/TUI/widgets/` - Reusable UI components
- `ClassicLib/TUI/handlers/` - Business logic handlers for scan operations

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

# Use AsyncBridge for async in sync contexts
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())
```

### Performance Monitoring Patterns

Use the PerformanceMonitor module for tracking operations:

```python
from ClassicLib.PerformanceMonitor import timed_operation, TimedBlock


@timed_operation("Database query")
def query_database():
    # Your code here
    pass


# Context manager for timing blocks
with TimedBlock("YAML loading", log_level="debug"):
    # Your code here
    pass
```

### Batch Settings Loading

For improved performance, use batch loading when accessing multiple YAML settings:

```python
from ClassicLib.YamlSettingsCache import yaml_cache

# Instead of multiple individual calls, batch them
requests = [
    (str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path"),
    (bool, YAML.Settings, "CLASSIC_Settings.Update Check"),
    (int, YAML.Settings, "MaxOutputLines")
]
values = yaml_cache.batch_get_settings(requests)
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

### Test Isolation Rules
**CRITICAL**: Production data and settings must be treated as READ-ONLY in tests.

#### Production Data is Read-Only
- **NEVER** modify `YAML.Settings` or other production YAML stores in tests
- **NEVER** write to production configuration files during testing
- **NEVER** access or modify user's actual game directories or crash logs
- Tests that need to modify settings should use `YAML.TEST` or create temporary files

#### Proper Test Isolation
```python
# BAD - Modifies production settings
def test_bad_example():
    yaml_settings(str, YAML.Settings, "some.key", "test_value")  # NEVER DO THIS

# GOOD - Uses test-specific configuration
def test_good_example(tmp_path):
    test_file = tmp_path / "test_settings.yaml"
    # Work with test_file, not production settings

# GOOD - Uses dedicated test enum
def test_with_test_enum():
    yaml_settings(str, YAML.TEST, "some.key", "test_value")  # Safe for testing
```

#### Test File Management
- Always use `tmp_path` fixture for temporary test files
- Create isolated test directories for each test
- Clean up resources in test teardown
- Never rely on files existing from previous test runs

## Code Quality Standards

### Type Annotations (Python 3.12+)

- All functions must have complete type annotations including return types
- Use modern Python 3.12+ generic syntax: `list[str]`, `dict[str, Any]`
- Use `TYPE_CHECKING` imports for circular import resolution

### Import Organization

- Remove unused imports
- Group imports: standard library, third-party, local project
- Use conditional imports for optional dependencies (PySide6, tqdm, aiosqlite)

### Path Management

- Always use `pathlib.Path` instead of string paths
- Use `encoding="utf-8", errors="ignore"` for file operations
- Use `open_file_with_encoding()` context manager for unknown encodings

### Message Handling

- Never use direct print statements - use MessageHandler system
- Use `msg_info()`, `msg_warning()`, `msg_error()` functions
- Initialize MessageHandler in test fixtures

## Important Notes

1. **Python 3.12+ Required** - Uses modern Python features and syntax
2. **Async Architecture** - Heavy use of asyncio for performance
3. **GUI Framework** - PySide6 (Qt) for GUI, Textual for TUI
4. **Build System** - PyInstaller with custom spec file for Windows executables
5. **Test Framework** - pytest with pytest-asyncio, pytest-xdist for parallel execution
6. **Configuration** - YAML files in `CLASSIC Data/` for settings and mod databases

## File Organization
- Main scripts at root level (CLASSIC_*.py)
- Core library in `ClassicLib/` with modular components
- TUI components in `ClassicLib/TUI/`
- Tests in `tests/` directory with test markers for categorization
- Sample crash logs in `Crash Logs/`
- Configuration and assets in `CLASSIC Data/`
- Documentation in `docs/`
- Built executables in `Release/`

## Development Workflow
1. Changes should maintain the modular architecture
2. Use MessageHandler for all user communication
3. Follow async patterns in ScanLog components
4. Use batch operations for YAML settings when loading multiple values
5. Add performance monitoring for critical operations
6. Write tests for new functionality with appropriate markers
7. Run linter and type checker before committing
8. Use terminal for running tests (VS Code test tool has freezing issues)
9. Pre-commit hooks will automatically check for test isolation violations

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and test isolation:

### Installation
```bash
# Install pre-commit (already in dev dependencies)
poetry install

# Install the git hooks
poetry run pre-commit install
```

### Available Hooks
- **Production YAML Checker** - Prevents use of production YAML stores in tests
- **Production Path Checker** - Prevents hardcoded production paths in tests
- **Standard hooks** - Trailing whitespace, YAML validation, etc.

### Running Manually
```bash
# Run on all files
poetry run pre-commit run --all-files

# Run on staged files
poetry run pre-commit run

# Run specific hook
poetry run pre-commit run check-test-isolation
```

## Memories
- Output test output to a file to avoid truncation.
- Do not make additions to the `MainWindow` class in `CLASSIC_Interface.py` unless absolutely necessary. Use Mixin classes with TYPE_CHECKING stubs instead.
