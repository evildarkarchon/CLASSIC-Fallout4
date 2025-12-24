# Test Fixtures Standards

## Fixture Location Rule

**All pytest fixtures MUST be defined in `tests/fixtures/`** - Never create fixtures in individual test files or scattered conftest.py files.

## Directory Structure

```
tests/fixtures/
├── __init__.py              # Re-exports for convenience
├── async_fixtures.py        # Async test utilities, event loops
├── crash_log_fixtures.py    # Crash log content and file creation
├── data_fixtures.py         # General test data fixtures
├── database_pool_fixtures.py # Database connection pool fixtures
├── fcx_fixtures.py          # FCX mode testing fixtures
├── mock_fixtures.py         # Common mock objects
├── qt_fixtures.py           # Qt/PySide6 testing fixtures
├── registry_fixtures.py     # GlobalRegistry fixtures
├── rust_fixtures.py         # Rust FFI compatible mocks
├── scanlog_fixtures.py      # Orchestrator, parser fixtures
├── stress_fixtures.py       # Stress/load testing fixtures
├── version_cache_fixtures.py # Version cache fixtures
└── yamldata_fixtures.py     # YamlData mock fixtures
```

## How Fixtures Are Loaded

All fixtures are imported in `tests/conftest.py` using wildcard imports:
```python
from tests.fixtures.crash_log_fixtures import *  # noqa: F403
from tests.fixtures.rust_fixtures import *  # noqa: F403
# ... etc
```

This makes all fixtures available to every test file automatically.

## Creating New Fixtures

1. **Identify the appropriate module** based on the fixture's domain
2. **Add the fixture** to the existing module, or create a new module if needed
3. **If creating a new module**, add the import to `tests/conftest.py`
4. **Document the fixture** with a docstring explaining its purpose

## Allowed Exceptions

Domain-specific `conftest.py` files may contain:
- **Imports only** - Re-importing fixtures for clarity
- **pytest hooks** - `pytest_configure`, `pytest_collection_modifyitems`, etc.
- **Module-level setup** - One-time initialization for a test directory

They should **NOT** contain fixture definitions.

## Anti-Patterns

- Fixtures in individual test files -> Move to `tests/fixtures/`
- Duplicate fixtures across conftest files -> Consolidate in one fixture module
- Fixtures in `tests/*/conftest.py` -> Move to central `tests/fixtures/`
