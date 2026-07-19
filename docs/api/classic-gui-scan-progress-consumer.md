# `classic-gui` Final Scan Run Progress Consumer

Contributor-facing documentation for how the active Qt frontend consumes the final Rust-owned Crash Log Scan Run contract through:

- [`classic-gui/src/workers/scanrequestbuilder.cpp`](../../classic-gui/src/workers/scanrequestbuilder.cpp)
- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/workers/scanrunpresentation.cpp`](../../classic-gui/src/workers/scanrunpresentation.cpp)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/app/mainwindow.cpp`](../../classic-gui/src/app/mainwindow.cpp)

This page documents the active `ScanRunObserver` path, which is the GUI's only Crash Log Scan Run execution contract.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page to understand:

- how Qt constructs only valid tagged Standard or Targeted requests
- where Rust-owned discovery, concurrency, and lifecycle events enter Qt
- how `BatchProgressModel` projects serialized final-contract events into visible progress
- how cancellation and terminal statuses become Qt signals
- which policies remain in Rust and which transformations are presentation-only

For the CXX observer contract, see [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md). For discovery-ordered terminal results, see [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md).

---

## Request Construction Boundary

`ScanController::startScan(...)` does not collect Crash Logs. It captures the immutable, revision-approved `CrashLogScanLaunchSettings`, the runtime FCX XSE-log hint, and the optional Targeted input list, then invokes `ScanWorker::doScan(...)` on a worker thread.

`buildScanRunRequest(...)` projects those values into one opaque Rust-owned `ScanRunRequest`:

- no Targeted inputs constructs Standard intent with a `ScanRunStandardSourceDto`
- one or more Targeted inputs constructs Targeted intent with a `ScanRunTargetedSourceDto`
- Standard requests receive either `LeaveInPlace` or `MoveToConfiguredOrDefault` Unsolved Logs intent
- Targeted constructors have no Unsolved Logs parameter, so persisted Standard movement settings cannot leak into a Targeted run
- FCX requests use the corresponding `_with_fcx` constructor and must carry `ScanRunSetupContextDto`
- a positive configured concurrency becomes an explicit value; a non-positive GUI setting omits it and selects Rust's adaptive policy

The worker then calls exactly one operation:

```cpp
scan_run_contract_execute(*request, *m_cancellation, &observer)
```

Rust owns discovery, Targeted rejection policy, effective-concurrency selection, scheduling, FCX setup evaluation, Autoscan Report persistence, Unsolved Logs finalization, cancellation admission seams, aggregate counts, and terminal ordering. Qt supplies facts and presents the resulting contract; it does not repeat those decisions.

---

## Where Events Enter Qt

The local `GuiScanRunObserver` in [`scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) implements `classic::scanner::ScanRunObserver`.

The observer:

- receives `ScanRunContractEvent` values serially in execution order
- owns a mutable `BatchProgressModel`
- emits worker Qt signals from the synchronous worker-thread call
- is `noexcept`, catches every Qt-side presentation exception, records delivery failure, and explicitly requests safe cancellation

Observer delivery is non-controlling. A presentation failure does not become a Rust scan failure and no exception crosses CXX. After execution returns, `ScanWorker` checks `deliveryFailed()` and emits an adapter-local error instead of presenting a possibly incomplete event stream as a successful run.

The worker owns one monotonic `ScanRunCancellation`. `requestCancel()` calls `scan_run_cancellation_cancel(...)`; the GUI does not poll or decide which queued work may still start.

---

## Event-To-Signal Mapping

### `DiscoveryCompleted`

`BatchProgressModel` sets its total from `event.discovery.accepted_logs.size()`. The worker then emits:

- `discoveryCompleted(total, rejectionWarning, reportDirectories)`
- `progress(0, "Found ...")`
- `progressDetailed(0, "Found ...", 0, total)`

`formatScanRunRejections(...)` preserves every Rust-provided Targeted `{path, reason}` pair. It formats a warning but does not reapply rejection policy. `scanRunReportDirectories(...)` derives case-insensitively de-duplicated directories from the Rust-accepted logs.

`ScanController` receives discovery through a `Qt::BlockingQueuedConnection`, then emits `scanDiscovered`, optional `scanWarning`, and `scanReportDirectoriesResolved`. This lets the UI install report-directory watching and session baselines before the worker continues into report-producing scan work.

### `EffectiveConcurrencySelected`

The model stores `event.effective_concurrency`. The worker emits:

- `effectiveConcurrencySelected(...)`
- `progress(...)`
- `progressDetailed(...)`

The value is informational: Qt reports the exact Rust-selected admission limit and does not select or adjust concurrency itself.

### Per-log events

`LogQueued`, `LogStarted`, `LogPhase`, and `LogFinished` update the progress model and emit both progress signals. Status presentation is event-aware:

- `LogQueued` -> `Queued: <path>`
- `LogStarted` -> `Scanning: <path>`
- `LogPhase` -> `setup`, `parse`, `analysis`, or `finalization` plus the path
- `LogFinished` -> `Finished: <path>`

The correlation key is `event.discovery_index`. `event.completed` and `event.total` remain Rust-owned lifecycle snapshots forwarded through `progressDetailed(...)`.

The observer does not turn `LogFinished.disposition` into success/error UI state. Structured disposition and failure-stage presentation happens from the terminal execution result after the call returns.

---

## Visible Progress Model

`BatchProgressModel` is initialized by `DiscoveryCompleted`, not by a GUI-collected input count. It stores per-log state in a `QHash<quint64, LogProgressState>` keyed by `discovery_index`.

Current rank and contribution ladder:

| Event | Rank | Contribution |
|---|---:|---:|
| `LogQueued` | 0 | 0.00 |
| `LogStarted` | 1 | 0.08 |
| `LogPhase(Setup)` | 2 | 0.15 |
| `LogPhase(Parse)` | 3 | 0.40 |
| `LogPhase(Analyze)` | 4 | 0.82 |
| `LogPhase(Finalize)` | 5 | 0.95 |
| `LogFinished` | 6 | 1.00 |

`DiscoveryCompleted` and `EffectiveConcurrencySelected` initialize run state without adding per-log contribution.

For each log, only an event at the same or a later rank may replace stored state. The model sums contributions, divides by the discovered total, and applies `std::max(m_percent, computedPercent)`. Therefore:

- interleaved serialized events can advance different logs independently
- a late lower-rank event cannot regress a finished log
- failed and successful `LogFinished` events both represent completed work and contribute `1.00`
- visible percent is a weighted presentation estimate, while completed/total are separate Rust lifecycle counts

---

## Controller And Main-Window Flow

`ScanController` never receives a raw bridge event. It relays presentation-ready worker signals:

- `scanDiscovered(total)`
- `scanConcurrencySelected(concurrency)`
- `scanProgress(percent, status, completed, total)`
- `scanLogScanned(discoveryIndex, success, path)`
- `scanFinished(...)`, `scanNoLogsFound(...)`, `scanCancelled(...)`, or `scanError(...)`
- `scanWarning(...)` and `scanReportDirectoriesResolved(...)`

`MainWindow::onCrashScanProgress(...)` updates its displayed count monotonically from structured completed/total values, then formats percent, elapsed time, counts, and event status. `onCrashScanDiscovered(...)` initializes the accepted-log total. The main window does not infer a log count from percentage and does not see raw observer tags.

`SignalHub` receives only coarse lifecycle presentation: start, two-field progress, completion, no-logs, cancellation, and error. Final-contract discovery indices and typed terminal data stay on the worker/controller path.

---

## Terminal Presentation And Cancellation

After `scan_run_contract_execute(...)` returns, `presentScanRunExecution(...)` maps the typed execution envelope into `ScanRunTerminalPresentation` without flattening distinct lifecycle states.

Terminal mapping:

- `Completed` emits an explicit `100% / Complete` progress update and `finished(total, succeeded, failed)`
- `CancelledBeforeDiscovery` emits `cancelled(...)` and has no discovery payload
- `Cancelled` emits `cancelled(...)` with completed and not-started counts
- `NoCrashLogsFound` emits the dedicated `noLogsFound(...)` signal with searched locations when available; the controller relays `scanNoLogsFound(...)`, and MainWindow restores idle state without presenting an error dialog
- `SetupFailed` emits `error(...)` with structured setup details
- a typed infrastructure error emits `error(...)` with its stage, message, and optional path

Cancellation after discovery does not interrupt admitted work. Rust finishes durable report/movement handling for admitted logs, prevents later admissions at safe seams, and returns non-started accepted logs as `CancelledBeforeStart`. The worker skips those entries when emitting `logScanned(...)`.

The presentation layer projects:

- the run-scoped FCX setup status, message, rendered report, checks, proposed path updates, complete configuration-issue severity/file/section/setting/current/recommended/description data, actions, and fatal errors
- optional Installed YAML Data presence plus selected Main/game role, provenance, schema, SHA-256 and byte length; `Existing`/`Generated` Local Ignore state and exact identity; and diagnostic role/candidate/path/kind/message context
- per-log `Succeeded`, `Failed`, and `CancelledBeforeStart` dispositions
- all applicable `Analysis`, `ReportWrite`, and `UnsolvedLogsFinalization` failures
- Autoscan Report paths and movement state
- discovery-ordered terminal logs and Rust-owned aggregate counts

For completed or cancelled work, report directories are also derived from terminal Autoscan Report paths and emitted through `reportDirectoriesResolved(...)` when non-empty.

When intake metadata is present, `ScanWorker` emits the Qt-owned snapshot through
`installedYamlDataResolved(...)` before terminal lifecycle signals can destroy
the worker. `ScanController` relays it as `scanInstalledYamlDataResolved(...)`;
MainWindow clears stale state at scan start, retains the complete snapshot past
worker lifetime, logs exact identities and diagnostics, and includes selected
provenance/schema and Local Ignore state in terminal status. Recovery-only scan
states remain reserved for #147.

---

## What Current Tests Assert

[`test_scanrequestbuilder.cpp`](../../classic-gui/tests/test_scanrequestbuilder.cpp) behavior-tests the tagged constructor boundary: one installation root and typed game cross the request seam, empty Targeted input creates Standard discovery, while Targeted input creates Targeted discovery with structured rejections and cannot express Standard movement.

[`test_scan_progress_model.cpp`](../../classic-gui/tests/test_scan_progress_model.cpp) uses `ScanRunContractEvent` directly. It verifies discovery/concurrency initialization, monotonic serialized lifecycle progress, interleaved per-log advancement, late-phase suppression, and full work contribution for a failed `LogFinished` event.

[`test_scanrunpresentation.cpp`](../../classic-gui/tests/test_scanrunpresentation.cpp) verifies paired Targeted rejections, report-directory de-duplication, discovery-ordered typed dispositions and failure stages, every expected lifecycle status, complete FCX setup presentation including configuration-issue current/recommended values, Installed YAML Data presence/identity/generated-Ignore diagnostics, infrastructure-stage/path preservation, and invalid-envelope handling.

[`test_scanworker_cancellation.cpp`](../../classic-gui/tests/test_scanworker_cancellation.cpp) verifies monotonic/idempotent cancellation, that cancellation requested before execution reaches Rust's `CancelledBeforeDiscovery` lifecycle rather than a generic error, and that a completed shared-fixture run publishes typed Installed YAML Data with exact identities.

[`test_scan_settings_wiring.cpp`](../../classic-gui/tests/test_scan_settings_wiring.cpp) pins the worker publication, controller relay, and MainWindow retention/user-visible status wiring. The behavior tests above own lifecycle assertions.

---

## Source-Backed Limits And Caveats

- Observer delivery is serialized but occurs during the synchronous worker-thread call; it is not a UI-thread callback guarantee.
- Status text follows serialized execution-event order, which may interleave across discovered logs.
- `discovery_index` identifies Rust's accepted discovery sequence. It is not necessarily an index into the user's original Targeted input list because inputs may expand, de-duplicate, or be rejected during discovery.
- `LogFinished` reaches the observer only after per-log report writing and applicable movement are final, but Qt waits for the terminal result to present success/failure details.
- `MainWindow::onCrashLogScanned(...)` currently uses notifications as a count increment and ignores their index, success, and path arguments.
- The worker emits an explicit final `100%` update only for `Completed`; cancellation and error terminals restore UI state through their distinct signals.
- No GUI layer resets cancellation or reads process-global FCX state; both capabilities are absent from the shipped scan contract.

---

## Contributor Rule Of Thumb

- Change request policy in Rust and its tagged constructors, not by adding GUI flag combinations.
- When final observer tags or fields change, update the bridge observer documentation, `BatchProgressModel`, presentation tests, and this page together.
- Debug totals and accepted paths from `DiscoveryCompleted`; debug concurrency from `EffectiveConcurrencySelected`; debug success/failure details from the terminal execution result.
- Do not add a second progress DTO, caller-input correlation, completion-order result reconstruction, GUI discovery, or GUI-owned durable finalization to this flow.
