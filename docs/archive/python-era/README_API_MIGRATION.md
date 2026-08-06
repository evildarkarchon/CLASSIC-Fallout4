# YAML Settings Test API Migration Guide

## Overview
This document describes the API changes made to align tests with the current AsyncYamlSettingsCore implementation.

## Key API Changes

### 1. Method Name Changes
- **OLD**: `async_yaml_core.load_yaml(path)`
- **NEW**: `async_yaml_core.file_ops.load_yaml_file(path)`

- **OLD**: `async_yaml_core.get_setting(type, store, key, value)`
- **NEW**: `async_yaml_core.async_yaml_settings(type, store, key, value)`

- **OLD**: `async_yaml_core.load_multiple_stores(stores)`
- **NEW**: Use `batch_get_settings()` or custom implementation

### 2. Property Access Changes
- **OLD**: `async_yaml_core.path_cache`
- **NEW**: `async_yaml_core.cache.path_cache`

- **OLD**: `async_yaml_core.settings_cache`
- **NEW**: `async_yaml_core.cache.settings_cache`

### 3. Mock Function Changes
All mock functions for `get_path_for_store` must be synchronous, not async:

```python
# OLD - INCORRECT
async def mock_get_path(store):
    return path

# NEW - CORRECT
def mock_get_path(store):
    return path
```

### 4. Cache Access Changes
- File-level caching is not implemented in `file_ops.load_yaml_file()`
- Settings caching happens at the `async_yaml_settings()` level
- Cache key format: `(type, yaml_store, key_path)` not `(yaml_store, key_path, type)`

### 5. Import Path Changes
- **OLD**: `from ClassicLib.AsyncYamlSettingsCore import ...`
- **NEW**: `from ClassicLib.AsyncYamlSettings.core import ...`

### 6. Removed/Non-existent Methods
- `prefetch_all_settings()` - Not implemented
- `_load_yaml_file()` - Use `file_ops.load_yaml_file()` instead
- Static store protection - Not implemented in current version

## Test Files Updated
1. `test_yaml_settings_cache.py`
2. `test_yaml_integration.py`
3. `test_async_yaml_error_handling.py`
4. `test_async_yaml_performance.py`
5. `test_async_yaml_core.py`
6. `test_yaml_sync_wrapper.py`
7. `test_async_yaml_batch.py`
8. `test_async_yaml_caching.py`
9. `test_async_yaml_convenience.py`

## Important Notes
- The project rule states: "When API changes occur: Update tests to use the new API, NEVER add backward compatibility to production code just to fix tests"
- All tests have been updated to use the correct current API
- No backward compatibility functions were added to production code
