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
| `classic::settings` | `src/settings.rs` | typed User Settings snapshots, migration, preview, and commit operations; one read-only YAML string accessor |
| `classic::config` | `src/config.rs` | loaded YAML Data access and selected config/cache helpers |
| `classic::files` | `src/files.rs` | game-target backup, file writing, and Autoscan Report discovery and reading |
| `classic::database` | `src/database.rs` | narrowed FormID database pool and lookup operations |
| `classic::scanner` | `src/scanner.rs` | final tagged Crash Log Scan Run contract, the Crash Log Scan Launch that builds its requests, and Papyrus monitoring |
| `classic::update` | `src/update.rs` | app notifications and first-party YAML Data update workflows |

No bridge namespace owns a second copy of Rust policy. In particular, C++ does
not own complete-run discovery, adaptive scheduling, FCX state, report
persistence, failed-log movement, or terminal ordering.

---

## `classic::settings`

Typed User Settings entry points open an explicit CLASSIC root and project
Rust-owned snapshots and review artifacts into DTOs. The important workflows
are:

- open typed Update Preferences, Crash Log Scan, and Game Setup groups, or every
  GUI-consumed group from one revision-cohesive snapshot
- plan, apply, and restore User Settings migrations
- preview ordinary updates or explicit bootstrap updates without writing
- commit an accepted revision-anchored update or report a structured conflict

The bridge never interprets raw first-party User Settings key paths. Unknown
content is preserved by the Rust owner, and operational failures retain stable
core error codes in the CXX error message.

The `YamlOps` handle (`yaml_ops_new`, `yaml_ops_load_file`, `yaml_ops_get_string`)
reads one string value from a caller-chosen YAML file. The generic settings
cache, YAML setters, validators, the legacy TUI import and in-memory plan
reversal left the bridge with no frontend caller (#309); they remain Rust API.

### Frontend projection into scan requests

Native frontends do not build scan requests from settings themselves: they call
the Crash Log Scan Launch (below), which opens User Settings read-only and
returns an executable request plus a read-only view of what it decided.

---

## `classic::config`

There is **no positional directory-pair loader**. A `YamlData` handle is only
reachable by consuming a snapshot — `installed_yaml_data_snapshot_yaml_data(...)`
for the authoritative runtime path or `explicit_yaml_data_snapshot_yaml_data(...)`
for deterministic caller-selected files — so C++ cannot select Installed YAML
Data outside the Rust-owned policy. Its scalar/vector getters return narrowed
values or CXX DTOs rather than exposing the complete Rust model.

Tooling callers use the typed explicit-file flow:

1. `explicit_yaml_data_load(ExplicitYamlDataPathsDto, ExplicitYamlDataGameId, selected_version)` reads exactly the supplied Main, game, and Local Ignore files.
2. `explicit_yaml_data_load_status(...)` returns either a ready state or a typed `ExplicitYamlDataLoadErrorDto` with error kind, optional YAML role, optional path, and message.
3. `explicit_yaml_data_load_take_snapshot(...)` consumes a ready load, after which `explicit_yaml_data_snapshot_game(...)` preserves the requested typed game, the role and identity getters expose the selected role plus exact retained SHA-256 and byte lengths, and `explicit_yaml_data_snapshot_yaml_data(...)` clones the parsed `YamlData` view.

Fallout 4 VR selects the shared Fallout 4 data role. The explicit flow never consults installed cache or bundled candidates and never generates, repairs, backs up, or falls back from a selected file.

First-party update tooling uses the separate Installed YAML Data inspection flow:

1. `installed_yaml_data_inspect(installation_root, ExplicitYamlDataGameId)` starts config-owned independent selection for Main and the registered game file, reusing the bridge's shared typed YAML Data game identity.
2. `installed_yaml_data_inspection_status(...)` returns ready state or `InstalledYamlDataInspectionErrorDto`, preserving typed unsupported-game / no-usable-source failures, the failed role, and structured candidate diagnostics.
3. `installed_yaml_data_inspection_take(...)` consumes a ready operation; the inspection getters return requested game, shared game-data role, each selected file's provenance/schema/exact SHA-256 and byte length, and all non-terminal fallback diagnostics.

Inspection is read-only: it does not create the update cache, promote a `.prev` sibling, mutate a rejected candidate, or read or modify Local Ignore YAML Data.

Runtime callers use the Installed YAML Data load flow for valid, missing, or malformed Local Ignore YAML Data:

1. `installed_yaml_data_load(installation_root, ExplicitYamlDataGameId, selected_game_version)` delegates Main/game selection, existing Local Ignore validation, and missing Local Ignore generation to config core.
2. `installed_yaml_data_load_status(...)` uses exactly one of `has_snapshot`, `has_recovery_plan`, or `has_error` to report Ready, Local Ignore Recovery Required, or fatal failure. Fatal `InstalledYamlDataLoadErrorDto` roles cover Main/game `NoUsableSource`, Local Ignore read/creation failures, and default validation when a missing Local Ignore must be generated; the DTO also preserves the optional path, structured no-usable-source diagnostics, and core message.
3. `installed_yaml_data_load_take_snapshot(...)` consumes Ready. Snapshot getters expose parsed `YamlData`, simplify-log removal entries retained from selected Main, requested game and registered role, Main/game provenance/schema/exact-byte identity, Local Ignore state/identity, and structured diagnostics.
4. `installed_yaml_data_load_take_recovery_plan(...)` consumes Recovery Required into an opaque Rust-owned `LocalIgnoreRecoveryPlan`. Its getters expose retained Main/game metadata, malformed identity, malformed path, selected-game-version mode, and diagnostics without raw bytes or YAML documents. `local_ignore_recovery_plan_has_default_local_ignore_identity(...)` reports whether selected-Main defaults were usable; callers inspect it before the identity getter because CXX projects an unavailable optional identity as an empty DTO.
5. `local_ignore_recovery_plan_proceed_without_ignore(...)` consumes that plan and returns the retained snapshot with `LocalIgnoreYamlDataState::ProceedWithoutIgnore` and an empty ignore list for this operation. It performs no selection or filesystem operation, so the malformed file remains authoritative and a later load requires recovery again.
6. `local_ignore_recovery_plan_reset_to_default(...)` consumes the plan into a `LocalIgnoreResetOperation`. `local_ignore_reset_status(...)` distinguishes reset, conflict, and typed operational error before consumption. Reset-result getters expose canonical/backup paths, malformed/backup/replacement identities, structured diagnostics, and the retained `ResetToDefault` snapshot; conflict getters expose expected/current identities and an optional already verified backup path. `LocalIgnoreResetErrorDto` retains every core error kind plus optional `Create`, `Write`, `Flush`, `Sync`, or `Publish` stage. The bridge owns none of the conflict, backup, or atomic-replacement policy.

The adapter owns no source-selection, validation, generation, recovery, repair, or fallback policy. Existing Local Ignore bytes are never replaced implicitly; the bridge exposes neither raw bytes nor parsed YAML documents.

Three free functions project the human-facing Display Label for the enums above, so a C++ frontend renders one without writing a `switch`:

- `installed_yaml_data_provenance_label(InstalledYamlDataProvenance) -> String`
- `installed_yaml_data_diagnostic_kind_label(InstalledYamlDataDiagnosticKind) -> String`
- `local_ignore_yaml_data_state_label(LocalIgnoreYamlDataState) -> String`

The label is a separate entry point rather than a DTO field because a Qt view is not line-oriented: it wants the variant and its label in independently styled table columns. `classic-config-core` owns both names under the [Vocabulary naming contract](classic-vocabulary.md), so these labels are identical to the ones the Node and Python surfaces publish.

Labels are presentation only and are reworded freely between releases — branch on the enum, never on the string. Because CXX shared enums are open at the FFI boundary, an out-of-range value returns an empty string rather than an invented label; no value this bridge produces can reach that path.

The namespace also exposes selected cache controls and generic config helpers.
These are data-access APIs; they are not partial Crash Log Scan Run entry
points.

For the YAML schema and directory contract, see
[`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

---

## `classic::files`

The files namespace contains the filesystem operations the GUI calls:

- game-target backup management (`backup_manager_*`, `CxxBackupManager`), which
  delegates to `classic_resource_core::backup`, the owner of the game-target
  backup since #250
- `write_file_string(...)` and the encoding-aware `read_report_file(...)`
- non-recursive Autoscan Report discovery

These helpers do not provide a direct Autoscan Report writer for scan results.
Autoscan Report path derivation and persistence for a complete run belong to
`classic::scanner::scan_run_contract_execute(...)`. Hash-cache controls,
game-file groups, Crash Log collection, targeted-input resolution and file
similarity left the bridge with no frontend caller (#309).

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
schema compatibility, config-inspected installed identity, and rollback targets.
For first-party check/apply calls, Rust also discovers the Installation Root
through config's shared
[`locate_installation_root`](classic-config-core.md#installation-root-location),
the same locator the GUI calls directly as
`classic::config::locate_installation_root(executable_dir, working_dir)`
(empty input = unavailable, empty result = no Installation Root). The bridge passes the accepted update policy
and reviewed update identity through typed DTOs. The lower-level generic
`yaml_*` operations, which took caller-supplied channel coordinates, and the
binary-release `github_*` checks left the bridge with no frontend caller (#309).

The app-notification helper `check_app_notification(...)` is independent of
Crash Log Scan Runs. See [`yaml-update-delivery.md`](yaml-update-delivery.md) and
[`app-update-notification-delivery.md`](app-update-notification-delivery.md) for
their delivery contracts.

---

## `classic::scanner` Final Crash Log Scan Run

The focused semantic analyzers (Crash Suspect, Crashgen Settings, Mod Guidance,
Plugin Evidence, Named Record Finding, FormID Finding) left the bridge with no
frontend caller (#309). A complete run reaches all of them through the Rust
scan pipeline; there is no per-analyzer CXX entry point.

### Complete-run entry point

The only public complete-run flow starts through an opaque operation:

```cpp
auto operation = scan_run_contract_execute(request, cancellation, observer,
                                           ScanRunObserverFailurePolicy::CancelRun);
auto execution = scan_run_contract_execution_take_result(*operation);
```

It forwards to `classic_scanlog_core::scan_run::contract::execute(...)` on the
repository shared Tokio runtime. An expected malformed Local Ignore result
leaves a pending recovery beside the moved result; settling it is the only way
to answer the paused run. The bridge has no public orchestration object,
single-log analysis executor, batch lifecycle, reconstructable prepared-run
executor, resettable scan token, process-global FCX control, or direct report
writer.

The separate `scan_run_continuation_resume(...)` and
`scan_run_continuation_abandon(...)` entry points, the
`scan_run_contract_execution_has_continuation(...)` /
`scan_run_contract_execution_take_continuation(...)` accessors, and the opaque
`ScanRunContinuation` type were removed (#282) with no deprecated aliases. The
Scan Run contract manifest's `forbiddenExports` lists them for the bridge
source, so the gate fails if any reappears.

### Pending recovery and settling (ADR-0009)

A paused run offers its recovery as one **pending recovery**.

```cpp
auto operation = scan_run_contract_execute(request, cancellation, observer, policy);
auto execution = scan_run_contract_execution_take_result(*operation);
if (scan_run_contract_execution_has_pending_recovery(*operation)) {
    auto pending = scan_run_contract_execution_take_pending_recovery(*operation);
    ScanRunLocalIgnoreRecoverySettlement settlement{};  // has_decision = false: abandon
    if (!scan_run_pending_recovery_cancellation_requested(*pending)) {
        auto prompt = scan_run_pending_recovery_prompt(*pending);
        // ...ask the user; set has_decision/decision from the chosen description...
    }
    auto settled = scan_run_pending_recovery_settle(*pending, settlement, observer, policy);
}
```

| Function | Contract |
|---|---|
| `scan_run_contract_execution_has_pending_recovery(execution)` | True exactly when the run paused and the pending recovery has not been taken |
| `scan_run_contract_execution_take_pending_recovery(execution)` | Moves the opaque `ScanRunPendingRecovery` out; throws when the run did not pause or it was already taken |
| `scan_run_pending_recovery_prompt(pending)` | The `ScanRunRecoveryPrompt` Rust rendered for the pause, identical to the envelope's `recovery_prompt`, including Reset To Default availability |
| `scan_run_pending_recovery_cancellation_requested(pending)` | Read live from the control passed to `scan_run_contract_execute`; when true, do not prompt and settle with no decision |
| `scan_run_pending_recovery_settle(pending, settlement, observer, policy)` | Settles once, synchronously, applying the observer failure policy; returns the ordinary `ScanRunContractExecutionResult` |

`ScanRunLocalIgnoreRecoverySettlement { has_decision, decision }` is the
bridge's spelling of an optional Local Ignore Recovery Decision: `decision` is
read only when `has_decision` is true. With a decision, settling resumes the
same discovered Crash Logs without rediscovery, Reset To Default still running
as one non-interruptible transaction. With none, Rust cancels the run's own
control and finishes cancelled after discovery with no filesystem work; that is
abandonment, not a third decision, and it is what a frontend whose user backs
out passes — never cancelling first and then picking a placeholder decision.
No callback crosses the bridge for the decision: the frontend prompts on
whatever thread it already uses and settles afterwards.

The settled envelope is a shared struct, so it cannot carry a continuation or a
pending recovery; `has_recovery_prompt` is always false on it. A second settle,
with or without a decision, arrives as `has_resume_error` with code
`scan_run_continuation_consumed`. Settle throws only for an out-of-range
`decision` while `has_decision` is true, or an out-of-range policy, rejected
before anything is claimed.

### Scan-run Display Labels

Two free functions project the human-facing Display Label for run-contract
enums the GUI labels outside a rendered display line:

- `scan_run_installed_yaml_data_provenance_label(ScanRunInstalledYamlDataProvenance) -> String`
- `scan_run_local_ignore_yaml_data_state_label(ScanRunLocalIgnoreYamlDataState) -> String`

The provenance enum is neither run-owned nor a twin: the run contract reuses
the configuration crate's provenance type outright, and only the *CXX mirror*
is scanner-local, because cxx namespaces its shared enums per bridge module.
The Local Ignore state is a contract-stability twin that delegates its naming
to the configuration enum it mirrors; `RecoveryRequired` is the one variant
the run contract names itself, because a paused run has no configuration
counterpart.

A separate entry point rather than a DTO field lets a Qt view style variant and
label as independent table columns. Labels are presentation only and reworded
freely between releases, so branch on the enum and never on the string; an
out-of-range value returns an empty string rather than an invented label.

`classic-gui/src/workers/scanrunpresentation.cpp` calls both, for the one-row
progress summary that has no room for a rendered line. Every other scan-run
Display Label reaches the frontends inside a `Label` segment of a Rust-rendered
display line, so the other five label entry points left the bridge with their
last frontend caller (#309). Each frontend's
`tests/test_display_label_audit.cpp` enforces the split it actually uses.

### Requests

`ScanRunRequest` is an opaque Rust-owned value. Frontends obtain it only from
the Crash Log Scan Launch below (`scan_run_launch_request`); the bridge exports
no request constructors (#309), so the valid request matrix — Targeted requests
carry no movement policy, FCX requests carry run-scoped setup facts — is
enforced entirely in Rust.

`ScanRunConfigurationDto` (read back through the launch view) contains one
`installation_root`, a typed `GameId`, the selected game-version mode, non-FCX
analysis options, configured FormID database paths, an optional configured
Unsolved Logs destination, and optional explicit concurrency. CXX optionals use
`has_*` plus the corresponding value. Absent concurrency selects adaptively;
present zero reaches Rust as a typed `RequestValidation` infrastructure error.

### Crash Log Scan Launch

Rust builds every request from saved User Settings and per-run overrides
([`classic-scan-launch.md`](classic-scan-launch.md), ADR-0009). Launch opens
User Settings read-only and never writes them; both C++ frontends launch every
Crash Log Scan this way.

- `scan_run_launch_standard(installation_root, overrides)` and
  `scan_run_launch_targeted(installation_root, inputs, overrides)` return an
  opaque `ScanRunLaunch`. They throw only for unrepresentable input: a blank
  root or scan path, an unknown game-version token, or an out-of-range
  `ScanRunGameId`.
- `scan_run_launch_error(launch)` returns `ScanRunLaunchErrorDto`;
  `has_error` is authoritative and `kind` is `TargetedWithoutInputs` or
  `XseLogInspect` (FCX Mode on and the XSE log location could not be
  inspected, not mere absence).
- `scan_run_launch_view(launch)` returns `ScanRunLaunchRequestDto`, which
  reuses `ScanRunConfigurationDto`, `ScanRunStandardSourceDto`,
  `ScanRunTargetedSourceDto` and `ScanRunSetupContextDto` filled with what the
  launch decided, plus `intent`, `unsolved_logs`, `fcx_enabled`,
  `diagnostics` (`ScanRunLaunchDiagnosticDto`: `kind`, `code`, `message`), and
  `display_lines` (`ScanRunDisplayLine`, one per diagnostic in the same order,
  rendered by the scan presentation module). `ScanRunLaunchDiagnosticKind` is
  `UserSettings` or one of the game-differs kinds `GameVersionNotApplied`,
  `FcxModeNotApplied`, `CustomScanFolderNotApplied`, `SetupFoldersNotApplied`,
  whose `code` is the kind's snake_case token.
  Fields that do not apply to the intent are empty placeholders.
- `scan_run_launch_request(launch)` returns an executable `ScanRunRequest`
  copy for `scan_run_contract_execute`.

`ScanRunLaunchOverridesDto` uses `has_*` presence flags. A present
`max_concurrent` of zero requests adaptive concurrency and so overrides a saved
limit, unlike `ScanRunConfigurationDto`, where present zero is a request
validation error. `show_formid_values`, `simplify_logs` and `fcx_mode` are
supplied-as-on. `no_scan_path` supplies "no custom scan folder", withholding a
saved custom scan folder for the run; launching throws when it is combined with
`has_scan_path`. With FCX Mode on, by saved setting or `fcx_mode`, the view's
`setup_context` carries the game folder, documents folder, game executable and
XSE log that Rust resolved; the GUI's own executable normalization and XSE log
lookup are no longer needed once it launches through here.
`view` and `request` throw when the launch failed; check the error first.

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

The callback is `noexcept` and returns a `ScanRunObserverDelivery`: `{}` for
a delivered event, `{true, message}` for a failed one. No exception crosses the
bridge. `scan_run_contract_execute` and `scan_run_pending_recovery_settle` take
a `ScanRunObserverFailurePolicy` — `ContinueRun` or `CancelRun` — that decides
whether Rust cancels the run at the first failed delivery; out-of-range values
throw before anything runs. Under either policy Rust stops delivering to that
observer, and the envelope reports the failure in
`has_observer_delivery_failure` / `observer_delivery_failure_message`, so an
adapter no longer tracks it in its observer. A failure before the run pauses
for Local Ignore recovery makes Rust abandon the recovery: the envelope is
cancelled after discovery, `scan_run_contract_execution_has_pending_recovery`
is false, and nothing on disk changed.

See
[`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md)
for the complete event and ordering contract.

### Result and error envelope

The opaque operation owns one `ScanRunContractExecutionResult`; callers move it
out with `scan_run_contract_execution_take_result(...)`. Exactly one of
`has_result`, `has_error`, and `has_resume_error` is true for a populated
envelope. Initial expected recovery remains result data. Replay of a consumed
continuation and reset conflict/backup/replacement failures or durability
uncertainty set `has_resume_error` with stable kinds and codes; the reset
variants also retain expected/current identities, optional verified backup
path, applicable path/publication stage, or the complete durability recovery
receipt. Failures reached by otherwise valid settled execution
continue to use the typed infrastructure envelope.

The result retains:

- typed lifecycle status
- optional complete discovery and FCX setup results
- optional Installed YAML Data metadata when intake was reached
- optional Rust-selected effective concurrency
- aggregate counts
- per-log outcomes in discovery order

Each log retains its typed disposition, every applicable `Analysis`,
`ReportWrite`, and `UnsolvedLogsFinalization` failure, optional report path,
movement state, timing, and analysis counts.

Installed YAML Data metadata contains the selected Main/game role,
provenance, schema and exact-byte identity; Local Ignore state and identity;
and structured role/candidate/path/kind/message diagnostics. The DTO uses
`has_installed_yaml_data` for intake presence. The bridge maps only Rust-owned
facts; diagnostics never become Autoscan Report text. The run inventory covers
`Existing`, `Generated`, `RecoveryRequired`, `ProceedWithoutIgnore`, and
`ResetToDefault`. A
recovery result retains the malformed identity and structured diagnostic while
its process-local, non-cloneable pending recovery owns prepared intake and the
exact selected snapshot. Settling does not rediscover inputs or reselect YAML
Data. A successful Reset To Default settlement projects the durable backup metadata and
`LocalIgnoreReset` diagnostic. Pre-reset cancellation performs no filesystem
work; cancellation after the reset transaction begins is observed only after
the durable backup and replacement complete and returns normal cancelled result
data without analysis.

The infrastructure error retains one of the six stable stages, its message, and
an optional relevant path. Expected no-logs, setup, Local Ignore recovery,
cancellation, and per-log failure states remain result data.

Paths use the repository's established lossy UTF-8 CXX string conversion.
Optional output fields use explicit presence flags so absence is not conflated
with an empty string or zero.

### Display Content on the envelope

The envelope also carries `display_lines`: what the run *says*, in Rust's words,
for whichever payload the presence flags select. `scan_run_contract_execute`
and `scan_run_pending_recovery_settle` both return this same envelope type, so
one field covers the initial run, a settled run, and an abandoned run alike, and
it is populated for a result, an infrastructure error, and a resume error
equally. An abandoned run is an ordinary
cancelled one, so it describes itself here like any other; a frontend never has
to write the cancellation sentence. A moved-from envelope leaves it empty, as it
does every other field.

Rendering happens on the Rust side while the run value is still live, because
C++ receives a projected copy and cannot render from the Rust value later. The
pending recovery is taken out of the result before the result is rendered; that
ordering is load-bearing, not incidental, since the render entry point borrows.

`display_lines` is human-facing and is not a surface to match on. The typed
fields beside it stay the machine-facing contract — including
`resume_error.code`, which the rendered sentence deliberately omits because a
stable error code is identity rather than prose.

Each `ScanRunDisplayLine` carries a `ScanRunDisplaySeverity` — `Info`, `Notice`,
`Warning`, `Failure`, or `Success` — and an ordered list of segments. Rust names
no colour, no text attribute, and no widget; a frontend maps severity onto its
own styling, or onto nothing.

CXX cannot express a payload-carrying Rust enum, so each `ScanRunDisplaySegment`
crosses flattened as a `ScanRunDisplaySegmentKind` tag plus three payload fields,
with the fields the kind does not use left empty:

| `kind` | `text` | `path` | `count` |
|---|---|---|---|
| `Text` | fixed Rust-owned prose | empty | 0 |
| `Label` | a Display Label | empty | 0 |
| `Count` | the noun, already agreeing with `count` | empty | the value |
| `Path` | empty | the path, whole | 0 |
| `Name` | a domain entity name | empty | 0 |
| `Emphasis` | a value set apart from the prose | empty | 0 |

The taxonomy is fixed at six kinds for its first version, because each addition
touches this DTO and every frontend renderer.

A consuming frontend concatenates a line's segments in order and never reorders
within a line. It may reorder, group, or omit whole lines. It must not call a
`scan_run_*_label` entry point for anything already carried in a `Label` segment,
and must not re-decide a `Count`'s noun — print `count`, then `text`. The seven
label entry points remain correct for labelling a domain enum *outside* a display
line.

`classic-cli` consumes these today. See
[`classic-scan-presentation.md`](classic-scan-presentation.md) for the Rust
owner of this content.

### The Local Ignore recovery prompt on the envelope

`has_recovery_prompt` and `recovery_prompt` carry what to ask a user whose Local
Ignore is malformed, and which answers this run can honor. The flag is true only
when `result.status` is `LocalIgnoreRecoveryRequired`, which is also exactly when
the execution offers a pending recovery — so a run with nothing to ask
carries no prompt rather than an empty one. It follows the presence-flag
convention `has_local_ignore_reset` already uses, because CXX has no optional
struct.

`ScanRunRecoveryPrompt` is two vectors:

| Field | Contents |
|---|---|
| `lines` | Why the run paused and what is being decided about, as ordinary `ScanRunDisplayLine`s |
| `decisions` | One `ScanRunRecoveryDecisionDescription` per decision the continuation contract accepts |

Each `ScanRunRecoveryDecisionDescription` carries the
`ScanRunLocalIgnoreRecoveryDecision` to hand back to
`scan_run_pending_recovery_settle`, its Display Label, a `description` flattened
exactly as any other segment list, and `available`.

**A frontend must not offer a decision whose `available` is false.** The fact
travels on the decision rather than beside the prompt precisely so honouring it
takes no separate lookup — the shape that closed a confirmed gap, where
`local_ignore_reset_available` sat on the Installed YAML Data DTO and neither C++
frontend read it. Rust still fails safely and touches nothing on disk if one is
offered anyway, but the attempt spends the one-shot continuation, so the user is
left with no scan, no repair, and no second attempt.

Proceed Without Ignore is never unavailable; it needs nothing from the
installation. Only Reset To Default can be withdrawn.

Backing out appears nowhere in `decisions`.
`ScanRunLocalIgnoreRecoveryDecision` has exactly two variants by design, and
abandonment is spelled as the absence of a decision when settling through
`scan_run_pending_recovery_settle`. The affordance beside a description — a
bracketed letter, a key hint, a button — is the frontend's, as is the order it
presents them in. The description itself is not.

---

## Papyrus Monitoring

The Papyrus analyzer entry points create an analyzer for an explicit log path,
start monitoring, poll for updated statistics, and test existence. Papyrus
inspection is independent of the Crash Log Scan Run lifecycle. The pure
crash-log helpers (`detect_vr_log`, `detect_crash_pattern`,
`classify_crash_pattern`) and the Papyrus full-analysis and reset entry points
left the bridge with no frontend caller (#309).

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
