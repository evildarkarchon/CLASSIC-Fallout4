# Async-First Migration Guide

## Overview

This guide helps developers migrate existing code to use the new async-first architecture in CLASSIC.

## Architecture Changes

### Old Pattern (Duplicated Sync/Async)
```python
# Synchronous version
def process_data(data):
    return sync_implementation(data)

# Async version
async def process_data_async(data):
    return await async_implementation(data)

# Feature flag checking
if settings.get("Enable Async"):
    result = await process_data_async(data)
else:
    result = process_data(data)
```

### New Pattern (Async-First with Sync Adapters)
```python
# Core async implementation
class ProcessorCore:
    async def process_data(self, data):
        # Single async implementation
        return await self._process(data)

# Sync adapter for backwards compatibility
def process_data(data):
    """Sync adapter for async process_data."""
    core = ProcessorCore()
    return asyncio.run(core.process_data(data))
```

## Migration Steps

### 1. File I/O Operations

#### Before:
```python
# Direct file reading
with open(file_path, 'r') as f:
    content = f.read()

# Or using utilities
content = open_file_with_encoding(file_path)
```

#### After:
```python
# Async approach
from ClassicLib.FileIOCore import FileIOCore

async def read_file_async():
    io_core = FileIOCore()
    content = await io_core.read_file(file_path)
    return content

# Sync approach (for backwards compatibility)
from ClassicLib.FileIOCore import read_file_sync

content = read_file_sync(file_path)
```

### 2. Crash Log Processing

#### Before:
```python
# Using ThreadSafeLogCache with sync loading
cache = ThreadSafeLogCache(log_files)
log_data = cache.read_log(log_name)
```

#### After:
```python
# ThreadSafeLogCache now uses async loading internally
# No changes needed in calling code
cache = ThreadSafeLogCache(log_files)  # Uses FileIOCore internally
log_data = cache.read_log(log_name)
```

### 3. FormID Analysis

#### Before:
```python
# Sync version
analyzer = FormIDAnalyzer()
analyzer.formid_match(formids, plugins, report)

# Async version
analyzer = AsyncFormIDAnalyzer()
await analyzer.formid_match_async(formids, plugins, report)
```

#### After:
```python
# Sync usage (unchanged)
analyzer = FormIDAnalyzer()
analyzer.formid_match(formids, plugins, report)

# Async usage (direct)
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore
analyzer = FormIDAnalyzerCore()
await analyzer.formid_match(formids, plugins, report)
```

### 4. Batch Operations

#### Before:
```python
# Sequential file reading
results = {}
for file in files:
    with open(file, 'r') as f:
        results[file.name] = f.read()
```

#### After:
```python
# Concurrent file reading
from ClassicLib.FileIOCore import FileIOCore

async def read_all_files():
    io_core = FileIOCore()
    results = await io_core.read_multiple_files(files)
    return results

# Or using sync adapter
from ClassicLib.FileIOCore import FileIOCore
import asyncio

results = asyncio.run(FileIOCore().read_multiple_files(files))
```

## Component Migration Reference

| Old Component | New Component | Notes |
|--------------|--------------|-------|
| `AsyncScanGame.py` | `ScanGameCore.py` | Async-first implementation |
| `AsyncFormIDAnalyzer.py` | `FormIDAnalyzerCore.py` | Use FormIDAnalyzer for sync |
| `AsyncScanOrchestrator.py` | `OrchestratorCore.py` | Unified async implementation |
| `open_file_with_encoding()` | `FileIOCore.read_file()` | Automatic encoding detection |
| `crashlogs_reformat_with_async()` | `FileIOCore` methods | Use FileIOCore directly |
| `integrate_async_file_loading()` | `FileIOCore.read_multiple_files()` | Batch operations |

## Deprecated Functions

The following functions are deprecated and will be removed in a future version:

### ClassicLib/ScanLog/AsyncFileIO.py
- `crashlogs_reformat_with_async()` → Use `crashlogs_reformat_async()` directly
- `integrate_async_file_loading()` → Use `FileIOCore.read_multiple_files()`
- `write_report_with_async()` → Use `FileIOCore.write_crash_report()`

### ClassicLib/ScanLog/AsyncFormIDAnalyzer.py
- Entire module deprecated → Use `FormIDAnalyzer` (sync) or `FormIDAnalyzerCore` (async)

## Testing Migration

### Old Test Pattern:
```python
def test_sync_function():
    result = process_data(test_data)
    assert result == expected

async def test_async_function():
    result = await process_data_async(test_data)
    assert result == expected
```

### New Test Pattern:
```python
@pytest.mark.asyncio
async def test_async_core():
    core = ProcessorCore()
    result = await core.process_data(test_data)
    assert result == expected

def test_sync_adapter():
    result = process_data(test_data)  # Tests sync adapter
    assert result == expected
```

## Performance Considerations

1. **Async I/O Benefits**: The new architecture provides significant performance improvements for I/O-bound operations
2. **Batch Processing**: Use `FileIOCore.read_multiple_files()` for concurrent file operations
3. **Resource Management**: FileIOCore handles semaphores and resource limits automatically

## Common Pitfalls

1. **Don't mix sync and async inappropriately**:
   ```python
   # Wrong
   async def process():
       data = open(file, 'r').read()  # Sync I/O in async function
   
   # Right
   async def process():
       io_core = FileIOCore()
       data = await io_core.read_file(file)
   ```

2. **Use the right adapter**:
   ```python
   # In sync context
   content = read_file_sync(path)
   
   # In async context
   content = await FileIOCore().read_file(path)
   ```

3. **Handle deprecation warnings**:
   ```python
   # Update deprecated calls
   # Old: crashlogs_reformat_with_async(logs, remove_list)
   # New: asyncio.run(crashlogs_reformat_async(logs, remove_list))
   ```

## Migration Checklist

- [ ] Identify all file I/O operations in your code
- [ ] Replace direct file operations with FileIOCore methods
- [ ] Update imports to use new module locations
- [ ] Run tests to ensure compatibility
- [ ] Address any deprecation warnings
- [ ] Remove feature flag checks (no longer needed)
- [ ] Update documentation to reflect new patterns

## Support

For questions or issues during migration:
1. Check the deprecation warnings for specific guidance
2. Refer to the test suite for usage examples
3. Review FileIOCore documentation for available methods