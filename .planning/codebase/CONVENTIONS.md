# Coding Conventions

**Analysis Date:** 2026-01-29

## Naming Patterns

**Files:**
- Snake case for all Python files: `async_bridge.py`, `orchestrator_core.py`
- One primary class per file (exceptions allowed for small related helpers)
- Module name reflects primary class/functionality: `async_bridge.py` contains `AsyncBridge` class
- Fixture files: `*_fixtures.py` in `tests/fixtures/` directory
- Test files: `test_<component>_<type>.py` (e.g., `test_async_bridge_wrapper_unit.py`)

**Functions and Methods:**
- Snake case for all functions: `run_async()`, `ensure_loop()`, `gather_with_concurrency()`
- Private methods prefixed with single underscore: `_run_loop()`, `_cleanup_all()`
- Async functions may use `async_` prefix or `*_async` suffix: `async_cleanup()`, `read_file_async()`
- Convenience wrapper functions use `msg_*` pattern for messaging: `msg_info()`, `msg_error()`, `msg_warning()`, `msg_success()`, `msg_debug()`, `msg_critical()`
- Context managers: `msg_progress_context()` for progress tracking

**Classes:**
- PascalCase for all classes: `AsyncBridge`, `OrchestratorCore`, `GlobalRegistry`, `AsyncResourceTracker`, `MessageHandler`
- Exception classes inherit from base exception and use pattern: `RustError`, `RustIOError`, `RustParseError`, `RustConfigError`, `RustDatabaseError`
- Inner classes within test classes: `TestAsyncBridgeWrapper`, `OuterAsync`, `InnerAsync`

**Variables:**
- Snake case for all variables: `coro`, `thread_id`, `_shutdown`, `_instances`
- Module-level constants in ALL_CAPS: `FAST_PATH_OPERATIONS`, `SIZE_DEPENDENT_OPERATIONS`, `AIOFILES_AVAILABLE`
- Type variables: `T`, `P`, `R` (single letters for generic types)
- Protected class-level attributes: `_instances`, `_lock`, `_thread_local`, `_metrics_callback`

**Enums and Types:**
- Enum members in ALL_CAPS: `YAML.Game`, `YAML.Settings`, `MessageType.INFO`, `MessageTarget.CONSOLE`
- TypedDict names in PascalCase: similar to class names
- Literal string values lowercase: `"gui_mode"`, `"cli_mode"`

## Code Style

**Formatting:**
- Tool: Ruff (integrated with pyproject.toml)
- Line length: 140 characters
- Indentation: 4 spaces
- Quote style: Double quotes `""`
- Trailing commas: Enabled with `skip-magic-trailing-comma = false`

**Linting:**
- Tool: Ruff with strict configuration
- Type checking: Pyright in strict mode
- Error codes enforced:
  - `ANN` (Type Annotations): Required on all public functions/classes
  - `PTH` (Pathlib): Prefer `pathlib.Path` over string paths
  - `ARG` (Unused Arguments): Flag unused parameters
  - `ASYNC` (Async Suggestions): Enforce async best practices
  - `SIM` (Simplification): Use simpler patterns
  - `LOG` (Logging): Use logger module, not print()
  - `RUF` (Ruff-specific): Various Ruff recommendations
  - `UP` (pyupgrade): Modern Python syntax
- Disabled for tests (`tests/**/*.py`): Most style rules relaxed for test clarity
- Docstring validation: `D` (pydocstyle) rules enforced in production code

**File Organization:**
- Standard imports first (stdlib)
- Third-party imports second
- Relative imports prohibited (`ban-relative-imports = "all"`)
- Type checking imports isolated: `from typing import TYPE_CHECKING`
  - Runtime-expensive imports in `if TYPE_CHECKING:` block
  - Examples: `from packaging.version import Version`, `from ClassicLib.io.database.async_pool import AsyncDatabasePool`
- `__all__` list in modules exporting public API

## Import Organization

**Order:**
1. Future annotations: `from __future__ import annotations`
2. Standard library: `import logging`, `import asyncio`, `from pathlib import Path`
3. Third-party: `import pytest`, `from pyside6 import ...`
4. First-party (ClassicLib): `from ClassicLib.core.async_bridge import AsyncBridge`
5. TYPE_CHECKING block: Expensive imports for type hints only
6. Module docstring: At top before all imports
7. Logger setup: `logger = logging.getLogger(__name__)`

**Path Aliases:**
- No path aliases in use - full absolute imports from project root
- Example: `from ClassicLib.core.async_bridge import AsyncBridge` (not relative)

**Example Import Block:**
```python
"""Module docstring."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import GlobalRegistry

if TYPE_CHECKING:
    from packaging.version import Version
    from ClassicLib.io.database.async_pool import AsyncDatabasePool

logger = logging.getLogger(__name__)
```

## Error Handling

**Patterns:**
- Specific exception types instead of generic `Exception`
- Exception hierarchy for categorization: `RustError` base class with specific subtypes
- Examples: `RustIOError` (inherits `IOError`), `RustParseError` (inherits `ValueError`), `RustConfigError` (inherits `ValueError`)
- Catch specific exceptions before broader ones: `except (OSError, ValueError, UnicodeDecodeError) as e:`
- Log errors with context: `logger.error(f"Error reading {path}: {e}")`
- Use `from None` to suppress exception chains when appropriate: `raise RuntimeError(...) from None`
- Guard clauses with `return` to reduce nesting depth
- Try-except-else-finally pattern preferred:
  ```python
  try:
      # attempt operation
  except SpecificError as e:
      logger.error(f"Failed: {e}")
      raise
  else:
      return result
  finally:
      # cleanup
  ```

## Logging

**Framework:** Python's `logging` module

**Module-level logger:**
- Every module gets: `logger = logging.getLogger(__name__)`
- Located after imports, before code

**Log Levels:**
- `logger.debug()`: Detailed diagnostic info (thread IDs, lifecycle events)
- `logger.info()`: General informational messages
- `logger.warning()`: Warning conditions (e.g., "Thread did not stop within timeout")
- `logger.error()`: Error conditions (failures, exceptions)
- `logger.critical()`: Critical failures requiring immediate attention

**User-facing messages:** Use MessageHandler functions (not logger):
- `msg_info()`: Standard information
- `msg_warning()`: User warnings
- `msg_error()`: User-facing errors
- `msg_success()`: Success notifications
- `msg_debug()`: Debug output
- `msg_critical()`: Critical notifications

**No print() statements:** All output goes through MessageHandler or logger

## Comments

**When to Comment:**
- Complex algorithms or non-obvious logic only
- Explain the WHY, not the WHAT
- Document threading concerns, concurrency patterns
- Reference external documentation or issue numbers
- Examples of GOOD comments:
  - `# Double-check with lock - handle shutdown instances`
  - `# Fast path - check thread-local cache (no lock needed)`
  - `# Signal that we're ready AFTER set_event_loop() but BEFORE run_forever()`

**When NOT to Comment:**
- Self-documenting code (clear variable names, good structure)
- Code that replicates what the code literally does

**JSDoc/TSDoc:**
- Google-style docstrings required for all public functions/classes
- Use `/python-docstrings` skill for format validation
- Format:
  ```python
  def method(param1: str, param2: int) -> dict[str, Any]:
      """One-line summary.

      Longer description if needed. Can span multiple lines but stays
      focused on what the function does.

      Args:
          param1: Description of first parameter
          param2: Description of second parameter

      Returns:
          Description of return value

      Raises:
          ValueError: When this condition occurs
          RuntimeError: When that condition occurs

      """
  ```
- One-line docstrings acceptable for simple functions
- Multi-line docstrings start with summary line, blank line, then details
- Examples in docstrings use `>>>` format

## Function Design

**Size:**
- Prefer functions < 50 lines
- Maximum 12 branches per function
- Use dictionary mapping or match statements to replace long if-elif chains
- Extract complex logic into separate functions

**Parameters:**
- Type annotations required on all parameters
- Use keyword-only arguments (`*,`) for configuration parameters
- Document all parameters in docstring
- Avoid `**kwargs` - use explicit named parameters
- Default values preferred over `None` checks

**Return Values:**
- Explicit return type annotations required
- `None` explicit for void functions: `-> None:`
- Multiple return values as tuple: `-> tuple[str, int]:`
- Union types for conditional returns: `-> str | None:`

**Async Patterns:**
- Async functions clearly marked: `async def function_name():`
- Coroutines called with `await` (never bare coroutine objects)
- AsyncBridge pattern for sync-to-async bridging in GUI: `bridge.run_async(coro)`
- Never `asyncio.run()` inside async context (use `await`)
- Single global runtime via `classic_shared.get_runtime()` for all threads

## Module Design

**Exports:**
- Public API in `__all__` list at module level
- Example from `async_bridge.py`:
  ```python
  __all__ = [
      "AsyncBridge",
      "run_async",
      "run_async_with_timeout",
      "context_aware_sync",
      "smart_await",
      "create_sync_wrapper",
  ]
  ```

**Barrel Files:**
- Used for re-exporting public APIs
- Example: `ClassicLib/messaging/__init__.py` re-exports from submodules
- Pattern: Import internal modules, then `__all__` list, then `from .submodule import`
- Comment: `# ruff: noqa: TID252 - Relative imports intentional for __init__.py re-exports`

**Module Docstrings:**
- Required on every module (top of file)
- Document purpose, main classes/functions, usage examples
- Example from `async_bridge.py`: Comprehensive module-level docstring with usage patterns, phases, and references

## Concurrency and Threading

**Threading Patterns:**
- Thread ID acquisition: `threading.get_ident()`
- Thread-local storage: `threading.local()` for fast instance access
- Locks: `threading.Lock()` for critical sections
- Events: `threading.Event()` for synchronization
- Thread creation: `threading.Thread(target=func, args=(), daemon=True, name=descriptive_name)`

**Async Patterns:**
- Semaphores for concurrency control: `asyncio.Semaphore(limit)`
- Task gathering: `asyncio.gather(*tasks)` for concurrent execution
- Task cancellation: Clean cancellation with timeout in finally blocks
- Event loop management: Single-threaded event loop per thread (not per function)

**Data Classes:**
- Frozen/immutable preferred for shared data
- ClassVar for class-level shared state: `_instances: ClassVar[dict[int, "AsyncBridge"]]`
- Type annotations on all fields

## Special Patterns

**Singleton Pattern:**
- Used in `AsyncBridge`, `GlobalRegistry`, `MessageHandler`
- Thread-local caching with class-level dict backup
- `get_instance()` class method for thread-safe access
- Cleanup on program exit via `atexit.register()`

**Factory Pattern:**
- Located in `ClassicLib/integration/factory/` modules
- Examples: `get_parser()`, `get_file_io()`, `get_database_pool()`
- Returns appropriate implementation (Rust or Python fallback) based on availability

**Bridge Pattern:**
- AsyncBridge connects sync GUI code with async business logic
- Not used in pure async (CLI/TUI) code
- Alternative: `@context_aware_sync` decorator for transitional code

**Adapter Pattern:**
- Fallback implementations for when Rust modules unavailable
- Example: `get_parser()` returns either Rust or pure Python parser
- Check availability: `from ClassicLib.integration.status import is_rust_accelerated`

---

*Convention analysis: 2026-01-29*
