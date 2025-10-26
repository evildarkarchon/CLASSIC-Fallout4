# Slint GUI Development Guide

This guide covers development of the pure Rust GUI application built with Slint (`classic-gui-slint`).

## Overview

CLASSIC includes a pure Rust GUI application built with Slint. The GUI uses modern Fluent Design System styling and provides a native desktop experience.

## Dual Event Loop Architecture

The Slint GUI must coordinate between **two separate event loops**:

1. **Slint Event Loop** - Runs on the main thread, handles UI rendering and user interactions
2. **Tokio Runtime** - Shared multi-threaded async runtime for I/O operations (ONE RUNTIME RULE)

**Challenge**: Slint callbacks run on the main thread and are synchronous, but many operations (file I/O, scanning, backups) are async. We need to bridge between these two worlds without blocking the UI.

## AsyncBridge Pattern

The `AsyncBridge` module in `classic-shared` solves this coordination problem, inspired by Python's AsyncBridge pattern:

```rust
use classic_shared::AsyncBridge;

// In a Slint button callback:
main_window.on_scan_crash_logs({
    let window_weak = main_window.as_weak();
    let state = app_state.clone();
    move || {
        // Set loading state immediately (runs on UI thread)
        if let Some(w) = window_weak.upgrade() {
            w.set_scan_in_progress(true);
        }

        // Execute async operation via AsyncBridge
        AsyncBridge::run_with_ui_update(
            perform_scan(state),  // Runs on Tokio runtime
            move |result| {       // Runs on Slint event loop
                // Update UI with result
                if let Some(w) = window_weak.upgrade() {
                    w.set_scan_in_progress(false);
                    match result {
                        Ok(data) => w.show_success(&data),
                        Err(e) => w.show_error(&e.to_string()),
                    }
                }
            }
        );
    }
});
```

## AsyncBridge API

### `run_with_ui_update<F, R, C>(operation: F, on_complete: C)`
Execute an async operation and invoke a callback on the Slint event loop.

- **Use when**: You need to run async work and update UI with results
- **Pattern**: Background thread → Tokio runtime → UI callback
- **Thread safety**: Both operation and callback must be `Send + 'static`

```rust
AsyncBridge::run_with_ui_update(
    async { tokio::fs::read_to_string("file.txt").await },
    |result| {
        // Update UI here
        window.set_text(result.unwrap().into());
    }
);
```

### `spawn_background<F>(operation: F)`
Execute an async operation without a callback (fire-and-forget).

- **Use when**: Background tasks that don't need UI updates (logging, analytics)
- **Pattern**: Background thread → Tokio runtime

```rust
AsyncBridge::spawn_background(async {
    log_user_action("button_clicked").await;
});
```

### `invoke_on_ui_thread<F>(f: F)`
Invoke a function directly on the Slint event loop.

- **Use when**: You're already in an async context and need to update UI
- **Pattern**: Any thread → Slint event loop

```rust
AsyncBridge::invoke_on_ui_thread(|| {
    window.set_status("Ready".into());
});
```

### `run_with_loading<F, R, L, C>(set_loading: L, operation: F, on_complete: C)`
Higher-level convenience method with automatic loading state management.

- **Use when**: Operations that should show loading indicators
- **Pattern**: Auto-manages loading flag before/after operation

```rust
AsyncBridge::run_with_loading(
    |loading| window.set_loading(loading),
    fetch_data(),
    |result| display_result(result)
);
```

## Development Guidelines

### ✅ DO: Use AsyncBridge for Async Operations
```rust
// ✅ CORRECT - Uses AsyncBridge
main_window.on_backup_xse({
    let window = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            perform_backup(),
            |result| { /* update UI */ }
        );
    }
});
```

### ❌ DON'T: Block the Slint Event Loop
```rust
// ❌ WRONG - Blocks UI thread
main_window.on_backup_xse({
    move || {
        // This blocks the entire UI!
        let result = classic_shared::get_runtime().block_on(perform_backup());
        window.set_result(result);
    }
});
```

### ✅ DO: Use slint::spawn_local for Slint-Aware Async
When you need more control or want to use Slint's built-in async support:

```rust
main_window.on_scan_logs({
    let window = main_window.as_weak();
    move || {
        slint::spawn_local(async move {
            if let Some(w) = window.upgrade() {
                w.set_loading(true);
            }

            let result = handlers::scan::handle_scan().await;

            if let Some(w) = window.upgrade() {
                w.set_loading(false);
                w.display_result(result);
            }
        }).unwrap();
    }
});
```

**Note**: `slint::spawn_local` runs the async block on Slint's event loop, so you can freely call UI methods within it. However, for CPU-intensive or blocking operations, prefer `AsyncBridge` to avoid blocking the UI.

### ❌ DON'T: Forget to Handle Window Upgrades
```rust
// ❌ WRONG - Doesn't check if window still exists
AsyncBridge::run_with_ui_update(
    perform_backup(),
    |result| {
        window.set_result(result);  // May panic if window closed!
    }
);
```

```rust
// ✅ CORRECT - Always check window upgrade
AsyncBridge::run_with_ui_update(
    perform_backup(),
    move |result| {
        if let Some(w) = window_weak.upgrade() {
            w.set_result(result);
        }
    }
);
```

### ✅ DO: Clone Data Before Moving into Closures
```rust
// ✅ CORRECT - Clone what you need
main_window.on_backup_xse({
    let window = main_window.as_weak();
    let state = app_state.clone();  // Clone Arc
    move || {
        AsyncBridge::run_with_ui_update(
            perform_backup(state.clone()),
            move |result| { /* ... */ }
        );
    }
});
```

## Common Patterns

### Pattern 1: Simple Async Operation with UI Update
```rust
main_window.on_button_clicked({
    let window = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            async_operation(),
            move |result| {
                if let Some(w) = window.upgrade() {
                    w.handle_result(result);
                }
            }
        );
    }
});
```

### Pattern 2: Operation with Loading State
```rust
main_window.on_button_clicked({
    let window = main_window.as_weak();
    move || {
        // Set loading immediately
        if let Some(w) = window.upgrade() {
            w.set_loading(true);
        }

        AsyncBridge::run_with_ui_update(
            async_operation(),
            move |result| {
                if let Some(w) = window.upgrade() {
                    w.set_loading(false);
                    w.handle_result(result);
                }
            }
        );
    }
});
```

### Pattern 3: Multiple Parallel Operations
```rust
AsyncBridge::run_with_ui_update(
    async {
        // Run multiple operations in parallel
        let (result1, result2, result3) = tokio::join!(
            operation1(),
            operation2(),
            operation3()
        );
        (result1, result2, result3)
    },
    move |results| {
        if let Some(w) = window.upgrade() {
            w.display_results(results);
        }
    }
);
```

### Pattern 4: Macro for Reducing Boilerplate
```rust
// Define once for repetitive operations
macro_rules! setup_backup_operation {
    ($window:expr, $callback:ident, $operation:expr) => {
        $window.$callback({
            let window = $window.as_weak();
            move || {
                AsyncBridge::run_with_ui_update(
                    $operation,
                    move |result| {
                        if let Some(w) = window.upgrade() {
                            w.handle_backup_result(result);
                        }
                    }
                );
            }
        });
    };
}

// Use for multiple similar operations
setup_backup_operation!(main_window, on_backup_xse, perform_xse_backup());
setup_backup_operation!(main_window, on_backup_enb, perform_enb_backup());
```

## Building and Running

```bash
# Build and run Slint GUI
cargo run -p classic-gui-slint

# Build release version
cargo build -p classic-gui-slint --release

# Enable GUI bridge feature in classic-shared
# (automatically enabled by classic-gui-slint dependency)
```

## Troubleshooting

### Issue: UI freezes during operation
**Cause**: Blocking the Slint event loop
**Solution**: Ensure all long-running operations use `AsyncBridge` or `slint::spawn_local`

### Issue: "Failed to invoke callback on Slint event loop"
**Cause**: Slint event loop may have exited
**Solution**: Check that window still exists before invoking callbacks

### Issue: Nested runtime errors
**Cause**: Using `get_runtime().block_on()` from within an async context
**Solution**: Use `AsyncBridge::run_with_ui_update()` which properly coordinates threads

### Issue: Data race or shared state corruption
**Cause**: Modifying shared state from multiple threads without synchronization
**Solution**: Use `Arc<RwLock<T>>` for shared state (see `SharedAppState` pattern)

## Key Differences from Python AsyncBridge

The Rust `AsyncBridge` in `classic-shared` is conceptually similar to Python's `AsyncBridge` but adapted for Rust's ownership model and Slint's event loop:

| Python AsyncBridge | Rust AsyncBridge |
|-------------------|------------------|
| `asyncio.run()` in thread pool | `get_runtime().block_on()` in background thread |
| Python's GIL for thread safety | Rust's `Send + 'static` bounds |
| Direct callback invocation | `slint::invoke_from_event_loop()` |
| Weak references | `Weak<SlintComponent>` |

Both follow the same pattern: **spawn background thread → run async on runtime → callback on UI thread**.
