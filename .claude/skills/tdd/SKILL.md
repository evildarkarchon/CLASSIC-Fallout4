---
name: tdd
description: Test-Driven Development skill for hybrid Python-Rust projects. Enforces Red-Green-Refactor cycle with project-specific testing patterns for pytest, async code, and Rust integration tests.
---

This skill guides test-driven development for the CLASSIC hybrid Python-Rust architecture. Follow the Red-Green-Refactor cycle strictly: write a failing test first, implement minimal code to pass, then refactor while keeping tests green.

## TDD Workflow

### Phase 1: Red (Write Failing Test)

Before writing any implementation code:

1. **Understand the requirement** - What behavior needs to exist?
2. **Write the test first** - Express the requirement as a test
3. **Run the test** - Verify it fails for the right reason
4. **Commit the failing test** - Document the requirement

```python
# Example: Testing a new function
@pytest.mark.unit
def test_parse_formid_extracts_plugin_index():
    """FormID parser should extract plugin index from hex string."""
    result = parse_formid("0A001234")
    assert result.plugin_index == 0x0A
    assert result.local_id == 0x001234
```

### Phase 2: Green (Make It Pass)

Write the **minimal** code to make the test pass:

1. **Implement just enough** - No extra features
2. **Run the test** - Verify it passes
3. **Run related tests** - Ensure no regressions

```python
# Minimal implementation to pass the test
def parse_formid(formid_hex: str) -> FormIDResult:
    plugin_index = int(formid_hex[:2], 16)
    local_id = int(formid_hex[2:], 16)
    return FormIDResult(plugin_index=plugin_index, local_id=local_id)
```

### Phase 3: Refactor (Improve)

With passing tests as a safety net:

1. **Improve code quality** - Readability, performance, patterns
2. **Run all tests** - Maintain green status
3. **Commit the refactor** - Separate from feature commits

## Python Testing Patterns

### File and Function Naming

```
tests/
├── <domain>/
│   ├── test_<component>_unit.py        # Isolated unit tests
│   ├── test_<component>_integration.py # Cross-component tests
│   └── test_<component>_e2e.py         # End-to-end tests
```

Function naming: `test_<component>_<action>_<expected_result>`

```python
def test_parser_handles_empty_log():
def test_formid_analyzer_validates_hex_format():
def test_async_bridge_prevents_nested_calls():
```

### Required Markers

Every test MUST have appropriate markers:

```python
@pytest.mark.unit           # Isolated unit test
@pytest.mark.integration    # Cross-component test
@pytest.mark.asyncio        # Async test (required for async def)
@pytest.mark.slow           # Test takes >1 second
@pytest.mark.gui            # GUI component test
@pytest.mark.performance    # Performance test
@pytest.mark.rust           # Rust FFI test
```

### Fixture Organization

**All fixtures MUST be in `tests/fixtures/`** - Never in individual test files.

```python
# Good: Use centralized fixtures
from tests.fixtures.crash_log_fixtures import sample_crash_log

@pytest.mark.unit
def test_parser_with_fixture(sample_crash_log):
    result = parse_log(sample_crash_log)
    assert result.success

# Bad: Never define fixtures in test files
@pytest.fixture  # DO NOT DO THIS IN TEST FILES
def my_fixture():
    pass
```

To add a new fixture:
1. Identify the appropriate module in `tests/fixtures/`
2. Add the fixture with a docstring
3. If new module needed, add import to `tests/conftest.py`

## Async Testing Patterns

### Pattern 1: Pure Async Tests

For testing async functions directly:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_file_read():
    """Test async function with real async/await."""
    result = await read_file_async(test_path)
    assert result.content == expected
```

### Pattern 2: Sync Wrapper Tests

For testing synchronous functions that use AsyncBridge internally:

```python
@pytest.mark.unit
def test_sync_wrapper():
    """Test sync wrapper - mock AsyncBridge, not the async function."""
    with patch("module.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge
        mock_bridge.run_async.return_value = "expected_result"

        result = sync_wrapper_function()

        assert result == "expected_result"
        mock_bridge.run_async.assert_called_once()
```

### Singleton Cleanup

Always clean up singletons between tests:

```python
@pytest.fixture(autouse=True)
def clear_singletons():
    """Clear singleton instances between tests."""
    from ClassicLib.GlobalRegistry import GlobalRegistry
    GlobalRegistry._registry.clear()

    yield

    GlobalRegistry._registry.clear()
```

## Rust Testing Patterns

### Unit Tests (In-Module)

Place unit tests in `#[cfg(test)]` module within source files:

```rust
// src/parser.rs
pub fn parse_formid(hex: &str) -> Result<FormID, ParseError> {
    // implementation
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_formid_valid_hex() {
        let result = parse_formid("0A001234").unwrap();
        assert_eq!(result.plugin_index, 0x0A);
        assert_eq!(result.local_id, 0x001234);
    }

    #[test]
    fn test_parse_formid_invalid_hex() {
        let result = parse_formid("ZZZZZZZZ");
        assert!(result.is_err());
    }
}
```

### Async Rust Tests

Use `#[tokio::test]` for async tests:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_async_file_read() {
        let result = read_file_async("test.txt").await.unwrap();
        assert!(!result.is_empty());
    }
}
```

### Python Binding Tests

Place in `tests/rust_integration/`:

```python
# tests/rust_integration/test_yaml_rust_integration.py
@pytest.mark.unit
def test_rust_yaml_loads_correctly():
    """Test Rust YAML module loads and functions."""
    import classic_yaml

    result = classic_yaml.load_yaml_string("key: value")
    assert result["key"] == "value"
```

## Anti-Patterns to Avoid

### Never Modify Production YAML

```python
# FORBIDDEN
yaml_settings(str, YAML.Settings, "key", "value")

# CORRECT
yaml_settings(str, YAML.TEST, "key", "value")
# Or use mocks
with patch("module.yaml_settings") as mock:
    mock.return_value = "test_value"
```

### Never Use AsyncMock for Bridge-Wrapped Methods

```python
# WRONG - causes RuntimeWarning: coroutine was never awaited
mock.async_method = AsyncMock(return_value="result")

# CORRECT - mock the bridge, not the async method
mock_bridge.run_async.return_value = "result"
```

### Never Add Backward Compatibility to Fix Tests

```python
# WRONG - don't modify production code to fix tests
def old_api():  # Added for backward compatibility
    return new_api()

# CORRECT - update tests to use current API
def test_uses_current_api():
    result = new_api()  # Use the actual current API
```

### Never Create Fixtures in Test Files

```python
# WRONG - fixture in test file
@pytest.fixture
def my_local_fixture():
    return "data"

# CORRECT - add to tests/fixtures/<appropriate_module>.py
# Then import via conftest.py
```

## Test Execution Commands

### Python Tests

```bash
# Quick unit tests
uv run pytest -m "unit and not slow"

# Integration tests
uv run pytest -m "integration"

# Specific test file
uv run pytest tests/path/to/test_file.py -v

# Single test function
uv run pytest tests/path/to/test_file.py::test_function -v

# With coverage
uv run pytest --cov=ClassicLib --cov-report=html -n auto
```

### Rust Tests

```bash
# All Rust tests
cargo test --workspace --manifest-path rust/Cargo.toml

# Specific crate
cargo test -p classic-yaml-core --manifest-path rust/Cargo.toml

# With output
cargo test --workspace --manifest-path rust/Cargo.toml -- --nocapture
```

### Rust Integration (Python)

```bash
# All Rust integration tests
uv run pytest tests/rust_integration/ -v

# Specific module
uv run pytest tests/rust_integration/test_yaml_rust_integration.py -v
```

## TDD Checklist

Before marking a feature complete:

- [ ] Failing test written first (Red)
- [ ] Minimal implementation passes test (Green)
- [ ] Code refactored with tests still passing (Refactor)
- [ ] Appropriate markers applied (`@pytest.mark.unit`, etc.)
- [ ] Fixtures in `tests/fixtures/` (not in test file)
- [ ] Singletons cleaned up in fixtures
- [ ] No production YAML modifications
- [ ] No `AsyncMock` for bridge-wrapped methods
- [ ] Tests pass individually AND together

## References

For detailed patterns, consult:
- `tests/TEST_WRITING_GUIDE.md` - Complete test writing guide
- `docs/testing/async_test_patterns_guide.md` - Async testing patterns
- `docs/testing/TESTING_GUIDE_INDEX.md` - All testing documentation
- `.claude/rules/03-testing.md` - Testing standards and fixtures
