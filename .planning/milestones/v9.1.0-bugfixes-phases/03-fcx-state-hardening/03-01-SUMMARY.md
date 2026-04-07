---
phase: 03-fcx-state-hardening
plan: 01
subsystem: api
tags: [fcx, rust, mutex, bindings, docs]
requires: []
provides:
  - blocking FCX singleton reset semantics in classic-scanlog-core
  - typed reset outcome contract via FcxResetError
  - contention coverage proving reset waits and eventually clears stale state
affects: [03-02, 03-03, classic-scanlog-core, bindings]
tech-stack:
  added: []
  patterns: [blocking singleton reset, typed non-fatal no-op outcome]
key-files:
  created: []
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
    - docs/api/classic-scanlog-core.md
key-decisions:
  - "Use GLOBAL_FCX_HANDLER.lock() so FCX reset waits instead of silently skipping under contention."
  - "Model an already-clean singleton as Err(FcxResetError::Unnecessary) so bindings can treat no-op resets as benign."
patterns-established:
  - "FCX reset callers should branch on Result<(), FcxResetError> rather than infer reset outcomes from side effects."
  - "Binding scan entrypoints should auto-reset FCX state at scan start while allowing explicit reset APIs to remain public."
requirements-completed: [SAFE-01, CONS-02, TEST-01]
duration: 0 min
completed: 2026-04-06
---

# Phase 03 Plan 01: FCX Reset Contract Summary

**Blocking FCX singleton reset with a typed unnecessary outcome and contention-tested stale-state cleanup for downstream bindings.**

## Performance

- **Duration:** 0 min
- **Started:** 2026-04-06T02:19:27Z
- **Completed:** 2026-04-06T02:19:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added TDD coverage for dirty-state reset, already-clean no-op detection, and mutex contention behavior in `fcx_handler.rs`.
- Changed `FcxModeHandler::reset_global_state()` to return `Result<(), FcxResetError>` and block on the global mutex.
- Re-exported `FcxResetError` and documented the contributor-facing reset contract for binding implementers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the FCX reset contract and contention tests** - `d6b5b2fd` (test), `b58bb16b` (feat)
2. **Task 2: Re-export and document the new reset contract** - `dda98055` (docs)

_Note: Task 1 followed TDD and therefore produced separate RED and GREEN commits._

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` - Added `FcxResetError`, blocking reset behavior, and targeted contention tests.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs` - Re-exported `FcxResetError` at the crate root.
- `docs/api/classic-scanlog-core.md` - Documented blocking reset semantics and the benign `Unnecessary` outcome.

## Decisions Made
- Used a blocking `GLOBAL_FCX_HANDLER.lock()` in the core reset path so FCX cleanup cannot disappear during contention.
- Kept the no-op reset path typed as `Err(FcxResetError::Unnecessary)` so bindings can distinguish it from a real reset without treating it as fatal.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Core FCX reset semantics are now stable for the C++ and Node binding plans.
- Phase 03 plans 02 and 03 can consume `FcxResetError` directly from the crate root and preserve the benign `Unnecessary` path.

---
*Phase: 03-fcx-state-hardening*
*Completed: 2026-04-06*

## Self-Check: PASSED
