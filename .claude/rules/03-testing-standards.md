# Testing Standards

## Test-Driven Development (TDD) - REQUIRED

**All new features and bug fixes MUST follow TDD methodology.**

Use the Red-Green-Refactor cycle:
1. **Red**: Write a failing test first that defines expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green

AI agents should use the TDD skill at `.claude/skills/tdd/SKILL.md` for comprehensive patterns.

**TDD Checklist**:
- [ ] Failing test written first
- [ ] Minimal implementation passes test
- [ ] Code refactored with tests still passing
- [ ] Tests pass individually AND with parallel execution (`-n auto`)

## Test Organization
- **Structure**: Domain-driven directories in `tests/`
- **File Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Markers**: Required - `@pytest.mark.unit`, `.integration`, `.asyncio`, `.slow`, `.gui`, `.performance`
- **Rust tests**: Place in `tests/rust_integration/` directory (no special marker needed)

## Critical Rules
1. **NEVER modify production YAML** in tests (use `YAML.TEST` or mocks)
2. **NEVER add backward compatibility** to fix tests (update tests to match new API)
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones

## Testing Guides
See `docs/` for detailed guides:
- `testing/testing_async_bridge.md` - Async/sync mocking
- `testing/testing_global_registry.md` - Singleton isolation
- `testing/testing_yaml_cache.md` - Config testing
- `testing/test_pollution_guide.md` - Master pollution prevention guide

## Test Fixtures

**All fixtures MUST be defined in `tests/fixtures/`** - centralized for reuse and discoverability.

**Exception: Local Autouse Fixtures**
Local `conftest.py` files are allowed ONLY for `autouse=True` fixtures that must be scoped to a specific directory:

```python
# tests/stress/conftest.py - ALLOWED
from tests.fixtures.stress_fixtures import cleanup_after_stress_test as _cleanup_impl

@pytest.fixture(autouse=True)
def cleanup_after_stress_test():
    yield from _cleanup_impl()
```

This prevents autouse fixtures from running on the entire test suite while keeping implementations centralized.

## Test Anti-Patterns
- Production YAML in tests -> Use `YAML.TEST` or mocks
- Adding backward compatibility to fix tests -> Update tests to match new API
- Missing singleton cleanup -> Always clear GlobalRegistry, MessageHandler between tests
- Unawaited coroutines -> Use proper async mocking patterns
- Autouse fixtures in central module -> Use local conftest wrapper for directory scoping
