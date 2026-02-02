---
phase: 04-interface-consolidation
plan: 01
subsystem: scanning
tags: [formid, sync-wrapper, dead-code, async-first]

# Dependency graph
requires:
  - phase: 03-wrapper-thinning
    provides: Thin delegation pattern for Rust wrappers
provides:
  - FormIDAnalyzer sync wrapper removed (155 lines)
  - All callers updated to use FormIDAnalyzerCore directly
  - formid_rust.py fallback updated to FormIDAnalyzerCore
affects: [04-02, 04-03, 05-fallback-pruning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct async-first usage: callers use FormIDAnalyzerCore instead of sync wrapper"

key-files:
  created: []
  modified:
    - ClassicLib/scanning/logs/orchestrator_core.py
    - ClassicLib/integration/rust/formid_rust.py
    - ClassicLib/scanning/logs/__init__.py
    - ClassicLib/scanning/logs/analyzers/__init__.py
    - tests/async_tests/test_async_orchestrator_unit.py
    - tests/scanlog/orchestrator/test_orchestrator_unit.py

key-decisions:
  - "formid_rust.py uses formid_match_sync() since FormIDAnalyzerCore.formid_match is async"

patterns-established:
  - "Sync wrapper removal: update callers to Core class, use _sync methods where needed"

# Metrics
duration: 8min
completed: 2026-02-02
---

# Phase 4 Plan 1: Remove FormIDAnalyzer Sync Wrapper Summary

**Deleted FormIDAnalyzer.py sync wrapper (155 lines), updated all callers to FormIDAnalyzerCore directly, fixed formid_rust.py to use formid_match_sync**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-02T11:11:51Z
- **Completed:** 2026-02-02T11:19:38Z
- **Tasks:** 2
- **Files modified:** 7 (4 production, 1 deleted, 2 tests)

## Accomplishments
- Removed 155-line FormIDAnalyzer.py sync wrapper that wrapped FormIDAnalyzerCore with create_sync_wrapper calls
- Updated orchestrator_core.py to remove dead `self.formid_analyzer` assignment (was never used at runtime)
- Updated formid_rust.py fallback from sync wrapper to FormIDAnalyzerCore directly
- All 4217 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove FormIDAnalyzer references from all callers** - `9a9de57e` (refactor)
2. **Task 2: Delete FormIDAnalyzer.py and run tests** - `ad6cab4f` (feat)

## Files Created/Modified
- `ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py` - DELETED (155-line sync wrapper)
- `ClassicLib/scanning/logs/orchestrator_core.py` - Removed dead FormIDAnalyzer import and assignment
- `ClassicLib/integration/rust/formid_rust.py` - Changed fallback to FormIDAnalyzerCore, use formid_match_sync
- `ClassicLib/scanning/logs/__init__.py` - Removed FormIDAnalyzer re-export
- `ClassicLib/scanning/logs/analyzers/__init__.py` - Removed FormIDAnalyzer re-export
- `tests/async_tests/test_async_orchestrator_unit.py` - Updated to check _async_formid_analyzer
- `tests/scanlog/orchestrator/test_orchestrator_unit.py` - Removed dead formid_analyzer assertion

## Decisions Made
- formid_rust.py `_init_python_analyzer` now imports FormIDAnalyzerCore directly instead of the deleted sync wrapper
- Changed formid_rust.py `formid_match` to call `formid_match_sync()` because FormIDAnalyzerCore.formid_match is async (the sync wrapper had hidden this behind create_sync_wrapper)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed formid_rust.py formid_match calling async method synchronously**
- **Found during:** Task 1 (updating formid_rust.py)
- **Issue:** FormIDAnalyzerCore.formid_match is async, but formid_rust.py calls it synchronously. The old sync wrapper hid this via create_sync_wrapper. Switching to FormIDAnalyzerCore directly would break the call.
- **Fix:** Changed to call formid_match_sync() which is FormIDAnalyzerCore's built-in sync wrapper method
- **Files modified:** ClassicLib/integration/rust/formid_rust.py
- **Verification:** Import test passes, all 4217 tests pass
- **Committed in:** 9a9de57e (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test assertions referencing removed attribute**
- **Found during:** Task 2 (running tests)
- **Issue:** Two test files asserted `orchestrator.formid_analyzer is not None` which no longer exists
- **Fix:** Updated one to check `_async_formid_analyzer`, removed the other (was testing __init__ where async analyzer isn't set)
- **Files modified:** tests/async_tests/test_async_orchestrator_unit.py, tests/scanlog/orchestrator/test_orchestrator_unit.py
- **Verification:** All 4217 tests pass
- **Committed in:** ad6cab4f (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- First sync wrapper removed, pattern established for 04-02 and 04-03
- formid_rust.py Rust wrapper still has its own FormIDAnalyzer class (different from deleted sync wrapper) -- this is expected and correct
- integration/rust/__init__.py and factory.py still reference formid_rust.FormIDAnalyzer -- this is the Rust wrapper, not the sync wrapper

---
*Phase: 04-interface-consolidation*
*Completed: 2026-02-02*
