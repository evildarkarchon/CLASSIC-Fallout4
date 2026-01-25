# CLASSIC Testing Documentation Index

## Overview

This index provides a comprehensive guide to testing practices in the CLASSIC codebase, with special emphasis on handling singletons, async patterns, and parallel test execution.

## 📚 Testing Guides

### 1. [Rust Testing Guide](./rust_testing_guide.md)
**Purpose**: Comprehensive guide for testing Rust crates including patterns, fixtures, and coverage requirements.

**Key Concepts**:
- Test organization for business-logic (`-core`) crates
- Using `tempfile`, `serial_test`, and `#[tokio::test]`
- Coverage requirements and running `cargo-llvm-cov`
- Integration test patterns

**When to Use**:
- Writing tests for Rust crates
- Understanding coverage targets
- Setting up test fixtures for database or file operations
- Debugging test failures in Rust code

---

### 2. [Testing AsyncBridge](./testing_async_bridge.md)
**Purpose**: Avoid `RuntimeWarning: coroutine was never awaited` errors when testing sync/async bridge code.

**Key Concepts**:
- Mock `AsyncBridge.run_async`, not the underlying async methods
- Use `MagicMock` for bridge-wrapped methods, not `AsyncMock`
- Proper patterns for testing sync wrappers of async functions

**When to Use**:
- Testing any code that calls async functions through `AsyncBridge`
- Testing synchronous wrapper functions
- Debugging RuntimeWarnings about unawaited coroutines

---

### 3. [Testing GlobalRegistry](./testing_global_registry.md)
**Purpose**: Prevent test pollution and race conditions from singleton instances.

**Key Concepts**:
- Clear registry before/after tests
- Use unique keys for parallel test safety
- Mock entire registry for unit tests
- Worker isolation strategies for pytest-xdist

**When to Use**:
- Testing code that uses `GlobalRegistry`
- Testing singleton classes (ScanGameCore, MessageHandler)
- Running tests in parallel with pytest-xdist
- Experiencing test failures that only occur when tests run together

---

### 4. [Testing YamlSettingsCache](./testing_yaml_cache.md)
**Purpose**: Test configuration-dependent code without modifying production YAML files.

**Key Concepts**:
- NEVER modify production YAML files (YAML.Settings, YAML.Main)
- Always mock `yaml_settings` for unit tests
- Use `YAML.TEST` enum for test-safe modifications
- Clear cache between tests

**When to Use**:
- Testing code that reads configuration
- Testing settings updates
- Running parallel tests that access YAML
- Need to test different configuration scenarios

---

## 🚀 Quick Start Patterns

### For New Tests

```python
import pytest
from unittest.mock import patch, MagicMock

class TestMyFeature:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Standard test setup."""
        # 1. Clear GlobalRegistry
        from ClassicLib import GlobalRegistry
        GlobalRegistry._registry.clear()

        # 2. Initialize MessageHandler
        from ClassicLib.MessageHandler import init_message_handler
        init_message_handler(parent=None, is_gui_mode=False)

        # 3. Mock YAML settings
        with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
            mock_yaml.return_value = "test_value"
            yield

        # Cleanup
        GlobalRegistry._registry.clear()
        import ClassicLib.MessageHandler
        ClassicLib.MessageHandler._message_handler = None
```

### For Async Tests

```python
@pytest.mark.asyncio
async def test_async_feature():
    """Direct async test."""
    result = await async_function()
    assert result == expected

def test_sync_wrapper():
    """Test sync wrapper of async code."""
    with patch("module.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge
        mock_bridge.run_async.return_value = "result"

        result = sync_function()
        assert result == "result"
```

### For Parallel Tests

```python
import uuid

def test_parallel_safe():
    """Test that works in parallel execution."""
    # Use unique keys
    test_key = f"key_{uuid.uuid4()}"

    # Use tmp_path for files
    test_file = tmp_path / f"test_{uuid.uuid4()}.yaml"

    # Mock shared resources
    with patch("ClassicLib.GlobalRegistry.get") as mock_get:
        mock_get.return_value = "isolated_value"
        # Your test code
```

---

## ⚠️ Common Pitfalls

### 1. AsyncMock Misuse
```python
# ❌ WRONG
mock.async_method = AsyncMock()  # Causes RuntimeWarning

# ✅ CORRECT
mock_bridge.run_async.return_value = "result"
```

### 2. Production YAML Modification
```python
# ❌ FORBIDDEN
yaml_settings(str, YAML.Settings, "key", "value")

# ✅ CORRECT
yaml_settings(str, YAML.TEST, "key", "value")
```

### 3. Registry Pollution
```python
# ❌ BAD
GlobalRegistry.register("key", "value")
# No cleanup!

# ✅ GOOD
try:
    GlobalRegistry.register("key", "value")
finally:
    GlobalRegistry._registry.pop("key", None)
```

---

## 🔍 Debugging Test Issues

### Symptom: `RuntimeWarning: coroutine was never awaited`
**Solution**: See [Testing AsyncBridge Guide](./testing_async_bridge.md)
- Check for `AsyncMock()()` double-call pattern
- Verify AsyncBridge mocking

### Symptom: Tests pass individually but fail together
**Solution**: See [Testing GlobalRegistry Guide](./testing_global_registry.md)
- Add registry cleanup fixtures
- Check for shared state pollution

### Symptom: Tests fail only in parallel (pytest-xdist)
**Solution**: See all guides for parallel testing sections
- Use worker-specific keys/paths
- Isolate singleton instances per worker
- Mock shared resources

### Symptom: Settings changes persist between tests
**Solution**: See [Testing YamlSettingsCache Guide](./testing_yaml_cache.md)
- Clear cache in fixtures
- Mock yaml_settings function
- Use temp files for test data

---

## 📋 Testing Checklist

Before committing test changes, verify:

- [ ] No `AsyncMock` for bridge-wrapped methods
- [ ] No modification of production YAML files
- [ ] GlobalRegistry cleaned up in fixtures
- [ ] MessageHandler initialized for UI-related tests
- [ ] Cache cleared between tests
- [ ] Unique keys used for parallel safety
- [ ] tmp_path used for test files
- [ ] All mocks properly configured
- [ ] No hardcoded paths
- [ ] Tests pass both individually and together
- [ ] Tests pass with pytest-xdist (`-n auto`)

---

## 🔗 Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main project documentation with testing sections
- [pytest.ini](../pytest.ini) - Test configuration and markers
- [conftest.py](../tests/conftest.py) - Shared test fixtures

---

## 💡 Best Practices Summary

1. **Isolation First**: Every test should be completely independent
2. **Mock at Boundaries**: Mock external dependencies, not internal logic
3. **Clear State**: Always clean up singletons and caches
4. **Parallel Safety**: Design tests to work with pytest-xdist
5. **Production Safety**: Never touch production configuration
6. **Document Dependencies**: Make test requirements explicit
7. **Fail Fast**: Use clear assertions and error messages

---

## 📝 Contributing

When adding new testing patterns or discovering issues:

1. Update the relevant guide in `docs/`
2. Add examples from actual test fixes
3. Update this index if adding new guides
4. Include in CLAUDE.md for AI agent discovery

Remember: Good tests are the foundation of maintainable code!
