# Phase 24: Settings Dialog - Research

**Researched:** 2026-02-05
**Domain:** Slint GUI settings UI, YAML configuration persistence, Rust settings management
**Confidence:** HIGH

## Summary

This phase implements the Settings tab UI within the existing Slint GUI, connecting it to YAML-based settings persistence. The GUI currently has a placeholder Settings tab (3rd tab) that needs to be populated with sub-tabbed settings controls (General, Scanning, Paths) using live save-on-change semantics.

The existing codebase provides strong foundations: `classic-config-core` has a complete `ClassicConfig` struct with `load_from_yaml`/`save_to_yaml` methods, `classic-yaml-core` provides atomic YAML file operations, and the Slint widget library includes all needed UI controls (ComboBox, Switch, CheckBox, LineEdit, TabWidget). The main gap is that the GUI currently has zero settings integration -- it only persists window geometry via a separate JSON state file.

**Primary recommendation:** Use `ClassicConfig` from `classic-config-core` as the settings model (it already maps all needed fields), add `classic-yaml-core` for individual setting updates, implement sub-tabs using a nested TabWidget within the Settings tab, and use Slint's `changed` callback on `has-focus` for save-on-focus-loss on path LineEdits.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Settings live directly in the existing Settings tab (third tab) -- NOT a popup dialog window
- The Settings tab contains sub-tabs: General, Scanning, Paths
- No OK/Cancel buttons -- settings save on change (live save pattern)
- A single "Reset to Defaults" button at the bottom of the Settings tab, below the sub-tabs
- Reset to Defaults requires confirmation before executing
- General tab: Game Version dropdown (Auto, Original, NextGen, VR), Update Check toggle, Update Source dropdown (GitHub, Both), FCX Mode toggle
- Scanning tab: Simplify Logs toggle, Show FormID Values toggle, Move Unsolved Logs toggle, Auto Switch After Scan toggle
- Paths tab: INI Folder Path, Mods Folder Path, Custom Scan Path (all with text input + browse button)
- All path browse buttons use rfd native folder dialogs
- Excluded settings: Disable CLI Progress, Audio Notifications, Show Statistics, local_only/offline_data
- "Auto" game version runs detection immediately and shows detected version as hint
- Changing game version does NOT reset folder paths
- Legacy VR Mode migration: if YAML has VR Mode=true and no Game Version, auto-migrate to Game Version=VR on first load
- Live save: Dropdowns save on selection change, checkboxes/toggles save on click, paths save after browse or on focus loss/Enter
- Path validation: reject and show error if directory doesn't exist; only save valid directories
- Reset to Defaults: single button, resets ALL settings across all sub-tabs, requires confirmation

### Claude's Discretion
- Sub-tab visual style (standard Slint TabWidget or custom)
- Settings label placement and spacing
- Error display style for invalid paths (inline error text, colored border, or both)
- Auto-detection hint display format for "Auto" game version
- Confirmation prompt style for Reset to Defaults (modal overlay or inline)
- Default values for each setting

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core (already in workspace)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slint | 1.15.0 | UI framework | Already used for all GUI components |
| classic-config-core | 8.2.0+ | Settings model (ClassicConfig struct) | Has load/save YAML, all settings fields |
| classic-yaml-core | (workspace) | Atomic YAML read/write, get/set_setting | Thread-safe, caching, atomic writes |
| rfd | 0.15 | Native folder dialogs | Already used in GUI for browse callbacks |
| directories | 6.0.0 | Config directory resolution | Already a dependency |

### New Dependencies Needed

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| classic-config-core | (workspace) | Must be added to classic-gui Cargo.toml | Settings load/save |
| classic-yaml-core | (workspace) | Must be added to classic-gui Cargo.toml | Individual setting writes, atomic saves |

### No Alternatives Needed
All required libraries are already in the workspace. No new external crates required.

**Installation (Cargo.toml additions):**
```toml
classic-config-core = { path = "../../business-logic/classic-config-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
```

## Architecture Patterns

### Recommended Project Structure
```
rust/ui-applications/classic-gui/
├── ui/
│   ├── main.slint                      # MainWindow - Settings tab updated
│   └── widgets/
│       ├── types.slint                 # Add settings-related shared structs
│       ├── settings_general.slint      # NEW: General sub-tab component
│       ├── settings_scanning.slint     # NEW: Scanning sub-tab component
│       ├── settings_paths.slint        # NEW: Paths sub-tab component
│       └── path_input.slint            # EXISTING: Reuse for path fields
├── src/
│   ├── main.rs                         # Add settings callbacks setup
│   ├── settings.rs                     # NEW: Settings load/save logic
│   ├── lib.rs                          # Export settings module
│   └── ...existing files...
```

### Pattern 1: Nested TabWidget for Sub-Tabs
**What:** Place a TabWidget inside the Settings Tab to create General/Scanning/Paths sub-tabs
**When to use:** For the 3-section settings layout
**Confidence:** HIGH -- Slint TabWidget documentation does not prohibit nesting, and the project already uses TabWidget for the outer 3-tab layout.

```slint
// In main.slint, inside the Settings Tab:
Tab {
    title: "Settings";
    VerticalBox {
        padding: 16px;
        spacing: 12px;

        TabWidget {
            Tab {
                title: "General";
                SettingsGeneral {
                    // properties bound to root settings properties
                }
            }
            Tab {
                title: "Scanning";
                SettingsScanning { }
            }
            Tab {
                title: "Paths";
                SettingsPaths { }
            }
        }

        // Reset button below the sub-tabs
        HorizontalBox {
            alignment: center;
            Button {
                text: "Reset to Defaults";
                clicked => { root.reset-settings-requested(); }
            }
        }
    }
}
```

### Pattern 2: Live Save-on-Change via Callbacks
**What:** Each UI control fires a callback to Rust on change; Rust immediately persists to YAML
**When to use:** All settings controls (mandatory per CONTEXT.md)
**Example flow:**

```
User toggles Switch -> Slint `toggled()` callback fires
  -> Rust callback handler:
     1. Update in-memory ClassicConfig
     2. Write to YAML file via classic-yaml-core atomic save
     3. (Optional) Update Slint property if derived state changed
```

```rust
// Rust callback handler pattern
window.on_setting_fcx_mode_changed(move |checked| {
    let mut state = state.lock();
    if !state.initialized { return; }
    state.settings.fcx_mode = checked;
    if let Err(e) = save_setting(&state.settings_path, "fcx_mode", Yaml::Boolean(checked)) {
        eprintln!("Failed to save setting: {}", e);
    }
});
```

### Pattern 3: Path Validation with Error Feedback
**What:** Validate path exists before saving; show inline error if invalid
**When to use:** All three path settings (INI, Mods, Custom Scan)

```slint
// Path input with validation error
component SettingsPathInput inherits VerticalBox {
    in-out property <string> path;
    in-out property <string> error-message: "";
    in-out property <bool> has-error: false;
    in-out property <string> label;
    callback browse-clicked();
    callback path-accepted(string);

    HorizontalBox {
        spacing: 8px;
        Text { text: root.label; min-width: 120px; vertical-alignment: center; }
        LineEdit {
            text <=> root.path;
            horizontal-stretch: 1;
            accepted(text) => { root.path-accepted(text); }
            // Save on focus loss using changed callback
            changed has-focus => {
                if (!self.has-focus) {
                    root.path-accepted(self.text);
                }
            }
        }
        Button {
            text: "Browse...";
            clicked => { root.browse-clicked(); }
        }
    }
    if root.has-error : Text {
        text: root.error-message;
        color: #ff6b6b;
        font-size: 11px;
    }
}
```

### Pattern 4: Game Version Auto-Detection with Hint
**What:** When "Auto" is selected in the Game Version dropdown, immediately run detection and display result as hint text
**When to use:** Game Version dropdown specifically

```slint
// In General settings
HorizontalBox {
    spacing: 8px;
    Text { text: "Game Version:"; min-width: 120px; vertical-alignment: center; }
    ComboBox {
        model: ["Auto", "Original", "NextGen", "VR"];
        current-index <=> root.game-version-index;
        selected(value) => { root.game-version-selected(self.current-index); }
    }
    // Hint text shown only when Auto is selected
    if root.game-version-index == 0 : Text {
        text: root.auto-detected-hint;  // e.g., "(detected: NextGen)"
        color: #888888;
        font-size: 11px;
        vertical-alignment: center;
    }
}
```

### Pattern 5: Confirmation Dialog for Reset
**What:** Overlay or inline confirmation before resetting all settings
**Recommendation:** Use an inline confirmation pattern (show/hide confirmation text + button pair) rather than a modal popup, since Slint popup support is limited and inline confirmation is simpler.

```slint
// Reset to Defaults with inline confirmation
HorizontalBox {
    alignment: center;
    spacing: 8px;

    if !root.reset-confirm-visible : Button {
        text: "Reset to Defaults";
        clicked => { root.reset-confirm-visible = true; }
    }
    if root.reset-confirm-visible : HorizontalBox {
        spacing: 8px;
        Text {
            text: "Reset ALL settings to defaults?";
            color: #ff6b6b;
            vertical-alignment: center;
        }
        Button {
            text: "Yes, Reset";
            clicked => {
                root.confirm-reset();
                root.reset-confirm-visible = false;
            }
        }
        Button {
            text: "Cancel";
            clicked => { root.reset-confirm-visible = false; }
        }
    }
}
```

### Anti-Patterns to Avoid
- **Do NOT use OK/Cancel pattern** -- user explicitly dislikes it; settings save immediately
- **Do NOT save settings during initialization** -- use the existing `initialized` flag pattern from `AppState` to gate saves
- **Do NOT read the Python `CLASSIC Settings.yaml` format** -- the Rust GUI uses `CLASSIC_Settings.yaml` (snake_case keys) at a different path
- **Do NOT create a new Tokio runtime** -- ONE RUNTIME RULE via `classic_shared_core::get_runtime()`
- **Do NOT modify the Python settings file** -- the Rust GUI has its own settings file

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML read/write | Custom YAML serialization | `classic-yaml-core` `YamlOperations` | Atomic writes, caching, tested |
| Settings model | New settings struct | `classic-config-core` `ClassicConfig` | Already has all fields, load/save |
| File dialogs | Custom file picker | `rfd::AsyncFileDialog` via existing `browse_folder()` | Already implemented in `dialogs.rs` |
| Config directory | `std::env` manual lookup | `directories::ProjectDirs` | Already used in `state.rs` |
| Path validation | Manual `std::fs::metadata` | `std::path::Path::is_dir()` | Simpler, sufficient |

**Key insight:** The `ClassicConfig` struct in `classic-config-core` already maps most settings (fcx_mode, show_formid_values, simplify_logs, move_unsolved_logs, update_check, auto_switch_to_results, paths). It just needs to be extended with `game_version` (string) and `update_source` (string) fields which it currently lacks.

## Common Pitfalls

### Pitfall 1: Initialization Flag Not Set During Settings Load
**What goes wrong:** Settings load from YAML triggers `changed` callbacks on Slint properties, which fire save callbacks, creating a load-save-load loop.
**Why it happens:** Live save pattern means any property change triggers a save.
**How to avoid:** Use the existing `initialized` flag in `AppState`. Set `initialized = false` before loading settings into UI, set `initialized = true` after all properties are populated.
**Warning signs:** Settings file gets overwritten with defaults on startup.

### Pitfall 2: Slint Two-Way Binding Breaks After Programmatic Set
**What goes wrong:** Setting a Slint property from Rust can break two-way bindings (`<=>`).
**Why it happens:** Slint binding issue #8102 -- programmatic writes can break binding chains.
**How to avoid:** Use `in-out` properties with explicit callbacks rather than relying on two-way bindings for settings that are both loaded and saved. Use one-way binding (`<-`) for display-only, explicit callbacks for save triggers.
**Warning signs:** UI shows stale values after programmatic update.

### Pitfall 3: YAML Key Name Mismatch Between Python and Rust
**What goes wrong:** Reading/writing wrong keys in the YAML file.
**Why it happens:** Python uses `"CLASSIC_Settings.FCX Mode"` (space-separated under `CLASSIC_Settings:`), Rust uses `fcx_mode` (snake_case at root level). The files have different structures.
**How to avoid:** The Rust GUI MUST use its own `CLASSIC_Settings.yaml` (already at `rust/CLASSIC_Settings.yaml`) with the `ClassicConfig` format (snake_case keys, no nesting under CLASSIC_Settings). Do NOT try to read the Python format.
**Warning signs:** Settings appear as defaults even though YAML file has values.

### Pitfall 4: ComboBox current-index vs current-value Confusion
**What goes wrong:** Saving the display string instead of the internal value for Game Version.
**Why it happens:** ComboBox `selected(string)` callback returns the display text, not an index. Need to map display values to storage values.
**How to avoid:** Use `current-index` for selection tracking; maintain a mapping array in Rust (index 0 = "auto", 1 = "Original", etc.).
**Warning signs:** YAML contains "Auto" instead of "auto", or "NextGen" where the code expects a different casing.

### Pitfall 5: Path Save Timing with LineEdit
**What goes wrong:** Path saves on every keystroke via `edited` callback, causing excessive I/O.
**Why it happens:** LineEdit `edited(string)` fires on every character change.
**How to avoid:** Save paths only on: (a) `accepted()` callback (Enter key), (b) `changed has-focus` when focus is lost, (c) after successful browse dialog selection. Do NOT use `edited()` for save triggering.
**Warning signs:** YAML file constantly being written during typing.

### Pitfall 6: ClassicConfig Missing Game Version and Update Source Fields
**What goes wrong:** Cannot load/save Game Version or Update Source settings.
**Why it happens:** The existing `ClassicConfig` struct has `vr_mode: bool` but no `game_version: String` or `update_source: String` field.
**How to avoid:** Extend `ClassicConfig` with `game_version` and `update_source` fields before implementing the UI. Alternatively, use `classic-yaml-core` `YamlOperations::set_setting` for direct YAML key access without modifying ClassicConfig.
**Warning signs:** Compiler errors when trying to access game_version on ClassicConfig.

### Pitfall 7: Reset to Defaults Must Reload UI State
**What goes wrong:** YAML is reset but UI still shows old values.
**Why it happens:** Resetting the file doesn't automatically update Slint properties.
**How to avoid:** After writing defaults to YAML, explicitly re-populate all Slint properties from the new defaults. Use a single `load_settings_into_ui()` function called both at startup and after reset.
**Warning signs:** UI shows stale values after Reset to Defaults.

## Code Examples

### Loading Settings at Startup

```rust
// Source: Based on classic-config-core ClassicConfig::load_from_yaml
use classic_config_core::ClassicConfig;

fn load_settings(settings_path: &Path) -> ClassicConfig {
    // Try to load from YAML, fall back to defaults
    let rt = classic_shared_core::get_runtime();
    match rt.block_on(ClassicConfig::load_from_yaml(settings_path)) {
        Ok(config) => config,
        Err(e) => {
            eprintln!("Failed to load settings, using defaults: {}", e);
            ClassicConfig::default()
        }
    }
}

fn populate_settings_ui(window: &MainWindow, config: &ClassicConfig) {
    // Populate toggles
    window.set_setting_fcx_mode(config.fcx_mode);
    window.set_setting_simplify_logs(config.simplify_logs);
    window.set_setting_show_formid(config.show_formid_values);
    window.set_setting_move_unsolved(config.move_unsolved_logs);
    window.set_setting_update_check(config.update_check);
    window.set_setting_auto_switch(config.auto_switch_to_results);

    // Populate paths
    if let Some(ref path) = config.paths.ini_folder {
        window.set_setting_ini_path(path.to_string_lossy().to_string().into());
    }
    // ... etc
}
```

### Saving Individual Settings (Live Save Pattern)

```rust
// Source: Based on classic-yaml-core YamlOperations
use classic_yaml_core::YamlOperations;
use yaml_rust2::Yaml;

fn save_setting(settings_path: &Path, key: &str, value: Yaml) -> Result<(), Box<dyn std::error::Error>> {
    let ops = YamlOperations::new();

    // Load current YAML
    let yaml = ops.load_yaml_file(settings_path)?;

    // Update single setting
    let updated = ops.set_setting(&yaml, key, value)?;

    // Atomic save
    ops.save_yaml_file(settings_path, &updated)?;

    Ok(())
}

// Usage in callback:
// save_setting(&path, "fcx_mode", Yaml::Boolean(true));
// save_setting(&path, "paths.ini_folder", Yaml::String("/path/to/ini".into()));
```

### Path Validation

```rust
fn validate_path(path_str: &str) -> Result<PathBuf, String> {
    if path_str.trim().is_empty() {
        return Err("Path cannot be empty".to_string());
    }
    let path = PathBuf::from(path_str);
    if path.is_dir() {
        Ok(path)
    } else {
        Err(format!("Directory does not exist: {}", path_str))
    }
}
```

### Game Version Auto-Detection Stub
**Note:** No existing Rust function detects game version from the game executable. The version-registry-core has matching logic but no detection-from-filesystem function.

```rust
// Simplified approach: Check game EXE version if game_root path is set
// This is a stub -- actual implementation depends on what detection method is available
fn detect_game_version(game_root: &Path) -> String {
    // Look for Fallout4.exe and check its file version
    // Or check for known VR markers (Fallout4VR.exe)
    let vr_exe = game_root.join("Fallout4VR.exe");
    if vr_exe.exists() {
        return "VR".to_string();
    }

    // Check file size/version of Fallout4.exe for OG vs NG
    // This is a placeholder -- real detection logic needed
    "NextGen".to_string()  // Fallback
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OK/Cancel settings dialog | Live save-on-change | Phase 24 decision | No dialog buttons, immediate persistence |
| `VR Mode` boolean | `Game Version` dropdown | Phase 24 decision | Auto-migrate VR Mode on first load |
| Python YAML format | Rust YAML format | v9.0.0 GUI milestone | Different key names, different file |
| Slint experimental `changed` | Slint stable `changed` | Slint 1.8+ | Can use `changed has-focus` for focus-loss detection |

**Key version info:**
- Slint 1.15.0: TabWidget, ComboBox, Switch, CheckBox, LineEdit all available as standard widgets
- Slint `changed` property callback: Stable as of recent versions (documented without experimental flag)
- `classic-yaml-core`: Has atomic file writes (`save_yaml_file`), get/set by dot-notation key path
- `classic-config-core`: Has `ClassicConfig` with load/save, but missing `game_version` and `update_source` fields

## Open Questions

1. **Game Version Auto-Detection**
   - What we know: `classic-version-registry-core` has version matching (given a version, find the closest known). `classic-version-core` parses version strings. No function takes a game directory and returns "Original/NextGen/VR".
   - What's unclear: How to detect game version from filesystem. Python side likely checks the Fallout4.exe file version or uses registry keys.
   - Recommendation: For Phase 24, implement basic detection (check for Fallout4VR.exe for VR, otherwise default to "NextGen" or read from config). Full auto-detection can be enhanced later if needed. Alternatively, just display "Auto" without a detection hint if detection is complex.

2. **ClassicConfig Extension**
   - What we know: `ClassicConfig` has most fields but lacks `game_version: String` and `update_source: String`.
   - What's unclear: Whether to extend ClassicConfig or use raw YAML operations.
   - Recommendation: Extend `ClassicConfig` with the missing fields. It's the natural settings model and extending it is trivial. Update both `from_yaml` and `to_yaml` methods.

3. **Settings File Path**
   - What we know: The Rust settings file is at `rust/CLASSIC_Settings.yaml` relative to project root. `ClassicConfig::load_or_default()` looks for `CLASSIC_Settings.yaml` in the current directory.
   - What's unclear: Where the GUI executable runs from (current dir may vary).
   - Recommendation: Use `directories::ProjectDirs` for a stable config path (same as window state), OR look for the settings file relative to the executable path. The existing `state.rs` pattern using `ProjectDirs::from("com", "classic", "classic-gui")` provides a reliable approach.

4. **Nested TabWidget Support**
   - What we know: Slint documentation does not explicitly address nesting. The outer content of a Tab is a regular layout, so placing a TabWidget inside should work.
   - What's unclear: Whether fluent-dark theme renders nested tabs differently (smaller inner tabs vs outer tabs).
   - Recommendation: Test early. If nested TabWidget looks bad, fall back to a custom button-row sub-tab selector pattern.

## Sources

### Primary (HIGH confidence)
- Slint 1.15.0 TabWidget docs: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/tabwidget/
- Slint ComboBox docs: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/basic-widgets/combobox/
- Slint Switch docs: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/basic-widgets/switch/
- Slint CheckBox docs: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/basic-widgets/checkbox/
- Slint LineEdit docs: https://docs.slint.dev/latest/docs/slint/reference/std-widgets/views/lineedit/ (has `accepted()` for Enter, `has-focus` for focus tracking)
- Slint property `changed` callback: https://docs.slint.dev/latest/docs/slint/guide/language/coding/properties/
- Codebase: `classic-config-core` ClassicConfig at `rust/business-logic/classic-config-core/src/config.rs`
- Codebase: `classic-yaml-core` YamlOperations at `rust/business-logic/classic-yaml-core/src/lib.rs`
- Codebase: GUI main.slint at `rust/ui-applications/classic-gui/ui/main.slint`
- Codebase: GUI state.rs at `rust/ui-applications/classic-gui/src/state.rs`
- Codebase: GUI dialogs.rs at `rust/ui-applications/classic-gui/src/dialogs.rs`
- Codebase: Settings YAML format at `rust/CLASSIC_Settings.yaml`

### Secondary (MEDIUM confidence)
- Slint blog on property changed callbacks: https://slint.dev/blog/property-changed-callback
- Slint issue on `changed has-focus` for LineEdit: https://github.com/slint-ui/slint/issues/6331 (fixed)
- Slint binding breakage issue: https://github.com/slint-ui/slint/issues/8102

### Tertiary (LOW confidence)
- Nested TabWidget behavior: Not documented; inferred from Slint component composition model. Needs testing.
- Game version auto-detection: No existing Rust implementation found in codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries exist in workspace, APIs verified from source code
- Architecture: HIGH - Patterns derived from existing GUI code and verified Slint widget APIs
- Pitfalls: HIGH - Based on actual codebase analysis (initialization flag, key name differences, binding issues documented in Slint issues)
- Settings persistence: HIGH - ClassicConfig load/save verified from source, YamlOperations API verified
- Game version detection: LOW - No existing Rust implementation; stub approach needed
- Nested TabWidget: MEDIUM - Slint docs don't prohibit it but don't explicitly confirm it either

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (stable domain, Slint 1.15 unlikely to change within 30 days)
