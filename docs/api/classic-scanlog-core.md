# `classic-scanlog-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-scanlog-core/`](../../business-logic/classic-scanlog-core).

`classic-scanlog-core` owns two distinct kinds of behavior:

- independently useful Crash Log parsing, inspection, analysis, and report-assembly utilities
- the single complete Crash Log Scan Run use-case boundary in `scan_run::contract`

A complete run always enters through `scan_run::contract::execute`. Discovery,
setup, intake, scheduling, analysis, Autoscan Report persistence, failed-log
accounting, and Standard-run Unsolved Logs finalization are internal parts of
that operation. They are not public lifecycle building blocks.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Complete Crash Log Scan Runs

The public use-case seam is:

```rust
scan_run::contract::execute(request, cancellation, observer).await
```

It accepts one tagged request, a separate monotonic cancellation control, and
an optional observer. It returns either a meaningful terminal `RunResult` or a
typed run-wide `InfrastructureError`.

There is no public prepared-run, orchestration, batch-lifecycle, direct
Autoscan Report writer, concurrency-policy helper, or process-global FCX
control. Callers that need a complete scan must not assemble those stages
themselves.

### Request contract

`contract::Request` has exactly two intents:

- `Standard` discovers supported Crash Logs from configured sources and carries
  one Standard-only `UnsolvedLogsIntent`.
- `Targeted` resolves explicit candidate paths and reports accepted and rejected
  inputs in deterministic order. It has no Unsolved Logs movement capability.

Use the invariant-preserving factories:

- `Request::standard(configuration, source, unsolved_logs)`
- `Request::standard_with_fcx(configuration, source, unsolved_logs, setup_context)`
- `Request::targeted(configuration, source)`
- `Request::targeted_with_fcx(configuration, source, setup_context)`

The tagged representation makes Targeted movement unrepresentable. The FCX
factories require `CrashLogScanSetupContext`, so FCX cannot be enabled without
run-scoped setup facts.

`Configuration` contains the projected, already-accepted facts needed by Rust:
YAML roots, game and version, analysis options, FormID database paths, an
optional configured Unsolved Logs destination, and optional explicit
concurrency. The scan module does not open or persist frontend User Settings.
Adapters project one accepted settings snapshot into this configuration.

Omitting concurrency selects Rust's adaptive value. A present zero is invalid
and returns `InfrastructureErrorStage::RequestValidation`. The selected value
is emitted once through `Event::EffectiveConcurrencySelected` and retained in
the terminal result.

### Cancellation contract

`contract::Cancellation` is separate from the request and is monotonic: it can
be requested and inspected, but not reset.

Cancellation is cooperative at Rust-owned safe seams:

- cancellation before discovery completes returns `CancelledBeforeDiscovery`
  and no discovery result
- once discovery completes, the complete discovery result is retained
- queued logs do not start after cancellation is observed
- an admitted log finishes analysis, report persistence, and applicable
  Unsolved Logs finalization before its terminal outcome is published

Terminal results distinguish completed work from
`LogDisposition::CancelledBeforeStart`; callers do not infer cancellation from
missing events or free-form text.

### Observer and event contract

Observation is optional and non-controlling. `contract::Observer` receives
serialized calls in execution order for:

- `DiscoveryCompleted`
- `EffectiveConcurrencySelected`
- `LogQueued`
- `LogStarted`
- `LogPhase` with `Setup`, `Parse`, `Analyze`, or `Finalize`
- `LogFinished` with `Succeeded`, `Failed`, or `CancelledBeforeStart`

Log-scoped events carry a discovery index and path. Event order describes live
execution and may interleave across logs; it is not terminal result order.
Observer delivery failure is outside the core result. An adapter may record the
delivery problem and explicitly request cancellation through the separate
control, but observation itself cannot change scheduling or outcomes.

### Terminal result and ordering

`RunResult` retains:

- `Completed`, `NoCrashLogsFound`, `SetupFailed`,
  `CancelledBeforeDiscovery`, or `Cancelled`
- the complete discovery result when discovery finished
- the run-scoped FCX setup result when applicable
- Rust-selected effective concurrency when selection occurred
- aggregate total, succeeded, failed, and cancelled counts
- one `LogResult` per accepted log, always in discovery order

Each `LogResult` carries its discovery index, Crash Log path, optional Autoscan
Report path, disposition, all structured failures, movement state, timing, and
analysis counts. A failed log can retain more than one failure; do not collapse
analysis, report-write, and movement failures into one message.

`NoCrashLogsFound`, setup failure, cancellation, and per-log failures are
expected lifecycle data. They are not run-wide exceptions.

### Durable finalization

For an admitted log, Rust owns one durable unit:

1. analyze the accepted Crash Log
2. persist its sibling `{stem}-AUTOSCAN.md` report when analysis produced one
3. for eligible Standard failures, finalize the configured Unsolved Logs move
4. emit `LogFinished`

Destination collision handling and partial filesystem failure reporting are
implemented once in Rust. Targeted requests never resolve or apply an Unsolved
Logs destination.

---

## Error Contract

`InfrastructureError` is reserved for failures that prevent a meaningful
terminal run result. It contains a stable stage, human-readable message, and an
optional relevant path.

Stable stages are:

- `RequestValidation`
- `Discovery`
- `Intake`
- `FormIdDatabaseAccess`
- `Initialization`
- `InternalInvariant`

Per-log durable failures use `LogFailureStage::{Analysis, ReportWrite,
UnsolvedLogsFinalization}` inside `RunResult`. See
[`error-contract.md`](error-contract.md) for the CXX, Node, and Python
projections.

---

## Independently Useful Public Utilities

The complete-run boundary does not absorb tools whose use-case is independent
of scan execution. These utilities do not discover logs, persist Autoscan
Reports, move failed logs, or select run concurrency.

### Parsing

- `LogParser` parses Bethesda-style Crash Logs into named sections, header
  facts, addresses, FormIDs, plugins, and error markers.
- `StreamingLogParser` and `StreamingIteratorParser` support bounded-memory
  parsing of large inputs.
- `PatternMatcher` provides reusable pattern matching without starting a scan.

Deprecated parsing aliases are not an alternate run seam; new code should use
the canonical parser methods documented in source.

### Focused analyzers

- `FormIDAnalyzerCore` extracts, validates, and optionally resolves FormIDs.
- `PluginAnalyzer` detects and classifies plugin references.
- `RecordScanner` scans call stacks for named records and lazily caches its
  per-instance Aho-Corasick matchers with `std::sync::OnceLock`.
- `SuspectScanner` applies suspect and error heuristics to supplied sections.
- `SettingsValidator` evaluates supplied settings data.
- `GpuDetector` extracts GPU information.
- the mod detector and crashgen version/registry helpers operate on supplied
  data without owning a run lifecycle.

Batch-shaped helpers on these focused value operations remain ordinary utility
APIs. They are not Crash Log admission, scheduling, cancellation, persistence,
or batch-run interfaces.

### Report assembly

`ReportFragment`, `ReportComposer`, `ReportGenerator`, and `StringPool` remain
available for independent report-text assembly. They produce or combine text;
they do not write an Autoscan Report to disk. Full scan persistence belongs
exclusively to `scan_run::contract::execute`.

`AutoscanReportAssembler` owns the canonical report-section order used by the
internal run engine. Its output includes header/version facts, settings and
preflight results, plugins, FormIDs, named records, suspects, run-scoped FCX
facts, and final guidance in deterministic order.

### Papyrus and small detection helpers

Papyrus inspection and small pure helpers such as VR-log and crash-pattern
detection remain independent utilities. They do not start or partially execute
a Crash Log Scan Run.

---

## Runtime And Concurrency

The crate does not create an asynchronous runtime. `contract::execute` is async
and must run on the shared Tokio runtime provided by
[`classic-shared-core`](../../foundation/classic-shared-core).

Scheduling, admission, observer serialization, and effective-concurrency
selection are private implementation details of the final run operation.
CPU-bound parsing may use Rayon internally, but adapters do not own either
runtime or reconstruct the scheduling policy.

---

## Binding And Frontend Contract

CXX, Node, and Python expose language-appropriate projections of the same
request, cancellation, observer, result, and error contract. The CLI, GUI, TUI,
and binding-local CLIs construct requests and present Rust-owned facts; they do
not perform discovery, select concurrency, reset FCX state, write reports, or
move failed logs around the call.

Cross-interface behavior is pinned by
[`tests/fixtures/crash_log_scan_run/manifest.json`](../../tests/fixtures/crash_log_scan_run/manifest.json).
The binding compliance suite checks both exhaustive variant acknowledgement and
the absence of contracted execution exports from source, declarations, stubs,
runtime registries, and parity baselines.

---

## Example

```rust
use classic_scanlog_core::scan_run::contract::{
    self, Cancellation, Configuration, Options, Request,
};
use classic_scanlog_core::{
    CrashLogScanFacts, StandardCrashLogScanSource, StandardUnsolvedLogsIntent,
};
use classic_shared_core::GameId;
use std::path::PathBuf;

# async fn example() -> Result<(), Box<dyn std::error::Error>> {
let request = Request::standard(
    Configuration {
        yaml_dir_root: PathBuf::from("C:/CLASSIC"),
        yaml_dir_data: PathBuf::from("C:/CLASSIC/CLASSIC Data"),
        game: GameId::Fallout4,
        game_version: "auto".to_string(),
        options: Options::new(false, false),
        scan_facts: CrashLogScanFacts {
            formid_database_paths: Vec::new(),
            unsolved_logs_destination: None,
        },
        max_concurrent: None,
    },
    StandardCrashLogScanSource {
        base_directory: PathBuf::from("C:/CLASSIC"),
        custom_scan_directory: None,
        configured_documents_root: None,
    },
    StandardUnsolvedLogsIntent::LeaveInPlace,
);

let cancellation = Cancellation::new();
let result = contract::execute(request, &cancellation, None).await?;
for log in result.logs {
    println!("{}: {:?}", log.crash_log.display(), log.disposition);
}
# Ok(())
# }
```

When a public contract type or variant changes, update the applicable CXX,
Node, and Python projections, generated declarations/stubs, runtime coverage
registries, parity baselines, this page, and the binding compliance manifest in
the same change.
