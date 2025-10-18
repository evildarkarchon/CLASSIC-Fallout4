# PyO3-Async-Runtimes Implementation Plan

## Overview

This document outlines the plan to migrate from blocking Rust FFI calls to **true async Python functions** using `pyo3-async-runtimes`. This will eliminate all event loop blocking issues and enable native async/await in Python backed by Rust's Tokio runtime.

## Current Problem

**Current Architecture (BLOCKING):**
```
Python async def get_entry()
  → Direct call to Rust
    → Rust releases GIL
    → But BLOCKS the calling thread with get_runtime().block_on()
      → Thread blocked until Rust completes
```

**Issues:**
- ❌ Python async functions are actually synchronous wrappers
- ❌ Rust blocks threads even though it releases GIL
- ❌ Event loops get blocked waiting for Rust
- ❌ No true concurrency despite async/await syntax
- ❌ Complex workarounds (thread pools, event loop chunking)

## Target Architecture (TRUE ASYNC)

**New Architecture (NON-BLOCKING):**
```
Python async def get_entry()
  → Returns Python coroutine immediately
    → Backed by Rust Future
      → Tokio runtime handles execution
        → Python event loop awaits completion
          → True async concurrency ✅
```

**Benefits:**
- ✅ True async Python functions (real coroutines)
- ✅ No thread blocking - Rust futures integrate with Python's event loop
- ✅ Native concurrent execution without thread pools
- ✅ Clean architecture - no workarounds needed
- ✅ Full Rust performance + Python async patterns

## Implementation Plan

### Phase 1: Add Dependencies (All `-py` Crates)

**Crates to Update:**
- `classic-database-py`
- `classic-file-io-py`
- `classic-scanlog-py`
- `classic-yaml-py`
- `classic-config-py`

**Changes to `Cargo.toml`:**
```toml
[dependencies]
pyo3 = { workspace = true }
pyo3-async-runtimes = { version = "0.26", features = ["tokio-runtime"] }
tokio = { workspace = true }  # Already have this
classic-shared = { path = "../classic-shared" }  # For get_runtime()
```

### Phase 2: Update Classic-Database-Py

**File:** `classic-database-py/src/pool.rs`

**Before (Blocking):**
```rust
#[pyo3(name = "get_entry")]
pub fn py_get_entry(&self, py: Python<'_>, formid: String, plugin: String, table: Option<String>)
    -> PyResult<Option<String>>
{
    without_gil(py, || {
        get_runtime().block_on(async {  // BLOCKS!
            self.inner.get_entry(&formid, &plugin, table.as_deref())
                .await
                .map_err(to_pyerr)
        })
    })
}
```

**After (True Async):**
```rust
use pyo3_async_runtimes::tokio::future_into_py;

#[pyo3(name = "get_entry")]
pub fn py_get_entry<'py>(
    &self,
    py: Python<'py>,
    formid: String,
    plugin: String,
    table: Option<String>
) -> PyResult<Bound<'py, PyAny>> {
    let inner = self.inner.clone();

    // Returns Python coroutine immediately - no blocking!
    future_into_py(py, async move {
        inner.get_entry(&formid, &plugin, table.as_deref())
            .await
            .map_err(to_pyerr)
    })
}
```

**Key Changes:**
1. Return type: `PyResult<Option<String>>` → `PyResult<Bound<'py, PyAny>>` (coroutine)
2. Use `future_into_py()` instead of `block_on()`
3. Clone `self.inner` (Arc) for move into async block
4. No `without_gil()` needed - function returns immediately

### Phase 3: Update Classic-File-IO-Py

**File:** `classic-file-io-py/src/lib.rs`

**Before (Blocking):**
```rust
#[pyo3(name = "read_file")]
pub fn py_read_file(&self, py: Python<'_>, path: String) -> PyResult<String> {
    without_gil(py, || {
        get_runtime().block_on(async {  // BLOCKS!
            self.inner.read_file(&path).await.map_err(to_pyerr)
        })
    })
}
```

**After (True Async):**
```rust
use pyo3_async_runtimes::tokio::future_into_py;

#[pyo3(name = "read_file")]
pub fn py_read_file<'py>(
    &self,
    py: Python<'py>,
    path: String
) -> PyResult<Bound<'py, PyAny>> {
    let inner = self.inner.clone();

    future_into_py(py, async move {
        inner.read_file(&path).await.map_err(to_pyerr)
    })
}
```

### Phase 4: Update Python Wrappers

**Python side stays mostly the same** - functions are already `async def`:

**Before:**
```python
async def get_entry(self, formid: str, plugin: str) -> str | None:
    # Was calling blocking Rust
    result = self._rust_pool.get_entry(formid, plugin, game_table)
    return result
```

**After:**
```python
async def get_entry(self, formid: str, plugin: str) -> str | None:
    # Now awaits true Python coroutine from Rust!
    result = await self._rust_pool.get_entry(formid, plugin, game_table)
    return result
```

**Key Change:** Add `await` before Rust calls! That's it!

### Phase 5: Remove Thread Pool Workarounds

**Delete these patterns:**
```python
# OLD - No longer needed!
await asyncio.to_thread(self._rust_pool.get_entry, ...)
await loop.run_in_executor(None, self._rust_pool.get_entry, ...)

# NEW - Just await!
await self._rust_pool.get_entry(...)
```

**Remove from:**
- `ClassicLib/rust/database_rust.py` - All asyncio.to_thread calls
- `ClassicLib/rust/file_io_rust.py` - All asyncio.to_thread calls
- `ClassicLib/ScanLog/ScanLogsExecutor.py` - Thread-per-log workaround
- `ClassicLib/Interface/Workers.py` - Can restore simple run_until_complete

### Phase 6: Testing Strategy

**Unit Tests:**
```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_async_database_query():
    from classic_core.database import RustDatabasePool

    pool = RustDatabasePool(10, 300, "Fallout4")
    pool.initialize([str(db_path)])

    # Should be true coroutine now
    result = pool.get_entry("00000007", "Fallout4.esm", "Fallout4")
    assert asyncio.iscoroutine(result), "Should return coroutine!"

    # Await it
    entry = await result
    assert entry is not None
```

**Performance Test:**
```python
import asyncio
import time

async def test_concurrent_queries():
    pool = RustDatabasePool(10, 300, "Fallout4")
    pool.initialize([str(db_path)])

    # Create 100 concurrent queries
    tasks = [
        pool.get_entry(f"0000000{i % 10}", "Fallout4.esm", "Fallout4")
        for i in range(100)
    ]

    start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    print(f"100 concurrent queries in {elapsed:.3f}s")
    # Should be MUCH faster than sequential
```

## Migration Checklist

### Database Module (`classic-database-py`)
- [ ] Add pyo3-async-runtimes dependency
- [ ] Update `get_entry()` to return coroutine
- [ ] Update `batch_lookup()` to return coroutine
- [ ] Update `get_entries_batch()` to return coroutine
- [ ] Update `initialize()` to return coroutine
- [ ] Update `close()` to return coroutine
- [ ] Update Python wrapper to await Rust calls
- [ ] Remove asyncio.to_thread workarounds
- [ ] Test with pytest-asyncio

### File I/O Module (`classic-file-io-py`)
- [ ] Add pyo3-async-runtimes dependency
- [ ] Update `read_file()` to return coroutine
- [ ] Update `read_lines()` to return coroutine
- [ ] Update `write_file()` to return coroutine
- [ ] Update `read_multiple_files()` to return coroutine
- [ ] Update Python wrapper to await Rust calls
- [ ] Remove asyncio.to_thread workarounds
- [ ] Test with pytest-asyncio

### YAML Module (`classic-yaml-py`)
- [ ] Add pyo3-async-runtimes dependency (if needed)
- [ ] Evaluate if YAML operations need async (likely sync is fine)

### Scanlog Module (`classic-scanlog-py`)
- [ ] Add pyo3-async-runtimes dependency
- [ ] Update `parse_complete()` to return coroutine
- [ ] Update `extract_section()` to return coroutine
- [ ] Update Python wrapper to await Rust calls
- [ ] Test with pytest-asyncio

### Application Layer
- [ ] Remove thread-per-log workaround from ScanLogsExecutor
- [ ] Restore simple event loop in Workers.py
- [ ] Remove all asyncio.to_thread calls
- [ ] Update OrchestratorCore to await Rust calls
- [ ] Test full scan performance
- [ ] Verify progress bar updates smoothly

## Expected Performance Improvements

**Current (with workarounds):**
- Scan time: 50-80 seconds (varies)
- Progress: Jerky or frozen
- Concurrency: Limited by thread pool

**After Migration:**
- Scan time: **15-25 seconds** (true parallelism)
- Progress: Smooth real-time updates
- Concurrency: Full async concurrency (100+ operations)

## Rollback Plan

If issues occur:

1. **Keep Git Branch:** Create `feature/pyo3-async-runtimes` branch
2. **Incremental Migration:** Migrate one module at a time
3. **Feature Flag:** Can add Cargo feature to toggle old/new behavior
4. **Easy Revert:** Just checkout main branch

## Reference Links

- PyO3-Async-Runtimes GitHub: https://github.com/PyO3/pyo3-async-runtimes
- Docs.rs: https://docs.rs/pyo3-async-runtimes/latest/pyo3_async_runtimes/
- PyO3 Async Guide: https://pyo3.rs/latest/ecosystem/async-await
- Stack Overflow Examples: Search "pyo3-async-runtimes tokio"

## Timeline Estimate

- **Phase 1 (Dependencies):** 30 minutes
- **Phase 2 (Database Module):** 2 hours
- **Phase 3 (File I/O Module):** 2 hours
- **Phase 4 (Python Wrappers):** 1 hour
- **Phase 5 (Remove Workarounds):** 1 hour
- **Phase 6 (Testing):** 2 hours

**Total:** ~8-10 hours for complete migration

## Success Criteria

✅ All Rust functions return Python coroutines
✅ No blocking calls (no `block_on()` in Rust)
✅ No thread pool workarounds in Python
✅ Scan completes in <30 seconds
✅ Progress bar updates smoothly
✅ All tests pass
✅ No event loop conflicts
