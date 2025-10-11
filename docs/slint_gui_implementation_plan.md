# Slint GUI Implementation Plan for CLASSIC

**Version:** 1.0
**Date:** 2025-10-11
**Status:** Planning Phase

## Overview

This document outlines the implementation plan for a Slint-based pure Rust GUI for CLASSIC that achieves **feature parity** with the existing Python/PySide6 interface while modernizing the design with **Microsoft's Fluent Design System**. The Slint GUI will leverage the existing `-core` business logic crates while providing a native Windows 11 desktop experience with 10-150x performance improvements.

## Goals

1. **Feature Parity**: Implement all functionality from the Python GUI (PRIMARY GOAL)
2. **Modern Design**: Fluent Design System with dark theme (not exact Python GUI replica)
3. **Pure Rust**: 100% Rust implementation using existing `-core` crates
4. **Performance**: Leverage Rust's performance for responsive UI (10-150x faster operations)
5. **Maintainability**: Clean separation between UI (.slint files) and business logic (Rust)

## Architecture

### Project Structure

```
classic-gui-slint/              # New crate for Slint GUI
├── Cargo.toml
├── src/
│   ├── main.rs                 # Entry point
│   ├── app.rs                  # Application state management
│   ├── handlers/               # Event handlers
│   │   ├── mod.rs
│   │   ├── scan.rs             # Scan operations handlers
│   │   ├── backup.rs           # Backup operations handlers
│   │   ├── settings.rs         # Settings handlers
│   │   └── results.rs          # Results viewer handlers
│   ├── models/                 # Data models for UI bindings
│   │   ├── mod.rs
│   │   ├── report.rs           # Report list model
│   │   └── settings.rs         # Settings model
│   ├── async_bridge.rs         # Tokio/Slint async integration
│   └── styles/                 # Style constants
│       └── colors.rs           # Color definitions
├── ui/                         # Slint UI files
│   ├── main.slint              # Main window
│   ├── tabs/
│   │   ├── main_tab.slint      # Main options tab
│   │   ├── backups_tab.slint   # File backup tab
│   │   ├── articles_tab.slint  # Articles/links tab
│   │   └── results_tab.slint   # Results viewer tab
│   ├── components/
│   │   ├── folder_selector.slint   # Folder selection widget
│   │   ├── scan_button.slint       # Main scan buttons
│   │   ├── backup_section.slint    # Backup operation section
│   │   ├── report_list.slint       # Report list widget
│   │   └── markdown_viewer.slint   # Markdown viewer
│   └── styles/
│       └── fluent_dark.slint   # Fluent Design dark theme
└── README.md
```

### Dependencies

```toml
[dependencies]
# CLASSIC core crates (business logic)
classic-shared = { path = "../classic-shared" }
classic-yaml-core = { path = "../classic-yaml-core" }
classic-database-core = { path = "../classic-database-core" }
classic-file-io-core = { path = "../classic-file-io-core" }
classic-scanlog-core = { path = "../classic-scanlog-core" }
classic-config-core = { path = "../classic-config-core" }

# Slint framework
slint = { version = "1.9", features = ["backend-qt", "markdown"] }

# Async runtime (shared with -core crates)
tokio = { workspace = true }

# Utilities
anyhow = { workspace = true }
thiserror = { workspace = true }
tracing = { workspace = true }

# File system operations
notify = "6.1"  # File watcher for results tab
walkdir = "2.4"

# Markdown rendering (if not built into Slint)
pulldown-cmark = "0.9"

# Clipboard support
arboard = "3.3"

# System integration
open = "5.0"  # Open URLs and folders
```

## Design System: Fluent Design

### Why Fluent Design?

CLASSIC targets Windows users (Fallout 4/Skyrim modding is primarily Windows-based), making Microsoft's **Fluent Design System** the ideal choice:

**Advantages:**
1. **Native Windows 11 Integration**: Feels at home on Windows
2. **Excellent Dark Mode**: Mica, Acrylic, and backdrop materials designed for dark themes
3. **Desktop-Optimized**: Better suited for desktop apps than mobile-focused Material Design
4. **Modern & Professional**: Clean, minimal aesthetic with subtle depth
5. **Accessibility Built-in**: WCAG 2.1 compliant color contrasts and focus indicators
6. **Performance-Friendly**: Efficient animations and GPU-accelerated effects

**Fluent Design Principles Applied:**
- **Light**: Subtle use of shadows and highlights to create depth
- **Depth**: Layering and parallax effects for visual hierarchy
- **Motion**: Smooth, purposeful animations (not excessive)
- **Material**: Acrylic transparency effects for modern look
- **Scale**: Responsive sizing that adapts to window dimensions

### Color Palette (Fluent Dark Theme)

Based on Windows 11 Fluent Dark theme with CLASSIC-specific accents:

```rust
// src/styles/colors.rs
pub struct FluentDark {
    // Base colors (Windows 11 dark theme)
    pub background: Color,              // #202020 (solid background)
    pub background_layer1: Color,       // #2b2b2b (elevated layer 1)
    pub background_layer2: Color,       // #323232 (elevated layer 2)
    pub background_layer3: Color,       // #3a3a3a (elevated layer 3 - cards/buttons)

    // Acrylic/transparency (for modern effects)
    pub acrylic_background: Color,      // #202020 with 70% opacity
    pub acrylic_border: Color,          // #5c5c5c with 50% opacity

    // Text colors (WCAG AA compliant)
    pub text_primary: Color,            // #ffffff (primary text)
    pub text_secondary: Color,          // #a0a0a0 (secondary text)
    pub text_tertiary: Color,           // #6d6d6d (disabled/tertiary text)
    pub text_on_accent: Color,          // #000000 (text on accent backgrounds)

    // Interactive states
    pub hover: Color,                   // #404040 (hover overlay)
    pub pressed: Color,                 // #2a2a2a (pressed overlay)
    pub disabled: Color,                // #3a3a3a (disabled background)

    // Accent colors (Windows 11 blue + CLASSIC green)
    pub accent: Color,                  // #60cdff (Fluent blue - primary actions)
    pub accent_hover: Color,            // #4fb3e6 (darker blue on hover)
    pub accent_pressed: Color,          // #3e9ccf (even darker when pressed)
    pub accent_secondary: Color,        // #005fb8 (secondary accent)

    // Semantic colors
    pub success: Color,                 // #2ded8a (green - success/papyrus start)
    pub warning: Color,                 // #faa919 (orange - warnings)
    pub error: Color,                   // #ed2d2d (red - errors/papyrus stop)
    pub info: Color,                    // #60cdff (blue - informational)

    // Borders and dividers
    pub border: Color,                  // #5c5c5c (default borders)
    pub border_subtle: Color,           // #383838 (subtle dividers)
    pub focus_border: Color,            // #60cdff (focus indicator)

    // Scrollbars
    pub scrollbar_bg: Color,            // #1a1a1a (scrollbar track)
    pub scrollbar_thumb: Color,         // #5c5c5c (scrollbar thumb)
    pub scrollbar_thumb_hover: Color,   // #707070 (scrollbar thumb hover)
}
```

**Slint Theme File (`ui/styles/fluent_dark.slint`):**
```slint
// Fluent Design Dark Theme for CLASSIC
export global FluentDark {
    // Base layers
    property<color> background: #202020;
    property<color> layer1: #2b2b2b;
    property<color> layer2: #323232;
    property<color> layer3: #3a3a3a;

    // Text hierarchy
    property<color> text-primary: #ffffff;
    property<color> text-secondary: #a0a0a0;
    property<color> text-tertiary: #6d6d6d;
    property<color> text-on-accent: #000000;

    // Interactive states
    property<color> hover: #404040;
    property<color> pressed: #2a2a2a;
    property<color> disabled: #3a3a3a;

    // Accent colors
    property<color> accent: #60cdff;
    property<color> accent-hover: #4fb3e6;
    property<color> accent-pressed: #3e9ccf;

    // Semantic colors
    property<color> success: #2ded8a;
    property<color> warning: #faa919;
    property<color> error: #ed2d2d;
    property<color> info: #60cdff;

    // Borders
    property<color> border: #5c5c5c;
    property<color> border-subtle: #383838;
    property<color> focus: #60cdff;

    // Scrollbars
    property<color> scrollbar-bg: #1a1a1a;
    property<color> scrollbar-thumb: #5c5c5c;
    property<color> scrollbar-thumb-hover: #707070;

    // Spacing (8px base unit - Fluent standard)
    property<length> spacing-xs: 4px;
    property<length> spacing-sm: 8px;
    property<length> spacing-md: 16px;
    property<length> spacing-lg: 24px;
    property<length> spacing-xl: 32px;

    // Border radius (Fluent uses 4px base)
    property<length> radius-sm: 4px;
    property<length> radius-md: 8px;
    property<length> radius-lg: 12px;

    // Typography (Segoe UI family - Windows standard)
    property<string> font-family: "Segoe UI Variable";
    property<length> font-size-sm: 12px;
    property<length> font-size-base: 14px;
    property<length> font-size-lg: 16px;
    property<length> font-size-xl: 20px;
    property<length> font-size-2xl: 24px;

    // Font weights
    property<int> font-weight-regular: 400;
    property<int> font-weight-semibold: 600;
    property<int> font-weight-bold: 700;

    // Shadows (subtle depth)
    property<length> shadow-sm: 2px;
    property<length> shadow-md: 4px;
    property<length> shadow-lg: 8px;

    // Animation durations (Fluent standard)
    property<duration> animation-fast: 150ms;
    property<duration> animation-normal: 250ms;
    property<duration> animation-slow: 350ms;
}
```

### Typography

**Font Stack:**
- **Primary**: Segoe UI Variable (Windows 11 native)
- **Fallback**: Segoe UI, system-ui, sans-serif
- **Monospace**: Cascadia Mono, Consolas, monospace (for code blocks)

**Type Scale:**
```slint
export global Typography {
    // Headings
    property<length> h1: 24px;  // weight: 700
    property<length> h2: 20px;  // weight: 600
    property<length> h3: 16px;  // weight: 600

    // Body text
    property<length> body: 14px;      // weight: 400 (default)
    property<length> body-large: 16px; // weight: 400
    property<length> body-small: 12px; // weight: 400

    // UI elements
    property<length> button: 14px;    // weight: 600
    property<length> caption: 12px;   // weight: 400
    property<length> label: 14px;     // weight: 600
}
```

### Component Styling Patterns

#### Buttons (Fluent Style)

```slint
// ui/components/fluent_button.slint
export component FluentButton inherits Rectangle {
    in property<string> text <=> label.text;
    in property<bool> primary: false;
    in property<bool> enabled: true;

    callback clicked();

    // Base styling
    background: primary ? FluentDark.accent : FluentDark.layer3;
    border-radius: FluentDark.radius-sm;
    min-height: 32px;
    min-width: 120px;

    // Hover state
    TouchArea {
        clicked => {
            if (enabled) {
                root.clicked();
            }
        }
    }

    states [
        hover when touch.has-hover && enabled: {
            background: primary ? FluentDark.accent-hover : FluentDark.hover;
            in { animate background { duration: FluentDark.animation-fast; } }
        }
        pressed when touch.pressed && enabled: {
            background: primary ? FluentDark.accent-pressed : FluentDark.pressed;
        }
        disabled when !enabled: {
            background: FluentDark.disabled;
            opacity: 0.5;
        }
    ]

    // Text label
    HorizontalLayout {
        padding: 8px 16px;
        alignment: center;

        Text {
            text: label.text;
            color: primary ? FluentDark.text-on-accent : FluentDark.text-primary;
            font-size: FluentDark.font-size-base;
            font-weight: FluentDark.font-weight-semibold;
        }
    }
}
```

#### Cards (Elevated Surfaces)

```slint
// ui/components/fluent_card.slint
export component FluentCard inherits Rectangle {
    // Card with subtle elevation
    background: FluentDark.layer2;
    border-radius: FluentDark.radius-md;
    border-width: 1px;
    border-color: FluentDark.border-subtle;

    // Subtle shadow for depth
    drop-shadow-blur: FluentDark.shadow-sm;
    drop-shadow-color: #00000040;
    drop-shadow-offset-y: 2px;

    // Content padding
    padding: FluentDark.spacing-md;
}
```

#### Tabs (Modern Tab Bar)

```slint
export component FluentTabBar {
    // Horizontal tab bar with accent underline
    background: FluentDark.layer1;
    height: 48px;

    HorizontalLayout {
        spacing: 0;

        for tab in tabs: Rectangle {
            // Tab item
            background: tab.selected ? FluentDark.layer2 : transparent;

            TouchArea {
                clicked => { select-tab(tab.index); }
            }

            VerticalLayout {
                padding: 12px 20px;

                Text {
                    text: tab.title;
                    color: tab.selected ? FluentDark.text-primary : FluentDark.text-secondary;
                    font-weight: tab.selected ? FluentDark.font-weight-semibold : FluentDark.font-weight-regular;
                }

                // Accent underline for selected tab
                Rectangle {
                    height: 2px;
                    background: tab.selected ? FluentDark.accent : transparent;
                    in { animate background { duration: FluentDark.animation-normal; } }
                }
            }
        }
    }
}
```

### Animation Guidelines

**Fluent Motion Principles:**
1. **Purposeful**: Animations guide attention, not distract
2. **Fast**: Keep animations under 350ms
3. **Natural**: Use easing functions (ease-in-out)
4. **Consistent**: Same animation style throughout app

**Common Animations:**
```slint
// Fade in
in {
    animate opacity {
        duration: FluentDark.animation-normal;
        easing: ease-in-out;
    }
}

// Slide up
in {
    animate y {
        duration: FluentDark.animation-normal;
        easing: cubic-bezier(0.1, 0.9, 0.2, 1);
    }
}

// Button press (scale down slightly)
pressed when touch.pressed: {
    scale: 0.98;
    in { animate scale { duration: FluentDark.animation-fast; } }
}

// Focus ring (expand outward)
focus when has-focus: {
    border-color: FluentDark.focus;
    border-width: 2px;
    in { animate border-width { duration: FluentDark.animation-fast; } }
}
```

### Accessibility Features

1. **High Contrast Support**: All colors meet WCAG AA (4.5:1 contrast ratio)
2. **Focus Indicators**: Visible focus rings on all interactive elements
3. **Keyboard Navigation**: Tab order and keyboard shortcuts
4. **Screen Reader Support**: Proper labels and ARIA attributes
5. **Text Scaling**: Responsive typography that scales with system settings

### Layout Principles

**Spacing System (8px base):**
- **xs**: 4px (tight spacing)
- **sm**: 8px (default spacing)
- **md**: 16px (section spacing)
- **lg**: 24px (major section breaks)
- **xl**: 32px (page margins)

**Responsive Breakpoints:**
- **Minimum**: 550x350 (maintains functionality)
- **Default**: 650x350 (optimal for most users)
- **Large**: 1200x700+ (expands Results tab, more columns)

## UI Components Breakdown

### 1. Main Window (`main.slint`)

Replicates: `CLASSIC_Interface.py` MainWindow

**Layout:**
- Window title: "Crash Log Auto Scanner & Setup Integrity Checker | {version}"
- Window icon: CLASSIC.ico
- Dark theme by default
- Tab widget with 4 tabs: MAIN OPTIONS, FILE BACKUP, ARTICLES, RESULTS
- Minimum size: 550x350
- Default size: 650x350
- Window geometry persistence (save/restore size and position)

**Slint Structure:**
```slint
import { TabWidget, VerticalBox } from "std-widgets.slint";
import { DarkTheme } from "styles/dark_theme.slint";
import { MainTab } from "tabs/main_tab.slint";
import { BackupsTab } from "tabs/backups_tab.slint";
import { ArticlesTab } from "tabs/articles_tab.slint";
import { ResultsTab } from "tabs/results_tab.slint";

export component MainWindow inherits Window {
    title: "Crash Log Auto Scanner & Setup Integrity Checker | 6.7.1";
    icon: @image-url("../assets/CLASSIC.ico");
    min-width: 550px;
    min-height: 350px;
    preferred-width: 650px;
    preferred-height: 350px;
    background: DarkTheme.background;

    callback window-closed();

    VerticalBox {
        padding: 10px;
        spacing: 10px;

        TabWidget {
            Tab {
                title: "MAIN OPTIONS";
                MainTab { }
            }
            Tab {
                title: "FILE BACKUP";
                BackupsTab { }
            }
            Tab {
                title: "ARTICLES";
                ArticlesTab { }
            }
            Tab {
                title: "RESULTS";
                ResultsTab { }
            }
        }
    }
}
```

### 2. Main Tab (`tabs/main_tab.slint`)

Replicates: `TabSetupMixin.setup_main_tab()`

**Components:**
- **Header Section (fixed height 100px)**:
  - Folder selector: "STAGING MODS FOLDER" (optional, with browse button)
  - Folder selector: "CUSTOM SCAN FOLDER" (optional, with browse button)

- **Main Buttons**:
  - "SCAN CRASH LOGS" (large, prominent)
  - "SCAN GAME FILES" (large, prominent)

- **Bottom Utility Buttons** (2 rows):
  - Row 1: ABOUT | HELP | SETTINGS | OPEN CRASH LOGS | CHECK UPDATES
  - Row 2: START/STOP PAPYRUS MONITORING (toggleable, green/red) | EXIT

**Key Features:**
- Folder path validation (auto-validate when user finishes editing)
- Button states (disabled during scan operations)
- Papyrus button color changes (green for START, red for STOP)
- Tooltips on all interactive elements

### 3. Backups Tab (`tabs/backups_tab.slint`)

Replicates: `TabSetupMixin.setup_backups_tab()`

**Components:**
- **Information labels** (at top):
  - "BACKUP > Backup files from the game folder into the CLASSIC Backup folder."
  - "RESTORE > Restore file backup from the CLASSIC Backup folder into the game folder."
  - "REMOVE > Remove files only from the game folder without removing existing backups."

- **Backup Sections** (4 categories):
  - XSE section: BACKUP | RESTORE | REMOVE buttons
  - RESHADE section: BACKUP | RESTORE | REMOVE buttons
  - VULKAN section: BACKUP | RESTORE | REMOVE buttons
  - ENB section: BACKUP | RESTORE | REMOVE buttons

- **Bottom bar**:
  - "OPEN CLASSIC BACKUPS" button (opens backup folder in file explorer)

**Key Features:**
- Check existing backups on tab load
- Update button states based on backup availability
- Progress indicators during operations

### 4. Articles Tab (`tabs/articles_tab.slint`)

Replicates: `TabSetupMixin.setup_articles_tab()`

**Components:**
- Title label: "USEFUL RESOURCES & LINKS" (centered, bold)
- **3-column grid** of buttons with external links:
  - BUFFOUT 4 INSTALLATION
  - FALLOUT 4 SETUP TIPS
  - IMPORTANT PATCHES LIST
  - BUFFOUT 4 NEXUS
  - CLASSIC NEXUS
  - CLASSIC GITHUB
  - DDS TEXTURE SCANNER
  - BETHINI PIE
  - WRYE BASH

**Key Features:**
- Buttons open URLs in default browser
- Hover states for interactivity
- Tooltips showing full URL

### 5. Results Tab (`tabs/results_tab.slint`)

Replicates: `ResultsViewerMixin.setup_results_tab()`

**Layout:**
- Horizontal split pane (resizable)
  - Left panel (30%): Report list + buttons
  - Right panel (70%): Markdown viewer + toolbar

**Left Panel Components:**
- **Report List**:
  - List of *-AUTOSCAN.md reports (sorted by date, descending)
  - Shows report filename and date
  - Context menu (View, Copy to Clipboard, Delete)

- **Button Bar**:
  - Refresh | Delete | Open Folder

**Right Panel Components:**
- **Metadata Widget**: Shows report filename, size, date
- **Markdown Viewer**: Renders markdown with syntax highlighting
- **Toolbar**:
  - Copy button (copy report to clipboard)
  - Zoom controls: - | 100% | +

**Key Features:**
- Auto-refresh on directory changes (file watcher)
- Debounced refresh (500ms)
- Auto-select first report on load
- Delete confirmation dialog
- Markdown rendering with code blocks, tables, links

## Theme System

### Dark Mode Colors (from `StyleSheets.py`)

```rust
// src/styles/colors.rs
pub struct DarkTheme {
    pub background: Color,          // #2b2b2b
    pub surface: Color,             // #3c3c3c
    pub border: Color,              // #5c5c5c
    pub text: Color,                // #ffffff
    pub text_secondary: Color,      // #666666
    pub hover: Color,               // #444444
    pub pressed: Color,             // #222222
    pub accent: Color,              // #0078d4
    pub scrollbar_bg: Color,        // #202020
    pub scrollbar_handle: Color,    // #686868
}
```

**Slint Theme File (`ui/styles/dark_theme.slint`):**
```slint
export global DarkTheme {
    property<color> background: #2b2b2b;
    property<color> surface: #3c3c3c;
    property<color> border: #5c5c5c;
    property<color> text: #ffffff;
    property<color> text-secondary: #666666;
    property<color> hover: #444444;
    property<color> pressed: #222222;
    property<color> accent: #0078d4;
    property<color> scrollbar-bg: #202020;
    property<color> scrollbar-handle: #686868;

    // Button colors
    property<color> button-bg: #3c3c3c;
    property<color> button-hover: #444444;
    property<color> button-pressed: #222222;

    // Special colors
    property<color> papyrus-start: #2ded8a;  // Green
    property<color> papyrus-stop: #ed2d2d;   // Red
}
```

## Async Integration Pattern

### Tokio + Slint Integration

Slint runs its own event loop, so we need to coordinate with Tokio. The pattern:

1. **Main thread**: Slint UI event loop
2. **Background thread**: Tokio runtime for async operations
3. **Communication**: `slint::invoke_from_event_loop()` to update UI from async tasks

```rust
// src/async_bridge.rs
use slint::ComponentHandle;
use std::sync::Arc;
use tokio::runtime::Runtime;

pub struct AsyncBridge {
    runtime: Arc<Runtime>,
}

impl AsyncBridge {
    pub fn new() -> Self {
        let runtime = Arc::new(
            tokio::runtime::Builder::new_multi_thread()
                .worker_threads(num_cpus::get())
                .enable_all()
                .build()
                .expect("Failed to create Tokio runtime")
        );

        Self { runtime }
    }

    /// Spawn async task and invoke callback on UI thread when done
    pub fn spawn<F, T>(&self, future: F, ui_callback: impl Fn(T) + Send + 'static)
    where
        F: Future<Output = T> + Send + 'static,
        T: Send + 'static,
    {
        let runtime = self.runtime.clone();
        std::thread::spawn(move || {
            let result = runtime.block_on(future);
            slint::invoke_from_event_loop(move || ui_callback(result)).unwrap();
        });
    }

    /// Use shared global runtime from classic-shared
    pub fn use_shared_runtime() -> &'static Runtime {
        classic_shared::get_runtime()
    }
}
```

**Usage in Event Handlers:**

```rust
// src/handlers/scan.rs
use crate::async_bridge::AsyncBridge;
use crate::MainWindow;
use classic_scanlog_core::LogParser;

pub fn handle_scan_crash_logs(main_window: &MainWindow, bridge: &AsyncBridge) {
    let main_window_weak = main_window.as_weak();

    // Disable scan buttons
    main_window.set_scan_in_progress(true);

    // Spawn async scan operation
    bridge.spawn(
        async move {
            // Use -core crate for scanning
            let parser = LogParser::new();
            let results = parser.scan_logs().await?;
            Ok(results)
        },
        move |result| {
            // Update UI on completion (runs on UI thread)
            let main_window = main_window_weak.upgrade().unwrap();
            main_window.set_scan_in_progress(false);

            match result {
                Ok(results) => {
                    main_window.set_scan_results(results);
                    // Show completion message
                }
                Err(e) => {
                    // Show error message
                }
            }
        }
    );
}
```

## Implementation Phases

### Phase 1: Project Setup & Basic Window (Week 1)

**Tasks:**
- [ ] Create `classic-gui-slint` crate in workspace
- [ ] Add Slint dependencies to `Cargo.toml`
- [ ] Create basic `MainWindow` in `main.slint`
- [ ] Implement dark theme in `dark_theme.slint`
- [ ] Create `main.rs` with window initialization
- [ ] Test window display and theme
- [ ] Implement window geometry persistence (save/restore)

**Deliverables:**
- Empty window with dark theme
- Tab widget with 4 placeholder tabs
- Window geometry saves between sessions

### Phase 2: Main Tab UI (Week 2)

**Tasks:**
- [ ] Create `FolderSelector` component
- [ ] Implement folder browse dialogs (native file picker)
- [ ] Create main scan buttons (SCAN CRASH LOGS, SCAN GAME FILES)
- [ ] Create bottom utility buttons
- [ ] Implement Papyrus button toggle styles (green/red)
- [ ] Add tooltips to all interactive elements
- [ ] Connect buttons to placeholder handlers

**Deliverables:**
- Fully functional Main Tab layout
- Button states (enabled/disabled)
- Folder path display and validation

### Phase 3: Scan Operations Integration (Week 3)

**Tasks:**
- [ ] Implement `AsyncBridge` for Tokio/Slint integration
- [ ] Create `handlers/scan.rs` module
- [ ] Integrate `classic-scanlog-core` for crash log scanning
- [ ] Integrate `classic-file-io-core` for game file scanning
- [ ] Add progress indicators during scanning
- [ ] Display scan results in message dialogs
- [ ] Implement scan cancellation
- [ ] Add audio notifications (completion sounds)

**Deliverables:**
- Functional crash log scanning
- Functional game file scanning
- Progress feedback and completion notifications

### Phase 4: Backups Tab (Week 4)

**Tasks:**
- [ ] Create `BackupSection` component
- [ ] Implement backup operations (XSE, ReShade, Vulkan, ENB)
- [ ] Create `handlers/backup.rs` module
- [ ] Integrate `classic-file-io-core` for file operations
- [ ] Add backup state detection (existing backups)
- [ ] Implement open backups folder functionality
- [ ] Add confirmation dialogs for destructive operations
- [ ] Add progress indicators for file operations

**Deliverables:**
- Fully functional Backups Tab
- All backup/restore/remove operations working
- State management for backup availability

### Phase 5: Articles Tab (Week 5)

**Tasks:**
- [ ] Create 3-column grid layout
- [ ] Add 9 resource buttons with URLs
- [ ] Implement `open` crate for URL launching
- [ ] Add hover states and tooltips
- [ ] Style buttons to match Python GUI

**Deliverables:**
- Fully functional Articles Tab
- All links open in default browser

### Phase 6: Results Tab - Part 1 (Week 6)

**Tasks:**
- [ ] Create split pane layout (resizable)
- [ ] Implement `ReportList` component
- [ ] Add report scanning (glob *-AUTOSCAN.md)
- [ ] Integrate `notify` crate for file watching
- [ ] Implement report list population
- [ ] Add refresh/delete/open folder buttons
- [ ] Implement context menu (View, Copy, Delete)
- [ ] Add report selection handling

**Deliverables:**
- Functional report list
- File watcher auto-refresh
- Report management (delete, open folder)

### Phase 7: Results Tab - Part 2 (Week 7)

**Tasks:**
- [ ] Create `MarkdownViewer` component
- [ ] Integrate markdown rendering (Slint built-in or `pulldown-cmark`)
- [ ] Add metadata widget
- [ ] Implement zoom controls (-, 100%, +)
- [ ] Add copy to clipboard functionality
- [ ] Implement code syntax highlighting in markdown
- [ ] Add table rendering support
- [ ] Handle markdown images and links

**Deliverables:**
- Fully functional Results Tab
- Markdown rendering with formatting
- Zoom and copy functionality

### Phase 8: Settings & Dialogs (Week 8)

**Tasks:**
- [ ] Create settings dialog component
- [ ] Integrate `classic-config-core` for configuration
- [ ] Implement About dialog
- [ ] Implement Help dialogs
- [ ] Create Papyrus monitoring dialog
- [ ] Add update check dialog
- [ ] Implement path selection dialogs
- [ ] Add error message dialogs
- [ ] Add confirmation dialogs

**Deliverables:**
- All dialogs functional
- Settings persistence
- Help and About screens

### Phase 9: Polish & Testing (Week 9-10)

**Tasks:**
- [ ] Add loading spinners/animations
- [ ] Implement proper error handling throughout
- [ ] Add logging and diagnostics
- [ ] Test all scan operations end-to-end
- [ ] Test all backup operations
- [ ] Test window geometry persistence
- [ ] Test file watcher stability
- [ ] Performance profiling and optimization
- [ ] Memory usage optimization
- [ ] Add keyboard shortcuts
- [ ] Accessibility improvements
- [ ] Cross-platform testing (Windows primary, Linux/macOS if time)

**Deliverables:**
- Polished, production-ready GUI
- Comprehensive test coverage
- Performance benchmarks

### Phase 10: Documentation & Release (Week 11)

**Tasks:**
- [ ] Write user documentation
- [ ] Create developer documentation
- [ ] Add README with screenshots
- [ ] Create build and packaging scripts
- [ ] Test Windows installer
- [ ] Update main CLAUDE.md with Slint GUI info
- [ ] Create release notes
- [ ] Tag v1.0 release

**Deliverables:**
- Complete documentation
- Release packages
- Migration guide from Python GUI

## Technical Considerations

### 1. Shared Runtime (ONE RUNTIME RULE)

**CRITICAL**: Use `classic_shared::get_runtime()` for all async operations to avoid deadlocks.

```rust
use classic_shared::get_runtime;

// In handlers
pub fn handle_operation() {
    get_runtime().spawn(async move {
        // Async operation here
    });
}
```

### 2. State Management

Use Slint's property system for reactive UI updates:

```slint
// In main_tab.slint
export component MainTab {
    property<bool> scan-in-progress: false;
    property<string> mods-folder-path: "";
    property<string> scan-folder-path: "";

    callback scan-crash-logs();
    callback scan-game-files();

    // Buttons automatically disabled when scan-in-progress is true
    Button {
        text: "SCAN CRASH LOGS";
        enabled: !scan-in-progress;
        clicked => { scan-crash-logs(); }
    }
}
```

### 3. Error Handling

Use `anyhow::Result` for operations, display errors in dialogs:

```rust
pub async fn perform_scan() -> anyhow::Result<ScanResults> {
    let parser = LogParser::new()
        .context("Failed to initialize log parser")?;

    let results = parser.scan_logs().await
        .context("Scan operation failed")?;

    Ok(results)
}
```

### 4. File Watcher Pattern

Use `notify` crate for Results Tab auto-refresh:

```rust
use notify::{Watcher, RecursiveMode, Event};
use std::sync::mpsc::channel;

pub fn setup_file_watcher(path: PathBuf, callback: impl Fn() + Send + 'static) {
    let (tx, rx) = channel();
    let mut watcher = notify::recommended_watcher(tx).unwrap();
    watcher.watch(&path, RecursiveMode::NonRecursive).unwrap();

    std::thread::spawn(move || {
        for event in rx {
            if let Ok(Event { kind: EventKind::Create(_) | EventKind::Modify(_), .. }) = event {
                slint::invoke_from_event_loop(callback).unwrap();
            }
        }
    });
}
```

### 5. Clipboard Integration

Use `arboard` crate for clipboard operations:

```rust
use arboard::Clipboard;

pub fn copy_to_clipboard(text: &str) -> anyhow::Result<()> {
    let mut clipboard = Clipboard::new()?;
    clipboard.set_text(text)?;
    Ok(())
}
```

### 6. URL and Folder Opening

Use `open` crate for system integration:

```rust
use open;

pub fn open_url(url: &str) -> anyhow::Result<()> {
    open::that(url)?;
    Ok(())
}

pub fn open_folder(path: &Path) -> anyhow::Result<()> {
    open::that(path)?;
    Ok(())
}
```

## Migration Path from Python GUI

### For Users

1. **Seamless Transition**: Same UI layout and workflow
2. **Performance Boost**: 10-150x faster operations
3. **Native Experience**: Better OS integration, smaller memory footprint
4. **Settings Migration**: Auto-detect and migrate YAML settings
5. **No Python Required**: Single executable, no dependencies

### For Developers

1. **Cleaner Architecture**: UI in .slint, logic in Rust
2. **Type Safety**: Compile-time guarantees, no runtime errors
3. **Easier Testing**: Pure Rust test infrastructure
4. **Better Tooling**: Rust-analyzer, cargo, clippy
5. **Modular Design**: Business logic in `-core` crates remains reusable

## Testing Strategy

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_folder_validation() {
        let path = "/invalid/path";
        assert!(validate_folder_path(path).is_err());
    }

    #[tokio::test]
    async fn test_scan_operation() {
        let parser = LogParser::new();
        let results = parser.scan_logs().await.unwrap();
        assert!(!results.is_empty());
    }
}
```

### Integration Tests

```rust
#[test]
fn test_scan_workflow() {
    // 1. Launch GUI
    // 2. Set folder paths
    // 3. Trigger scan
    // 4. Verify results display
    // 5. Check report generation
}
```

### UI Tests (Manual for MVP)

- [ ] Test all buttons and interactions
- [ ] Test tab switching
- [ ] Test window resize and geometry persistence
- [ ] Test file watcher responsiveness
- [ ] Test markdown rendering
- [ ] Test error dialogs
- [ ] Test keyboard navigation

## Performance Targets

Based on existing Rust acceleration:

| Operation | Python GUI | Slint GUI Target |
|-----------|------------|------------------|
| Crash Log Scan | 2-3 seconds | 200-300ms |
| Game File Scan | 5-10 seconds | 500-1000ms |
| FormID Analysis | 250ms/1000 IDs | 10ms/1000 IDs |
| Report Load | 100-200ms | 10-20ms |
| UI Responsiveness | 60 FPS | 120 FPS |
| Memory Usage | 150-200 MB | 50-75 MB |
| Startup Time | 1-2 seconds | 200-500ms |

## Future Enhancements (Post-MVP)

1. **Cross-platform support**: Linux and macOS builds
2. **Plugin system**: Extensible architecture for mods
3. **Advanced search**: Full-text search in reports
4. **Export options**: PDF, HTML export for reports
5. **Batch operations**: Scan multiple logs in parallel
6. **Remote monitoring**: Web-based results viewer
7. **CLI integration**: Embed `classic-cli` in GUI for power users
8. **Theme customization**: User-defined color schemes
9. **Accessibility**: Screen reader support, keyboard navigation
10. **Internationalization**: Multi-language support

## Resources

### Slint Documentation

- **Official Docs**: https://slint.dev/docs
- **Rust API**: https://slint.dev/docs/rust/slint/
- **Tutorial**: https://slint.dev/docs/tutorial/rust
- **Examples**: https://github.com/slint-ui/slint/tree/master/examples

### Slint + Tokio Integration

- **Discussion**: https://github.com/slint-ui/slint/discussions/4377
- **Pattern**: Use `slint::spawn_local()` for UI thread, `slint::invoke_from_event_loop()` for callbacks
- **Best Practice**: Tokio on background thread, communicate via channels

### Fluent Design System

- **Official Guidelines**: https://fluent2.microsoft.design/
- **Design Tokens**: https://fluent2.microsoft.design/design-tokens
- **Components**: https://fluent2.microsoft.design/components
- **Accessibility**: https://fluent2.microsoft.design/accessibility

### CLASSIC Architecture

- **CLAUDE.md**: Project guidelines and Rust workspace structure
- **Rust Documentation**: `docs/RUST_DOCUMENTATION_INDEX.md`
- **Core Crates**: Use `-core` crates for all business logic

## Success Criteria

1. ✅ **Feature parity** (all functionality implemented) - PRIMARY GOAL
2. ✅ **Modern Fluent Design** (polished, professional dark theme)
3. ✅ **Performance targets met** (10x improvement minimum)
4. ✅ **Zero crashes or panics** in normal use
5. ✅ **Settings migration** works automatically
6. ✅ **File watcher** is reliable and responsive
7. ✅ **Markdown rendering** is accurate and fast
8. ✅ **Accessibility** (WCAG AA compliance, keyboard navigation)
9. ✅ **Window geometry persists** correctly
10. ✅ **Compiles on Windows** with no warnings

## Conclusion

This implementation plan provides a comprehensive roadmap for building a modern Slint-based GUI with **Fluent Design** that achieves **feature parity** with the Python/PySide6 interface while delivering a superior native Windows experience. By leveraging Rust's performance (10-150x speedups), Microsoft's Fluent Design System, and the existing `-core` business logic crates, we can create a polished, professional desktop application.

**Key Advantages:**
- **Feature Parity**: All Python GUI functionality maintained
- **Modern Design**: Fluent Design System with Windows 11 native feel
- **Performance**: 10-150x faster operations with Rust acceleration
- **Native Experience**: Better OS integration, smaller memory footprint
- **Maintainability**: Clean separation of UI (.slint) and logic (Rust)

The 11-week timeline is ambitious but achievable with focused development. The modular architecture ensures that each phase can be completed independently, and the clear separation between UI (.slint) and logic (Rust) maintains code quality and testability throughout the project.

**Next Steps:**
1. Review this plan with stakeholders
2. Create `classic-gui-slint` crate
3. Begin Phase 1: Project Setup & Basic Window
4. Set up CI/CD for automated builds and tests