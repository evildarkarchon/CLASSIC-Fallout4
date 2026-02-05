---
# Frontmatter - Machine readable metadata
phase: 19-foundation-and-async-bridge
plan: 02
subsystem: gui
tags: [slint, async, tokio, asyncbridge, cancellation, progress]

# What this plan builds on and provides
dependency-graph:
  requires:
    - 19-01 # classic-gui crate structure
  provides:
    - AsyncBridge callback wiring pattern
    - Worker thread with progress callbacks
    - Cooperative cancellation via CancellationToken
  affects:
    - 20-03 # Game detection will use this async pattern
    - 21-xx # All orchestrator integration uses this pattern
    - All future async GUI operations

# Track technology choices
tech-stack:
  added:
    - parking_lot (thread-safe mutex for callback state)
  patterns:
    - AsyncBridge::run_with_ui_update for async-to-UI coordination
    - upgrade_in_event_loop for progress callbacks
    - CancellationToken for cooperative cancellation
    - ScanWindowProperties trait for testability

# Files affected
key-files:
  created:
    - rust/ui-applications/classic-gui/src/worker.rs
  modified:
    - rust/ui-applications/classic-gui/src/main.rs
    - rust/ui-applications/classic-gui/src/lib.rs
    - rust/ui-applications/classic-gui/ui/main.slint
    - rust/ui-applications/classic-gui/Cargo.toml

# Important decisions made
decisions:
  - id: scan-property-prefix
    choice: Use scan- prefix for properties (scan-progress, scan-status)
    reason: Distinguishes scan-related properties from future general properties
  - id: trait-abstraction
    choice: ScanWindowProperties trait for window abstraction
    reason: Enables testing without Slint-generated code dependency

# Metrics
metrics:
  duration: 4m
  completed: 2026-02-05
---

# Phase 19 Plan 02: AsyncBridge Integration Summary

**AsyncBridge wiring with worker thread pattern, progress callbacks, and cooperative cancellation**

## What Was Built

### 1. Worker Module (worker.rs)
Created a worker module demonstrating the async pattern that all future scan operations will follow:

- **simulate_scan function**: Async operation that processes files with progress updates
- **ScanWindowProperties trait**: Abstracts Slint-generated window properties for testability
- **Progress callbacks**: Uses `upgrade_in_event_loop` for thread-safe UI updates
- **Cancellation**: CancellationToken for cooperative cancellation

### 2. Callback Wiring (main.rs)
Implemented the full callback infrastructure:

- **ScanWindowProperties impl**: Connects trait to Slint-generated MainWindow
- **AppState**: Shared state struct holding CancellationToken
- **on_start_scan callback**: Creates token, sets UI state, spawns async via AsyncBridge
- **on_cancel_scan callback**: Triggers cancellation token

### 3. UI Property Updates (main.slint)
Updated property names for Rust compatibility:

- `progress` -> `scan-progress` (generates `set_scan_progress()`)
- `status` -> `scan-status` (generates `set_scan_status()`)
- Updated ProgressIndicator and Text bindings

## Key Pattern Established

```rust
// From any Slint callback:
AsyncBridge::run_with_ui_update(
    async_operation(window_weak.clone(), cancel_token),
    |result| {
        // Handle completion on UI thread
    }
);

// From async operation:
let _ = window_weak.upgrade_in_event_loop(move |window| {
    window.set_scan_progress(progress);
    window.set_scan_status(status.into());
});
```

This pattern:
1. Keeps UI thread responsive
2. Runs async work on Tokio runtime (ONE RUNTIME RULE)
3. Updates UI safely via event loop
4. Supports cooperative cancellation

## Commits

| Commit | Description |
|--------|-------------|
| b028e36c | Add worker module with cancellation support |
| 42338509 | Wire AsyncBridge callbacks with progress and cancellation |

## Verification Results

- [x] cargo build -p classic-gui succeeds
- [x] cargo clippy -p classic-gui passes (only Slint-generated warnings)
- [x] Release build produces working executable
- [x] Application starts without runtime panics
- [x] No Tokio runtime conflicts (ONE RUNTIME RULE followed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Clippy] Fixed useless vec! warning**
- **Found during:** Task 2
- **Issue:** Using `vec![]` for static data when array suffices
- **Fix:** Changed to array literal `[...]`
- **Files modified:** worker.rs
- **Commit:** 42338509

## Next Phase Readiness

Phase 19 Foundation complete. Ready for:
- **Phase 20**: Settings and configuration loading (uses AsyncBridge pattern)
- **Phase 21**: OrchestratorCore integration (replaces simulate_scan with real scanning)

## Testing Notes

Interactive verification requires manual testing:
1. Click "Scan Crash Logs" - should show progress incrementally
2. Watch progress bar fill over ~2.5 seconds (5 files x 500ms)
3. Status should show current file name
4. Cancel mid-scan - should stop and reset
5. UI should remain responsive throughout (tabs switch, window resizes)
