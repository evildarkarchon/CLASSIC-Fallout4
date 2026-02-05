# Phase 19: Foundation and Async Bridge - Research

**Researched:** 2026-02-05
**Domain:** Slint GUI framework with Tokio async integration
**Confidence:** HIGH

## Summary

This phase establishes the foundation for CLASSIC's Rust-native GUI using Slint 1.15.0 with Skia renderer. The research validates that the existing AsyncBridge in `classic-shared-core` already implements the correct pattern for Slint/Tokio coordination. The critical finding is that CLASSIC's ONE RUNTIME RULE aligns perfectly with Slint's async integration requirements.

The project already has async bridge infrastructure in `rust/foundation/classic-shared-core/src/async_bridge.rs` (enabled via `gui-bridge` feature). This code uses the correct patterns: `get_runtime().spawn()` for async operations and `slint::invoke_from_event_loop()` for UI updates. The phase must create the GUI crate, wire up Slint builds, and demonstrate the worker thread pattern with progress callbacks.

**Primary recommendation:** Create `classic-gui` crate in `rust/ui-applications/` using the existing `AsyncBridge` from `classic-shared-core` with the `gui-bridge` feature enabled.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slint | 1.15.0 | Declarative GUI toolkit | Already in workspace deps, cross-platform native UI |
| slint-build | 1.15.0 | Build script for .slint compilation | Required for compiling .slint to Rust |
| tokio | 1.49.0 | Async runtime | Already in workspace, ONE RUNTIME RULE |
| tokio-util | 0.7.x | CancellationToken support | Standard Tokio ecosystem for cancellation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| classic-shared-core | 8.2.0 | Runtime + AsyncBridge | Core async/UI coordination |
| classic-scanlog-core | local | OrchestratorCore | Real scan operations in later phases |
| image | (via slint feature) | Image loading | For window icon from .ico file |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| renderer-skia | renderer-femtovg | FemtoVG is lighter but Skia has better anti-aliasing/text |
| renderer-skia | renderer-software | Software works without GPU but slower, less capable |

**Installation:**
```toml
# In classic-gui/Cargo.toml
[dependencies]
slint = { workspace = true, features = ["backend-winit", "renderer-skia", "image-default-formats"] }
classic-shared-core = { path = "../../foundation/classic-shared-core", features = ["gui-bridge"] }
tokio-util = "0.7"

[build-dependencies]
slint-build = "1.15"
```

## Architecture Patterns

### Recommended Project Structure
```
rust/ui-applications/classic-gui/
  Cargo.toml          # Crate manifest
  build.rs            # slint_build::compile()
  src/
    main.rs          # Entry point, Slint app initialization
    lib.rs           # Re-exports for testing
  ui/
    main.slint       # Main window definition
    widgets/         # Reusable widget components (later phases)
  assets/
    CLASSIC.ico      # Window icon (copy from Python GUI)
```

### Pattern 1: AsyncBridge for Worker Operations
**What:** Use existing `AsyncBridge::run_with_ui_update()` for background work with UI callback
**When to use:** Any operation that shouldn't block UI (file I/O, scanning, network)
**Example:**
```rust
// Source: classic-shared-core/src/async_bridge.rs (existing code)
use classic_shared_core::AsyncBridge;

// In a Slint button callback:
let window_weak = window.as_weak();
AsyncBridge::run_with_ui_update(
    async move {
        // This runs on Tokio runtime
        perform_scan().await
    },
    move |result| {
        // This runs on Slint event loop
        if let Some(w) = window_weak.upgrade() {
            w.set_progress(100.0);
            w.set_status("Complete".into());
        }
    }
);
```

### Pattern 2: Progress Updates via upgrade_in_event_loop
**What:** Send incremental progress from worker to UI without callback overhead
**When to use:** Long operations needing frequent UI updates (scanning multiple files)
**Example:**
```rust
// Source: Slint documentation - upgrade_in_event_loop pattern
use std::thread;
use std::time::Duration;

let window_weak = window.as_weak();
thread::spawn(move || {
    for i in 0..100 {
        // Simulate work
        thread::sleep(Duration::from_millis(50));

        // Update UI from worker thread
        let progress = i as f32;
        window_weak.upgrade_in_event_loop(move |window| {
            window.set_progress(progress);
            window.set_status(format!("Processing {}%...", i).into());
        }).ok();
    }
});
```

### Pattern 3: Cancellation with CancellationToken
**What:** Cooperative cancellation for stoppable operations
**When to use:** Scan operations that user may want to cancel
**Example:**
```rust
// Source: tokio-util documentation
use tokio_util::sync::CancellationToken;
use tokio::select;

let token = CancellationToken::new();
let token_clone = token.clone();

// Store token in UI state for cancel button
// ...

// In worker:
classic_shared_core::get_runtime().spawn(async move {
    for path in log_paths {
        select! {
            _ = token_clone.cancelled() => {
                // Clean up and exit
                return;
            }
            result = process_log(&path) => {
                // Continue processing
            }
        }
    }
});

// Cancel button callback:
token.cancel();
```

### Pattern 4: Slint Build Configuration
**What:** build.rs compiles .slint files to Rust at build time
**When to use:** Every GUI application using Slint
**Example:**
```rust
// Source: slint-build crate documentation
// build.rs
fn main() {
    slint_build::compile("ui/main.slint").unwrap();
}

// main.rs
slint::include_modules!();

fn main() {
    let window = MainWindow::new().unwrap();
    window.run().unwrap();
}
```

### Anti-Patterns to Avoid
- **Creating new Tokio runtime:** NEVER call `Runtime::new()`. Use `classic_shared_core::get_runtime()` exclusively.
- **Blocking UI thread:** Don't call `block_on()` from Slint callbacks. Use `AsyncBridge` or `spawn_local`.
- **Direct UI updates from workers:** Never set Slint properties from non-UI threads. Use `invoke_from_event_loop` or `upgrade_in_event_loop`.
- **Polling in event loop:** Don't spin-wait. Use channels or callbacks for cross-thread communication.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async/UI coordination | Custom thread pool + channels | `AsyncBridge` in classic-shared-core | Already handles thread transitions correctly |
| Cancellation | Boolean flags | `tokio_util::sync::CancellationToken` | Atomic, correct, supports child tokens |
| Progress throttling | Manual timers | `upgrade_in_event_loop` batching | Slint coalesces rapid updates automatically |
| Image loading | Manual file parsing | `slint::Image::load_from_path()` | Handles formats, errors, caching |

**Key insight:** The async bridge already exists in the codebase. This phase wires it up to a real Slint application, not reinvents it.

## Common Pitfalls

### Pitfall 1: Tokio Runtime Conflicts
**What goes wrong:** Creating multiple Tokio runtimes causes panics ("Cannot start a runtime from within a runtime")
**Why it happens:** Easy to accidentally call `Runtime::new()` or use `#[tokio::main]` macro
**How to avoid:** Use ONLY `classic_shared_core::get_runtime()`. Never use `#[tokio::main]`.
**Warning signs:** "Cannot start a runtime" panic, application hangs on async operations

### Pitfall 2: Skia Build Path Spaces on Windows
**What goes wrong:** Compilation fails with "multiple source files" errors
**Why it happens:** Default CARGO_HOME on Windows may contain spaces in username path
**How to avoid:** Set `CARGO_HOME=C:\cargo_home` or similar space-free path
**Warning signs:** Build errors mentioning "unused linker input", path fragments in error messages

### Pitfall 3: Missing MSVC Runtime on Windows
**What goes wrong:** Application terminates immediately without error
**Why it happens:** Skia renderer requires Visual C++ Redistributable
**How to avoid:** Ensure MSVC 2022 is installed with latest patches; include VC++ Redist in distribution
**Warning signs:** .exe starts then exits with no console output, works on dev machine only

### Pitfall 4: UI Updates from Wrong Thread
**What goes wrong:** UI doesn't update, panics about thread safety
**Why it happens:** Setting Slint properties directly from Tokio worker threads
**How to avoid:** Always use `invoke_from_event_loop()` or `upgrade_in_event_loop()` for UI updates
**Warning signs:** "not on UI thread" errors, silent update failures, intermittent crashes

### Pitfall 5: Forgetting gui-bridge Feature
**What goes wrong:** AsyncBridge not found, missing slint dependency
**Why it happens:** `classic-shared-core` has AsyncBridge behind optional feature
**How to avoid:** Explicitly enable: `classic-shared-core = { ..., features = ["gui-bridge"] }`
**Warning signs:** "cannot find AsyncBridge" compile error, missing `slint::invoke_from_event_loop`

## Code Examples

Verified patterns from official sources:

### Main Application Entry Point
```rust
// Source: Slint documentation + existing async_bridge.rs patterns
// main.rs
slint::include_modules!();

use classic_shared_core::get_runtime;

fn main() {
    // Initialize global Tokio runtime (ONE RUNTIME RULE)
    // This triggers lazy initialization before Slint event loop starts
    let _ = get_runtime();

    // Create and configure window
    let window = MainWindow::new().expect("Failed to create window");

    // Set up callbacks
    setup_callbacks(&window);

    // Run event loop (blocks until window closes)
    window.run().expect("Failed to run application");
}

fn setup_callbacks(window: &MainWindow) {
    let window_weak = window.as_weak();

    window.on_start_scan(move || {
        let window_weak = window_weak.clone();

        classic_shared_core::AsyncBridge::run_with_ui_update(
            async move {
                // Simulated long operation
                tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                "Scan complete!".to_string()
            },
            move |result| {
                if let Some(w) = window_weak.upgrade() {
                    w.set_status(result.into());
                }
            }
        );
    });
}
```

### Progress Callback Pattern
```rust
// Source: Slint GitHub discussions #4175, #8466
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

fn start_scan_with_progress(window: &MainWindow) {
    let window_weak = window.as_weak();
    let cancelled = Arc::new(AtomicBool::new(false));
    let cancelled_clone = cancelled.clone();

    // Store cancellation flag for cancel button
    // (In real impl, store in application state)

    std::thread::spawn(move || {
        let files = vec!["log1.txt", "log2.txt", "log3.txt"];
        let total = files.len() as f32;

        for (i, file) in files.iter().enumerate() {
            if cancelled_clone.load(Ordering::Relaxed) {
                // Cancelled - update UI and exit
                window_weak.upgrade_in_event_loop(|w| {
                    w.set_status("Cancelled".into());
                    w.set_progress(0.0);
                }).ok();
                return;
            }

            // Simulate processing
            std::thread::sleep(std::time::Duration::from_millis(500));

            // Update progress
            let progress = ((i + 1) as f32 / total) * 100.0;
            let status = format!("Processing {}...", file);
            window_weak.upgrade_in_event_loop(move |w| {
                w.set_progress(progress);
                w.set_status(status.into());
            }).ok();
        }

        // Complete
        window_weak.upgrade_in_event_loop(|w| {
            w.set_status("Complete".into());
            w.set_progress(100.0);
        }).ok();
    });
}
```

### Slint UI Definition
```slint
// Source: Slint documentation patterns
// ui/main.slint
import { Button, ProgressIndicator, TabWidget, Tab, VerticalBox, HorizontalBox } from "std-widgets.slint";

export component MainWindow inherits Window {
    title: "Crash Log Auto Scanner & Setup Integrity Checker | CLASSIC v9.0.0";
    icon: @image-url("../assets/CLASSIC.ico");
    preferred-width: 650px;
    preferred-height: 580px;
    min-width: 550px;
    min-height: 580px;

    // Properties accessible from Rust
    in-out property <float> progress: 0;
    in-out property <string> status: "Ready";

    // Callbacks invoked from UI
    callback start-scan();
    callback cancel-scan();

    VerticalBox {
        padding: 10px;
        spacing: 10px;

        TabWidget {
            Tab {
                title: "MAIN OPTIONS";
                VerticalBox {
                    // Main options content (placeholder)
                    Text { text: "Main options will appear here"; }

                    HorizontalBox {
                        Button {
                            text: "Scan Crash Logs";
                            clicked => { root.start-scan(); }
                        }
                        Button {
                            text: "Cancel";
                            clicked => { root.cancel-scan(); }
                        }
                    }
                }
            }
            Tab {
                title: "FILE BACKUP";
                Text { text: "Backup options will appear here"; }
            }
            Tab {
                title: "ARTICLES";
                Text { text: "Articles will appear here"; }
            }
            Tab {
                title: "RESULTS";
                Text { text: "Results will appear here"; }
            }
        }

        // Progress area
        VerticalBox {
            ProgressIndicator {
                progress: root.progress / 100;
            }
            Text {
                text: root.status;
                horizontal-alignment: center;
            }
        }
    }
}
```

### build.rs Configuration
```rust
// Source: slint-build documentation
// build.rs
fn main() {
    slint_build::compile("ui/main.slint").expect("Slint compilation failed");
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| spawn_local for all async | spawn_local for UI-only, runtime.spawn for real async | Slint 1.0+ | Proper Tokio integration |
| Qt backend default | backend-winit default (non-Linux) | Slint 1.2+ | More portable, less dependencies |
| femtovg default renderer | Choice of femtovg/skia/software | Slint 1.4+ | Skia for best text/graphics quality |

**Deprecated/outdated:**
- `sixtyfps` crate name: Renamed to `slint` in 0.2.0
- `invoke_from_event_loop` returning `()`: Now returns `Result` since 1.0
- Direct Qt dependency: No longer required with winit backend

## Open Questions

Things that couldn't be fully resolved:

1. **Exact .ico loading behavior on Windows**
   - What we know: `@image-url()` in Slint supports ICO via `image-default-formats` feature
   - What's unclear: Whether Windows taskbar uses the embedded icon correctly
   - Recommendation: Test during implementation; may need Windows resource embedding for taskbar

2. **fluent-dark automatic detection**
   - What we know: Slint auto-selects dark variant based on system setting
   - What's unclear: Whether explicit `SLINT_STYLE=fluent-dark` is needed for consistency
   - Recommendation: Test both approaches; prefer system detection for user preference respect

## Sources

### Primary (HIGH confidence)
- [Slint Backends & Renderers](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/) - Renderer feature flags, Windows build requirements
- [Slint crate feature flags](https://lib.rs/crates/slint/features) - Complete feature list
- [slint-build crate](https://lib.rs/crates/slint-build) - Build script usage
- [Slint Image struct](https://docs.rs/slint/latest/slint/struct.Image.html) - Image loading patterns
- [Slint Window reference](https://docs.slint.dev/latest/docs/slint/reference/window/window/) - Window properties
- [CancellationToken docs](https://docs.rs/tokio-util/latest/tokio_util/sync/struct.CancellationToken.html) - Cancellation patterns
- Existing `classic-shared-core/src/async_bridge.rs` - Project's async bridge implementation

### Secondary (MEDIUM confidence)
- [Slint + async Rust discussion #4377](https://github.com/slint-ui/slint/discussions/4377) - Community patterns
- [Progress callback discussion #4175](https://github.com/slint-ui/slint/discussions/4175) - upgrade_in_event_loop pattern
- [Tokio task cancellation patterns](https://cybernetist.com/2024/04/19/rust-tokio-task-cancellation-patterns/) - Cancellation best practices

### Tertiary (LOW confidence)
- None - all claims verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - workspace already has slint/tokio, async_bridge exists
- Architecture: HIGH - patterns verified against Slint docs and existing code
- Pitfalls: HIGH - Windows Skia issues documented officially, runtime conflicts well-understood

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (Slint releases monthly; core patterns stable)
