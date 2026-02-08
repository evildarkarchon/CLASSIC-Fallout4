# CLASSIC GUI Simplification Design

**Date**: 2026-02-07
**Scope**: Rust GUI (classic-gui) UI/UX improvements
**Status**: Approved

## Summary

Six changes to simplify and fix the Rust Slint GUI:

1. Replace scan checkboxes with direct action buttons
2. Fix path label/input row heights (Main + Settings)
3. Remove Update Source selector (GitHub-only)
4. Remove Custom Scan Path from Settings (redundant with Main tab)
5. Move "Generate statistics" to Settings > General
6. Fix results viewer not showing all report sections

## 1. Main Tab Redesign: Scan Buttons

### Current
- GroupBox "Scan Options" with 3 CheckBoxes: Scan crash logs, Scan game files, Generate statistics
- Morphing "Scan Crash Logs / Cancel" button at bottom

### New
- Remove the "Scan Options" GroupBox entirely
- Replace bottom button with two side-by-side action buttons:
  - **"Scan Crash Logs"** - immediately scans using Crash Logs path
  - **"Scan Game Files"** - immediately scans using Game Folder path
- Both morph to **"Cancel"** during scan (existing morphing pattern)
- "Generate statistics" moves to Settings (see change 5)

### Layout
```
Main Options tab:
  [Folder Paths GroupBox]
    Crash Logs: [path] [Browse]
    Game Folder: [path] [Browse]
  [Spacer]
  [Scan Crash Logs] [Scan Game Files]  <- centered
```

### Properties to change
- Remove: `option-scan-logs`, `option-scan-game` (no longer user-facing toggles)
- Keep: `scan-in-progress`, `scan-status`, `scan-progress`
- Add: `start-scan-logs()` and `start-scan-game()` callbacks (replace `start-scan()`)

## 2. Path Label Height Fix

### Problem
Path input rows on Main tab and Settings > Paths are taller than necessary.

### Fix
Add `height: 32px` to each `HorizontalBox` containing a path label + PathInput. This matches the toolbar button height for visual consistency.

### Files affected
- `ui/main.slint` - Crash Logs and Game Folder rows
- `ui/widgets/settings_paths.slint` - All SettingsPathInput rows

## 3. Remove Update Source Selector

### Current
Settings > General has a ComboBox with ["GitHub", "Both"] for update source selection.

### Change
Remove entirely. GitHub is now the only update source.

### Removals
- `settings_general.slint`: HorizontalBox with "Update Source:" label + ComboBox
- `main.slint`: `update-source-index` property, `setting-update-source-changed` callback
- `main.rs`: `on_setting_update_source_changed` handler, `update_source_index_to_string()`, `update_source_string_to_index()` functions
- Settings initialization code loading `update_source`

## 4. Remove Custom Scan Path from Settings

### Rationale
The "Crash Logs" path on the Main tab serves the same purpose as the Custom Scan Path.

### Removals
- `settings_paths.slint`: SettingsPathInput for "Custom Scan Path:"
- `main.slint`: `setting-scan-path`, `setting-scan-error`, `setting-scan-has-error` properties; `setting-browse-scan`, `setting-scan-path-accepted` callbacks
- `main.rs`: Browse handler, path-accepted handler, validation logic for scan_custom
- Settings initialization code loading `scan_custom`

## 5. Move "Generate Statistics" to Settings > General

### Change
Add a CheckBox to `settings_general.slint`:
```slint
CheckBox {
    text: "Generate statistics during scan";
    checked <=> root.generate-stats;
    toggled => { root.generate-stats-changed(self.checked); }
}
```

### Wiring
- Property: `generate-stats: bool` (in-out, persisted to config)
- Callback: `generate-stats-changed(bool)` saves to YAML config
- On startup: load from config and set property
- Scan logic reads this property when starting either scan type

## 6. Fix Results Viewer Missing Sections

### Problem
FormID, Plugin-related Errors, Mods with Solutions, and Named Records sections don't display even though the data exists in report_lines.

### Approach
Debug investigation using real crash log reports from the project's `Crash Logs/` directory:

1. Run a real scan and capture the full `report_lines` output
2. Check if the missing sections are present in the raw lines
3. Pass the joined content through `parse_markdown()` and verify all blocks are generated
4. If blocks are generated but not displayed, check Slint rendering
5. If blocks are not generated, fix the markdown parser

### Likely causes
- Triple-newline sequences from embedded `\n\n` in lines + `\n` join separator
- Content gating in orchestrator (conditional guards preventing sections from being added)
- Slint model/rendering limit with large block counts

### Test plan
- Add test using representative report content containing all section types
- Verify `parse_markdown()` produces blocks for every section
- Visual verification with real scan output
