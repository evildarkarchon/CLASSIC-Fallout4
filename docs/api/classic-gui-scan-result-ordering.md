# `classic-gui` Scan Result Ordering And `input_index` Correlation

Contributor-facing documentation for how the active Qt frontend handles batch scan result ordering through:

- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanworker.h`](../../classic-gui/src/workers/scanworker.h)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp)
- [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp)
- [`classic-gui/src/core/signalhub.h`](../../classic-gui/src/core/signalhub.h)

This page documents the current GUI behavior visible in source today for the active Rust/C++/Qt path. It does not invent a stronger future ordering contract, and it does not claim that the Qt layer receives input-ordered batch results from the bridge.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- where completion-order batch results enter the Qt scan flow
- how `result.input_index` maps returned batch results back to the original `QStringList`
- how progress events and returned results serve different purposes in the GUI
- what `ResultsController` assumes about reports and what it does not assume about scan result order
- which current tests cover this area and which gaps still exist

For the bridge-side batch callback contract, see [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md). For the broader Qt progress-consumer flow, see [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md).

---

## Current Ordering Boundary

The active ordering boundary for Qt contributors is the Rust-owned Crash Log Scan Run bridge call.

`ScanWorker::doScan(...)` calls `classic::scanner::scan_run_execute(...)` for the selected Crash Logs in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp).

That matters because the documented bridge behavior today is:

- callback events can interleave across logs
- returned `ScanRunLogResult` items are in completion order, not original input order
- `input_index` is the stable correlation key back to the original request list

Qt does not re-sort the returned batch vector into input order before processing it. Instead, it consumes the completion-order vector and uses `result.input_index` whenever it needs to recover the original log row.

---

## Where Completion-Order Results Enter The GUI Path

Completion-order results enter the active GUI path here in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp):

```cpp
classic::scanner::ScanRunRequestDto request{};
request.targeted_mode = targetedMode;
request.log_paths = std::move(rustPaths);
auto results = classic::scanner::scan_run_execute(request, progress_callback,
                                                  *m_cancellationToken);

for (const auto& result : results) {
    const int index = static_cast<int>(qMin(result.input_index, static_cast<uint32_t>(total - 1)));
    const QString fallbackPath = logPaths[index];
    ...
    emit logScanned(index, result.success, resolvedPath);
}
```

Current source-backed behavior:

- the loop runs in returned vector order, which is completion order
- Autoscan Report writing and optional Unsolved Logs movement have already happened in Rust before each returned result
- `logScanned(index, success, path)` is emitted in completion order too
- the emitted `index` is derived from `result.input_index`, not from the loop position

So the GUI preserves original-row identity per result, but it does not preserve original-row notification order for batch completion.

---

## How `result.input_index` Maps Back To The Original `QStringList`

The original request order for the batch is the `QStringList logPaths` passed into `ScanWorker::doScan(...)`.

When batch results come back, `ScanWorker` uses `result.input_index` to recover that original list position:

1. clamp `result.input_index` with `qMin(..., total - 1)`
2. use the resulting `index` to read `logPaths[index]`
3. treat that original `QStringList` entry as the fallback path when `result.log_path` is empty
4. emit `logScanned(index, scanSuccess, resolvedPath)` with that recovered original index

Practical effect in current code:

- batch result arrival order may differ from input order
- per-result row identity still points back to the original `QStringList`
- later UI consumers that care about row identity should use the emitted `index`, not assume the next completion belongs to the next input row

Current boundary worth keeping clear:

- this is correlation, not reordering
- the worker does not rebuild an input-ordered `QVector` or `QStringList` of results before emitting notifications

---

## Progress Events Versus Result Notifications

The active GUI has two different ordering-sensitive streams.

## Progress events

Bridge progress enters Qt through the local `BatchProgressCallback` adapter in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp).

Current responsibilities:

- consume each `BatchProgressEvent` as it arrives
- pass `event.input_index` into `BatchProgressModel::update(...)`
- emit live `progress(...)` and `progressDetailed(...)` updates

Current ordering behavior:

- event arrival order follows callback delivery, not original input order
- `BatchProgressModel` uses `event.input_index` only as a per-log key for monotonic aggregate progress
- live status text uses `event.log_path`, so the visible status line follows callback arrival order too

## Result notifications

Returned scan-run results are handled later, after the bridge call returns its full `Vec<ScanRunLogResult>`.

Current responsibilities:

- update success and error counters
- emit `logScanned(...)`
- emit final `finished(...)` and explicit `100%` progress updates

Current ordering behavior:

- this path uses batch result completion order
- original-row identity is recovered with `result.input_index`
- `MainWindow::onCrashLogScanned(...)` therefore observes completion-order notifications tagged with original indices

Short version:

- progress events answer "what is happening right now?"
- returned results answer "what finished, and which original input row did it belong to?"

---

## What `ResultsController` Does And Does Not Assume

`ResultsController` is not part of the per-result correlation path.

Current behavior in [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp):

- it listens only to `SignalHub::scanStarted` and `SignalHub::scanCompleted`
- it pauses directory watching during scans and refreshes the report list after completion
- it discovers `*-AUTOSCAN.md` files from configured report directories
- it globally sorts discovered report paths newest first by file modification time

What it does not assume:

- it does not consume `input_index`
- it does not consume `ScanWorker::logScanned(...)`
- it does not assume reports arrive in original log input order
- it does not assume reports arrive in bridge completion order either

Its ordering responsibility is narrower:

- per-directory report discovery comes from `classic::files::discover_report_files(...)`
- the controller then applies its own global newest-first sort across directories

So `ResultsController` is a report-list refresh layer, not a scan-result ordering layer.

---

## Session-Scoped NEW Badge

The Results list marks reports with a visible **NEW** indicator when their `*-AUTOSCAN.md` path was not present in the session baseline for its report directory.

Current behavior in [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp) and [`classic-gui/src/widgets/reportlistwidget.cpp`](../../classic-gui/src/widgets/reportlistwidget.cpp):

- before computing NEW paths, the controller seeds an in-memory baseline set (`m_baselineReports`) for each configured report directory that has not been baselined yet
- when a report directory is added later in the session, any reports already present in that directory are seeded before `newPaths` is computed
- targeted scans publish their resolved report directories before the worker starts, allowing the Results controller to seed those directories before scan output is written
- on every later refresh, `newPaths = current paths − baseline` (case-insensitive absolute-path comparison)
- `ReportListWidget::setReports(paths, newPaths)` renders matching rows in bold with accent foreground, appends a ✨ marker to the label, and adds `(new this session)` to the tooltip
- the badge is session-scoped only; it resets when the app restarts and is not cleared when a report is selected or viewed

Why a snapshot instead of file modification time:

- scan report generation overwrites existing `{stem}-AUTOSCAN.md` files via `fs::write`, so mtime cannot distinguish a genuinely new report from a re-generated one
- a path present when its report directory baseline is seeded stays non-NEW even if overwritten during the session; a path absent from that directory baseline and created by a scan is NEW for the rest of the session

Tests:

- [`classic-gui/tests/test_resultscontroller.cpp`](../../classic-gui/tests/test_resultscontroller.cpp) — baseline, post-baseline, overwrite, and later-directory seeding cases
- [`classic-gui/tests/test_reportlistwidget.cpp`](../../classic-gui/tests/test_reportlistwidget.cpp) — badge rendering and the existing no-coloring path when no new-set is supplied

---

## Current End-To-End Qt Behavior

For multi-log crash scans today:

1. `ScanController` gathers a `QStringList` of crash-log paths and starts `ScanWorker`
2. `ScanWorker` submits that list to `scan_run_execute(...)`
3. live progress events reach Qt in callback arrival order and are aggregated by `BatchProgressModel` using `event.input_index`
4. returned scan-run results come back in completion order after Rust-owned Autoscan Report writing and Unsolved Logs decisions
5. `ScanWorker` uses `result.input_index` to recover the original `QStringList` row for each completed result
6. `MainWindow` receives live progress counts from `progressDetailed(...)` and later completion notifications from `logScanned(...)`
7. `ResultsController` refreshes reports only after the scan-completed signal, then sorts report files by modification time

Nothing in the active Qt path turns the batch result vector into an input-ordered sequence before side effects or signals occur.

---

## What Current Tests Lock In

## Direct coverage

[`classic-gui/tests/test_scan_progress_model.cpp`](../../classic-gui/tests/test_scan_progress_model.cpp) locks in the Qt-side use of `input_index` for progress aggregation indirectly through `BatchProgressModel` state updates.

It currently verifies that:

- visible progress stays monotonic across a single-log lifecycle
- in-flight phase events raise aggregate progress before terminal completion
- later phases contribute more than earlier phases
- late lower-rank events are ignored after a terminal state

[`classic-gui/tests/test_scan_settings_wiring.cpp`](../../classic-gui/tests/test_scan_settings_wiring.cpp) locks in the source-level wiring around the batch progress path.

It currently verifies that:

- `ScanWorker` uses `BatchProgressCallback`
- `ScanWorker` consumes `BatchProgressEvent`
- `ScanWorker` calls `scan_run_execute(...)`
- `ScanWorker` forwards `event.completed` and `event.total` through `progressDetailed(...)`
- single-log and multi-log scans both cross the same Rust Crash Log Scan Run seam

[`classic-gui/tests/test_mainwindow_geometry.cpp`](../../classic-gui/tests/test_mainwindow_geometry.cpp) locks in the status-bar side of the live progress contract.

It currently verifies that:

- `MainWindow` stores separate crash-scan total and completed counters
- `onCrashScanProgress(...)` updates those counters from structured `completed` and `total` arguments
- status text reads tracked scan counts instead of inferring them from percent alone

## Related but different coverage

[`classic-gui/tests/test_resultscontroller.cpp`](../../classic-gui/tests/test_resultscontroller.cpp) covers report discovery, watcher refresh, auto-switching, and open-folder behavior.

It does not lock in any batch-scan `input_index` correlation rule.

---

## Where There Are No Dedicated Tests Yet

There is currently no dedicated Qt test that proves all of these together at runtime:

- returned batch results arrive in completion order and are processed in that order by `ScanWorker`
- `result.input_index` is used to map each completion back to the original `QStringList`
- `logScanned(index, ...)` preserves original-row identity even when completions are out of order
- report file side effects occur in completion order while the Results tab later shows newest-first filesystem order
  - report file side effects are now Rust-owned before results return; the Qt ordering concern is notification order, not file-write order

There is also no dedicated `ResultsController` test asserting report-list ordering as a contributor-facing scan-order contract. The controller sorts by file modification time, but the existing tests focus on discovery and refresh behavior rather than a stable semantic ordering promise.

So today the strongest source-backed statement is:

- the code uses `input_index` for correlation
- the tests cover progress-model monotonicity and wiring
- there is not yet a focused integration test for out-of-order batch completion correlation in the Qt layer

---

## Source-Backed Limits And Caveats

- The bridge callback and returned result vector come from `scan_run_execute(...)` for both single-log and multi-log scans.
- `ScanWorker` clamps `result.input_index` with `qMin(result.input_index, total - 1)` before indexing `logPaths`; this is a defensive bound, not a statement that out-of-range indices are expected.
- `ScanWorker` uses `result.log_path` when present and falls back to the original `QStringList` entry when it is empty.
- `ScanWorker` does not write Autoscan Reports or move Unsolved Logs; it observes the `ScanRunLogResult` produced after Rust-owned side effects.
- `BatchProgressModel` uses `event.input_index` only to track per-log progress state; it does not expose or preserve a user-visible input order.
- `MainWindow` progress text reflects callback arrival order for status messages and structured completed counts for scan totals; those are separate concepts.
- `MainWindow::onCrashLogScanned(...)` increments the completed counter again as per-result notifications arrive, so contributors should not treat that counter as a one-source-of-truth mirror of bridge terminal events.
- `ResultsController` refreshes reports only after `SignalHub::scanCompleted()` and then sorts by file modification time, so the Results tab does not represent original input order or bridge completion order as a documented contract.
- `SignalHub` carries only coarse scan lifecycle signals for this flow: start, progress text, completion, and error. It does not carry `input_index` or per-result ordering metadata.

These are current behavior notes, not a future ordering design.

---

## Contributor Rule Of Thumb

- If you are debugging wrong-row updates in batch crash scans, start in [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) and verify `result.input_index` handling first.
- If you are debugging percent regressions or odd live progress, check [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp), not `ResultsController`.
- If you are debugging why the Results tab order differs from scan completion order, check [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp) and remember it sorts report files by modified time.
- If you need a stronger Qt-side ordering guarantee, make it real in `ScanWorker` and tests first, then document it.
