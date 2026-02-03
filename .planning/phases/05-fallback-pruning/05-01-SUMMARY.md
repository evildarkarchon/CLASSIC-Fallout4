---
phase: 05-fallback-pruning
plan: 01
subsystem: integration
tags: [rust, fallback, factory, pruning, runtime-error]

# Dependency graph
requires:
  - phase: 04-interface-consolidation
    provides: Thin Rust wrappers with consistent factory patterns
provides:
  - 5 Python fallback files deleted (database_py, file_io_py, formid_py, record_py, report_py)
  - RuntimeError pattern for missing Rust modules in factory.py
  - CLASSIC_DISABLE_RUST mechanism fully removed
affects: [05-02, 05-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RuntimeError on missing Rust: factory raises instead of falling back"
    - "Direct try-import without env-var gating"

key-files:
  created: []
  modified:
    - ClassicLib/integration/factory.py
    - ClassicLib/integration/python/__init__.py
    - ClassicLib/support/setup.py
    - tests/fixtures/database_pool_fixtures.py
    - tests/fixtures/yamldata_fixtures.py

key-decisions:
  - "RuntimeError with reinstall message for 4 factory functions (file_io, formid, record, report)"
  - "database_py removed but no factory.py change needed (uses async_pool.py path)"
  - "CLASSIC_DISABLE_RUST removed entirely -- Rust always attempted, fallback only for parser/plugin/mod_detector"

patterns-established:
  - "Hard error pattern: raise RuntimeError(f'Required Rust module for X not available: {e}. Reinstall CLASSIC.') from e"
  - "Factory functions always try Rust import (no env-var gating)"

# Metrics
duration: 22min
completed: 2026-02-02
---

# Phase 5 Plan 1: Easy Fallback Removal Summary

**Removed 5 of 8 Python fallback files and eliminated CLASSIC_DISABLE_RUST mechanism, establishing Rust-required pattern**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-02T23:50:53Z
- **Completed:** 2026-02-03T00:12:48Z
- **Tasks:** 2
- **Files modified:** 29

## Accomplishments
- Deleted 5 Python fallback implementations (database_py, file_io_py, formid_py, record_py, report_py) -- 4173 lines removed
- Factory functions for file_io, formid, record, report now raise RuntimeError when Rust unavailable
- Completely removed _is_rust_disabled(), _DISABLE_RUST_ENV_VAR, and all env-var guards from factory.py
- Removed _log_disabled_status from SetupCoordinator
- Updated 17+ test files to remove fallback and disable-rust test patterns

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove 5 easy fallback files and their tests** - `2d301b4f` (feat)
2. **Task 2: Remove CLASSIC_DISABLE_RUST mechanism** - `3fe170cf` (feat)

## Files Created/Modified
- `ClassicLib/integration/factory.py` - Removed _is_rust_disabled, all env-var guards; 4 functions now raise RuntimeError
- `ClassicLib/integration/python/__init__.py` - Only exports parser, mod_detector, plugin
- `ClassicLib/support/setup.py` - Removed disabled status check and _log_disabled_status
- `tests/fixtures/database_pool_fixtures.py` - Import _cached_formid_lookup from FormIDAnalyzerCore
- `tests/fixtures/yamldata_fixtures.py` - Removed CLASSIC_DISABLE_RUST env var manipulation
- `tests/integration/test_factory_*.py` - 6 test files updated to remove _is_rust_disabled mocking
- `tests/setup/test_setup_coordinator_unit.py` - Removed disabled-status tests
- `tests/interface/test_yaml_settings_rust_integration.py` - Removed env var control test

## Decisions Made
- database_py has no factory.py route (uses async_pool.py), so no RuntimeError needed there
- Tests that previously set _is_rust_disabled=True now either mock ImportError directly or were deleted
- mock_yamldata_python_only fixture simplified (no longer manipulates env var)
- is_rust_accelerated() kept as compat function but no longer checks disabled flag

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock TypeError in get_record_scanner test**
- **Found during:** Task 1 (after removing _is_rust_disabled guard)
- **Issue:** TestGetRecordScanner.test_returns_scanner_instance passed MagicMock to Rust, which requires str for crashgen_name
- **Fix:** Added proper typed attributes (classic_records_list, game_ignore_records, crashgen_name) to mock
- **Files modified:** tests/integration/test_factory_analyzers_unit.py
- **Committed in:** 2d301b4f

**2. [Rule 3 - Blocking] Fixed database_pool_fixtures importing from deleted formid_py**
- **Found during:** Task 1 (database_py removal)
- **Issue:** clean_sync_database_pool fixture imported _cached_formid_lookup from deleted formid_py.py
- **Fix:** Changed import to ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore (where function also exists)
- **Files modified:** tests/fixtures/database_pool_fixtures.py
- **Committed in:** 2d301b4f

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for test suite to pass. No scope creep.

## Issues Encountered
None - plan executed as specified after the two auto-fixes above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 3 remaining fallbacks (parser_py, mod_detector_py, plugin_py) ready for 05-02 and 05-03
- Factory pattern established: RuntimeError for required Rust, try-import fallback for optional
- All 4095 tests pass

---
*Phase: 05-fallback-pruning*
*Completed: 2026-02-02*
