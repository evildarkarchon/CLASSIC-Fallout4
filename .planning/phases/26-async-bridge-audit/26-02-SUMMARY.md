---
phase: 26-async-bridge-audit
plan: 02
subsystem: infra
tags: [async, tokio, slint, bridge, timeout, cancellation, error-handling, testability]

# Dependency graph
requires:
  - phase: 26-01
    provides: Clean async_bridge.rs with LazyLock, no dead code
provides:
  - BridgeError enum for structured error handling
  - EventLoopDispatcher trait for mockable UI dispatch
  - run_with_timeout method for deadline-bounded operations
  - run_cancellable method for cooperative cancellation
  - set_dispatcher() for test injection of mock dispatchers
affects: [26-03]

# Tech tracking
tech-stack:
  added: [tokio-util (optional, behind gui-bridge feature)]
  patterns: [trait-based dispatch abstraction, log-and-drop error handling, OnceLock dispatcher injection]

key-files:
  modified:
    - rust/foundation/classic-shared-core/src/async_bridge.rs
    - rust/foundation/classic-shared-core/src/lib.rs
    - rust/foundation/classic-shared-core/Cargo.toml

key-decisions:
  - "OnceLock for dispatcher: get_or_init defaults to SlintDispatcher, no explicit initialization required in production"
  - "Log-and-drop over Result propagation: fire-and-forget methods cannot return errors, so dispatch failures are logged"
  - "Option<R> for run_cancellable: simpler than Result<R, BridgeError> since cancellation is an expected outcome, not an error"

patterns-established:
  - "EventLoopDispatcher trait: all dispatch goes through trait object, enabling unit tests without Slint event loop"
  - "set_dispatcher() injection: test code calls set_dispatcher(MockDispatcher) before exercising bridge methods"
  - "BridgeError enum: structured error type for timeout/cancellation/dispatch failures"

# Metrics
duration: 5min
completed: 2026-02-06
---

# Phase 26 Plan 02: Resilience APIs and Dispatcher Trait Summary

**BridgeError enum, EventLoopDispatcher trait for testability, run_with_timeout and run_cancellable methods with tokio-util**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-06T07:25:47Z
- **Completed:** 2026-02-06T07:30:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added BridgeError enum with Timeout, Cancelled, and DispatchFailed variants for structured error handling
- Extracted EventLoopDispatcher trait abstracting slint::invoke_from_event_loop behind a mockable interface
- Added run_with_timeout wrapping tokio::time::timeout with BridgeError::Timeout on deadline expiry
- Added run_cancellable accepting CancellationToken, returning Option<R> (None = cancelled)
- Replaced all .expect() calls on dispatch with log-and-drop error handling
- Updated lib.rs re-exports to expose BridgeError, EventLoopDispatcher, SlintDispatcher, set_dispatcher

## Task Commits

Each task was committed atomically:

1. **Task 1: Add BridgeError, EventLoopDispatcher trait, and dispatcher infrastructure** - `f7364d16` (feat)
2. **Task 2: Add run_with_timeout and run_cancellable methods** - `d2b518eb` (feat)

## Files Created/Modified
- `rust/foundation/classic-shared-core/src/async_bridge.rs` - Full bridge API with BridgeError, EventLoopDispatcher, run_with_timeout, run_cancellable
- `rust/foundation/classic-shared-core/src/lib.rs` - Updated re-exports for new public types
- `rust/foundation/classic-shared-core/Cargo.toml` - Added tokio-util as optional dependency behind gui-bridge feature

## Decisions Made
- **OnceLock for dispatcher**: `get_or_init` defaults to `SlintDispatcher` so production code requires no explicit initialization
- **Log-and-drop error handling**: Fire-and-forget methods (run_with_ui_update, invoke_on_ui_thread) log dispatch failures instead of panicking, keeping the application stable
- **Option<R> for run_cancellable**: Cancellation is an expected outcome, not an error -- `None` is cleaner than `Err(BridgeError::Cancelled)` for callers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Pre-existing icu_properties dependency error**: Running `cargo check -p classic-shared-core --features gui-bridge` directly triggers a transitive dependency conflict in `icu_properties` (zerovec missing `alloc` feature). This is NOT caused by plan changes -- `cargo check -p classic-gui` (which enables the same feature) compiles cleanly. The issue is isolated to direct feature-flag checking of the crate and does not affect the actual build.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- AsyncBridge now has 5 public methods covering all coordination patterns
- EventLoopDispatcher trait enables mock-based testing in 26-03
- BridgeError provides structured error reporting for all bridge operations
- All dispatch operations use log-and-drop instead of panicking
- classic-gui compiles cleanly with the new API (backward compatible)

## Self-Check: PASSED

---
*Phase: 26-async-bridge-audit*
*Completed: 2026-02-06*
