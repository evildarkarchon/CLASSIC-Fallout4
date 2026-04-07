---
phase: 03-fcx-state-hardening
plan: 02
subsystem: api
tags: [fcx, cxx, rust, bindings, docs]
requires:
  - phase: 03-01
    provides: blocking FCX reset contract and FcxResetError semantics
provides:
  - explicit classic::scanner::fcx_reset_global_state bridge entrypoint
  - automatic FCX reset at the start of every public C++ scan session
  - contributor docs for C++ reset-only FCX behavior and failure mapping
affects: [03-03, classic-cpp-bridge, classic-gui, bindings]
tech-stack:
  added: []
  patterns: [binding-level reset helper, pre-scan FCX guard, reset-only C++ FCX surface]
key-files:
  created: []
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
    - docs/api/classic-cpp-bridge-data-entrypoints.md
key-decisions:
  - "Keep the C++ FCX surface reset-only in Phase 3 and expose a standalone classic::scanner::fcx_reset_global_state() helper."
  - "Preserve existing C++ batch signatures by short-circuiting with failed batch DTOs on reset failure instead of widening the public API to Result<Vec<_>> mid-phase."
patterns-established:
  - "C++ scan entrypoints should normalize FcxResetError::Unnecessary to success through a shared bridge helper before invoking scan work."
  - "Reset-only FCX bindings should document explicit reset access separately from automatic scan-session reset behavior."
requirements-completed: [SAFE-02]
duration: 6 min
completed: 2026-04-06
---

# Phase 03 Plan 02: C++ FCX Reset Surface Summary

**C++ bridge FCX reset helper plus automatic pre-scan state cleanup on every public scan session entrypoint.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T02:22:00Z
- **Completed:** 2026-04-06T02:28:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `classic::scanner::fcx_reset_global_state()` to the CXX bridge and normalized benign no-op resets to success.
- Wired FCX cleanup into C++ single-log and batch scan entrypoints so each scan session starts from clean state.
- Documented the explicit reset API, auto-reset behavior, and the reset-only FCX scope for C++ callers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the explicit C++ FCX reset bridge and pre-scan guard** - `29ffaacc` (feat)
2. **Task 2: Document the reset-only C++ FCX surface** - `958ba581` (docs)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - Added the reset helper export, pre-scan reset guards, and scanner coverage for FCX cleanup.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` - Documented the explicit reset entrypoint, auto-reset semantics, and reset-only C++ FCX boundary.

## Decisions Made
- Kept C++ FCX exposure reset-only in this phase, matching D-09 and avoiding any new issue DTO/getter surface.
- Preserved the existing batch C++ signatures and represented a future real reset failure as an immediate failed batch result instead of a breaking API change.

## Deviations from Plan

### Execution adjustments

**1. Preserved existing batch return types while enforcing pre-scan reset gating**
- **Found during:** Task 1 (Add the explicit C++ FCX reset bridge and pre-scan guard)
- **Issue:** The existing C++ batch entrypoints return `Vec<...>` rather than `Result<Vec<...>>`, so surfacing a true reset failure as a bridge error would have required a broader public API change and downstream C++ consumer updates.
- **Fix:** Kept the public signatures stable and short-circuited batch entrypoints with a single failed result DTO carrying the reset error text before any scan work begins.
- **Files modified:** ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs, docs/api/classic-cpp-bridge-data-entrypoints.md
- **Verification:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner`; `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml`
- **Committed in:** 29ffaacc, 958ba581

---

**Total deviations:** 1 execution adjustment
**Impact on plan:** The explicit reset API and automatic C++ scan-session reset shipped as planned without widening the current C++ batch API mid-phase.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Known Stubs
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs:5` - Pre-existing `Placeholder` module comment remains in the file but does not affect the implemented C++ FCX reset behavior.

## Next Phase Readiness
- Phase 03-03 can mirror the same reset-helper pattern on the Node binding surface.
- The C++ bridge contract and docs are aligned for the FCX reset-only path.

## Self-Check: PASSED
