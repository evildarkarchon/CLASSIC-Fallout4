# AsyncBridge Refactoring Migration Guide

This document tracks the migration of AsyncBridge usage from non-compliant patterns to the documented architecture.

## Background

Per project documentation (`.claude/rules/08-memories.md`), AsyncBridge is ONLY for:
1. **GUI workers** (Qt threads)
2. **Testing**

Production CLI code MUST use the async-first pattern with a single `asyncio.run()` at the entry point.

## Import Classification

### Tier 1: Core (Never Refactor)
These are the implementation files for AsyncBridge itself.

| File | Status | Notes |
|------|--------|-------|
| `ClassicLib/AsyncBridge.py` | Keep | Implementation itself |
| `ClassicLib/_async_utils/__init__.py` | Keep | Re-exports |
| `ClassicLib/_async_utils/bridge_helpers.py` | Keep | Helper implementation |

### Tier 2: Legitimate (Keep)
These files correctly use AsyncBridge for GUI or testing purposes.

| File | Status | Notes |
|------|--------|-------|
| `ClassicLib/Interface/Workers.py` | Keep | QThread workers (correct usage) |
| `ClassicLib/Interface/Pastebin.py` | Keep | GUI-triggered operations |
| `ClassicLib/FileIO/sync_adapters.py` | Keep | GUI-only sync adapters |
| `ClassicLib/YamlSettings/sync/cache.py` | Keep | Lazy GUI initialization |
| `ClassicLib/__init__.py` | Keep | Re-export for convenience |
| `CLASSIC_Interface_QML.py` | Keep | GUI entry point |
| `tests/**/*.py` | Keep | All test files are valid users |

### Tier 3: Violations (Must Refactor)
These files use AsyncBridge in non-GUI production paths.

| File | Status | Migration Action |
|------|--------|------------------|
| `ClassicLib/ScanGame/ScanModInis.py` | **REFACTOR** | Mark sync functions as GUI-only |
| `ClassicLib/ScanGame/Config.py` | **REFACTOR** | Mark sync methods as GUI-only |
| `ClassicLib/ScanGame/GameFilesManager.py` | **REFACTOR** | Mark sync function as GUI-only |
| `ClassicLib/ScanGame/GameIntegrityOrchestrator.py` | **REFACTOR** | Mark sync functions as GUI-only |
| `ClassicLib/ScanGame/core/ini_fallback.py` | **REFACTOR** | Mark sync function as GUI-only |
| `ClassicLib/ScanLog/FormIDAnalyzerCore.py` | **REFACTOR** | Remove `run_async`, ensure callers use async |
| `ClassicLib/ScanLog/ScanLogsUtils.py` | **REFACTOR** | Remove `run_async`, ensure callers use async |
| `ClassicLib/ScanLog/FormIDAnalyzer.py` | **REFACTOR** | Mark sync wrappers as GUI-only |
| `ClassicLib/ScanLog/ScanLogsExecutor.py` | **REFACTOR** | Mark sync wrapper as GUI-only |
| `ClassicLib/rust/file_io_rust.py` | **REFACTOR** | Mark sync methods as GUI-only |
| `ClassicLib/rust/formid_rust.py` | **REFACTOR** | Document sync functions as GUI-only |
| `ClassicLib/rust/orchestrator_api.py` | **REFACTOR** | Document sync functions as GUI-only |
| `ClassicLib/rust/parser_rust.py` | **REFACTOR** | Document sync functions as GUI-only |
| `ClassicLib/FileGeneration.py` | **REFACTOR** | Mark sync function as GUI-only |
| `CLASSIC_ScanGame.py` | **REFACTOR** | Mark sync wrappers as GUI-only exports |

## Migration Approach

### Dual Interface Pattern

For modules shared by GUI and CLI, provide both interfaces:

```python
# Primary async API (CLI uses this directly)
async def scan_files_async() -> ScanResult:
    """Async file scanning.

    CLI code should call this directly within an async context.
    """
    ...

# GUI-only sync wrapper
def scan_files() -> ScanResult:
    """Sync file scanning. GUI workers only.

    WARNING: This function uses AsyncBridge internally and creates
    additional event loop overhead. Not for CLI use.

    For CLI usage, use scan_files_async() instead.
    """
    from ClassicLib.AsyncBridge import AsyncBridge
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(scan_files_async())
```

### Entry Point Pattern

CLI entry points follow async-first:

```python
async def main() -> None:
    # All async operations with direct await
    result = await scan_files_async()
    await write_results_async(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Refactoring Checklist

### ScanGame Modules
- [x] `ScanModInis.py`: Added GUI-only warnings to `scan_mod_inis()` and `check_vsync_settings()`
- [x] `Config.py`: Added GUI-only warnings to `get()` and `has()` methods
- [x] `GameFilesManager.py`: Already documented with IMPORTANT - Usage section
- [x] `GameIntegrityOrchestrator.py`: Already documented with IMPORTANT - Usage section
- [x] `core/ini_fallback.py`: Added GUI-only warning to `detect_all_issues()`

### ScanLog Modules
- [x] `FormIDAnalyzerCore.py`: Moved `run_async` to local scope, added GUI-only warnings
- [x] `ScanLogsUtils.py`: Moved `run_async` to local scope, added GUI-only warning to `crashlogs_scan()`
- [x] `FormIDAnalyzer.py`: Already documented as GUI-only in class docstring
- [x] `ScanLogsExecutor.py`: Already documented as GUI-only with Phase 2 context awareness

### Rust Wrapper Modules
- [x] `file_io_rust.py`: Added GUI-only warnings to `create_file_io_sync()` and `SyncWrapper`
- [x] `formid_rust.py`: Already documented with AsyncBridge usage examples
- [x] `orchestrator_api.py`: Already documented with AsyncBridge usage examples
- [x] `parser_rust.py`: Already documented with AsyncBridge usage examples

### Utility Modules
- [x] `FileGeneration.py`: Added GUI-only warning to `generate_all_files()`

### Entry Points
- [x] `CLASSIC_ScanGame.py`: Already documented at module level with usage patterns

## Validation Steps

1. Run full test suite: `uv run pytest -n auto`
2. Test GUI manually with real crash logs
3. Test CLI execution paths work correctly
4. Verify no new AsyncBridge imports in CLI execution paths
