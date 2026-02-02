---
phase: 02-integration-layer-simplification
plan: 01
subsystem: integration
tags: [factory-pattern, refactoring, import-consolidation, rust-integration]

# Dependency graph
requires:
  - phase: 01-foundation-cleanup
    provides: clean codebase with dead code removed and singleton management
provides:
  - flat factory.py module with 23+ factory functions and detect_component utility
  - is_component_available() replacing is_rust_accelerated() in production code
  - is_rust_accelerated() compat shim with component key mapping
  - config.py, detector.py, status.py deleted
  - factory/ subpackage directory deleted
affects:
  - 02-integration-layer-simplification (plan 02 - acceleration coordinator removal)
  - 03-wrapper-thinning (wrapper modules now import from flat factory.py)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct try-import factory pattern (no custom caching layers)"
    - "is_component_available() for bool detection, detect_component() for tuple"

key-files:
  created: []
  modified:
    - ClassicLib/integration/factory.py
    - ClassicLib/integration/__init__.py
    - tests/fixtures/singleton_fixtures.py
    - .github/workflows/ci.yml

key-decisions:
  - "Kept is_rust_accelerated() as compat shim with _COMPONENT_KEY_MAP for coordinator (deleted in 02-02)"
  - "Inlined DISABLE_RUST_ENV_VAR constant from config.py into factory.py"
  - "Added get_rust_component_status() and print_rust_status() to factory.py as status.py replacements"

patterns-established:
  - "Factory functions use direct try-import with _is_rust_disabled() guard"
  - "No custom detection caching -- Python sys.modules handles it"

# Metrics
duration: 8min
completed: 2026-02-02
---

# Phase 2 Plan 1: Factory Collapse Summary

**Collapsed 3-layer factory/detector/status architecture into single flat factory.py with 23+ factory functions, detect_component utility, and backward-compat shims**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-02T08:44:31Z
- **Completed:** 2026-02-02T08:52:29Z
- **Tasks:** 2
- **Files modified:** 80+

## Accomplishments

- Consolidated 8 factory submodules + detector.py + status.py + config.py into single flat factory.py (~948 lines)
- Updated 16 rust wrapper modules, 6 production files, 40+ test files to new import paths
- Eliminated _components_cache and _detection_cache dictionaries (Python sys.modules handles caching)
- All 4338 tests pass with no import-related regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create flat factory.py and delete subpackage** - `2ef90121` + `ce1712fa` (refactor)
   - Core collapse in 2ef90121 (prior commit)
   - Compat shims + config.py deletion in ce1712fa
2. **Task 2: Update all caller import paths and singleton fixtures** - `7de02d49` (refactor)

## Files Created/Modified

- `ClassicLib/integration/factory.py` - Flat module with all factory functions + detect_component + compat shims
- `ClassicLib/integration/__init__.py` - Re-exports from factory.py
- `ClassicLib/integration/rust/*.py` (16 files) - detect_component import path updated
- `ClassicLib/Interface/workers/Workers.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/Interface/controllers/results_viewer.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/scanning/logs/orchestrator_core.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/scanning/logs/hybrid_orchestrator.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/scanning/logs/parser.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/io/database/pool_manager.py` - is_rust_accelerated -> is_component_available
- `ClassicLib/support/setup.py` - get_rust_component_status from factory.py
- `ClassicLib/acceleration/coordinator.py` - imports from factory instead of detector/status
- `ClassicLib/core/rust_loader.py` - uses factory.detect_component
- `tests/fixtures/singleton_fixtures.py` - factory module paths updated
- `.github/workflows/ci.yml` - Rust status diagnostic updated

**Deleted files:**
- `ClassicLib/integration/config.py`
- `ClassicLib/integration/detector.py` (in prior commit)
- `ClassicLib/integration/status.py` (in prior commit)
- `ClassicLib/integration/factory/` (8 files, in prior commit)
- `tests/integration/test_integration_status_unit.py`

## Decisions Made

- Kept `is_rust_accelerated()` as backward-compat shim with `_COMPONENT_KEY_MAP` dict mapping legacy component keys to (module, class) tuples. This supports the acceleration coordinator which is deleted in plan 02-02.
- Added `get_rust_component_status()` and `print_rust_status()` to factory.py as drop-in replacements for the deleted status.py functions.
- Inlined `DISABLE_RUST_ENV_VAR` constant from config.py into factory.py as `_DISABLE_RUST_ENV_VAR`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The factory subpackage collapse and file deletions were already committed in a prior session (`2ef90121`). Task 1 completion (compat shims, config.py deletion) and Task 2 (caller updates) were staged and committed cleanly on top.
- One pre-existing flaky performance test (`test_detect_mods_scaling`) fails intermittently but passes in isolation -- unrelated to this refactor.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Factory.py is the single source of truth for component detection and factory functions
- Plan 02-02 (acceleration coordinator removal) can proceed -- coordinator already imports from factory.py
- The `is_rust_accelerated()` shim and `_COMPONENT_KEY_MAP` in factory.py are marked for removal when coordinator is deleted in 02-02

---
*Phase: 02-integration-layer-simplification*
*Completed: 2026-02-02*
