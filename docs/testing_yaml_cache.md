# Testing Guide: YamlSettingsCache and Configuration Testing

## Overview

YamlSettingsCache is a singleton that manages all YAML configuration throughout CLASSIC. It provides caching, batch operations, and centralized access to settings. Testing code that uses YamlSettingsCache requires special care to avoid test pollution, especially in parallel test execution.

## The Challenge with YamlSettingsCache

### Shared State Issues
- Cache persists between tests
- File modifications affect other tests
- Parallel tests can cause race conditions
- Production YAML files should never be modified

## Critical Testing Rules

### ⚠️ NEVER Modify Production YAML Files

```python
# ❌ ABSOLUTELY FORBIDDEN
def test_bad():
    from ClassicLib.YamlSettingsCache import yaml_settings
    from ClassicLib.Constants import YAML

    # NEVER DO THIS - Modifies production settings!
    yaml_settings(str, YAML.Settings, "some.key", "test_value")

# ✅ CORRECT: Use test-specific YAML or mocks
def test_good():
    from unittest.mock import patch

    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
        mock_yaml.return_value = "test_value"
        # Your test code here
```

## Correct Testing Patterns

### ✅ Pattern 1: Mock yaml_settings Function

```python
from unittest.mock import patch, MagicMock

@patch("ClassicLib.YamlSettingsCache.yaml_settings")
def test_with_mocked_yaml(mock_yaml_settings):
    """Mock yaml_settings to return test values."""
    # Setup mock responses
    def yaml_side_effect(type_, yaml_key, setting_path, default=None):
        test_values = {
            "CLASSIC_Settings.MODS Folder Path": "C:/Test/Mods",
            "CLASSIC_Settings.Update Check": True,
            "MaxOutputLines": 1000
        }
        return test_values.get(setting_path, default)

    mock_yaml_settings.side_effect = yaml_side_effect

    # Your test code
    from my_module import function_using_settings
    result = function_using_settings()

    # Verify calls
    mock_yaml_settings.assert_called()
```

### ✅ Pattern 2: Clear Cache in Fixtures

```python
import pytest
from ClassicLib.YamlSettingsCache import YamlSettingsCache

@pytest.fixture(autouse=True)
def clear_yaml_cache():
    """Clear YAML cache before and after each test."""
    # Get the singleton instance
    cache = YamlSettingsCache()

    # Clear cache before test
    cache._cache.clear()
    cache._last_modified.clear()

    yield

    # Clear cache after test
    cache._cache.clear()
    cache._last_modified.clear()
```

### ✅ Pattern 3: Use Test-Specific YAML Files

```python
@pytest.fixture
def test_yaml_file(tmp_path):
    """Create a test-specific YAML file."""
    import yaml

    test_yaml = tmp_path / "test_settings.yaml"
    test_data = {
        "test_section": {
            "key1": "value1",
            "key2": 42,
            "key3": True
        }
    }

    with open(test_yaml, 'w') as f:
        yaml.dump(test_data, f)

    return test_yaml

def test_with_test_yaml(test_yaml_file):
    """Test using temporary YAML file."""
    from ClassicLib.YamlSettingsCache import YamlSettingsCache

    cache = YamlSettingsCache()

    # Read from test file (not production!)
    with open(test_yaml_file, 'r') as f:
        import yaml
        data = yaml.safe_load(f)

    assert data["test_section"]["key1"] == "value1"
```

### ✅ Pattern 4: Mock the Entire Cache

```python
@pytest.fixture
def mock_yaml_cache():
    """Provide a completely mocked YamlSettingsCache."""
    from unittest.mock import MagicMock, patch

    with patch("ClassicLib.YamlSettingsCache.YamlSettingsCache") as MockCache:
        mock_instance = MagicMock()

        # Setup test data
        test_settings = {
            "path1": "value1",
            "path2": True,
            "path3": 100
        }

        # Configure mock methods
        mock_instance.get_setting.side_effect = lambda *args, **kwargs: test_settings.get(args[2], args[3] if len(args) > 3 else None)
        mock_instance.batch_get_settings.return_value = ["value1", True, 100]

        MockCache.return_value = mock_instance
        yield mock_instance
```

## Testing Batch Operations

### ✅ Testing batch_get_settings

```python
def test_batch_operations():
    """Test batch loading of settings."""
    from unittest.mock import patch

    with patch("ClassicLib.YamlSettingsCache.yaml_cache") as mock_cache:
        # Setup batch response
        mock_cache.batch_get_settings.return_value = [
            "C:/Games/Fallout4/Mods",
            True,
            1000
        ]

        # Test code that uses batch operations
        from ClassicLib.YamlSettingsCache import yaml_cache
        requests = [
            (str, "Settings", "CLASSIC_Settings.MODS Folder Path"),
            (bool, "Settings", "CLASSIC_Settings.Update Check"),
            (int, "Settings", "MaxOutputLines")
        ]
        values = yaml_cache.batch_get_settings(requests)

        assert values[0] == "C:/Games/Fallout4/Mods"
        assert values[1] is True
        assert values[2] == 1000
```

## Parallel Testing Considerations

### Worker Isolation for pytest-xdist

```python
import pytest
import os

@pytest.fixture(scope="function")
def isolated_yaml_cache(tmp_path, monkeypatch):
    """Create isolated YAML cache for each test worker."""
    # Get worker ID
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    # Create worker-specific cache directory
    worker_cache_dir = tmp_path / f"cache_{worker_id}"
    worker_cache_dir.mkdir(exist_ok=True)

    # Monkey-patch the cache to use worker-specific paths
    from ClassicLib.YamlSettingsCache import YamlSettingsCache

    original_init = YamlSettingsCache.__init__

    def patched_init(self):
        original_init(self)
        # Override cache paths for this worker
        self._cache_dir = worker_cache_dir

    monkeypatch.setattr(YamlSettingsCache, "__init__", patched_init)

    yield

    # Cleanup is automatic with tmp_path
```

### Thread-Safe Test Patterns

```python
import threading
import pytest

def test_thread_safe_cache_access():
    """Test that cache handles concurrent access correctly."""
    from unittest.mock import patch, MagicMock
    from threading import Lock

    # Create thread-safe mock
    mock_cache = MagicMock()
    mock_cache._lock = Lock()

    results = []

    def thread_worker(thread_id):
        with mock_cache._lock:
            # Simulate cache access
            value = f"value_{thread_id}"
            results.append(value)

    # Create and start threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=thread_worker, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    assert len(results) == 10
    assert len(set(results)) == 10  # All unique values
```

## Real-World Examples from CLASSIC

### Example 1: Testing with Mocked Settings

```python
@pytest.fixture
def mock_settings():
    """Mock YAML settings for tests."""
    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
        def yaml_side_effect(type_, yaml_key, setting_path, default=None):
            from ClassicLib.Constants import YAML

            if yaml_key == YAML.Main:
                settings_map = {
                    "catch_log_errors": ["error", "warning", "critical"],
                    "exclude_log_files": ["ignore.log"],
                    "exclude_log_errors": ["ignorable error"],
                }
            elif yaml_key == YAML.Settings:
                settings_map = {
                    "CLASSIC_Settings.MODS Folder Path": "C:/Test/Mods",
                    "CLASSIC_Settings.Game Folder Path": "C:/Test/Game",
                }
            else:
                settings_map = {}

            return settings_map.get(setting_path, default)

        mock_yaml.side_effect = yaml_side_effect
        yield mock_yaml

def test_log_scanner(mock_settings):
    """Test log scanner with mocked settings."""
    from ClassicLib.ScanLog import ClassicScanLogs

    scanner = ClassicScanLogs()
    # Scanner will use mocked settings
    result = scanner.scan_logs(test_path)
    assert result is not None
```

### Example 2: Testing Settings Updates

```python
def test_settings_update():
    """Test updating settings without touching production files."""
    from unittest.mock import patch, MagicMock

    # Create a mock that tracks calls
    mock_set_setting = MagicMock()

    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:
        # First call returns old value, subsequent calls for writing
        mock_yaml.side_effect = [
            "old_value",  # Read current value
            None,  # Write new value
        ]

        # Simulate updating a setting
        from ClassicLib.YamlSettingsCache import yaml_settings
        from ClassicLib.Constants import YAML

        # Read current
        old = yaml_settings(str, YAML.TEST, "test.key")
        assert old == "old_value"

        # "Update" (mocked)
        yaml_settings(str, YAML.TEST, "test.key", "new_value")

        # Verify the calls
        assert mock_yaml.call_count == 2
```

## Common Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Direct File Manipulation

```python
# BAD: Directly modifying YAML files
def test_bad():
    import yaml
    with open("CLASSIC Data/Settings.yaml", "w") as f:
        yaml.dump({"bad": "idea"}, f)
    # This modifies production files!

# GOOD: Use temp files
def test_good(tmp_path):
    import yaml
    test_file = tmp_path / "test.yaml"
    with open(test_file, "w") as f:
        yaml.dump({"good": "practice"}, f)
```

### ❌ Anti-Pattern 2: Not Clearing Cache

```python
# BAD: Cache pollution between tests
def test_one():
    cache = YamlSettingsCache()
    cache._cache["key"] = "value1"

def test_two():
    cache = YamlSettingsCache()
    # Might still have "key" from test_one!
    assert "key" not in cache._cache  # FAILS!

# GOOD: Clear cache in fixture
def test_with_clear_cache(clear_yaml_cache):
    cache = YamlSettingsCache()
    cache._cache["key"] = "value"
    # Cache will be cleared after test
```

### ❌ Anti-Pattern 3: Assuming File Paths

```python
# BAD: Hardcoded paths
def test_bad():
    settings_file = "C:/Users/someone/CLASSIC Data/Settings.yaml"
    # Fails on other machines!

# GOOD: Use fixtures and tmp_path
def test_good(tmp_path):
    settings_file = tmp_path / "Settings.yaml"
    # Works everywhere
```

## Best Practices Summary

1. **NEVER modify production YAML files** - Use YAML.TEST or mocks
2. **Always mock yaml_settings** for unit tests
3. **Clear cache between tests** using fixtures
4. **Use tmp_path for test files** instead of real paths
5. **Isolate workers** in parallel tests
6. **Document test dependencies** clearly
7. **Prefer mocking over file I/O** for speed
8. **Test batch operations** separately from single operations

## Quick Reference

| Scenario | Solution | Example |
|----------|----------|---------|
| Read settings | Mock yaml_settings | `patch("ClassicLib.YamlSettingsCache.yaml_settings")` |
| Write settings | Use YAML.TEST enum | `yaml_settings(str, YAML.TEST, ...)` |
| Clear cache | Fixture | `clear_yaml_cache` fixture |
| Parallel tests | Worker isolation | `isolated_yaml_cache` fixture |
| Batch operations | Mock batch_get_settings | `mock_cache.batch_get_settings.return_value = [...]` |
| Test files | Use tmp_path | `tmp_path / "test.yaml"` |

## Debugging Tips

1. **Cache not clearing?** Check if you're clearing both `_cache` and `_last_modified`
2. **Settings bleeding between tests?** Add autouse fixture to clear cache
3. **Parallel test failures?** Ensure worker isolation with separate cache directories
4. **Mock not working?** Verify you're patching at the right import location
5. **File access errors?** Use tmp_path instead of production paths

## Related Documentation

- [Testing AsyncBridge](./testing_async_bridge.md)
- [Testing GlobalRegistry](./testing_global_registry.md)
- [CLAUDE.md Testing Section](../CLAUDE.md#testing-patterns)
- [Test Isolation Rules](../CLAUDE.md#test-isolation-rules)
