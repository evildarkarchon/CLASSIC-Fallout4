# CLI & TUI Architecture Documentation

**Version:** 8.0.0
**Last Updated:** 2025-10-10
**Target Audience:** Developers contributing to CLASSIC CLI/TUI

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [CLI Architecture](#cli-architecture)
3. [TUI Architecture](#tui-architecture)
4. [Shared Components](#shared-components)
5. [Design Patterns](#design-patterns)
6. [Performance Considerations](#performance-considerations)
7. [Testing Strategy](#testing-strategy)
8. [Build & Distribution](#build--distribution)
9. [Contributing Guidelines](#contributing-guidelines)

---

## Architecture Overview

### Design Principles

1. **Direct Business Logic Access**: CLI and TUI use `-core` crates directly, bypassing PyO3 bindings
2. **ONE RUNTIME RULE**: All async operations share the global Tokio runtime from `classic-shared`
3. **Zero Dependencies**: Single-binary distribution with no runtime dependencies
4. **Performance First**: Target <500ms startup, 60 FPS rendering (TUI)
5. **Cross-Platform**: Windows primary, Linux/macOS supported

### Dependency Graph

```
┌─────────────────────────────────────────────────────┐
│  CLI Application (rust/ui-applications/classic-cli)                      │
│  - Argument parsing (clap)                          │
│  - Progress bars (indicatif)                        │
│  - Terminal utilities (console)                     │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  TUI Application (rust/ui-applications/classic-tui)                      │
│  - Terminal UI (ratatui)                            │
│  - Cross-platform terminal (crossterm)              │
│  - Widget system (custom)                           │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  Business Logic Layer (-core crates)                │
│  - rust/business-logic/classic-scanlog-core: Log parsing                │
│  - rust/business-logic/classic-database-core: FormID lookups            │
│  - rust/business-logic/classic-file-io-core: File operations            │
│  - rust/business-logic/classic-yaml-core: YAML operations               │
│  - rust/business-logic/classic-config-core: Configuration                │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  Foundation Layer (classic-shared)                  │
│  - Global Tokio runtime                             │
│  - Error types                                      │
│  - Common utilities                                 │
└─────────────────────────────────────────────────────┘
```

### Key Architectural Decision: Direct Core Access

**Why CLI/TUI don't use PyO3 bindings:**

```rust
// ✅ CLI/TUI (Direct - no conversion overhead)
use classic_scanlog_core::LogParser;
let parser = LogParser::new();  // Native Rust type

// ❌ Python bindings (PyO3 conversion overhead)
use classic_scanlog_py::RustLogParser;  // Wrapper with conversions
```

**Benefits:**

- **Zero overhead**: No Python ↔ Rust conversions
- **Native types**: Work directly with Rust types
- **Better errors**: Full Rust error information
- **Faster**: 10-25% performance gain vs going through PyO3

---

## CLI Architecture

### Crate Structure

```
rust/ui-applications/classic-cli/
├── src/
│   ├── main.rs         # Entry point, orchestration
│   ├── lib.rs          # Library exports for testing
│   ├── args.rs         # Clap argument parsing
│   ├── config.rs       # Configuration management
│   ├── executor.rs     # Scan execution logic
│   ├── output.rs       # Output formatting
│   └── error.rs        # Error types
├── tests/
│   └── integration_tests.rs  # Integration tests
└── benches/
    └── cli_benchmarks.rs     # Performance benchmarks
```

### Component Breakdown

#### 1. Argument Parsing (`args.rs`)

**Technology:** Clap 4.5 with derive macros

```rust
use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "rust/ui-applications/classic-cli")]
#[command(about = "CLASSIC Crash Log Auto Scanner")]
pub struct CliArgs {
    /// Enable FCX mode
    #[arg(long)]
    pub fcx_mode: bool,

    /// Show FormID values
    #[arg(long)]
    pub show_fid_values: bool,

    // ... more flags

    /// Custom scan path
    #[arg(long, value_name = "PATH")]
    pub scan_path: Option<PathBuf>,
}
```

**Design Decisions:**

- Long flags only (`--fcx-mode`, not `-f`) for clarity
- Optional values as `Option<T>` to distinguish "not provided" from "provided false"
- PathBuf for all path arguments

#### 2. Configuration (`config.rs`)

**Responsibilities:**

- Load YAML configuration
- Merge CLI arguments with config
- Validate paths
- Persist changes

```rust
pub struct CliConfig {
    pub fcx_mode: bool,
    pub show_formid_values: bool,
    pub stat_logging: bool,
    pub move_unsolved_logs: bool,
    pub simplify_logs: bool,
    pub update_check: bool,
    pub paths: PathConfig,
}

impl CliConfig {
    /// Load from YAML, create default if missing
    pub async fn load_from_yaml(path: &Path) -> Result<Self> {
        // Uses rust/business-logic/classic-yaml-core directly
    }

    /// Merge CLI args (CLI args take precedence)
    pub fn merge_cli_args(&mut self, args: &CliArgs) {
        if args.fcx_mode {
            self.fcx_mode = true;
        }
        // ... merge other fields
    }
}
```

**Priority Order:**

1. Default values (lowest)
2. YAML configuration
3. CLI arguments (highest - overrides all)

#### 3. Scan Executor (`executor.rs`)

**Responsibilities:**

- Orchestrate scan workflow
- Use `-core` crates for business logic
- Progress reporting
- Statistics collection

```rust
pub struct ScanExecutor {
    config: CliConfig,
    yaml_data: YamlData,  // From rust/business-logic/classic-config-core
}

impl ScanExecutor {
    pub async fn scan(&self) -> Result<ScanResults> {
        // 1. Find crash logs
        let logs = self.find_crash_logs().await?;

        // 2. Parse logs (rust/business-logic/classic-scanlog-core)
        let parser = LogParser::new();
        let parsed = parser.parse_logs(&logs).await?;

        // 3. Analyze FormIDs (rust/business-logic/classic-database-core)
        let analyzer = FormIDAnalyzer::new(&self.yaml_data);
        let analyzed = analyzer.analyze(&parsed).await?;

        // 4. Generate reports
        self.generate_reports(&analyzed).await?;

        Ok(analyzed)
    }
}
```

**Async Design:**

- Uses `tokio::main` at entry point
- All I/O is async (file reads, database queries)
- Parallel log processing with `rayon` for CPU-bound work

#### 4. Output Formatting (`output.rs`)

**Responsibilities:**

- Format scan results for console
- Progress bars with `indicatif`
- Color-coded output with `console`
- Summary statistics

```rust
pub struct OutputFormatter {
    progress_bar: ProgressBar,
}

impl OutputFormatter {
    pub fn display_progress(&self, current: usize, total: usize) {
        self.progress_bar.set_position(current as u64);
        self.progress_bar.set_message(format!("{}/{}", current, total));
    }

    pub fn display_summary(&self, stats: &ScanStats) {
        println!("\nResults:");
        println!("  Scanned: {} logs", stats.scanned_logs);
        println!("  Patterns matched: {}", stats.patterns_matched);
        // ... more stats
    }
}
```

### Main Execution Flow

```rust
// main.rs
#[tokio::main]
async fn main() -> Result<()> {
    // 1. Parse CLI arguments
    let args = CliArgs::parse();

    // 2. Load/create configuration
    let config_path = get_config_path()?;
    let mut config = load_or_create_config(&config_path, &args).await?;

    // 3. Merge CLI args into config
    config.merge_cli_args(&args);

    // 4. Initialize executor
    let yaml_data = load_yaml_data(&config)?;
    let executor = ScanExecutor::new(config, yaml_data);

    // 5. Execute scan
    let results = executor.scan().await?;

    // 6. Display summary
    let formatter = OutputFormatter::new();
    formatter.display_summary(&results.stats);

    // 7. Pause (Windows only)
    #[cfg(target_os = "windows")]
    pause();

    Ok(())
}
```

---

## TUI Architecture

### Crate Structure

```
rust/ui-applications/classic-tui/
├── src/
│   ├── main.rs         # Entry point
│   ├── lib.rs          # Library exports
│   ├── app.rs          # Application state
│   ├── events.rs       # Event definitions
│   ├── ui/
│   │   ├── mod.rs
│   │   ├── main_screen.rs      # Main screen layout
│   │   ├── help_screen.rs      # Help screen
│   │   ├── settings_screen.rs  # Settings UI
│   │   └── layout.rs           # Layout management
│   ├── widgets/
│   │   ├── mod.rs
│   │   ├── folder_selector.rs  # Folder path widget
│   │   ├── scan_button.rs      # Scan button widget
│   │   ├── output_viewer.rs    # Scrollable output
│   │   ├── checkbox.rs         # Checkbox widget
│   │   └── status_bar.rs       # Status bar
│   └── handlers/
│       ├── mod.rs
│       ├── input_handler.rs    # Keyboard input
│       └── scan_handler.rs     # Scan orchestration
├── tests/
│   └── widget_integration_tests.rs
└── benches/
    └── tui_benchmarks.rs
```

### Component Breakdown

#### 1. Application State (`app.rs`)

**Central state management:**

```rust
pub struct App {
    // Configuration
    config: ClassicConfig,

    // UI State
    ui_state: UiState,
    focused_widget: WidgetId,

    // Scan State
    scan_state: ScanState,
    output_lines: Vec<String>,

    // Control
    should_quit: bool,
}

pub enum UiState {
    MainScreen,
    HelpScreen,
    SettingsScreen,
    PapyrusScreen,
}

pub enum ScanState {
    Idle,
    CrashScanning { progress: f64 },
    GameScanning { progress: f64 },
    Completed,
    Error(String),
}
```

**Design Pattern:** Central state with immutable borrows for rendering

#### 2. Widget System

**Base Widget Trait:**

```rust
pub trait Widget {
    fn render(&self, f: &mut Frame, area: Rect);
    fn handle_input(&mut self, key: KeyEvent) -> Option<Message>;
}
```

**FolderSelector Example:**

```rust
pub struct FolderSelector {
    label: String,
    value: Option<PathBuf>,
    focused: bool,
}

impl FolderSelector {
    pub fn new(label: impl Into<String>) -> Self {
        Self {
            label: label.into(),
            value: None,
            focused: false,
        }
    }

    pub fn set_value(&mut self, path: PathBuf) {
        self.value = Some(path);
    }

    pub fn validate(&self) -> bool {
        self.value
            .as_ref()
            .map(|p| p.exists() && p.is_dir())
            .unwrap_or(false)
    }

    pub fn render(&self, f: &mut Frame, area: Rect) {
        let border_color = if self.focused {
            Color::Yellow
        } else if self.validate() {
            Color::Green
        } else {
            Color::Red
        };

        let widget = Paragraph::new(self.display_text())
            .block(Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)));

        f.render_widget(widget, area);
    }
}
```

**Widget Design Principles:**

- **Self-contained**: Each widget manages own state
- **Immutable rendering**: `&self` for render (no mutations during draw)
- **Color-coded feedback**: Visual state indication
- **Keyboard-first**: Tab navigation, shortcuts

#### 3. Event System (`events.rs`)

**Message-based communication:**

```rust
pub enum UiMessage {
    // Navigation
    FocusNext,
    FocusPrevious,
    ChangeScreen(UiState),

    // Input
    KeyPressed(KeyEvent),
    PathChanged(PathBuf),

    // Control
    Quit,
}

pub enum ScanMessage {
    Started,
    Progress(f64),
    Output(String),
    Completed(ScanResults),
    Error(String),
}
```

**Event Flow:**

```
User Input → InputHandler → UiMessage → App::handle_message() → Update State
                                                              ↓
                                                           Re-render
```

#### 4. Async Scan Handling

**Challenges:**

- UI runs on main thread (must stay responsive)
- Scans are async and potentially long-running
- Need real-time progress updates

**Solution: Message Passing with Channels**

```rust
// handlers/scan_handler.rs
pub struct ScanHandler {
    tx: mpsc::Sender<ScanMessage>,
}

impl ScanHandler {
    pub async fn start_crash_scan(&self, config: ClassicConfig) {
        let tx = self.tx.clone();

        // Spawn scan in background
        tokio::spawn(async move {
            tx.send(ScanMessage::Started).await.ok();

            // Use rust/business-logic/classic-scanlog-core
            let executor = ScanExecutor::new(config);

            match executor.scan().await {
                Ok(results) => {
                    tx.send(ScanMessage::Completed(results)).await.ok();
                }
                Err(e) => {
                    tx.send(ScanMessage::Error(e.to_string())).await.ok();
                }
            }
        });
    }
}
```

**In Main Loop:**

```rust
// main.rs
loop {
    // Render current state
    terminal.draw(|f| app.render(f))?;

    // Handle input (non-blocking)
    if event::poll(Duration::from_millis(16))? {
        if let Event::Key(key) = event::read()? {
            app.handle_input(key, &scan_tx).await?;
        }
    }

    // Process scan messages (non-blocking)
    while let Ok(msg) = scan_rx.try_recv() {
        app.handle_scan_message(msg).await?;
    }

    if app.should_quit {
        break;
    }
}
```

**Target**: 16ms/frame = 60 FPS

#### 5. Rendering Pipeline

**Layout Management:**

```rust
// ui/layout.rs
pub fn main_screen_layout(area: Rect) -> Vec<Rect> {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Title
            Constraint::Length(6),  // Folder selectors
            Constraint::Length(3),  // Buttons
            Constraint::Length(2),  // Options
            Constraint::Min(0),     // Output (fills remaining)
            Constraint::Length(1),  // Status bar
        ])
        .split(area);

    chunks.to_vec()
}
```

**Rendering Strategy:**

- **Dirty regions**: Only re-render changed areas (Ratatui handles this)
- **Double buffering**: Ratatui swaps buffers automatically
- **Minimal allocations**: Reuse strings where possible

---

## Shared Components

### 1. Configuration Layer

**Shared between CLI and TUI:**

```rust
// rust/business-logic/classic-config-core/src/lib.rs
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
```

**Used by:**

- CLI: Load via `CliConfig::load_from_yaml()`
- TUI: Load via `App::load_config()`
- Python: Load via PyO3 bindings (rust/python-bindings/classic-config-py)

### 2. Business Logic (-core crates)

**Direct usage pattern:**

```rust
// CLI executor.rs
use classic_scanlog_core::LogParser;
use classic_database_core::DatabasePool;
use classic_file_io_core::FileIOCore;

let parser = LogParser::new();
let db_pool = DatabasePool::new(db_path).await?;
let file_io = FileIOCore::new();
```

**No PyO3 bindings involved** - native Rust types throughout.

### 3. Error Handling

**Error types from classic-shared:**

```rust
// classic-shared/src/errors.rs
#[derive(Debug, thiserror::Error)]
pub enum ClassicError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Database error: {0}")]
    Database(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Scan error: {0}")]
    Scan(String),
}
```

**Used consistently** across CLI, TUI, and all `-core` crates.

---

## Design Patterns

### 1. Builder Pattern (Configuration)

```rust
let config = CliConfig::default()
    .with_fcx_mode(true)
    .with_stat_logging(true)
    .with_mods_folder(path);
```

### 2. Command Pattern (TUI Actions)

```rust
pub enum Action {
    StartScan(ScanType),
    ChangeScreen(UiState),
    UpdatePath(PathBuf),
}

impl App {
    pub fn execute_action(&mut self, action: Action) {
        match action {
            Action::StartScan(scan_type) => {
                self.start_scan(scan_type);
            }
            // ... handle other actions
        }
    }
}
```

### 3. State Machine (Scan States)

```rust
impl App {
    fn transition_scan_state(&mut self, new_state: ScanState) {
        match (&self.scan_state, &new_state) {
            (ScanState::Idle, ScanState::CrashScanning { .. }) => {
                // Valid transition
                self.scan_state = new_state;
            }
            (ScanState::CrashScanning { .. }, ScanState::Completed) => {
                // Valid transition
                self.scan_state = new_state;
            }
            _ => {
                // Invalid transition - log warning
            }
        }
    }
}
```

### 4. Message Passing (Async Communication)

```rust
// Separate concerns:
// - Main thread: UI rendering
// - Background task: Async scan

let (tx, rx) = mpsc::channel(100);

// Background scan
tokio::spawn(async move {
    // ... perform scan
    tx.send(ScanMessage::Completed(results)).await.ok();
});

// Main loop
while let Some(msg) = rx.recv().await {
    app.handle_message(msg);
}
```

---

## Performance Considerations

### CLI Performance Targets

| Metric         | Target | Actual |
|----------------|--------|--------|
| Cold start     | <500ms | ~400ms |
| Config load    | <50ms  | ~30ms  |
| Scan (47 logs) | <1s    | ~800ms |
| Memory usage   | <50MB  | ~45MB  |

### TUI Performance Targets

| Metric        | Target | Actual  |
|---------------|--------|---------|
| Render FPS    | 60     | 60      |
| Frame time    | <16ms  | ~8-12ms |
| Input latency | <50ms  | ~20ms   |
| Memory usage  | <100MB | ~95MB   |

### Optimization Techniques

**1. Lazy Loading**

```rust
// Don't load database until needed
let db_pool = LazyLock::new(|| DatabasePool::new(path));
```

**2. Async Parallelism**

```rust
// Parse logs in parallel
let results = stream::iter(logs)
    .map(|log| parse_log(log))
    .buffer_unordered(num_cpus::get())
    .collect()
    .await;
```

**3. String Interning**

```rust
// Reuse common strings
use string_cache::DefaultAtom;
let atom = DefaultAtom::from("common_string");
```

**4. Zero-Copy Where Possible**

```rust
// Use &str instead of String when not owning
pub fn process(data: &str) -> &str {
    // No allocation
}
```

---

## Testing Strategy

### Unit Tests

**Widget tests:**

```rust
#[test]
fn test_folder_selector_validation() {
    let mut selector = FolderSelector::new("Test");

    // Invalid path
    selector.set_value(PathBuf::from("/nonexistent"));
    assert!(!selector.validate());

    // Valid path
    let temp = tempdir().unwrap();
    selector.set_value(temp.path().to_path_buf());
    assert!(selector.validate());
}
```

### Integration Tests

**CLI workflow tests:**

```rust
#[tokio::test]
async fn test_cli_scan_workflow() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("config.yaml");

    // Create config
    let config = CliConfig::default();
    config.save_to_yaml(&config_path).await.unwrap();

    // Load config
    let loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();

    assert_eq!(loaded.fcx_mode, config.fcx_mode);
}
```

### Benchmarks

**Performance regression detection:**

```rust
fn bench_folder_selector_validation(c: &mut Criterion) {
    let temp_dir = tempdir().unwrap();
    let mut selector = FolderSelector::new("Test");
    selector.set_value(temp_dir.path().to_path_buf());

    c.bench_function("folder_validation", |b| {
        b.iter(|| {
            black_box(selector.validate())
        })
    });
}
```

---

## Build & Distribution

### Release Build

```bash
# CLI
cargo build --release --bin rust/ui-applications/classic-cli

# TUI
cargo build --release --bin rust/ui-applications/classic-tui

# Both
cargo build --release --workspace --bins
```

### Optimization Flags

```toml
# Cargo.toml (workspace level)
[profile.release]
opt-level = 3           # Maximum optimization
lto = "fat"             # Link-time optimization
codegen-units = 1       # Single codegen unit
strip = true            # Strip symbols
panic = "abort"         # Smaller binary
```

### Binary Size

**Before optimizations:**

- CLI: ~25MB
- TUI: ~30MB

**After optimizations + UPX:**

- CLI: ~8-10MB
- TUI: ~12-15MB

### UPX Compression

```bash
# Windows
upx --best --lzma target/release/rust/ui-applications/classic-cli.exe
upx --best --lzma target/release/rust/ui-applications/classic-tui.exe

# Linux/macOS
upx --best --lzma target/release/rust/ui-applications/classic-cli
upx --best --lzma target/release/rust/ui-applications/classic-tui
```

---

## Contributing Guidelines

### Code Style

**Follow Rust conventions:**

```bash
# Format code
cargo fmt

# Lint
cargo clippy -- -D warnings

# Check
cargo check --workspace
```

### Adding New Features

**1. CLI Feature:**

1. Add argument to `CliArgs` in `args.rs`
2. Update `CliConfig` in `config.rs`
3. Implement logic in `executor.rs`
4. Add tests
5. Update documentation

**2. TUI Widget:**

1. Create widget in `widgets/new_widget.rs`
2. Implement `render()` method
3. Add to main screen layout
4. Handle input in `input_handler.rs`
5. Add tests
6. Update documentation

### Pull Request Checklist

- [ ] Code compiles without warnings
- [ ] Tests pass (`cargo test --workspace`)
- [ ] Benchmarks run (`cargo bench`)
- [ ] Formatted (`cargo fmt`)
- [ ] Linted (`cargo clippy`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

---

## Further Reading

- **Ratatui Docs**: https://ratatui.rs/
- **Clap Docs**: https://docs.rs/clap/
- **Tokio Docs**: https://tokio.rs/
- **CLASSIC Rust Docs**: [Rust Documentation Index](RUST_DOCUMENTATION_INDEX.md)

---

**Happy coding!** 🦀
