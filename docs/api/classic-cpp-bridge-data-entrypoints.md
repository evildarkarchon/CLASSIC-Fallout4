# `classic-cpp-bridge` Data Entry Points

Contributor-facing guide to the active data and Crash Log scanning APIs in
[`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge).

The bridge is intentionally narrower than the Rust crates behind it. It maps
typed values and errors into CXX-compatible shapes while keeping business
decisions in Rust.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Ownership By Namespace

| Namespace | Bridge source | Responsibility |
|---|---|---|
| `classic::settings` | `src/settings.rs` | typed User Settings snapshots, migration, preview, and commit operations; generic settings cache helpers |
| `classic::config` | `src/config.rs` | loaded YAML Data access and selected config/cache helpers |
| `classic::files` | `src/files.rs` | generic file, backup, log collection, targeted-resolution, and report-reading helpers |
| `classic::database` | `src/database.rs` | narrowed FormID database pool and lookup operations |
| `classic::scanner` | `src/scanner.rs` | final tagged Crash Log Scan Run contract, small pure scan helpers, and Papyrus inspection |
| `classic::update` | `src/update.rs` | binary compatibility checks, app notifications, and YAML Data update workflows |

No bridge namespace owns a second copy of Rust policy. In particular, C++ does
not own complete-run discovery, adaptive scheduling, FCX state, report
persistence, failed-log movement, or terminal ordering.

---

## `classic::settings`

Typed User Settings entry points open an explicit CLASSIC root and project
Rust-owned snapshots and review artifacts into DTOs. The important workflows
are:

- open typed Update Preferences, Crash Log Scan, Game Setup, and frontend-state
  groups
- plan, reverse, apply, and restore User Settings migrations
- preview ordinary updates or explicit bootstrap updates without writing
- commit an accepted revision-anchored update or report a structured conflict
- import the legacy TUI namespace through a typed, restorable transition

The bridge never interprets raw first-party User Settings key paths. Unknown
content is preserved by the Rust owner, and operational failures retain stable
core error codes in the CXX error message.

Generic settings-cache functions remain separate from first-party User
Settings ownership. They expose selected loaders, cache statistics, and scalar
validators for caller-chosen YAML content.

### Frontend projection into scan requests

Native frontends open one accepted Crash Log Scan settings snapshot and project
it into `ScanRunConfigurationDto`, a Standard or Targeted source DTO, optional
FCX setup context, and the Standard-only Unsolved Logs policy. The adapter does
not reopen settings during execution.

---

## `classic::config`

`yaml_data_load(yaml_dir_root, yaml_dir_data, game, game_version)` loads the
runtime YAML Data model used by focused C++ consumers. Scalar/vector getters
return narrowed values or CXX DTOs rather than exposing the complete Rust
model.

Tooling callers use the separate typed explicit-file flow:

1. `explicit_yaml_data_load(ExplicitYamlDataPathsDto, ExplicitYamlDataGameId, selected_version)` reads exactly the supplied Main, game, and Local Ignore files.
2. `explicit_yaml_data_load_status(...)` returns either a ready state or a typed `ExplicitYamlDataLoadErrorDto` with error kind, optional YAML role, optional path, and message.
3. `explicit_yaml_data_load_take_snapshot(...)` consumes a ready load, after which `explicit_yaml_data_snapshot_game(...)` preserves the requested typed game, the role and identity getters expose the selected role plus exact retained SHA-256 and byte lengths, and `explicit_yaml_data_snapshot_yaml_data(...)` clones the parsed `YamlData` view.

Fallout 4 VR selects the shared Fallout 4 data role. The explicit flow never consults installed cache or bundled candidates and never generates, repairs, backs up, or falls back from a selected file. The existing positional runtime loader is not the contract for this tooling operation.

First-party update tooling uses the separate Installed YAML Data inspection flow:

1. `installed_yaml_data_inspect(installation_root, ExplicitYamlDataGameId)` starts config-owned independent selection for Main and the registered game file, reusing the bridge's shared typed YAML Data game identity.
2. `installed_yaml_data_inspection_status(...)` returns ready state or `InstalledYamlDataInspectionErrorDto`, preserving typed unsupported-game / no-usable-source failures, the failed role, and structured candidate diagnostics.
3. `installed_yaml_data_inspection_take(...)` consumes a ready operation; the inspection getters return requested game, shared game-data role, each selected file's provenance/schema/exact SHA-256 and byte length, and all non-terminal fallback diagnostics.

Inspection is read-only: it does not create the update cache, promote a `.prev` sibling, mutate a rejected candidate, or read or modify Local Ignore YAML Data.

Runtime callers use the Installed YAML Data load flow for valid existing or missing Local Ignore YAML Data:

1. `installed_yaml_data_load(installation_root, ExplicitYamlDataGameId, selected_game_version)` delegates Main/game selection, existing Local Ignore validation, and missing Local Ignore generation to config core.
2. `installed_yaml_data_load_status(...)` reports Ready or `InstalledYamlDataLoadErrorDto`. Its load-specific role is Main or game for `NoUsableSource` and Local Ignore for Local Ignore default-validation, create, read, UTF-8, parse, or role-validation failures; the DTO also preserves the optional path, structured no-usable-source diagnostics, and core message.
3. `installed_yaml_data_load_take_snapshot(...)` consumes Ready. Snapshot getters expose parsed `YamlData`, requested game and registered role, Main/game provenance/schema/exact-byte identity, `LocalIgnoreYamlDataState::{Existing, Generated}` and authoritative Local Ignore identity, plus selection and `LocalIgnoreGenerated` diagnostics.

The adapter owns no source-selection, validation, generation, repair, or fallback policy. Existing Local Ignore bytes are never replaced; the bridge exposes neither raw bytes nor parsed YAML documents.

The namespace also exposes selected cache controls and generic config helpers.
These are data-access APIs; they are not partial Crash Log Scan Run entry
points.

For the YAML schema and directory contract, see
[`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

---

## `classic::files`

The files namespace contains independently useful filesystem operations:

- hash-cache helpers
- backup and game-file group management
- generic encoding-aware reads and writes
- `LogCollector` inspection for callers whose use-case is log enumeration
- targeted-input resolution for non-run review tools
- non-recursive Autoscan Report discovery and report-file reading

These helpers do not provide a direct Autoscan Report writer for scan results.
Autoscan Report path derivation and persistence for a complete run belong to
`classic::scanner::scan_run_contract_execute(...)`.

`resolve_targeted_inputs(...)` is a standalone resolver and flattens rejected
inputs into parallel `rejected_paths` and `rejected_reasons` vectors. The final
scan contract instead returns paired rejection objects in its discovery DTO.
Native scan frontends pass raw Targeted candidates to the tagged request and do
not pre-resolve them with this helper.

`discover_report_files(...)` remains non-recursive, sorts readable matches
newest first, and returns an empty vector for an unreadable or absent directory.

---

## `classic::database`

The database namespace projects a deliberately small subset of
`classic-database-core`:

- create and initialize a pool from explicit paths
- inspect availability and the selected game table
- perform one lookup or a fixed-size batch lookup
- clear cache entries and close the pool
- construct an opaque owned strict FormID Value Lookup from a disabled adapter,
  fully owned in-memory replies, one SQLite path, or an existing shared `DbPool`
- perform strict single and positional batch lookups with explicit typed outcome
  and error envelopes

The legacy `db_pool_get_entry*` and `db_pool_get_entries_batch*` helpers remain
fail-soft for compatibility: they narrow misses and several failures into empty
strings, empty vectors, or `found: false`. The additive
`FormIdValueLookup` handle is the strict path. Its successful outcomes preserve
`Disabled`, `Missing`, and `Found` as separate enum values, while failures carry
`FormIdValueLookupErrorCode::MalformedResult` or
`FormIdValueLookupErrorCode::OperationalFailure` (the CXX projections of the
core `malformed_result` and `operational_failure` codes), a message, and optional
FormID/plugin context.

SQLite constructor failures remain attached to the opaque handle and are read
through `formid_value_lookup_construction_result(...)`; they are not flattened
into CXX exception text. In-memory construction copies all scripted replies into
Rust-owned storage and introduces no callback. Batch requests use owned key DTOs
and return one outcome per input in input order, or one typed whole-batch error
with no partial outcomes. SQLite construction, single lookup, and batch lookup
all block through the process-wide shared Tokio runtime helper; the bridge does
not create another runtime.

The namespace does not expose tuning, rebalance, or detailed statistics.
Complete scan runs receive configured FormID paths through
`ScanRunConfigurationDto`; C++ does not attach a pool to an external scan
orchestrator.

---

## `classic::update`

Native CLI and GUI callers use the first-party YAML Data operations:

- `yaml_data_check_update(enabled)`
- `yaml_data_apply_update(enabled, approved)`
- `yaml_data_rollback_update()`

Rust owns the Pages URL, `yaml-data-v*` channel, shippable-file inventory,
schema compatibility, config-inspected installed identity, and rollback targets. The
bridge passes the accepted update policy and reviewed update identity through
typed DTOs. Lower-level `yaml_check_update`, `yaml_apply_update`, and
`yaml_rollback_update` operations remain for tests and unusual hosts that
intentionally supply their own channel coordinates.

Binary compatibility and app-notification helpers are independent of Crash Log
Scan Runs. See [`yaml-update-delivery.md`](yaml-update-delivery.md) and
[`app-update-notification-delivery.md`](app-update-notification-delivery.md) for
their delivery contracts.

---

## `classic::scanner` Final Crash Log Scan Run

### Focused semantic analyzers

`crashgen_settings_analyzer_new(...)` constructs one immutable analyzer from an
owned configuration DTO. Construction validates the configuration and compiles
matcher state once; callers inspect the construction envelope before sharing
the opaque handle across concurrent calls.

`crashgen_settings_analyze(...)` accepts one aggregate owned input and returns
typed Crashgen expectation outcomes separately from disabled-setting notices.
The bridge preserves the YAML-authored message, fix, severity, kind, and
Autoscan Report placement without rendering report lines. A successful analysis
with no findings is represented by a present result containing two empty
vectors.

Construction and analysis failures use an explicit envelope containing
`AnalyzerErrorDto`. Its `analyzer_kind`, stable `code`, and human-readable
`message` mirror the Rust analyzer contract; no C++ layer reinterprets the
error policy.

`crash_suspect_analyzer_new(...)` follows the same immutable-handle and typed
construction-envelope convention over owned main-error and stack rule DTOs.
`crash_suspect_analyze(...)` accepts owned main-error and call-stack evidence
and returns one `CrashSuspectFindingDto` per matched main-error rule, stack
rule, or DLL involvement notice. Rule ids, names, and severities use explicit
presence flags for the DLL variant; no DTO contains report lines, markdown, or
padding widths. Invalid matcher configuration retains
`AnalyzerKind::CrashSuspect` and the shared stable analyzer error code.

`mod_guidance_analyzer_new(...)` constructs the aggregate Mod Guidance handle
from owned conflict, frequent-crash, solution, and important-mod DTOs. The
construction result reports invalid rules or matcher state before the handle is
used. `mod_guidance_analyze(...)` accepts owned plugin/load-order, optional GPU,
and XSE-module facts and returns typed match state plus authored guidance in
four semantic collections. The DTOs contain no report headings, group order,
icons, separators, markdown, or rendered lines; construction and execution
failures retain `AnalyzerKind::ModGuidance` and the shared stable analyzer error
code.

`plugin_evidence_analyzer_new(...)` validates owned plugin-ignore configuration
and returns the same immutable-handle construction envelope.
`plugin_evidence_analyze(...)` accepts owned call-stack lines and plugin
identities, then returns `PluginEvidenceDto` records containing normalized
identity and occurrence count. A present result with an empty `evidence` vector
means analysis completed without evidence; an absent result is reserved for an
error envelope. No Plugin Evidence DTO contains report prose or markdown, and
failures retain `AnalyzerKind::PluginEvidence` plus the shared stable error code.

`named_record_finding_analyzer_new(...)` validates owned target/ignore patterns,
compiles matcher state, and returns the same immutable-handle construction
envelope. `named_record_finding_analyze(...)` accepts owned Crash Log lines and
returns distinct `NamedRecordFindingDto` values with exact occurrence counts.
A present result with an empty `findings` vector means analysis completed with
no matches. The bridge projects no headings, sorting policy, prose, or markdown;
failures retain `AnalyzerKind::NamedRecordFinding` and the shared stable code.

The `formid_finding_analyzer_*_new(...)` constructors create the aggregate
FormID Finding handle over disabled lookup, owned in-memory replies, or one
SQLite adapter. Construction and analysis run through the process-wide shared
runtime. `formid_finding_analyze(...)` accepts owned Crash Log lines and
plugin/prefix records, then returns canonical identifiers, checked occurrence
counts, explicit plugin/value presence flags, and a typed lookup status.
Unresolved identifiers remain in the result; lookup misses are successful data,
while malformed replies and operational failures use the shared analyzer
envelope. No DTO exposes caches, database internals, matcher inputs, report
prose, or markdown.

### Complete-run entry point

The only public complete-run operation is:

```cpp
scan_run_contract_execute(request, cancellation, observer)
    -> ScanRunContractExecutionResult
```

It forwards to `classic_scanlog_core::scan_run::contract::execute(...)` on the
repository shared Tokio runtime. The bridge has no public orchestration object,
single-log analysis executor, batch lifecycle, prepared-run executor,
resettable scan token, process-global FCX control, or direct report writer.

### Tagged request construction

`ScanRunRequest` and `ScanRunUnsolvedLogs` are opaque Rust-owned values. C++
constructs exactly the valid request matrix:

- `scan_run_request_standard(configuration, source, unsolved_logs)`
- `scan_run_request_standard_with_fcx(configuration, source, unsolved_logs, setup_context)`
- `scan_run_request_targeted(configuration, source)`
- `scan_run_request_targeted_with_fcx(configuration, source, setup_context)`

Targeted constructors accept no movement policy. FCX constructors require a
`ScanRunSetupContextDto`, keeping setup facts scoped to one run.

`ScanRunConfigurationDto` contains YAML roots, game/version, non-FCX analysis
options, configured FormID database paths, an optional configured Unsolved Logs
destination, and optional explicit concurrency. CXX optionals use `has_*` plus
the corresponding value. Absent concurrency selects adaptively; present zero
reaches Rust as a typed `RequestValidation` infrastructure error.

Standard movement uses one opaque value returned by:

- `scan_run_unsolved_logs_leave_in_place()`
- `scan_run_unsolved_logs_move_to_configured_or_default()`
- `scan_run_unsolved_logs_move_to_custom(path)`

### Cancellation

`ScanRunCancellation` is monotonic and opaque:

- `scan_run_cancellation_new()`
- `scan_run_cancellation_cancel(...)`
- `scan_run_cancellation_is_cancelled(...)`

It has no reset. Rust checks it at safe admission seams. Cancellation before
discovery yields no discovery result; after discovery, accepted work remains
known, queued logs do not start, and admitted logs finish durable finalization.

### Observation

Pass `nullptr` for no observer or a live `ScanRunObserver` from
`include/classic_cxx_bridge/scan_run_observer.h`. Calls are serialized in
execution order and cover discovery, effective concurrency, queued, started,
phase, and finished events.

The callback is `noexcept`. An adapter records delivery failure outside the
core result and may request safe cancellation through the same cancellation
object.

See
[`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md)
for the complete event and ordering contract.

### Result and error envelope

Exactly one of `ScanRunContractExecutionResult.has_result` and `has_error` is
true.

The result retains:

- typed lifecycle status
- optional complete discovery and FCX setup results
- optional Rust-selected effective concurrency
- aggregate counts
- per-log outcomes in discovery order

Each log retains its typed disposition, every applicable `Analysis`,
`ReportWrite`, and `UnsolvedLogsFinalization` failure, optional report path,
movement state, timing, and analysis counts.

The error retains one of the six stable infrastructure stages, its message, and
an optional relevant path. Expected no-logs, setup, cancellation, and per-log
failure states remain result data.

Paths use the repository's established lossy UTF-8 CXX string conversion.
Optional output fields use explicit presence flags so absence is not conflated
with an empty string or zero.

---

## Small Scan And Papyrus Utilities

`detect_vr_log(content)` and `detect_crash_pattern(content)` are small pure
inspection helpers. They do not execute a scan or persist a report.

The Papyrus analyzer entry points create an analyzer for an explicit log path,
start monitoring, inspect updates or full statistics, test existence, and reset
the analyzer's own incremental state. Papyrus inspection is independent of the
Crash Log Scan Run lifecycle.

---

## Error And DTO Conventions

The bridge uses four adaptation patterns:

1. opaque Rust values for invariant-preserving requests, controls, and review
   artifacts
2. flattened DTOs with explicit presence flags for optional fields
3. CXX `Result<T>`/`rust::Error` for operational failures where no meaningful
   result can be represented
4. documented fail-soft primitives only on older narrow data helpers where an
   empty string/vector is the established contract

The final scan operation deliberately uses a typed result/error envelope rather
than fail-soft sentinels. See [`error-contract.md`](error-contract.md).

---

## Debugging Checklist

For a complete scan:

1. confirm the frontend built one tagged `ScanRunRequest`
2. inspect `DiscoveryCompleted` for accepted/rejected paths and totals
3. inspect `EffectiveConcurrencySelected` rather than calculating a native
   worker count
4. correlate live events by `discovery_index`
5. inspect terminal logs directly in discovery order
6. use structured setup, per-log failure, and infrastructure stage fields
   instead of parsing messages

For data helpers, debug the owning namespace first. Do not work around a final
scan result by invoking generic file or collector helpers around the execution
call; that would recreate lifecycle policy outside Rust.

---

## Contributor Rule Of Thumb

- Add complete scan behavior to the Rust final contract, then map it exhaustively
  through CXX.
- Keep request construction invariant-preserving and adapters presentation-only.
- Keep independent file, parser, database, and Papyrus utilities independent;
  do not turn them into alternate scan execution paths.
- When the scan contract changes, update exhaustive CXX tests, the CXX parity
  baseline, shared contract manifest, frontend consumers, and these docs in the
  same change.
