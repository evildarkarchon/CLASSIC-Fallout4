# Test Pollution Prevention Guide

## Overview

Test pollution occurs when tests share mutable state, causing failures, flaky behavior, and false positives/negatives in test results. In the CLASSIC codebase, several components maintain global state that persists across tests, leading to contamination and unreliable test execution, especially when running tests in parallel with `pytest-xdist`.

## What is Test Pollution?

Test pollution manifests in several ways:

1. **State Leakage** - Data from one test affects another test
2. **Resource Contamination** - Shared resources (files, connections, caches) persist across tests
3. **Singleton Persistence** - Global instances maintain state between tests
4. **Configuration Pollution** - Settings or configuration changes affect subsequent tests
5. **Race Conditions** - Parallel tests interfere with each other through shared state

## Pollution Sources in CLASSIC

The CLASSIC codebase has **9 major test pollution sources** that require careful handling:

| Component | Type | Severity | Parallel Impact |
|-----------|------|----------|-----------------|
| [AsyncBridge](#asyncbridge) | Singleton | Critical | High |
| [GlobalRegistry](#globalregistry) | Singleton Registry | Critical | High |
| [YamlSettingsCache](#yamlsettingscache) | Cached Singleton | Critical | High |
| [DatabasePoolManager](#databasepoolmanager) | Singleton Pool | Critical | High |
| [Version String Cache](#version-string-cache) | LRU Cache | High | Medium |
| [MessageHandler](#messagehandler) | Singleton | High | Medium |
| [Database Pools](#database-pools) | Connection Pools | High | High |
| [ThreadSafeLogCache](#threadsafelogcache) | Thread-Safe Cache | Medium | High |
| [FileIOCore](#fileiocore) | Bridge Coupling | Medium | Medium |

## 🔴 Critical Pollution Sources

### AsyncBridge

**Problem**: Singleton event loop manager that persists across tests
- **Symptoms**: RuntimeWarning about coroutines never awaited, event loop conflicts
- **Impact**: All async operations affected
- **Solution**: Mock `AsyncBridge.get_instance()` or reset `_instance`

```python
# ❌ Wrong
async def test_async_function():
    result = await some_async_operation()  # Uses polluted bridge

# ✅ Correct
@patch("module.AsyncBridge")
def test_async_function(mock_bridge_class):
    mock_bridge = MagicMock()
    mock_bridge_class.get_instance.return_value = mock_bridge
    mock_bridge.run_async.return_value = "expected_result"
```

**📖 [Complete Guide: Testing AsyncBridge](testing_async_bridge.md)**

### GlobalRegistry

**Problem**: Singleton registry that accumulates entries across tests
- **Symptoms**: Registry entries from previous tests, key conflicts, memory growth
- **Impact**: All components using registry
- **Solution**: Clear registry in fixtures

```python
# ❌ Wrong
def test_with_registry():
    GlobalRegistry.register("key", value)  # Pollutes global state

# ✅ Correct
@pytest.fixture(autouse=True)
def clean_registry():
    GlobalRegistry._registry.clear()
    yield
    GlobalRegistry._registry.clear()
```

**📖 [Complete Guide: Testing GlobalRegistry](testing_global_registry.md)**

### YamlSettingsCache

**Problem**: Cached configuration that persists across tests
- **Symptoms**: Settings from previous tests, cache growth, wrong configuration values
- **Impact**: All configuration-dependent code
- **Solution**: Mock `yaml_settings` calls

```python
# ❌ Wrong - Modifies production settings
def test_settings():
    yaml_settings(str, YAML.Settings, "key", "test_value")  # NEVER!

# ✅ Correct - Mock the function
@patch("module.yaml_settings")
def test_settings(mock_yaml):
    mock_yaml.return_value = "test_value"
```

**📖 [Complete Guide: Testing YamlSettingsCache](testing_yaml_cache.md)**

### DatabasePoolManager

**Problem**: Singleton database connection pool manager that persists across tests
- **Symptoms**: Shared database connections, pool not initialized errors, connection reuse issues
- **Impact**: All async FormID lookups and database operations
- **Solution**: Use fixture to reset singleton state

```python
# ❌ Wrong - Singleton persists
async def test_database_pool():
    manager = DatabasePoolManager()
    pool = await manager.get_pool()  # May get pool from previous test

# ✅ Correct - Use isolation fixture
@pytest.fixture(autouse=True)
def clean_database_pool_manager():
    DatabasePoolManager._instance = None
    DatabasePoolManager._lock = None
    yield
    DatabasePoolManager._instance = None
```

**Fixture Available**: `clean_database_pool_manager` (autouse in tests/fixtures/database_pool_fixtures.py)

## 🟡 High Impact Pollution Sources

### Version String Cache

**Problem**: LRU cache for version parsing that accumulates entries across tests
- **Symptoms**: Cached results from previous tests, incorrect cache hit rates, memory growth
- **Impact**: All version parsing operations
- **Solution**: Clear LRU cache between tests

```python
# ❌ Wrong - Cache persists
def test_version_parsing():
    version = crashgen_version_gen("1.28.6")  # May use cached result

# ✅ Correct - Clear cache
@pytest.fixture(autouse=True)
def clean_version_caches():
    crashgen_version_gen.cache_clear()
    yield
    crashgen_version_gen.cache_clear()
```

**Fixture Available**: `clean_version_caches` (autouse in tests/fixtures/version_cache_fixtures.py)

### MessageHandler

**Problem**: Singleton message routing system
- **Symptoms**: Messages from one test appear in another, GUI dialogs in CLI tests
- **Impact**: All user communication code
- **Solution**: Reset handler between tests

```python
@pytest.fixture(autouse=True)
def clean_message_handler():
    ClassicLib.MessageHandler._message_handler = None
    yield
    ClassicLib.MessageHandler._message_handler = None
```

**📖 [Complete Guide: Testing MessageHandler](testing_message_handler.md)**

### Database Pools

**Problem**: Connection pools that persist across tests
- **Symptoms**: Database locked errors, connection leaks, query cache pollution
- **Impact**: All FormID lookup operations
- **Solution**: Reset pool singletons and close connections

```python
@pytest.fixture(autouse=True)
def reset_database_pools():
    SyncDatabasePool._instance = None
    yield
    if SyncDatabasePool._instance:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None
```

**📖 [Complete Guide: Testing Database Pools](testing_database_pools.md)**

### ThreadSafeLogCache

**Problem**: Thread-safe cache with persistent locks and data
- **Symptoms**: Cached logs from previous tests, thread lock conflicts
- **Impact**: All crash log processing
- **Solution**: Create fresh instances per test

```python
@pytest.fixture
def fresh_log_cache(tmp_path):
    log_files = [tmp_path / f"test_{i}.log" for i in range(3)]
    cache = ThreadSafeLogCache(log_files)
    yield cache
    cache.close()
    cache.cache.clear()
```

**📖 [Complete Guide: Testing ThreadSafeLogCache](testing_thread_safe_cache.md)**

### FileIOCore

**Problem**: Indirect coupling through AsyncBridge singleton
- **Symptoms**: File operations use stale bridge state, encoding pollution
- **Impact**: All file I/O operations
- **Solution**: Mock AsyncBridge or reset bridge state

```python
@patch("ClassicLib.FileIOCore.AsyncBridge")
def test_file_operations(mock_bridge_class):
    mock_bridge = MagicMock()
    mock_bridge_class.get_instance.return_value = mock_bridge
    mock_bridge.run_async.return_value = "file_content"
```

**📖 [Complete Guide: Testing FileIOCore](testing_fileio_core.md)**

## Quick Reference: Pollution Prevention Patterns

### 1. Universal Cleanup Fixture

Create a comprehensive fixture that handles all major pollution sources:

```python
@pytest.fixture(autouse=True)
def prevent_test_pollution():
    """Prevent test pollution from all major sources."""
    # Clear singletons
    AsyncBridge._instance = None
    GlobalRegistry._registry.clear()
    ClassicLib.MessageHandler._message_handler = None
    SyncDatabasePool._instance = None

    yield

    # Post-test cleanup
    AsyncBridge._instance = None
    GlobalRegistry._registry.clear()
    ClassicLib.MessageHandler._message_handler = None
    if SyncDatabasePool._instance:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None
```

### 2. Mocking Strategy

For unit tests, mock the pollution sources:

```python
# Mock all major singletons
@patch("module.AsyncBridge")
@patch("module.yaml_settings")
@patch("module.GlobalRegistry")
def test_unit_with_mocks(mock_registry, mock_yaml, mock_bridge):
    # Configure mocks
    mock_bridge.get_instance.return_value.run_async.return_value = "result"
    mock_yaml.return_value = "setting_value"
    mock_registry.get.return_value = "registry_value"
```

### 3. Integration Test Pattern

For integration tests, use real components with proper cleanup:

```python
@pytest.fixture
def integration_setup():
    """Setup for integration tests with real components."""
    # Reset all singletons
    AsyncBridge._instance = None
    GlobalRegistry._registry.clear()

    # Initialize fresh components
    handler = init_message_handler(parent=None, is_gui_mode=False)

    yield

    # Thorough cleanup
    # ... cleanup code
```

## Parallel Testing with pytest-xdist

When running tests in parallel, additional considerations apply:

### 1. Worker Isolation

```python
import os

@pytest.fixture
def worker_isolation():
    """Ensure proper isolation for parallel workers."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    # Worker-specific cleanup
    AsyncBridge._instance = None
    GlobalRegistry._registry.clear()

    yield worker_id

    # Worker-specific cleanup
    AsyncBridge._instance = None
    GlobalRegistry._registry.clear()
```

### 2. File Isolation

```python
@pytest.fixture
def worker_tmp_path(tmp_path):
    """Worker-specific temporary paths."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')
    worker_path = tmp_path / f"worker_{worker_id}"
    worker_path.mkdir(exist_ok=True)
    return worker_path
```

## Detection and Debugging

### 1. Pollution Detection Fixture

```python
@pytest.fixture(autouse=True)
def detect_pollution():
    """Detect pollution between tests."""
    # Check for existing pollution before test
    if AsyncBridge._instance is not None:
        pytest.fail("AsyncBridge pollution detected!")
    if GlobalRegistry._registry:
        pytest.fail(f"GlobalRegistry pollution: {GlobalRegistry._registry}")
    if ClassicLib.MessageHandler._message_handler is not None:
        pytest.fail("MessageHandler pollution detected!")

    yield

    # Could also check after test for leaks
```

### 2. Resource Monitoring

```python
import psutil
import os

@pytest.fixture(autouse=True)
def monitor_resources():
    """Monitor system resources for leaks."""
    process = psutil.Process(os.getpid())

    initial_memory = process.memory_info().rss
    initial_files = len(process.open_files())

    yield

    final_memory = process.memory_info().rss
    final_files = len(process.open_files())

    if final_memory > initial_memory * 1.1:  # 10% increase
        print(f"WARNING: Memory increased from {initial_memory} to {final_memory}")

    if final_files > initial_files:
        print(f"WARNING: File handles leaked: {initial_files} -> {final_files}")
```

## Best Practices Summary

### ✅ DO

1. **Use fixtures for cleanup** - Automate pollution prevention
2. **Mock in unit tests** - Isolate components being tested
3. **Reset singletons** - Clear state between tests
4. **Use tmp_path** - Isolate file operations
5. **Test in isolation** - Each test should be independent
6. **Handle errors properly** - Don't let errors leave state
7. **Use autouse fixtures** - Automatic cleanup without remembering

### ❌ DON'T

1. **Share state** - Never rely on state from other tests
2. **Modify production config** - Use mocks or test-specific settings
3. **Leave resources open** - Always clean up connections, files, etc.
4. **Ignore warnings** - AsyncIO and resource warnings indicate problems
5. **Skip cleanup** - Always clean up, even if test fails
6. **Use global variables** - Avoid module-level state
7. **Trust test order** - Tests should pass in any order

## Migration Guide

If you have existing tests that may be polluted:

### 1. Identify Pollution

Run tests multiple times in different orders:
```bash
# Test for pollution
pytest tests/ --random-order
pytest tests/ --maxfail=1  # Stop on first failure
pytest tests/ -n 4  # Parallel execution
```

### 2. Add Universal Fixture

Add the comprehensive cleanup fixture to `conftest.py`:
```python
# In tests/conftest.py
@pytest.fixture(autouse=True)
def prevent_all_pollution():
    # ... comprehensive cleanup
```

### 3. Fix Specific Issues

For each failing test, apply the appropriate pattern from the specific guides.

### 4. Verify Fix

```bash
# Verify tests are now isolated
pytest tests/ -n auto --count=10  # Run each test 10 times in parallel
```

## Performance Considerations

Test pollution prevention has minimal performance impact when done correctly:

- **Mocking** is faster than real components
- **Fixture cleanup** adds ~1ms per test
- **Parallel isolation** enables faster overall execution
- **Resource cleanup** prevents memory leaks that slow down test suites

## Related Documentation

### Component-Specific Guides
- 📖 [Testing AsyncBridge](testing_async_bridge.md) - Async/sync bridge mocking patterns
- 📖 [Testing GlobalRegistry](testing_global_registry.md) - Singleton registry isolation
- 📖 [Testing YamlSettingsCache](testing_yaml_cache.md) - Configuration testing without pollution
- 📖 [Testing MessageHandler](testing_message_handler.md) - Message system isolation patterns
- 📖 [Testing Database Pools](testing_database_pools.md) - Connection pool resource management
- 📖 [Testing ThreadSafeLogCache](testing_thread_safe_cache.md) - Thread-safe cache isolation
- 📖 [Testing FileIOCore](testing_fileio_core.md) - File I/O operations without bridge pollution

### CLASSIC Testing Documentation
- 🧪 [Testing Guidelines in CLAUDE.md](../CLAUDE.md#testing-patterns) - General testing patterns for CLASSIC
- 🔧 [Pre-commit Hooks](../CLAUDE.md#pre-commit-hooks) - Automated pollution prevention

## Conclusion

Test pollution is a serious issue that can make test suites unreliable and debugging nightmarish. By understanding the pollution sources in CLASSIC and applying the prevention patterns outlined in this guide, you can create a robust, reliable test suite that works correctly in parallel execution.

The key principles are:
1. **Isolate tests** - Each test should be completely independent
2. **Clean up thoroughly** - Reset all global state between tests
3. **Mock when possible** - Unit tests should mock pollution sources
4. **Test the patterns** - Verify your pollution prevention works

Remember: A test that passes only sometimes is worse than a test that always fails, because it gives false confidence while hiding real problems.
