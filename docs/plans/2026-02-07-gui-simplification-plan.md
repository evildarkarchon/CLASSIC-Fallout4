# GUI Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify the Rust Slint GUI by converting scan checkboxes to action buttons, fixing path label heights, removing redundant settings, and fixing the results viewer.

**Architecture:** All changes are in the `classic-gui` crate (`rust/ui-applications/classic-gui/`). Changes span Slint markup (`.slint` files), Rust callbacks (`main.rs`), settings persistence (`settings.rs`), and the markdown parser (`markdown.rs`). The scan logic (`scan.rs`) stays unchanged -- only how it's triggered changes.

**Tech Stack:** Slint 1.x (`.slint` markup), Rust, pulldown-cmark (markdown parsing), classic-config-core (settings YAML)

---

### Task 1: Remove Update Source Selector (Settings > General)

The simplest removal. No behavioral changes, just deleting dead code.

**Files:**
- Modify: `rust/ui-applications/classic-gui/ui/widgets/settings_general.slint:13-14,22,68-83`
- Modify: `rust/ui-applications/classic-gui/ui/main.slint:54,93,302,306`
- Modify: `rust/ui-applications/classic-gui/src/main.rs:25-26,691,784-799`
- Modify: `rust/ui-applications/classic-gui/src/settings.rs:110,249-272`
- Modify: `rust/ui-applications/classic-gui/src/lib.rs:27-28`

**Step 1: Remove Update Source from settings_general.slint**

Delete the `update-source-index` property (line 14), the `update-source-changed` callback (line 22), and the entire "Update Source" HorizontalBox (lines 68-83).

The component should go from having these properties/callbacks:

```slint
// Remove this property:
in-out property <int> update-source-index: 0;

// Remove this callback:
callback update-source-changed(int);

// Remove this entire HorizontalBox (lines 68-83):
// Update Source
HorizontalBox {
    spacing: 8px;
    Text {
        text: "Update Source:";
        min-width: 140px;
        vertical-alignment: center;
    }
    ComboBox {
        model: ["GitHub", "Both"];
        current-index <=> root.update-source-index;
        selected(value) => {
            root.update-source-changed(self.current-index);
        }
    }
}
```

Also update the file header comment from:
```
// Contains: Game Version dropdown, Update Check toggle, Update Source dropdown, FCX Mode toggle
```
to:
```
// Contains: Game Version dropdown, Update Check toggle, FCX Mode toggle
```

**Step 2: Remove Update Source wiring from main.slint**

Delete these lines:
- Line 54: `in-out property <int> setting-update-source-index: 0;`
- Line 93: `callback setting-update-source-changed(int);`
- Line 302: `update-source-index <=> root.setting-update-source-index;`
- Line 306: `update-source-changed(idx) => { root.setting-update-source-changed(idx); }`

**Step 3: Remove Update Source Rust handlers from main.rs**

Delete the import of `update_source_index_to_string` and `update_source_string_to_index` from line 25.

Delete line 691: `window.set_setting_update_source_index(update_source_string_to_index(&config.update_source));`

Delete the entire "Update source dropdown changed" block (lines 784-799):
```rust
// Update source dropdown changed
{
    let state = Arc::clone(state);
    window.on_setting_update_source_changed(move |index| {
        let mut state = state.lock();
        if !state.initialized {
            return;
        }
        let source_str = update_source_index_to_string(index);
        if let Err(e) =
            save_setting_string(&mut state.settings, "update_source", source_str)
        {
            tracing::warn!("Failed to save update_source: {}", e);
        }
    });
}
```

**Step 4: Remove Update Source helpers from settings.rs**

Delete the `"update_source"` arm from `save_setting_string` (line 110):
```rust
"update_source" => config.update_source = value.to_string(),
```

Delete both helper functions (lines 249-272):
```rust
pub fn update_source_index_to_string(index: i32) -> &'static str { ... }
pub fn update_source_string_to_index(source: &str) -> i32 { ... }
```

Delete the corresponding tests:
- `test_update_source_index_round_trip` (lines 301-308)
- `test_update_source_unknown_defaults_to_github` (lines 310-314)
- `test_update_source_all_values` (lines 418-421)
- `test_update_source_negative_index` (lines 423-426)

In `test_save_setting_string_all_keys`, remove `"update_source"` from the keys array (line 508).

In `test_save_setting_string_modifies_config`, remove the update_source block (lines 570-571).

**Step 5: Update lib.rs re-exports**

Remove `update_source_index_to_string` and `update_source_string_to_index` from the `pub use settings::{...}` block (lines 27-28).

**Step 6: Build and run tests**

Run: `cargo build -p classic-gui 2>&1`
Expected: Compiles with no errors (warnings ok)

Run: `cargo test -p classic-gui 2>&1`
Expected: All remaining tests pass

**Step 7: Commit**

```bash
git add rust/ui-applications/classic-gui/
git commit -m "refactor(gui): remove Update Source selector (GitHub-only)"
```

---

### Task 2: Remove Custom Scan Path from Settings > Paths

Another removal -- the "Custom Scan Path" row and all its wiring.

**Files:**
- Modify: `rust/ui-applications/classic-gui/ui/widgets/settings_paths.slint:60-63,68,73,96-103`
- Modify: `rust/ui-applications/classic-gui/ui/main.slint:70-72,105,108,334-336,339,342`
- Modify: `rust/ui-applications/classic-gui/src/main.rs:725-731,983-1031,1087-1112`
- Modify: `rust/ui-applications/classic-gui/src/settings.rs:146,163`

**Step 1: Remove Custom Scan Path from settings_paths.slint**

Delete the scan-path properties (lines 60-63):
```slint
// Custom Scan Path
in-out property <string> scan-path: "";
in-out property <string> scan-error: "";
in-out property <bool> scan-has-error: false;
```

Delete the scan callbacks (lines 68, 73):
```slint
callback browse-scan();
callback scan-path-accepted(string);
```

Delete the Custom Scan Path SettingsPathInput (lines 96-103):
```slint
SettingsPathInput {
    label: "Custom Scan Path:";
    path <=> root.scan-path;
    error-message <=> root.scan-error;
    has-error <=> root.scan-has-error;
    browse-clicked => { root.browse-scan(); }
    path-accepted(text) => { root.scan-path-accepted(text); }
}
```

Update file header comment:
```
// Contains: INI Folder, Mods Folder with validation error display
```

**Step 2: Remove Custom Scan Path wiring from main.slint**

Delete lines 70-72:
```slint
in-out property <string> setting-scan-path: "";
in-out property <string> setting-scan-error: "";
in-out property <bool> setting-scan-has-error: false;
```

Delete lines 105, 108:
```slint
callback setting-browse-scan();
callback setting-scan-path-accepted(string);
```

Delete lines 334-336:
```slint
scan-path <=> root.setting-scan-path;
scan-error <=> root.setting-scan-error;
scan-has-error <=> root.setting-scan-has-error;
```

Delete lines 339, 342:
```slint
browse-scan => { root.setting-browse-scan(); }
scan-path-accepted(text) => { root.setting-scan-path-accepted(text); }
```

**Step 3: Remove Custom Scan Path Rust handlers from main.rs**

Delete the `scan_custom` block from `populate_settings_ui` (lines 725-731):
```rust
if let Some(ref path) = config.paths.scan_custom {
    window.set_setting_scan_path(path.to_string_lossy().to_string().into());
} else {
    window.set_setting_scan_path(SharedString::default());
}
window.set_setting_scan_error(SharedString::default());
window.set_setting_scan_has_error(false);
```

Delete the "Browse custom scan folder" block (lines 983-1031).

Delete the "Scan path accepted" block (lines 1087-1112).

**Step 4: Remove scan_custom from settings.rs path validation**

Remove the `"scan_custom"` arm from the empty-path match in `save_path_setting` (line 146):
```rust
"scan_custom" => config.paths.scan_custom = None,
```

Remove the `"scan_custom"` arm from the valid-path match (line 163):
```rust
"scan_custom" => config.paths.scan_custom = Some(path_buf),
```

Remove the related tests:
- `test_save_path_setting_empty_clears_scan_custom` (lines 437-442)
- `test_save_path_setting_valid_dir_scan_custom` (lines 584-592)

**Step 5: Build and run tests**

Run: `cargo build -p classic-gui 2>&1`
Run: `cargo test -p classic-gui 2>&1`
Expected: Compiles and all tests pass

**Step 6: Commit**

```bash
git add rust/ui-applications/classic-gui/
git commit -m "refactor(gui): remove Custom Scan Path from Settings (redundant with Main tab)"
```

---

### Task 3: Fix Path Label Heights

Add `height: 32px` to path input rows on both the Main tab and Settings > Paths.

**Files:**
- Modify: `rust/ui-applications/classic-gui/ui/main.slint:134,150`
- Modify: `rust/ui-applications/classic-gui/ui/widgets/settings_paths.slint:16`

**Step 1: Fix Main tab path row heights**

In `main.slint`, add `height: 32px;` to both HorizontalBox rows in the Folder Paths GroupBox.

For the Crash Logs row (around line 134), change:
```slint
HorizontalBox {
    spacing: 8px;
```
to:
```slint
HorizontalBox {
    spacing: 8px;
    height: 32px;
```

Same for the Game Folder row (around line 150).

**Step 2: Fix Settings > Paths row heights**

In `settings_paths.slint`, the `SettingsPathInput` component's inner HorizontalBox (line 16) needs a height constraint. Change:
```slint
HorizontalBox {
    spacing: 8px;
```
to:
```slint
HorizontalBox {
    spacing: 8px;
    height: 32px;
```

This fixes all Settings path rows in one place since they all use the same component.

**Step 3: Build to verify no layout errors**

Run: `cargo build -p classic-gui 2>&1`
Expected: Compiles cleanly

**Step 4: Commit**

```bash
git add rust/ui-applications/classic-gui/ui/
git commit -m "fix(gui): constrain path input row heights to 32px"
```

---

### Task 4: Replace Scan Checkboxes with Action Buttons

The main UI redesign -- remove the Scan Options GroupBox and morphing button, replace with two side-by-side action buttons.

**Files:**
- Modify: `rust/ui-applications/classic-gui/ui/main.slint:37-39,78,167-211`
- Modify: `rust/ui-applications/classic-gui/src/main.rs:302-419`

**Step 1: Update main.slint properties and callbacks**

Remove these properties (lines 37-39):
```slint
in-out property <bool> option-scan-logs: true;
in-out property <bool> option-scan-game: false;
in-out property <bool> option-generate-stats: false;
```

Replace the single `start-scan` callback (line 78):
```slint
callback start-scan();
```
with two separate callbacks:
```slint
callback start-scan-logs();
callback start-scan-game();
```

**Step 2: Replace Main tab scan UI**

Delete the entire Scan Options GroupBox (lines 167-189):
```slint
// Scan options section
GroupBox {
    title: "Scan Options";
    ...
}
```

Replace the bottom button section (lines 191-211) with:
```slint
// Flexible spacer to push buttons to bottom
Rectangle {
    vertical-stretch: 1;
}

// Action buttons
HorizontalBox {
    alignment: center;
    spacing: 12px;

    Button {
        text: root.scan-in-progress ? "Cancel" : "Scan Crash Logs";
        primary: !root.scan-in-progress;
        enabled: root.scan-in-progress || root.crash-log-path != "";
        clicked => {
            if (root.scan-in-progress) {
                root.cancel-scan();
            } else {
                root.start-scan-logs();
            }
        }
    }

    Button {
        text: root.scan-in-progress ? "Cancel" : "Scan Game Files";
        enabled: !root.scan-in-progress;
        clicked => {
            if (root.scan-in-progress) {
                root.cancel-scan();
            } else {
                root.start-scan-game();
            }
        }
    }
}
```

Note: The "Scan Game Files" button is always disabled during scan (only one cancel needed) and disabled when not in progress because game file scanning is not yet implemented (stub). The crash log button disables when path is empty.

**Step 3: Wire up the new scan callbacks in main.rs**

Replace `window.on_start_scan(...)` (lines 308-418) with `window.on_start_scan_logs(...)`. The callback body stays nearly identical -- it already reads `crash_log_path` and calls `scan_crash_logs`. Just rename the callback registration from `on_start_scan` to `on_start_scan_logs`.

Add a stub for `window.on_start_scan_game`:
```rust
// Start game files scan callback (stub - not yet implemented)
{
    let window_weak = window.as_weak();
    window.on_start_scan_game(move || {
        if let Some(w) = window_weak.upgrade() {
            w.set_scan_status("Game file scanning not yet implemented".into());
        }
    });
}
```

**Step 4: Build and run tests**

Run: `cargo build -p classic-gui 2>&1`
Run: `cargo test -p classic-gui 2>&1`
Expected: Compiles and tests pass

**Step 5: Commit**

```bash
git add rust/ui-applications/classic-gui/
git commit -m "feat(gui): replace scan checkboxes with direct action buttons"
```

---

### Task 5: Move Generate Statistics to Settings > General

Add "Generate statistics" as a persistent boolean setting in the General settings tab.

**Files:**
- Modify: `rust/ui-applications/classic-gui/ui/widgets/settings_general.slint`
- Modify: `rust/ui-applications/classic-gui/ui/main.slint`
- Modify: `rust/ui-applications/classic-gui/src/main.rs`
- Modify: `rust/ui-applications/classic-gui/src/settings.rs`

**Step 1: Add Generate Statistics to settings_general.slint**

Add a new property, callback, and CheckBox. After the FCX Mode section (line 99), before the spacer, add:

```slint
// Generate Statistics
HorizontalBox {
    spacing: 8px;
    Text {
        text: "Generate Statistics:";
        min-width: 140px;
        vertical-alignment: center;
    }
    Switch {
        checked <=> root.generate-stats;
        toggled => {
            root.generate-stats-changed(self.checked);
        }
    }
}
```

Add to the component's properties section (after `fcx-mode`):
```slint
// Generate statistics
in-out property <bool> generate-stats: false;
```

Add to the callbacks section:
```slint
callback generate-stats-changed(bool);
```

Update file header comment to include "Generate Statistics toggle".

**Step 2: Wire in main.slint**

Add a new settings property (in the General section, around line 55):
```slint
in-out property <bool> setting-generate-stats: false;
```

Add a new callback (in the General callbacks section, around line 94):
```slint
callback setting-generate-stats-changed(bool);
```

Wire in the SettingsGeneral component usage (around line 303):
```slint
generate-stats <=> root.setting-generate-stats;
generate-stats-changed(val) => { root.setting-generate-stats-changed(val); }
```

**Step 3: Add Rust callback handler in main.rs**

In `setup_settings_general_callbacks`, add after the FCX mode block:
```rust
// Generate statistics toggle changed
{
    let state = Arc::clone(state);
    window.on_setting_generate_stats_changed(move |checked| {
        let mut state = state.lock();
        if !state.initialized {
            return;
        }
        if let Err(e) = save_setting_bool(&mut state.settings, "generate_stats", checked) {
            tracing::warn!("Failed to save generate_stats: {}", e);
        }
    });
}
```

In `populate_settings_ui`, add:
```rust
window.set_setting_generate_stats(config.generate_stats);
```

Note: `ClassicConfig` may not have a `generate_stats` field yet. Check `classic-config-core` -- if not, we need to add it there. If it already has `generate_stats` as a field, use it. If not, use `option-generate-stats` or equivalent. The scan callback in Task 4 should read this setting when starting a scan.

**Step 4: Add generate_stats to save_setting_bool in settings.rs**

Add to the match in `save_setting_bool`:
```rust
"generate_stats" => config.generate_stats = value,
```

If `ClassicConfig` doesn't have this field, add a comment noting it needs to be added to `classic-config-core` first.

**Step 5: Build and run tests**

Run: `cargo build -p classic-gui 2>&1`
Run: `cargo test -p classic-gui 2>&1`
Expected: Compiles and tests pass

**Step 6: Commit**

```bash
git add rust/ui-applications/classic-gui/
git commit -m "feat(gui): move Generate Statistics to Settings > General"
```

---

### Task 6: Debug and Fix Results Viewer Missing Sections

Investigation + fix for FormID, Plugin-related Errors, Mods with Solutions, and Named Records not showing.

**Files:**
- Modify: `rust/ui-applications/classic-gui/src/markdown.rs`
- Reference: `Crash Logs/crash-2025-08-25-08-22-24-AUTOSCAN.md` (has all sections)

**Step 1: Write a test using real report content**

In `markdown.rs`, add a test that uses content representative of a full report. Use the actual content from `crash-2025-08-25-08-22-24-AUTOSCAN.md` (which contains all the missing sections: "Checking for Plugin-related Errors", "Checking for Named Records", "Checking For Mods That HAVE SOLUTIONS").

```rust
#[test]
fn test_full_report_all_sections_present() {
    let report = r#"# crash-2025-08-25-08-22-24.log
**AUTOSCAN REPORT GENERATED BY CLASSIC v8.2.0**

---

### Error Information

**Main Error:** Unhandled exception at 0x7FF68919FECE

---

### Checking for Known Crash Messages, Errors and Suspects

- **Checking for NPC Pathing Crash....... SUSPECT FOUND! > Severity : 3**

-----
* **ONE OR MORE SUSPECTS DETECTED!** *

---

### Checking for Settings-related Issues

-----
### Checking For Mods That HAVE SOLUTIONS

**[!] FOUND : [74] Looks Menu Customization Compendium**

    - If you are getting broken hair colors, install this mod.
    -----
### Checking for Important Mods

### Checking for Plugin-related Errors

* COULDN'T FIND ANY PLUGIN SUSPECTS *

### Checking for Named Records

- (void* -> x-cell-og.dll+000BACC) | 2

---

### End of Report

Generated by CLASSIC v8.2.0"#;

    let blocks = parse_markdown(report);

    // Check that all section headers are present
    let headings: Vec<&str> = blocks
        .iter()
        .filter(|b| b.block_type == BLOCK_HEADING)
        .map(|b| b.text.as_str())
        .collect();

    assert!(headings.contains(&"Error Information"), "Missing Error Information heading");
    assert!(headings.contains(&"Checking for Known Crash Messages, Errors and Suspects"), "Missing Suspects heading");
    assert!(headings.contains(&"Checking for Settings-related Issues"), "Missing Settings heading");
    assert!(headings.iter().any(|h| h.contains("HAVE SOLUTIONS")), "Missing HAVE SOLUTIONS heading");
    assert!(headings.contains(&"Checking for Plugin-related Errors"), "Missing Plugin Errors heading");
    assert!(headings.contains(&"Checking for Named Records"), "Missing Named Records heading");
    assert!(headings.contains(&"End of Report"), "Missing End of Report heading");
}
```

**Step 2: Run the test**

Run: `cargo test -p classic-gui test_full_report_all_sections_present -- --nocapture 2>&1`
Expected: This test will likely FAIL -- revealing which sections are dropped. Examine the output to identify the root cause.

**Step 3: Diagnose the issue**

The most likely cause based on code analysis: the report lines from the Rust orchestrator each contain embedded `\n\n` (double newlines). When joined with `\n` by `get_report_content`, this creates `\n\n\n` sequences. This shouldn't break pulldown-cmark, but might create unexpected paragraph boundaries.

Another possibility: the `-----` (5-dash) separator used between items. In CommonMark, `-----` IS a thematic break (horizontal rule), same as `---`. But the `-----` lines within indented content (like `    -----`) might cause the parser to break out of a list context, losing subsequent content.

Also check: `* NOTICE *` and `* text *` patterns -- single asterisks can be parsed as emphasis markers rather than list items.

Based on what the test reveals, apply the appropriate fix. Common fixes might include:
- Normalizing `\n\n\n+` to `\n\n` before parsing
- Handling additional pulldown-cmark event types in the match (e.g., `Link`, `Image`)
- Fixing how the orchestrator formats its report lines

**Step 4: Implement the fix**

Apply the fix based on the diagnosis. If the issue is in `parse_markdown`, modify the parser. If the issue is in the report line format, the fix belongs in `get_report_content` (normalizing the joined string before parsing).

A likely quick fix -- add normalization before parsing in `get_report_content` or at the call site in `update_report_blocks`:

```rust
// In update_report_blocks or before calling parse_markdown:
// Normalize excessive newlines that can confuse the block renderer
let normalized = content.replace("\n\n\n", "\n\n");
let blocks = parse_markdown(&normalized);
```

**Step 5: Verify the fix**

Run: `cargo test -p classic-gui test_full_report_all_sections_present -- --nocapture 2>&1`
Expected: PASS -- all section headings are found in the parsed blocks

**Step 6: Run full test suite**

Run: `cargo test -p classic-gui 2>&1`
Expected: All tests pass

**Step 7: Commit**

```bash
git add rust/ui-applications/classic-gui/src/
git commit -m "fix(gui): results viewer now shows all report sections"
```

---

### Task 7: Final Build Verification and Cleanup

Verify everything works together.

**Step 1: Full workspace build**

Run: `cargo build -p classic-gui 2>&1`
Expected: Clean compile

**Step 2: Full test suite**

Run: `cargo test -p classic-gui 2>&1`
Expected: All tests pass

**Step 3: Check for dead code warnings**

Look at the build output for `unused` warnings. If any `option-scan-logs`, `option-scan-game`, `update-source`, or `scan-custom` references remain, clean them up.

**Step 4: Run cargo clippy**

Run: `cargo clippy -p classic-gui 2>&1`
Expected: No new warnings introduced by our changes

**Step 5: Commit any cleanup**

```bash
git add rust/ui-applications/classic-gui/
git commit -m "chore(gui): cleanup dead code from GUI simplification"
```
