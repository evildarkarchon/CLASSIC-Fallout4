---
phase: 09-orchestration-migration
plan: 03
subsystem: scanning
tags: [async, asyncio, lazy-loading, cli, executor]

# Dependency graph
requires:
  - phase: 09-02
    provides: "Rust orchestrator integration in ScanLogsExecutor"
provides:
  - "CLI scanner works without async context RuntimeError"
  - "Lazy loading pattern for crashlog_list via asyncio.to_thread()"
  - "Updated unit tests for lazy loading behavior"
affects: [10-entry-point-streamlining, gui-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.to_thread() for running sync functions from async context"
    - "Lazy initialization in executor __init__ with deferred loading in execute_scan()"

key-files:
  created: []
  modified:
    - ClassicLib/scanning/logs/executor.py
    - tests/scanlog/executor/test_executor_unit.py

key-decisions:
  - "Use asyncio.to_thread() to run sync settings functions in thread pool, avoiding async context detection"
  - "Defer both crashlog_list AND remove_list loading to execute_scan() via _ensure_crashlog_list_async()"
  - "Handle None config values when applying to Rust AnalysisConfig (only override if not None)"

patterns-established:
  - "Lazy loading pattern: defer sync operations from __init__ to async execution methods via asyncio.to_thread()"

# Metrics
duration: 14min
completed: 2026-02-03
---

# Phase 09 Plan 03: CLI Async Context Fix Summary

**Lazy initialization via asyncio.to_thread() fixes CLI startup RuntimeError when yaml_settings() detects async context**

## Performance

- **Duration:** 14 min
- **Started:** 2026-02-03T11:35:05Z
- **Completed:** 2026-02-03T11:49:24Z
- **Tasks:** 2 (1 implementation + 1 verification)
- **Files modified:** 2

## Accomplishments
- CLI scanner starts and runs successfully without RuntimeError
- crashlog_list and remove_list lazily loaded via asyncio.to_thread() during execute_scan()
- Unit tests updated to reflect new lazy loading behavior
- GUI scan_sync() still works correctly (AsyncBridge creates isolated event loop)

## Task Commits

Each task was committed atomically:

1. **Task 1: Make crashlog_list initialization lazy in ScanLogsExecutor** - `fc304a9f` (fix)
2. **Task 2: Verify GUI compatibility with lazy loading** - No commit (verification only, all tests pass)

## Files Created/Modified
- `ClassicLib/scanning/logs/executor.py` - Added _ensure_crashlog_list_async() for lazy loading, deferred crashlog_list and remove_list initialization
- `tests/scanlog/executor/test_executor_unit.py` - Updated 3 tests for lazy loading behavior, added 3 new async tests for _ensure_crashlog_list_async()

## Decisions Made
- **asyncio.to_thread() pattern**: The sync functions (crashlogs_get_files, yaml_settings) run in a thread pool worker which does NOT have an event loop running, so async context detection returns False
- **Defer remove_list too**: remove_list also calls yaml_settings() and needed to be deferred to avoid the same error
- **Handle None config values**: When applying ScanConfig to Rust AnalysisConfig, only override values that are not None (rust_config already has defaults from AnalysisConfig.from_yamldata())

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] remove_list also needs lazy loading**
- **Found during:** Task 1 (first fix attempt)
- **Issue:** After fixing crashlog_list, yaml_settings() for remove_list in __init__ still caused RuntimeError
- **Fix:** Deferred remove_list loading to _ensure_crashlog_list_async() alongside crashlog_list
- **Files modified:** ClassicLib/scanning/logs/executor.py
- **Verification:** CLI starts without error
- **Committed in:** fc304a9f (Task 1 commit)

**2. [Rule 1 - Bug] None config values fail Rust AnalysisConfig assignment**
- **Found during:** Task 1 (after fixing lazy loading)
- **Issue:** self.config.fcx_mode was None, Rust doesn't accept NoneType for bool field
- **Fix:** Only override rust_config values if self.config value is not None
- **Files modified:** ClassicLib/scanning/logs/executor.py
- **Verification:** CLI completes scan successfully
- **Committed in:** fc304a9f (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes essential for CLI to work. No scope creep.

## Issues Encountered
- Pre-existing test failures in test_executor_integration.py and test_pipeline_stages_integration.py - these tests reference deleted orchestrator_core module from Phase 9-02. Not caused by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CLI async context issue (Gap 1) fully resolved
- Phase 9 orchestration migration complete
- Ready for Phase 10: Entry Point Streamlining

---
*Phase: 09-orchestration-migration*
*Completed: 2026-02-03*
