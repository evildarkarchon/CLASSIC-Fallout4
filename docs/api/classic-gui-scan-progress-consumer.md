# `classic-gui` Scan Progress Consumer Flow

Contributor-facing notes for how the current Qt frontend consumes batch scan progress through:

- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanworker_execution.h`](../../classic-gui/src/workers/scanworker_execution.h)
- [`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp)

This page documents the current GUI consumer behavior visible in source today for the active Rust/C++/Qt path. It does not describe deprecated paths, and it does not invent a future UI contract.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Where The Callback Enters Qt

The bridge callback now enters Qt in `QtBatchProgressCallback` inside [`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp).

For multi-log scans:

- [`ScanWorker::doScan(...)`](../../classic-gui/src/workers/scanworker.cpp) calls `scanworker_execution::executeBatchScan(...)`
- `executeBatchScan(...)` constructs `QtBatchProgressCallback`
- `QtBatchProgressCallback::on_batch_progress(...)` feeds each `BatchProgressEvent` into `BatchProgressModel::update(...)`
- the adapter forwards `(percent, status, completed, total)` through `BatchProgressCallback`
- `ScanWorker` turns that higher-level callback payload into `progress(...)` and `progressDetailed(...)` Qt signals

`ScanWorker` no longer implements the bridge callback or calls `orchestrator_process_logs_batch_with_progress(...)` directly.

---

## Current Responsibility Split

[`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp):

- builds the Rust config and orchestrator
- owns the bridge callback adapter
- converts bridge strings to `QString`
- uses `BatchProgressModel` to keep visible percent monotonic
- returns `SingleScanResult` or `BatchScanResult` DTOs back to the worker

[`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp):

- chooses batch or single-log flow
- emits Qt progress signals from the execution-layer callback payload
- correlates returned batch results back to original rows with `inputIndex`
- writes reports, moves unsolved artifacts, and emits `logScanned(...)`

[`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp) and [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp) still consume only the Qt signal layer, not raw bridge events.

---

## Fields The GUI Uses

The execution-layer callback adapter currently uses these bridge fields directly:

- `event.input_index` as the per-log key for `BatchProgressModel`
- `event.log_path` as the status string source
- `event.completed` and `event.total` as structured progress counts
- `event.event_kind` and `event.phase` for progress ranking and weighting

It does not expose raw bridge enums as first-class UI state.

---

## Ordering Notes

- callback arrival order can still interleave across logs
- `BatchProgressModel` uses `input_index` for per-log state, not for visible input ordering
- returned `BatchScanResult` handling happens later, after the batch call completes
- the result-ordering and `inputIndex` correlation rules for that later phase are documented in [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md)

---

## Source-Backed Limits And Caveats

- The bridge callback path is only used for multi-log scans; single-log scans still use `executeSingleScan(...)` and worker-local coarse progress updates.
- `ScanController` and `MainWindow` do not consume raw `BatchProgressEvent`; they only see the transformed Qt signal payload.
- Visible status text follows callback arrival order because it uses `event.log_path` from the active callback event.
- Visible percent comes from `BatchProgressModel`, while completed-log counters are forwarded separately from bridge `completed` and later worker result notifications.
- `ScanWorker` still emits a final explicit `100%` / `Complete` update after iterating returned batch results.

These are current consumer behavior notes, not a future UI design.
