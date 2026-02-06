---
phase: 24-settings-dialog
plan: 02
subsystem: ui
tags: [slint, settings, yaml, config, persistence, callbacks, rfd, path-validation]

# Dependency graph
requires:
  - phase: 24-settings-dialog-01
    provides: Settings tab UI layout, ClassicConfig with game_version/update_source, all Slint callbacks/properties
  - phase: 20-window-management
    provides: AppState initialization pattern, persist_state pattern, browse_folder async dialog
provides:
  - Settings persistence module (settings.rs) with load/save/validate/reset
  - 15 live save-on-change callbacks wired in main.rs
  - Settings loaded from YAML at startup and displayed in UI
  - Path validation with inline error display
  - Game version auto-detection stub with hint display
  - Reset to Defaults with full UI repopulation
affects: [25-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live save-on-change: each setting callback immediately persists to YAML"
    - "Initialization guard: all callbacks check state.initialized to prevent save loops"
    - "populate_settings_ui: single function for startup and reset, called while initialized=false"
    - "save_path_setting: validates directory existence, returns user-facing error string"

key-files:
  created:
    - "rust/ui-applications/classic-gui/src/settings.rs"
  modified:
    - "rust/ui-applications/classic-gui/Cargo.toml"
    - "rust/ui-applications/classic-gui/src/lib.rs"
    - "rust/ui-applications/classic-gui/src/main.rs"

key-decisions:
  - "ProjectDirs config directory for settings.yaml (same as window_state.json)"
  - "save_full_config approach: update in-memory ClassicConfig then save entire file"
  - "Empty path clears the setting (sets to None) without validation error"
  - "Game version detect_game_version is a stub checking for VR/standard exe"
  - "Reset temporarily disables initialized flag to prevent save loops during repopulation"

patterns-established:
  - "Settings callback pattern: lock state, check initialized, update field, save, update UI"
  - "Path validation pattern: validate -> update config -> save -> clear error (or show error)"
  - "populate_settings_ui: reusable function for both startup and reset flows"

# Metrics
duration: 6min
completed: 2026-02-06
---

# Phase 24 Plan 02: Settings Persistence Wiring Summary

**Live save-on-change settings persistence via ClassicConfig with 15 callbacks, path validation, game version detection stub, and Reset to Defaults**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-06T04:44:45Z
- **Completed:** 2026-02-06T04:50:31Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created settings.rs module with 12 public functions for load/save/validate/reset/convert
- Wired all 15 settings callbacks in main.rs for live save-on-change persistence
- Settings load from YAML at startup and populate all UI controls
- Path validation rejects non-existent directories with inline error messages
- Game version "Auto" runs detection and displays hint text
- Reset to Defaults resets config, saves to YAML, and refreshes all UI controls
- 13 unit tests covering round-trips, defaults, validation, and error cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create settings.rs module with load/save/validate/reset logic** - `d3ef374d` (feat)
2. **Task 2: Wire settings callbacks in main.rs** - `613cd2d5` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/src/settings.rs` - Settings persistence: load, save, validate paths, reset, game version detection, index/string converters
- `rust/ui-applications/classic-gui/Cargo.toml` - Added classic-config-core, anyhow, yaml-rust2 dependencies
- `rust/ui-applications/classic-gui/src/lib.rs` - Added settings module and re-exports
- `rust/ui-applications/classic-gui/src/main.rs` - AppState with ClassicConfig, populate_settings_ui, 15 callback registrations

## Decisions Made
- **ProjectDirs for settings.yaml**: Same config directory as window_state.json for consistency
- **Full config save approach**: Rather than individual YAML key updates, the entire ClassicConfig is saved on each change. Simpler, avoids partial-write issues, and ClassicConfig is small
- **Empty path clears setting**: Entering empty text in a path field clears the setting without error, matching user expectation
- **Stub game version detection**: Checks for Fallout4VR.exe (VR) or Fallout4.exe (NextGen). Full EXE version detection is deferred
- **Reset disabled initialized flag**: Temporarily sets initialized=false during repopulation to prevent cascading saves from UI property updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Settings tab is fully functional: all controls load, save, validate, and reset
- Phase 24 (Settings Dialog) is now complete (both plans done)
- Ready for Phase 25 integration testing
- No blockers

## Self-Check: PASSED

---
*Phase: 24-settings-dialog*
*Completed: 2026-02-06*
