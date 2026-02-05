# Feature Landscape: Slint GUI for CLASSIC

**Domain:** Desktop crash log analyzer GUI
**Researched:** 2026-02-05
**Overall Confidence:** MEDIUM

## Executive Summary

Slint provides a solid foundation for building the CLASSIC GUI with native Rust integration. The existing Qt GUI requires:
- Tabbed interface (4 tabs)
- Crash log scanning with progress feedback
- Markdown report viewing
- Report list with context menus
- Settings dialog with multiple tabs
- Dark theme styling

Slint covers most table stakes features but has notable gaps in markdown rendering and file dialogs that require external libraries or custom implementations.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

### TabWidget (Tabbed Interface)

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in `TabWidget` with `Tab` children |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Notes:** Native TabWidget with `current-index` property for programmatic tab switching. Maps directly to existing Qt tab structure (MAIN OPTIONS, FILE BACKUP, ARTICLES, RESULTS).

**Example:**
```slint
TabWidget {
    Tab { title: "MAIN OPTIONS"; /* content */ }
    Tab { title: "FILE BACKUP"; /* content */ }
    Tab { title: "ARTICLES"; /* content */ }
    Tab { title: "RESULTS"; /* content */ }
}
```

**Sources:**
- [TabWidget Documentation](https://releases.slint.dev/1.5.1/docs/slint/src/language/widgets/tabwidget)

---

### Buttons and Standard Controls

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in Button, CheckBox, ComboBox, SpinBox, LineEdit |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Current Qt Widgets to Map:**
- QPushButton -> Button
- QCheckBox -> CheckBox
- QComboBox -> ComboBox
- QSpinBox -> SpinBox
- QLineEdit -> LineEdit
- QTextEdit -> TextEdit

**Notes:** All standard widgets available with consistent styling across Fluent/Material themes.

**Sources:**
- [Widgets Documentation](https://releases.slint.dev/1.1.0/docs/slint/src/builtins/widgets)

---

### Progress Indicator

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in `ProgressIndicator` |
| **Complexity** | MEDIUM (async updates require specific patterns) |
| **Status** | AVAILABLE |

**Current Usage:** Qt progress dialogs during scanning operations.

**Slint Pattern for Async Updates:**
```rust
// Use upgrade_in_event_loop or channel communication
let weak = ui.as_weak();
tokio::spawn(async move {
    // ... scanning work ...
    weak.upgrade_in_event_loop(|ui| {
        ui.set_scan_progress(0.5); // 50%
    });
});
```

**Sources:**
- [ProgressIndicator Discussion](https://github.com/slint-ui/slint/discussions/8466)
- [Async Progress Updates](https://github.com/slint-ui/slint/discussions/4175)

---

### Dark Theme Styling

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in dark variants for Fluent and Material styles |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Options:**
- `fluent-dark` - Windows-style dark theme
- `material-dark` - Material Design dark theme

**Implementation:** Set at compile time or detect system preference automatically.

**Current Qt Style:** Custom CSS-like stylesheet (DARK_MODE constant) with colors:
- Background: #2b2b2b
- Widget: #3c3c3c
- Borders: #5c5c5c
- Text: #ffffff
- Accent: #0078d4

**Sources:**
- [Style Selection](https://releases.slint.dev/1.5.1/docs/slint/src/advanced/style)

---

### Report List (ListView)

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in `ListView` with virtualization |
| **Complexity** | MEDIUM |
| **Status** | AVAILABLE (with caveats) |

**Current Usage:** QListWidget showing scan reports (*-AUTOSCAN.md files).

**Slint Strengths:**
- Virtualization: Only visible items instantiated
- Handles 50M+ items with recent optimizations

**Slint Concerns:**
- Flickering reported with rapid content updates
- Destruction performance issues with large lists
- May need custom optimization for 10K+ items

**Pattern:**
```slint
ListView {
    for report in reports: Rectangle {
        Text { text: report.name; }
    }
}
```

**Sources:**
- [ListView Performance](https://github.com/slint-ui/slint/discussions/7986)
- [Layout Optimization PR](https://github.com/slint-ui/slint/pull/7408)

---

### Context Menu (Right-Click)

| Aspect | Details |
|--------|---------|
| **Slint Support** | `ContextMenuArea` with Menu/MenuItem (Slint 1.10+) |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Current Usage:** Right-click on reports list for View/Copy/Delete actions.

**Slint Implementation:**
```slint
ContextMenuArea {
    Menu {
        MenuItem { text: "View Report"; }
        MenuSeparator { }
        MenuItem { text: "Copy to Clipboard"; }
        MenuItem { text: "Delete"; }
    }
    // ... list content ...
}
```

**Sources:**
- [ContextMenuArea Docs](https://docs.slint.dev/latest/docs/slint/reference/window/contextmenuarea/)
- [Menu Support Blog](https://slint.dev/blog/making-slint-desktop-ready)

---

### Modal Dialogs

| Aspect | Details |
|--------|---------|
| **Slint Support** | `Dialog` element with StandardButton |
| **Complexity** | MEDIUM |
| **Status** | PARTIAL |

**Current Usage:**
- Settings dialog (modal, tabbed)
- About dialog
- Error dialogs with details
- Confirmation dialogs (delete report)

**Slint Limitations:**
- No built-in blocking modal behavior like Windows
- PopupWindow "steals mouse input"
- True modal parent/child relationship requires workarounds

**Pattern for Settings:**
```slint
export component SettingsDialog inherits Dialog {
    TabWidget {
        Tab { title: "General"; /* settings */ }
        Tab { title: "Scanning"; /* settings */ }
        Tab { title: "Paths"; /* settings */ }
    }
    StandardButton { kind: ok; }
    StandardButton { kind: cancel; }
}
```

**Sources:**
- [Dialog Documentation](https://docs.slint.dev/latest/docs/slint/reference/window/dialog/)
- [Modal Dialog Discussion](https://github.com/slint-ui/slint/discussions/6028)

---

### Clipboard Operations

| Aspect | Details |
|--------|---------|
| **Slint Support** | TextEdit/LineEdit have copy/paste; platform clipboard API |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Current Usage:** Copy report content to clipboard.

**Pattern:**
```rust
// Direct clipboard access from Rust
use arboard::Clipboard;
let mut clipboard = Clipboard::new()?;
clipboard.set_text(report_content)?;
```

**Notes:** TextEdit widgets support Ctrl+C/Ctrl+V natively. For programmatic access, use `arboard` crate.

**Sources:**
- [Clipboard in Slint](https://docs.rs/slint/latest/slint/platform/enum.Clipboard.html)
- [Clipboard Discussion](https://github.com/slint-ui/slint/discussions/2930)

---

### Window Geometry Persistence

| Aspect | Details |
|--------|---------|
| **Slint Support** | Window properties accessible from Rust |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Current Usage:** Save/restore window size per tab.

**Pattern:** Store window dimensions in settings, restore on startup:
```rust
// On close
let size = window.size();
settings.set_window_width(size.width);
settings.set_window_height(size.height);

// On startup
window.set_width(settings.window_width());
window.set_height(settings.window_height());
```

---

### Image/Icon Display

| Aspect | Details |
|--------|---------|
| **Slint Support** | Built-in Image element, SVG/PNG/JPEG |
| **Complexity** | LOW |
| **Status** | AVAILABLE |

**Current Usage:** Application icon, button icons.

**Pattern:**
```slint
Image {
    source: @image-url("CLASSIC.ico");
    width: 128px;
    height: 128px;
}
```

**Supported Formats:** SVG, PNG, JPEG (plus many more with cargo feature).

**Sources:**
- [Image Documentation](https://docs.slint.dev/latest/docs/slint/reference/elements/image/)

---

## Differentiators

Features Slint does better than Qt/Python, or unique Slint advantages.

### Native Rust Integration

| Aspect | Details |
|--------|---------|
| **Advantage** | Direct call to Rust business logic, no FFI overhead |
| **Complexity** | N/A (architectural benefit) |

**Current Pain Point:** Python GUI -> AsyncBridge -> Rust via PyO3 -> Back to Python.

**Slint Advantage:** Rust GUI -> Direct Rust calls -> Same runtime.

**Impact:**
- Eliminate AsyncBridge complexity
- Single Tokio runtime for everything
- No GIL contention
- Type-safe across entire stack

---

### Compile-Time UI Validation

| Aspect | Details |
|--------|---------|
| **Advantage** | .slint files validated at compile time |
| **Complexity** | N/A (tooling benefit) |

**Current Pain Point:** Qt signals/slots can fail at runtime with typos.

**Slint Advantage:**
- Property bindings checked at compile
- LSP integration for IDE errors
- No runtime signal connection failures

---

### Lightweight Runtime

| Aspect | Details |
|--------|---------|
| **Advantage** | <300KB RAM footprint |
| **Complexity** | N/A (runtime benefit) |

**Current:** Qt + Python runtime is 50-100MB+.

**Slint:** Entire runtime fits in <300KB RAM. Faster startup, smaller binary.

---

### GPU-Accelerated Rendering

| Aspect | Details |
|--------|---------|
| **Advantage** | Skia or software renderer, GPU acceleration |
| **Complexity** | N/A (rendering benefit) |

**Renderers Available:**
- Skia (GPU accelerated, best quality)
- FemtoVG (OpenGL)
- Software (fallback, works everywhere)

---

### Multi-Window Support (Slint 1.7+)

| Aspect | Details |
|--------|---------|
| **Advantage** | Multiple windows with shared state |
| **Complexity** | LOW |

**Pattern:** Define multiple Window components, manage from Rust.

**Sources:**
- [Multi-Window Blog](https://slint.dev/blog/slint-1.7-released)

---

### Tokio Integration

| Aspect | Details |
|--------|---------|
| **Advantage** | Native async with existing Rust infrastructure |
| **Complexity** | MEDIUM |

**Pattern:**
```rust
slint::spawn_local(async move {
    // Run on UI thread
    let result = tokio::spawn(async {
        // Background Tokio task
        scan_logs().await
    }).await;

    ui.set_scan_result(result);
});
```

**Sources:**
- [Async Integration](https://github.com/slint-ui/slint/discussions/4377)

---

## Anti-Features

Features Slint cannot do or should NOT try to do.

### Native Markdown Rendering

| Aspect | Details |
|--------|---------|
| **Why Avoid** | Not yet implemented in Slint |
| **What To Do Instead** | Custom solution or external renderer |
| **Severity** | HIGH (critical for CLASSIC) |

**Current State:** Rich text support is in active development (issue #9560, #6684) but NOT production-ready.

**Alternatives:**
1. **Convert markdown to styled elements:** Parse markdown in Rust, render as Slint Text/Rectangle with styling
2. **WebView integration:** Use embedded WebView with marked.js (adds complexity)
3. **Pre-render to HTML:** Keep Qt-style HTML approach with embedded browser component

**Recommendation:** Implement custom markdown-to-Slint renderer using `pulldown-cmark` (Rust markdown parser). Render headings, bold, lists, code blocks as styled Slint elements.

**Complexity:** HIGH

**Sources:**
- [Rich Text Issue](https://github.com/slint-ui/slint/issues/9560)
- [Markdown Issue](https://github.com/slint-ui/slint/issues/6684)

---

### Native File Dialogs

| Aspect | Details |
|--------|---------|
| **Why Avoid** | Slint has no built-in file dialog |
| **What To Do Instead** | Use external crate |
| **Severity** | MEDIUM |

**Current Usage:**
- Browse for INI folder
- Open crash logs folder

**Solution:** Use `rfd` (Rust File Dialog) or `native-dialog` crate:
```rust
use rfd::FileDialog;

let folder = FileDialog::new()
    .set_directory(&starting_path)
    .pick_folder();
```

**Complexity:** LOW (well-documented integration)

**Sources:**
- [File Dialog Discussion](https://github.com/slint-ui/slint/discussions/3015)
- [rfd crate](https://crates.io/crates/rfd)

---

### Native Tooltips

| Aspect | Details |
|--------|---------|
| **Why Avoid** | No built-in tooltip property |
| **What To Do Instead** | Custom PopupWindow or skip |
| **Severity** | LOW |

**Current Usage:** Tooltips on buttons (e.g., "Refresh the reports list").

**Workaround:** PopupWindow with delay, but it's clunky and "steals mouse input."

**Recommendation:** For MVP, skip tooltips. Add later when Slint implements native support (tracked in issue #6446).

**Sources:**
- [Tooltip Discussion](https://github.com/slint-ui/slint/discussions/1617)
- [Tooltip Issue](https://github.com/slint-ui/slint/issues/6446)

---

### Native Splitter/Resizable Panes

| Aspect | Details |
|--------|---------|
| **Why Avoid** | No built-in splitter widget |
| **What To Do Instead** | Custom implementation or fixed layout |
| **Severity** | MEDIUM |

**Current Usage:** QSplitter between reports list (30%) and markdown viewer (70%).

**Workaround:** Custom splitter using TouchArea:
```slint
// Custom splitter implementation required
Rectangle {
    property <length> split-position: 300px;

    // Left panel
    Rectangle { width: split-position; }

    // Drag handle
    TouchArea {
        moved => { split-position = mouse-x; }
    }

    // Right panel
    Rectangle { x: split-position + 5px; }
}
```

**Complexity:** MEDIUM

**Sources:**
- [Splitter Discussion](https://github.com/slint-ui/slint/discussions/343)

---

### Blocking Modal Dialogs

| Aspect | Details |
|--------|---------|
| **Why Avoid** | Slint dialogs don't block like native OS modals |
| **What To Do Instead** | Use callbacks, disable parent UI |
| **Severity** | LOW |

**Pattern:** Instead of blocking, use callback pattern:
```rust
ui.on_settings_accepted(|| {
    // Handle save
});
ui.on_settings_cancelled(|| {
    // Handle cancel
});
show_settings_dialog();
// UI continues, callbacks handle result
```

---

### System Tray (If Needed)

| Aspect | Details |
|--------|---------|
| **Why Avoid** | Not implemented in Slint |
| **What To Do Instead** | External crate if needed |
| **Severity** | N/A (not currently used) |

**Notes:** Current CLASSIC does not use system tray. If needed, use `tray-icon` crate.

---

## Feature Dependencies

```
Window Setup
    |
    +-- Dark Theme (compile-time selection)
    |
    +-- TabWidget
            |
            +-- Main Tab
            |       +-- Buttons
            |       +-- Scan Controls
            |       +-- Progress Indicator
            |
            +-- File Backup Tab
            |       +-- Buttons
            |       +-- File Operations (via rfd)
            |
            +-- Articles Tab
            |       +-- Static Content
            |
            +-- Results Tab
                    +-- Split Layout (custom)
                    |       +-- ListView (reports)
                    |       +-- Markdown Viewer (custom)
                    |
                    +-- Context Menu
                    +-- Clipboard Operations

Settings Dialog (separate window)
    +-- TabWidget
    +-- Form Controls
    +-- File Browser (via rfd)
```

---

## MVP Recommendation

**Phase 1: Core Window**
1. Main window with TabWidget (4 tabs)
2. Dark theme (fluent-dark or material-dark)
3. Basic buttons and controls

**Phase 2: Scanning**
1. Scan buttons with enable/disable states
2. Progress indicator with async updates
3. Basic error dialogs

**Phase 3: Results Viewer**
1. ListView for reports (without splitter initially)
2. Basic text display (plain text, not markdown)
3. Context menu for actions
4. Clipboard copy

**Phase 4: Markdown Rendering**
1. Custom markdown-to-Slint renderer
2. Headers, bold, lists, code blocks
3. Custom styling for CLASSIC report elements

**Phase 5: Settings and Polish**
1. Settings dialog with tabs
2. File dialogs (via rfd)
3. Window geometry persistence
4. Splitter (if needed)

**Defer to Post-MVP:**
- Tooltips (wait for Slint native support)
- System tray (not currently used)
- Rich text editing (read-only reports only)

---

## Sources Summary

### Official Documentation
- [Slint Main Site](https://slint.dev/)
- [Slint GitHub](https://github.com/slint-ui/slint)
- [Widget Documentation](https://releases.slint.dev/1.1.0/docs/slint/src/builtins/widgets)

### Blog Posts
- [Slint 1.7 Release](https://slint.dev/blog/slint-1.7-released)
- [Making Slint Desktop-Ready](https://slint.dev/blog/making-slint-desktop-ready)

### GitHub Discussions
- [Async Integration](https://github.com/slint-ui/slint/discussions/4377)
- [Progress Updates](https://github.com/slint-ui/slint/discussions/8466)
- [File Dialogs](https://github.com/slint-ui/slint/discussions/3015)
- [Context Menus](https://docs.slint.dev/latest/docs/slint/reference/window/contextmenuarea/)
- [Modal Dialogs](https://github.com/slint-ui/slint/discussions/6028)

### Known Issues
- [Rich Text Issue #9560](https://github.com/slint-ui/slint/issues/9560)
- [Markdown Issue #6684](https://github.com/slint-ui/slint/issues/6684)
- [Tooltip Issue #6446](https://github.com/slint-ui/slint/issues/6446)
