# Testing Standards

## TDD Required

All new features and bug fixes MUST follow TDD. Use the `/tdd` skill for detailed patterns.

**Workflow**: Red (failing test) -> Green (minimal pass) -> Refactor (improve with tests green)

## Test Organization

- **Location**: Domain-driven directories in `tests/`
- **Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Rust tests**: `tests/rust_integration/` directory

### Required Markers

```python
@pytest.mark.unit           # Isolated unit test
@pytest.mark.integration    # Cross-component test
@pytest.mark.asyncio        # Async test
@pytest.mark.slow           # Test takes >1 second
@pytest.mark.gui            # GUI component test
@pytest.mark.performance    # Performance test
```

## Fixtures

**All fixtures MUST be in `tests/fixtures/`** - Never in individual test files.

```
tests/fixtures/
├── async_fixtures.py        # Async utilities, event loops
├── crash_log_fixtures.py    # Crash log content
├── mock_fixtures.py         # Common mocks
├── registry_fixtures.py     # GlobalRegistry fixtures
├── rust_fixtures.py         # Rust FFI mocks
├── scanlog_fixtures.py      # Parser fixtures
└── yamldata_fixtures.py     # YamlData mocks
```

**Exception**: Local `conftest.py` allowed ONLY for `autouse=True` fixtures scoped to directory:
```python
# tests/stress/conftest.py - wraps centralized implementation
from tests.fixtures.stress_fixtures import cleanup_impl
@pytest.fixture(autouse=True)
def cleanup():
    yield from cleanup_impl()
```

## Critical Rules

1. **NEVER modify production YAML** - Use `YAML.TEST` or mocks
2. **NEVER add backward compatibility to fix tests** - Update tests to match new API
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** - Mock AsyncBridge, not async functions directly
5. **Tests are exempt from API stability** - Always use current APIs

## References

- `/tdd` skill - Complete TDD patterns
- `docs/testing/` - Detailed testing guides
