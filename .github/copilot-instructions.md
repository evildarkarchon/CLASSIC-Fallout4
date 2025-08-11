# CLASSIC-Fallout4 AI Coding Agent Instructions

## Project Overview

CLASSIC is a crash log analyzer for Fallout 4 and Skyrim that processes Buffout 4/Crash Logger output. The project evolved from monolithic to modular orchestrator-based architecture and supports both GUI (PySide6) and CLI modes with optional async processing.

## Architecture Patterns

### Dual Entry Point Architecture
- **CLI entry**: `CLASSIC_ScanLogs.py` for command-line interface
- **GUI entry**: `CLASSIC_Interface.py` for PySide6 graphical interface
- **Game integrity**: `CLASSIC_ScanGame.py` for game file validation
- **Component coordination**: Orchestrators manage `FormIDAnalyzer`, `PluginAnalyzer`, `SettingsScanner`, etc.

### Async-First Orchestrator Pattern
- **Core implementation**: `ClassicLib.ScanLog.AsyncScanOrchestrator` with `AsyncCrashLogPipeline`
- **Sync adapter**: `ClassicLib.ScanLog.ScanOrchestrator` wraps async with `asyncio.run()`
- **Graceful fallback**: Async components fall back to sync when dependencies unavailable
- **Thread safety**: Use `ThreadSafeLogCache` for concurrent crash log processing

### Conditional Imports & Dependency Management
```python
# Pattern for optional GUI dependencies
try:
    from PySide6.QtCore import QObject, Signal
    HAS_QT = True
except ImportError:
    HAS_QT = False
    class QObject:
        """Stub for when PySide6 is not available."""
```

### Global State Management
- **GlobalRegistry**: Use `ClassicLib.GlobalRegistry` instead of global variables
- **MessageHandler**: Universal system for UI/CLI output via `msg_info()`, `msg_warning()`, `msg_error()`
- **YAML Cache**: Centralized config via `ClassicLib.YamlSettingsCache.yaml_settings()`

## Critical Code Standards

### Type Annotations (Python 3.12+ Syntax)
```python
# Use modern generics, complete function signatures
def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
    """All functions MUST have complete type annotations."""
```

### Import Organization & Cleanup
1. **Always audit for unused imports** - Remove any imports that aren't used
2. **Group imports**: Standard library → Third-party → Local ClassicLib imports
3. **Conditional imports**: Use try/except for optional dependencies (PySide6, aiosqlite, tqdm)

### File Operations
- Always use `pathlib.Path` objects, never string paths
- Use `encoding="utf-8", errors="ignore"` for file operations
- Use `open_file_with_encoding(file_path)` context manager for unknown encodings

## Testing Requirements

### Test Architecture
- **100% pass rate required** - tests are critical for stability
- **MessageHandler initialization**: Use `init_message_handler_fixture` from `tests/conftest.py`
- **Defensive programming**: Use `hasattr()` checks for optional orchestrator components
- **Async testing**: Use `@pytest.mark.asyncio` for async component tests

### Mock Patterns
```python
# Patch where functions are used, not where defined
with patch.object(scanner.orchestrator, 'process_crash_log') as mock_process:
    # Test logic here

# Access components defensively
if hasattr(scanner.orchestrator, '_formid_analyzer'):
    scanner.orchestrator._formid_analyzer.formid_match(formids, plugins, report)
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

## Key Integration Points

### Crash Log Processing Pipeline
1. **File discovery**: `crashlogs_get_files()` finds log files
2. **Reformatting**: `crashlogs_reformat()` or `crashlogs_reformat_async()` standardizes formats
3. **Async orchestration**: `AsyncScanOrchestrator` with `AsyncCrashLogPipeline` coordinates analysis
4. **Component analysis**: FormID, plugin, settings, and suspect scanning via specialized analyzers
5. **Report generation**: `ReportGenerator` produces final output

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

## Common Pitfalls

1. **Never use print statements** - always use MessageHandler system (`msg_info`, `msg_warning`, `msg_error`)
2. **Don't patch where functions are defined** - patch where they're used in tests
3. **Initialize MessageHandler** before creating ClassicScanLogs instances in tests
4. **Use Path objects**, not string paths
5. **Check component availability** with `hasattr()` for orchestrator parts
6. **Remove unused imports** - audit all import statements
7. **Update tests alongside code changes** - maintain 100% pass rate

## Key Reference Files

- `ClassicLib/__init__.py`: Main module exports and MessageHandler functions
- `ClassicLib/ScanLog/AsyncScanOrchestrator.py`: Async-first orchestration
- `ClassicLib/ScanLog/ScanOrchestrator.py`: Sync adapter wrapping async core
- `ClassicLib/MessageHandler.py`: Unified output system for GUI/CLI
- `ClassicLib/GlobalRegistry.py`: Shared state management
- `tests/conftest.py`: Test fixtures and MessageHandler initialization
- `.cursor/rules/classic-fallout4-standards.mdc`: Comprehensive coding standards
