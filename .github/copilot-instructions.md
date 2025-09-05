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

## Key Integration Points

### Fragment-Based Architecture (NEW)
```python
# Modern immutable fragment composition pattern replaces mutable lists
from ClassicLib.ScanLog.ReportFragment import ReportFragment, ReportComposer

# Generate fragments instead of mutating lists
def detect_mods_new() -> ReportFragment:
    lines = ["* ⚠️ Mod warning\n"]
    return ReportFragment.from_lines(lines)

# Compose fragments immutably
composer = ReportComposer()
composer.add(header_fragment)
composer.add_conditional(lambda: detect_mods(), "SECTION HEADER")
final_report = composer.build()
```

### AsyncBridge Pattern (Critical)
```python
# Efficient sync-to-async execution without creating new event loops
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Never create event loops manually - use AsyncBridge
# ❌ Don't: asyncio.run() in sync context repeatedly
# ✅ Do: AsyncBridge for persistent thread-local event loops
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

## Key Architecture Files

- `ClassicLib/__init__.py` - Main exports and MessageHandler functions
- `ClassicLib/ScanLog/OrchestratorCore.py` - Async-first core orchestration
- `ClassicLib/FileIOCore.py` - Unified async file I/O operations
- `ClassicLib/MessageHandler.py` - Universal output system
- `ClassicLib/GlobalRegistry.py` - Shared state management
- `ClassicLib/TUI/app.py` - Terminal UI application controller
- `ClassicLib/AsyncBridge.py` - Sync-to-async execution bridge
- `ClassicLib/ScanLog/ReportFragment.py` - Immutable fragment composition system
- `tests/conftest.py` - Test fixtures and initialization
- `.cursor/rules/classic-fallout4-standards.mdc` - Comprehensive standards
