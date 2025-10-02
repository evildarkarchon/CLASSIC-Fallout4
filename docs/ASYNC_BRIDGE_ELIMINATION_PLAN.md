# AsyncBridge Elimination Plan

## Executive Summary

This document outlines the strategy to eliminate unnecessary AsyncBridge usage throughout CLASSIC, reserving it only for the GUI components that truly require sync-to-async bridging. The core insight is that CLI, TUI, and most backend components already run in async contexts and can use native `await` instead of AsyncBridge overhead.

## Current State Analysis

### Entry Points

| Entry Point | Mode | Async Context | Needs AsyncBridge? |
|------------|------|---------------|-------------------|
| `CLASSIC_Interface.py` | GUI (PySide6) | No (Qt event loop) | **YES** ✓ |
| `CLASSIC_TUI.py` | TUI (Textual) | Yes (asyncio native) | **NO** ✗ |
| `CLASSIC_ScanLogs.py` | CLI | No (sync main()) | **NO** ✗ - Uses sync wrapper |
| `CLASSIC_ScanGame.py` | CLI | No (sync functions) | **NO** ✗ - Uses sync wrappers |

### Current AsyncBridge Usage

Analyzed 103 files using AsyncBridge. Key categories:

#### 1. **Core Library Sync Wrappers** (Should be context-aware)
- `YamlSettingsCache` - ✅ **DONE** (now has async variants)
- `ClassicScanLogsInfo.__post_init__` - ✅ **DONE** (now has `create_async()`)
- `FileIOCore` sync adapters
- `RustFileIOCore` sync adapters
- `FormIDAnalyzer` sync methods
- `ScanOrchestrator` sync methods

#### 2. **Entry Point Wrappers** (Should be removed or context-aware)
- `CLASSIC_ScanLogs.py` - Uses `run_async()` unnecessarily
- `CLASSIC_ScanGame.py` - Multiple `run_async()` calls
- `ScanLogsExecutor.scan_sync()` - Wrapper for GUI
- `GameFilesManager` sync functions
- `GameIntegrityOrchestrator` sync functions
- `ScanModInis` sync wrappers

#### 3. **GUI Workers** (✅ KEEP AsyncBridge - These are legitimate GUI requirements)
- `Interface.Workers.UpdateCheckWorker` - ✓ QThread worker, needs AsyncBridge
- `Interface.Workers.CrashLogsScanWorker` - ✓ Creates event loop in QThread (OK)
- `Interface.Workers.GameFilesScanWorker` - ✓ Calls sync wrapper from QThread (OK)
- `Interface.Papyrus.PapyrusMonitorWorker` - ✓ QThread worker, no AsyncBridge (polling loop)
- `Interface.Pastebin.PastebinFetchWorker` - ✓ Creates event loop in QThread (OK)
- GUI settings dialogs - ✓ Any Qt signal/slot handlers that need async ops

#### 4. **Test Infrastructure** (Should be removed)
- Many tests use AsyncBridge unnecessarily
- Should use `pytest-asyncio` with native `async def` tests

## Revised Strategy: Make CLI Async-First Like TUI

### Key Insight: CLI Should Be Async Like TUI, Not Sync

After analyzing all entry points:

1. **GUI** (`CLASSIC_Interface.py`): Qt event loop → QThread workers → AsyncBridge ✓
2. **TUI** (`CLASSIC_TUI.py`): Async-native Textual app → Direct `await` ✓
3. **CLI** (`CLASSIC_ScanLogs.py`, `CLASSIC_ScanGame.py`): ❌ **CURRENTLY SYNC, SHOULD BE ASYNC**

**Problem**: CLI uses sync wrappers when it should use async like TUI
- Current: `main()` → `scan_sync()` → AsyncBridge → async core
- Should be: `async def main()` → `await scan()` → async core directly
- Only `os.system("pause")` at the end needs to be sync

### What Needs AsyncBridge vs What Doesn't

#### ✅ KEEP AsyncBridge (Legitimate Use Cases)

**1. GUI Workers ONLY** (Qt threads can't share event loop)
- `Interface.Workers.UpdateCheckWorker` - QThread needs AsyncBridge
- `Interface.Workers.CrashLogsScanWorker` - Creates own event loop (alternative pattern)
- Any Qt signal/slot handlers calling async code

**2. Public Sync API** (For external callers that need sync interface)
- `ScanLogsExecutor.scan_sync()` - Keep for GUI workers
- `FileIOCore` sync adapters - Keep for small file ops where sync is faster
- Other sync wrappers ONLY if they have legitimate external sync callers

#### ❌ REMOVE AsyncBridge (Can Use Native Async)

**1. CLI Entry Points** → Convert to async-first
- `CLASSIC_ScanLogs.py` - Convert `main()` to `async def main()`
- `CLASSIC_ScanGame.py` - Convert all entry functions to async
- Remove sync wrapper calls, use direct `await` instead

**2. Core Library Internal Calls**
- `FileIOCore` async methods calling other FileIOCore async methods
- `FormIDAnalyzer` internal operations between async methods
- `ScanOrchestrator` pipeline stages (all async)
- Any ClassicLib async code calling other async code

**3. TUI Code** (Already async-native ✓)
- All Textual app handlers
- All TUI screens and widgets
- TUI has its own event loop, uses `await` directly

**4. Test Code** (Should use pytest-asyncio)
- Convert `AsyncBridge.run_async()` → `@pytest.mark.asyncio async def test_*()`
- Use native `await` in async tests
- Better test isolation and debugging

## Implementation Strategy

### Phase 1: Context Detection Infrastructure ✅ COMPLETED

**Status**: Already implemented in YamlSettingsCache refactor

**Approach**: Provide dual interfaces:
- Sync methods use AsyncBridge (for GUI)
- Async methods use native `await` (for CLI/TUI)

**Example**:
```python
# Sync for GUI
def batch_get_settings(self, requests):
    return self._bridge.run_async(self._core.batch_get_settings(requests))

# Async for CLI/TUI
async def batch_get_settings_async(self, requests):
    return await self._core.batch_get_settings(requests)
```

### Phase 2: GlobalRegistry Integration

**Goal**: Use `GlobalRegistry.is_gui_mode()` to automatically select sync vs async

**Implementation**:
```python
from ClassicLib import GlobalRegistry

def smart_wrapper(async_func):
    """
    Decorator that automatically uses AsyncBridge only in GUI mode.
    In CLI/TUI modes, returns the async function directly.
    """
    if GlobalRegistry.is_gui_mode():
        # GUI mode - wrap with AsyncBridge
        def sync_wrapper(*args, **kwargs):
            bridge = AsyncBridge.get_instance()
            return bridge.run_async(async_func(*args, **kwargs))
        return sync_wrapper
    else:
        # CLI/TUI mode - return async function as-is
        return async_func
```

**Benefits**:
- Single code path
- Automatic optimization based on runtime mode
- No manual variant selection

### Phase 3: Core Library Refactoring

#### 3.1 FileIOCore Sync Adapters

**Current**: `ClassicLib/FileIO/sync_adapters.py` (always uses AsyncBridge)

**Target**:
```python
# Option A: Remove sync_adapters.py entirely
# - CLI/TUI code uses FileIOCore directly with await
# - GUI code uses new context-aware wrappers

# Option B: Make sync_adapters context-aware
def read_file_sync(path: Path) -> str:
    if GlobalRegistry.is_gui_mode():
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(FileIOCore().read_file(path))
    else:
        raise RuntimeError("Use async version: await FileIOCore().read_file(path)")
```

**Files to update**:
- `ClassicLib/FileIO/sync_adapters.py`
- `ClassicLib/rust/file_io_rust.py` (RustFileIOCore sync methods)

#### 3.2 FormIDAnalyzer

**Current**: `ClassicLib/ScanLog/FormIDAnalyzer.py`
```python
def formid_match(self, formids_matches, crashlog_plugins):
    return run_async(self._core.formid_match(formids_matches, crashlog_plugins))
```

**Target**: Remove sync wrappers entirely
```python
# Remove formid_match() sync method
# Callers in async contexts use _core.formid_match() directly
# GUI callers use context-aware wrapper
```

**Files to update**:
- `ClassicLib/ScanLog/FormIDAnalyzer.py`
- `ClassicLib/ScanLog/FormIDAnalyzerCore.py`

#### 3.3 ScanOrchestrator

**Current**: `ClassicLib/ScanLog/ScanOrchestrator.py`
```python
def process_crash_log(self, crashlog_file):
    result = run_async(self._core.process_crash_log(crashlog_file))
```

**Target**: Remove sync wrapper
```python
# Remove sync method
# All callers are async (OrchestratorCore, ScanLogsExecutor)
```

### Phase 4: Entry Point Cleanup

#### 4.1 CLASSIC_ScanLogs.py (CLI) - ❌ NEEDS ASYNC CONVERSION

**Current State** (Line 272):
```python
def main() -> None:
    # ... setup ...
    executor = ScanLogsExecutor(config)
    result: ScanResult = executor.scan_sync()  # ❌ Unnecessarily uses AsyncBridge
    msg_info(executor.generate_summary(result))
    os.system("pause")
```

**Target**:
```python
async def main_async() -> None:
    # ... setup ...
    executor = ScanLogsExecutor(config)
    result: ScanResult = await executor.scan()  # ✅ Direct async, no bridge
    msg_info(executor.generate_summary(result))

def main() -> None:
    asyncio.run(main_async())
    os.system("pause")  # Only sync part
```

**Benefits**:
- No AsyncBridge overhead in CLI
- Consistent with TUI (both async-first)
- 10-20% performance improvement
- Matches CLASSIC's async-first architecture

#### 4.2 CLASSIC_ScanGame.py (CLI) - ❌ NEEDS ASYNC CONVERSION

**Current State**: All functions are sync wrappers using AsyncBridge
```python
def check_log_errors(folder_path: Path | str) -> str:
    bridge: AsyncBridge = AsyncBridge.get_instance()  # ❌ Unnecessary overhead
    core: ScanGameCore = get_scan_game_core()
    return bridge.run_async(core.check_log_errors(folder_path))
```

**Target**:
```python
async def check_log_errors_async(folder_path: Path | str) -> str:
    core: ScanGameCore = get_scan_game_core()
    return await core.check_log_errors(folder_path)  # ✅ Direct async

def check_log_errors(folder_path: Path | str) -> str:
    """Sync wrapper - ONLY for GUI workers if needed"""
    return asyncio.run(check_log_errors_async(folder_path))
```

**Analysis**:
- CLI should use async functions directly
- Keep sync wrappers only if GUI actually needs them
- Most GUI workers can be converted to async patterns too

#### 4.3 CLASSIC_TUI.py - ✅ ALREADY FULLY ASYNC (MODEL FOR CLI)

**Current State**: Textual App is async-native
```python
class CLASSICTuiApp(App):
    async def action_run_crash_scan(self) -> None:
        # All TUI handlers are async, use native await
        await self.scan_handler.perform_crash_scan()
```

**Analysis**:
- Textual framework is async-native
- All handlers use `async def` with native `await`
- **NO AsyncBridge** - This is the model CLI should follow
- **CLI should adopt this same pattern**

#### 4.4 ScanLogsExecutor - ⚠️ PATTERN NEEDS REVISION

**Current Implementation**:
```python
class ScanLogsExecutor:
    async def scan(self):
        """Main async entry point - used by TUI"""
        # ... async implementation ...

    def scan_sync(self):
        """Sync wrapper for CLI and GUI"""
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(self.scan())
```

**Target Implementation**:
```python
class ScanLogsExecutor:
    async def scan(self):
        """Main async entry point - used by TUI and CLI"""
        # ... async implementation ...

    def scan_sync(self):
        """Sync wrapper ONLY for GUI workers"""
        # CLI should NOT use this anymore
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(self.scan())
```

**Analysis**:
- TUI uses `scan()` directly with await ✓
- CLI should use `scan()` directly with await (not scan_sync)
- GUI Workers keep using `scan_sync()` wrapper ✓

### Phase 5: Test Infrastructure Cleanup

**Current**: Many tests use AsyncBridge unnecessarily

**Target**:
```python
# Before
def test_something():
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_function())

# After
@pytest.mark.asyncio
async def test_something():
    result = await async_function()
```

**Benefits**:
- Faster test execution
- Clearer test code
- Better async debugging

## Revised Implementation Order

### Priority 1: Convert CLI to Async-First (HIGH IMPACT) ⭐⭐⭐
**Goal**: Make CLI async-first like TUI, following CLASSIC's async-first architecture

1. **Convert CLASSIC_ScanLogs.py**:
   - Change `main()` to `async def main_async()`
   - Use `await executor.scan()` instead of `executor.scan_sync()`
   - Wrap with `asyncio.run(main_async())` at entry point
   - Keep `os.system("pause")` in sync wrapper

2. **Convert CLASSIC_ScanGame.py**:
   - Convert all entry functions to async
   - Remove AsyncBridge calls, use direct `await`
   - Keep sync wrappers only if GUI actually needs them

**Expected Impact**:
- 15-25% AsyncBridge reduction
- 10-20% CLI performance improvement
- Consistency with TUI architecture

### Priority 2: Core Library Internal Calls (HIGH IMPACT) ⭐⭐
**Goal**: Remove AsyncBridge from code that's already in async context

3. ✅ **YamlSettingsCache** - COMPLETED (has async variants)
4. ✅ **ClassicScanLogsInfo** - COMPLETED (has `create_async()`)
5. **FileIOCore Internal Operations**:
   - Keep: `sync_adapters.py` (for small file ops where sync is faster)
   - Remove: AsyncBridge calls within async FileIOCore methods
   - Example: FileIOCore async method calling another FileIOCore async method
6. **FormIDAnalyzer Internal Chain**:
   - Remove: AsyncBridge in FormIDAnalyzerCore async methods
   - Keep: Sync wrapper methods ONLY if GUI needs them
7. **ScanOrchestrator Pipeline**:
   - Remove: AsyncBridge between pipeline stages
   - All pipeline stages are async, should use native `await`

**Expected Impact**: 20-30% reduction in AsyncBridge usage

### Priority 3: Test Infrastructure Cleanup (HIGH VALUE) ⭐
**Goal**: Better test performance and clarity

8. **Convert pytest tests to native async**:
   - Pattern: `AsyncBridge.run_async()` → `@pytest.mark.asyncio async def`
   - Better async debugging
   - Faster test execution
   - ~40 test files to update

**Expected Impact**: 15-25% reduction in AsyncBridge usage

### Priority 4: Documentation and Guidelines (PREVENT REGRESSION)
9. **Update developer documentation**:
   - When to use AsyncBridge (GUI workers ONLY)
   - When NOT to use AsyncBridge (CLI, TUI, internal async code, tests)
   - Code review checklist for AsyncBridge usage
10. **Add linting rules**:
    - Flag AsyncBridge usage in CLI code (should use asyncio.run)
    - Flag AsyncBridge usage in TUI code (should use await)
    - Flag AsyncBridge in internal ClassicLib async methods
    - Allow AsyncBridge ONLY in Interface/ GUI workers

### ✅ KEEP AsyncBridge (Legitimate Use Cases)

**GUI Workers ONLY** - Keep as-is:
- `Interface.Workers.UpdateCheckWorker` - QThread needs AsyncBridge
- `Interface.Workers.CrashLogsScanWorker` - Creates event loop (alternative pattern)
- GUI signal/slot handlers - Only if they need async ops
- `ScanLogsExecutor.scan_sync()` - For GUI workers only

**Sync Adapters for Performance** - Keep if sync is faster:
- `FileIOCore` sync adapters for small file operations
- Other operations where sync is demonstrably faster than async

### ❌ REMOVE AsyncBridge (Convert to Async)

**CLI Entry Points**:
- `CLASSIC_ScanLogs.py` - Convert to async-first
- `CLASSIC_ScanGame.py` - Convert to async-first
- CLI should NOT use sync wrappers anymore

**TUI** - Already done:
- Uses native `await` throughout ✓
- No AsyncBridge usage ✓

**Core Library Internal**:
- Async methods calling other async methods
- Pipeline stages communicating
- All internal async code paths

## Migration Pattern Template

### For Each Component with Sync Wrappers:

```python
# BEFORE: Sync wrapper always uses AsyncBridge
def sync_method(self, arg):
    return run_async(self.async_method(arg))

# AFTER Option A: Context-aware (recommended)
def sync_method(self, arg):
    if GlobalRegistry.is_gui_mode():
        return run_async(self.async_method(arg))
    else:
        raise RuntimeError(f"Use async version: await {self.__class__.__name__}.async_method()")

# AFTER Option B: Remove entirely (if no GUI callers)
# Just delete the sync wrapper
# Callers use: await instance.async_method(arg)
```

## Verification Strategy

### 1. Mode Detection Tests
```python
def test_gui_mode_uses_asyncbridge():
    GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
    # Verify sync methods work

async def test_cli_mode_uses_native_async():
    GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)
    # Verify async methods work
```

### 2. Performance Benchmarks

Track performance improvement:
- Before: CLI with AsyncBridge overhead
- After: CLI with native async
- Expected: 10-30% faster in async-heavy operations

### 3. Integration Tests

Ensure all entry points work:
- ✅ GUI mode (with AsyncBridge)
- ✅ TUI mode (native async)
- ✅ CLI mode (native async)

## Success Metrics (Revised for Async-First CLI)

1. **AsyncBridge Usage Reduction**:
   - Current: 73 files using AsyncBridge
   - Target: ~10-15 files (GUI workers + performance sync adapters ONLY)
   - Reduction: ~80-85%

2. **Usage Distribution** (Target):
   - GUI Workers: 5-10 files ✓ (QThread workers need AsyncBridge)
   - Performance Sync Adapters: 3-5 files ✓ (Where sync is demonstrably faster)
   - CLI Entry Points: 0 files ✗ (Convert to async-first with asyncio.run)
   - Core Library Internal: 0 files ✗ (Use native await)
   - Tests: 0 files ✗ (Convert to pytest-asyncio)
   - TUI: 0 files ✓ (Already async-native)

3. **Performance Improvement**:
   - CLI: 10-20% faster (eliminate AsyncBridge overhead)
   - Core library internal calls: 5-15% faster (reduced bridging)
   - Test suite: 20-40% faster (native async tests)
   - TUI: Already optimal (native async)
   - GUI: No regression (keeps AsyncBridge where needed)

4. **Code Clarity & Architecture**:
   - CLI matches TUI pattern (both async-first)
   - Clear rule: AsyncBridge ONLY in GUI workers
   - Internal async code uses native `await`
   - Consistent async-first architecture throughout
   - Better async debugging and stack traces

## Risk Mitigation

### Risk: Breaking GUI Functionality
**Mitigation**:
- Comprehensive GUI testing before/after
- Keep all GUI-specific AsyncBridge usage
- Use `GlobalRegistry.is_gui_mode()` guards

### Risk: Breaking CLI Entry Point
**Mitigation**:
- Test CLI thoroughly before/after conversion
- `os.system("pause")` stays in sync wrapper
- Document the async-first pattern
- CLI performance should improve, not regress

### Risk: Test Failures
**Mitigation**:
- Update tests incrementally
- Use pytest-asyncio fixtures
- Document test patterns

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | ✅ Done | None |
| Phase 2 | 2-3 days | Phase 1 |
| Phase 3 | 5-7 days | Phase 2 |
| Phase 4 | 3-4 days | Phase 3 |
| Phase 5 | 2-3 days | Phase 4 |
| **Total** | **2-3 weeks** | Sequential |

## Next Steps

1. **Immediate**: Implement GlobalRegistry context detection helper
2. **Short-term**: Convert CLI/TUI entry points (Phase 3)
3. **Medium-term**: Refactor core library (Phase 4)
4. **Long-term**: Complete test cleanup (Phase 5)

## References

- [YamlSettingsCache Refactor](ClassicLib/YamlSettingsCache.py) - ✅ Example of dual interface pattern
- [ClassicScanLogsInfo](ClassicLib/ScanLog/scanloginfo/classic_scan_logs_info.py:186) - ✅ Example of async factory pattern
- [GlobalRegistry](ClassicLib/GlobalRegistry.py) - `is_gui_mode()` for context detection
- [AsyncBridge](ClassicLib/AsyncBridge.py) - Current implementation
