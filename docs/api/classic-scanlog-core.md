# `classic-scanlog-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-scanlog-core/`](../../business-logic/classic-scanlog-core).

`classic-scanlog-core` owns two distinct kinds of behavior:

- independently useful Crash Log parsing, inspection, and semantic-analysis utilities
- the single complete Crash Log Scan Run use-case boundary in `scan_run::contract`

A new run always enters through `scan_run::contract::execute`. A run paused for
Local Ignore recovery resumes only through its returned
`CrashLogScanRunContinuation`. Discovery,
setup, intake, scheduling, analysis, Autoscan Report persistence, failed-log
accounting, and Standard-run Unsolved Logs finalization are internal parts of
that operation. They are not public lifecycle building blocks.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Complete Crash Log Scan Runs

The public use-case seam is:

```rust
scan_run::contract::execute(request, cancellation, observer, observer_failure_policy).await
```

It accepts one tagged request, a separate monotonic cancellation control, an
optional observer, and the [observer failure
policy](#observer-delivery-failure-policy). It returns either a meaningful
terminal `RunResult` or a typed run-wide `InfrastructureError`.

`scan_run::contract::execute_in_version_registry_scope(request, version_registry,
cancellation, observer, observer_failure_policy)` runs the same operation but reads Version Registry
metadata only from the supplied
[`VersionRegistryScope`](classic-version-registry-core.md#version-registry-scopes):
Standard XSE Folder discovery, FCX setup, Installed YAML Data metadata, the
analysis configuration, and per-log crashgen and plugin-limit analysis. A
continuation returned for Local Ignore recovery keeps the scope, so `resume`
reads it too. `execute` uses the process default scope. This variant still
hashes FCX setup inputs through the process default `FileHashScope`.

`scan_run::contract::execute_in_scopes(request, version_registry, file_hash,
yaml_file_cache, cancellation, observer, observer_failure_policy)` additionally carries an opaque
[`FileHashScope`](classic-file-io-core.md#file-hash-scopes) and an opaque
[`YamlFileCacheScope`](classic-shared-core.md#cache-scopes). The FCX Game Setup
Intake step hashes the game executable and XSE scripts through
`GameSetupIntake::run_in_scopes(&file_hash, &version_registry)`, so those cache
entries and hit/miss counters land only in `file_hash`. Standard discovery
reads the installation's Game Local document (to derive the XSE Folder)
through `classic_scangame_core::resolve_xse_folder_for_scan_in_scopes`, so its
path/mtime YAML-file cache entries and counters land only in `yaml_file_cache`
(issue #234). A Local Ignore continuation keeps every scope. `execute` and
`execute_in_version_registry_scope` pass the process default hash and
YAML-file cache scopes, so unscoped Rust, CXX, and Node scan runs keep hashing
and reading exactly as before. The Python `classic_scanlog` facade runs every
scan through `execute_in_scopes` with its own isolated Version Registry scope,
`FileHashScope`, and `YamlFileCacheScope`, chosen at facade entry, so its FCX
hashing never reaches the `classic_file_io` or `classic_scangame` caches or
statistics, and `classic_config.clear_yaml_cache()` cannot evict its cached
Game Local reads. Public-interface probes: `tests/file_hash_scope.rs`,
`tests/yaml_file_cache_scope.rs`, and `tests/version_registry_scope.rs`.

Malformed Local Ignore is a meaningful `LocalIgnoreRecoveryRequired` result.
That result owns an opaque `CrashLogScanRunContinuation`; callers explicitly
choose `LocalIgnoreRecoveryDecision::ProceedWithoutIgnore` or
`LocalIgnoreRecoveryDecision::ResetToDefault`. Calling
`continuation.resume(decision, cancellation, observer, observer_failure_policy).await` consumes the
retained work once and returns `Result<RunResult, ResumeError>`.

A caller that wants to back out instead of deciding calls
`continuation.abandon(cancellation, observer).await`. It requests cancellation
on the supplied control and then claims the continuation with a decision the
run never acts on, so no recovery is applied, nothing on disk is touched, and
the caller receives the ordinary post-discovery `Cancelled` result described
under [Cancellation contract](#cancellation-contract). `LocalIgnoreRecoveryDecision`
deliberately has no abandonment variant — adding one reshapes a type crossing
five binding surfaces — so `abandon` is the single shared implementation of a
sequence every frontend would otherwise write for itself. It shares `resume`'s
one-shot claim: whichever of the two runs first spends the continuation, and
every later `abandon` or `resume` returns `ResumeError::ContinuationConsumed`.

#### Pending and settled recovery (ADR-0009)

`resume` and `abandon` are being replaced by settling a pending recovery. Both
shapes exist while frontends migrate; #282 removes `resume`, `abandon`, and the
`RunResult::continuation` field.

- `RunResult::take_pending_recovery(&mut self) -> Option<PendingRecovery>` takes
  the continuation out of a paused result and returns `Some` exactly when the run
  paused. The rest of the result stays readable for rendering the pause.
- `PendingRecovery` bundles the single-use continuation, the paused run's own
  `Cancellation` (the control the caller passed to `execute`), and the typed
  recovery facts (`installed_yaml_data()`, whose `local_ignore_reset_available`
  decides whether Reset To Default can be offered). A recovery status with no
  continuation cannot be represented.
- `cancellation_requested()` reads that control live. When it is `true`, a
  frontend does not prompt: it settles with no decision.
- `settle(decision: Option<LocalIgnoreRecoveryDecision>, observer,
  observer_failure_policy).await` returns `Result<SettledRunResult, ResumeError>`. `Some(decision)` resumes the
  same discovered Crash Logs without rediscovery; Reset To Default is still the
  non-interruptible transaction. `None` is abandonment with `abandon`'s
  semantics: it cancels the run's control, then finishes cancelled after
  discovery with no filesystem work. Abandonment is still not a third decision.
  `settle` borrows, so a replay is the typed `ResumeError::ContinuationConsumed`.
- `SettledRunResult` has `RunResult`'s fields minus the continuation, so a
  settled run cannot ask for a second recovery. Compile-fail doctests pin that.
  `From<SettledRunResult> for RunResult` lets an adapter reuse one projection.
- `PendingRecovery::continuation()` exposes the same continuation to the legacy
  resume and abandon binding surfaces, so they share the one claim with `settle`.
  It goes away with them.

The recovery prompt is Display Content and is not part of `PendingRecovery`:
`classic-scan-presentation` bundles it as `PendingRecoveryWithPrompt` (see
[classic-scan-presentation.md](classic-scan-presentation.md)), keeping this
crate free of any dependency on the presentation crate.

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
one CLASSIC installation root, a typed `GameId`, the selected game-version
mode, analysis options, FormID database paths, an optional configured Unsolved
Logs destination, and optional explicit concurrency. The scan module derives
installed YAML Data locations from the root; adapters do not pass separate YAML
directories or parse a game string. The scan module does not open or persist
frontend User Settings. Adapters project one accepted settings snapshot into
this configuration.

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
- cancellation already requested before recovery resume consumes the
  continuation and returns the normal post-discovery `Cancelled` result;
  `CrashLogScanRunContinuation::abandon` is that behaviour named, requesting
  cancellation itself and leaving the control cancelled afterwards, and
  `PendingRecovery::settle(None, ..)` is the same operation on the settled
  surface
- a pending recovery reports cancellation already requested on the run's own
  control, so a frontend can skip the prompt
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

### Observer delivery failure policy

Event delivery can fail. `Observer::on_event` returns
`Result<(), ObserverDeliveryFailure>`; a closure returning `()` is an observer
that always delivers, and a closure returning that `Result` can fail. The
caller chooses an `ObserverFailurePolicy` at execution and settling time —
`execute(request, &cancellation, observer, policy)` (and the scoped variants)
and `PendingRecovery::settle(decision, observer, policy)`:

- `ContinueRun` lets the run finish normally
- `CancelRun` requests cancellation on the run's own control at the first
  failed delivery, at the same safe seams as any other cancellation

Under either policy Rust delivers no further events to an observer once one
delivery failed, and reports the first failure as
`observer_delivery_failure: Option<ObserverDeliveryFailure>` on `RunResult`,
`SettledRunResult`, and `InfrastructureError` (a failure that preceded a
run-wide error is not lost). Adapters read "delivery failed" there instead of
tracking it in their observers.

A delivery failure **before** the run pauses for Local Ignore recovery makes
Rust abandon that recovery, under either policy: the frontend that would answer
the prompt has lost its view of the run. The run finishes cancelled after
discovery, `take_pending_recovery()` returns `None`, the run's own control is
left cancelled, and nothing on disk is touched — the continuation is never
dropped un-abandoned. With `CancelRun` the cancellation usually lands before
intake, so the run never pauses in the first place.

`CrashLogScanRunContinuation::resume` takes the policy as well while it exists;
`abandon` takes none, because cancellation short-circuits it ahead of every
event.

### Terminal result and ordering

`RunResult` retains:

- `Completed`, `NoCrashLogsFound`, `SetupFailed`,
  `LocalIgnoreRecoveryRequired`,
  `CancelledBeforeDiscovery`, or `Cancelled`
- the complete discovery result when discovery finished
- the run-scoped FCX setup result when applicable
- the selected Installed YAML Data metadata when intake was reached
- Rust-selected effective concurrency when selection occurred
- aggregate total, succeeded, failed, and cancelled counts
- one `LogResult` per accepted log, always in discovery order

Each `LogResult` carries its discovery index, Crash Log path, optional Autoscan
Report path, disposition, all structured failures, movement state, timing, and
analysis counts. A failed log can retain more than one failure; do not collapse
analysis, report-write, and movement failures into one message.

`NoCrashLogsFound`, setup failure, cancellation, and per-log failures are
expected lifecycle data. They are not run-wide exceptions.

`LocalIgnoreRecoveryRequired` also retains completed discovery, setup data,
the exact selected Main/game snapshot, malformed Local Ignore identity and
diagnostics, and an opaque process-local continuation. The continuation is not
cloneable or serializable. Its state is atomically consumed, so sequential or
concurrent replay returns `ResumeError::ContinuationConsumed` with stable kind
`scan_run_continuation_consumed`. Resume never emits a second
`DiscoveryCompleted` event.

### Installed YAML Data intake

After discovery, the final operation loads Installed YAML Data once from the
configuration's installation root and typed game. Main and game candidates are
selected independently from updated, read-only previous, or bundled sources;
missing Local Ignore is generated from the exact selected Main defaults. The
ready immutable snapshot supplies both parsed analysis data and simplify-log
rules for the entire run. Scan execution never reopens selected Main, game, or
Local Ignore paths after accepting that snapshot.

`RunResult::installed_yaml_data` exposes stable run-level metadata: selected
Main/game schema, provenance and exact-byte identity, Local Ignore state and
identity, and structured fallback, validation, or generation
diagnostics. It is absent when initial execution did not reach intake. A
pre-resume cancellation also intentionally returns the ordinary
cancelled-after-discovery shape without recovery metadata, because the recovery
decision was never applied. These diagnostics are operational metadata and
never enter Autoscan Report text; equivalent accepted data therefore preserves
report bytes.

Ready runs expose `Existing` and `Generated`. A malformed file returns
`RecoveryRequired`; accepting Proceed Without Ignore resumes with
`ProceedWithoutIgnore` and an operation-scoped empty ignore list. Accepting
Reset To Default conflict-checks the retained malformed identity, verifies a
durable byte-exact backup, atomically publishes retained selected-Main defaults,
and resumes with `ResetToDefault`, reset diagnostics, and backup/replacement
metadata. The retained plan is consumed only at resume, so either decision
reuses the exact prepared intake and selected snapshot without rediscovery or
reselection. Changing Main/game files or creating a formerly missing Targeted
input while paused cannot change the resumed run.

Cancellation already observed before Reset To Default begins performs no
backup, replacement, or analysis. Once the synchronous reset transaction has
begun, cancellation is not observed again until publication returns. A
successful transaction completes durably, then returns the ordinary
post-discovery `Cancelled` result without analysis when cancellation raced it. Reset
conflict, backup failure, replacement failure, and replacement durability
uncertainty are distinct typed `ResumeError` variants with stable codes and
applicable identities, paths, and publication stage metadata. Durability
uncertainty uses `local_ignore_reset_durability_unknown` and returns canonical
and verified-backup paths plus malformed, backup, and replacement identities;
it is never reported as a successful or cancelled run.

### Vocabulary Tokens and Display Labels

Six enums in the Crash Log Scan Run contract implement the
[Vocabulary naming contract](classic-vocabulary.md), in two groups.

**Three the run crate owns outright.** These concepts live here, so this crate
is the single definition site for both their token and their prose. There is no
counterpart anywhere else in the workspace returning the same strings.

| Enum | Vocabulary Tokens | Display Labels that are more than a respelling |
| --- | --- | --- |
| `LogDisposition` | `succeeded`, `failed`, `cancelled_before_start` | — |
| `LogFailureStage` | `analysis`, `report_write`, `unsolved_logs_finalization` | `Unsolved Logs finalization` |
| `InfrastructureErrorStage` | `request_validation`, `discovery`, `intake`, `formid_database_access`, `initialization`, `internal_invariant` | `FormID database access`, `internal invariant validation` |

None of these three settles a wording conflict: the CLI, the GUI, and the TUI
already render exactly these phrases, so adopting them changes no shipped
output. The one gap they closed is the TUI's infrastructure stage, which
rendered the *token* — the frontend now renders these labels, converging on what
the other two already printed.

The right-hand column is what makes labels worth their own form. `Unsolved Logs`
and `FormID` are domain terms carrying glossary capitalization, and
`internal_invariant` names the thing rather than the failure — no mechanical
transform of a token could produce any of the three.

`InfrastructureErrorStage` also implements `Display`, which renders the
**token**, not the label. That is the form embedded in a rendered
`InfrastructureError` message and it is unchanged by this adoption.

**Three contract-stability twins.** This crate declares its own types so that
the types it mirrors stay out of the run contract, and each obtains its naming
by delegating to the enum it mirrors rather than restating it. Nothing in this
crate spells a token or a label for a variant that has a counterpart.

| Enum | Mirrors | Vocabulary Tokens |
| --- | --- | --- |
| `LocalIgnoreRunState` | `LocalIgnoreYamlDataState` | `existing`, `generated`, `recovery_required`, `proceed_without_ignore`, `reset_to_default` |
| `InstalledYamlDataRunDiagnosticKind` | `InstalledYamlDataDiagnosticKind` | `cache_unavailable`, `missing`, `read`, `invalid_utf8`, `parse`, `invalid_schema`, `incompatible_schema`, `invalid_role_data`, `local_ignore_generated`, `local_ignore_reset` |
| `LocalIgnoreResetFailureStage` | `classic-durable-publication`'s `PublicationStage` | `create`, `write`, `flush`, `sync`, `publish` |

The twins are not all symmetrical, and the conformance assertion covers that
rather than assuming a bijection. `InstalledYamlDataRunDiagnosticKind` and
`LocalIgnoreResetFailureStage` are true identity mappings and delegate every
variant. `LocalIgnoreRunState` is identity-plus-one: `RecoveryRequired` has no
configuration counterpart, because a run can pause for a caller decision and a
stored snapshot cannot, so it supplies both `recovery_required` and `recovery
required` locally. Every other variant delegates.

Delegation is what carries the settled wording in for free: `Parse` reads as
`parse failure`, `Read` as `read failure`, `Generated` as `generated from
selected Main defaults`, and `LocalIgnoreReset` keeps the glossary
capitalization in `Local Ignore reset` — none of which this crate had to be
told.

`LocalIgnoreResetFailureStage` delegates for a sharper reason than the other
two. Its source documents itself as *the* stage vocabulary for the whole
workspace, so a twin restating those five strings made that claim untrue. The
labels it inherits equal their tokens, which is that vocabulary's deliberate
choice: these name ordinary steps rather than domain terms, and rewording them
would change what all three frontends print for no reader's benefit.

Each surface exposes a Display Label projection for all six:

| Surface | Projection |
| --- | --- |
| CXX | `scan_run_installed_yaml_data_diagnostic_kind_label`, `scan_run_local_ignore_yaml_data_state_label`, `scan_run_log_disposition_label`, `scan_run_log_failure_stage_label`, `scan_run_infrastructure_error_stage_label`, `scan_run_local_ignore_reset_failure_stage_label` — each takes the frozen FFI mirror enum and returns `String`, or `""` for an out-of-range value |
| Node | the same six names in camelCase. The two twins take a `string_enum` value; the other four take the published snake_case token as a `string`, because this surface publishes those four as bare token strings rather than as `string_enum` types, and they throw for an unrecognized token |
| Python | the same six names, each taking the published snake_case token and raising `ValueError` for anything else |

The label crosses the binding seam as its own entry point rather than being
folded into a DTO string, because two of the three frontends are C++ and a Qt
view is not line-oriented — it wants the variant and its label separately, for
independently styled table columns.

The two Node shapes are a consequence of what each enum already published, not a
new inconsistency: a `string_enum` argument makes an unknown value unreachable,
while a `string` argument makes a typo reachable and therefore worth reporting.
Both surfaces that take a free-form token — Node's four and all six on Python —
reject rather than returning an empty label, because a blank cell in a frontend
carries nothing to diagnose it by.

Adding a variant to a mirrored enum cannot pass silently: the source-to-twin
`match` stops compiling, and if that guard is ever given up for a catch-all arm
the conformance assertion still fails, because it checks that every source
variant is reachable from some twin variant.

Tokens are frozen and changing one is breaking; labels are presentation only and
may be reworded.

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

Focused semantic analyzers use a separate shared `AnalyzerError` containing an
`AnalyzerKind`, stable `AnalyzerErrorCode`, and human-readable message. The
stable analyzer tokens are `crashgen_settings`, `crash_suspect`,
`mod_guidance`, `plugin_evidence`, `formid_finding`, and
`named_record_finding`. The first implemented codes are
`invalid_configuration`, `unsupported_configuration_version`,
`malformed_result`, and `operational_failure`; adapters must project these
tokens rather than inventing language-specific spellings.

Direct focused-analyzer callers receive this typed error unchanged through the
language-appropriate projection. During a complete run, failure to construct
the reusable analyzer set becomes a run-wide `Initialization` infrastructure
error before log scheduling. The private collector retries malformed or
operational FormID Value Lookup failures with lookup disabled because value
descriptions are optional report enrichment. Every other failure while
collecting one log becomes that log's `LogFailureStage::Analysis`, prevents a
partial Autoscan Report from being persisted, and does not convert successful
empty results into failures.

---

## Crash Log Collection And Targeted Input Resolution

The `log_collection` module is the discovery/intake area of this crate. It
moved here from `classic-file-io-core` (#254), so file I/O no longer depends on
XSE Folder resolution or `classic-operation-context`. A Crash Log Scan Run's
Standard discovery builds a `LogCollector` and its Targeted discovery calls
`resolve_targeted_inputs`; the same primitives stay public because the CXX,
Node, and Python collection surfaces expose them directly. Calling them does
not start, schedule, or finalize a run, and never moves Unsolved Logs.

Root re-exports: `LogCollector`, `CRASH_LOG_PATTERN` (`crash-*.log`),
`CRASH_AUTOSCAN_PATTERN` (`crash-*-AUTOSCAN.md`), `resolve_targeted_inputs`,
`TargetedResolution`, and `RejectedInput`. `log_collection::Result<T>` is
`Result<T, classic_file_io_core::FileIOError>`: the moved APIs kept their typed
filesystem error so binding error projections did not change. There is no
re-export from `classic_file_io_core`; import these names from
`classic_scanlog_core`.

### `LogCollector`

Construction and accessors:

- `LogCollector::new(base_folder, xse_folder, custom_folder)`
- `LogCollector::new_for_scan(base_folder, yaml_dir_data, game, selected_game_version, configured_docs_root, custom_folder)` - resolves the XSE Folder through `classic_scangame_core::resolve_xse_folder_for_scan` (config's Game Local facts plus XSE derivation, process default Version Registry snapshot) and keeps the custom folder additive
- `with_current_dir(xse_folder, custom_folder)`
- `crash_logs_dir()` (`<base>/Crash Logs`) and `pastebin_dir()` (`<base>/Crash Logs/Pastebin`)

Workflow methods, all `async` and returning `Result<_, FileIOError>`:

- `move_from_base_folder() -> usize`
- `copy_from_xse_folder() -> usize`
- `collect_crash_logs() -> Vec<PathBuf>`
- `collect_all() -> Vec<PathBuf>`

`collect_all()` flow:

1. Ensure `Crash Logs/` and `Crash Logs/Pastebin/` exist.
2. Move `crash-*.log` and `crash-*-AUTOSCAN.md` from the base folder into `Crash Logs/`.
3. Copy `crash-*.log` from the optional XSE Folder into `Crash Logs/`.
4. Return all `crash-*.log` files found recursively under `Crash Logs/` plus the optional custom folder.

Behavior worth knowing:

- base-folder files are moved, and XSE Folder files copied, only when the destination path does not already exist; XSE originals are preserved
- the custom folder is searched with a non-recursive `crash-*.log` glob and is additive to XSE Folder import, never a replacement
- autoscan markdown is organized by `move_from_base_folder()`, but `collect_crash_logs()` returns only `.log` files and does not deduplicate across sources
- `Io(String)` carries formatted glob or directory-setup failures
- inside the unpublished `classic-operation-context` cancellation scope, collection checks only at safe boundaries between completed directory/file operations and enumeration entries; cancellation discards the accumulator and the public method returns its zero/empty sentinel, which the scope-owning scan service distinguishes by reading the same monotonic control; completed moves and copies are not rolled back

The Crash Log Scan Run does not call `new_for_scan`: it derives the XSE Folder
from the run's own Version Registry scope with
`classic_scangame_core::resolve_xse_folder_for_scan_in_version_registry_scope` and passes it to
`LogCollector::new`.

### `resolve_targeted_inputs`

`resolve_targeted_inputs(inputs: Vec<PathBuf>) -> TargetedResolution` resolves
explicit user-supplied file and directory paths for Targeted runs.

- `TargetedResolution { logs: Vec<PathBuf>, rejected: Vec<RejectedInput> }` - deduplicated accepted logs in first-seen order, plus rejected inputs
- `RejectedInput { path: PathBuf, reason: String }` - the original input and a human-readable reason; the run contract converts it into `CrashLogScanRejectedInput`

Behavior worth knowing:

- explicit regular file inputs are accepted directly regardless of file name
- directory inputs are searched recursively with `**/crash-*.log`
- paths are canonicalized for deduplication while preserving first-seen order
- non-existent paths, non-file/non-directory paths, unreadable paths, and directories without matches are rejected with specific reasons
- no directories are created and no files are moved or copied
- inside the `classic-operation-context` cancellation scope, resolution yields between recursive entries, discards partial accumulators on cancellation, and returns an empty resolution for the scope-owning scan service to discard

## Custom-Scan Folder Policy

The `custom_scan` module owns which folders a user may configure as the
custom-scan folder (an extra, additive Crash Log discovery root). It moved here
from `classic-path-core` (#254 follow-up); path core keeps only Game and
Documents path behavior and has no re-export. Scanlog depends on path core (path
core depends only on shared core), so the graph stays acyclic.

Root re-exports: `is_restricted_path`, `validate_custom_scan_path`, and
`validate_settings_paths`. The fallible functions return
`classic_path_core::ValidationResult<()>`: they kept path core's typed
`ValidationError`, so the variants, messages, and every binding error projection
are unchanged.

- `is_restricted_path(path) -> bool` - heuristic, case-insensitive substring
  checks against `windows`, `program files`, `program files (x86)`,
  `programdata`, `system32`, `syswow64`, and `appdata`; roots and very shallow
  paths (`parent().is_none()` or component count `<= 2`) are also restricted.
  It is string matching, not a canonicalized allow/deny policy.
- `validate_custom_scan_path(path)` - `ValidationError::PathError(..)` when the
  path is missing or not a directory, otherwise
  `ValidationError::RestrictedPath(path)` (`Path is restricted for custom scans: <path>`)
  when `is_restricted_path` rejects it.
- `validate_settings_paths(game_path, docs_path, custom_scan_path, game_exe)` -
  the combined setup check: path core's
  `validate_game_and_documents_paths(game_path, docs_path, game_exe)` first,
  then `validate_custom_scan_path` when a custom-scan folder is given; returns
  the first `ValidationError`.

These helpers are synchronous and touch the filesystem. The Crash Log Scan Run
does not call them; frontends (the TUI settings flow) and the CXX
(`is_restricted_path`, `check_restricted_path`, `path_validate_custom_scan`),
Node (`isRestrictedPath`, `validateCustomScanPath`, `validateSettingsPaths`),
and Python (`classic_path.PathValidator.*`) path surfaces delegate to them with
unchanged export names.

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
- `detect_crash_pattern(content)` classifies the first 30 lines using
  ASCII-case-insensitive symbolic exception names and hexadecimal aliases. It
  returns a stable token (`ACCESS_VIOLATION`, `STACK_OVERFLOW`,
  `INT_DIVIDE_BY_ZERO`, `BREAKPOINT`, `ILLEGAL_INSTRUCTION`,
  `STACK_BUFFER_OVERRUN`, or `HEAP_CORRUPTION`), or `None`. Earlier lines win;
  the shared source table determines priority when one line has multiple known
  patterns. This operation classifies a known error, rather than returning the
  complete main-error text.

Node exposes that classifier as `detectCrashPattern` (`null` for no match),
Python as `detect_crash_pattern` (`None`), and CXX as
`classify_crash_pattern` (empty string). CXX's existing
`detect_crash_pattern` retains its legacy full-main-error-text contract for
compatibility. All token classification is implemented in the Rust core;
the bindings only convert inputs and the optional result.

Deprecated parsing aliases are not an alternate run seam; new code should use
the canonical parser methods documented in source.

### Focused analyzers

The six supported Focused Semantic Analyzers share one ownership contract: an
immutable reusable handle accepts one owned input and returns one aggregate
typed semantic result. Results preserve findings, counts, states, and authored
YAML Data guidance, but never expose report lines or presentation policy. A
completed no-match call returns an explicit empty result. There is no public
Autoscan Report Contribution enum; the aggregate collector is private because
only a complete Crash Log Scan Run needs to coordinate all six results.

- `CrashgenSettingsAnalyzer` is a complete semantic focused analyzer.
  Its fallible constructor validates typed Crashgen configuration and
  normalizes plugin predicate matcher state once. The immutable, cloneable
  handle accepts one owned `CrashgenSettingsAnalysisInput` and is `Send + Sync`.
- `CrashgenSettingsAnalysisResult` always represents completed analysis,
  including the explicit success case where both `expectation_outcomes` and
  `disabled_setting_notices` are empty. Outcomes preserve the YAML-authored
  rule id, expanded message and fix, kind, severity, and YAML-owned Autoscan
  Report Placement without carrying markdown or report lines.
- `CrashSuspectAnalyzer` validates and compiles owned main-error and stack rules
  during construction. Its immutable, cloneable `Send + Sync` handle accepts
  one owned `CrashSuspectAnalysisInput` containing main-error and call-stack
  evidence.
- `CrashSuspectAnalysisResult` contains one `CrashSuspectFinding` for each
  matched main-error rule, matched stack rule, or DLL involvement notice. Rule
  findings retain authored ids, names, and severities; DLL involvement retains
  its typed kind. No finding carries markdown, padding widths, separators, or
  code-authored report prose, and a completed no-match analysis is an explicit
  empty result.
- `ModGuidanceAnalyzer` validates owned conflict, frequent-crash, solution,
  and important-mod configuration and compiles all literal matcher state during
  construction. Its immutable, cloneable `Send + Sync` handle accepts one
  owned `ModGuidanceAnalysisInput` containing plugin load-order ids, optional
  GPU facts, and XSE module names.
- `ModGuidanceAnalysisResult` preserves typed matched, missing, and GPU-mismatch
  state together with authored names, descriptions, optional fixes, links, warnings,
  and matched plugin ids. It carries no headings, group order, icons,
  separators, markdown, or report lines; completed no-match analysis is an
  explicit empty result. A conflict without an authored fix remains `None`, and
  Autoscan Report Assembly omits that remediation line.
- `PluginEvidenceAnalyzer` validates and normalizes owned game-plugin ignore
  configuration during construction. Its immutable, cloneable `Send + Sync`
  handle accepts one owned `PluginEvidenceAnalysisInput` containing call-stack
  lines and plugin identities in caller-provided casing.
- `PluginEvidenceAnalysisResult` contains normalized `PluginEvidence` identities
  with per-line occurrence counts in candidate order. It carries no report prose,
  markdown, headings, or sorting policy; completed no-match analysis is an
  explicit empty result.
- `NamedRecordFindingAnalyzer` validates owned target/ignore patterns and compiles
  both Aho-Corasick matchers during construction. Its immutable, cloneable
  `Send + Sync` handle accepts owned Crash Log lines and returns distinct exact
  extracted records with checked occurrence counts in first-observed order.
- `NamedRecordFindingAnalysisResult` carries no report text or sorting policy;
  completed no-match analysis is an explicit empty result. Autoscan Report
  Assembly alone sorts findings and renders the legacy named-record prose.
- `FormIDFindingAnalyzer` accepts owned Crash Log lines and plugin/prefix facts,
  aggregates distinct canonical FormIDs with checked occurrence counts, resolves
  plugins, and optionally enriches resolved findings through the opaque strict
  `FormIdValueLookup` facade. Its result retains unresolved identifiers and
  distinguishes lookup disabled, miss, and hit states without carrying report
  prose. Lookup misses are data; malformed replies and operational failures use
  the shared typed analyzer error. Public free batch extraction and validation
  helpers remain available for independent utility use.
- `PluginAnalyzer` retains independently useful load-order parsing, plugin-limit,
  filtering, and batch detection utilities; its former report-producing match
  methods are removed. Plugin-limit checks classify the detected game version
  from the process default Version Registry snapshot unless
  `with_version_registry_scope(scope)` selects another scope.
- `RecordScanner` remains a utility-only raw record extractor and lazily caches
  its per-instance Aho-Corasick matchers with `std::sync::OnceLock`. Its former
  report-producing `scan_named_records` family is removed; `contains_record`
  and the record batch utilities remain public.
- `CrashgenSettingsAnalyzer` is the public settings-analysis boundary. It
  returns typed expectation outcomes and disabled-setting notices without
  exposing report fragments or rendering helpers.
- `GpuDetector` extracts GPU information.
- crashgen version/registry helpers operate on supplied data without owning a
  run lifecycle.

Batch-shaped helpers on these focused value operations remain ordinary utility
APIs. They are not Crash Log admission, scheduling, cancellation, persistence,
or batch-run interfaces.

### Report assembly

Autoscan Report rendering mechanics are private implementation details.
`ReportFragment`, `ReportComposer`, `ReportGenerator`, `StringPool`, and the
fragment-producing `SettingsValidator` facade are not public Rust or binding
contracts. Callers use semantic analyzers for focused work or the complete
Crash Log Scan Run contract for persisted reports.

The private contribution collector runs the applicable analyzers without
rendering. A present empty aggregate records completed analysis with no match;
absence records that prepared evidence did not admit the analysis. Any typed
analyzer failure aborts collection for that log instead of offering a partial
contribution set to assembly.

The private `AutoscanReportAssembler` is the sole owner of canonical
report-section order, grouping, sorting, headings, separators, padding, icons,
markdown, and code-authored prose. Its output includes header/version facts,
settings and preflight results, plugins, FormIDs, named records, suspects,
run-scoped FCX facts, and final guidance. Full scan persistence belongs
exclusively to the Rust-owned execution flow started by
`scan_run::contract::execute` and, after an expected recovery pause, completed
by `CrashLogScanRunContinuation::resume`.

Successful runs over identical Crash Log, YAML Data, scan facts, and options
must persist byte-identical Autoscan Reports. The public-seam regression test
[`autoscan_report_goldens.rs`](../../business-logic/classic-scanlog-core/tests/autoscan_report_goldens.rs)
compares persisted bytes against the immutable
[`autoscan_report_goldens`](../../tests/fixtures/autoscan_report_goldens/README.md)
corpus without calling private collector or formatting helpers. See
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

### Papyrus and small detection helpers

Papyrus inspection and small pure helpers such as VR-log and crash-pattern
detection remain independent utilities. They do not start or partially execute
a Crash Log Scan Run.

`detect_vr_log` recognizes `Fallout4VR.exe`, `Fallout4VR.esm`, `SkyrimVR.exe`
and `SkyrimVR.esm` case-insensitively. Node `detectVrLog`, Python
`LogParser.detect_vr_log`, and CXX `detect_vr_log` all delegate to that core
helper. This preserves CXX's existing Skyrim VR recognition while adding the
same markers to Node/Python and executable/case support to CXX.

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

`CrashLogScanRunContinuation::abandon` reaches every surface. The TUI depends on
this crate directly and calls it; CXX exposes it as
`scan_run_continuation_abandon`, Node as `scanRunAbandon`, and Python as
`scan_run_abandon`. Each takes a continuation and a cancellation and no
decision, and returns the same envelope its `resume` sibling does. The TUI and
the Qt GUI route the choice through this operation, so neither writes the
cancel-then-resume-with-a-placeholder sequence any more. The native CLI no
longer calls it: it settles the pending recovery instead (below). `classic-py-cli` has no
such choice to route: it treats a recovery-required result as terminal and never
resumes.

A binding consumer should prefer it over cancelling and then resuming with a
placeholder decision. The two are equivalent only when cancellation is requested
strictly before the claim; reversing that order spends the one-shot continuation
on a real recovery attempt, which is the failure this operation exists to make
unwritable.

The pending recovery and settling reach every surface too, as one object bundling
the continuation, the rendered prompt, and whether cancellation was already
requested. CXX exposes `ScanRunPendingRecovery` with
`scan_run_contract_execution_has_pending_recovery` /
`scan_run_contract_execution_take_pending_recovery`,
`scan_run_pending_recovery_prompt`,
`scan_run_pending_recovery_cancellation_requested`, and a synchronous
`scan_run_pending_recovery_settle` (no callback crosses the bridge). Node exposes
`JsScanRunSuccess.pendingRecovery` and `scanRunSettle`; Python exposes
`ScanRunExecution.pending_recovery` and `scan_run_settle`. Each binding backs its
legacy continuation and its pending recovery with the same bundle, so the old
resume and abandon surfaces keep working and share the one claim. See
[classic-cpp-bridge-data-entrypoints.md](classic-cpp-bridge-data-entrypoints.md)
and [node-python-contract-map.md](node-python-contract-map.md).

The native CLI (`classic-cli/src/scan_run_cli.cpp`, #281) is the first frontend
on this flow: execute, check for a pending recovery, and when its run is already
cancelled settle with no decision without printing anything; otherwise print the
pending recovery's prompt lines, then settle with the chosen decision, or with no
decision when the user cancels. A non-interactive run reports the paused
envelope unsettled. It no longer calls has-continuation, take-continuation,
resume, or abandon, and its "second recovery request" and "recovery without a
continuation" fatal branches are gone: the settled envelope cannot carry another
recovery. Its `cli.recovery-interaction` consumer obligation records the
decision passed to settling as `settledDecision`.

The observer failure policy and the reported delivery failure reach every
surface (#278). CXX observers return `ScanRunObserverDelivery` from
`on_scan_run_event` instead of throwing, `scan_run_contract_execute` and
`scan_run_pending_recovery_settle` take a `ScanRunObserverFailurePolicy`, and
the execution envelope carries `has_observer_delivery_failure` /
`observer_delivery_failure_message`. Node's `cancelOnObserverError` and
Python's `cancel_on_observer_error` are the policy (`true` is `CancelRun`), and
their `observerError` / `observer_error` is the Rust-reported failure; neither
binding tracks delivery failure itself. The legacy CXX
`scan_run_continuation_resume` takes no policy and continues the run. The
native CLI passes `CLI_SCAN_RUN_OBSERVER_FAILURE_POLICY` (`CancelRun`) to both
execute and settle, its observer only returns the failed delivery, and it warns
about the failure from the envelope's `has_observer_delivery_failure` rather
than from state of its own.

The Focused Semantic Analyzer cutover was deliberately breaking across Rust, CXX, Node,
and Python. Retired report primitives and fragment-producing methods have no
deprecated aliases or forwarding facades; parity includes the six positive
semantic analyzer surfaces and negative absence checks for those retired names.

Cross-interface behavior is pinned by
[`tests/fixtures/crash_log_scan_run/manifest.json`](../../tests/fixtures/crash_log_scan_run/manifest.json).
The binding compliance suite checks the inventory against Rust and requires
each variant to map to a required executable scenario fact or a named retained
analyzer. Blocking semantic and consumer receipts prove executable coverage;
copied adapter acknowledgements and positive source markers are retired.
Negative checks retain the absence of contracted execution exports from source,
declarations, stubs, runtime registries, and parity baselines.

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
        installation_root: PathBuf::from("C:/CLASSIC"),
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
let result = contract::execute(
    request,
    &cancellation,
    None,
    contract::ObserverFailurePolicy::ContinueRun,
)
.await?;
for log in result.logs {
    println!("{}: {:?}", log.crash_log.display(), log.disposition);
}
# Ok(())
# }
```

When a public contract type or variant changes, update the applicable CXX,
Node, and Python projections, generated declarations/stubs, runtime coverage
registries, parity baselines, this page, and the binding compliance manifest in
the same change. Update the source-derived variant evidence policy and affected
executable pack expectations or retained analyzer dispositions as applicable;
do not restore per-adapter acknowledgement or marker lists.
