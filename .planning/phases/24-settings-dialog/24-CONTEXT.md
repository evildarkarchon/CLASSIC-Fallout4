# Phase 24: Settings Dialog - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

User can configure application settings (game version, scan options, folder paths) within the existing Settings tab of the Slint GUI. Settings persist via classic-settings-core. No new capabilities (e.g., new setting types, import/export) — just the UI layer for existing settings.

</domain>

<decisions>
## Implementation Decisions

### Dialog access pattern
- Settings live directly in the existing Settings tab (third tab) — NOT a popup dialog window
- The Settings tab contains sub-tabs: General, Scanning, Paths
- No OK/Cancel buttons — settings save on change (live save pattern)
- A single "Reset to Defaults" button at the bottom of the Settings tab, below the sub-tabs
- Reset to Defaults requires confirmation before executing

### Settings per tab — General
- Game Version dropdown: Auto, Original, NextGen, VR
- Update Check toggle (boolean)
- Update Source dropdown: GitHub, Both
- FCX Mode toggle (boolean)

### Settings per tab — Scanning
- Simplify Logs toggle (boolean)
- Show FormID Values toggle (boolean)
- Move Unsolved Logs toggle (boolean)
- Auto Switch After Scan toggle (boolean)

### Settings per tab — Paths
- INI Folder Path (text input + browse button)
- Mods Folder Path (text input + browse button)
- Custom Scan Path (text input + browse button)
- All three use rfd native folder dialogs for browsing

### Excluded settings (not relevant to Rust GUI)
- Disable CLI Progress (CLI-only)
- Audio Notifications (not implemented in Rust GUI)
- Show Statistics (not implemented in Rust GUI)
- local_only / offline_data (internal)

### Game version behavior
- Dropdown offers: Auto, Original, NextGen, VR
- "Auto" runs detection immediately when selected and shows detected version as hint (e.g., "Auto (detected: NextGen)")
- Changing game version does NOT reset folder paths — user manually updates paths if needed
- Legacy VR Mode migration: if YAML has VR Mode=true and no Game Version, auto-migrate to Game Version=VR on first load

### Save/cancel semantics
- Live save-on-change for all settings (no OK/Cancel buttons)
- Dropdowns save immediately on selection change
- Checkboxes/toggles save immediately on click
- Path fields save immediately after browse dialog selection; if typed manually, save on focus loss or Enter key
- Path validation: validate that folder exists before saving; reject and show error if directory doesn't exist; only save valid directories
- Reset to Defaults: single button at bottom of Settings tab, resets ALL settings across all sub-tabs, requires confirmation prompt before executing

### Claude's Discretion
- Sub-tab visual style (standard Slint TabWidget or custom)
- Settings label placement and spacing
- Error display style for invalid paths (inline error text, colored border, or both)
- Auto-detection hint display format for "Auto" game version
- Confirmation prompt style for Reset to Defaults (modal overlay or inline)
- Default values for each setting

</decisions>

<specifics>
## Specific Ideas

- User explicitly dislikes the Save/Cancel pattern — settings should feel immediate, like toggling a switch
- Validation should be strict for paths: only save directories that actually exist
- The "Auto" game version should give immediate feedback about what it detected, not wait until scan time

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-settings-dialog*
*Context gathered: 2026-02-05*
