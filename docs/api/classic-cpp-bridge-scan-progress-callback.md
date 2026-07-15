# `classic::scanner` Scan Progress Callback Contract

Contributor-facing documentation for the current batch scan progress callback contract declared and used by:

- [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs)
- [`cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h`](../../cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h)

This page documents the callback behavior visible in source today for the active Rust/C++ scan path.

It is intentionally narrower than [`classic-scanlog-core.md`](classic-scanlog-core.md): the lower-level crate exposes per-log phase progress through `OrchestratorCore::process_log_with_progress(...)` and now owns the indexed/evented batch driver, while the callback contract described here is the C++ bridge mapping of those core events into bridge DTOs.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- what a C++ `ScanBatchProgressCallback` implementation is expected to receive
- where `BatchProgressEvent` and its enums are declared
- how Rust batch scanning queues, orders, and drains callback events
- which parts of the progress behavior come from `classic-scanlog-core` and which parts are added by the C++ bridge
- which current limits frontend contributors should treat as source-backed behavior rather than assumptions

This page is for contributors working on the active Rust/C++ path.

For the broader `classic::scanner` entry points, see [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md). For the active Qt consumer path, see [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md). For the underlying scan engine, see [`classic-scanlog-core.md`](classic-scanlog-core.md).

---

## Where The Contract Lives

## C++ declaration

The callback interface itself is declared in [`cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h`](../../cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h):

```cpp
class ScanBatchProgressCallback {
public:
    virtual ~ScanBatchProgressCallback() = default;
    virtual void on_batch_progress(const BatchProgressEvent& event) const = 0;
};
```

The header forward-declares `BatchProgressEvent`; the concrete shared DTO and enums are declared in the Rust CXX bridge in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs).

## Rust declaration and use

The bridge-local batch callback contract is defined inside the `#[cxx::bridge(namespace = "classic::scanner")]` module in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs).

The legacy consumers are `orchestrator_process_logs_batch_with_progress(...)`
and `scan_run_execute(...)`. The final Crash Log Scan Run contract uses the
separate optional `ScanRunObserver` described below.

`orchestrator_process_logs_batch_with_progress(...)`:

- calls `OrchestratorCore::process_logs_batch_with_events(...)`
- converts core `BatchScanEventKind` and `ScanProgressPhase` values into bridge event DTOs
- emits bridge-level terminal `Completed` or `Failed` events
- returns `Vec<BatchScanResult>` in completion order after callback emission finishes

`scan_run_execute(request, callback, cancellation_token)`:

- calls `classic_scanlog_core::CrashLogScanRun::run(...)`
- reads selected logs and scan settings from the bridge `ScanRunRequestDto`
- maps `CrashLogScanRunEvent` values into the same `BatchProgressEvent` DTO
- emits terminal `Completed` or `Failed` events after Rust has finalized per-log Crash Log Scan Run work such as Autoscan Report writing and Unsolved Logs movement
- returns `Vec<ScanRunLogResult>` in completion order after callback emission finishes
- observes the caller-provided `ScanCancellationToken` so C++ frontends can cancel queued logs without owning scan-run internals

## Final Crash Log Scan Run observer

[`cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h`](../../cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h)
declares the optional final-contract callback:

```cpp
class ScanRunObserver {
public:
    virtual ~ScanRunObserver() = default;
    virtual void on_scan_run_event(const ScanRunContractEvent& event) const noexcept = 0;
};
```

`scan_run_contract_execute(request, cancellation, observer)` forwards directly
to `classic_scanlog_core::scan_run::contract::execute(...)`. A null observer
means no observation. A non-null observer receives serialized events in
execution order:

- `DiscoveryCompleted`, containing complete retained discovery data
- `EffectiveConcurrencySelected`, containing the exact Rust-selected admission limit
- `LogQueued`
- `LogStarted`
- `LogPhase`, with `Setup`, `Parse`, `Analyze`, or `Finalize`
- `LogFinished`, with `Succeeded`, `Failed`, or `CancelledBeforeStart`

Log event payloads use `discovery_index`, and the terminal result always stores
logs in discovery order even when event/completion order differs. Observer
delivery is non-controlling. Implementations must handle delivery failures
internally and may explicitly request safe cancellation through the same
`ScanRunCancellation`; exceptions must not cross the `noexcept` callback.

The native CLI and Qt GUI are active final-observer consumers. `classic-cli/src/scanner.cpp` lazily creates its progress display from `DiscoveryCompleted`, reports the Rust-selected value from `EffectiveConcurrencySelected`, correlates log events by `discovery_index`, and requests safe cancellation if presentation fails. [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp) likewise implements `ScanRunObserver`, initializes Qt state from discovery and concurrency events, forwards serialized log events through Qt signals, and uses [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp) to keep visible progress monotonic. Neither active native frontend uses `BatchProgressEvent` or completion-order `ScanRunLogResult` correlation. The GUI consumer path is documented in [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md).

---

## Current Event Shape

## `BatchProgressEventKind`

The bridge declares five event kinds:

- `Queued`
- `Started`
- `Phase`
- `Completed`
- `Failed`

These are bridge events, not direct `classic-scanlog-core` enum variants.

## `BatchProgressPhase`

The bridge declares four phases:

- `Setup`
- `Parse`
- `Analyze`
- `Finalize`

`scanner.rs` maps lower-level `classic_scanlog_core::ScanProgressPhase` into the same four phase names with `map_progress_phase(...)`.

## `BatchProgressEvent`

Current shared DTO shape from [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs):

```cpp
struct BatchProgressEvent {
    std::uint32_t completed;
    std::uint32_t total;
    std::uint32_t input_index;
    rust::String log_path;
    BatchProgressEventKind event_kind;
    BatchProgressPhase phase;
    bool success;
};
```

Field meaning in current source:

- `completed` - batch-level completed-log count at emit time
- `total` - total logs in this batch call
- `input_index` - original position in the `log_paths` input slice
- `log_path` - log path associated with this event
- `event_kind` - lifecycle stage for this event
- `phase` - current coarse scan phase
- `success` - meaningful on terminal events; false for non-terminal events the bridge emits today

Practical contributor note:

- `input_index` is the stable correlation key when result order and callback order differ from input order

---

## Current Lifecycle And Ordering

## Per-log lifecycle the core and bridge preserve

The core batch coordinator emits lifecycle events in [`business-logic/classic-scanlog-core/src/orchestrator.rs`](../../business-logic/classic-scanlog-core/src/orchestrator.rs). The bridge maps those core events into C++ DTOs in [`cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator.rs), and bridge-side tests still assert monotonic successful and failed lifecycles.

For one log, the intended lifecycle is:

1. `Queued` + `Setup`
2. `Started` + `Setup`
3. zero or more `Phase` events in `Setup -> Parse -> Analyze -> Finalize` order
4. terminal `Completed` or `Failed`, carrying the last seen phase

The bridge tests explicitly verify monotonic ordering for both successful and failed lifecycles in `scanner.rs`.

## Batch-level ordering rules visible in source

Current behavior across `OrchestratorCore::process_logs_batch_with_events(...)`, `orchestrator_process_logs_batch_with_progress(...)`, and `scan_run_execute(...)`:

- all `Queued` events are emitted first, one per input log, before tasks are started
- `Queued` events use `completed = 0`, `phase = Setup`, and `success = false`
- per-log tasks then run with unordered async buffering, so logs advance concurrently
- the C++ bridge forwards mapped core events directly through the callback
- terminal results and callback events are therefore not globally input-ordered
- returned `BatchScanResult` items are also in completion order, not input order
- `scan_run_execute(...)` returns `ScanRunLogResult` items in completion order and uses the same `input_index` correlation rule

Important distinction:

- the core event stream preserves monotonic ordering per log
- it does not guarantee a globally grouped event stream by input order when multiple logs are active

## Queueing and tie-breaking behavior

The core batch coordinator uses an unbounded Tokio MPSC channel for worker progress events.

Worker tasks do not invoke the C++ callback directly. Instead they:

- send `Started` and `Phase` events into the channel
- return a per-log `AnalysisResult` when scanning finishes

The coordinator loop then chooses between ready progress events and ready task results with a biased `tokio::select!`.

Source-backed tie-breaking rules:

- when both a progress event and a task result are ready, the `tokio::select!` block is `biased` toward progress reception
- this favors surfacing phase updates before terminal result handling when both are visible at the same time

## Drain behavior before terminal events

When a task result arrives, `OrchestratorCore::process_logs_batch_with_events(...)` calls `drain_ready_batch_progress_events(...)` before emitting `Completed` or `Failed`.

That drain step:

- repeatedly `try_recv()`s immediately ready channel events
- on empty channel, yields up to `2` runtime turns so same-log phase sends that were already scheduled can land
- stops after those bounded yields or when the channel disconnects

The source keeps the completed counter update after this drain. As a result, drained `Started` or `Phase` events carry the pre-terminal `completed` count, and the terminal `Completed` or `Failed` event carries the incremented count.

Current consequence for contributors:

- same-log late phase events are usually flushed before terminal `Completed` or `Failed`
- cross-log phase events that are already ready are also forwarded immediately during this drain
- the core does not rebuffer those cross-log events to force strict per-log grouping across the whole batch

## Abnormal end-of-batch behavior

After the main loop, the core still emits any leftover channel-buffered progress events.

The source comment explicitly treats these as an abnormal-shutdown diagnostics path where some task results never surfaced. In that situation, a contributor should not assume every orphaned progress event will be followed by a terminal `Completed` or `Failed` event.

---

## Callback Invocation Notes

The strongest source-backed statement is this:

- worker tasks send progress into a channel
- the bridge invokes `callback.on_batch_progress(&event)` from one coordination path in `emit_progress_event(...)`

That means callback delivery is serialized by the bridge coordinator rather than called concurrently from each worker task.

What the source does not document:

- a UI-thread guarantee
- a specific Rust runtime thread guarantee for callback invocation
- reentrancy guarantees beyond the single coordinator call path shown in `scanner.rs`

Frontend contributors should therefore avoid assuming more than serialized delivery from the bridge side unless they verify the calling layer separately.

---

## Debugging Notes For Frontend Consumers

## Mapping events back to logs

Use the correlation key belonging to the selected contract, never callback arrival order.

- legacy `BatchProgressEvent` / `BatchScanResult` consumers use `input_index`; callback and return order can differ from input order
- the final `ScanRunContractEvent` uses `discovery_index`, which identifies the committed `DiscoveryCompleted.accepted_logs` sequence
- the final terminal result stores logs in discovery order, so final-contract consumers do not rebuild input order from event or completion order
- the active GUI follows the final rule and carries `discovery_index` through its progress model and terminal presentation

## Treat progress as monotonic, not exact phase accounting

The active GUI progress model in [`classic-gui/src/workers/scanprogressmodel.cpp`](../../classic-gui/src/workers/scanprogressmodel.cpp) ranks final `ScanRunContractEvent` tags (`LogQueued`, `LogStarted`, `LogPhase`, and `LogFinished`) and ignores late lower-rank regressions.

That matches the source-backed contract better than assuming:

- every phase will appear exactly once
- every log will emit all four phases
- logs will progress in lockstep

## Understand `completed`

`completed` is a batch snapshot, not a per-log phase counter.

- `Queued`, `Started`, and `Phase` events can all report the same `completed` value
- the count increments only when a terminal result is handled
- terminal `Completed` or `Failed` is the event that carries the updated count for that finished log

## Turn on diagnostics when the stream looks wrong

`scanner.rs` enables extra logging when `CLASSIC_SCAN_DIAGNOSTICS` is present in the environment.

With diagnostics enabled, the bridge logs:

- each emitted event with index, kind, phase, completed count, success, and log path
- a final batch summary with queued, started, phase, completed, failed, and max in-flight counts

This is the main source-backed debugging aid for callback sequencing issues.

---

## Source-Backed Limits And Caveats

- `ScanBatchProgressCallback` is used by `orchestrator_process_logs_batch_with_progress(...)` and `scan_run_execute(...)`; single-log `orchestrator_process_log(...)` has no callback surface.
- The batch callback contract is bridge-local coordination over `OrchestratorCore::process_log_with_progress(...)`, not a direct lower-level batch API contract from `classic-scanlog-core`.
- `Queued` is a bridge-only event kind; lower layers expose phase progress, not queued-batch bookkeeping.
- The bridge currently sets `success = false` on `Queued`, `Started`, and `Phase` events and sets the actual result on terminal events only.
- `orchestrator_process_logs_batch_with_progress(...)` computes adaptive concurrency locally when `max_concurrent == 0`; `scan_run_execute(...)` delegates that default to `classic-scanlog-core` through `CrashLogScanRun`.
- Legacy `BatchScanResult`, legacy `ScanRunLogResult`, and their callback events use completion order at the batch level; those callers must use `input_index` when stable original ordering matters. The final contract instead returns discovery-ordered log results and uses `discovery_index` on observer events.
- The bridge uses an unbounded progress channel, so the current contract does not expose backpressure semantics to C++ callers.
- The ready-event drain is bounded to two empty yields; it improves same-log ordering but is not a proof of globally strict ordering under every scheduler timing.
- The source comments explicitly allow leftover non-terminal events to be emitted in abnormal shutdown paths after the main loop.

These are current behavior notes, not a future callback design.

---

## Contributor Rule Of Thumb

- If you are changing only scan phases in `classic-scanlog-core`, check whether the bridge enum mapping and this page still match.
- If you change `BatchProgressEvent`, `BatchProgressEventKind`, or `BatchProgressPhase` in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs), update this page and any active C++ consumers in the same change.
- If frontend progress looks unstable, inspect Rust diagnostics first, then the Qt-side rank and aggregation model.
- If you need stronger guarantees than the current source provides, document them only after the bridge and tests make them real.
