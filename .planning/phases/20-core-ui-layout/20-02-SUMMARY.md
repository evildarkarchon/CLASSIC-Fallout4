---
phase: 20-core-ui-layout
plan: 02
subsystem: ui
tags: [slint, state-persistence, file-dialog, rfd, directories, serde]

# Dependency graph
requires:
  - phase: 20-01
    provides: Main window layout, PathInput widget, tab tracking
provides:
  - Window state persistence (position, size, paths, active tab)
  - Native folder dialog integration via rfd
  - Per-tab state management
affects: [21-scan-orchestration, 22-results-display, 24-settings]

# Tech tracking
tech-stack:
  added:
    - directories (cross-platform config directories)
    - rfd 0.15 (native file dialogs)
  patterns:
    - State persistence via JSON in user config directory
    - AsyncBridge.run_with_ui_update for async dialogs
    - Initialization flag pattern to skip saves during setup

key-files:
  created:
    - rust/ui-applications/classic-gui/src/state.rs
    - rust/ui-applications/classic-gui/src/dialogs.rs
  modified:
    - rust/ui-applications/classic-gui/Cargo.toml
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/src/main.rs

key-decisions:
  - "State stored as JSON in user config directory via directories crate"
  - "rfd 0.15 for native file dialogs (de facto Rust standard)"
  - "Save on every significant change (tab change, path selection, exit)"
  - "Initialization flag prevents spurious saves during setup"

patterns-established:
  - "State persistence: WindowState struct serialized to JSON in ProjectDirs config"
  - "Async dialogs: browse_folder with AsyncBridge.run_with_ui_update callback"
  - "App lifecycle: load state -> create window -> restore -> callbacks -> run -> save"

# Metrics
duration: 6min
completed: 2026-02-05
---

# Phase 20 Plan 02: State Persistence and Dialogs Summary

**Window state persistence using directories/serde and native folder dialogs via rfd with AsyncBridge integration**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-05T11:52:46Z
- **Completed:** 2026-02-05T11:58:46Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- State persistence module with per-tab geometry storage
- Native folder dialog integration using rfd crate
- Browse callbacks wired to async dialogs with path updates
- State loads on startup, saves on tab change/path selection/exit
- Unit tests for state serialization and geometry management

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies for state persistence and dialogs** - `a77eb2ce` (chore)
2. **Task 2: Create state persistence module** - `3afc9140` (feat)
3. **Task 3: Create dialogs module and wire everything to main** - `16ad249f` (feat)

## Files Created/Modified
- `rust/Cargo.toml` - Added directories crate to workspace
- `rust/ui-applications/classic-gui/Cargo.toml` - Added directories, serde, serde_json, rfd dependencies
- `rust/ui-applications/classic-gui/src/state.rs` - WindowState, TabGeometry, load/save functions
- `rust/ui-applications/classic-gui/src/dialogs.rs` - browse_folder async function using rfd
- `rust/ui-applications/classic-gui/src/lib.rs` - Export state and dialogs modules
- `rust/ui-applications/classic-gui/src/main.rs` - Wired state persistence and browse callbacks

## Decisions Made
- **directories crate for config path:** Cross-platform user config directory via ProjectDirs::from("com", "classic", "classic-gui")
- **JSON for state file:** Simple, human-readable, easy to debug with serde_json
- **rfd 0.15:** De facto standard for native Rust file dialogs, works with async/await
- **Save on significant changes:** Tab change, path selection, and app exit ensures state is preserved
- **Initialization flag:** Prevents saves during window setup that would overwrite restored state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Slint-generated code produces missing_docs warnings (30 warnings) - expected behavior, cannot add docs to auto-generated code
- clippy passes for all source code, only warnings are on generated Slint bindings

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- State persistence complete and functional
- Browse dialogs wired and working with AsyncBridge
- Paths persist between sessions
- Tab state persists between sessions
- Ready for Phase 21: Scan Orchestration (can use persisted paths for scanning)

---
*Phase: 20-core-ui-layout*
*Completed: 2026-02-05*
