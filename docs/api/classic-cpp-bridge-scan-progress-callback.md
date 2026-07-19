# `classic::scanner` Crash Log Scan Run Observer Contract

Contributor-facing documentation for the final CXX observer declared in
[`cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h`](../../cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_run_observer.h)
and projected by
[`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs).

The CXX bridge exposes one complete scan operation:

```cpp
auto operation = scan_run_contract_execute(request, cancellation, observer);
auto execution = scan_run_contract_execution_take_result(*operation);
```

`operation` is Rust-owned because a recovery-required result may also retain a
non-cloneable `ScanRunContinuation`. Call
`scan_run_contract_execution_has_continuation`, then
`scan_run_contract_execution_take_continuation`; resume it exactly once with
`scan_run_continuation_resume(..., ProceedWithoutIgnore, ...)` and take that
operation's result envelope. Resume emits post-discovery events only.

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
    virtual void on_scan_run_event(
        const ScanRunContractEvent& event) const noexcept = 0;
};
```

Pass `nullptr` when observation is not needed. A non-null observer must remain
alive for the synchronous CXX call. Rust serializes observer calls in execution
order; worker tasks do not call C++ concurrently.

The callback is `noexcept`. Presentation or transport failure remains an
adapter concern and must not cross the CXX boundary or become a core scan
failure. An adapter that cannot continue presenting events may record the
failure and call `scan_run_cancellation_cancel(...)` to request cancellation at
the next safe seam.

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
one of `has_result`, `has_error`, and `has_resume_error`; the last contains
`ContinuationConsumed` plus stable code `scan_run_continuation_consumed`.

The result retains lifecycle status, optional discovery and setup data,
optional Installed YAML Data metadata, optional effective concurrency,
aggregate counts, and discovery-ordered log results. Installed metadata records
the independently selected Main/game provenance and identity, Local Ignore
state and identity, and structured fallback/generation diagnostics from the
single immutable run snapshot. Recovery-required results retain completed
discovery plus `RecoveryRequired` metadata beside the opaque continuation.
Proceed Without Ignore reuses that exact snapshot and projects
`ProceedWithoutIgnore` without reopening files or mutating the malformed
Ignore. Per-log failures preserve `Analysis`,
`ReportWrite`, and `UnsolvedLogsFinalization` as structured data.

The error side is reserved for run-wide infrastructure failures and preserves
the stable stage, message, and optional path. Expected no-logs, setup,
cancellation, and per-log failure states remain result data.

---

## Active Consumers

The native CLI and Qt GUI implement this observer contract. Both initialize
from discovery and effective-concurrency events, correlate live state by
`discovery_index`, and present typed terminal outcomes after execution returns.

See:

- [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md)
- [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md)
- [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md)

When an event tag or field changes, update the Rust contract, CXX enum/DTO
mapping, observer consumers, exhaustive mapping tests, parity baseline, shared
contract manifest, and these pages together.
