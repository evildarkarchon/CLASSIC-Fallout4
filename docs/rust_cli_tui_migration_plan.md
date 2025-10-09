# Rust CLI & TUI Migration Implementation Plan

**Document Version:** 1.0
**Date:** 2025-10-08
**Status:** Planning Phase

## Executive Summary

This document outlines the comprehensive plan to migrate CLASSIC's Command-Line Interface (CLI) and Terminal User Interface (TUI) from Python to Rust. The migration aims to leverage Rust's performance, reduce Python startup overhead, and create standalone native executables with improved user experience.

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Goals and Success Criteria](#goals-and-success-criteria)
3. [Architecture Overview](#architecture-overview)
4. [Implementation Phases](#implementation-phases)
5. [Technical Specifications](#technical-specifications)
6. [Risk Analysis](#risk-analysis)
7. [Testing Strategy](#testing-strategy)
8. [Migration Timeline](#migration-timeline)

---

## Current State Analysis

### CLI Current Features (CLASSIC_ScanLogs.py)

**Entry Point:** `CLASSIC_ScanLogs.py`
- **Async-first architecture** using `asyncio.run()` at entry point
- **Command-line argument parsing**:
  - `--fcx-mode`: Enable FCX mode
  - `--show-fid-values`: Show FormID values
  - `--stat-logging`: Enable statistical logging
  - `--move-unsolved`: Move unsolved logs
  - `--ini-path`: Custom INI path
  - `--scan-path`: Custom scan directory
  - `--mods-folder-path`: Custom mods folder
  - `--simplify-logs`: Simplify log output

**Core Components:**
- `ScanLogsExecutor`: Main scan execution orchestration
- `OrchestratorCore`: Crash log processing pipeline
- `ScanConfig`: Configuration management
- `YamlSettingsCache`: YAML settings persistence

**Workflow:**
1. Parse CLI arguments → `parse_arguments()`
2. Create config from args → `create_config_from_args()`
3. Initialize executor → `ScanLogsExecutor(config)`
4. Execute async scan → `await executor.scan()`
5. Display summary → `executor.generate_summary()`
6. Pause for user input → `os.system("pause")`

### TUI Current Features (CLASSIC_TUI.py)

**Framework:** Textual (Python async TUI library)
**Entry Point:** `CLASSIC_TUI.py` → `CLASSICTuiApp`

#### Main Screen Features (`main_screen.py`):
- **Folder Selection**:
  - Staging mods folder selector
  - Custom scan folder selector
  - Path validation and persistence
- **Scan Operations**:
  - Crash Logs Scan button (F5/R)
  - Game Files Scan button (F6/G)
  - Papyrus Monitor toggle (F7/P)
- **Settings**:
  - Update check checkbox
- **Output Viewer**:
  - Scrollable text output
  - Search functionality (/)
  - Clear output (Ctrl+L)

#### Additional Screens:
- **Help Screen** (F1): Keyboard shortcuts and usage
- **Settings Screen** (Ctrl+O): Configuration management
- **Papyrus Screen** (F7/P): Real-time Papyrus log monitoring

#### Key Bindings:
- `q` / `Ctrl+C`: Quit
- `F1`: Help
- `F5` / `r`: Crash scan
- `F6` / `g`: Game scan
- `F7` / `p`: Papyrus monitor
- `Ctrl+L`: Clear output
- `Ctrl+O`: Settings
- `/`: Search
- Tab navigation support

#### TUI Architecture:
- **Async event loop** via Textual
- **Widget-based composition**: FolderSelector, ScanButton, OutputViewer, StatusBar
- **Message-based event handling**: Custom messages for scan start/completion
- **Handlers**: TuiScanHandler, TuiPapyrusHandler, MessageHandler
- **Reactive properties**: `staging_folder`, `custom_folder`

### GUI Main Tab Features (for TUI Parity Reference)

**From `TabSetupMixin.setup_main_tab()`:**
- Staging mods folder selection
- Custom scan folder selection (with validation)
- Main scan buttons:
  - Crash Logs Scan
  - Game Files Scan
  - Papyrus Monitor toggle
- Bottom utility buttons:
  - Help
  - Settings
  - Open Crash Logs Folder
  - Check for Updates

### Shared Backend Components (Already in Rust)

**Rust Acceleration Active in:**
- ✅ **classic-scanlog**: Log parsing, FormID analysis, pattern matching (~1500 LOC)
- ✅ **classic-file-io**: File I/O, encoding detection, DDS parsing
- ✅ **classic-database**: SQLite FormID lookups with connection pooling
- ✅ **classic-yaml**: YAML operations (yaml-rust2)
- ✅ **classic-shared**: Runtime, errors, utilities

**Performance Gains:**
| Component | Python Time | Rust Time | Speedup |
|-----------|-------------|-----------|---------|
| Log Parsing | 2-3s | 200-300ms | **10x** |
| FormID Analysis | 250ms/1000 IDs | 10ms/1000 IDs | **25x** |
| Pattern Matching | 100ms/scan | 5ms/scan | **20x** |
| File I/O | 50ms/file | 5ms/file | **10x** |

---

## Goals and Success Criteria

### Primary Goals

1. **Performance**: Achieve <500ms cold start time (vs 2-3s Python startup)
2. **Distribution**: Create single-binary executables for Windows
3. **Parity**: Match all CLI functionality and TUI Main tab features
4. **UX**: Improve responsiveness and reduce memory footprint
5. **Maintainability**: Cleaner architecture with Rust's type safety

### Success Criteria

#### CLI Success Metrics:
- ✅ All command-line arguments supported
- ✅ Configuration persistence via YAML
- ✅ Identical scan output format
- ✅ <500ms startup time
- ✅ <50MB binary size
- ✅ Windows executable with UPX compression

#### TUI Success Metrics:
- ✅ Main screen parity with Python TUI:
  - Folder selection widgets
  - Crash/Game scan buttons
  - Update check toggle
  - Output viewer with scroll
- ✅ Keyboard shortcuts functional
- ✅ Settings screen
- ✅ Help screen
- ✅ 60 FPS rendering
- ✅ <100MB memory usage
- ✅ Smooth async operation

#### Quality Metrics:
- ✅ 80%+ test coverage
- ✅ Zero unsafe code blocks
- ✅ Comprehensive error handling
- ✅ Cross-platform compatibility (Windows primary, Linux/macOS stretch)

---

## Architecture Overview

### Proposed Rust Crate Structure

```
classic-cli/          # New CLI application crate
├── src/
│   ├── main.rs       # CLI entry point
│   ├── args.rs       # Argument parsing (clap)
│   ├── config.rs     # Configuration management
│   ├── executor.rs   # Scan execution orchestration
│   └── output.rs     # Output formatting and display
└── Cargo.toml

classic-tui/          # New TUI application crate
├── src/
│   ├── main.rs       # TUI entry point
│   ├── app.rs        # Application state and event loop
│   ├── ui/
│   │   ├── mod.rs
│   │   ├── layout.rs      # Layout management
│   │   ├── main_screen.rs # Main screen implementation
│   │   ├── help_screen.rs # Help screen
│   │   └── settings_screen.rs # Settings screen
│   ├── widgets/
│   │   ├── mod.rs
│   │   ├── folder_selector.rs
│   │   ├── scan_button.rs
│   │   ├── output_viewer.rs
│   │   └── status_bar.rs
│   ├── handlers/
│   │   ├── mod.rs
│   │   ├── scan_handler.rs
│   │   └── input_handler.rs
│   └── events.rs     # Event definitions
└── Cargo.toml

classic-shared/       # Existing (enhance for CLI/TUI)
├── src/
│   ├── runtime.rs    # Global Tokio runtime
│   ├── errors.rs     # Error types
│   ├── paths.rs      # Path utilities
│   └── config.rs     # Shared config types
```

### Key Rust Dependencies

#### CLI Dependencies:
```toml
[dependencies]
clap = { version = "4.5", features = ["derive", "cargo"] }
tokio = { version = "1.47", features = ["full"] }
anyhow = "1.0"
classic-scanlog = { path = "../classic-scanlog" }
classic-file-io = { path = "../classic-file-io" }
classic-database = { path = "../classic-database" }
classic-yaml = { path = "../classic-yaml" }
classic-shared = { path = "../classic-shared" }
indicatif = "0.17"  # Progress bars
console = "0.15"    # Terminal utilities
```

#### TUI Dependencies:
```toml
[dependencies]
ratatui = "0.28"    # Modern TUI framework (fork of tui-rs)
crossterm = "0.28"  # Terminal manipulation
tokio = { version = "1.47", features = ["full"] }
anyhow = "1.0"
classic-scanlog = { path = "../classic-scanlog" }
classic-file-io = { path = "../classic-file-io" }
classic-database = { path = "../classic-database" }
classic-yaml = { path = "../classic-yaml" }
classic-shared = { path = "../classic-shared" }
tui-input = "0.9"   # Text input widgets
```

**Why Ratatui?**
- Modern, actively maintained (Textual-like for Rust)
- Async-friendly with tokio
- Rich widget ecosystem
- Excellent cross-platform support
- Used in production tools (gitui, bottom, etc.)

### Shared Configuration Layer

**Design**: Both CLI and TUI will use a shared `ClassicConfig` struct in `classic-shared`:

```rust
// classic-shared/src/config.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassicConfig {
    pub fcx_mode: bool,
    pub show_formid_values: bool,
    pub stat_logging: bool,
    pub move_unsolved_logs: bool,
    pub simplify_logs: bool,
    pub update_check: bool,
    pub paths: PathConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathConfig {
    pub ini_folder: Option<PathBuf>,
    pub scan_custom: Option<PathBuf>,
    pub mods_folder: Option<PathBuf>,
    pub game_root: PathBuf,
}

impl ClassicConfig {
    pub fn load_from_yaml(path: &Path) -> Result<Self>;
    pub fn save_to_yaml(&self, path: &Path) -> Result<()>;
    pub fn merge_cli_args(&mut self, args: &CliArgs);
}
```

---

## Implementation Phases

### Phase 1: CLI Foundation (Week 1-2)

**Goal**: Create functional CLI with argument parsing and basic scan execution.

#### Tasks:
1. **Create `classic-cli` crate**:
   - Set up Cargo.toml with dependencies
   - Create main.rs with basic structure

2. **Implement argument parsing** (`args.rs`):
   ```rust
   use clap::Parser;

   #[derive(Parser, Debug)]
   #[command(name = "classic")]
   #[command(about = "CLASSIC Crash Log Auto Scanner", long_about = None)]
   pub struct CliArgs {
       /// Enable FCX mode
       #[arg(long)]
       pub fcx_mode: Option<bool>,

       /// Show FormID values in output
       #[arg(long)]
       pub show_fid_values: Option<bool>,

       /// Enable statistical logging
       #[arg(long)]
       pub stat_logging: Option<bool>,

       /// Move unsolved logs to subfolder
       #[arg(long)]
       pub move_unsolved: Option<bool>,

       /// Path to INI folder
       #[arg(long, value_name = "PATH")]
       pub ini_path: Option<PathBuf>,

       /// Path to custom scan folder
       #[arg(long, value_name = "PATH")]
       pub scan_path: Option<PathBuf>,

       /// Path to mods folder
       #[arg(long, value_name = "PATH")]
       pub mods_folder_path: Option<PathBuf>,

       /// Simplify logs (may remove important info)
       #[arg(long)]
       pub simplify_logs: Option<bool>,
   }
   ```

3. **Configuration management** (`config.rs`):
   - Load YAML settings
   - Merge CLI args with saved config
   - Validate and persist settings

4. **Scan executor** (`executor.rs`):
   - Bridge to existing Rust backend
   - Call `classic-scanlog` components
   - Handle async scan orchestration

5. **Output formatting** (`output.rs`):
   - Match Python CLI output format
   - Progress indicators with `indicatif`
   - Summary statistics display

**Deliverable**: `classic-cli` binary that can execute crash scans with CLI args.

### Phase 2: CLI Polish & Integration (Week 3)

#### Tasks:
1. **Progress indicators**:
   - Multi-progress bar for parallel scans
   - Real-time statistics updates
   - Color-coded output (warnings, errors)

2. **Error handling**:
   - Graceful degradation
   - User-friendly error messages
   - Exit codes for scripting

3. **YAML integration**:
   - Settings persistence
   - Auto-detection of game paths
   - Configuration validation

4. **Testing**:
   - Unit tests for argument parsing
   - Integration tests with test data
   - Output format validation

**Deliverable**: Production-ready CLI with full feature parity.

### Phase 3: TUI Foundation (Week 4-5)

**Goal**: Create basic TUI with main screen and folder selection.

#### Tasks:
1. **Create `classic-tui` crate**:
   - Set up Cargo.toml with ratatui
   - Basic app structure with event loop

2. **App state management** (`app.rs`):
   ```rust
   pub struct App {
       config: ClassicConfig,
       ui_state: UiState,
       scan_state: ScanState,
       should_quit: bool,
   }

   pub enum UiState {
       MainScreen,
       HelpScreen,
       SettingsScreen,
   }

   pub enum ScanState {
       Idle,
       CrashScanning { progress: f64 },
       GameScanning { progress: f64 },
   }
   ```

3. **Main screen layout** (`ui/main_screen.rs`):
   - Top section: Folder selectors (2 rows)
   - Middle section: Scan buttons (horizontal)
   - Bottom section: Status bar
   - Central area: Output viewer (scrollable)

4. **Folder selector widget** (`widgets/folder_selector.rs`):
   - Label + text input + browse button
   - Path validation
   - Visual feedback (border colors)

5. **Event handling** (`handlers/input_handler.rs`):
   - Keyboard shortcuts (F5, F6, F7, etc.)
   - Focus management
   - Input validation

**Deliverable**: TUI with navigable main screen and folder selection.

### Phase 4: TUI Scan Operations (Week 6)

#### Tasks:
1. **Scan button widget** (`widgets/scan_button.rs`):
   - Visual states (idle, scanning, completed)
   - Click/keyboard activation
   - Progress indication

2. **Output viewer widget** (`widgets/output_viewer.rs`):
   - Scrollable text buffer (Vec<String>)
   - Line wrapping
   - Color support (ANSI)
   - Search functionality (/)

3. **Scan handler** (`handlers/scan_handler.rs`):
   - Async scan execution in background
   - Real-time output streaming
   - Progress updates via channels

   ```rust
   pub struct ScanHandler {
       tx: mpsc::Sender<ScanMessage>,
       handle: Option<JoinHandle<()>>,
   }

   pub enum ScanMessage {
       Progress(f64),
       Output(String),
       Completed(ScanResult),
       Error(String),
   }
   ```

4. **Status bar widget** (`widgets/status_bar.rs`):
   - Scan progress
   - Key hints
   - Stats display

**Deliverable**: Functional scan operations with real-time output.

### Phase 5: TUI Additional Screens (Week 7)

#### Tasks:
1. **Help screen** (`ui/help_screen.rs`):
   - Keyboard shortcuts table
   - Feature descriptions
   - Navigation instructions

2. **Settings screen** (`ui/settings_screen.rs`):
   - Checkbox widgets for boolean settings
   - Path input fields
   - Save/Cancel buttons

3. **Screen navigation**:
   - Screen stack management
   - Smooth transitions
   - Escape to return to previous screen

**Deliverable**: Complete screen navigation and settings management.

### Phase 6: Testing & Optimization (Week 8)

#### Tasks:
1. **Comprehensive testing**:
   - Unit tests for all widgets
   - Integration tests for workflows
   - Performance benchmarks
   - Memory leak checks

2. **Performance optimization**:
   - Render optimization (only dirty regions)
   - Output buffering strategies
   - Async task management

3. **Cross-platform testing**:
   - Windows primary focus
   - Linux/macOS validation
   - Terminal compatibility matrix

4. **Documentation**:
   - User guides (CLI and TUI)
   - Developer documentation
   - Migration guide for users

**Deliverable**: Production-ready CLI and TUI with comprehensive docs.

### Phase 7: Distribution & Deployment (Week 9)

#### Tasks:
1. **Build optimization**:
   - Release builds with LTO
   - Strip symbols
   - UPX compression for Windows

2. **Binary packaging**:
   - Windows: `classic-cli.exe`, `classic-tui.exe`
   - Include YAML templates
   - Installation guide

3. **CI/CD integration**:
   - GitHub Actions for builds
   - Automated testing
   - Release artifact generation

4. **Migration path**:
   - Side-by-side with Python versions initially
   - User communication plan
   - Deprecation timeline

**Deliverable**: Distributable binaries and release process.

---

## Technical Specifications

### CLI Command-Line Interface

```bash
# Basic crash scan
classic-cli

# With options
classic-cli --fcx-mode --show-fid-values --stat-logging

# Custom paths
classic-cli --scan-path "C:\CustomLogs" --mods-folder-path "C:\MO2\mods"

# Full configuration
classic-cli \
  --fcx-mode \
  --show-fid-values \
  --move-unsolved \
  --ini-path "C:\Users\Name\Documents\My Games\Fallout4" \
  --scan-path "D:\AdditionalCrashLogs" \
  --mods-folder-path "C:\MO2\mods" \
  --simplify-logs
```

**Output Format:**
```
CLASSIC v8.0.0 - Crash Log Auto Scanner
========================================

Initializing scan...
  ✓ Loaded configuration from CLASSIC_Settings.yaml
  ✓ Found 47 crash logs in scan directory
  ✓ FormID database loaded (125,347 entries)

Scanning crash logs...
[████████████████████████████████] 47/47 (100%) - 2.3s

Results:
  Scanned: 47 logs
  Patterns matched: 234
  FormIDs resolved: 1,842
  Suspects identified: 12

Top suspects:
  1. SomePlugin.esp (18 occurrences)
  2. AnotherMod.esl (12 occurrences)
  3. ProblemMod.esp (8 occurrences)

Reports saved to: F:\Fallout 4\Crash Logs\Reports\

Press any key to continue...
```

### TUI Screen Layouts

#### Main Screen:
```
┌──────────────────────────────────────────────────────────────────┐
│ CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker      │
│ Terminal User Interface                                          │
└──────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│ STAGING MODS FOLDER                                              │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ C:\MO2\mods                                         [Browse] │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ CUSTOM SCAN FOLDER                                               │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ D:\AdditionalLogs                                   [Browse] │ │
│ └──────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [Crash Logs Scan]  [Game Files Scan]  [Papyrus Monitor]         │
├──────────────────────────────────────────────────────────────────┤
│ [ ] Check for Updates                                            │
├══════════════════════════════════════════════════════════════════┤
│                      OUTPUT VIEWER                               │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ Waiting for scan...                                        │   │
│ │                                                            │   │
│ │                                                            │   │
│ │ (Press / to search)                                        │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
│ F1 Help │ F5 Crash Scan │ F6 Game Scan │ F7 Papyrus │ Q Quit │
└──────────────────────────────────────────────────────────────────┘
```

### Widget Specifications

#### FolderSelector Widget:
```rust
pub struct FolderSelector {
    label: String,
    value: String,
    focused: bool,
    valid: bool,
}

impl FolderSelector {
    pub fn new(label: &str) -> Self;
    pub fn set_value(&mut self, path: String);
    pub fn validate(&self) -> bool;
    pub fn render(&self, area: Rect, buf: &mut Buffer);
    pub fn handle_input(&mut self, key: KeyEvent) -> Option<FolderMessage>;
}

pub enum FolderMessage {
    PathChanged(String),
    BrowseRequested,
}
```

#### ScanButton Widget:
```rust
pub struct ScanButton {
    label: String,
    scan_type: ScanType,
    state: ButtonState,
}

pub enum ScanType {
    CrashLogs,
    GameFiles,
}

pub enum ButtonState {
    Idle,
    Scanning { progress: f64 },
    Completed,
    Error(String),
}

impl ScanButton {
    pub fn new(label: &str, scan_type: ScanType) -> Self;
    pub fn start_scan(&mut self);
    pub fn update_progress(&mut self, progress: f64);
    pub fn complete(&mut self);
    pub fn render(&self, area: Rect, buf: &mut Buffer);
}
```

#### OutputViewer Widget:
```rust
pub struct OutputViewer {
    lines: Vec<String>,
    scroll_offset: usize,
    search_query: Option<String>,
    max_lines: usize,
}

impl OutputViewer {
    pub fn new() -> Self;
    pub fn append(&mut self, line: String);
    pub fn clear(&mut self);
    pub fn scroll_up(&mut self, lines: usize);
    pub fn scroll_down(&mut self, lines: usize);
    pub fn search(&mut self, query: String);
    pub fn render(&self, area: Rect, buf: &mut Buffer);
}
```

### Async Architecture

**Pattern**: Tokio-based async runtime with message passing:

```rust
// main.rs
#[tokio::main]
async fn main() -> Result<()> {
    let (event_tx, mut event_rx) = mpsc::channel(100);
    let (scan_tx, mut scan_rx) = mpsc::channel(100);

    // Spawn event loop
    let ui_handle = tokio::spawn(async move {
        let mut terminal = setup_terminal()?;
        let mut app = App::new();

        loop {
            terminal.draw(|f| app.render(f))?;

            if event::poll(Duration::from_millis(16))? {
                if let Event::Key(key) = event::read()? {
                    app.handle_input(key, &scan_tx).await?;
                }
            }

            // Process scan messages
            while let Ok(msg) = scan_rx.try_recv() {
                app.handle_scan_message(msg).await?;
            }

            if app.should_quit {
                break;
            }
        }
        Ok(())
    });

    ui_handle.await??;
    Ok(())
}
```

---

## Risk Analysis

### High-Priority Risks

#### 1. **Terminal Compatibility Issues**
- **Risk**: Different terminals have varying Unicode/color support
- **Mitigation**:
  - Use `crossterm` for cross-platform compatibility
  - Implement ASCII fallback mode
  - Detect terminal capabilities at startup
  - Test matrix: Windows Terminal, PowerShell, CMD, ConEmu, Alacritty

#### 2. **Async Complexity**
- **Risk**: Race conditions between UI rendering and scan tasks
- **Mitigation**:
  - Use ONE RUNTIME RULE (shared Tokio runtime)
  - Message passing for UI updates (no shared state)
  - Comprehensive async tests
  - Timeout guards on all operations

#### 3. **YAML Compatibility**
- **Risk**: Existing Python-generated YAML may not parse correctly
- **Mitigation**:
  - Use yaml-rust2 (same as Python backend)
  - Comprehensive migration tests
  - Validation layer for legacy configs
  - Migration tool if needed

### Medium-Priority Risks

#### 4. **Binary Size**
- **Risk**: Rust binaries can be large (>10MB)
- **Mitigation**:
  - Strip symbols (`strip = true`)
  - Link-time optimization (LTO)
  - UPX compression for distribution
  - Target <50MB compressed

#### 5. **Windows Console Limitations**
- **Risk**: Windows console has quirks (UTF-8, ANSI codes)
- **Mitigation**:
  - Enable Windows Terminal mode detection
  - SetConsoleOutputCP(65001) in init
  - Test on Windows 10/11 consoles
  - Provide Windows Terminal recommendation

### Low-Priority Risks

#### 6. **User Adoption**
- **Risk**: Users may resist switching from Python versions
- **Mitigation**:
  - Side-by-side installation initially
  - Clear performance benefits messaging
  - Migration guide documentation
  - Gradual deprecation timeline

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 80%+

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cli_args_parsing() {
        let args = CliArgs::parse_from(&[
            "classic-cli",
            "--fcx-mode",
            "--show-fid-values",
            "--scan-path", "C:\\Test"
        ]);

        assert_eq!(args.fcx_mode, Some(true));
        assert_eq!(args.show_fid_values, Some(true));
        assert_eq!(args.scan_path.unwrap(), PathBuf::from("C:\\Test"));
    }

    #[test]
    fn test_folder_selector_validation() {
        let mut selector = FolderSelector::new("Test");
        selector.set_value("/nonexistent/path".to_string());
        assert!(!selector.validate());

        // Use tempdir for valid path test
        let temp = tempfile::tempdir().unwrap();
        selector.set_value(temp.path().to_string_lossy().to_string());
        assert!(selector.validate());
    }

    #[tokio::test]
    async fn test_scan_handler_execution() {
        let handler = ScanHandler::new();
        let (tx, mut rx) = mpsc::channel(10);

        handler.start_crash_scan(tx).await.unwrap();

        // Should receive progress updates
        let msg = rx.recv().await.unwrap();
        assert!(matches!(msg, ScanMessage::Progress(_)));
    }
}
```

### Integration Tests

**Scenarios**:
1. **End-to-end CLI scan**:
   - Prepare test crash logs
   - Execute CLI with args
   - Verify output format
   - Check generated reports

2. **TUI workflow**:
   - Simulated input sequence
   - Folder selection → Scan → View results
   - Verify UI state transitions

3. **Configuration persistence**:
   - CLI args → YAML save
   - TUI settings change → YAML update
   - Load saved config → Verify applied

### Performance Tests

**Benchmarks** (using Criterion):
```rust
#[bench]
fn bench_cli_startup(b: &mut Bencher) {
    b.iter(|| {
        // Measure cold start time
        let start = Instant::now();
        let _ = main();
        start.elapsed()
    });

    // Assert < 500ms
}

#[bench]
fn bench_tui_render(b: &mut Bencher) {
    let mut app = App::new();
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();

    b.iter(|| {
        terminal.draw(|f| app.render(f)).unwrap();
    });
}
```

**Targets**:
- CLI startup: <500ms
- TUI render frame: <16ms (60 FPS)
- Scan execution: Match Rust backend performance
- Memory usage: <100MB for TUI

### Test Data

**Required Test Assets**:
- Sample crash logs (various formats)
- Test YAML configurations
- FormID database snapshot
- Plugin list fixtures
- Edge case scenarios (malformed logs, missing files)

---

## Migration Timeline

### Detailed Schedule

| Phase | Week | Deliverables | Dependencies |
|-------|------|--------------|--------------|
| **Phase 1** | 1-2 | CLI Foundation: Arg parsing, config, basic scan | Rust backend complete |
| **Phase 2** | 3 | CLI Polish: Progress, errors, YAML, testing | Phase 1 |
| **Phase 3** | 4-5 | TUI Foundation: Main screen, widgets, events | Phase 2 (config layer) |
| **Phase 4** | 6 | TUI Scans: Scan buttons, output viewer, handler | Phase 3, Rust backend |
| **Phase 5** | 7 | TUI Screens: Help, Settings, navigation | Phase 4 |
| **Phase 6** | 8 | Testing & Optimization: Tests, perf, cross-platform | Phase 5 |
| **Phase 7** | 9 | Distribution: Builds, CI/CD, docs, release | Phase 6 |

**Total Estimated Time**: 9 weeks (45 business days)

### Milestones

**M1 (Week 2)**: CLI Alpha - Basic scan functional
**M2 (Week 3)**: CLI Beta - Feature complete
**M3 (Week 5)**: TUI Alpha - Main screen interactive
**M4 (Week 7)**: TUI Beta - All screens functional
**M5 (Week 8)**: Release Candidate - Testing complete
**M6 (Week 9)**: **Production Release**

### Go/No-Go Criteria

**Before advancing to next phase:**
- ✅ All deliverables complete
- ✅ Tests passing (unit + integration)
- ✅ Code review approved
- ✅ Performance targets met
- ✅ Documentation updated

---

## Appendix

### A. Ratatui vs Alternatives

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| **Ratatui** | Modern, async-friendly, active | Younger ecosystem | ✅ **Selected** |
| tui-rs | Stable, proven | Unmaintained | ❌ Deprecated |
| cursive | High-level, easy | Not async-native | ❌ Sync only |
| termion | Lightweight | Low-level, no widgets | ❌ Too low-level |

### B. Clap Derive Example

```rust
use clap::Parser;

#[derive(Parser)]
#[command(name = "classic")]
#[command(author = "CLASSIC Team")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(about = "Crash Log Auto Scanner & Setup Integrity Checker")]
struct CliArgs {
    /// Enable FCX mode for enhanced FormID analysis
    #[arg(long, value_name = "BOOL")]
    fcx_mode: Option<bool>,

    // ... other args
}

// Usage:
let args = CliArgs::parse();
```

### C. Build Configuration

```toml
# Cargo.toml (workspace level)
[profile.release]
opt-level = 3           # Maximum optimization
lto = "fat"             # Link-time optimization
codegen-units = 1       # Single codegen unit for better optimization
strip = true            # Strip symbols
panic = "abort"         # Smaller binary

[profile.release-with-debug]
inherits = "release"
debug = true            # For profiling
```

### D. GitHub Actions Workflow

```yaml
name: Build CLI & TUI

on:
  push:
    branches: [main, classic-next]
  pull_request:

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Build CLI
        run: cargo build --release --bin classic-cli

      - name: Build TUI
        run: cargo build --release --bin classic-tui

      - name: Run Tests
        run: cargo test --workspace

      - name: Compress with UPX
        run: |
          upx --best --lzma target/release/classic-cli.exe
          upx --best --lzma target/release/classic-tui.exe

      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: classic-binaries-windows
          path: |
            target/release/classic-cli.exe
            target/release/classic-tui.exe
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-08 | AI Assistant | Initial comprehensive plan |

---

**Next Steps:**
1. Review plan with stakeholders
2. Set up `classic-cli` and `classic-tui` crate skeletons
3. Begin Phase 1: CLI Foundation
4. Establish CI/CD pipeline for Rust builds
