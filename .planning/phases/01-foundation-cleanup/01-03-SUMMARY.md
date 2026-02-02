---
phase: 01-foundation-cleanup
plan: 03
subsystem: global-state
tags: [singleton, test-isolation, lru-cache, fixtures, pytest]
dependency-graph:
  requires: []
  provides: [singleton-reset-fixture, mutable-flag-removal]
  affects: [all-future-test-plans]
tech-stack:
  added: []
  patterns: [lru_cache-for-oneshot-flags, autouse-fixture-for-isolation]
key-files:
  created:
    - tests/fixtures/singleton_fixtures.py
  modified:
    - ClassicLib/support/game_path.py
    - tests/conftest.py
    - tests/game/test_game_path_generation_unit.py
decisions:
  - id: GLOB-01
    choice: "lru_cache(maxsize=1) replaces _VERSION_WARNING_LOGGED mutable flag"
    reason: "Testable via cache_clear(), no global statement needed"
  - id: GLOB-03
    choice: "Autouse fixture resets all 19+ globals after every test"
    reason: "Prevents state leakage between tests; exposed pre-existing bug in settings e2e test"
metrics:
  duration: 21m
  completed: 2026-02-02
---

# Phase 01 Plan 03: Global State Cleanup Summary

**One-liner:** Replaced mutable _VERSION_WARNING_LOGGED flag with lru_cache, created comprehensive autouse reset_all_singletons fixture covering 19+ globals across 4 categories.

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~21 minutes |
| Start | 2026-02-02T03:06:48Z |
| End | 2026-02-02T03:28:06Z |
| Tasks | 2/2 |
| Files created | 1 |
| Files modified | 3 |

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 798545c4 | Replace _VERSION_WARNING_LOGGED with lru_cache pattern |
| 2 | 161951bb | Create reset_all_singletons autouse fixture |

## What Was Done

### Task 1: Replace mutable global flags and audit reset methods

- Replaced `_VERSION_WARNING_LOGGED = False` / `global _VERSION_WARNING_LOGGED` pattern with `@functools.lru_cache(maxsize=1)` decorator on `_log_version_warning()`
- Added `import functools` to game_path.py
- Updated test to use `cache_clear()` instead of direct flag manipulation
- Audited all 18+ remaining `global` statements in ClassicLib/ -- all are lazy-init singleton patterns (not mutable flags)
- Confirmed no mutable True/False global flag patterns remain

### Task 2: Create reset_all_singletons() autouse fixture

Created `tests/fixtures/singleton_fixtures.py` with four reset categories:

1. **Class singletons with reset_instance()** (4): RustAcceleration, VersionRegistry, YamlSettingsCache, DatabasePoolManager
2. **Module-level singletons** (9): MessageHandler, GameIntegrityOrchestratorCore, GameFilesManagerCore, AsyncYamlSettingsCore, FileIO, components_cache, ThreadManager, EMOJI_PATTERN, ALL_ADDRESS_LIB_INFO_CACHE, GlobalRegistry
3. **Lazy-import caches** (6): _PyReportFragment (4 modules), _PyReportGenerator, _PyReportComposer, VERSION_TOOLTIP, GAME_VERSION_OPTIONS
4. **lru_cache functions** (1): _log_version_warning

Added autouse fixture in conftest.py that yields control to the test then resets all state on teardown.

## Verification Results

- `grep _VERSION_WARNING_LOGGED ClassicLib/`: 0 results (flag removed)
- `grep lru_cache ClassicLib/support/game_path.py`: confirmed replacement
- `tests/fixtures/singleton_fixtures.py` exists with `reset_all_singletons_impl()`
- `tests/conftest.py` has autouse `reset_all_singletons` fixture
- 3231 unit tests pass with fixture active
- 2423+ broader tests pass (excluding pre-existing failures)

## Deviations from Plan

### Pre-existing Issues Discovered

**1. Test state leakage exposed in settings e2e test**

- **Found during:** Task 2 verification (broader test run)
- **Issue:** `tests/gui/settings/test_settings_persistence_e2e.py::test_settings_persistence_across_instances` fails because it relies on MessageHandler being initialized by a previous test -- classic state leakage
- **Confirmed pre-existing:** Test also fails on pre-change codebase when run in isolation
- **Action:** Not fixed (out of scope), documented for future cleanup

**2. Task 1 commit included pre-staged files**

- **Issue:** 3 files from previous work were already in git staging area when Task 1 was committed
- **Impact:** Commit 798545c4 includes changes to `ClassicLib/core/constants.py`, `ClassicLib/integration/rust/database_rust.py` (deleted), and `tests/rust_integration/api/test_rust_database_pool_integration.py` that were not part of this plan
- **Root cause:** Files were staged by prior plan execution and not committed

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| GLOB-01 | lru_cache replaces mutable flag | Testable via cache_clear(), eliminates global statement |
| GLOB-02 | All 18 remaining globals are lazy-init (no action needed) | Audit confirmed no other mutable flags exist |
| GLOB-03 | Autouse fixture resets all categories | Comprehensive isolation prevents state leakage |

## Next Phase Readiness

- All global state is now reset-able and test-isolated
- The autouse fixture will benefit all future test plans in any phase
- Pre-existing settings e2e test should be fixed in a future plan (not blocking)
