---
phase: 26-async-bridge-audit
plan: 03
subsystem: async-bridge
tags: [asyncbridge, slint, tokio, cancellation, dispatcher, testing, mockdispatcher]

# Dependency graph
requires:
  - phase: 26-02
    provides: "BridgeError, EventLoopDispatcher trait, SlintDispatcher, set_dispatcher, run_with_timeout, run_cancellable"
provides:
  - "GUI call sites migrated to new bridge API (scan uses run_cancellable)"
  - "SlintDispatcher initialized at startup before any bridge usage"
  - "15 comprehensive bridge unit tests with MockDispatcher and FailingDispatcher"
  - "Phase 26 async bridge audit complete"
affects: []

# Tech tracking
tech-stack:
  added: ["zerovec (dev-dep workaround for icu_properties/slint transitive)"]
  patterns: ["Dual cancellation (bridge-level + inner-loop)", "MockDispatcher for bridge testing without Slint event loop", "FailingDispatcher for error path testing"]

key-files:
  created: []
  modified:
    - "rust/ui-applications/classic-gui/src/main.rs"
    - "rust/foundation/classic-shared-core/src/async_bridge.rs"
    - "rust/foundation/classic-shared-core/Cargo.toml"

key-decisions:
  - "Dual cancellation pattern: run_cancellable for bridge-level + CancellationToken param for per-log inner-loop"
  - "set_dispatcher(SlintDispatcher) called explicitly at startup (step 3b) rather than relying on get_or_init default"
  - "Browse callbacks left unchanged -- no timeout/cancellation needs, migration would add complexity without benefit"
  - "zerovec dev-dependency workaround for icu_properties transitive dep issue when building with gui-bridge in isolation"
  - "15 unit tests with MockDispatcher and FailingDispatcher rather than integration tests requiring Slint event loop"

patterns-established:
  - "Dual cancellation: run_cancellable wraps outer cancellation, inner function checks token per-iteration"
  - "MockDispatcher pattern: implements EventLoopDispatcher with synchronous execution and dispatch counting"
  - "FailingDispatcher pattern: simulates stopped event loop for error path testing"

# Metrics
duration: 7min
completed: 2026-02-06
---

# Phase 26 Plan 03: GUI Call Site Migration and Bridge Tests Summary

**Scan callback migrated to run_cancellable with dual cancellation, SlintDispatcher initialized at startup, 15 bridge unit tests with MockDispatcher**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-06T07:33:46Z
- **Completed:** 2026-02-06T07:40:46Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Migrated scan callback from run_with_ui_update to run_cancellable with dual cancellation pattern
- Added set_dispatcher(SlintDispatcher) at startup (step 3b) before any AsyncBridge usage
- Wrote 15 comprehensive bridge unit tests covering error types, dispatcher contracts, and type safety
- Fixed icu_properties/zerovec transitive dependency issue for standalone gui-bridge testing
- Phase 26 (Async Bridge Audit) complete: dead code removed, deps cleaned, APIs added, call sites updated, tests written

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate GUI call sites to new bridge API** - `1fd9f08f` (feat)
2. **Task 2: Write bridge unit tests with MockDispatcher** - `2bb96e6f` (test)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `rust/ui-applications/classic-gui/src/main.rs` - Updated imports (SlintDispatcher, set_dispatcher), added dispatcher init at startup, migrated scan callback to run_cancellable with Option<Result> handling
- `rust/foundation/classic-shared-core/src/async_bridge.rs` - Replaced minimal 2-test module with 15 comprehensive tests using MockDispatcher and FailingDispatcher
- `rust/foundation/classic-shared-core/Cargo.toml` - Added zerovec dev-dependency with alloc feature (workaround for icu_properties transitive dep)

## Decisions Made
- **Dual cancellation pattern**: run_cancellable handles bridge-level cancellation (races whole future against token), while scan_crash_logs retains its CancellationToken parameter for per-log inner-loop checks. Both are needed: bridge catches cancellation between await points, inner-loop catches mid-iteration.
- **Explicit dispatcher init**: Called set_dispatcher(SlintDispatcher) explicitly at startup rather than relying on get_or_init fallback. Makes initialization order explicit and mirrors test pattern.
- **Browse callbacks unchanged**: The 5 browse dialog callbacks and 1 spawn_background timer use run_with_ui_update / spawn_background correctly. No timeout or cancellation needs -- migration would add complexity without benefit.
- **zerovec dev-dep workaround**: When building classic-shared-core with gui-bridge feature in isolation, the minimal Slint dependency doesn't activate zerovec/alloc transitively (classic-gui's richer Slint features do). Added zerovec = { version = "0.11", features = ["alloc"] } as dev-dependency plus cargo update for icu_properties 2.0.1 -> 2.0.2 to resolve the compile error.
- **Unit tests over integration tests**: The OnceLock-based DISPATCHER can only be set once per process, making full bridge method integration tests fragile. Instead, 15 unit tests validate error types, trait contracts, closure execution, and type safety through MockDispatcher and FailingDispatcher without requiring a Slint event loop.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed icu_properties/zerovec transitive dependency for gui-bridge testing**
- **Found during:** Task 2 (Bridge unit tests)
- **Issue:** `cargo test -p classic-shared-core --features gui-bridge` failed with icu_properties compile errors because zerovec lacked the `alloc` feature when building classic-shared-core in isolation (vs through classic-gui which activates it transitively)
- **Fix:** Added zerovec dev-dependency with alloc feature and ran cargo update for icu_properties 2.0.1 -> 2.0.2
- **Files modified:** rust/foundation/classic-shared-core/Cargo.toml, Cargo.lock
- **Verification:** `cargo test -p classic-shared-core --features gui-bridge` passes, `cargo check -p classic-gui` still compiles
- **Committed in:** 2bb96e6f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to unblock standalone gui-bridge testing. No scope creep.

## Issues Encountered
- The Cargo.lock had icu_properties 2.0.1 which had a bug with zerovec feature resolution. Updating to 2.0.2 plus the zerovec dev-dep workaround resolved the issue cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 26 (Async Bridge Audit) is complete. All 3 plans executed:
  - 26-01: Dead code removal, dependency cleanup, module documentation
  - 26-02: Resilience APIs (BridgeError, EventLoopDispatcher, run_with_timeout, run_cancellable)
  - 26-03: GUI call site migration and comprehensive bridge tests
- v9.0.0 Slint GUI milestone is complete (all 16 plans across phases 19-26)
- The async bridge is now fully audited with clean API, tested dispatcher abstraction, and proper error handling

## Self-Check: PASSED

---
*Phase: 26-async-bridge-audit*
*Completed: 2026-02-06*
