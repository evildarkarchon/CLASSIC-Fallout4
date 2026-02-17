# CLASSIC Ratatui TUI - Product Requirements Document

**Version:** 1.0
**Date:** February 2026
**Target Framework:** ratatui 0.30+ / crossterm 0.28+ (Rust)
**Status:** Draft
**Inspired By:** CLASSIC Qt 6 GUI (`classic-gui/`)

---

## 1. Executive Summary

### 1.1 Purpose

This document specifies the requirements for a Rust-native Terminal User Interface for CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker), built with the **ratatui** immediate-mode TUI framework. The TUI provides full feature parity with the Qt 6 C++ GUI while running entirely in the terminal with mouse support, scroll-wheel navigation, and alternate-buffer rendering.

### 1.2 Goals

- **Full feature parity** with the Qt 6 GUI (`classic-gui/`)
- **Pure Rust implementation** — direct crate dependencies, no FFI overhead
- **Mouse-first + Keyboard-first** — all features accessible via both input methods
- **Scroll-wheel support** — especially in the results viewer for navigating large reports
- **Alternate-buffer rendering** — preserves terminal history on exit
- **Shared core crates** — reuses the same business logic as the Slint GUI
- **Cross-platform** — Windows primary (CI target), with Linux/macOS support via Crossterm

### 1.3 Non-Goals

- Replacing the Slint GUI or Qt GUI (this is an additional UI target)
- Web or mobile rendering
- GPU-accelerated rendering (terminal-only)
- Image or icon display (Unicode symbols used instead)
- Drag-and-drop file operations

### 1.4 Terminology

| Term | Definition |
|------|-----------|
| **TUI** | Terminal User Interface |
| **Alternate buffer** | Terminal feature where the app renders to a separate screen buffer; original terminal content is restored on exit |
| **Immediate-mode** | Rendering paradigm where the entire UI is redrawn from state each frame (no persistent widget tree) |
| **Raw mode** | Terminal mode where input is delivered unbuffered and unechoed |
| **Hit-testing** | Checking if mouse coordinates fall within a widget's rendered area |

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     CLASSIC Ratatui TUI App                          │
│                  (classic-tui crate, binary)                         │
├──────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Main Tab  │ │ Backup   │ │ Articles │ │ Results  │ │ Settings │ │
│  │           │ │ Tab      │ │ Tab      │ │ Tab      │ │ (Overlay)│ │
│  └─────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│        │            │            │             │            │       │
├────────┴────────────┴────────────┴─────────────┴────────────┴───────┤
│                     State Management Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐                 │
│  │  AppState     │  │  InputMode   │  │  Overlay   │                │
│  │  (all fields) │  │  (focus mgr) │  │  (modals)  │                │
│  └──────┬───────┘  └──────────────┘  └────────────┘                 │
├─────────┴───────────────────────────────────────────────────────────┤
│                     Async Task Layer (Tokio)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ ScanTask     │  │ GameFiles    │  │ Papyrus      │               │
│  │ (crash logs) │  │ Task         │  │ Monitor Task │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
├─────────┴────────────────┴──────────────────┴───────────────────────┤
│                 Rust Core Crates (direct dependency)                │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐           │
│  │classic-scanlog │ │classic-yaml    │ │classic-file-io │           │
│  │-core           │ │-core           │ │-core           │           │
│  ├────────────────┤ ├────────────────┤ ├────────────────┤           │
│  │classic-config  │ │classic-database│ │classic-update  │           │
│  │-core           │ │-core           │ │-core           │           │
│  ├────────────────┤ ├────────────────┤ ├────────────────┤           │
│  │classic-shared  │ │classic-registry│ │classic-papyrus │           │
│  │-core           │ │-core           │ │-core           │           │
│  └────────────────┘ └────────────────┘ └────────────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Crate Location & Structure

The TUI lives in the Rust workspace alongside the Slint GUI:

```
ClassicLib-rs/ui-applications/classic-tui/
├── Cargo.toml
├── src/
│   ├── main.rs              # Entry point, terminal setup, event loop
│   ├── app.rs               # App struct, state, top-level dispatch
│   ├── event.rs             # Event handling (key, mouse, resize, tick)
│   ├── ui.rs                # Top-level render function, layout
│   │
│   ├── tabs/
│   │   ├── mod.rs
│   │   ├── main_tab.rs      # Main options tab (paths, scan buttons)
│   │   ├── backup_tab.rs    # File backup tab (4 categories)
│   │   ├── articles_tab.rs  # Resource links tab (3x3 grid)
│   │   └── results_tab.rs   # Results tab (list + viewer)
│   │
│   ├── overlays/
│   │   ├── mod.rs
│   │   ├── settings.rs      # Settings overlay (4 sub-tabs)
│   │   ├── about.rs         # About overlay
│   │   ├── help.rs          # Help overlay (shortcuts reference)
│   │   ├── papyrus.rs       # Papyrus monitor overlay
│   │   ├── confirm.rs       # Confirmation dialog
│   │   └── path_setup.rs    # First-run path detection
│   │
│   ├── widgets/
│   │   ├── mod.rs
│   │   ├── path_input.rs    # Path input with browse button
│   │   ├── toggle_switch.rs # Toggle switch for settings
│   │   ├── scan_button.rs   # Morphing scan/cancel button
│   │   ├── status_bar.rs    # Bottom status bar with progress
│   │   ├── markdown.rs      # Markdown renderer (styled blocks)
│   │   └── scrollable.rs    # Scrollable text with mouse wheel
│   │
│   ├── state.rs             # WindowState, persistence, settings
│   ├── scan.rs              # Scan orchestration (crash logs + game files)
│   ├── backup.rs            # Backup operations
│   ├── papyrus.rs           # Papyrus monitoring task
│   ├── update.rs            # Update checking
│   ├── markdown.rs          # Markdown parsing → styled blocks
│   ├── input.rs             # Text input state machine
│   └── theme.rs             # Color palette, style constants
└── tests/
    ├── render_tests.rs       # TestBackend snapshot tests
    ├── event_tests.rs        # Input handling tests
    └── integration_tests.rs  # Full workflow tests
```

### 2.3 Workspace Integration

```toml
# ClassicLib-rs/Cargo.toml (workspace)
[workspace]
members = [
    # ... existing crates ...
    "ui-applications/classic-tui",
]
```

```toml
# ClassicLib-rs/ui-applications/classic-tui/Cargo.toml
[package]
name = "classic-tui"
version = "0.1.0"
edition = "2024"
rust-version = "1.85.0"

[[bin]]
name = "classic-tui"
path = "src/main.rs"

[dependencies]
# TUI framework
ratatui = "0.30"
crossterm = "0.28"

# Core CLASSIC crates (direct, no FFI)
classic-shared-core = { path = "../../foundation/classic-shared-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-config-core = { path = "../../business-logic/classic-config-core" }
classic-file-io-core = { path = "../../business-logic/classic-file-io-core" }
classic-database-core = { path = "../../business-logic/classic-database-core" }
classic-registry-core = { path = "../../business-logic/classic-registry-core" }
classic-update-core = { path = "../../business-logic/classic-update-core" }
classic-papyrus-core = { path = "../../business-logic/classic-papyrus-core" }

# Async
tokio = { version = "1", features = ["full"] }
tokio-util = { version = "0.7", features = ["rt"] }

# Utilities
arboard = "3.2"           # Clipboard
color-eyre = "0.6"        # Error handling + panic hooks
tracing = "0.1"           # Logging
tracing-appender = "0.2"  # File logging
pulldown-cmark = "0.12"   # Markdown parsing
serde = { version = "1", features = ["derive"] }
serde_json = "1"          # Window state persistence
serde_yaml = "0.9"        # Settings persistence
directories = "5"         # Platform paths
open = "5"                # Open URLs/folders in default app

# Companion TUI crates
tui-input = "0.11"        # Single-line text input widget
throbber-widgets-tui = "0.7" # Spinner for indeterminate progress

[lints.rust]
unsafe_code = "deny"

[lints.clippy]
all = { level = "deny", priority = -1 }
```

### 2.4 Threading Model

The TUI follows the ONE RUNTIME RULE, sharing the Tokio runtime with all core crates:

```
┌─────────────────────────────────────────────────────┐
│  Main Thread (UI)                                    │
│  ┌───────────────────────────────────────────────┐   │
│  │  Event Loop:                                   │   │
│  │    1. Poll crossterm events (16ms timeout)     │   │
│  │    2. Check mpsc channels for async results    │   │
│  │    3. Update AppState                          │   │
│  │    4. Render frame (ratatui immediate-mode)    │   │
│  └───────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────┤
│  Tokio Runtime (classic_shared::get_runtime())       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │ Scan Task   │  │ GameFiles    │  │ Papyrus      ││
│  │             │  │ Task         │  │ Monitor      ││
│  │ Sends:      │  │ Sends:       │  │ Sends:       ││
│  │ Progress(%) │  │ Progress(%)  │  │ Stats(...)   ││
│  │ Complete()  │  │ Complete()   │  │              ││
│  │ Error(msg)  │  │ Error(msg)   │  │              ││
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘│
│         │                │                 │        │
│         └────────────────┴─────────────────┘        │
│                      via mpsc::Sender                │
│                      to UI thread                    │
└──────────────────────────────────────────────────────┘
```

**Channel Communication:**

```rust
enum AsyncMessage {
    // Scan progress
    ScanProgress { percent: f64, status: String },
    ScanComplete(ScanResult),
    ScanError(String),

    // Game files progress
    GameFilesProgress { percent: f64, status: String },
    GameFilesComplete { output: String, has_errors: bool, total_checks: usize },
    GameFilesError(String),

    // Papyrus monitoring
    PapyrusStats(PapyrusStatsData),
    PapyrusError(String),

    // Update check
    UpdateResult(UpdateCheckResult),

    // Backup operations
    BackupComplete(String),
    BackupError(String),
}
```

---

## 3. Terminal Setup & Lifecycle

### 3.1 Startup Sequence

```rust
fn main() -> color_eyre::Result<()> {
    // 1. Install panic hooks (restores terminal on panic)
    color_eyre::install()?;

    // 2. Initialize file-based logging
    let _guard = init_logging();

    // 3. Initialize Tokio runtime (ONE RUNTIME RULE)
    let runtime = classic_shared::get_runtime();

    // 4. Enter alternate screen + raw mode + mouse capture
    crossterm::execute!(
        std::io::stderr(),
        EnterAlternateScreen,
        EnableMouseCapture,
    )?;
    crossterm::terminal::enable_raw_mode()?;

    // 5. Create ratatui terminal
    let backend = CrosstermBackend::new(std::io::stderr());
    let mut terminal = Terminal::new(backend)?;

    // 6. Load persisted state (settings + window state)
    let app = App::new()?;

    // 7. Run event loop
    let result = app.run(&mut terminal, runtime);

    // 8. Restore terminal (always, even on error)
    crossterm::terminal::disable_raw_mode()?;
    crossterm::execute!(
        std::io::stderr(),
        DisableMouseCapture,
        LeaveAlternateScreen,
    )?;

    result
}
```

### 3.2 Event Loop

```rust
impl App {
    fn run(mut self, terminal: &mut Terminal<impl Backend>, runtime: &Runtime) -> Result<()> {
        let (tx, rx) = mpsc::unbounded_channel::<AsyncMessage>();
        self.async_tx = Some(tx);

        while !self.should_quit {
            // 1. Render
            terminal.draw(|frame| self.render(frame))?;

            // 2. Drain async messages (non-blocking)
            while let Ok(msg) = rx.try_recv() {
                self.handle_async_message(msg);
            }

            // 3. Poll terminal events with timeout (60 FPS target)
            if crossterm::event::poll(Duration::from_millis(16))? {
                let event = crossterm::event::read()?;
                self.handle_event(event);
            }

            // 4. Tick-based updates (auto-clear status, animations)
            self.tick();
        }

        // Save state on exit
        self.save_state()?;
        Ok(())
    }
}
```

### 3.3 Panic Safety

The `color-eyre` panic hook ensures terminal restoration even on panic:

```rust
// color_eyre::install() sets up:
// 1. Panic hook that calls disable_raw_mode() + LeaveAlternateScreen
// 2. Rich error reports with backtraces
// 3. Eyre hook for ? operator error chains
```

### 3.4 Windows Considerations

**Critical:** On Windows, Crossterm sends both `KeyEventKind::Press` and `KeyEventKind::Release` events. All key handlers must filter for `Press` only:

```rust
Event::Key(key) if key.kind == KeyEventKind::Press => {
    self.handle_key(key);
}
```

**Output Target:** Use `stderr()` (not `stdout()`) for the terminal backend. This allows piping stdout for CLI interop while the TUI renders on stderr.

---

## 4. Application State

### 4.1 Core State Structure

```rust
struct App {
    // Navigation
    active_tab: TabIndex,         // 0=Main, 1=Backup, 2=Articles, 3=Results
    active_overlay: Option<Overlay>,  // Settings, Help, About, Papyrus, PathSetup, Confirm

    // Main tab state
    staging_mods_input: InputState,
    custom_scan_input: InputState,
    main_focus: MainFocus,        // Which element has focus

    // Backup tab state
    backup_selected_row: usize,   // 0-3 (XSE, ReShade, Vulkan, ENB)
    backup_statuses: [BackupStatus; 4],

    // Articles tab state
    articles_selected: usize,     // 0-8 (3x3 grid, row-major)

    // Results tab state
    results: ResultsState,        // See §4.3

    // Settings state (overlay)
    settings: SettingsState,      // See §4.4

    // Scan state
    scan_in_progress: bool,
    scan_type: Option<ScanType>,  // CrashLogs or GameFiles
    scan_progress: f64,           // -1.0 = indeterminate, 0-100 = determinate
    scan_status: String,

    // Papyrus state
    papyrus_active: bool,
    papyrus_stats: PapyrusStatsData,

    // Status bar
    status_message: String,
    status_clear_at: Option<Instant>,  // Auto-clear after 5 seconds

    // Update check
    update_checking: bool,
    update_result: Option<UpdateCheckResult>,

    // Async communication
    async_tx: Option<mpsc::UnboundedSender<AsyncMessage>>,
    cancel_token: Option<CancellationToken>,

    // Lifecycle
    should_quit: bool,
    initialized: bool,

    // Persisted state
    config: ClassicConfig,
    window_state: WindowState,
}
```

### 4.2 Tab Index

```rust
#[derive(Clone, Copy, PartialEq, Eq)]
enum TabIndex {
    MainOptions = 0,
    FileBackup = 1,
    Articles = 2,
    Results = 3,
}

impl TabIndex {
    const NAMES: [&'static str; 4] = ["Main Options", "File Backup", "Articles", "Results"];
    fn next(self) -> Self { /* wrapping increment */ }
    fn prev(self) -> Self { /* wrapping decrement */ }
}
```

### 4.3 Results State

```rust
struct ResultsState {
    // Report list (left panel)
    reports: Vec<ReportEntry>,
    filtered_reports: Vec<usize>,     // Indices into `reports` after search filter
    list_state: ListState,            // ratatui list selection state
    search_query: String,
    search_input: InputState,
    sort_ascending: bool,

    // Report viewer (right panel)
    selected_report: Option<PathBuf>,
    report_content: String,           // Raw markdown content
    rendered_blocks: Vec<StyledBlock>, // Parsed markdown blocks
    scroll_offset: usize,             // Vertical scroll position
    scrollbar_state: ScrollbarState,
    total_lines: usize,               // Total rendered lines (for scroll bounds)
    viewport_height: usize,           // Visible area height (updated each frame)

    // Splitter
    list_panel_width: u16,            // Persisted width of left panel

    // Metadata
    report_date: String,
    report_size: String,

    // Empty state
    has_results: bool,
}
```

### 4.4 Settings State

```rust
struct SettingsState {
    active_sub_tab: SettingsSubTab,  // General, Scanning, Paths, Updates

    // General sub-tab
    game_version_index: usize,      // 0=Auto, 1=Original, 2=NextGen, 3=VR
    fcx_mode: bool,

    // Scanning sub-tab
    simplify_logs: bool,
    show_formid_values: bool,
    move_unsolved_logs: bool,
    auto_switch_after_scan: bool,
    max_concurrent_scans: u32,      // 0 = auto

    // Paths sub-tab
    ini_folder_input: InputState,
    ini_folder_error: Option<String>,
    formid_databases: Vec<PathBuf>,
    formid_selected: Option<usize>,

    // Updates sub-tab
    update_check_on_startup: bool,
    update_status_message: String,

    // Reset confirmation
    reset_confirm_visible: bool,

    // Dirty tracking
    has_unsaved_changes: bool,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum SettingsSubTab {
    General = 0,
    Scanning = 1,
    Paths = 2,
    Updates = 3,
}
```

### 4.5 Input State

For text input fields, using `tui-input` or a custom state:

```rust
struct InputState {
    value: String,
    cursor: usize,
    focused: bool,
}
```

---

## 5. Screen Layout

### 5.1 Top-Level Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CLASSIC v9.0.0                                                          │
├───────────────┬───────────────┬───────────────┬──────────────────────────┤
│ Main Options  │ File Backup   │  Articles     │  Results                 │
├───────────────┴───────────────┴───────────────┴──────────────────────────┤
│                                                                          │
│                         [Active Tab Content]                             │
│                                                                          │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Ready                                                    ░░░░░░░░░░ 0%  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Layout Constraints:**

```rust
let [title_area, tabs_area, content_area, status_area] = Layout::vertical([
    Constraint::Length(1),      // Title bar
    Constraint::Length(1),      // Tab bar
    Constraint::Min(10),        // Tab content (fills remaining)
    Constraint::Length(1),      // Status bar + progress
]).areas(frame.area());
```

### 5.2 Title Bar (1 row)

```
 CLASSIC v9.0.0                           F1:Help  Ctrl+O:Settings  Q:Quit
```

- Left: Application name + version
- Right: Key hint strip (context-sensitive)

### 5.3 Tab Bar (1 row)

Uses ratatui `Tabs` widget:

```rust
let tabs = Tabs::new(TabIndex::NAMES.to_vec())
    .select(self.active_tab as usize)
    .highlight_style(Style::default().fg(ACCENT_BLUE).bold())
    .divider(" │ ");
```

**Mouse interaction:** Click on a tab name to switch tabs. Hit-test against each tab label's rendered position.

### 5.4 Status Bar (1 row)

```
 Scanning: 45% - Processing crash-2026-01-29.log    ████████████░░░░░░░ 45%
```

Layout: Status text (left, fills) + progress gauge (right, fixed width 20).

**Progress modes:**
- **Idle:** "Ready" + empty gauge
- **Indeterminate:** Animated throbber (`throbber-widgets-tui`) + status text
- **Determinate:** `Gauge` widget with percentage + status text
- **Auto-clear:** Status message reverts to "Ready" after 5 seconds post-completion

---

## 6. Tab Specifications

### 6.1 Main Options Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Staging Mods Folder:                                                    │
│  ┌──────────────────────────────────────────────────────┐ ┌────────────┐ │
│  │ C:\Games\Fallout4\Mods                               │ │  Browse    │ │
│  └──────────────────────────────────────────────────────┘ └────────────┘ │
│                                                                          │
│  Custom Scan Folder:                                                     │
│  ┌──────────────────────────────────────────────────────┐ ┌────────────┐ │
│  │ C:\CrashLogs\Custom                                   │ │  Browse    │ │
│  └──────────────────────────────────────────────────────┘ └────────────┘ │
│                                                                          │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐                              │
│  │ SCAN CRASH LOGS  │  │ SCAN GAME FILES  │                              │
│  └──────────────────┘  └──────────────────┘                              │
│                                                                          │
│                                                                          │
│  ┌───────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ About │ │ Help     │ │ Settings   │ │ Open Logs    │ │ Check Update│ │
│  └───────┘ └──────────┘ └────────────┘ └──────────────┘ └─────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ START PAPYRUS MONITORING                                    [OFF]   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

**Layout:**

```rust
let [paths_area, _spacer1, scan_buttons_area, _spacer2, utility_row1, utility_row2, papyrus_area]
    = Layout::vertical([
        Constraint::Length(7),     // Two path inputs (label + input each)
        Constraint::Fill(1),       // Flexible spacer
        Constraint::Length(3),     // Scan buttons
        Constraint::Fill(1),       // Flexible spacer
        Constraint::Length(3),     // Utility buttons row 1
        Constraint::Length(1),     // Spacing
        Constraint::Length(3),     // Papyrus toggle
    ]).areas(content_area);
```

**Components:**

1. **Path Input Widget** (reusable)
   - Label text above
   - Text input field (editable, supports paste)
   - Browse button (opens OS folder dialog via `rfd` or displays TUI path browser)
   - Validation: green border if valid directory, red if invalid, default if empty
   - Click to focus input; Tab to move to Browse button
   - Persists to YAML on change (debounced)

2. **Scan Buttons**
   - "SCAN CRASH LOGS" — primary style (blue background)
   - "SCAN GAME FILES" — primary style (blue background)
   - Both disabled during active scan, text changes to "SCANNING..."
   - Click or Enter to activate
   - Morphing pattern: during scan, button text changes to "CANCEL" with secondary styling

3. **Utility Buttons Row**
   - About, Help, Settings, Open Crash Logs, Check Updates
   - Horizontal layout with equal spacing
   - Click or Enter to activate
   - "Check Updates" shows "CHECKING..." while active

4. **Papyrus Monitor Toggle**
   - Full-width button with ON/OFF indicator
   - When ON: green highlight, text "STOP PAPYRUS MONITORING"
   - When OFF: default style, text "START PAPYRUS MONITORING"
   - Opens Papyrus overlay when activated

**Custom Scan Folder Validation Rules** (matching Qt GUI):
1. Empty is valid (clears setting)
2. Must exist and be a directory
3. Cannot be Windows system directories (Program Files, Windows, System32)
4. Cannot be inside or equal to Crash Logs folder
5. Invalid paths show error in status bar

**Mouse Interactions:**
- Click text input to focus and position cursor
- Click Browse button to trigger folder selection
- Click scan/utility buttons to activate
- Click Papyrus toggle to start/stop

**Keyboard Navigation:**
- Tab/Shift+Tab: cycle through focusable elements
- Enter: activate focused button or confirm input
- Escape: unfocus text input

### 6.2 File Backup Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      BACKUP / RESTORE / REMOVE                           │
│                                                                          │
│  Manage backups for game modification files.                             │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Type            │ Status      │ Backup    │ Restore   │ Remove      │ │
│  ├─────────────────┼─────────────┼───────────┼───────────┼─────────────┤ │
│  │ Script Extender │ ✓ Exists    │ [Backup]  │ [Restore] │  [Remove]   │ │
│  │ ReShade         │ ○ None      │ [Backup]  │     -     │     -       │ │
│  │ Vulkan          │ ○ None      │ [Backup]  │     -     │     -       │ │
│  │ ENB             │ ✓ Exists    │ [Backup]  │ [Restore] │  [Remove]   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      OPEN CLASSIC BACKUPS                            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

**Implementation:** Uses ratatui `Table` widget with `TableState` for row selection.

**Columns:**
| Column | Width | Content |
|--------|-------|---------|
| Type | 20 chars | Backup category name |
| Status | 12 chars | "✓ Exists" (green) or "○ None" (dim) |
| Backup | 10 chars | Always clickable |
| Restore | 10 chars | Clickable only if backup exists, else "-" (dim) |
| Remove | 10 chars | Clickable only if backup exists, else "-" (dim) |

**4 Backup Categories:**
1. Script Extender (XSE/F4SE)
2. ReShade
3. Vulkan
4. ENB

**Mouse Interactions:**
- Click a row to select it
- Click action buttons (Backup/Restore/Remove) to trigger operation
- Click "OPEN CLASSIC BACKUPS" to open folder in file explorer

**Keyboard:**
- Up/Down arrows: select row
- B: Backup selected type
- R: Restore selected type (if backup exists)
- D: Remove selected backup (with confirmation)
- O: Open backup folder

**Confirmation Dialog:** Destructive operations (Remove) show a confirmation overlay:
```
┌─────────────────────────────────────┐
│  Remove ENB backup?                 │
│                                     │
│  This will delete all backed up     │
│  ENB files permanently.             │
│                                     │
│     [Yes, Remove]    [Cancel]       │
└─────────────────────────────────────┘
```

### 6.3 Articles Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       USEFUL RESOURCES & LINKS                           │
│                                                                          │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐ │
│  │ BUFFOUT 4           │ │ FALLOUT 4           │ │ IMPORTANT           │ │
│  │ INSTALLATION        │ │ SETUP TIPS          │ │ PATCHES LIST        │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘ │
│                                                                          │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐ │
│  │ BUFFOUT 4           │ │ CLASSIC             │ │ CLASSIC             │ │
│  │ NEXUS               │ │ NEXUS               │ │ GITHUB              │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘ │
│                                                                          │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐ │
│  │ DDS TEXTURE         │ │ BETHINI             │ │ WRYE                │ │
│  │ SCANNER             │ │ PIE                 │ │ BASH                │ │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘ │
│                                                                          │
│  Press Enter or click to open in browser                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Implementation:** 3x3 grid of bordered buttons, each linked to a URL.

**Link Data** (hardcoded, matches Qt GUI exactly):

| Index | Label | URL |
|-------|-------|-----|
| 0 | BUFFOUT 4 INSTALLATION | https://www.nexusmods.com/fallout4/articles/3115 |
| 1 | FALLOUT 4 SETUP TIPS | https://www.nexusmods.com/fallout4/articles/4141 |
| 2 | IMPORTANT PATCHES LIST | https://www.nexusmods.com/fallout4/articles/3769 |
| 3 | BUFFOUT 4 NEXUS | https://www.nexusmods.com/fallout4/mods/47359 |
| 4 | CLASSIC NEXUS | https://www.nexusmods.com/fallout4/mods/56255 |
| 5 | CLASSIC GITHUB | https://github.com/evildarkarchon/CLASSIC-Fallout4 |
| 6 | DDS TEXTURE SCANNER | https://www.nexusmods.com/fallout4/mods/71588 |
| 7 | BETHINI PIE | https://www.nexusmods.com/site/mods/631 |
| 8 | WRYE BASH | https://www.nexusmods.com/fallout4/mods/20032 |

**Navigation:**
- Arrow keys move selection in 2D grid (wrapping)
- Enter or click opens URL in default browser via `open::that()`
- Selected item highlighted with accent color border

**Mouse:** Click any button to open its URL.

### 6.4 Results Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Filter: [_______________]                   │ crash-2026-01-29-AUTOSCAN │
│ ────────────────────────                    │ Date: 2026-01-29 15:42    │
│ Report ▼                                    │ Size: 12.4 KB             │
│ ─────────────────────────                   ├───────────────────────────┤
│ ► crash-2026-01-29-AUTO                     │ [Copy All]                │
│   crash-2026-01-28-AUTO                     ├───────────────────────────┤
│   crash-2026-01-27-AUTO                     │ # Crash Log Analysis      │
│   crash-2026-01-25-AUTO                     │                           │
│   GameFiles-2026-01-24                      │ **Scan Date:** 2026-01-29 │
│                                             │ **Game:** Fallout 4       │
│                                             │                           │
│                                             │ ## Summary                │
│                                             │                           │
│                                             │ Found 3 potential issues: │
│                                             │ - Missing F4SE plugin     │
│                                             │ - Outdated mod version    │
│                                             │ - Script conflict         │
│                                             │                           │
│                                             │ ## Detailed Analysis      │
│                                             │ ...                       │
│ ─────────────────────────                   │                          █│
│ [Refresh] [Delete] [Open]                   │                          ░│
└──────────────────────────────────────────────────────────────────────────┘
```

**This is the most complex tab.** It mirrors the Qt GUI's horizontal splitter layout.

**Layout:**

```rust
let [left_panel, right_panel] = Layout::horizontal([
    Constraint::Length(self.results.list_panel_width),  // Resizable, default 30
    Constraint::Min(30),                                // Viewer fills rest
]).areas(content_area);
```

#### 6.4.1 Left Panel: Report List

**Components (top to bottom):**
1. **Search/Filter Input** — `tui-input` widget, real-time substring filtering
2. **Sort Header** — "Report ▲" or "Report ▼", clickable to toggle sort direction
3. **Report List** — ratatui `List` with `ListState`, scrollable, selectable
4. **Action Buttons** — Refresh, Delete, Open Folder

**List Items:**
- Display: Filename (truncated with elide) + timestamp on second line (dim)
- Selected: Highlighted background (#404060)
- Selection triggers report loading in viewer

**Search Behavior:**
- Case-insensitive substring match on filename
- Real-time filtering as user types
- Auto-selects first match
- Empty search shows all reports

**Sort Behavior:**
- Toggle ascending/descending by filename
- Visual indicator: ▲ (ascending) or ▼ (descending)
- Click sort header or press `S` to toggle

**Action Buttons:**
- **Refresh [F5]:** Rescan report directories, rebuild list
- **Delete [Del]:** Delete selected report (with confirmation overlay)
- **Open Folder [O]:** Open crash logs directory in file explorer

#### 6.4.2 Right Panel: Report Viewer

**Components (top to bottom):**
1. **Metadata Bar** — Filename, date (extracted from filename), file size
2. **Toolbar** — Copy All button (right-aligned)
3. **Markdown Viewer** — Scrollable styled text content
4. **Scrollbar** — Vertical scrollbar (right edge)

**Markdown Rendering:**

The markdown parser converts CommonMark content into styled terminal blocks using `pulldown-cmark`:

| Block Type | Rendering | Style |
|-----------|-----------|-------|
| Heading (H1) | Text | Bold, Cyan, 22px equivalent (all-caps or underlined) |
| Heading (H2) | Text | Bold, White |
| Heading (H3) | Text | Bold, Gray |
| Paragraph | Text | Default, word-wrapped |
| Bold text | Text | Bold modifier |
| Italic text | Text | Italic modifier (terminal-dependent) |
| Code block | Text | Dark background (#2a2a2e), monospace |
| Horizontal rule | Line | Dim "─" repeated across width |
| List item (depth 1) | Text | "• " prefix |
| List item (depth 2) | Text | "  ◦ " prefix (indented) |
| List item (depth 3+) | Text | "    ■ " prefix (double-indented) |
| Blockquote | Text | "│ " prefix (dim), italic |

**Scroll-Wheel Support (KEY REQUIREMENT):**

```rust
// Mouse scroll events in results viewer
Event::Mouse(MouseEvent {
    kind: MouseEventKind::ScrollDown,
    column, row, ..
}) if viewer_area.contains(Position::new(column, row)) => {
    self.results.scroll_offset = self.results.scroll_offset
        .saturating_add(3);  // 3 lines per scroll tick
    self.results.clamp_scroll();
}

Event::Mouse(MouseEvent {
    kind: MouseEventKind::ScrollUp,
    column, row, ..
}) if viewer_area.contains(Position::new(column, row)) => {
    self.results.scroll_offset = self.results.scroll_offset
        .saturating_sub(3);
}
```

**Keyboard scrolling:**
- Up/Down: 1 line
- PageUp/PageDown: viewport height
- Home/End: top/bottom of document

**Copy All:**
- Copies raw markdown content to clipboard via `arboard`
- Status bar shows "Copied to clipboard" for 3 seconds

#### 6.4.3 Empty State

When no reports are available:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                        No scan results                                   │
│                                                                          │
│                  Run a scan to see results here                          │
│                                                                          │
│                     [Scan Crash Logs]                                    │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

Centered vertically and horizontally. The "Scan Crash Logs" button switches to the Main tab when clicked.

#### 6.4.4 Report Discovery

Reports are discovered from these directories (matching Qt GUI):

1. **Primary:** Crash Logs folder (from settings or default `./Crash Logs`)
2. **Custom:** Custom Scan Folder (if configured)

Files matched: `*.md` (all markdown files in these directories)

Sort: Newest-first by filename timestamp extraction (pattern: `YYYY-MM-DD_HH-MM-SS`)

**File Watching:**
- Poll-based: Check for new/changed files every 2 seconds via tick handler
- Auto-refresh on detection of changes
- Maintains current selection if possible

---

## 7. Overlay Specifications

Overlays are modal dialogs rendered on top of the current tab content. They capture all input until dismissed.

### 7.1 About Overlay

```
┌───────────────────────────────────────┐
│               About                   │
├───────────────────────────────────────┤
│                                       │
│              CLASSIC                  │
│                                       │
│  Crash Log Auto Scanner &             │
│  Setup Integrity Checker              │
│                                       │
│  Version: 9.0.0                       │
│                                       │
│  Developed by evildarkarchon          │
│  Based on the original by Poet        │
│  Credits: wxMichael, kittivelae,      │
│           AtomicFallout757            │
│                                       │
│  github.com/evildarkarchon/           │
│    CLASSIC-Fallout4                   │
│                                       │
│           [Close (Esc)]               │
└───────────────────────────────────────┘
```

**Size:** Centered, 40 chars wide, auto height.
**Dismiss:** Esc, Enter, or click Close button.

### 7.2 Help Overlay

```
┌──────────────────────────────────────────────────────────────────┐
│                          Help                                     │
├────────────────┬─────────────────┬──────────────────┬────────────┤
│  Shortcuts     │  Usage          │  Features        │            │
├────────────────┴─────────────────┴──────────────────┴────────────┤
│                                                                   │
│  Global Shortcuts                                                 │
│  ─────────────────────────────────────────                        │
│  F1            Show this help                                     │
│  F5            Run crash logs scan                                │
│  F6            Run game files scan                                │
│  F7            Toggle Papyrus monitor                             │
│  Ctrl+O        Open settings                                     │
│  Tab/S-Tab     Navigate between elements                          │
│  1-4           Switch to tab by number                            │
│  Q / Ctrl+C    Quit application                                   │
│                                                                   │
│  Results Tab                                                      │
│  ─────────────────────────────────────────                        │
│  ↑/↓           Select report                                     │
│  Scroll Wheel  Scroll report content                              │
│  Ctrl+A        Copy all report content                            │
│  Del           Delete selected report                             │
│  S             Toggle sort order                                  │
│  /             Focus search filter                                │
│                                                                   │
│  Backup Tab                                                       │
│  ─────────────────────────────────────────                        │
│  ↑/↓           Select backup type                                │
│  B             Backup selected                                    │
│  R             Restore selected                                   │
│  D             Remove selected backup                             │
│                                                                   │
│                       [Close (Esc)]                               │
└──────────────────────────────────────────────────────────────────┘
```

**Size:** Centered, 70 chars wide, 80% of terminal height.
**Sub-tabs:** Shortcuts, Usage, Features (ratatui `Tabs` widget within overlay).
**Scrollable:** Content scrolls if it exceeds visible area.

### 7.3 Settings Overlay

```
┌──────────────────────────────────────────────────────────────────┐
│                         Settings                                  │
├────────────────┬──────────────┬──────────────┬───────────────────┤
│  General       │  Scanning    │  Paths       │  Updates          │
├────────────────┴──────────────┴──────────────┴───────────────────┤
│                                                                   │
│  Game Version:    [▸ Auto            ▾]                           │
│                                                                   │
│  FCX Mode:        [ ] Off                                         │
│                                                                   │
│                                                                   │
│                                                                   │
│                                                                   │
│                                                                   │
│                                                                   │
│                                                                   │
│                                                                   │
├───────────────────────────────────────────────────────────────────┤
│  [Reset to Defaults]                          [Cancel]    [OK]    │
└──────────────────────────────────────────────────────────────────┘
```

**Size:** Centered, 70 chars wide, 60% of terminal height.
**4 Sub-tabs** (matching Qt GUI's SettingsDialog):

#### General Sub-tab
| Setting | Widget | YAML Key | Default |
|---------|--------|----------|---------|
| Game Version | Dropdown (cycle on Enter/click) | `Game Version` | "Auto" |
| FCX Mode | Toggle [X]/[ ] | `FCX Mode` | false |

#### Scanning Sub-tab
| Setting | Widget | YAML Key | Default |
|---------|--------|----------|---------|
| Simplify Logs | Toggle | `Simplify Logs` | false |
| Show FormID Values | Toggle | `Show FormID Values` | false |
| Move Unsolved Logs | Toggle | `Move Unsolved Logs` | false |
| Auto Switch After Scan | Toggle | `Auto Switch After Scan` | true |
| Max Concurrent Scans | Number input (0-32) | `Max Concurrent Scans` | 0 (auto) |

#### Paths Sub-tab
| Setting | Widget | YAML Key | Default |
|---------|--------|----------|---------|
| INI Folder | Path input + Browse | `INI Folder Path` | "" (auto-detect) |
| FormID Databases | List + Add/Remove | `FormID Databases.{Game}` | [] |

FormID Database list:
- Shows added database file paths
- "Add..." button opens file dialog (filter: `*.db`, `*.sqlite`)
- Remove button deletes selected entry
- Built-in database is always included (noted in help text)

#### Updates Sub-tab
| Setting | Widget | YAML Key | Default |
|---------|--------|----------|---------|
| Check on Startup | Toggle | `Update Check` | true |
| Check Now | Button | N/A | N/A |

"Check Now" button:
- Disabled during check, text shows "Checking..."
- Result shown as status text below button
- Uses Rust `classic-update-core` directly

#### Footer Buttons
- **Reset to Defaults:** Shows inline confirmation "Reset ALL settings? [Yes] [Cancel]"
- **Cancel:** Discard changes, close overlay
- **OK:** Save all settings to YAML, emit settings changed, close overlay

**Settings Persistence:**
- All settings saved via `classic-config-core`
- Full config save on OK (matching Slint GUI's save-on-each-change adapted for modal pattern)
- Loaded from YAML on app startup

### 7.4 Papyrus Monitor Overlay

```
┌─────────────────────────────────────────┐
│          PAPYRUS LOG MONITOR            │
├─────────────────────────────────────────┤
│                                         │
│  Dumps:            0                    │
│  Stacks:           0                    │
│  Warnings:         0                    │
│  Errors:           0                    │
│  Lines Processed:  0                    │
│  Dumps/Stacks:     0.00                 │
│                                         │
│  Status: Monitoring...                  │
│                                         │
│         [STOP MONITORING]               │
└─────────────────────────────────────────┘
```

**Size:** Centered, 42 chars wide, auto height.
**Non-blocking:** Unlike other overlays, the Papyrus monitor keeps polling in the background. However, it captures input focus.
**Update Rate:** Stats refresh every 1 second via async channel message.
**Key Metric:** The Dumps/Stacks ratio gives script developers a direct measure of VM health — a high ratio indicates scripts are failing frequently relative to total stack activity.

**Dismiss:** Click "STOP MONITORING" or press Esc → stops monitoring and closes overlay.

### 7.5 Path Setup Overlay (First Run)

```
┌──────────────────────────────────────────────────────────────────┐
│              CLASSIC - Path Setup                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CLASSIC could not automatically detect some required paths.     │
│  Please provide the following:                                    │
│                                                                   │
│  Game Folder Path:                                                │
│  ┌──────────────────────────────────────────────┐ ┌────────────┐ │
│  │ C:\...\steamapps\common\Fallout 4             │ │  Browse    │ │
│  └──────────────────────────────────────────────┘ └────────────┘ │
│                                                                   │
│  Documents / INI Folder Path:                                     │
│  ┌──────────────────────────────────────────────┐ ┌────────────┐ │
│  │ C:\Users\...\Documents\My Games\Fallout4      │ │  Browse    │ │
│  └──────────────────────────────────────────────┘ └────────────┘ │
│                                                                   │
│                              [Cancel]    [OK]                     │
└──────────────────────────────────────────────────────────────────┘
```

**Trigger:** Shown on startup if game folder or documents path cannot be auto-detected.
**Conditional sections:** Only shows fields that couldn't be auto-detected.

### 7.6 Confirmation Overlay

```
┌─────────────────────────────────────┐
│  Delete report?                     │
│                                     │
│  crash-2026-01-29-AUTOSCAN.md       │
│  will be permanently deleted.       │
│                                     │
│       [Yes]         [Cancel]        │
└─────────────────────────────────────┘
```

**Generic confirmation dialog** used for:
- Delete report
- Remove backup
- Reset settings to defaults

---

## 8. Mouse Interaction Specification

### 8.1 Mouse Events Handled

| Event | Context | Action |
|-------|---------|--------|
| `Left Click` | Tab bar | Switch to clicked tab |
| `Left Click` | Button widget | Activate button |
| `Left Click` | Text input | Focus input, position cursor |
| `Left Click` | List item | Select item |
| `Left Click` | Table row | Select row |
| `Left Click` | Articles grid button | Open URL in browser |
| `Left Click` | Sort header | Toggle sort direction |
| `Left Click` | Overlay backdrop | Close overlay (optional) |
| `ScrollUp` | Results viewer | Scroll up 3 lines |
| `ScrollDown` | Results viewer | Scroll down 3 lines |
| `ScrollUp` | Report list | Scroll list up |
| `ScrollDown` | Report list | Scroll list down |
| `ScrollUp` | Help overlay content | Scroll help text up |
| `ScrollDown` | Help overlay content | Scroll help text down |

### 8.2 Hit-Testing Pattern

Since ratatui is immediate-mode, widget areas must be stored during rendering for mouse event processing:

```rust
struct ClickAreas {
    tab_areas: Vec<Rect>,           // One per tab label
    buttons: HashMap<String, Rect>, // Named button areas
    list_items: Vec<Rect>,          // Report list items
    table_rows: Vec<Rect>,          // Backup table rows
    articles_grid: Vec<Rect>,       // Article button areas
    viewer_area: Rect,              // Results viewer scroll area
    sort_header: Rect,              // Sort toggle area
}
```

Updated each frame during `render()`, consumed during `handle_event()`.

### 8.3 Cursor Shapes

The terminal cursor is hidden during normal operation (`crossterm::cursor::Hide`). Cursor is shown only when a text input is focused.

---

## 9. Keyboard Shortcut Summary

### 9.1 Global Shortcuts (always active unless overlay captures input)

| Key | Action |
|-----|--------|
| `F1` | Open Help overlay |
| `F5` | Start crash logs scan (or Refresh in Results tab) |
| `F6` | Start game files scan |
| `F7` | Toggle Papyrus monitoring |
| `Ctrl+O` | Open Settings overlay |
| `Q` | Quit (when not focused on text input) |
| `Ctrl+C` | Quit |
| `1` | Switch to Main Options tab |
| `2` | Switch to File Backup tab |
| `3` | Switch to Articles tab |
| `4` | Switch to Results tab |
| `Tab` | Next focusable element |
| `Shift+Tab` | Previous focusable element |
| `Esc` | Close overlay / unfocus input / cancel |

### 9.2 Main Tab Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Activate focused button or confirm input |
| `Tab` | Cycle focus: Mods Input → Browse → Scan Input → Browse → Scan Crash → Scan Game → Utility buttons → Papyrus |

### 9.3 Backup Tab Shortcuts

| Key | Action |
|-----|--------|
| `↑/↓` | Select backup type row |
| `B` | Backup selected type |
| `R` | Restore selected type |
| `D` | Remove selected backup (with confirmation) |
| `O` | Open backup folder |

### 9.4 Articles Tab Shortcuts

| Key | Action |
|-----|--------|
| `↑/↓/←/→` | Navigate 3x3 grid |
| `Enter` | Open selected link in browser |

### 9.5 Results Tab Shortcuts

| Key | Action |
|-----|--------|
| `↑/↓` | Select report in list (when list focused) |
| `↑/↓` | Scroll viewer 1 line (when viewer focused) |
| `PageUp/PageDown` | Scroll viewer by page |
| `Home/End` | Scroll to top/bottom of viewer |
| `Scroll Wheel` | Scroll viewer 3 lines per tick |
| `Ctrl+A` | Copy all report content to clipboard |
| `Del` | Delete selected report |
| `/` | Focus search filter |
| `S` | Toggle sort direction |
| `Enter` | Load selected report (when list focused) |
| `F5` | Refresh report list |
| `O` | Open crash logs folder |
| `Left/Right` or `Tab` | Switch focus between list and viewer panels |

### 9.6 Overlay Shortcuts

| Key | Action |
|-----|--------|
| `Esc` | Close overlay / Cancel |
| `Enter` | Activate focused button or confirm |
| `Tab/Shift+Tab` | Navigate within overlay |
| `1-4` | Switch sub-tab (in Settings/Help) |

---

## 10. Visual Design

### 10.1 Color Palette

```rust
mod theme {
    use ratatui::style::Color;

    // Core colors
    pub const BG_PRIMARY: Color = Color::Rgb(30, 30, 30);       // #1e1e1e
    pub const BG_SURFACE: Color = Color::Rgb(45, 45, 45);       // #2d2d2d
    pub const BG_ELEVATED: Color = Color::Rgb(60, 60, 60);      // #3c3c3c
    pub const BG_OVERLAY: Color = Color::Rgb(20, 20, 20);       // #141414

    // Text
    pub const TEXT_PRIMARY: Color = Color::Rgb(224, 224, 224);   // #e0e0e0
    pub const TEXT_MUTED: Color = Color::Rgb(136, 136, 136);     // #888888
    pub const TEXT_DIM: Color = Color::Rgb(102, 102, 102);       // #666666

    // Accent
    pub const ACCENT_BLUE: Color = Color::Rgb(0, 120, 212);     // #0078d4 (Windows blue)
    pub const ACCENT_BLUE_LIGHT: Color = Color::Rgb(74, 158, 255); // #4a9eff

    // Semantic
    pub const SUCCESS: Color = Color::Rgb(46, 125, 50);         // #2E7D32
    pub const WARNING: Color = Color::Rgb(255, 193, 7);         // #ffc107
    pub const ERROR: Color = Color::Rgb(255, 107, 107);         // #ff6b6b
    pub const ERROR_BG: Color = Color::Rgb(220, 53, 69);        // #dc3545

    // Selection
    pub const SELECTED_BG: Color = Color::Rgb(64, 64, 96);      // #404060

    // Code blocks
    pub const CODE_BG: Color = Color::Rgb(42, 42, 46);          // #2a2a2e

    // Borders
    pub const BORDER_DEFAULT: Color = Color::Rgb(85, 85, 85);   // #555555
    pub const BORDER_FOCUS: Color = ACCENT_BLUE;
    pub const BORDER_VALID: Color = SUCCESS;
    pub const BORDER_INVALID: Color = ERROR;
}
```

### 10.2 Border Style

Use `BorderType::Rounded` for all panels and overlays (matches the modern Qt GUI aesthetic):

```rust
Block::bordered()
    .border_type(BorderType::Rounded)
    .border_style(Style::default().fg(theme::BORDER_DEFAULT))
    .title("Panel Title")
```

### 10.3 Button Rendering

Since ratatui has no built-in button widget, buttons are rendered as bordered text blocks:

```rust
fn render_button(label: &str, focused: bool, primary: bool, area: Rect, buf: &mut Buffer) {
    let (fg, bg, border) = if primary {
        (Color::White, theme::ACCENT_BLUE, theme::ACCENT_BLUE)
    } else if focused {
        (theme::TEXT_PRIMARY, theme::BG_ELEVATED, theme::BORDER_FOCUS)
    } else {
        (theme::TEXT_PRIMARY, theme::BG_SURFACE, theme::BORDER_DEFAULT)
    };

    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(border))
        .style(Style::default().bg(bg));

    let text = Paragraph::new(label)
        .alignment(Alignment::Center)
        .style(Style::default().fg(fg).bold());

    text.block(block).render(area, buf);
}
```

### 10.4 Toggle Switch Rendering

```
  FCX Mode:         [■] On     or    [ ] Off
```

Rendered as inline text with styled checkbox character:
- Checked: `[■]` in green/accent color + "On" text
- Unchecked: `[ ]` in dim color + "Off" text

### 10.5 Minimum Terminal Size

- **Minimum:** 80 columns x 24 rows
- **Recommended:** 120 columns x 40 rows
- If terminal is smaller than minimum, show a centered message: "Terminal too small. Minimum: 80x24"

---

## 11. Scan Workflows

### 11.1 Crash Log Scan Workflow

1. User clicks "SCAN CRASH LOGS" or presses F5
2. **Pre-scan validation:**
   - Validate CLASSIC Data directory exists
   - Ensure CLASSIC Settings.yaml exists (create from template if missing)
   - Ensure CLASSIC Ignore.yaml exists (create from template if missing)
3. **UI state change:**
   - `scan_in_progress = true`
   - Button morphs to "CANCEL" (secondary style)
   - Both path inputs disabled
   - Status bar: "Discovering crash logs..." + indeterminate throbber
4. **Spawn async task** on Tokio runtime:
   ```rust
   let tx = self.async_tx.clone().unwrap();
   let cancel_token = CancellationToken::new();
   self.cancel_token = Some(cancel_token.clone());

   get_runtime().spawn(async move {
       // Discovery phase
       tx.send(AsyncMessage::ScanProgress {
           percent: -1.0,
           status: "Discovering crash logs...".into(),
       }).ok();

       let log_paths = LogCollector::discover(&crash_log_path).await?;

       // Analysis phase
       for (i, path) in log_paths.iter().enumerate() {
           if cancel_token.is_cancelled() {
               tx.send(AsyncMessage::ScanComplete(ScanResult::cancelled(i, log_paths.len()))).ok();
               return Ok(());
           }

           let percent = ((i + 1) as f64 / log_paths.len() as f64) * 100.0;
           tx.send(AsyncMessage::ScanProgress {
               percent,
               status: format!("Scanning: {}", path.file_name()),
           }).ok();

           // Process via classic-scanlog-core
           orchestrator.analyze_log(&path).await?;
       }

       // Report writing phase
       tx.send(AsyncMessage::ScanProgress {
           percent: -1.0,
           status: "Writing reports...".into(),
       }).ok();

       let reports = orchestrator.write_reports().await?;
       tx.send(AsyncMessage::ScanComplete(ScanResult::success(reports))).ok();
   });
   ```
5. **Progress updates** arrive via mpsc channel, update status bar
6. **On completion:**
   - Status bar: "Scanned N logs" (or with error count)
   - `scan_in_progress = false`
   - Button morphs back to "SCAN CRASH LOGS"
   - If `auto_switch_after_scan` enabled: switch to Results tab
   - Auto-select first report
   - Status auto-clears after 5 seconds
7. **On cancellation:**
   - User clicks "CANCEL" or presses Esc during scan
   - `cancel_token.cancel()` called
   - Status: "Cancelled (X of Y logs)"
   - Partial results preserved

### 11.2 Game Files Scan Workflow

1. User clicks "SCAN GAME FILES" or presses F6
2. **Pre-scan validation:**
   - Read Game Folder Path from settings
   - Read Game EXE Path from settings
   - Show error if game folder not configured
3. **Spawn async task** (similar to crash logs but using `GameFilesManager`)
4. **On completion:**
   - Generate markdown report: `GameFiles-YYYY-MM-DD_HH-MM-SS-AUTOSCAN.md`
   - Write to Crash Logs folder
   - Status: "Game files scan completed: N checks" (or "errors found")
   - Auto-switch to Results tab

### 11.3 Update Check Workflow

1. User clicks "Check Updates" button
2. Button disabled, text "CHECKING..."
3. Status bar: "Checking for updates..."
4. **Spawn async task:**
   ```rust
   get_runtime().spawn(async move {
       let result = classic_update_core::check_github_update(
           "evildarkarchon",
           "CLASSIC-Fallout4",
           current_version,
       ).await;
       tx.send(AsyncMessage::UpdateResult(result)).ok();
   });
   ```
5. **Results:**
   - Update available: Status shows "Update available: vX.Y.Z"
   - Up to date: Status shows "You are up to date"
   - Error: Status shows "Update check failed"
6. Button re-enabled

---

## 12. Configuration & Persistence

### 12.1 Settings File

**Location:** Shared with other CLASSIC UIs
**Format:** YAML (via `classic-config-core`)
**File:** `CLASSIC Settings.yaml` in CLASSIC Data directory

All settings keys match the Qt GUI and Slint GUI exactly (see §7.3 for mapping table).

### 12.2 TUI-Specific State File

**Location:** `~/.config/classic-tui/state.json` (via `directories` crate)
**Format:** JSON

```json
{
    "active_tab": 0,
    "results_panel_width": 30,
    "sort_ascending": false
}
```

This is minimal — only TUI-specific layout preferences. Application settings are shared via YAML.

### 12.3 Logging

**Location:** `~/.local/share/classic-tui/classic-tui.log` (via `directories` crate)
**Library:** `tracing` + `tracing-appender`
**Behavior:** Truncated on each launch (not appended)
**Required because:** stderr is used for TUI rendering, so log output cannot go to stderr

---

## 13. Testing Strategy

### 13.1 Unit Tests (Rust)

Using ratatui's `TestBackend` for render verification:

```rust
#[test]
fn test_main_tab_renders() {
    let backend = TestBackend::new(120, 40);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new_for_testing();

    terminal.draw(|frame| app.render(frame)).unwrap();

    // Assert specific cells or use snapshot testing
    let buffer = terminal.backend().buffer();
    // ... assertions ...
}
```

### 13.2 Snapshot Testing

Using `insta` crate for golden-file snapshots of rendered buffers:

```rust
#[test]
fn test_results_tab_with_reports() {
    let mut app = App::new_for_testing();
    app.results.reports = vec![/* mock data */];
    app.active_tab = TabIndex::Results;

    let buffer = render_to_buffer(&mut app, 120, 40);
    insta::assert_snapshot!(buffer_to_string(&buffer));
}
```

### 13.3 Event Handling Tests

```rust
#[test]
fn test_tab_switching_via_number_keys() {
    let mut app = App::new_for_testing();
    assert_eq!(app.active_tab, TabIndex::MainOptions);

    app.handle_key(KeyEvent::new(KeyCode::Char('3'), KeyModifiers::NONE));
    assert_eq!(app.active_tab, TabIndex::Articles);
}

#[test]
fn test_scroll_wheel_in_results_viewer() {
    let mut app = App::new_for_testing();
    app.results.scroll_offset = 10;

    app.handle_mouse(MouseEvent {
        kind: MouseEventKind::ScrollDown,
        column: 60, row: 15,
        modifiers: KeyModifiers::NONE,
    });

    assert_eq!(app.results.scroll_offset, 13); // +3 lines per tick
}
```

### 13.4 Integration Tests

Full workflow tests with mock core crates:
- Start scan → receive progress → view results
- Settings change → verify YAML persistence
- Backup → verify file operations

### 13.5 Test Markers

```rust
// In Cargo.toml
[features]
test-utils = []  # Enables mock implementations for testing
```

---

## 14. Accessibility

### 14.1 Keyboard-First Design

Every feature is accessible via keyboard. Mouse is an enhancement, not a requirement.

### 14.2 Focus Indicators

Focused elements always have a visual indicator:
- Input fields: border color changes to accent blue
- Buttons: border color changes to accent blue
- List items: highlighted background
- Tab bar: active tab in bold accent color

### 14.3 Color Contrast

All text colors meet WCAG AA contrast ratios against their backgrounds:
- Primary text (#e0e0e0) on dark background (#1e1e1e): ratio ~12:1
- Muted text (#888888) on dark background (#1e1e1e): ratio ~4.5:1
- Error text (#ff6b6b) on dark background (#1e1e1e): ratio ~5:1

### 14.4 Terminal Compatibility

The TUI should work in:
- Windows Terminal (primary target)
- PowerShell / cmd.exe (basic functionality)
- Alacritty, WezTerm, iTerm2 (full feature support)
- SSH sessions (keyboard-only, no mouse)
- tmux/screen (with appropriate TERM settings)

---

## 15. Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Startup time | < 500ms | Includes state loading, no scan |
| Frame render time | < 5ms | 60 FPS target (16ms budget) |
| Input latency | < 16ms | Immediate response to key/mouse |
| Memory (idle) | < 20MB | No scan results loaded |
| Memory (scan) | < 100MB | 1000 logs scanned |
| Status bar update | Per-log | Real-time during scan |
| Report list filter | < 10ms | For < 1000 reports |
| Markdown render | < 50ms | For 500-block reports |

---

## 16. Dependencies Summary

### 16.1 Direct Crate Dependencies

| Crate | Purpose | Version |
|-------|---------|---------|
| `ratatui` | TUI framework | 0.30 |
| `crossterm` | Terminal backend (input, raw mode, alternate screen) | 0.28 |
| `tokio` | Async runtime (shared via ONE RUNTIME RULE) | 1.x |
| `tokio-util` | CancellationToken for scan cancellation | 0.7 |
| `color-eyre` | Error handling + panic hooks (terminal restoration) | 0.6 |
| `arboard` | Clipboard (copy report content) | 3.2 |
| `pulldown-cmark` | Markdown parsing to styled blocks | 0.12 |
| `tui-input` | Text input widget | 0.11 |
| `throbber-widgets-tui` | Animated spinner for indeterminate progress | 0.7 |
| `tracing` | Structured logging | 0.1 |
| `tracing-appender` | File-based log output | 0.2 |
| `serde` / `serde_json` | TUI state persistence | 1.x |
| `directories` | Platform-appropriate config/data paths | 5.x |
| `open` | Open URLs and folders in default application | 5.x |

### 16.2 CLASSIC Core Crate Dependencies

All from the existing workspace (no new crates needed):

| Crate | Purpose |
|-------|---------|
| `classic-shared-core` | Tokio runtime, string interning, caching |
| `classic-scanlog-core` | Crash log parsing and analysis |
| `classic-yaml-core` | YAML settings loading/caching |
| `classic-config-core` | Configuration management |
| `classic-file-io-core` | File I/O, encoding detection, backups |
| `classic-database-core` | FormID database operations |
| `classic-registry-core` | Game registry, path detection |
| `classic-update-core` | GitHub version checking |
| `classic-papyrus-core` | Papyrus log analysis |

---

## 17. Implementation Phases

### Phase 1: Foundation
- [ ] Crate setup in workspace
- [ ] Terminal lifecycle (alternate buffer, raw mode, mouse capture, panic hooks)
- [ ] Event loop with 60 FPS target
- [ ] App state skeleton
- [ ] Top-level layout (title bar, tab bar, content area, status bar)
- [ ] Tab switching (keyboard 1-4 + mouse click)
- [ ] Theme/color constants
- [ ] File-based logging

### Phase 2: Main Options Tab
- [ ] Path input widget (text input, validation, browse button)
- [ ] Scan buttons (with morphing cancel state)
- [ ] Utility button row (About, Help, Settings, Open Logs, Check Updates)
- [ ] Papyrus toggle button
- [ ] Focus management (Tab/Shift+Tab cycling)
- [ ] Mouse click handling for all buttons

### Phase 3: Scan Integration
- [ ] Async scan task (crash logs) via mpsc channel
- [ ] Progress reporting (indeterminate + determinate)
- [ ] Cancellation via CancellationToken
- [ ] Status bar progress display (Gauge + throbber)
- [ ] Auto-clear status after 5 seconds
- [ ] Game files scan integration

### Phase 4: Results Tab
- [ ] Report discovery and list population
- [ ] Report list with ListState (selection, scrolling)
- [ ] Search/filter input (real-time)
- [ ] Sort toggle (ascending/descending)
- [ ] Markdown parser (pulldown-cmark → styled blocks)
- [ ] Scrollable viewer with Paragraph::scroll()
- [ ] **Scroll-wheel support** (mouse wheel → scroll offset)
- [ ] Scrollbar widget (visual indicator)
- [ ] Copy All to clipboard
- [ ] Report metadata display
- [ ] Delete report with confirmation
- [ ] Refresh / Open Folder buttons
- [ ] Auto-switch after scan
- [ ] Empty state
- [ ] File watching (poll-based, 2-second interval)

### Phase 5: Settings Overlay
- [ ] Overlay rendering (centered, bordered, on top of tab content)
- [ ] 4 sub-tabs with content
- [ ] Toggle switches for boolean settings
- [ ] Dropdown for Game Version
- [ ] Path input for INI folder
- [ ] FormID database list (add/remove)
- [ ] Number input for Max Concurrent Scans
- [ ] Reset to Defaults with inline confirmation
- [ ] OK/Cancel save flow
- [ ] Settings persistence via classic-config-core

### Phase 6: Supporting Overlays
- [ ] About overlay
- [ ] Help overlay (with sub-tabs for Shortcuts/Usage/Features)
- [ ] Confirmation overlay (generic)
- [ ] Path Setup overlay (first-run)
- [ ] Papyrus monitor overlay with live stats

### Phase 7: Backup Tab
- [ ] Backup table with TableState
- [ ] Status indicators (✓/○)
- [ ] Backup/Restore/Remove operations
- [ ] Confirmation for destructive operations
- [ ] Open Backup Folder button
- [ ] Status bar feedback

### Phase 8: Articles Tab
- [ ] 3x3 grid layout
- [ ] Arrow key navigation
- [ ] Mouse click to open URL
- [ ] Highlight selected item

### Phase 9: Polish & Integration
- [ ] Update check integration
- [ ] Papyrus monitoring integration
- [ ] Path validation matching Qt GUI rules
- [ ] Custom Scan Folder validation (system dir check, crash logs dir check)
- [ ] Terminal resize handling
- [ ] Minimum size guard
- [ ] Edge cases (empty states, error recovery)

### Phase 10: Testing & Release
- [ ] Unit tests (render + event handling)
- [ ] Snapshot tests (TestBackend + insta)
- [ ] Integration tests (full workflows)
- [ ] CI integration (ci-rust.yml)
- [ ] Build documentation
- [ ] README/changelog updates

---

## 18. Build & Run Commands

```bash
# Build
cargo build -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml

# Build (release)
cargo build -p classic-tui --release --manifest-path ClassicLib-rs/Cargo.toml

# Run
cargo run -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml

# Test
cargo test -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml

# Test with output
cargo test -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture
```

---

## 19. Feature Parity Matrix (vs Qt GUI)

| Feature | Qt GUI | Ratatui TUI | Notes |
|---------|--------|-------------|-------|
| **Main Tab** | | | |
| Staging Mods Folder input | ✓ | ✓ | Text input + browse |
| Custom Scan Folder input + validation | ✓ | ✓ | Same validation rules |
| Scan Crash Logs button | ✓ | ✓ | Morphing cancel |
| Scan Game Files button | ✓ | ✓ | Morphing cancel |
| About button/dialog | ✓ | ✓ | Overlay |
| Help button/dialog | ✓ | ✓ | Overlay with sub-tabs |
| Settings button/dialog | ✓ | ✓ | Overlay with 4 sub-tabs |
| Open Crash Logs button | ✓ | ✓ | Opens in file explorer |
| Check Updates button | ✓ | ✓ | Background async |
| Papyrus Monitor toggle + dialog | ✓ | ✓ | Toggle + non-modal overlay |
| Exit button | ✓ | ✓ | Q key / button |
| **Backup Tab** | | | |
| 4 backup categories | ✓ | ✓ | Table widget |
| Backup/Restore/Remove per category | ✓ | ✓ | Keyboard + mouse |
| Status indicators | ✓ | ✓ | ✓/○ text symbols |
| Open Backups folder | ✓ | ✓ | Opens in file explorer |
| **Articles Tab** | | | |
| 3x3 resource link grid | ✓ | ✓ | 9 buttons |
| Open in browser | ✓ | ✓ | via `open::that()` |
| **Results Tab** | | | |
| Report list with search | ✓ | ✓ | List + filter input |
| Sort toggle | ✓ | ✓ | ▲/▼ header |
| Markdown viewer | ✓ | ✓ | Styled blocks |
| Scroll-wheel support | ✓ | ✓ | **Key requirement** |
| Scrollbar | ✓ | ✓ | ratatui Scrollbar |
| Copy All to clipboard | ✓ | ✓ | arboard |
| Zoom controls | ✓ | ✗ | N/A in terminal (fixed font) |
| Report metadata | ✓ | ✓ | Date, file size |
| Refresh / Delete / Open Folder | ✓ | ✓ | Buttons + shortcuts |
| File watching auto-refresh | ✓ | ✓ | Poll-based (2s) |
| Auto-switch after scan | ✓ | ✓ | Configurable |
| Splitter (resizable panels) | ✓ | Partial | Fixed width (persisted) — no drag |
| **Settings** | | | |
| Game Version dropdown | ✓ | ✓ | Cycle widget |
| FCX Mode toggle | ✓ | ✓ | Toggle switch |
| Simplify Logs toggle | ✓ | ✓ | Toggle switch |
| Show FormID Values toggle | ✓ | ✓ | Toggle switch |
| Move Unsolved Logs toggle | ✓ | ✓ | Toggle switch |
| Auto Switch After Scan toggle | ✓ | ✓ | Toggle switch |
| Max Concurrent Scans spinner | ✓ | ✓ | Number input |
| INI Folder path input | ✓ | ✓ | Text input + browse |
| FormID Databases list | ✓ | ✓ | List + add/remove |
| Check for Updates on Startup toggle | ✓ | ✓ | Toggle switch |
| Check Now button | ✓ | ✓ | Button |
| Reset to Defaults | ✓ | ✓ | Inline confirmation |
| **Dialogs** | | | |
| About dialog | ✓ | ✓ | Overlay |
| Settings dialog (4 tabs) | ✓ | ✓ | Overlay + sub-tabs |
| Path detection dialog | ✓ | ✓ | First-run overlay |
| Papyrus monitor dialog | ✓ | ✓ | Non-modal overlay |
| Error dialogs | ✓ | ✓ | Status bar messages |
| Confirmation dialogs | ✓ | ✓ | Overlay |
| **Infrastructure** | | | |
| Status bar with progress | ✓ | ✓ | Gauge + throbber |
| Dark theme | ✓ | ✓ | Matching color palette |
| Window geometry persistence | ✓ | Partial | Tab + panel width only |
| Settings persistence (YAML) | ✓ | ✓ | Shared with all UIs |
| Background threading | ✓ | ✓ | Tokio (shared runtime) |
| File-based logging | ✓ | ✓ | tracing + appender |
| Mouse support | ✓ | ✓ | Full Crossterm mouse events |
| Keyboard navigation | ✓ | ✓ | Comprehensive shortcuts |

**Notable differences from Qt GUI:**
1. **No zoom controls** — terminal has fixed-size characters; users zoom via terminal settings
2. **No draggable splitter** — panel width is adjustable but persisted, not drag-interactive
3. **No per-tab window geometry** — terminal size is controlled by the terminal emulator
4. **Unicode symbols instead of icons** — ✓, ○, •, ▲, ▼ replace graphical icons
5. **Alternate buffer** — preserves terminal history (Qt GUI is a window that simply closes)

---

## Appendix A: Data Flow Diagram

```
User Input (Keyboard / Mouse)
         │
         ▼
┌─────────────────────┐
│  crossterm::event   │  ← Poll with 16ms timeout
│  ::read()           │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│  App::handle_event  │────▶│  App state mutation  │
│  (dispatch by tab   │     │  (immediate-mode)    │
│   and overlay)      │     └──────────┬───────────┘
└─────────────────────┘                │
                                       ▼
                              ┌─────────────────────┐
                              │  App::render(frame)  │  ← Every 16ms
                              │  (full redraw)       │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │  Terminal output     │
                              │  (diff-based write)  │
                              └─────────────────────┘

Async Tasks (Tokio) ──── mpsc::channel ────▶ App::handle_async_message()
```

---

## Appendix B: File Locations

| Resource | Location | Format |
|----------|----------|--------|
| Binary | `ClassicLib-rs/target/{debug,release}/classic-tui` | Executable |
| TUI State | `~/.config/classic-tui/state.json` | JSON |
| App Settings | `{CLASSIC Data}/CLASSIC Settings.yaml` | YAML (shared) |
| Log File | `~/.local/share/classic-tui/classic-tui.log` | Text |
| Crash Logs | User-configured or `./Crash Logs/` | Directory |
| Reports | Same as crash logs directory | `*.md` files |

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **ratatui** | Rust TUI framework (immediate-mode rendering) |
| **crossterm** | Cross-platform terminal manipulation library |
| **Alternate buffer** | Secondary terminal screen buffer (preserves shell history) |
| **Raw mode** | Terminal mode with unbuffered, unechoed input |
| **Immediate-mode** | UI paradigm where widgets are recreated each frame from state |
| **Hit-testing** | Checking if mouse coordinates fall within a widget's area |
| **CancellationToken** | Tokio primitive for cooperative task cancellation |
| **mpsc** | Multi-producer, single-consumer channel for async→UI communication |
| **ONE RUNTIME RULE** | Project convention: single shared Tokio runtime |
| **AsyncBridge** | Pattern for bridging async Tokio tasks to UI thread updates |

---

*End of Document*
