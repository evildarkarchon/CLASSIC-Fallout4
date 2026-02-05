---
phase: 15-bug-fixes
plan: 01
subsystem: testing
tags: [rust, serial_test, parallel-tests, cache, yaml]

# Dependency graph
requires:
  - phase: 14
    provides: cache instrumentation foundation
provides:
  - Reliable Rust cache tests under parallel execution
  - #[serial] pattern for cache-touching tests
  - BUG-01 regression tests
affects: [future-rust-tests, ci-pipeline]

# Tech tracking
tech-stack:
  added: [serial_test]
  patterns: [serial-test-isolation, clear-cache-at-boundary]

key-files:
  modified:
    - rust/business-logic/classic-yaml-core/Cargo.toml
    - rust/business-logic/classic-yaml-core/src/lib.rs
    - tests/regression/test_bug_fixes.py
    - tests/regression/__init__.py

key-decisions:
  - "Used serial_test crate for test serialization (standard Rust solution)"
  - "Added clear_global_yaml_cache() at start of serial tests to prevent pollution between sequential runs"
  - "Added #[serial] to 3 cache-touching tests: test_clear_cache, test_clear_global_yaml_cache_function, test_cache_stats_empty"

patterns-established:
  - "Serial test pattern: clear cache at start, use #[serial] attribute"
  - "Regression test organization: tests/regression/ with BUG-XX class naming"

# Metrics
duration: 6min
completed: 2026-02-05
---

# Phase 15 Plan 01: Fix BUG-01 Cache Test Pollution Summary

**Added #[serial] attribute to cache-touching tests in classic-yaml-core with serial_test crate, preventing intermittent parallel test failures**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-05T03:04:20Z
- **Completed:** 2026-02-05T03:10:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added serial_test = "3.2" dev-dependency for test serialization
- Added #[serial] attribute to 3 cache-touching tests
- Added clear_global_yaml_cache() at test start to prevent pollution
- Created regression test directory with BUG-01 tests
- Tests now pass reliably under parallel execution (--test-threads=4)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add serial_test dependency and fix Rust cache tests** - `5047f9a5` (fix)
2. **Task 2: Create regression test directory and BUG-01 regression test** - `b5af502e` (test, added as part of 15-02 execution)

**Plan metadata:** (this summary)

_Note: Task 2's regression tests were added in commit b5af502e during 15-02 execution since both plans share the same regression test file._

## Files Created/Modified

- `rust/business-logic/classic-yaml-core/Cargo.toml` - Added serial_test dev-dependency
- `rust/business-logic/classic-yaml-core/src/lib.rs` - Added #[serial] and clear_global_yaml_cache() to cache tests
- `tests/regression/__init__.py` - Created regression test package
- `tests/regression/test_bug_fixes.py` - Created BUG-01 regression tests

## Decisions Made

1. **Used serial_test crate** - Standard Rust solution for serializing tests that share global state
2. **Clear at start pattern** - Clear cache at test start rather than end to prevent pollution from previous serial tests
3. **Three tests serialized** - test_clear_cache, test_clear_global_yaml_cache_function, test_cache_stats_empty all touch global YAML_CACHE

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Also added #[serial] to test_cache_stats_empty**

- **Found during:** Task 1 (analyzing cache-touching tests)
- **Issue:** Plan specified 2 tests, but test_cache_stats_empty also clears cache and expects it to be empty
- **Fix:** Added #[serial] attribute to this test as well
- **Files modified:** rust/business-logic/classic-yaml-core/src/lib.rs
- **Verification:** All 65 unit tests pass under parallel execution
- **Committed in:** 5047f9a5 (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (missing critical functionality)
**Impact on plan:** Essential for complete fix. No scope creep.

## Issues Encountered

- Pre-existing failing test in classic-scanlog-core (`test_detect_mods_important_not_installed`) - unrelated to this plan, not addressed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BUG-01 is fully fixed with regression tests
- Ready for 15-02-PLAN.md (BUG-02 path resolution fix)
- Note: 15-02 work was already committed (3b42da8a, b5af502e) but needs SUMMARY

---
*Phase: 15-bug-fixes*
*Completed: 2026-02-05*
