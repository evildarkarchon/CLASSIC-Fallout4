# `classic-gui` Discovery-Ordered Scan Results

Contributor-facing documentation for how the active Qt frontend consumes final Crash Log Scan Run ordering through:

- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanrunpresentation.cpp`](../../classic-gui/src/workers/scanrunpresentation.cpp)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/controllers/resultscontroller.cpp`](../../classic-gui/src/controllers/resultscontroller.cpp)
- [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp)

The active GUI consumes terminal outcomes that Rust has already sorted into discovery order. It does not correlate results back to a GUI-owned input list.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page to understand:

- the difference between serialized event order and terminal result order
- what `discovery_index` identifies after Standard or Targeted discovery
- how `ScanWorker` emits per-log terminal notifications
- why Results-tab ordering remains independent from scan-result ordering
- what the current tests guarantee

For live progress consumption, see [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md). For the CXX final observer and retained terminal contract, see [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md).

---

## The Two Ordering Domains

The final Crash Log Scan Run exposes two intentionally different orders.

### Serialized execution-event order

`ScanRunObserver` receives `DiscoveryCompleted`, `EffectiveConcurrencySelected`, and per-log events from one serial observer pump. Events from concurrently admitted logs may interleave. This order answers "what is happening now?"

Every log-scoped event carries `discovery_index` and `crash_log`, so `BatchProgressModel` can maintain independent state for each discovered log without assuming that events arrive grouped by log.

### Discovery-ordered terminal results

`ScanRunContractExecutionResult.result.logs` is sorted by discovery index before crossing CXX. This order answers "what was the final outcome for each accepted log?"

The Rust contract preserves terminal results in discovery order independently of event delivery or work completion order. Qt does not sort, clamp, or remap the returned vector. `presentScanRunExecution(...)` iterates it as received and retains each `log.discovery_index` in `ScanRunLogPresentation`.

---

## What `discovery_index` Means

`discovery_index` is the zero-based position in Rust's accepted discovery sequence.

- Standard runs use the accepted order produced by Rust-owned `LogCollector` discovery.
- Targeted runs canonicalize, expand directories, de-duplicate accepted logs, and retain rejected `{path, reason}` entries in discovery data.
- Rejected Targeted inputs do not receive per-log outcomes.

Consequently, `discovery_index` is not a promise about the user's original Targeted list position. It identifies `discovery.accepted_logs`, which is the same committed discovery payload delivered by `DiscoveryCompleted` and retained on the terminal result.

No caller-supplied input index or completion-order reconstruction participates in the shipped contract.

---

## Where Terminal Results Enter Qt

`ScanWorker::doScan(...)` moves one `ScanRunContractExecutionResult` from the
opaque execution operation:

```cpp
auto operation = scan_run_contract_execute(*request, *m_cancellation, &observer);
auto execution = scan_run_contract_execution_take_result(*operation);
```

`presentScanRunExecution(...)` first preserves the result-level counts and run status, then projects logs in their existing order:

```cpp
for (const auto& log : result.logs) {
    presentation.logs.append(presentLog(log));
}
```

The projection retains:

- `discoveryIndex`
- `Succeeded`, `Failed`, or `CancelledBeforeStart` disposition
- Crash Log and optional Autoscan Report paths
- every structured analysis, report-write, and Unsolved Logs finalization failure
- optional message and movement state

No `QStringList` lookup, fallback-path recovery, `qMin` clamp, or completion-order correlation remains in the active worker.

---

## Per-Log Qt Notifications

After terminal projection, `ScanWorker` iterates `terminal.logs` in discovery order.

- `CancelledBeforeStart` entries are skipped because they represent accepted work that Rust never admitted.
- failures are logged with all projected structured failure messages
- admitted succeeded or failed entries emit `logScanned(discoveryIndex, succeeded, crashLog)`

Therefore `ScanController::scanLogScanned(...)` notifications are discovery ordered for admitted outcomes, not completion ordered. There can be gaps in emitted indices when cancellation leaves accepted logs unstarted.

`MainWindow::onCrashLogScanned(...)` currently ignores index, success, and path and uses each notification only to advance its completed display count. It does not update a row by index today. The signal still carries discovery identity for consumers that need it.

The terminal aggregate counts remain authoritative:

- `total` counts all accepted logs
- `succeeded` and `failed` count admitted terminal work
- `cancelled` counts accepted logs not started

On a completed run, the worker emits `finished(total, succeeded, failed)`. On cancellation, it emits the typed cancellation presentation instead of a completion summary.

`NoCrashLogsFound` is also a typed expected terminal with discovery data and no per-log outcomes. The worker emits `noLogsFound(...)`, and the controller/MainWindow restore idle state through the dedicated no-logs route rather than treating the empty result as an infrastructure error.

---

## Progress Order Is Still Independent

Live event order is not changed to match terminal order.

- the visible status line follows serialized observer delivery and may move between logs
- `BatchProgressModel` keys state by `event.discovery_index`
- `event.completed`/`event.total` are Rust-owned snapshots from execution order
- the terminal `logScanned(...)` loop happens only after the final contract returns

Do not infer terminal vector order from the last progress event, and do not delay or reorder observer events to mimic the discovery-ordered result vector.

---

## Report-Directory Ordering Boundary

Qt learns report directories at two points:

1. `DiscoveryCompleted` derives unique directories from Rust-accepted Crash Logs and publishes them through a blocking controller handoff before scan output is written.
2. Terminal presentation derives unique directories from actual Autoscan Report paths and publishes them when non-empty.

Both helpers preserve first-seen order and de-duplicate paths case-insensitively. These lists configure where the Results controller watches; they are not the visible report sort order.

`ResultsController` remains outside per-log result correlation. It:

- listens to coarse `SignalHub` start/completion/no-logs/cancellation/error lifecycle
- pauses watching while a scan runs and resumes afterward
- discovers `*-AUTOSCAN.md` files from configured directories
- globally sorts report paths newest-first by filesystem modification time

The Results tab therefore represents report recency, not discovery order, event order, or execution completion order.

---

## Session-Scoped NEW Badge

The report list's **NEW** marker also depends on directory baselines, not scan-result order.

- when a report directory is first configured, `ResultsController` seeds an in-memory baseline from paths already present
- the blocking `DiscoveryCompleted` handoff lets newly discovered Targeted directories be configured and baselined before Rust writes reports
- later refreshes compute new paths as current paths minus that directory's baseline using case-insensitive absolute-path comparison
- an existing report overwritten by a scan is not NEW; a previously absent path remains NEW for the rest of the session
- the baseline is session-only and resets on application restart

On completion, `SignalHub::scanCompleted` resumes watching and refreshes the report list. No-logs, cancellation, and error terminals also resume watching and refresh through the cleanup path, but they do not pretend the run completed successfully.

---

## Current End-To-End Behavior

For either Standard or Targeted GUI scans:

1. `ScanController` forwards request facts without discovering logs.
2. Rust performs discovery and commits an accepted sequence.
3. `DiscoveryCompleted` initializes Qt totals, warnings, and report directories from that committed sequence.
4. Per-log observer events arrive serially in execution order and correlate by `discovery_index`.
5. Rust completes admitted report persistence and applicable movement before `LogFinished`.
6. Rust sorts terminal per-log outcomes into discovery order.
7. `presentScanRunExecution(...)` preserves that order and typed data.
8. `ScanWorker` emits admitted `logScanned(...)` notifications in discovery order and skips `CancelledBeforeStart` outcomes.
9. `ResultsController` later refreshes filesystem reports and applies its own newest-first order.

Qt owns none of the discovery, completion-order reconciliation, durable finalization, or terminal sorting in this sequence.

---

## What Current Tests Lock In

[`test_scanrunpresentation.cpp`](../../classic-gui/tests/test_scanrunpresentation.cpp) directly verifies that:

- terminal logs retain discovery order and discovery indices
- succeeded, failed, and cancelled-before-start dispositions remain distinct
- analysis, report-write, and Unsolved Logs finalization failures all survive presentation
- aggregate counts, report paths, messages, and movement state are preserved
- Targeted rejection paths stay paired with their Rust-provided reasons

[`test_scan_progress_model.cpp`](../../classic-gui/tests/test_scan_progress_model.cpp) verifies the separate event-order domain: state is keyed by discovery index, interleaved logs advance independently, and late lower-rank events cannot regress visible progress.

[`test_scanrequestbuilder.cpp`](../../classic-gui/tests/test_scanrequestbuilder.cpp) verifies that Standard and Targeted discovery begin through distinct tagged requests and that Targeted rejection remains structured discovery data.

[`test_resultscontroller.cpp`](../../classic-gui/tests/test_resultscontroller.cpp) and [`test_reportlistwidget.cpp`](../../classic-gui/tests/test_reportlistwidget.cpp) cover directory baselines, NEW-path behavior, refresh, and badge rendering. Those tests do not redefine terminal scan-result order.

---

## Source-Backed Limits And Caveats

- Discovery order is a Rust contract for accepted logs, not necessarily filesystem lexical order or original Targeted-input order.
- Event delivery may interleave even though terminal results are discovery ordered.
- `logScanned(...)` excludes `CancelledBeforeStart`, so emitted notification indices need not be contiguous after cancellation.
- The worker derives terminal report directories only from non-empty Autoscan Report paths; a failed log without a report contributes no directory at that stage.
- Results-tab newest-first sorting depends on filesystem modification times and is intentionally separate from scan ordering.
- `SignalHub` carries no discovery index or per-result DTO. Detailed identity stays on `ScanController::scanLogScanned(...)`.

---

## Contributor Rule Of Thumb

- Use `discovery_index` to correlate final-contract events and accepted discovery data.
- Trust the terminal `logs` vector's discovery order; do not add GUI sorting or original-input fallback logic.
- Treat event order, terminal order, and Results-tab order as three separate contracts.
- Do not introduce caller-input correlation or completion-order result handling into the Qt worker.
