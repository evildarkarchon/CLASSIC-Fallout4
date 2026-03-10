# `classic-gui` Scan Result Ordering And `input_index` Correlation

Contributor-facing notes for the current Qt batch scan ordering path through:

- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanworker_execution.h`](../../classic-gui/src/workers/scanworker_execution.h)
- [`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp)

This page documents the current source-backed behavior only. It does not claim that batch results are input ordered, and it does not invent a stronger GUI ordering guarantee than the code implements today.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Current Ordering Boundary

The active GUI-to-bridge execution boundary is [`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp).

For multi-log scans, [`ScanWorker::doScan(...)`](../../classic-gui/src/workers/scanworker.cpp) calls `scanworker_execution::executeBatchScan(...)`, and that helper:

- builds the Rust scan config
- creates the orchestrator
- adapts bridge progress through `QtBatchProgressCallback`
- calls `classic::scanner::orchestrator_process_logs_batch_with_progress(...)`
- returns a `QVector<BatchScanResult>` to `ScanWorker`

`ScanWorker` does not call the bridge batch API directly anymore.

---

## Returned Result Ordering

`executeBatchScan(...)` preserves the bridge return shape when it copies results into `QVector<BatchScanResult>`:

- returned batch results are consumed in bridge completion order
- each result carries `inputIndex` as the stable correlation key back to the original `QStringList`
- the GUI does not re-sort the returned batch vector into input order before side effects or signals

That means the worker preserves original row identity per result, but batch completion notifications still follow returned completion order.

---

## How `inputIndex` Is Used Now

[`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) validates `result.inputIndex` against the original `logPaths` list with `try_get_fallback_path(...)`.

Current source-backed behavior:

1. use `result.inputIndex` to look up the original `QStringList` entry
2. if the index is invalid, emit an error and skip that result
3. otherwise use that original entry as the fallback path when `result.logPath` is empty
4. emit `logScanned(index, scanSuccess, resolvedPath)` with the recovered original index

There is no `qMin(..., total - 1)` clamp in the current worker path.

Important limit:

- this is correlation, not reordering

---

## Progress Events Versus Result Notifications

The current GUI has two separate ordering-sensitive streams.

`executeBatchScan(...)` adapts bridge progress events immediately through `QtBatchProgressCallback`, which uses [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp) to compute monotonic visible percent and forwards:

- `percent`
- `status`
- `completed`
- `total`

Later, after the bridge batch call returns, `ScanWorker` iterates the returned `QVector<BatchScanResult>` and performs:

- AUTOSCAN report writes
- optional unsolved-artifact moves
- success and error counting
- `logScanned(...)` emission

So progress answers "what is happening now", while returned results answer "what finished, and which original input row did it belong to?"

---

## Results Tab Interaction

[`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp) is not part of the `inputIndex` correlation path.

It refreshes report files after scan completion and applies its own file-system-based ordering. The Results tab therefore does not document either original input order or bridge completion order as a contributor-facing contract.

---

## Contributor Rule Of Thumb

- If a batch completion updates the wrong row, check `result.inputIndex` handling in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp).
- If visible progress regresses or looks odd, check [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp).
- If you need a stronger ordering guarantee than correlation-by-`inputIndex`, make it real in code and tests first, then document it.
