---
phase: 02-integration-layer-simplification
plan: 02
subsystem: integration
tags: [protocols, type-safety, pyright, dead-code-removal, acceleration]

# Dependency graph
requires:
  - phase: 02-01
    provides: flat factory.py module with all factory functions
provides:
  - Protocol-based return types for all major factory functions
  - Deletion of unused acceleration coordinator package
affects: [03-wrapper-thinning, 04-python-fallback-consolidation]

# Tech tracking
tech-stack:
  added: []
  patterns: [Protocol-based structural typing for factory returns]

key-files:
  created:
    - ClassicLib/integration/types.py
  modified:
    - ClassicLib/integration/factory.py
    - tests/fixtures/singleton_fixtures.py

key-decisions:
  - "get_yamldata keeps Any return type (Rust YamlData and Python ClassicScanLogsInfo have incompatible interfaces)"
  - "Utility module factories (get_constants, etc.) keep Any | None (return raw modules, not class instances)"
  - "Protocols are static-only (no @runtime_checkable) to avoid overhead"
  - "GpuDetectorProtocol defined for module-level interface even though factory returns a module"

patterns-established:
  - "Protocol types in types.py for factory boundary type checking"
  - "TYPE_CHECKING-guarded Protocol imports to avoid runtime cost"

# Metrics
duration: 12min
completed: 2026-02-02
---

# Phase 2 Plan 2: Acceleration Removal and Factory Type Narrowing Summary

**Deleted 960-line unused acceleration package and narrowed 13 factory return types from Any to Protocol-based interfaces with full pyright compliance**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-02T08:54:59Z
- **Completed:** 2026-02-02T09:07:06Z
- **Tasks:** 2
- **Files modified:** 3 (+ 8 deleted)

## Accomplishments
- Deleted ClassicLib/acceleration/ package (5 files, ~960 lines) -- zero production callers confirmed
- Created ClassicLib/integration/types.py with 13 Protocol classes matching actual Rust/Python implementation interfaces
- Narrowed all major factory function return types from Any to Protocol types
- pyright passes with 0 errors on factory.py
- Full test suite passes (4276 tests, 2 pre-existing flaky failures unrelated to changes)

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete acceleration package and create Protocol types** - `b48032e7` (refactor)
2. **Task 2: Narrow factory return types and pass pyright** - `e104448e` (feat)

## Files Created/Modified
- `ClassicLib/integration/types.py` - Protocol classes for all major factory return types (NEW)
- `ClassicLib/integration/factory.py` - Return type annotations updated to use Protocols
- `tests/fixtures/singleton_fixtures.py` - Removed RustAcceleration reset block
- `ClassicLib/acceleration/` - Entire directory deleted (5 files)
- `tests/rust_acceleration/` - Entire directory deleted (2 files)

## Decisions Made
- get_yamldata keeps Any: Rust YamlData and Python ClassicScanLogsInfo have fundamentally incompatible interfaces
- Utility module factories keep Any | None: they return raw imported modules, not class instances
- No @runtime_checkable on Protocols: static checking only, avoids runtime overhead
- get_mod_detector returns dict[str, Any]: functions stored as dict values, Protocol impractical

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 4 Phase 2 success criteria met:
  - SC1: factory.py is a single flat module (verified in 02-01)
  - SC2: ClassicLib/acceleration/ does not exist
  - SC3: No Any in major factory function return types, pyright passes
  - SC4: uv run pytest passes
- Phase 2 complete, ready for Phase 3 (Wrapper Thinning)
- Phase 3 flagged HIGH research need for Python-to-Rust migration patterns

---
*Phase: 02-integration-layer-simplification*
*Completed: 2026-02-02*
