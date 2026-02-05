# Phase 20: Core UI Layout - Research

**Researched:** 2026-02-05
**Domain:** Slint GUI layout, theming, and window state persistence
**Confidence:** HIGH

## Summary

This phase builds upon the Phase 19 foundation to create the production-ready main window shell with proper theming, tabbed navigation, and state persistence. The research confirms that Slint 1.15.0 provides all necessary features: `fluent-dark` style for forced dark mode, `TabWidget` with `current-index` for tab management, and `Window` properties with Rust API for state persistence.

The key challenge is implementing per-tab window state persistence, which Slint does not provide built-in. This requires a custom solution using the `directories` crate for cross-platform config storage and serde for serialization. The existing Python implementation in `WindowGeometryManager` provides the exact pattern to replicate: save/restore geometry on tab change, handle maximized state separately, and persist on application exit.

For file dialogs (path inputs with Browse buttons), the `rfd` crate provides the async-native solution that integrates cleanly with Slint and Tokio.

**Primary recommendation:** Force `fluent-dark` style at build time via `slint_build::compile_with_config()`, implement state persistence using `directories` + `serde_json`, and use `rfd::AsyncFileDialog` for folder browsing.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slint | 1.15.0 | GUI framework | Already in workspace, Rust-native |
| directories | 6.0.0 | Config file paths | Already in workspace deps, cross-platform |
| serde_json | 1.0 | State serialization | Already in workspace, simple JSON I/O |
| rfd | 0.15+ | File dialogs | De facto standard for Rust async file dialogs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tokio-util | 0.7 | CancellationToken | Already available for cancellable dialogs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rfd | native-dialog | native-dialog is sync-only; rfd has async API that fits Tokio pattern |
| serde_json | toml/yaml | JSON is simpler, no new dependencies needed |

**Installation:**
```toml
# In classic-gui/Cargo.toml - additions to existing deps
[dependencies]
rfd = "0.15"
serde = { workspace = true }
serde_json = { workspace = true }
directories = { workspace = true }
```

## Architecture Patterns

### Recommended Project Structure
```
rust/ui-applications/classic-gui/
  src/
    main.rs              # Entry point (existing)
    lib.rs               # Re-exports (existing)
    worker.rs            # Scan worker (existing)
    state.rs             # NEW: Window state persistence
    dialogs.rs           # NEW: File dialog wrappers
    ui_extensions.rs     # NEW: MainWindow extensions
  ui/
    main.slint           # UPDATE: Full layout with tabs
    widgets/
      path_input.slint   # NEW: Reusable path input component
      styled_group.slint # NEW: Styled GroupBox wrapper
  build.rs               # UPDATE: Force fluent-dark style
```

### Pattern 1: Force fluent-dark at Build Time
**What:** Configure Slint compiler to use fluent-dark style regardless of system settings
**When to use:** When dark-only mode is required (per CONTEXT.md decision)
**Example:**
```rust
// Source: Slint documentation - style selection
// build.rs
fn main() {
    let config = slint_build::CompilerConfiguration::new()
        .with_style("fluent-dark".into());
    slint_build::compile_with_config("ui/main.slint", config)
        .expect("Slint compilation failed");
}
```

### Pattern 2: Palette.color-scheme Override
**What:** Explicitly set dark color scheme in Slint code as backup
**When to use:** Additional guarantee for dark mode
**Example:**
```slint
// Source: Slint Palette documentation
import { Palette } from "std-widgets.slint";

export component MainWindow inherits Window {
    // Force dark color scheme
    init => {
        Palette.color-scheme = ColorScheme.dark;
    }
}
```

### Pattern 3: Tab Index Binding for State Tracking
**What:** Bind TabWidget current-index to track active tab
**When to use:** When tab changes need to trigger geometry save/restore
**Example:**
```slint
// Source: Slint TabWidget documentation
export component MainWindow inherits Window {
    in-out property <int> active-tab-index: 0;

    callback tab-changed(int);

    TabWidget {
        current-index <=> root.active-tab-index;

        // Notify Rust when tab changes
        property <int> _tab-watcher: root.active-tab-index;
        changed _tab-watcher => { root.tab-changed(root.active-tab-index); }
    }
}
```

### Pattern 4: Window State Persistence
**What:** Save/restore window position, size, and per-tab geometry
**When to use:** Per CONTEXT.md requirement for per-tab state persistence
**Example:**
```rust
// Source: directories crate + existing Python WindowGeometryManager pattern
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Default)]
struct TabGeometry {
    width: Option<i32>,
    height: Option<i32>,
    maximized: bool,
}

#[derive(Serialize, Deserialize, Default)]
struct WindowState {
    // Per-tab geometry
    main_options: TabGeometry,
    results: TabGeometry,
    settings: TabGeometry,
    // Global position
    position_x: Option<i32>,
    position_y: Option<i32>,
    last_tab: i32,
}

fn get_config_path() -> Option<PathBuf> {
    ProjectDirs::from("com", "CLASSIC", "CLASSIC-GUI")
        .map(|dirs| dirs.config_dir().join("window_state.json"))
}

fn save_state(state: &WindowState) -> Result<(), std::io::Error> {
    if let Some(path) = get_config_path() {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(state)?;
        fs::write(path, json)?;
    }
    Ok(())
}

fn load_state() -> WindowState {
    get_config_path()
        .and_then(|path| fs::read_to_string(path).ok())
        .and_then(|json| serde_json::from_str(&json).ok())
        .unwrap_or_default()
}
```

### Pattern 5: Async File Dialog with Slint
**What:** Open native folder picker without blocking UI
**When to use:** Path input "Browse" button clicks
**Example:**
```rust
// Source: rfd crate documentation + Slint async patterns
use rfd::AsyncFileDialog;
use slint::Weak;

async fn pick_folder(
    window_weak: Weak<MainWindow>,
    initial_dir: Option<PathBuf>,
) -> Option<PathBuf> {
    let mut dialog = AsyncFileDialog::new()
        .set_title("Select Folder");

    if let Some(dir) = initial_dir {
        dialog = dialog.set_directory(dir);
    }

    dialog.pick_folder().await.map(|handle| handle.path().to_path_buf())
}

// In callback setup:
window.on_browse_logs_folder({
    let window_weak = window.as_weak();
    move || {
        let window_weak = window_weak.clone();
        classic_shared_core::get_runtime().spawn(async move {
            if let Some(path) = pick_folder(window_weak.clone(), None).await {
                window_weak.upgrade_in_event_loop(move |w| {
                    w.set_logs_path(path.to_string_lossy().into());
                }).ok();
            }
        });
    }
});
```

### Pattern 6: Reusable Path Input Component
**What:** Custom component combining LineEdit + Browse button
**When to use:** All folder/file path inputs
**Example:**
```slint
// Source: Slint custom components documentation
// ui/widgets/path_input.slint
import { LineEdit, Button, HorizontalBox } from "std-widgets.slint";

export component PathInput inherits HorizontalBox {
    in-out property <string> path;
    in property <string> placeholder: "Enter path...";
    in property <bool> enabled: true;

    callback browse-clicked();
    callback path-edited(string);

    spacing: 5px;

    LineEdit {
        horizontal-stretch: 1;
        text <=> root.path;
        placeholder-text: root.placeholder;
        enabled: root.enabled;
        edited(text) => { root.path-edited(text); }
    }

    Button {
        text: "Browse";
        enabled: root.enabled;
        clicked => { root.browse-clicked(); }
    }
}
```

### Anti-Patterns to Avoid
- **Setting style at runtime:** Slint style is compile-time only. Don't try `Palette.color-scheme` to change styles; it only affects color variants within the chosen style.
- **Blocking UI for file dialogs:** Don't use sync FileDialog API. Use AsyncFileDialog with spawn.
- **Saving geometry on every resize:** Too frequent. Save on tab change and window close only.
- **Hardcoded paths for config:** Use `directories` crate for cross-platform paths.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config file location | `%APPDATA%` hardcode | `directories::ProjectDirs` | Cross-platform, follows OS conventions |
| File dialogs | Custom modal | `rfd::AsyncFileDialog` | Native OS dialogs, async-compatible |
| State serialization | Manual file format | `serde_json` | Already in workspace, reliable |
| Dark theme colors | Manual hex values | `Palette` properties | Theme-aware, consistent with fluent-dark |

**Key insight:** Per-tab geometry persistence requires custom code (Slint has no built-in), but all the building blocks (Window API, directories, serde) are standard Rust crates.

## Common Pitfalls

### Pitfall 1: Style Not Applied
**What goes wrong:** Window renders with system-default light style instead of dark
**Why it happens:** `SLINT_STYLE` environment variable not set, or using wrong `compile()` call
**How to avoid:** Use `slint_build::compile_with_config()` with explicit style in build.rs
**Warning signs:** Light backgrounds, blue accent instead of dark theme colors

### Pitfall 2: Tab Change Events Fire on Init
**What goes wrong:** Geometry save/restore triggers during window creation, corrupting state
**Why it happens:** TabWidget sets initial index, triggering change callback
**How to avoid:** Use a `geometry_initialized` flag, skip save until setup complete (see Python pattern)
**Warning signs:** Window size jumps on startup, wrong tab geometry on first launch

### Pitfall 3: Window Position on Multi-Monitor
**What goes wrong:** Window opens off-screen after monitor configuration change
**Why it happens:** Saved position is on a now-disconnected monitor
**How to avoid:** Validate position against current screen bounds before applying; use Slint's Window API
**Warning signs:** Window invisible on launch, requires Alt+Tab or taskbar click to find

### Pitfall 4: File Dialog Blocks Event Loop
**What goes wrong:** UI freezes while file dialog is open
**Why it happens:** Using sync `FileDialog` instead of `AsyncFileDialog`
**How to avoid:** Always use `AsyncFileDialog` with spawn on Tokio runtime
**Warning signs:** Progress animations stop, window becomes unresponsive

### Pitfall 5: Minimum Size Not Enforced
**What goes wrong:** User can resize window smaller than content, causing clipping
**Why it happens:** `min-width`/`min-height` not set on Window or overridden by layout
**How to avoid:** Set explicit min-width/min-height on Window component
**Warning signs:** Controls overlap when window is small, scroll bars appear unexpectedly

### Pitfall 6: Maximized State Loss
**What goes wrong:** Window loses maximized state on tab switch
**Why it happens:** Resizing maximized window un-maximizes it in most window managers
**How to avoid:** Save maximized state separately, restore state before resize (see Python pattern)
**Warning signs:** Maximized window un-maximizes when switching tabs

## Code Examples

Verified patterns from official sources:

### Complete build.rs with Style Configuration
```rust
// Source: Slint documentation - CompilerConfiguration
// build.rs
fn main() {
    let config = slint_build::CompilerConfiguration::new()
        .with_style("fluent-dark".into());

    slint_build::compile_with_config("ui/main.slint", config)
        .expect("Slint compilation failed");
}
```

### Window Properties for Layout
```slint
// Source: Slint Window documentation
export component MainWindow inherits Window {
    title: "Crash Log Auto Scanner and Setup Integrity Checker v9.0.0";
    icon: @image-url("../assets/CLASSIC.ico");

    // Initial size (800x600 per CONTEXT.md)
    preferred-width: 800px;
    preferred-height: 600px;

    // Minimum floor (640x480 recommended)
    min-width: 640px;
    min-height: 480px;

    // Background inherits from fluent-dark Palette automatically
}
```

### Three-Tab Layout Structure
```slint
// Source: Slint TabWidget documentation
import { TabWidget, VerticalBox, Button, GroupBox, CheckBox } from "std-widgets.slint";
import { PathInput } from "widgets/path_input.slint";

export component MainWindow inherits Window {
    // Tab tracking
    in-out property <int> active-tab-index: 0;
    callback tab-changed(int);

    VerticalBox {
        padding: 10px;

        TabWidget {
            current-index <=> root.active-tab-index;

            Tab {
                title: "Main Options";
                // Content placeholder
            }
            Tab {
                title: "Results";
                // Content placeholder
            }
            Tab {
                title: "Settings";
                // Content placeholder
            }
        }

        // Progress bar area at bottom
    }
}
```

### Button with Primary Accent
```slint
// Source: Slint Button documentation
Button {
    text: "Scan Crash Logs";
    primary: true;  // Uses accent color (#0078D4 in fluent)
    clicked => { /* action */ }
}
```

### Window State Manager
```rust
// Source: directories + serde crates, Python WindowGeometryManager pattern
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use slint::{PhysicalPosition, PhysicalSize};

pub struct WindowStateManager {
    state: WindowState,
    config_path: Option<std::path::PathBuf>,
    initialized: bool,
}

impl WindowStateManager {
    pub fn new() -> Self {
        let config_path = ProjectDirs::from("com", "CLASSIC", "CLASSIC-GUI")
            .map(|dirs| dirs.config_dir().join("window_state.json"));

        let state = config_path
            .as_ref()
            .and_then(|p| std::fs::read_to_string(p).ok())
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default();

        Self {
            state,
            config_path,
            initialized: false,
        }
    }

    pub fn on_tab_changed(&mut self, window: &slint::Window, old_tab: i32, new_tab: i32) {
        if !self.initialized {
            self.initialized = true;
            return; // Skip save on initialization
        }

        // Save old tab geometry
        self.save_tab_geometry(window, old_tab);

        // Restore new tab geometry
        self.restore_tab_geometry(window, new_tab);

        // Update last tab
        self.state.last_tab = new_tab;
    }

    pub fn save(&self) {
        if let Some(ref path) = self.config_path {
            if let Some(parent) = path.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            if let Ok(json) = serde_json::to_string_pretty(&self.state) {
                let _ = std::fs::write(path, json);
            }
        }
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SLINT_STYLE env var | CompilerConfiguration::with_style() | Slint 1.4+ | More reliable compile-time style |
| Palette.color-scheme = dark | fluent-dark style variant | Slint 1.3+ | Full dark theme, not just color swap |
| Sync file dialogs | AsyncFileDialog | rfd 0.12+ | Non-blocking UI |

**Deprecated/outdated:**
- Setting `SLINT_STYLE` at runtime: Was never supported, compile-time only
- Using `sixtyfps` crate name: Renamed to `slint` in 0.2.0

## Open Questions

Things that couldn't be fully resolved:

1. **Per-tab minimum size enforcement**
   - What we know: Can set min-width/min-height on Window
   - What's unclear: Whether changing min-size on tab switch causes visual flicker
   - Recommendation: Test during implementation; may need to set to largest minimum across all tabs

2. **Accent color customization (#0078D4)**
   - What we know: fluent-dark has built-in accent color, Palette exposes accent-background
   - What's unclear: Whether accent color matches exactly #0078D4 or is slightly different
   - Recommendation: Use Palette.accent-background for consistency; accept any minor color variance

3. **Window position persistence on Wayland**
   - What we know: Slint docs mention position API "not available on some windowing systems, such as Wayland"
   - What's unclear: Whether set_position() silently fails or errors
   - Recommendation: Gracefully handle position restore failure; document as known limitation

## Sources

### Primary (HIGH confidence)
- [Slint Window documentation](https://docs.slint.dev/latest/docs/slint/reference/window/window/) - Window properties and API
- [Slint Widget Styles](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/style/) - fluent-dark style selection
- [Slint Palette](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/globals/palette/) - Color scheme properties
- [slint::Window Rust API](https://docs.rs/slint/latest/slint/struct.Window.html) - position/size methods
- [rfd AsyncFileDialog](https://docs.rs/rfd/latest/rfd/struct.AsyncFileDialog.html) - Async file dialog API
- [directories ProjectDirs](https://docs.rs/directories/latest/directories/struct.ProjectDirs.html) - Config path resolution
- Existing Python `WindowGeometryManager` in codebase - Per-tab geometry pattern

### Secondary (MEDIUM confidence)
- [Slint TabWidget documentation](https://releases.slint.dev/1.5.1/docs/slint/src/language/widgets/tabwidget) - current-index property
- [Slint Button documentation](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/basic-widgets/button/) - primary property
- [Slint file dialog discussion #3015](https://github.com/slint-ui/slint/discussions/3015) - Community patterns for file dialogs

### Tertiary (LOW confidence)
- None - all critical claims verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all crates already in workspace or well-documented standard choices
- Architecture: HIGH - patterns verified in Slint docs and existing Python implementation
- Pitfalls: HIGH - documented in official sources and derived from Python implementation experience

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (Slint 1.15 is current; patterns are stable)
