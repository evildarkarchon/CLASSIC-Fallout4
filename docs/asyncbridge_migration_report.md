# AsyncBridge Migration Report

## Overview
This document summarizes the migration from `asyncio.run()` to `AsyncBridge` throughout the CLASSIC codebase to ensure thread-safe async execution and proper test isolation.

## Migration Completed
Date: 2025-09-15

## Why AsyncBridge?

The `AsyncBridge` class provides several critical advantages over direct `asyncio.run()` usage:

1. **Thread-Safe Execution**: Maintains a persistent event loop per thread
2. **Test Isolation**: Proper cleanup between tests prevents state leakage
3. **Performance**: Reuses event loops instead of creating new ones
4. **Consistency**: Unified async execution pattern across the codebase

## Files Migrated

### Production Code (2 files)
- `ClassicLib/ScanLog/AsyncIntegration.py`
  - Replaced `asyncio.run(async_crashlogs_scan())` with AsyncBridge

- `ClassicLib/ScanLog/AsyncFileIO.py`
  - Replaced `asyncio.run(timed_reformat_async(...))` with AsyncBridge

### Test Code (4 files)
- `tests/core/test_crash_log_processing_unit.py`
  - Replaced `asyncio.run(process_with_orchestrator())` with AsyncBridge
  - Added `message_handler` and `async_bridge` fixtures

- `tests/core/test_crash_log_processing_integration.py`
  - Replaced `asyncio.run(process_with_orchestrator())` with AsyncBridge
  - Added `message_handler` and `async_bridge` fixtures

- `tests/performance/test_async_performance_error_handling.py`
  - Replaced two `asyncio.run()` calls with AsyncBridge
  - Added `message_handler` and `async_bridge` fixtures

- `tests/performance/test_async_performance_memory.py`
  - Replaced `asyncio.run(async_load())` with AsyncBridge
  - Added `message_handler` and `async_bridge` fixtures

## Migration Pattern

### Before:
```python
import asyncio

def run_sync():
    result = asyncio.run(async_function())
    return result
```

### After:
```python
from ClassicLib.AsyncBridge import AsyncBridge

def run_sync():
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_function())
    return result
```

## Test Fixture Requirements

All test functions that use AsyncBridge must include the `async_bridge` fixture to ensure proper cleanup:

```python
def test_something(tmp_path: Path, message_handler, async_bridge):
    """Test with AsyncBridge support."""
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_operation())
```

The `async_bridge` fixture:
- Manages thread-local AsyncBridge instances
- Ensures event loop cleanup between tests
- Prevents test pollution in parallel execution
- Automatically provided by `tests/fixtures/registry_fixtures.py`

## Benefits Achieved

1. **Eliminated Event Loop Conflicts**: No more "RuntimeError: asyncio.run() cannot be called from a running event loop"
2. **Improved Test Isolation**: Each test gets a clean AsyncBridge state
3. **Thread Safety**: Parallel test execution with pytest-xdist now works reliably
4. **Performance**: Reusing event loops reduces overhead
5. **Consistency**: Single pattern for sync-to-async bridging

## Verification

After migration, verification shows:
- ✅ No `asyncio.run()` calls remain in production code
- ✅ No `asyncio.run()` calls remain in test code
- ✅ All migrated files use AsyncBridge consistently
- ✅ All affected tests have required fixtures

## Usage Guidelines

### For New Code:
```python
# Always use AsyncBridge for sync-to-async calls
from ClassicLib.AsyncBridge import AsyncBridge

def sync_wrapper():
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(async_function())
```

### For Tests:
```python
# Always include async_bridge fixture
def test_async_operations(async_bridge):
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_operation())
    assert result is not None
```

### Never Do:
- Don't use `asyncio.run()` directly
- Don't forget the `async_bridge` fixture in tests
- Don't create new event loops manually

## Related Documentation
- [Test Fixture Standards](testing_fixture_standards.md)
- [Test Isolation Audit Report](test_isolation_audit_report.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
