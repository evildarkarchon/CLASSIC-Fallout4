---
phase: 24-settings-dialog
plan: 01
subsystem: ui
tags: [slint, settings, tabwidget, combobox, switch, yaml, config]

# Dependency graph
requires:
  - phase: 20-window-management
    provides: TabWidget layout, PathInput widget, fluent-dark theme
  - phase: 23-markdown-renderer
    provides: types.slint shared struct pattern, widget organization
provides:
  - Settings tab UI with three sub-tabs (General, Scanning, Paths)
  - All settings properties and callbacks on MainWindow
  - ClassicConfig with game_version and update_source fields
  - VR mode legacy migration in config loading
  - Reset to Defaults with inline confirmation
affects: [24-02, 25-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nested TabWidget for sub-tab navigation"
    - "Inline confirmation pattern for destructive actions"
    - "SettingsPathInput private component with validation error display"
    - "VR mode migration in ClassicConfig::from_yaml"

key-files:
  created:
    - "rust/ui-applications/classic-gui/ui/widgets/settings_general.slint"
    - "rust/ui-applications/classic-gui/ui/widgets/settings_scanning.slint"
    - "rust/ui-applications/classic-gui/ui/widgets/settings_paths.slint"
  modified:
    - "rust/ui-applications/classic-gui/ui/main.slint"
    - "rust/business-logic/classic-config-core/src/config.rs"

key-decisions:
  - "Nested TabWidget for settings sub-tabs inside Settings tab"
  - "Inline confirmation for Reset to Defaults (not modal popup)"
  - "SettingsPathInput as private component in settings_paths.slint"
  - "VR mode migration: vr_mode=true + no game_version -> game_version=VR"

patterns-established:
  - "Nested TabWidget: sub-tabs inside a main tab"
  - "Inline confirmation: show/hide confirm row instead of modal"
  - "Settings property naming: setting-{name} prefix on MainWindow"

# Metrics
duration: 5min
completed: 2026-02-06
---

# Phase 24 Plan 01: Settings Tab UI Layout Summary

**Three-tab Settings UI (General/Scanning/Paths) with nested TabWidget, inline Reset confirmation, and ClassicConfig extended with game_version/update_source fields including VR mode migration**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-06T04:34:46Z
- **Completed:** 2026-02-06T04:39:42Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended ClassicConfig with game_version and update_source fields with full YAML round-trip
- Implemented VR mode legacy migration (vr_mode=true -> game_version="VR" on load)
- Created three settings sub-tab Slint widgets (General, Scanning, Paths)
- Replaced Settings tab placeholder with nested TabWidget and all controls
- Added Reset to Defaults with inline confirmation below sub-tabs
- Wired all settings properties and callbacks through MainWindow

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend ClassicConfig with game_version and update_source** - `efb6121` (feat)
2. **Task 2: Create settings sub-tab widgets and wire into main.slint** - `9dbde22` (feat)

## Files Created/Modified
- `rust/ui-applications/classic-gui/ui/widgets/settings_general.slint` - General settings sub-tab: Game Version dropdown, Update Check/FCX Mode switches, Update Source dropdown
- `rust/ui-applications/classic-gui/ui/widgets/settings_scanning.slint` - Scanning settings sub-tab: 4 toggle switches for scan behavior
- `rust/ui-applications/classic-gui/ui/widgets/settings_paths.slint` - Paths settings sub-tab: 3 path inputs with validation error display and Browse buttons
- `rust/ui-applications/classic-gui/ui/main.slint` - Settings tab with nested TabWidget, all settings properties/callbacks, Reset to Defaults
- `rust/business-logic/classic-config-core/src/config.rs` - ClassicConfig with game_version, update_source, VR migration, and tests

## Decisions Made
- **Nested TabWidget**: Used standard Slint TabWidget inside Settings Tab for sub-tabs, confirmed working with fluent-dark theme
- **Inline confirmation**: Reset to Defaults uses show/hide row pattern instead of modal popup (simpler, better Slint support)
- **SettingsPathInput**: Private component in settings_paths.slint wrapping LineEdit+Browse+error -- not exported since it is specific to settings
- **Property naming**: All settings use `setting-` prefix on MainWindow to distinguish from scan/results properties
- **Label widths**: 140px min-width for General/Paths labels, 180px for Scanning labels to accommodate longer text

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All UI controls in place, ready for Plan 02 to wire Rust callbacks for persistence
- ClassicConfig has all fields Plan 02 needs (game_version, update_source, all booleans, paths)
- Callbacks are defined on MainWindow but not yet connected to Rust handlers
- No blockers for Plan 02

## Self-Check: PASSED

---
*Phase: 24-settings-dialog*
*Completed: 2026-02-06*
