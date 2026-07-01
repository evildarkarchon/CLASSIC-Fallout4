# `classic-gui` Scan Progress Consumer Flow

Contributor-facing documentation for how the active Qt frontend consumes the Rust/C++ batch scan progress callback contract through:

- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanworker.h`](../../classic-gui/src/workers/scanworker.h)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/workers/scanprogressmodel.h`](../../classic-gui/src/workers/scanprogressmodel.h)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/controllers/scancontroller.h`](../../classic-gui/src/controllers/scancontroller.h)
- [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp)

This page documents the current GUI consumer behavior visible in source today for the active Rust/C++/Qt path. It does not describe deprecated `classic-pybridge` behavior and it does not invent a future UI contract.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- where `BatchProgressEvent` enters `classic-gui`
- how `BatchProgressCallback`, `BatchProgressModel`, `ScanController`, and `MainWindow` divide responsibility
- which callback fields the GUI uses directly and which ones it only uses indirectly
- how visible percent progress stays monotonic even when callback ordering interleaves across logs
- what the current Qt-side tests actually lock in

For the bridge-side contract itself, see [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md). For the wider C++ scan entry points, see [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md). For the Qt-side result-ordering and `input_index` correlation rules that happen after progress delivery, see [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md).

---

## Where The Callback Enters Qt

The callback enters the GUI in the local adapter class `BatchProgressCallback` inside [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp).

`ScanWorker::doScan(...)` uses the callback-enabled `classic::scanner::scan_run_execute(...)` bridge entry point for both single-log and multi-log Crash Log Scan Runs. The bridge callback contract is therefore the current GUI progress path for all selected Crash Logs.

The callback adapter is intentionally small:

- it owns a mutable `BatchProgressModel`
- it passes each `BatchProgressEvent` into `BatchProgressModel::update(...)`
- it converts `event.log_path` into a `QString` status string
- it forwards the returned visible percent plus `event.completed` and `event.total` through `ScanWorker` signals

Current signal fan-out from the callback adapter:

```cpp
Q_EMIT m_worker.progress(percent, status);
Q_EMIT m_worker.progressDetailed(percent, status, completed, total);
```

---

## Current End-To-End Flow

## 1. `ScanWorker` owns Rust orchestration and callback adaptation

[`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) is the only active Qt file that implements `classic::scanner::ScanBatchProgressCallback`.

Current worker responsibilities:

- pass selected Crash Logs and scan settings to `scan_run_execute(...)`
- adapt bridge callback events into Qt signals
- map completion-order `ScanRunLogResult` values back to original log rows with `result.input_index`
- emit Qt signals from Rust-owned Crash Log Scan Run outcomes

Important boundary:

- callback events drive live progress updates
- `logScanned(...)` and `finished(...)` happen later, while iterating returned scan-run results; Autoscan Report writing and Unsolved Logs movement have already happened in Rust

## 2. `BatchProgressModel` turns event stream state into visible percent

[`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp) does not expose raw bridge events to the UI. It keeps per-log state in a `QHash<quint32, LogProgressState>` keyed by `event.input_index` and returns one aggregate percentage for the whole batch.

Current rank ladder:

- `Queued` -> rank `0`
- `Started` -> rank `1`
- `Phase + Setup` -> rank `2`
- `Phase + Parse` -> rank `3`
- `Phase + Analyze` -> rank `4`
- `Phase + Finalize` -> rank `5`
- `Completed` or `Failed` -> rank `6`

Current per-log contribution weights:

- `Queued` -> `0.00`
- `Started` -> `0.08`
- `Setup` -> `0.15`
- `Parse` -> `0.40`
- `Analyze` -> `0.82`
- `Finalize` -> `0.95`
- terminal `Completed` or `Failed` -> `1.00`

The model sums the latest accepted contribution for each known log, divides by `m_totalLogs`, converts to `0..100`, and then clamps the visible percent with `std::max(m_percent, computedPercent)`.

## 3. `ScanController` relays worker signals, not raw callback events

[`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp) never sees `BatchProgressEvent` directly.

Current controller responsibilities in this flow:

- collect candidate crash logs before creating the worker thread
- emit `scanStarted()` and `scanDiscovered(int)`
- connect `ScanWorker::progressDetailed` to `ScanController::scanProgress`
- connect `ScanWorker::logScanned` to `ScanController::scanLogScanned`
- connect `ScanWorker::finished` and `ScanWorker::error` to controller completion/error handling

`ScanController::scanProgress` therefore carries the already-transformed Qt payload:

- `float percent`
- `QString status`
- `int completed`
- `int total`

## 4. `MainWindow` turns structured progress into status-bar UI state

[`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp) connects `ScanController::scanProgress` to `MainWindow::onCrashScanProgress(...)`.

Current main-window responsibilities:

- start crash-scan UI state in `onScanCrashLogs()`
- keep `m_crashScanTimer`, `m_crashScanTotalLogs`, and `m_crashScanLogsCompleted`
- update those counters from structured progress in `onCrashScanProgress(...)`
- render percent, scanned-log counts, elapsed time, and status text in `onScanProgress(...)`
- update completion counters again from `scanDiscovered`, `scanLogScanned`, and `scanFinished`
- reset button/progress-bar state on completion or error

The visible status bar is therefore driven by two streams:

- live callback-derived `scanProgress(percent, status, completed, total)` updates
- later per-result `scanLogScanned(...)` notifications as the worker iterates returned batch results

---

## What The GUI Propagates And Transforms

## Fields used directly from `BatchProgressEvent`

The callback adapter currently uses these bridge fields directly:

- `event.input_index` - used only inside `BatchProgressModel` as the stable per-log key
- `event.log_path` - converted to `QString` and shown as the status text
- `event.completed` - forwarded as the structured completed-log count
- `event.total` - forwarded as the structured total-log count
- `event.event_kind` - ranked by `BatchProgressModel`
- `event.phase` - ranked and weighted by `BatchProgressModel`

## Fields not surfaced as first-class UI state

The adapter does not currently expose these as distinct UI concepts:

- `event.success` - ignored for live progress; success and failure only affect terminal result handling later
- raw `event_kind` names - the UI does not display `Queued`, `Started`, `Phase`, `Completed`, or `Failed` directly
- raw phase names - the UI does not display `Setup`, `Parse`, `Analyze`, or `Finalize` directly

## Transformations applied on the Qt side

Current transformations from bridge event to UI state:

1. `event.log_path` becomes a `QString status`
2. `event` becomes a monotonic aggregate `float percent` through `BatchProgressModel::update(...)`
3. `event.completed` and `event.total` become `int completed` and `int total` in `progressDetailed(...)`
4. `MainWindow::onCrashScanProgress(...)` clamps `completed` to `total` when `total > 0`
5. `MainWindow::onScanProgress(...)` formats status text such as `Scanning: 42% | 1/3 logs scanned | elapsed 2.4s | ...`

---

## How Monotonic Visible Progress Is Enforced

The GUI enforces monotonic visible progress in `BatchProgressModel`, not in `MainWindow`.

There are two layers to that enforcement:

- per log, a new event is accepted only when its rank is greater than or equal to the stored rank for that `input_index`
- across the whole batch, `m_percent` is updated with `std::max(m_percent, computedPercent)` so the returned percent never decreases even if later events would recompute to a lower value

Practical consequences of the current model:

- late regressions such as `Phase + Parse` after `Completed` are ignored for that log
- interleaved updates from different logs can still raise the aggregate percent smoothly
- the visible percent is an intentionally weighted approximation of batch progress, not an exact projection of bridge `completed`
- `Completed` and `Failed` both contribute `1.00`, so visible percent reaches full contribution for either terminal outcome

This matches the bridge contract better than assuming callback order alone is safe to show directly.

---

## What The Current Tests Assert

## `test_scan_progress_model.cpp`

[`classic-gui/tests/test_scan_progress_model.cpp`](../../classic-gui/tests/test_scan_progress_model.cpp) is the direct behavioral test for `BatchProgressModel`.

It currently asserts that:

- a single log lifecycle from `Queued` through `Completed` never decreases visible percent
- in-flight `Phase` updates advance visible batch progress before terminal completion
- later phases contribute more than earlier phases for a log in progress
- a late lower-rank phase after terminal completion is ignored
- a one-log terminal completion produces `100.0f`

## `test_scan_settings_wiring.cpp`

[`classic-gui/tests/test_scan_settings_wiring.cpp`](../../classic-gui/tests/test_scan_settings_wiring.cpp) uses source-text checks rather than runtime signal assertions, but it still captures the intended wiring.

It currently asserts that:

- `ScanWorker` defines `BatchProgressCallback` and consumes `BatchProgressEvent`
- `ScanWorker` calls `scan_run_execute(...)`
- `ScanWorker` forwards `event.completed` and `event.total` into `progressDetailed(percent, status, completed, total)`
- `ScanWorker` delegates both single-log and multi-log runs to Rust
- `ScanController` forwards scan settings into `ScanWorker::doScan(...)`
- `MainWindow` connects `ScanController::scanProgress` to `MainWindow::onCrashScanProgress(...)`
- `MainWindow::onCrashScanProgress(...)` receives structured `completed` and `total` counts

## `test_mainwindow_geometry.cpp`

[`classic-gui/tests/test_mainwindow_geometry.cpp`](../../classic-gui/tests/test_mainwindow_geometry.cpp) includes one progress-related UI contract check.

It currently asserts that:

- `MainWindow` stores crash-scan timer and count fields in `mainwindow.h`
- `onCrashScanProgress(...)` updates `m_crashScanLogsCompleted` from the structured `completed` and `total` arguments
- `onScanProgress(...)` formats status text using tracked scanned-log counts and elapsed time
- crash-scan progress handling does not infer completed-log counts from percent alone

---

## Source-Backed Limits And Caveats

- The bridge callback path is used for both single-log and multi-log scans in `ScanWorker` through `scan_run_execute(...)`.
- `ScanController` and `MainWindow` do not consume raw `BatchProgressEvent`; they only see Qt signals emitted by `ScanWorker`.
- The GUI uses `event.log_path` as the live status string, so visible status order follows callback arrival order rather than original input order.
- The GUI uses `event.input_index` only inside `BatchProgressModel` and later for `BatchScanResult` correlation; `MainWindow` never sees that key directly.
- Visible percent and visible completed-log counts come from different sources: percent is the weighted aggregate from `BatchProgressModel`, while completed counts come from bridge `event.completed` and later `logScanned(...)`/`finished(...)` signals.
- `MainWindow::onCrashLogScanned(...)` increments the completed counter again as batch results are processed. That is harmless because `onCrashScanProgress(...)` and `onScanCompleted(...)` clamp or overwrite the value, but contributors should not treat those counters as a one-source-of-truth mirror of bridge state.
- The Qt side does not currently expose `event.success`, raw phase names, or raw event-kind names to the user interface.
- `BatchProgressModel` treats `Completed` and `Failed` identically for percentage contribution, so percent tracks work completion, not success rate.
- `ScanWorker` emits an explicit final `100%` / `Complete` update after iterating all batch results, even though the callback path may already have reached `100%`.
- `ScanWorker` no longer writes Autoscan Reports or moves Unsolved Logs; those side effects are owned by Rust `CrashLogScanRun` before each `ScanRunLogResult` reaches Qt.

These are current consumer behavior notes, not a future UI design.

---

## Contributor Rule Of Thumb

- If callback sequencing changes in Rust, check whether `BatchProgressModel` ranking and weighting still make sense for the GUI.
- If you change `BatchProgressEvent` fields or semantics, update both [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md) and this page in the same change.
- If the status bar counts look wrong, inspect both `progressDetailed(...)` emission in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) and counter handling in [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp).
- If you need stronger frontend guarantees than weighted monotonic progress, make them real in code and tests first, then document them.
