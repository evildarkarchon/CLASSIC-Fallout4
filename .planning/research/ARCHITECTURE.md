# Architecture Patterns: Slint GUI Integration

**Domain:** Native Rust GUI for crash log analysis application
**Researched:** 2026-02-05
**Confidence:** HIGH (based on official Slint documentation and GitHub discussions)

## Recommended Architecture

The Slint GUI integrates directly with existing `-core` crates, bypassing the Python binding layer entirely. This follows the existing architecture's principle that "CLI/TUI applications use `-core` crates directly."

```
+------------------------------------+
|         Slint GUI Application       |
|    rust/ui-applications/classic-gui |
+------------------------------------+
              |
              v
+------------------------------------+
|         Slint Runtime              |
|  (Main thread event loop)          |
+------------------------------------+
              |
    +--------------------+
    | invoke_from_event  |
    | _loop() bridge     |
    +--------------------+
              |
              v
+------------------------------------+
|      Worker Thread Pool            |
|  (Tokio runtime from classic-shared)|
+------------------------------------+
              |
              v
+------------------------------------+
|      Business Logic Layer          |
|  classic-scanlog-core              |
|  classic-settings-core             |
|  classic-path-core                 |
|  classic-yaml-core                 |
+------------------------------------+
              |
              v
+------------------------------------+
|      Foundation Layer              |
|  classic-shared-core               |
|  (Global Tokio runtime, errors)    |
+------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `classic-gui` | UI presentation, user interaction, state management | Slint runtime, worker threads |
| Slint Runtime | Event loop, rendering, property reactivity | UI components, invoke handlers |
| Worker Thread Pool | Async task execution via Tokio | Business logic crates, UI via channels |
| `classic-scanlog-core` | Log parsing, analysis, report generation | File I/O, settings, database |
| `classic-settings-core` | Configuration loading and management | YAML core, file I/O |
| `classic-shared-core` | Global Tokio runtime, error types | All crates |

### Data Flow

```
User clicks "Scan" button
        |
        v
Slint callback handler triggered (main thread)
        |
        v
Clone Weak<MainWindow> reference
        |
        v
Spawn worker thread with tokio::spawn()
        |
        v
Worker calls OrchestratorCore::process_log() (async)
        |
        v
Worker sends progress via channel to UI
        |
        v
Channel receiver uses upgrade_in_event_loop()
        |
        v
UI updates progress bar (main thread)
        |
        v
Worker completes, sends final result
        |
        v
UI displays report (main thread)
```

## Crate Location and Structure

The Slint GUI application lives at: `rust/ui-applications/classic-gui/`

```
rust/ui-applications/classic-gui/
|-- Cargo.toml
|-- build.rs                    # Compiles .slint files
|-- src/
|   |-- main.rs                 # Entry point, event loop
|   |-- app.rs                  # Application state, initialization
|   |-- controllers/
|   |   |-- mod.rs
|   |   |-- scan.rs             # Scan operations controller
|   |   |-- settings.rs         # Settings controller
|   |   |-- backup.rs           # Backup operations controller
|   |   `-- update.rs           # Update check controller
|   |-- workers/
|   |   |-- mod.rs
|   |   |-- scan_worker.rs      # Background scan task
|   |   `-- progress.rs         # Progress channel handling
|   `-- bridge/
|       |-- mod.rs
|       `-- tokio_bridge.rs     # Tokio <-> Slint communication
|-- ui/
|   |-- main.slint              # Main window layout
|   |-- components/
|   |   |-- scan_panel.slint    # Scan tab UI
|   |   |-- backup_panel.slint  # Backup tab UI
|   |   |-- results_panel.slint # Results tab UI
|   |   `-- progress.slint      # Progress indicators
|   `-- globals/
|       |-- logic.slint         # Global callbacks for Rust
|       `-- state.slint         # Shared state properties
```

### Cargo.toml Dependencies

```toml
[package]
name = "classic-gui"
version = "0.1.0"
edition = "2021"

[dependencies]
# GUI
slint = { workspace = true }

# Business logic (direct imports, no Python bindings)
classic-shared-core = { path = "../../foundation/classic-shared-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }
classic-settings-core = { path = "../../business-logic/classic-settings-core" }
classic-path-core = { path = "../../business-logic/classic-path-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-file-io-core = { path = "../../business-logic/classic-file-io-core" }
classic-database-core = { path = "../../business-logic/classic-database-core" }

# Async compatibility
async-compat = "0.2"
tokio = { workspace = true }
futures = { workspace = true }

# Channels for worker communication
crossbeam-channel = "0.5"

[build-dependencies]
slint-build = "1.14"
```

## Async Handling Pattern: The Tokio-Slint Bridge

### The Core Challenge

Slint's event loop and Tokio's runtime cannot coexist in the same thread. Slint requires its event loop on the main thread, while the existing `classic-shared-core` provides a global multi-threaded Tokio runtime via `get_runtime()`.

**Constraint from Slint maintainers:** "The spawn call on the current-thread runtime would schedule execution, but once the Slint event loop runs, the current-thread runtime cannot actually execute the task."

### Recommended Solution: Worker Thread Pattern

Use a dedicated worker thread pool running on the existing Tokio runtime, communicating back to the UI via `invoke_from_event_loop()` or `upgrade_in_event_loop()`.

```rust
use classic_shared_core::get_runtime;
use slint::Weak;
use std::sync::mpsc;

/// Bridge between Tokio async operations and Slint UI
pub struct TokioBridge {
    /// Sender for progress updates
    progress_tx: mpsc::Sender<ProgressUpdate>,
}

impl TokioBridge {
    /// Spawn an async task on the global Tokio runtime
    pub fn spawn_scan<F>(&self, window: Weak<MainWindow>, task: F)
    where
        F: Future<Output = AnalysisResult> + Send + 'static,
    {
        let progress_tx = self.progress_tx.clone();

        // Use the existing global runtime (ONE RUNTIME RULE)
        get_runtime().spawn(async move {
            let result = task.await;

            // Update UI from the event loop thread
            window.upgrade_in_event_loop(move |win| {
                win.set_scan_result(result.into());
                win.set_is_scanning(false);
            }).ok();
        });
    }
}
```

### Alternative: async_compat Wrapper

For simpler cases where you need to call async code from Slint callbacks:

```rust
use async_compat::Compat;

fn setup_callbacks(window: &MainWindow) {
    let window_weak = window.as_weak();

    window.on_start_scan(move || {
        let weak = window_weak.clone();

        // Use spawn_local with Compat to bridge to Tokio
        slint::spawn_local(Compat::new(async move {
            // This runs on the UI thread but can call Tokio futures
            let result = some_tokio_operation().await;

            weak.upgrade_in_event_loop(move |win| {
                win.set_result(result);
            }).ok();
        })).ok();
    });
}
```

### Progress Updates Pattern

For long-running scans that need to update progress:

```rust
use crossbeam_channel::{bounded, Sender, Receiver};
use slint::Timer;
use std::time::Duration;

pub struct ProgressBridge {
    receiver: Receiver<ProgressUpdate>,
    timer: Timer,
}

impl ProgressBridge {
    pub fn new(window: Weak<MainWindow>) -> (Self, Sender<ProgressUpdate>) {
        let (tx, rx) = bounded(100);

        let timer = Timer::default();
        let rx_clone = rx.clone();
        let window_clone = window.clone();

        // Poll channel periodically from the UI thread
        timer.start(
            slint::TimerMode::Repeated,
            Duration::from_millis(16), // ~60 FPS
            move || {
                while let Ok(update) = rx_clone.try_recv() {
                    if let Some(win) = window_clone.upgrade() {
                        win.set_progress(update.percent as f32 / 100.0);
                        win.set_status_text(update.message.into());
                    }
                }
            },
        );

        (Self { receiver: rx, timer }, tx)
    }
}
```

## State Management Approach

### Global Callbacks Pattern

Slint's recommended state management uses exported globals with callbacks that bridge to Rust:

```slint
// ui/globals/logic.slint
export global ScanLogic {
    // Callbacks invoked from UI, handled in Rust
    callback start-scan();
    callback stop-scan();
    callback select-folder() -> string;

    // Properties bound to UI, set from Rust
    in-out property <bool> is-scanning: false;
    in-out property <float> scan-progress: 0.0;
    in-out property <string> status-message: "";
    in-out property <[ScanResult]> results: [];
}

export global SettingsLogic {
    callback load-settings();
    callback save-setting(string, string);

    in-out property <string> game-path: "";
    in-out property <bool> fcx-mode: false;
    in-out property <bool> simplify-logs: false;
}
```

### Rust Backend Connection

```rust
fn setup_globals(window: &MainWindow) {
    let logic = window.global::<ScanLogic>();
    let settings = window.global::<SettingsLogic>();

    // Set up scan callback
    let window_weak = window.as_weak();
    logic.on_start_scan(move || {
        let weak = window_weak.clone();

        // Update UI state
        if let Some(win) = weak.upgrade() {
            win.global::<ScanLogic>().set_is_scanning(true);
        }

        // Spawn scan on worker thread
        spawn_scan_worker(weak);
    });

    // Load initial settings
    if let Ok(config) = load_classic_settings() {
        settings.set_game_path(config.game_path.into());
        settings.set_fcx_mode(config.fcx_mode);
    }
}
```

### State Update Flow

```
User Action (button click)
        |
        v
Slint callback triggered
        |
        v
Rust on_<callback> handler
        |
        v
Update optimistic UI state (set_is_scanning(true))
        |
        v
Spawn worker on Tokio runtime
        |
        v
Worker processes, sends progress via channel
        |
        v
Timer/channel polls updates to UI
        |
        v
Worker completes
        |
        v
upgrade_in_event_loop() to set final state
```

## Patterns to Follow

### Pattern 1: Weak Reference Capture

**What:** Always capture weak references to windows in closures to avoid memory leaks.

**When:** Any callback or async task that updates UI.

**Example:**
```rust
let window_weak = window.as_weak();
window.on_some_action(move || {
    let weak = window_weak.clone();
    get_runtime().spawn(async move {
        let result = do_work().await;
        weak.upgrade_in_event_loop(move |win| {
            win.set_result(result);
        }).ok();
    });
});
```

### Pattern 2: ONE RUNTIME RULE Compliance

**What:** Use `classic_shared_core::get_runtime()` for all async operations.

**When:** Any Tokio operation in the GUI.

**Example:**
```rust
// CORRECT: Use shared runtime
use classic_shared_core::get_runtime;

fn spawn_task<F: Future + Send + 'static>(f: F) {
    get_runtime().spawn(f);
}

// WRONG: Creating new runtime
// let rt = Runtime::new().unwrap(); // NEVER DO THIS
```

### Pattern 3: UI Thread Safety

**What:** All UI updates must happen on the main thread via `upgrade_in_event_loop()`.

**When:** Updating any Slint property or calling any Slint method from a worker thread.

**Example:**
```rust
// From worker thread
window_weak.upgrade_in_event_loop(move |win| {
    // This closure runs on the main UI thread
    win.set_progress(0.5);
    win.global::<ScanLogic>().set_status_message("Processing...".into());
}).ok();
```

### Pattern 4: Global Callbacks for Business Logic

**What:** Define callbacks in `.slint` globals, implement in Rust.

**When:** Any action that requires Rust business logic.

**Example:**
```slint
// In .slint
export global Logic {
    pure callback format-formid(string) -> string;
    callback analyze-log(string);
}
```

```rust
// In Rust
window.global::<Logic>().on_format_formid(|formid| {
    classic_scanlog_core::format_formid(&formid).into()
});

window.global::<Logic>().on_analyze_log(move |path| {
    spawn_analysis(path.to_string(), window_weak.clone());
});
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Blocking the UI Thread

**What:** Running long operations synchronously in callbacks.

**Why bad:** Freezes the UI, poor user experience.

**Instead:** Spawn on worker thread, update UI via `upgrade_in_event_loop()`.

```rust
// BAD
window.on_scan(|| {
    let result = heavy_computation(); // Blocks UI!
    window.set_result(result);
});

// GOOD
window.on_scan(move || {
    let weak = window_weak.clone();
    get_runtime().spawn(async move {
        let result = heavy_computation_async().await;
        weak.upgrade_in_event_loop(|win| win.set_result(result)).ok();
    });
});
```

### Anti-Pattern 2: Strong Reference Cycles

**What:** Capturing strong window references in closures stored on the window.

**Why bad:** Memory leak, window never freed.

**Instead:** Use `window.as_weak()` before capturing.

### Anti-Pattern 3: Multiple Tokio Runtimes

**What:** Creating new Tokio runtimes instead of using the shared one.

**Why bad:** Violates ONE RUNTIME RULE, causes deadlocks.

**Instead:** Always use `classic_shared_core::get_runtime()`.

### Anti-Pattern 4: Direct Property Mutation from Threads

**What:** Trying to set Slint properties directly from worker threads.

**Why bad:** Slint is not thread-safe, will panic or corrupt state.

**Instead:** Use `upgrade_in_event_loop()` for all UI updates.

## Build Order for Phases

Based on dependencies and integration complexity, the recommended build order is:

### Phase 1: Foundation (Infrastructure)
1. Create `rust/ui-applications/classic-gui/` directory structure
2. Set up `Cargo.toml` with dependencies on `-core` crates
3. Create `build.rs` for Slint compilation
4. Create minimal `main.rs` that shows an empty window
5. Verify Slint compiles and window displays

**Dependencies:** None (fresh crate)
**Validates:** Build system, Slint integration works

### Phase 2: Tokio Bridge
1. Implement `TokioBridge` for async operation spawning
2. Implement `ProgressBridge` for progress updates
3. Create `bridge/mod.rs` with channel-based communication
4. Add unit tests for bridge functionality

**Dependencies:** Phase 1, `classic-shared-core`
**Validates:** ONE RUNTIME RULE compliance, async pattern works

### Phase 3: Core UI Layout
1. Design main window layout in `ui/main.slint`
2. Implement tab structure (Main, Backup, Results)
3. Create reusable components (buttons, progress bars)
4. Set up global callbacks and state properties

**Dependencies:** Phase 1
**Validates:** UI renders correctly, globals accessible

### Phase 4: Settings Integration
1. Connect `classic-settings-core` to UI
2. Implement settings loading on startup
3. Add settings panel UI
4. Wire save functionality

**Dependencies:** Phases 2, 3, `classic-settings-core`, `classic-yaml-core`
**Validates:** Settings load/save works

### Phase 5: Scan Operations
1. Implement `ScanController` using `OrchestratorCore`
2. Wire scan button to spawn worker
3. Implement progress updates during scan
4. Display results in results panel

**Dependencies:** Phases 2, 3, 4, `classic-scanlog-core`
**Validates:** Core functionality works

### Phase 6: Polish and Feature Parity
1. Add remaining features (backup, updates, pastebin)
2. Implement error handling dialogs
3. Add window geometry persistence
4. Performance optimization

**Dependencies:** All previous phases
**Validates:** Feature parity with Python GUI

## Scalability Considerations

| Concern | Current (100s of logs) | Scale (1000s of logs) | Future (10000s) |
|---------|------------------------|----------------------|-----------------|
| Scan performance | Single orchestrator | Parallel batch via `process_logs_batch()` | Consider streaming results |
| Memory usage | Load all results | Virtualized list view | Pagination, lazy loading |
| Progress updates | Simple percentage | Per-file progress | Hierarchical progress tree |
| UI responsiveness | 60 FPS target | Debounce updates | Render on demand |

## Sources

- [Slint + async Rust Discussion](https://github.com/slint-ui/slint/discussions/4377) - Official guidance on async integration
- [Slint + Tokio Main Thread Discussion](https://github.com/slint-ui/slint/discussions/5784) - Tokio runtime compatibility
- [spawn_local Documentation](https://docs.rs/slint/latest/slint/fn.spawn_local.html) - Official API docs
- [Progress Indicator Updates](https://github.com/slint-ui/slint/discussions/4175) - Progress bar patterns
- [Backend Tokio Communication](https://github.com/slint-ui/slint/discussions/7246) - Worker thread patterns
- [Global Callbacks Recipe](https://releases.slint.dev/releases/1.5.1/docs/slint/src/recipes/recipes) - State management
- [Rust Structs for State Management](https://github.com/slint-ui/slint/discussions/5114) - Global singletons
- [async-compat Documentation](https://docs.rs/async-compat/latest/async_compat/) - Tokio bridge crate
- [Slint Rust Template](https://github.com/slint-ui/slint-rust-template) - Project structure reference
- [Slint Rust Documentation](https://docs.slint.dev/latest/docs/rust/slint) - Official Rust API docs
