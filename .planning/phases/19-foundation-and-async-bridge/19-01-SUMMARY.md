---
phase: 19-foundation-and-async-bridge
plan: 01
subsystem: ui
tags: [slint, rust, gui, tokio, async-bridge]

# Dependency graph
requires:
  - phase: classic-shared-core
    provides: Tokio runtime (ONE RUNTIME RULE), AsyncBridge with gui-bridge feature
provides:
  - classic-gui crate with Slint framework
  - Main window scaffold with tabbed interface
  - Build system with slint-build
  - ONE RUNTIME RULE compliance
affects: [19-02, 20-settings, 21-scan, 22-results, 23-articles, 24-backup]

# Tech tracking
tech-stack:
  added: [slint 1.15.0, slint-build 1.15.0, tokio-util 0.7]
  patterns: [Slint UI compilation, ONE RUNTIME RULE, AsyncBridge for GUI]

key-files:
  created:
    - rust/ui-applications/classic-gui/Cargo.toml
    - rust/ui-applications/classic-gui/build.rs
    - rust/ui-applications/classic-gui/src/main.rs
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/ui/main.slint
    - rust/ui-applications/classic-gui/assets/CLASSIC.ico
  modified:
    - rust/Cargo.toml

key-decisions:
  - "Skia renderer for hardware-accelerated graphics on Windows"
  - "Initialize Tokio runtime before Slint event loop for ONE RUNTIME RULE"
  - "Use workspace dependencies for version consistency"

patterns-established:
  - "GUI crates in rust/ui-applications/ directory"
  - "Slint files in ui/ subdirectory with build.rs compilation"
  - "AsyncBridge from classic-shared-core with gui-bridge feature"

# Metrics
duration: 6min
completed: 2026-02-05
---

# Phase 19 Plan 01: Create classic-gui Slint Crate Summary

**Slint-based GUI crate with build system, tabbed window scaffold, and ONE RUNTIME RULE compliance**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-05T09:18:55Z
- **Completed:** 2026-02-05T09:24:43Z
- **Tasks:** 3
- **Files created:** 6
- **Files modified:** 1

## Accomplishments
- Created classic-gui crate with Slint 1.15.0 and Skia renderer
- Established build system with slint-build for UI compilation
- Built tabbed window scaffold matching Python GUI layout (4 tabs)
- Verified executable builds and launches successfully (17.7MB release binary)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create classic-gui crate structure** - `37b0453e` (feat)
2. **Task 2: Create main.slint with scaffold UI** - `d85d3f88` (feat)
3. **Task 3: Verify build and window display** - (verification only, no commit)

## Files Created/Modified

### Created
- `rust/ui-applications/classic-gui/Cargo.toml` - Crate manifest with Slint, classic-shared-core dependencies
- `rust/ui-applications/classic-gui/build.rs` - Slint compilation build script
- `rust/ui-applications/classic-gui/src/main.rs` - Application entry point with ONE RUNTIME compliance
- `rust/ui-applications/classic-gui/src/lib.rs` - Library with AsyncBridge re-export
- `rust/ui-applications/classic-gui/ui/main.slint` - UI definition with 4-tab layout
- `rust/ui-applications/classic-gui/assets/CLASSIC.ico` - Application icon

### Modified
- `rust/Cargo.toml` - Added workspace member, updated slint to 1.15.0, added slint-build and tokio-util

## Decisions Made

1. **Skia renderer for Windows** - Selected `renderer-skia` feature for hardware-accelerated graphics. Builds successfully on Windows with MSVC.

2. **ONE RUNTIME RULE compliance** - Initialize Tokio runtime via `get_runtime()` before Slint event loop starts, ensuring single runtime across async operations.

3. **Workspace dependencies** - Added slint-build 1.15.0 and tokio-util 0.7 to workspace dependencies for version consistency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Documentation warnings from generated code** - Slint generates Rust code without doc comments, triggering `missing_docs` warnings. These are expected and harmless since they originate from the generated `MainWindow` struct.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 02:
- Crate structure established
- AsyncBridge available from classic-shared-core
- Window scaffold ready for callback wiring
- Progress bar and status properties exposed

**Next step:** Wire start-scan/cancel-scan callbacks to async operations with progress reporting.

---
*Phase: 19-foundation-and-async-bridge*
*Completed: 2026-02-05*
