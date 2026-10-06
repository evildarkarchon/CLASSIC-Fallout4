# `classic::scanner` Crash Log Scan Run Observer Contract

Contributor-facing documentation for the final CXX observer declared in
[`cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h`](../../cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h)
and projected by
[`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs).

The CXX bridge exposes one complete scan operation:

```cpp
auto operation = scan_run_contract_execute(request, cancellation, observer,
                                           ScanRunObserverFailurePolicy::CancelRun);
auto execution = scan_run_contract_execution_take_result(*operation);
```

`operation` is Rust-owned because a recovery-required result may also retain a
non-cloneable `ScanRunContinuation`. Call
`scan_run_contract_execution_has_continuation`, then
`scan_run_contract_execution_take_continuation`; resume it exactly once with
`scan_run_continuation_resume(...)` and either `ProceedWithoutIgnore` or
`ResetToDefault`, then take that
operation's result envelope. Resume emits post-discovery events only.

`scan_run_continuation_abandon(...)` claims the same continuation without a
decision, for a user who backs out. It takes an observer for signature symmetry
with resume — so one adapter can be wired to both — but emits **nothing**:
cancellation short-circuits ahead of every stage that produces an event, which
is also why nothing on disk is touched. A frontend must therefore not treat
"observed no event" as a delivery failure on this path.

`scan_run_pending_recovery_settle(pending, settlement, observer, policy)` is the settled
form of the same two calls (see `classic-cpp-bridge-data-entrypoints.md`). With
a decision it emits post-discovery events only, like resume; with no decision it
emits nothing, like abandon. The observer is the only callback involved; the
recovery decision itself never crosses the bridge as a callback.

There is no CXX batch-scan callback, orchestration object, prepared-run entry
point, resettable scan token, or direct report-writing operation. Native
frontends construct a tagged request and consume the same Rust-owned lifecycle
as every other adapter.

---

## Observer Declaration

```cpp
class ScanRunObserver {
public:
    virtual ~ScanRunObserver() = default;
    virtual ScanRunObserverDelivery on_scan_run_event(
        const ScanRunContractEvent& event) const noexcept = 0;
};

struct ScanRunObserverDelivery {  // shared CXX struct
    bool failed;
    rust::String message;
};
```

Pass `nullptr` when observation is not needed. A non-null observer must remain
alive for the synchronous CXX call. Rust serializes observer calls in execution
order; worker tasks do not call C++ concurrently.

The callback is `noexcept`; no exception may cross the CXX boundary. It reports
the outcome of each delivery by value instead: return `{}` when the event was
delivered and `{true, "why"}` when presentation or transport failed. Rust then
applies the `ScanRunObserverFailurePolicy` the caller passed to
`scan_run_contract_execute` or `scan_run_pending_recovery_settle`:

- `ContinueRun` lets the run finish
- `CancelRun` requests cancellation on the run's own control at the next safe
  seam

Either way Rust delivers no further events to that observer and reports the
first failure on the envelope as `has_observer_delivery_failure` and
`observer_delivery_failure_message` (a failure with an empty message gets a
generic one). A failure before the run pauses for Local Ignore recovery makes
Rust abandon the recovery, so the envelope comes back cancelled with no pending
recovery or continuation and nothing written. An out-of-range policy throws
before the run starts. The legacy `scan_run_continuation_resume` takes no
policy and continues the run.

---

## Event Shape

`ScanRunContractEvent.kind` selects the meaningful payload:

| Kind | Meaningful fields |
|---|---|
| `DiscoveryCompleted` | complete `discovery` result |
| `EffectiveConcurrencySelected` | `effective_concurrency` |
| `LogQueued` | `discovery_index`, `crash_log`, `completed`, `total` |
| `LogStarted` | `discovery_index`, `crash_log`, `completed`, `total` |
| `LogPhase` | log fields plus `phase` |
| `LogFinished` | log fields plus `disposition` |

Fields unrelated to the selected tag contain bridge defaults and must be
ignored.

Progress phases are `Setup`, `Parse`, `Analyze`, and `Finalize`. Finished
dispositions are `Succeeded`, `Failed`, and `CancelledBeforeStart`.

`display_lines` is the one field the tag does not select: every event kind
renders, so it is always populated. It carries what this event *says*, in Rust's
words, already rendered inline on the observer callback before the event crossed
the bridge — there is no later opportunity, because the C++ observer receives a
projected copy and never holds the Rust event.

A single event can produce more than one line. A `DiscoveryCompleted` that
refused some of its targeted inputs states the refusal separately, so a consumer
can style or suppress it without losing the acceptance count.

An observer that shows only some event kinds omits whole lines, which the adapter
contract allows; rewording the ones it keeps is what it may not do. `classic-cli`
omits `LogQueued` and `LogPhase` for exactly this reason — its progress display
already covers both.

The line and segment shape, the six segment kinds, and the rules a consumer must
follow are documented once, under "Display Content on the envelope" in
[`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md).
The same `ScanRunDisplayLine` type is used here.

`discovery_index` refers to the accepted-log sequence emitted by
`DiscoveryCompleted`. It is not necessarily the original Targeted input index:
directories may expand, duplicates may collapse, and unsupported inputs may be
rejected during discovery.

---

## Ordering Guarantees

Observer delivery and terminal results intentionally describe different
orders:

- events are serialized in actual execution order and may interleave across
  admitted logs
- each log's lifecycle is monotonic from queued through finished
- `LogFinished` is not emitted until analysis, Autoscan Report persistence, and
  applicable Unsolved Logs finalization resolve
- terminal `result.logs` is always sorted by discovery order

Consumers use `discovery_index` for live per-log correlation and use the
terminal vector directly for deterministic summaries. They do not reconstruct
terminal ordering from callback arrival order.

---

## Discovery And Concurrency

`DiscoveryCompleted` is the authoritative source for accepted logs, Targeted
rejections, source intent, and searched locations. Frontends initialize totals
from its accepted-log count rather than from a caller-collected list.

`EffectiveConcurrencySelected` reports Rust's admission limit after discovery.
The same value is retained in the terminal result. Native callers do not select
an adaptive worker count locally.

If cancellation prevents discovery completion, neither event is emitted and the
terminal status is `CancelledBeforeDiscovery`. Once discovery completes, that
complete result remains available even if later work is cancelled.

---

## Cancellation And Durable Boundaries

`ScanRunCancellation` is opaque and monotonic. It has `new`, `cancel`, and
`is_cancelled` operations and no reset.

Rust checks cancellation before admitting queued logs. An admitted log is not
interrupted between analysis and durable finalization. A queued accepted log
that never starts appears in the terminal result as `CancelledBeforeStart` and
may receive a corresponding finished event, but never a started event.

---

## Terminal Data And Errors

`ScanRunContractExecutionResult` is an explicit result/error envelope. Initial
execution sets exactly one of `has_result` and `has_error`. Resume sets exactly
one of `has_result`, `has_error`, and `has_resume_error`; the last distinguishes
`ContinuationConsumed`, reset conflict, reset backup failure, reset replacement
failure, and replacement durability uncertainty with stable codes and
applicable structured metadata. Durability uncertainty includes canonical and
verified-backup paths plus malformed, backup, and replacement identities.

The result retains lifecycle status, optional discovery and setup data,
optional Installed YAML Data metadata, optional effective concurrency,
aggregate counts, and discovery-ordered log results. Installed metadata records
the independently selected Main/game provenance and identity, Local Ignore
state and identity, and structured fallback/generation diagnostics from the
single immutable run snapshot. Recovery-required results retain completed
discovery plus `RecoveryRequired` metadata beside the opaque continuation.
Proceed Without Ignore reuses that exact snapshot and projects
`ProceedWithoutIgnore` without reopening files or mutating the malformed
Ignore. Reset To Default reuses the same retained selection, publishes the
config-owned durable repair, and projects `ResetToDefault`, backup metadata, and
the `LocalIgnoreReset` diagnostic. Per-log failures preserve `Analysis`,
`ReportWrite`, and `UnsolvedLogsFinalization` as structured data.

The error side is reserved for run-wide infrastructure failures and preserves
the stable stage, message, and optional path. Expected no-logs, setup,
cancellation, and per-log failure states remain result data.

---

## Active Consumers

The native CLI and Qt GUI implement this observer contract. Both initialize
from discovery and effective-concurrency events, correlate live state by
`discovery_index`, and present typed terminal outcomes after execution returns.

The native CLI's observer reports a presentation failure only by returning a
failed `ScanRunObserverDelivery`; it neither cancels nor records the failure.
The CLI executes and settles under `CancelRun`
(`CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY`) and prints its warning from the
envelope's `has_observer_delivery_failure`.

See:

- [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md)
- [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md)
- [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md)

When an event tag or field changes, update the Rust contract, CXX enum/DTO
mapping, observer consumers, exhaustive mapping tests, parity baseline, shared
contract manifest, and these pages together.
