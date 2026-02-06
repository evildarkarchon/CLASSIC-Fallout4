---
phase: 26-async-bridge-audit
plan: 01
subsystem: infra
tags: [rust, async-bridge, lazylock, dead-code-removal, tokio]

# Dependency graph
requires:
  - phase: 19-slint-bootstrap
    provides: AsyncBridge struct with gui-bridge feature
provides:
  - Cleaned async_bridge.rs with 3 public methods (run_with_ui_update, spawn_background, invoke_on_ui_thread)
  - std::sync::LazyLock throughout classic-shared-core (RUNTIME, METRICS, TIMER_START)
  - Leaner Cargo.toml without once_cell and num_cpus dependencies
affects: [26-02, 26-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "std::sync::LazyLock for all static initialization (replaces once_cell::sync::Lazy)"

key-files:
  created: []
  modified:
    - rust/foundation/classic-shared-core/src/async_bridge.rs
    - rust/foundation/classic-shared-core/src/lib.rs
    - rust/foundation/classic-shared-core/src/performance_core.rs
    - rust/foundation/classic-shared-core/Cargo.toml

key-decisions:
  - "Use std::sync::LazyLock instead of once_cell::sync::Lazy (std library, no external dependency needed)"
  - "Remove Bridge type alias - one canonical name (AsyncBridge) per user decision"

patterns-established:
  - "LazyLock pattern: Use std::sync::LazyLock::new(|| ...) for all static initialization in classic-shared-core"

# Metrics
duration: 5min
completed: 2026-02-06
---

# Phase 26 Plan 01: Dead Code Removal and LazyLock Migration Summary

**Removed BRIDGE_POOL, legacy methods, and Bridge alias from async_bridge.rs; migrated all statics to std::sync::LazyLock; removed once_cell and num_cpus dependencies**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-06T07:18:09Z
- **Completed:** 2026-02-06T07:22:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Removed 112 lines of dead code from async_bridge.rs (BRIDGE_POOL, run_with_ui_update_blocking, run_with_loading, Bridge alias)
- Migrated 3 static initializations from once_cell::sync::Lazy to std::sync::LazyLock (RUNTIME, METRICS, TIMER_START)
- Removed once_cell and num_cpus from classic-shared-core dependencies, reducing build time and dependency footprint
- All 25 tests pass, classic-gui compiles successfully

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead code from async_bridge.rs** - `5482fc1a` (refactor)
2. **Task 2: Migrate once_cell to LazyLock and remove unused dependencies** - `9bc7b374` (refactor)

## Files Created/Modified
- `rust/foundation/classic-shared-core/src/async_bridge.rs` - Cleaned to 3 public methods, removed dead code and unused imports
- `rust/foundation/classic-shared-core/src/lib.rs` - RUNTIME static uses std::sync::LazyLock
- `rust/foundation/classic-shared-core/src/performance_core.rs` - METRICS and TIMER_START statics use std::sync::LazyLock
- `rust/foundation/classic-shared-core/Cargo.toml` - Removed once_cell and num_cpus dependencies, kept rayon

## Decisions Made
- Used `std::sync::LazyLock` instead of `once_cell::sync::Lazy` -- LazyLock is in the standard library since Rust 1.80, eliminating the external dependency
- Removed `Bridge` type alias -- one canonical name (`AsyncBridge`) avoids confusion per user decision from research phase
- Used closure syntax `LazyLock::new(|| Instant::now())` for TIMER_START instead of function pointer `Lazy::new(Instant::now)` -- LazyLock requires explicit closure

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing Slint dependency issue: `cargo check -p classic-shared-core --features gui-bridge` fails due to `icu_properties`/`zerovec` missing `alloc` feature when building Slint directly. This is NOT caused by these changes and does not affect `cargo check -p classic-gui` which resolves the feature tree correctly. Verification was done via `cargo check -p classic-gui` instead.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- async_bridge.rs is clean and ready for Plan 02 (new API methods: run_cancellable, run_with_progress, run_with_timeout)
- LazyLock pattern established for any new statics in classic-shared-core
- No blockers or concerns

## Self-Check: PASSED

---
*Phase: 26-async-bridge-audit*
*Completed: 2026-02-06*
