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

**IMPORTANT**: The `ClassicLib.AsyncCore` module is deprecated as of v2.x and will be removed in v3.0.0. Use `AsyncBridge` for all sync/async bridging needs.

When working with async code:
```python
# Use FileIOCore for all file operations
from ClassicLib.FileIOCore import FileIOCore

async def process_files():
    io_core = FileIOCore()
    content = await io_core.read_file(path)
    await io_core.write_file(output_path, processed_content)

# ALWAYS use AsyncBridge for running async code in sync contexts
# This is optimized for performance and prevents event loop conflicts
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Sync adapter usage (for backwards compatibility)
# Note: These adapters internally use AsyncBridge
from ClassicLib.FileIOCore import read_file_sync
content = read_file_sync(path)

# DEPRECATED - Do not use AsyncCore patterns:
# from ClassicLib.AsyncCore import SyncAdapter  # Use AsyncBridge instead
# from ClassicLib.AsyncCore import create_sync_adapter  # Use AsyncBridge.run_async() instead
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

### Test Organization Rules
**CRITICAL**: Maintain clean test architecture to prevent test suite degradation.

#### File Size Limits
- **Maximum 300 lines per test file** - Split larger files into logical components
- Files approaching 250 lines should be considered for refactoring
- Exception allowed only when tests are tightly coupled and splitting would harm maintainability

#### New Test Placement
- **NO tests in root `tests/` directory** - All tests must be in subdirectories
- New tests must be added to the appropriate subdirectory:
  - `tests/async_tests/` - Async patterns and infrastructure
  - `tests/core/` - Core functionality (crash logs, FormID, etc.)
  - `tests/scanning/` - Log and mod scanning
  - `tests/game/` - Game path and integrity
  - `tests/settings/` - YAML and settings management
  - `tests/performance/` - Performance benchmarks
  - `tests/concurrency/` - Thread safety
  - `tests/backup/` - Backup operations
  - `tests/io/` - File I/O operations
  - `tests/mods/` - Mod detection
  - `tests/utils/` - Utility functions
  - `tests/gui/` - GUI components
  - `tests/tui/` - TUI components
- Create new subdirectories if testing a new major component

#### Test File Naming
- Use descriptive names: `test_<component>_<aspect>.py`
- Examples: `test_backup_creation.py`, `test_async_error_handling.py`
- Avoid generic names like `test_utils.py` for new files

#### Test Type Separation
**CRITICAL**: Different test types must be in separate files for maintainability and execution control.

- **Unit Tests** - Must be in files named `test_<component>_unit.py`
  - Test individual functions/methods in isolation
  - Mock all external dependencies
  - Should run quickly (< 100ms per test)
  - Example: `test_formid_analyzer_unit.py`

- **Integration Tests** - Must be in files named `test_<component>_integration.py`
  - Test interaction between multiple components
  - May use real file I/O with temp directories
  - Can test database connections and external services
  - Example: `test_scan_pipeline_integration.py`

- **End-to-End Tests** - Must be in files named `test_<component>_e2e.py`
  - Test complete workflows from entry point to output
  - Simulate real user scenarios
  - May involve GUI/TUI interactions
  - Example: `test_crash_log_scanning_e2e.py`

**Never mix test types in the same file** - This ensures:
- Faster test execution by running only needed test types
- Clear dependency requirements for each test file
- Better mock management and test isolation
- Easier debugging when tests fail

### Test-Driven Development (TDD) Method

Follow the **Red-Green-Refactor** cycle for all new features and bug fixes:

#### 1. Red Phase - Write a Failing Test First
```python
# Example: Writing test for a new FormID validation feature
@pytest.mark.asyncio
async def test_validate_formid_format():
    """Test that FormID validation correctly identifies valid/invalid formats."""
    validator = FormIDValidator()

    # Test valid FormIDs
    assert await validator.is_valid("0x12345678") is True
    assert await validator.is_valid("12345678") is True

    # Test invalid FormIDs
    assert await validator.is_valid("invalid") is False
    assert await validator.is_valid("0xGGGGGGGG") is False
```

#### 2. Green Phase - Write Minimal Implementation
```python
# Minimal code to make the test pass
class FormIDValidator:
    async def is_valid(self, formid: str) -> bool:
        """Validate FormID format."""
        cleaned = formid.replace("0x", "").replace("0X", "")
        try:
            int(cleaned, 16)
            return len(cleaned) <= 8
        except ValueError:
            return False
```

#### 3. Refactor Phase - Improve Code Quality
```python
# Refactored with better structure and performance
from functools import lru_cache
import re

class FormIDValidator:
    FORMID_PATTERN = re.compile(r'^(?:0x)?[0-9a-fA-F]{1,8}$')

    @lru_cache(maxsize=1024)
    def _validate_format(self, formid: str) -> bool:
        """Cache validation results for frequently checked FormIDs."""
        return bool(self.FORMID_PATTERN.match(formid))

    async def is_valid(self, formid: str) -> bool:
        """Validate FormID format with caching."""
        return self._validate_format(formid.strip())
```

#### TDD Best Practices

1. **Write One Test at a Time** - Focus on a single behavior or requirement
2. **Keep Tests Simple** - Each test should verify one specific aspect
3. **Use Descriptive Test Names** - Test names should describe what they verify
4. **Test Edge Cases** - Include boundary conditions and error scenarios
5. **Mock External Dependencies** - Keep tests isolated and fast

```python
# Good test structure
class TestAsyncLogProcessor:
    """Tests for async log processing functionality."""

    @pytest.fixture
    async def processor(self, tmp_path):
        """Create processor with mocked dependencies."""
        mock_db = AsyncMock()
        return AsyncLogProcessor(db=mock_db, cache_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_processes_valid_log_file(self, processor, sample_log):
        """Should successfully process a valid crash log."""
        result = await processor.process(sample_log)
        assert result.status == "success"
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_handles_corrupted_log_gracefully(self, processor):
        """Should return error status for corrupted logs."""
        corrupted_log = Path("corrupted.log")
        result = await processor.process(corrupted_log)
        assert result.status == "error"
        assert "corrupted" in result.error_message.lower()
```

#### When to Apply TDD

- **New Features** - Always start with tests when adding new functionality
- **Bug Fixes** - Write a test that reproduces the bug before fixing it
- **Refactoring** - Ensure existing tests pass, add new tests for changed behavior
- **Performance Improvements** - Write performance tests with benchmarks

#### TDD with Async Code

For async components, follow the same TDD cycle with async test patterns:

```python
# Test async operations with proper fixtures
@pytest.mark.asyncio
async def test_concurrent_file_operations(tmp_path):
    """Test that multiple files can be processed concurrently."""
    files = [tmp_path / f"test_{i}.log" for i in range(10)]
    for f in files:
        f.write_text("test content")

    processor = AsyncFileProcessor()
    results = await processor.process_batch(files)

    assert len(results) == 10
    assert all(r.success for r in results)
```

### Test Isolation Rules
**CRITICAL**: Production data and settings must be treated as READ-ONLY in tests.

#### Production Data is Read-Only
- **NEVER** modify `YAML.Settings` or other production YAML stores in tests
- **NEVER** write to production configuration files during testing
- **NEVER** access or modify user's actual game directories or crash logs
- Tests that need to modify settings should use `YAML.TEST` or create temporary files

#### API Changes and Test Updates
- **ALWAYS** update tests to use the new API when refactoring occurs
- **NEVER** add backward compatibility functions to production code just to make tests pass
- Tests should validate the actual production API, not compatibility layers
- This ensures tests catch real breaking changes and API misuse

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

### Python File Organization

#### File Size Limits
- **500-line soft limit** - Files approaching this should be considered for refactoring
- **550-line hard limit** - Files must not exceed this size
- When files grow too large, split them into logical components

#### Class Organization
- **One class per file** - Each file should contain a single primary class
- **Exception**: Small, tightly related helper classes can be included in the same file
- Examples of acceptable related classes:
  - A data class and its associated enum
  - A main class and its small exception classes
  - A class and its TypedDict definitions

#### Refactoring Guidelines
- When files contain multiple classes, split them into subdirectories
- Maintain backward compatibility with re-exports and deprecation warnings
- Group related components in logical subdirectories
- Use descriptive file names that match the primary class name
- Helper functions should remain with their primary usage context

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

### Root Level
- Main scripts at root level (CLASSIC_*.py)
- Built executables in `Release/`
- Configuration and assets in `CLASSIC Data/`
- Documentation in `docs/`
- Sample crash logs in `Crash Logs/`

### ClassicLib Structure (Refactored)
The core library follows a modular, one-class-per-file organization after comprehensive refactoring:

#### Phase 1: Critical File Size Violations (Completed)

**MessageHandler** - `ClassicLib/MessageHandler/`
- `enums.py` - MessageType, MessageTarget enums
- `models.py` - Message class
- `cli_progress.py` - CLIProgressBar class
- `progress_context.py` - ProgressContext class
- `handler.py` - Main MessageHandler class
- `qt_compat.py` - Qt compatibility utilities
- `__init__.py` - Backward compatibility re-exports

**Utils** - `ClassicLib/Utils/`
- `path_utils.py` - Path-related utilities
- `string_utils.py` - String manipulation utilities
- `file_utils.py` - File operation utilities
- `logging_utils.py` - Logging utilities
- `version_utils.py` - Version handling utilities
- `web_utils.py` - Web-related utilities
- `__init__.py` - Re-exports all utilities

**FileIO** - `ClassicLib/FileIO/`
- `core.py` - Main FileIOCore class
- `path_utils.py` - Path handling utilities
- `sync_adapters.py` - Synchronous adapter methods
- `__init__.py` - Backward compatibility

**AsyncYamlSettings** - `ClassicLib/AsyncYamlSettings/`
- `core.py` - Main async settings class
- `cache.py` - Caching logic
- `validators.py` - Validation logic
- `file_operations.py` - File I/O operations
- `types.py` - Type definitions
- `__init__.py` - Re-exports

**ScanGame** - `ClassicLib/ScanGame/core/`
- `dds_processor.py` - DDS file processing
- `file_operations.py` - File operations
- `log_processor.py` - Log processing logic
- `utils.py` - Utility functions
- `validators.py` - Validation methods
- `__init__.py` - Core exports

#### Phase 2: High Priority Violations (Completed)

**Interface/Settings** - `ClassicLib/Interface/Settings/`
- `dialog.py` - Main settings dialog
- `path_manager.py` - Path management logic
- `tab_creators.py` - Tab creation utilities
- `__init__.py` - Settings exports

**Interface/Widgets** - `ClassicLib/Interface/Widgets/`
- `report_list.py` - ReportListWidget class
- `markdown_viewer.py` - MarkdownViewer class
- `report_metadata.py` - ReportMetadataWidget class
- `__init__.py` - Widget exports

#### Phase 3: ScanLog Module (Completed)

**ScanLog/fragments** - `ClassicLib/ScanLog/fragments/`
- `report_fragment.py` - Core ReportFragment class
- `report_composer.py` - Fragment composition logic
- `fragment_collector.py` - Backward compatibility wrapper
- `report_generator_functional.py` - Functional report generation
- `mod_detection.py` - Mod detection utilities

**ScanLog/models** - `ClassicLib/ScanLog/models/`
- `scan_config.py` - Configuration dataclass
- `scan_statistics.py` - Statistics tracking
- `scan_result.py` - Result container

**ScanLog/pipeline** - `ClassicLib/ScanLog/pipeline/`
- `async_crash_log_pipeline.py` - Main pipeline class
- `async_performance_monitor.py` - Performance monitoring

**ScanLog/scanloginfo** - `ClassicLib/ScanLog/scanloginfo/`
- `thread_safe_log_cache.py` - Thread-safe caching
- `classic_scan_logs_info.py` - Configuration dataclass

**ScanLog/composition** - `ClassicLib/ScanLog/composition/`
- `conditional_section.py` - Conditional header logic
- `report_composer.py` - Report composition class

#### Phase 5: TUI Module (Completed)

**TUI/widgets/dialogs** - `ClassicLib/TUI/widgets/dialogs/`
- `confirmation_dialog.py` - Confirmation dialog
- `error_dialog.py` - Error display dialog
- `progress_dialog.py` - Progress tracking dialog

**TUI/handlers/papyrus** - `ClassicLib/TUI/handlers/papyrus/`
- `papyrus_stats.py` - Statistics dataclass
- `tui_papyrus_handler.py` - Main handler class

### Backward Compatibility
All refactored modules maintain backward compatibility through re-exports:
- Original import paths still work with deprecation warnings
- Example: `from ClassicLib.ScanLog.models import ScanConfig` works
- New path: `from ClassicLib.ScanLog.models.scan_config import ScanConfig`
- Deprecation warnings guide migration to new structure

### Tests Organization
- `tests/` directory with test markers for categorization
- Subdirectories by functionality (async_tests, core, scanning, etc.)
- Maximum 300 lines per test file

## Development Workflow
1. Changes should maintain the modular architecture
2. Use MessageHandler for all user communication
3. Follow async patterns in ScanLog components
4. Always use AsyncBridge for running async code in sync contexts (optimized for performance)
5. Use batch operations for YAML settings when loading multiple values
6. Add performance monitoring for critical operations
7. Write tests for new functionality with appropriate markers
8. Run linter and type checker before committing
9. Use terminal for running tests (VS Code test tool has freezing issues)
10. **When API changes occur:** Update tests to use the new API, NEVER add backward compatibility to production code just to fix tests

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

## Common Anti-Patterns to Avoid

1. ❌ `print()` statements → ✅ `msg_info()`, `msg_warning()`, `msg_error()`
2. ❌ String paths → ✅ `pathlib.Path` objects
3. ❌ Unused imports → ✅ Audit and remove
4. ❌ Missing type annotations → ✅ Complete function signatures
5. ❌ Patching definitions → ✅ Patch where used in tests
6. ❌ Skip MessageHandler init → ✅ Use `init_message_handler_fixture`
7. ❌ `asyncio.run()` in sync context → ✅ Use `AsyncBridge.get_instance().run_async()`
8. ❌ Mutable lists in reports → ✅ Use `ReportFragment` composition
9. ❌ Production YAML in tests → ✅ Use `YAML.TEST` or mock `yaml_settings()`
10. ❌ Creating event loops manually → ✅ Use `AsyncBridge` for persistent loops
11. ❌ Adding backward compatibility for tests → ✅ Update tests to match the new API

## Memories
- Output test output to a file to avoid truncation.
- Do not make additions to the `MainWindow` class in `CLASSIC_Interface.py` unless absolutely necessary. Use Mixin classes with TYPE_CHECKING stubs instead.
- API compatibility is a priority. Any API-breaking change should also come with a way to access it with the old API, but with a DeprecationWarning.
