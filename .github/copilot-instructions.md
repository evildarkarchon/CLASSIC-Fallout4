# CLASSIC-Fallout4 AI Coding Agent Instructions

## Project Overview

CLASSIC is a crash log analyzer for Fallout 4 and Skyrim that processes Buffout 4/Crash Logger output. The project evolved from monolithic to modular orchestrator-based architecture and supports both GUI (PySide6) and CLI modes with optional async processing.

## Architecture Patterns

### Dual Entry Point Architecture
- **CLI entry**: `CLASSIC_ScanLogs.py` for command-line interface
- **GUI entry**: `CLASSIC_Interface.py` for PySide6 graphical interface
- **Component coordination**: Orchestrators manage `FormIDAnalyzer`, `PluginAnalyzer`, `SettingsScanner`, etc.

### Orchestrator Pattern (Dual Implementation)
- **Synchronous**: `ClassicLib.ScanLog.ScanOrchestrator` for standard processing
- **Asynchronous**: `ClassicLib.ScanLog.AsyncScanOrchestrator` for async operations
- **Graceful fallback**: Async components fall back to sync when dependencies unavailable
- **Thread safety**: Use standardized cache patterns for concurrent operations

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

### Import Organization
1. Standard library imports
2. Third-party imports (requests, aiohttp, PySide6)
3. Local project imports (from ClassicLib)

### File Operations
- Always use `pathlib.Path` objects
- Use `encoding="utf-8", errors="ignore"` for file operations
- Use `open_file_with_encoding(file_path)` context manager for unknown encodings

## Testing Requirements

### Test Architecture
- **100% pass rate required** - tests are critical for stability
- **Test fixtures**: Use existing fixtures from `tests/conftest.py`
- **MessageHandler initialization**: Required for `ClassicScanLogs` instances in tests
- **Defensive programming**: Use `hasattr()` checks for optional orchestrator components

### Mock Patterns
```python
# Patch where functions are used, not where defined
with patch.object(scanner.orchestrator, 'process_crash_log') as mock_process:
    # Test logic here
```

## Development Workflows

### Environment Setup
- **Python 3.12+** with Poetry dependency management
- **VS Code** with extensions from `.vscode/` recommendations
- **Poetry commands**: `poetry install`, `poetry up --latest` for updates

### Build Process
- **PyInstaller** builds via VS Code (Ctrl+Shift+D) or `pyinstaller CLASSIC.spec`
- **UPX compression** supported for exe optimization
- **Multiple specs**: `CLASSIC.spec` (GUI), `CLASSIC-CLI.spec` (CLI), `CLASSIC-Test.spec` (testing)

### Task Management
Available VS Code tasks:
- `delete-runtime-files`: Cleans log/config files
- `delete-runtime-folders`: Removes generated directories
- `cleanup-pyinstaller-folders`: Removes build artifacts

## Key Integration Points

### FormID Database System
- **Async FormID lookups**: `AsyncFormIDAnalyzer` with sync fallback
- **Database paths**: Configured via `ClassicLib.Constants.DB_PATHS`
- **Plugin analysis**: Cross-references crash data with mod FormIDs

### Crash Log Processing Pipeline
1. **File discovery**: `crashlogs_get_files()` finds log files
2. **Reformatting**: `crashlogs_reformat()` standardizes formats
3. **Orchestration**: `ScanOrchestrator` or `AsyncScanOrchestrator` coordinates analysis
4. **Component analysis**: FormID, plugin, settings, and suspect scanning
5. **Report generation**: `ReportGenerator` produces final output

### Configuration System
- **Main settings**: `CLASSIC Settings.yaml` via YAML cache
- **Ignore patterns**: `CLASSIC Ignore.yaml` for filtering
- **Local overrides**: `CLASSIC Data/CLASSIC <GAME> Local.yaml`

## Error Handling Patterns

### Exception Management
- **Avoid blind exceptions** unless required for optional functionality
- **Use `contextlib.suppress(ImportError)`** for optional imports
- **Log via MessageHandler**: Not direct print statements

### Thread Safety
- **ThreadSafeLogCache**: Specialized cache for crash log processing only
- **Standardized caching**: Use similar thread-safe patterns for other concurrent operations
- **Defensive component access** with `hasattr()` checks

## Performance Considerations

- **Async database operations** when aiosqlite available
- **Generator patterns** for large data processing
- **Memory management**: Avoid loading entire large files simultaneously
- **Resource cleanup**: Use context managers and finally blocks

## Code Quality Tools

- **Ruff**: Configured in `pyproject.toml` for linting/formatting
- **Pytest**: With coverage reporting via `pytest --cov=. --cov-report=html`
- **MyPy**: Type checking configuration in `pyproject.toml`

## Common Pitfalls

1. **Never use print statements** - always use MessageHandler system
2. **Don't patch where functions are defined** - patch where they're used in tests
3. **Initialize MessageHandler** before creating ClassicScanLogs instances
4. **Use Path objects**, not string paths
5. **Check component availability** with hasattr() for orchestrator parts
6. **Update tests alongside code changes** - don't leave tests broken

## Key Reference Files

- `ClassicLib/__init__.py`: Main module exports
- `ClassicLib/ScanLog/ScanOrchestrator.py`: Core processing coordination
- `ClassicLib/ScanLog/AsyncScanOrchestrator.py`: Async processing coordination
- `ClassicLib/MessageHandler.py`: Unified output system
- `tests/conftest.py`: Test fixtures and initialization
- `.cursor/rules/classic-fallout4-standards.mdc`: Comprehensive coding standards
