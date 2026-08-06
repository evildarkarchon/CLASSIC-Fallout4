# `classic-gui` Final Scan Run Progress Consumer

Contributor-facing documentation for how the active Qt frontend consumes the final Rust-owned Crash Log Scan Run contract through:

- [`classic-gui/src/workers/scanrequestbuilder.cpp`](../../classic-gui/src/workers/scanrequestbuilder.cpp)
- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)
- [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp)
- [`classic-gui/src/workers/scanrunpresentation.cpp`](../../classic-gui/src/workers/scanrunpresentation.cpp)
- [`classic-gui/src/controllers/scancontroller.cpp`](../../classic-gui/src/controllers/scancontroller.cpp)
- [`classic-gui/src/app/localignorerecoveryprompt.cpp`](../../classic-gui/src/app/localignorerecoveryprompt.cpp)
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

The worker starts exactly one operation and moves out its result envelope:

```cpp
auto operation = scan_run_contract_execute(*request, *m_cancellation, &observer);
auto execution = scan_run_contract_execution_take_result(*operation);
```

Rust owns discovery, Targeted rejection policy, effective-concurrency selection, scheduling, FCX setup evaluation, Autoscan Report persistence, Unsolved Logs finalization, cancellation admission seams, aggregate counts, and terminal ordering. Qt supplies facts and presents the resulting contract; it does not repeat those decisions.

If that envelope reports `LocalIgnoreRecoveryRequired`, the operation still owns an opaque single-use continuation. `ScanWorker` publishes the retained malformed-file metadata, takes the continuation, and synchronously asks `MainWindow` for one explicit choice through `ScanController`. `ScanController::makeLocalIgnoreRecoveryPrompt()` builds that handoff: the returned callable runs on the worker thread, marshals only the message across a `Qt::BlockingQueuedConnection`, and returns a typed decision. The operation, continuation, cancellation control, and original observer remain live on the worker stack throughout, and every path that cannot reach a live controller resolves to `Cancel`. The worker then calls `scan_run_continuation_resume(...)`, takes the resumed envelope, and presents it through the same terminal path.

The worker takes the continuation *before* it asks. That ordering means a prompt that throws drops the continuation instead of leaving the run resumable with an answer the user never gave, and it matches `execute_cli_scan_run(...)` in the native CLI.

Two adapter invariants are reported rather than guessed at: a recovery status with no retained continuation, and a configured-prompt-less worker. Both emit `error(...)` instead of choosing on the user's behalf, so a non-interactive `ScanWorker` can never make an implicit destructive choice.

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

`LogQueued`, `LogStarted`, `LogPhase`, and `LogFinished` update the progress model and emit both progress signals.

Status presentation is no longer event-aware, because it is no longer this frontend's to compose. `eventStatus(...)` renders `ScanRunContractEvent::display_lines`, which `classic-cpp-bridge` populates inline on the observer callback — before the event reaches C++, because this process receives a projected copy and never holds the Rust event. Every event kind renders, including the two the GUI used to phrase itself.

What remains this frontend's is the shape rather than the words: the progress row is a single `QProgressBar` format string, so an event that produced more than one line (a discovery that also states a rejection) is joined onto one line with ` - `.

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

After `scan_run_contract_execute(...)` returns an opaque operation and the
worker moves its result through `scan_run_contract_execution_take_result(...)`,
`presentScanRunExecution(...)` maps the typed envelope into
`ScanRunTerminalPresentation` without flattening distinct lifecycle states.

Terminal mapping:

- `Completed` emits an explicit `100% / Complete` progress update and `finished(total, succeeded, failed)`
- `CancelledBeforeDiscovery` emits `cancelled(...)` and has no discovery payload
- `Cancelled` emits `cancelled(...)` with completed and not-started counts
- `NoCrashLogsFound` emits the dedicated `noLogsFound(...)` signal with searched locations when available; the controller relays `scanNoLogsFound(...)`, and MainWindow restores idle state without presenting an error dialog
- `SetupFailed` emits `error(...)` with structured setup details
- `LocalIgnoreRecoveryRequired` calls `promptLocalIgnoreRecoveryChoice(parent, message, resetAvailable)`, a warning prompt with Back Up & Reset To Default, Continue Without Ignore, and Cancel choices. `message` is the paused run rendered as rich text rather than a sentence about it, because Rust exposes the Installed YAML Data block this decision is about only as part of the rendered run — the same call the native CLI and the TUI made. The dialog sets `Qt::TextBrowserInteraction` so the paths it shows can be opened; its own wording, its buttons, and the descriptions beside them are untouched and land with the gated recovery phase. The first two choices resume the retained run, while cancellation is recorded before a non-mutating placeholder decision so Rust returns the ordinary cancelled lifecycle without touching Local Ignore. Cancel is both the default and the escape button, so Return, Escape, and closing the window are all non-destructive
  - `resetAvailable` comes from `ScanRunInstalledYamlDataPresentation::localIgnoreResetAvailable`, projected from the bridge's `local_ignore_reset_available`. When it is false the reset button is not created, because `resume` claims the single-use continuation before validating the decision and then fails with a typed reset error: nothing on disk changes, but the run cannot be retried without starting over. `ScanWorker` treats absent Installed YAML Data as available, since a run that reported nothing has not reported a denial
- typed continuation replay and Local Ignore reset conflict/backup/replacement errors emit `error(...)`; the stable code stays on `resume_error.code` for a consumer to match on and is deliberately absent from the rendered sentences, because a code is machine-facing identity rather than prose
- a typed infrastructure error emits `error(...)` with the rendered failure block; the typed stage and path stay on `error` for a consumer

The three terminal signals that carry prose — `cancelled(...)`, `noLogsFound(...)`, and `error(...)` — carry the run rendered as **rich text**, because every one of them ends in a `QMessageBox`. `MainWindow::showScanRunMessage(...)` sets `Qt::TextBrowserInteraction` so a run's `Path` segments stay selectable and open from the dialog; `scanRunStatusLine(...)` reduces the same block to its leading line for the progress row, which is a single plain format string and can hold nothing more. Both are Display Layout: the words are identical to the ones the native CLI and the TUI print.

Cancellation after discovery does not interrupt admitted work. Rust finishes durable report/movement handling for admitted logs, prevents later admissions at safe seams, and returns non-started accepted logs as `CancelledBeforeStart`. The worker skips those entries when emitting `logScanned(...)`.

The presentation layer projects:

- the envelope's `display_lines` into Qt-owned `ScanRunDisplayLinePresentation` values, plus the same sequence rendered as plain text (`message`) and as rich text (`richText`). One field covers all three payloads, because `scan_run_contract_execute` and `scan_run_continuation_resume` return the same envelope and the lines describe whichever payload the presence flags select
- the run-scoped FCX setup status, message, rendered report, checks, proposed path updates, complete configuration-issue severity/file/section/setting/current/recommended/description data, actions, and fatal errors. This projection stays this frontend's, because the FCX Mode setup types have not adopted the shared vocabulary and `classic-scan-presentation` deliberately does not render them. It is grouped in *after* the rendered lines rather than spliced into them
- optional Installed YAML Data presence plus selected Main/game role, provenance, schema, SHA-256 and byte length; `Existing`, `Generated`, `RecoveryRequired`, or `ProceedWithoutIgnore` Local Ignore state and exact identity; whether Reset To Default can succeed for this run; and diagnostic role/candidate/path/kind/message context
- per-log `Succeeded`, `Failed`, and `CancelledBeforeStart` dispositions
- Autoscan Report paths and movement state
- discovery-ordered terminal logs and Rust-owned aggregate counts

Structured per-log failures are **not** projected into strings any more. Rust renders one display line per failure beneath the log's outcome, so a `<stage>: <message>` list built here would be the same sentence written twice in two places able to disagree. `ScanWorker` logs the whole rendered run once instead of composing its own per-log warnings.

For completed or cancelled work, report directories are also derived from terminal Autoscan Report paths and emitted through `reportDirectoriesResolved(...)` when non-empty.

When intake metadata is present, `ScanWorker` emits the Qt-owned snapshot through
`installedYamlDataResolved(...)` before terminal lifecycle signals can destroy
the worker. `ScanController` relays it as `scanInstalledYamlDataResolved(...)`;
MainWindow clears stale state at scan start, retains the complete snapshot past
worker lifetime, and includes selected provenance/schema and Local Ignore state
in terminal status through `installedYamlDataStatusSuffix()`. That suffix is the
one place this frontend still calls a bridge label accessor directly, and it is
the case they remain correct for: the status row is a single progress-bar format
string with no room for the rendered Installed YAML Data block, so it labels the
enums outside a display line. MainWindow no longer logs identities or
diagnostics itself — `ScanWorker` logs the rendered run, which carries that block
in the words every frontend uses. Recovery first
publishes the malformed-file identity, then successful continuation publishes
the final `ProceedWithoutIgnore` or `ResetToDefault` snapshot and durable reset
metadata before its terminal lifecycle signal.

`formatInstalledYamlDataWarning(...)` then aggregates that snapshot into at most
one run-level warning, which `MainWindow::onScanInstalledYamlDataResolved(...)`
hands to `onScanWarning(...)` — the same presentation Targeted discovery
rejections reach through `ScanController::scanWarning`.

What that warning *says* is no longer this frontend's. Its body is the run's
rendered lines under a GUI-owned section header, carried on
`ScanRunInstalledYamlDataPresentation::runDisplayLines`. It carries the whole run
rather than the Installed YAML Data block alone because Rust exposes that block
only as part of `render_run_result`, and selecting it back out by position would
be a structural assumption about a sequence that deliberately carries no
structure — the same call the native CLI and the TUI made for their recovery
prompts.

Which lines the dialog withholds is still deliberately selective, and still this
frontend's, because omitting whole lines is what an adapter may do. A withheld
line is recognised by the diagnostic message it carries as its `Emphasis`
payload, a value this frontend already holds a typed copy of and compares rather
than parses:

- degraded selection diagnostics (cache unavailable, missing, read, invalid
  UTF-8, parse, invalid/incompatible schema, invalid role data) are shown with
  their role, candidate provenance, and path, all of which Rust already renders
  onto the diagnostic's line
- a durable Local Ignore reset is shown with its byte-exact backup location and
  identity, because that is the only way a user recovers the replaced edits.
  Those are Rust's `Local Ignore backup:` and `Local Ignore replacement:` lines,
  and their paths are actionable in the dialog
- `LocalIgnoreGenerated` is excluded: generating an absent Local Ignore file from
  the selected Main defaults is an expected successful path, so a clean first run
  never interrupts the user
- the pre-decision `RecoveryRequired` snapshot is excluded, because the choice
  dialog is that snapshot's presentation; warning there would double-report the
  problem and interrupt the user before they can answer
- once the run state is `ProceedWithoutIgnore` or `ResetToDefault`, Local Ignore
  diagnostics are excluded as well. Rust attributes a role to Main and game
  selection diagnostics but not to Local Ignore ones, so the absent role is what
  separates the two. Both decisions leave the original diagnostic in the resumed
  snapshot — `ProceedWithoutIgnore` leaves the malformed file in place entirely —
  and re-reporting it would warn about a question the user just answered. A reset
  still warns, because its durable backup location is information the dialog
  could not have given
- the `LocalIgnoreReset` diagnostic line itself is withheld under those same two
  states, because the backup and replacement lines beside it say the same thing
  with the paths attached

These diagnostics are run-level only. Nothing in this path contributes to
Autoscan Report content.

---

## What Current Tests Assert

[`test_scanrequestbuilder.cpp`](../../classic-gui/tests/test_scanrequestbuilder.cpp) behavior-tests the tagged constructor boundary: one installation root and typed game cross the request seam, empty Targeted input creates Standard discovery, while Targeted input creates Targeted discovery with structured rejections and cannot express Standard movement.

[`test_scan_progress_model.cpp`](../../classic-gui/tests/test_scan_progress_model.cpp) uses `ScanRunContractEvent` directly. It verifies discovery/concurrency initialization, monotonic serialized lifecycle progress, interleaved per-log advancement, late-phase suppression, and full work contribution for a failed `LogFinished` event.

[`test_scanrunpresentation.cpp`](../../classic-gui/tests/test_scanrunpresentation.cpp) verifies paired Targeted rejections, report-directory de-duplication, discovery-ordered typed dispositions and failure stages, every expected lifecycle status including Local Ignore Recovery Required, complete FCX setup presentation including configuration-issue current/recommended values, Installed YAML Data presence/identity/generated-Ignore diagnostics, consumed-resume and structured reset/infrastructure error preservation, and invalid-envelope handling. It additionally pins the canonical Display Label for **every** variant of the five enums the presentation layer renders one for — Local Ignore state, Installed YAML Data provenance and diagnostic kind, infrastructure error stage, and Local Ignore reset failure stage. Quoting those strings as literals is deliberate: it is how a wording the Rust core settled is held across the binding boundary, so a core-side reword surfaces as a decision rather than as silently changed GUI output.

[`test_display_label_audit.cpp`](../../classic-gui/tests/test_display_label_audit.cpp) is the structural half of the same guarantee. It reads `classic-gui/src/` as text and asserts that no GUI source turns an audited enum into a string literal, counting occurrences rather than naming functions so a table written into an already-audited file is caught without anyone extending the test. It also asserts that the six rendered labels are still fetched from their bridge accessors, and carries a meta-test that fails when its own hand-written file list falls behind `src/`. Per-log disposition is audited negatively but not positively: the GUI renders no label for it, by the decision recorded at `presentLog`.

[`test_scanworker_cancellation.cpp`](../../classic-gui/tests/test_scanworker_cancellation.cpp) verifies monotonic/idempotent cancellation, that cancellation requested before execution reaches Rust's `CancelledBeforeDiscovery` lifecycle rather than a generic error, that a completed shared-fixture run publishes typed Installed YAML Data with exact identities, and all three malformed Local Ignore choices. Reset preserves malformed bytes in a verified backup and finishes the same scan, Proceed Without Ignore finishes without changing the file, and Cancel emits the ordinary cancelled lifecycle without backup or mutation. It also pins the two adapter invariants: a worker with no configured prompt, and a prompt that throws, both fail the run with the malformed file and the backup directory untouched.

[`test_scancontroller_recovery.cpp`](../../classic-gui/tests/test_scancontroller_recovery.cpp) exercises `makeLocalIgnoreRecoveryPrompt()` across a real worker thread: an unconfigured controller answers `Cancel`, each configured decision round-trips with its message, a worker-thread request is answered on the controller's thread while the caller blocks, and a destroyed controller degrades to `Cancel` rather than replaying its old answer.

[`test_localignorerecoveryprompt.cpp`](../../classic-gui/tests/test_localignorerecoveryprompt.cpp) drives the real modal dialog. It asserts that exactly the three choices are offered, that each button returns its typed decision, and that closing the window, Escape, and Return all resolve to `Cancel` so no keystroke can authorize a durable reset.

[`test_scan_settings_wiring.cpp`](../../classic-gui/tests/test_scan_settings_wiring.cpp) pins the worker publication, controller relay, and MainWindow retention/user-visible status wiring by source inspection. It no longer inspects the recovery flow: the three behavior tests above own that ground at runtime.

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
