# Code Style and Conventions for CLASSIC-Fallout4

## Python Version and Syntax
- **Python 3.12+ required** - Use modern Python features
- **Type hints mandatory** - All functions must have complete type annotations
- **Generic syntax** - Use `list[str]`, `dict[str, Any]` (not `List`, `Dict` from typing)

## File Organization
### Size Limits
- **500 lines** - Soft limit, consider refactoring
- **550 lines** - Hard limit, must not exceed
- **Test files**: Maximum 300 lines

### Class Structure
- **One class per file** - Primary class only
- **Exceptions allowed**:
  - Small helper classes tightly coupled to main class
  - Data classes with their enums
  - TypedDict definitions with their class
- **File naming** - Match the primary class name

## Import Organization
```python
# Standard library imports
import asyncio
from pathlib import Path

# Third-party imports
import pytest
from PySide6.QtWidgets import QWidget

# Local project imports
from ClassicLib.MessageHandler import msg_info
from ClassicLib.AsyncBridge import AsyncBridge
```

## Async Patterns
```python
# Always use AsyncBridge for sync/async bridging
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Never use asyncio.run() directly in sync contexts
# DEPRECATED: from ClassicLib.AsyncCore import SyncAdapter
```

## Path Handling
```python
# Always use pathlib.Path
from pathlib import Path

file_path = Path("data") / "config.yaml"

# File operations with encoding
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
```

## Message Output
```python
# Never use print() statements
# Always use MessageHandler system
from ClassicLib.MessageHandler import msg_info, msg_warning, msg_error

msg_info("Processing complete")
msg_warning("Potential issue detected")
msg_error("Critical failure")
```

## Naming Conventions
- **Classes**: PascalCase (e.g., `AsyncScanOrchestrator`)
- **Functions/Methods**: snake_case (e.g., `process_crash_log`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)
- **Private attributes**: Leading underscore (e.g., `_internal_state`)

## Documentation Standards
```python
def process_log(log_path: Path, validate: bool = True) -> dict[str, Any]:
    """Process a crash log file and extract relevant information.

    Args:
        log_path: Path to the crash log file
        validate: Whether to validate the log format

    Returns:
        Dictionary containing extracted crash information

    Raises:
        FileNotFoundError: If log file doesn't exist
        ValueError: If log format is invalid
    """
```

## Test Conventions
- **Test files**: `test_<module_name>.py`
- **Test classes**: `Test<ClassName>`
- **Test methods**: `test_<functionality>_<scenario>`
- **Use fixtures** for setup/teardown
- **Mock external dependencies**
- **Test isolation**: Never modify production data

## Error Handling
```python
# Be specific with exceptions
try:
    result = await process_file(path)
except FileNotFoundError:
    msg_error(f"File not found: {path}")
except PermissionError:
    msg_warning(f"Permission denied: {path}")
except Exception as e:
    msg_error(f"Unexpected error: {e}")
```

## Performance Patterns
```python
# Use batch operations for YAML settings
from ClassicLib.YamlSettingsCache import yaml_cache

requests = [
    (str, YAML.Settings, "key1"),
    (bool, YAML.Settings, "key2"),
]
values = yaml_cache.batch_get_settings(requests)

# Use performance monitoring
from ClassicLib.PerformanceMonitor import timed_operation

@timed_operation("Database query")
def query_database():
    pass
```

## Backward Compatibility
- **Maintain API compatibility** - Breaking changes need deprecation path
- **Use re-exports** in `__init__.py` for refactored modules
- **Add DeprecationWarning** for old APIs
- **Document migration path** in docstrings
