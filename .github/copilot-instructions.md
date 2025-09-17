# CLASSIC-Fallout4 AI Coding Agent Instructions

## Project Overview

CLASSIC is a crash log analyzer for Fallout 4 and Skyrim that processes Buffout 4/Crash Logger output. The architecture evolved from monolithic to async-first orchestrator pattern supporting three interfaces: GUI (PySide6), TUI (Textual), and CLI modes.

## Essential Development Commands

```bash
# Environment setup
poetry install                          # Install all dependencies
poetry install --with gui              # Include PySide6 for GUI development
poetry install --with windows          # Include Windows-specific dependencies

# Running the application
python CLASSIC_Interface.py            # GUI mode
python CLASSIC_TUI.py                  # TUI mode (Terminal UI)
python CLASSIC_ScanLogs.py            # CLI mode
python CLASSIC_ScanGame.py            # Game integrity checker

# Testing (critical - maintain 100% pass rate)
python -m pytest tests/ -v            # All tests with verbose output
python -m pytest -n auto              # Parallel execution (auto-detect cores)
python -m pytest -m "unit and not slow" --maxfail=3  # Quick feedback

# Code quality
ruff check .                           # Lint check
ruff format .                          # Format code
poetry up --latest                     # Update dependencies
```

## Architecture: Async-First Orchestrator Pattern

### Core Flow
1. **OrchestratorCore** (`ClassicLib.ScanLog.OrchestratorCore`) - Async-first implementation
2. **ScanOrchestrator** - Sync adapter wrapping `OrchestratorCore` with `asyncio.run()`
3. **AsyncScanOrchestrator** - DEPRECATED: Now aliases to `OrchestratorCore`

### Entry Points
- `CLASSIC_ScanLogs.py` - CLI with async/sync fallback
- `CLASSIC_Interface.py` - GUI with PySide6
- `CLASSIC_TUI.py` - Terminal UI with Textual framework
- `CLASSIC_ScanGame.py` - Game file validation

### Component Coordination
```python
# Orchestrators manage specialized analyzers:
FormIDAnalyzer     # Database lookups for mod identification
PluginAnalyzer     # Mod file analysis
SettingsScanner   # Configuration validation
SuspectScanner    # Known problematic pattern detection
ReportGenerator   # Final output formatting
```

## Critical Patterns

### Conditional Imports (GUI/CLI Compatibility)
```python
try:
    from PySide6.QtCore import QObject, Signal
    HAS_QT = True
except ImportError:
    HAS_QT = False
    class QObject:
        """Stub for when PySide6 is not available."""
```

### MessageHandler (Never Use Print)
```python
from ClassicLib import msg_info, msg_warning, msg_error
msg_info("Processing complete")         # ✓ Correct
print("Processing complete")            # ✗ Never do this
```

### FileIOCore (Unified Async File Operations)
```python
from ClassicLib.FileIOCore import FileIOCore

# Async-first file operations
async def process_files():
    io_core = FileIOCore()
    content = await io_core.read_file(path)
    await io_core.write_file(output_path, processed_content)

# Sync fallback available
from ClassicLib.FileIOCore import read_file_sync
content = read_file_sync(path)
```

### Async/Sync Compatibility
```python
try:
    return asyncio.run(self._process_crashlog_async(crashlog_file))
except ImportError:
    return self.orchestrator.process_crash_log(crashlog_file)
```

### Type Safety (Python 3.12+)
```python
def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
    """All functions MUST have complete type annotations."""
```

## Testing Requirements

### Test-Driven Development (TDD) Cycle
```python
# 1. RED: Write failing test first
@pytest.mark.asyncio
async def test_new_feature():
    result = await new_async_function()
    assert result.status == "success"

# 2. GREEN: Minimal implementation
async def new_async_function():
    return SimpleResult(status="success")

# 3. REFACTOR: Improve with performance/structure
```

### Test Isolation (CRITICAL)
```python
# NEVER access production YAML stores in tests
yaml_settings(str, YAML.Settings, "key")     # ❌ FORBIDDEN
yaml_settings(str, YAML.TEST, "key")         # ✅ Safe for testing

# NEVER create production directories
Path("CLASSIC Data").mkdir()                 # ❌ FORBIDDEN
Path(tmp_path / "CLASSIC Data").mkdir()      # ✅ Use tmp_path

# Pre-commit hooks enforce these rules automatically
```

### Test Initialization Pattern
```python
# REQUIRED: Initialize MessageHandler before creating ClassicScanLogs
from tests.conftest import init_message_handler_fixture
scanner = init_message_handler_fixture()  # Use fixture

# DEFENSIVE: Check component availability
if hasattr(scanner.orchestrator, '_formid_analyzer'):
    scanner.orchestrator._formid_analyzer.formid_match(formids, plugins, report)
```

### Testing AsyncBridge and Async Code

**IMPORTANT**: When testing code that uses AsyncBridge, proper mocking is critical to avoid `RuntimeWarning: coroutine was never awaited` errors.

```python
# ✅ CORRECT: Mock AsyncBridge.run_async for sync wrappers
with patch("module.AsyncBridge") as mock_bridge_class:
    mock_bridge = MagicMock()
    mock_bridge_class.get_instance.return_value = mock_bridge
    mock_bridge.run_async.return_value = "expected_result"

    result = sync_wrapper_function()
    assert result == "expected_result"

# ❌ WRONG: Don't use AsyncMock for bridge-wrapped methods
mock_instance.async_method = AsyncMock()  # This causes RuntimeWarning!
```

### Testing GlobalRegistry and Singletons

**CRITICAL**: GlobalRegistry manages singleton instances that persist across tests, causing test pollution and race conditions in parallel execution.

```python
# ✅ CORRECT: Clear registry in fixtures
@pytest.fixture(autouse=True)
def clean_global_registry():
    GlobalRegistry._registry.clear()
    yield
    GlobalRegistry._registry.clear()

# ✅ CORRECT: Use unique keys for parallel tests
test_key = f"key_{uuid.uuid4()}"
GlobalRegistry.register(test_key, value)
```

### Testing YamlSettingsCache

**WARNING**: NEVER modify production YAML files in tests. Always use mocks or the YAML.TEST enum.

```python
# ✅ CORRECT: Mock yaml_settings for tests
@patch("ClassicLib.YamlSettingsCache.yaml_settings")
def test_with_mock(mock_yaml):
    mock_yaml.return_value = "test_value"
    # Your test code

# ❌ FORBIDDEN: Never modify production settings
yaml_settings(str, YAML.Settings, "key", "value")  # NEVER in tests!

# ✅ CORRECT: Use test enum or temp files
yaml_settings(str, YAML.TEST, "key", "value")  # Safe for testing
```

### Testing Guides Index

Complete testing documentation for CLASSIC components and test pollution prevention:

#### Core Pollution Sources (Critical)
1. **[Testing AsyncBridge](../docs/testing_async_bridge.md)** - Async/sync bridge mocking patterns
2. **[Testing GlobalRegistry](../docs/testing_global_registry.md)** - Singleton isolation and parallel testing
3. **[Testing YamlSettingsCache](../docs/testing_yaml_cache.md)** - Configuration testing without pollution

#### Additional Pollution Sources
4. **[Testing MessageHandler](../docs/testing_message_handler.md)** - Message system singleton isolation
5. **[Testing Database Pools](../docs/testing_database_pools.md)** - Connection pool resource management
6. **[Testing ThreadSafeLogCache](../docs/testing_thread_safe_cache.md)** - Thread-safe cache isolation
7. **[Testing FileIOCore](../docs/testing_fileio_core.md)** - File I/O operations without bridge pollution

#### Master Guide
8. **[Test Pollution Prevention Guide](../docs/test_pollution_guide.md)** - **Comprehensive guide covering all pollution sources with quick reference patterns**

These guides are essential for writing reliable, isolated tests, especially when using `pytest-xdist` for parallel execution.

### Test Markers and Categories
```python
# Use appropriate pytest markers for test categorization
@pytest.mark.unit                # Fast, isolated tests
@pytest.mark.integration         # Multi-component tests
@pytest.mark.async_test          # Async/await pattern tests
@pytest.mark.gui                 # GUI-dependent tests (requires Qt)
@pytest.mark.slow                # Tests taking >1 second
@pytest.mark.performance         # Performance regression tests
@pytest.mark.file_io             # File I/O operations
```

### Test Organization Rules
```python
# NEW: File size limits and organization requirements
# - Maximum 300 lines per test file
# - NO tests in root tests/ directory - must be in subdirectories
# - Use descriptive names: test_<component>_<aspect>.py

# Test directories by functionality:
tests/async_tests/     # Async patterns and infrastructure
tests/core/           # Core functionality (crash logs, FormID, etc.)
tests/scanning/       # Log and mod scanning
tests/game/          # Game path and integrity
tests/settings/      # YAML and settings management
```

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

## Development Workflows

### Environment Setup
- **Python 3.12+** with Poetry dependency management
- **VS Code** with extensions from `.vscode/` recommendations
- **Commands**: `poetry install`, `poetry up --latest`, `ruff check .`, `ruff format .`

### Build Process
- **PyInstaller** builds via VS Code (Ctrl+Shift+D) or `pyinstaller CLASSIC.spec`
- **Multiple specs**: `CLASSIC.spec` (GUI), `CLASSIC-CLI.spec` (CLI), `CLASSIC-Test.spec` (testing)
- **UPX compression** supported for exe optimization

### Task Management
Available VS Code tasks:
- `delete-runtime-files`: Cleans log/config files
- `delete-runtime-folders`: Removes generated directories
- `cleanup-pyinstaller-folders`: Removes build artifacts

### Code Quality Enforcement
- **Pre-commit hooks**: Automatically check test isolation, YAML usage, and code quality
- **Installation**: `poetry run pre-commit install`
- **Manual run**: `poetry run pre-commit run --all-files`
- **Test isolation**: Prevents production YAML/path usage in tests

#### Available Hooks
- **Production YAML Checker** - Prevents use of production YAML stores in tests
- **Production Path Checker** - Prevents hardcoded production paths in tests
- **Standard hooks** - Trailing whitespace, YAML validation, etc.

#### Running Pre-commit Manually
```bash
# Run on all files
poetry run pre-commit run --all-files

# Run on staged files
poetry run pre-commit run

# Run specific hook
poetry run pre-commit run check-test-isolation
```

## Key Integration Points

### Fragment-Based Architecture (CURRENT)
```python
# Modern immutable fragment composition pattern - REQUIRED for new report code
from ClassicLib.ScanLog.fragments import ReportFragment, ReportComposer

# Generate fragments instead of mutating lists
def detect_mods_new() -> ReportFragment:
    lines = ["* ⚠️ Mod warning\n"]
    return ReportFragment.from_lines(lines)

# Compose fragments immutably
composer = ReportComposer()
composer.add(header_fragment)
composer.add_conditional(lambda: detect_mods(), "SECTION HEADER")
final_report = composer.build()

# Conditional sections with automatic headers
from ClassicLib.ScanLog.composition import ConditionalSection
section = ConditionalSection.with_header(
    lambda: content_fragment,
    "Header added only if content exists"
)
```

### AsyncBridge Pattern (Critical Performance)
```python
# Thread-safe singleton for efficient sync-to-async execution
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# PERFORMANCE: Maintains persistent thread-local event loops
# ❌ Don't: asyncio.run() repeatedly (creates new loops each time)
# ✅ Do: AsyncBridge for persistent thread-local event loops
# ❌ Don't: Create event loops manually
# ✅ Do: Use AsyncBridge singleton pattern
```

### Modular File Organization (CURRENT STRUCTURE)
```python
# Post-refactoring: One class per file, logical subdirectories
ClassicLib/
  ScanLog/
    fragments/          # Fragment composition system
      report_fragment.py
      report_composer.py
      fragment_collector.py
    composition/        # Conditional sections
      conditional_section.py
      report_composer.py
    models/            # Data classes
      scan_config.py
      scan_statistics.py
      scan_result.py
  MessageHandler/      # Messaging system
    handler.py         # Main handler
    models.py         # Message data classes
    enums.py          # Message types
  FileIO/             # File operations
    core.py           # FileIOCore class
    sync_adapters.py  # Sync compatibility
  Utils/              # Utilities by category
    path_utils.py
    string_utils.py
    file_utils.py

# Backward compatibility maintained via re-exports
from ClassicLib.ScanLog.ReportFragment import ReportFragment  # ✅ Works but deprecated
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment  # ✅ Preferred
```

### TUI Architecture (Terminal User Interface)
- **Main app**: `ClassicLib/TUI/app.py` - Textual application controller
- **Screens**: `ClassicLib/TUI/screens/` - Full-screen interfaces (main, help, settings, papyrus)
- **Widgets**: `ClassicLib/TUI/widgets/` - Reusable UI components (progress bars, dialogs, input forms)
- **Handlers**: `ClassicLib/TUI/handlers/` - Business logic handlers for scan operations
- **Themes**: `ClassicLib/TUI/themes/` - UI styling and color schemes

### Crash Log Processing Pipeline
1. **File discovery**: `crashlogs_get_files()` finds log files
2. **Reformatting**: `crashlogs_reformat()` or `crashlogs_reformat_async()` standardizes formats
3. **Async orchestration**: `OrchestratorCore` (async-first) coordinates analysis via fragments
4. **Component analysis**: FormID, plugin, settings, and suspect scanning via specialized analyzers
5. **Fragment composition**: `ReportComposer` builds immutable reports from fragments

### FormID Database System
- **Async-first lookups**: `AsyncFormIDAnalyzer` with sync fallback to `FormIDAnalyzer`
- **Database paths**: Configured via `ClassicLib.Constants.DB_PATHS`
- **Plugin cross-reference**: Maps crash data FormIDs to mod origins

### Configuration System
- **YAML cache**: Type-safe access via `yaml_settings(type, YAML.Section, "key")`
- **Main settings**: `CLASSIC Settings.yaml` for core configuration
- **Game-specific**: `CLASSIC Data/CLASSIC <GAME> Local.yaml` for local overrides
- **Ignore patterns**: `CLASSIC Ignore.yaml` for filtering false positives

## Error Handling Patterns

### Exception Management
- **Avoid blind exceptions** unless required for optional functionality
- **Use `contextlib.suppress(ImportError)`** for optional imports
- **Log via MessageHandler**: Never use direct print statements

### Thread Safety & Async Patterns
- **ThreadSafeLogCache**: Thread-safe in-memory cache for crash log data
- **Async database operations**: Use `aiosqlite` when available, fallback to sync
- **Resource cleanup**: Always use context managers and finally blocks

## Performance Considerations

- **Async-first architecture**: Core operations use async/await for better performance
- **Memory management**: Use generators for large data processing, avoid loading entire files
- **Database optimization**: Async FormID lookups with connection pooling
- **File I/O**: Batch operations where possible, use `FileIOCore` for unified async file handling

## Code Quality Tools

- **Ruff**: Configured in `pyproject.toml` for linting/formatting
- **Pytest**: With coverage reporting via `pytest --cov=. --cov-report=html`
- **Type checking**: MyPy configuration in `pyproject.toml`

## Common Anti-Patterns

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
11. ❌ Large files (>500 lines) → ✅ Split into logical components with subdirectories
12. ❌ Multiple classes per file → ✅ One primary class per file
13. ❌ Tests in root tests/ → ✅ Organize in subdirectories by functionality
14. ❌ Adding backward compatibility for tests → ✅ Update tests to match the new API

## Key Architecture Files

- `ClassicLib/__init__.py` - Main exports and MessageHandler functions
- `ClassicLib/ScanLog/OrchestratorCore.py` - Async-first core orchestration
- `ClassicLib/FileIOCore.py` - Unified async file I/O operations
- `ClassicLib/MessageHandler/handler.py` - Universal output system
- `ClassicLib/GlobalRegistry.py` - Shared state management
- `ClassicLib/TUI/app.py` - Terminal UI application controller
- `ClassicLib/AsyncBridge.py` - Sync-to-async execution bridge
- `ClassicLib/ScanLog/fragments/report_fragment.py` - Immutable fragment composition system
- `ClassicLib/ScanLog/composition/report_composer.py` - Fragment composition utilities
- `tests/conftest.py` - Test fixtures and initialization
