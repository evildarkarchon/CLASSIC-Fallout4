# Phase 21: Scan Operations - Research

**Researched:** 2026-02-05
**Domain:** Slint GUI async operations, Rust OrchestratorCore integration, progress reporting
**Confidence:** HIGH

## Summary

This phase wires the existing Rust OrchestratorCore business logic to the Slint GUI, replacing the simulated scan in worker.rs with real crash log analysis. The research confirms that all foundational components are already in place:

1. **OrchestratorCore** (classic-scanlog-core): Full async crash log analysis with `process_log()` and `process_logs_batch()` methods
2. **LogCollector** (classic-file-io-core): Async log discovery from F4SE directories and custom paths
3. **AsyncBridge** (classic-shared-core): Proven pattern for Slint-Tokio coordination via `run_with_ui_update()`
4. **CancellationToken** (tokio-util): Already used in worker.rs for cooperative cancellation

The key challenge is connecting these components while respecting the CONTEXT.md decisions:
- Morphing Scan/Cancel button (single button, dual purpose)
- Status bar with indeterminate -> determinate progress transition
- Partial results preservation on cancellation
- Auto-switch to Results tab on successful completion

**Primary recommendation:** Replace `simulate_scan()` with a `scan_crash_logs()` function that uses LogCollector for discovery, OrchestratorCore for analysis, and reports progress via `upgrade_in_event_loop()`.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| classic-scanlog-core | workspace | OrchestratorCore for log analysis | Already exists, fully tested |
| classic-file-io-core | workspace | LogCollector for log discovery | Already exists, async-native |
| classic-shared-core | workspace | AsyncBridge for UI coordination | Already used in Phase 20 |
| tokio-util | workspace | CancellationToken | Already in Cargo.toml |
| slint | 1.15.0 | UI framework | Already in workspace |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| parking_lot | workspace | Mutex for shared state | Already used in main.rs AppState |
| directories | workspace | Config file paths | Already used for state persistence |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tokio_util::CancellationToken | Arc<AtomicBool> | CancellationToken is cleaner, already in use |
| LogCollector | Manual glob | LogCollector handles XSE paths, move/copy operations |

**No new dependencies required - all components already exist in workspace.**

## Architecture Patterns

### Recommended Project Structure
```
rust/ui-applications/classic-gui/
  src/
    main.rs              # Entry point (UPDATE: wire real scan)
    lib.rs               # Re-exports (UPDATE: add scan_crash_logs)
    worker.rs            # UPDATE: Replace simulate_scan with real implementation
    state.rs             # Window state (no changes)
    dialogs.rs           # File dialogs (no changes)
    scan.rs              # NEW: Scan orchestration module
  ui/
    main.slint           # UPDATE: Morphing button, status bar
```

### Pattern 1: Scan Orchestration Function
**What:** Async function that coordinates log discovery, analysis, and progress reporting
**When to use:** When start-scan button is clicked
**Example:**
```rust
// Source: Existing patterns in worker.rs + orchestrator.rs
pub async fn scan_crash_logs<W>(
    window_weak: Weak<W>,
    cancel_token: CancellationToken,
    crash_log_path: String,
    xse_folder: Option<String>,
) -> Result<ScanResult, String>
where
    W: slint::ComponentHandle + ScanWindowProperties + 'static,
{
    // Phase 1: Log discovery (indeterminate progress)
    update_status(&window_weak, "Discovering crash logs...", -1.0);

    let collector = LogCollector::new(
        PathBuf::from(&crash_log_path),
        xse_folder.map(PathBuf::from),
        None,
    );

    let log_paths = collector.collect_all().await
        .map_err(|e| format!("Failed to collect logs: {}", e))?;

    if log_paths.is_empty() {
        return Err("No crash logs found".to_string());
    }

    let total = log_paths.len();

    // Phase 2: Analysis (determinate progress)
    let mut results = Vec::new();
    let mut errors = 0;

    for (i, path) in log_paths.iter().enumerate() {
        if cancel_token.is_cancelled() {
            return Ok(ScanResult::cancelled(results, i, total));
        }

        let filename = path.file_name().map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        let progress = ((i + 1) as f32 / total as f32) * 100.0;

        update_progress(&window_weak, progress, &filename);

        match orchestrator.process_log(path.to_string_lossy().to_string()).await {
            Ok(result) => results.push(result),
            Err(_) => errors += 1,
        }
    }

    Ok(ScanResult::complete(results, errors))
}
```

### Pattern 2: Morphing Button State
**What:** Single button that toggles between Scan and Cancel based on scan-in-progress
**When to use:** CONTEXT.md decision - single button, dual purpose
**Example:**
```slint
// Source: CONTEXT.md decision + Slint patterns
Button {
    text: root.scan-in-progress ? "Cancel" : "Scan Crash Logs";
    primary: !root.scan-in-progress;  // Primary style only when Scan
    clicked => {
        if (root.scan-in-progress) {
            root.cancel-scan();
        } else {
            root.start-scan();
        }
    }
}
```

### Pattern 3: Indeterminate/Determinate Progress Transition
**What:** Show spinning animation during discovery, then switch to percentage during analysis
**When to use:** CONTEXT.md decision - indeterminate during enumeration
**Example:**
```slint
// Source: Slint ProgressIndicator docs
ProgressIndicator {
    // indeterminate: true when progress < 0
    indeterminate: root.scan-progress < 0;
    progress: root.scan-progress >= 0 ? root.scan-progress / 100 : 0;
}
```

### Pattern 4: Status Bar Update with Filename
**What:** Show current filename being scanned alongside percentage
**When to use:** CONTEXT.md decision - progress bar shows percentage + current filename
**Example:**
```rust
// Source: Existing upgrade_in_event_loop pattern in worker.rs
fn update_progress<W: ScanWindowProperties + slint::ComponentHandle>(
    window_weak: &Weak<W>,
    progress: f32,
    filename: &str,
) {
    let status = format!("{:.0}% - Scanning {}...", progress, filename);
    let _ = window_weak.upgrade_in_event_loop(move |window| {
        window.set_scan_progress(progress);
        window.set_scan_status(status.into());
    });
}
```

### Pattern 5: Auto-Clear Status Bar with Timer
**What:** Clear status bar after delay when scan completes
**When to use:** CONTEXT.md decision - status bar auto-clears after delay
**Example:**
```rust
// Source: Tokio timer patterns
async fn auto_clear_status<W: ScanWindowProperties + slint::ComponentHandle>(
    window_weak: Weak<W>,
    delay_ms: u64,
) {
    tokio::time::sleep(Duration::from_millis(delay_ms)).await;
    let _ = window_weak.upgrade_in_event_loop(|window| {
        window.set_scan_status("".into());
    });
}
```

### Anti-Patterns to Avoid
- **Blocking the UI thread:** Never call `block_on()` from Slint callbacks. Use `AsyncBridge::run_with_ui_update()`.
- **Direct window access from async:** Always use `upgrade_in_event_loop()` for UI updates.
- **Ignoring cancellation between logs:** Check `cancel_token.is_cancelled()` before each log, not just at start.
- **Discarding partial results:** Keep completed results on cancellation per CONTEXT.md.
- **Separate Scan and Cancel buttons:** CONTEXT.md specifies morphing single button.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log discovery | Manual glob + XSE path logic | LogCollector | Handles all edge cases (move/copy, XSE folders) |
| Log analysis | Custom parser | OrchestratorCore | Full feature parity, tested |
| Async-UI coordination | Manual spawn + mutex | AsyncBridge | Proven pattern, handles thread transitions |
| Cancellation | Arc<AtomicBool> + manual checks | CancellationToken | Cleaner API, already in use |
| Progress tracking | Manual counter | LogCollector returns Vec for enumeration, then iterate | Natural progress from batch size |

**Key insight:** All business logic already exists in -core crates. This phase is pure integration work.

## Common Pitfalls

### Pitfall 1: Creating New OrchestratorCore Per Scan
**What goes wrong:** Expensive initialization (regex compilation, config loading) on every scan
**Why it happens:** Creating orchestrator inside the async function
**How to avoid:** Create OrchestratorCore once at app startup, share via Arc
**Warning signs:** Slow scan start, 100-200ms delay before first log

### Pitfall 2: Progress Updates Flood UI Thread
**What goes wrong:** UI becomes sluggish with rapid progress updates
**Why it happens:** Calling upgrade_in_event_loop for every percentage point
**How to avoid:** Throttle updates to ~10Hz (100ms intervals) or update only on file boundaries
**Warning signs:** Progress bar stuttering, main window unresponsive during scan

### Pitfall 3: Status Bar Never Clears
**What goes wrong:** Old status message stays visible after scan completes
**Why it happens:** No timer to auto-clear, or timer task gets dropped
**How to avoid:** Spawn a separate task for auto-clear that keeps window_weak alive
**Warning signs:** "Scanned 12 logs" message stays visible indefinitely

### Pitfall 4: Cancel Doesn't Stop Fast Enough
**What goes wrong:** One or more logs process after cancel is clicked
**Why it happens:** Checking cancellation only at start of batch, not between logs
**How to avoid:** Check `cancel_token.is_cancelled()` in loop before each `process_log()`
**Warning signs:** "Cancelled (5 of 10 logs)" but 6 logs actually processed

### Pitfall 5: Auto-Switch to Wrong Tab
**What goes wrong:** Switches to Results even on cancel or zero logs
**Why it happens:** Not checking scan result status before switching
**How to avoid:** Only switch tab when `results.len() > 0 && !cancelled`
**Warning signs:** User sees empty Results tab after cancelling

### Pitfall 6: Missing YamlData Configuration
**What goes wrong:** OrchestratorCore created without proper game configuration
**Why it happens:** Not loading YamlData/settings before creating orchestrator
**How to avoid:** Load settings at startup or use AnalysisConfig::from_yamldata()
**Warning signs:** Missing suspect patterns, empty mod databases, no FormID lookups

## Code Examples

Verified patterns from existing codebase:

### ScanResult Structure
```rust
// Source: Pattern derived from AnalysisResult in orchestrator.rs
pub struct ScanResult {
    /// Reports from successfully analyzed logs
    pub reports: Vec<AnalysisResult>,
    /// Number of logs that encountered errors
    pub error_count: usize,
    /// Total logs attempted (for cancelled display)
    pub attempted: usize,
    /// Total logs found
    pub total: usize,
    /// Whether scan was cancelled
    pub cancelled: bool,
}

impl ScanResult {
    pub fn complete(reports: Vec<AnalysisResult>, errors: usize) -> Self {
        let total = reports.len() + errors;
        Self {
            reports,
            error_count: errors,
            attempted: total,
            total,
            cancelled: false,
        }
    }

    pub fn cancelled(reports: Vec<AnalysisResult>, attempted: usize, total: usize) -> Self {
        Self {
            error_count: 0,
            reports,
            attempted,
            total,
            cancelled: true,
        }
    }

    pub fn format_status(&self) -> String {
        if self.cancelled {
            format!("Cancelled ({} of {} logs)", self.attempted, self.total)
        } else if self.error_count > 0 {
            format!("Scanned {} logs ({} errors)", self.total, self.error_count)
        } else {
            format!("Scanned {} logs", self.total)
        }
    }
}
```

### Updated Main.slint with Morphing Button
```slint
// Source: CONTEXT.md decision + existing main.slint structure
// Key change: single button with conditional text/action

// Scan button (morphs to Cancel during scan)
HorizontalBox {
    alignment: center;

    Button {
        text: root.scan-in-progress ? "Cancel" : "Scan Crash Logs";
        primary: !root.scan-in-progress;
        clicked => {
            if (root.scan-in-progress) {
                root.cancel-scan();
            } else {
                root.start-scan();
            }
        }
    }
}
```

### Complete Scan Workflow Integration
```rust
// Source: Pattern from main.rs setup_scan_callbacks + worker.rs simulate_scan
fn setup_scan_callback(window: &MainWindow, state: &Arc<Mutex<AppState>>) {
    let window_weak = window.as_weak();
    let state = Arc::clone(state);

    window.on_start_scan(move || {
        let window_weak = window_weak.clone();
        let state = Arc::clone(&state);

        // Create cancellation token
        let cancel_token = CancellationToken::new();
        {
            let mut state = state.lock();
            state.cancel_token = Some(cancel_token.clone());
        }

        // Get paths from UI
        let crash_log_path = window_weak.upgrade()
            .map(|w| w.get_crash_log_path().to_string())
            .unwrap_or_default();

        // Set UI to scanning state (immediate progress display)
        if let Some(w) = window_weak.upgrade() {
            w.set_scan_in_progress(true);
            w.set_scan_progress(-1.0); // Indeterminate
            w.set_scan_status("Discovering crash logs...".into());
        }

        // Spawn scan operation
        AsyncBridge::run_with_ui_update(
            scan_crash_logs(window_weak.clone(), cancel_token, crash_log_path, None),
            move |result| {
                if let Some(w) = window_weak.upgrade() {
                    match result {
                        Ok(scan_result) => {
                            w.set_scan_progress(100.0);
                            w.set_scan_status(scan_result.format_status().into());
                            w.set_scan_in_progress(false);

                            // Auto-switch to Results only on success with results
                            if !scan_result.cancelled && !scan_result.reports.is_empty() {
                                w.set_active_tab_index(1); // Results tab
                            }

                            // TODO: Store scan_result.reports for Results tab
                        }
                        Err(msg) => {
                            w.set_scan_progress(0.0);
                            w.set_scan_status(msg.into());
                            w.set_scan_in_progress(false);
                        }
                    }

                    // Auto-clear status after delay
                    let window_weak_for_clear = window_weak.clone();
                    AsyncBridge::spawn_background(async move {
                        tokio::time::sleep(Duration::from_secs(5)).await;
                        let _ = window_weak_for_clear.upgrade_in_event_loop(|w| {
                            if !w.get_scan_in_progress() {
                                w.set_scan_status("".into());
                            }
                        });
                    });
                }
            },
        );
    });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python OrchestratorCore | Rust OrchestratorCore | v8.2.0-part2 | All business logic in Rust |
| Qt/PySide6 GUI | Slint GUI | v9.0.0 | Rust-native UI |
| asyncio/AsyncBridge Python | tokio/AsyncBridge Rust | Phase 19 | No Python dependency |

**Deprecated/outdated:**
- simulate_scan(): Phase 20 placeholder, replaced with real scan in Phase 21
- Separate Scan and Cancel buttons: Replaced with morphing button per CONTEXT.md

## Open Questions

Things that couldn't be fully resolved:

1. **OrchestratorCore initialization timing**
   - What we know: OrchestratorCore needs AnalysisConfig with game settings
   - What's unclear: When to load YamlData (startup vs scan start)
   - Recommendation: Load at startup for faster scan initiation; defer to Phase 24 (Settings) for game configuration

2. **Auto-clear delay timing**
   - What we know: Status should auto-clear after scan
   - What's unclear: Exact delay (3s? 5s? 10s?)
   - Recommendation: 5 seconds is reasonable; can be tuned later (Claude's discretion per CONTEXT.md)

3. **Results storage between scan and Results tab**
   - What we know: Scan produces Vec<AnalysisResult> that Results tab needs
   - What's unclear: Where to store (AppState? Dedicated struct?)
   - Recommendation: Store in AppState; Results tab is Phase 22

## Sources

### Primary (HIGH confidence)
- Existing codebase: `rust/business-logic/classic-scanlog-core/src/orchestrator.rs`
- Existing codebase: `rust/business-logic/classic-file-io-core/src/log_collection.rs`
- Existing codebase: `rust/ui-applications/classic-gui/src/worker.rs`
- Existing codebase: `rust/foundation/classic-shared-core/src/async_bridge.rs`
- CONTEXT.md: Phase 21 implementation decisions

### Secondary (MEDIUM confidence)
- Slint ProgressIndicator documentation (indeterminate property)
- tokio-util CancellationToken documentation

### Tertiary (LOW confidence)
- None - all patterns verified in existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components already exist in workspace
- Architecture: HIGH - patterns verified in existing code (worker.rs, main.rs)
- Pitfalls: HIGH - derived from existing implementation experience

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (patterns are stable, all based on existing codebase)
