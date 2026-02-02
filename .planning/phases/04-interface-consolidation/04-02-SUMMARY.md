---
phase: 04-interface-consolidation
plan: 02
subsystem: async-bridge
tags: [async, sync-wrapper, create_sync_wrapper, bridge_helpers, sync_adapters]
dependency-graph:
  requires: ["04-01"]
  provides: ["create_sync_wrapper removed", "bridge_helpers deleted", "sync_adapters deleted", "AsyncBridge.run_async() as sole GUI sync pattern"]
  affects: ["04-03"]
tech-stack:
  added: []
  patterns: ["AsyncBridge.run_async() direct call in GUI sync wrappers", "Module-level helper functions for file I/O"]
key-files:
  created:
    - ClassicLib/io/files/sync_helpers.py
  modified:
    - ClassicLib/scanning/logs/executor.py
    - CLASSIC_ScanGame.py
    - ClassicLib/scanning/game/wrye_check.py
    - ClassicLib/Interface/controllers/results_viewer.py
    - ClassicLib/support/xse.py
    - ClassicLib/support/docs_path.py
    - ClassicLib/io/yaml/sync/convenience.py
    - ClassicLib/io/files/__init__.py
    - ClassicLib/__init__.py
    - ClassicLib/_async_utils/__init__.py
    - ClassicLib/core/async_bridge.py
  deleted:
    - ClassicLib/io/files/sync_adapters.py
    - ClassicLib/_async_utils/bridge_helpers.py
decisions:
  - "bridge_helpers functions (run_async, context_aware_sync, smart_await) inlined into async_bridge.py"
  - "_async_utils package kept for backward compatibility re-exports"
  - "Each caller gets module-level helper functions instead of centralized sync adapters"
metrics:
  duration: "17m"
  completed: "2026-02-02"
---

# Phase 4 Plan 2: Remove create_sync_wrapper Summary

**One-liner:** Eliminated create_sync_wrapper and its two implementation files, migrating all 8 callers to direct AsyncBridge.run_async() calls.

## What Was Done

### Task 1a: Create sync_helpers.py and migrate executor.py / CLASSIC_ScanGame.py
- Created `ClassicLib/io/files/sync_helpers.py` with `stream_lines_sync` (pure sync, no bridge)
- Migrated `executor.py` `scan_sync()` from `create_sync_wrapper(self.execute_scan, strict=True)` to `AsyncBridge.get_instance().run_async(self.execute_scan())`
- Migrated `CLASSIC_ScanGame.py` three sync wrappers (`check_log_errors`, `scan_mods_unpacked`, `scan_mods_archived`) to explicit `AsyncBridge.get_instance().run_async()` calls

### Task 1b: Migrate all sync file I/O callers and update re-exports
- `wrye_check.py`: replaced `read_file_sync` import with local `_read_file()` helper using AsyncBridge
- `results_viewer.py`: replaced `read_file_sync` import with local `_read_file()` helper
- `xse.py`: replaced `read_bytes_sync`/`read_lines_sync` with `_read_bytes()`/`_read_lines()` helpers
- `docs_path.py`: replaced `read_lines_sync`/`write_file_sync`/`append_file_sync` with `_read_lines()`/`_write_file()`/`_append_file()` helpers
- `yaml/sync/convenience.py`: replaced inline `write_file_sync` with inline AsyncBridge call
- `io/files/__init__.py`: removed all sync_adapters imports, now only exports `FileIOCore`, path utils, and `stream_lines_sync`
- `ClassicLib/__init__.py`: removed `read_file_sync`/`write_file_sync` from package-level exports

### Task 2: Delete files, clean up, run tests
- Deleted `ClassicLib/io/files/sync_adapters.py` (144 lines)
- Deleted `ClassicLib/_async_utils/bridge_helpers.py` (252 lines)
- Inlined `run_async`, `run_async_with_timeout`, `context_aware_sync`, `smart_await` directly into `async_bridge.py`
- Removed `create_sync_wrapper` from all `__all__` lists and exports
- Updated 8 test files to match new function names and mock paths
- Removed `TestCreateSyncWrapper` test class (function no longer exists)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] bridge_helpers functions needed by production code**
- **Found during:** Task 2
- **Issue:** `run_async`, `context_aware_sync`, `smart_await`, `run_async_with_timeout` were in bridge_helpers.py and used by production code (FormIDAnalyzerCore, scanning utils)
- **Fix:** Inlined these functions directly into `async_bridge.py` instead of just deleting bridge_helpers.py
- **Files modified:** ClassicLib/core/async_bridge.py
- **Commit:** d89c843a

**2. [Rule 1 - Bug] Test mock paths needed updating**
- **Found during:** Task 2
- **Issue:** 8 test files mocked old function names (read_file_sync, read_lines_sync, etc.) that were renamed to private helpers (_read_file, _read_lines, etc.)
- **Fix:** Updated all mock paths in test files to match new private helper names
- **Files modified:** tests/game/test_wrye_check_unit.py, tests/game/test_xse_check_unit.py, tests/interface/test_results_viewer_controller_unit.py, tests/io/test_file_reading_unit.py, tests/io/test_file_writing_unit.py, tests/scanlog/executor/test_executor_unit.py, tests/integration/test_classic_scangame_integration.py, tests/async_resources/test_async_bridge_context_aware_unit.py
- **Commit:** d89c843a

## Verification

- `grep -r "create_sync_wrapper" ClassicLib/` -- 0 results
- `grep -r "bridge_helpers" ClassicLib/` -- 0 results (except comment)
- `grep -r "sync_adapters" ClassicLib/` -- 0 results
- `ls ClassicLib/_async_utils/bridge_helpers.py` -- file not found
- `ls ClassicLib/io/files/sync_adapters.py` -- file not found
- `ls ClassicLib/io/files/sync_helpers.py` -- exists
- `uv run pytest` -- 4226 passed, 25 skipped, 0 failures

## Lines Removed

- sync_adapters.py: 144 lines deleted
- bridge_helpers.py: 252 lines deleted
- Net reduction: ~396 lines removed (minus ~120 lines inlined to async_bridge.py) = ~276 net lines removed

## Next Phase Readiness

Plan 04-03 (context_aware_sync removal) can proceed. The `context_aware_sync` decorator is now defined in `async_bridge.py` and re-exported from `_async_utils/__init__.py`.
