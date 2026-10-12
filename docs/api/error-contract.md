# Error Contract Conventions

Documents the C++ bridge error shape conventions for Rust error types as they cross the FFI boundary. These conventions are intentional design choices, not inconsistencies to fix.

Reference: [`AGENTS.md`](../../AGENTS.md).

Need an old-to-new path translation first? Use the shared [`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Scope

The binding surface adapts Rust `Result<T, E>` errors into the idiom expected by its consumers. This document covers the one active surface, the C++ (CXX) bridge: `rust::Error` exceptions and empty-string sentinels. The Python and Node bindings, with their typed exceptions and coded `Error` rejections, retired with ADR-0010 (in [`docs/adr/`](../adr/)).

### Shared focused-analyzer errors

All focused analyzers originate one Rust `AnalyzerError` shape with three
fields: stable `AnalyzerKind`, stable `AnalyzerErrorCode`, and a human-readable
message. `AnalyzerKind::as_str()` and `AnalyzerErrorCode::as_str()` are the only
machine-token source of truth. Crashgen Settings Analysis exposes
`crashgen_settings` with `invalid_configuration` or
`unsupported_configuration_version`; Crash Suspect Analysis exposes
`crash_suspect` with `invalid_configuration` for invalid rule or matcher state;
Mod Guidance Analysis exposes `mod_guidance` with `invalid_configuration` for
  invalid conflict, solution, important-mod, or matcher state; Plugin Evidence
  Analysis exposes `plugin_evidence` with `invalid_configuration` for invalid
  ignore configuration or matcher state; Named Record Finding Analysis exposes
  `named_record_finding` with `invalid_configuration` for invalid target/ignore
  configuration, matcher construction, or checked-count analysis failures;
  FormID Finding Analysis exposes `formid_finding` with
  `invalid_configuration` for invalid owned facts, `malformed_result` for an
  invalid strict-lookup reply, or `operational_failure` for lookup execution.
  A lookup miss is successful result data and never an analyzer error.

- CXX uses an explicit typed construction/analysis envelope so no field is
  flattened into `rust::Error` text.

An explicit empty semantic result is a successful focused analysis, not error
recovery. Direct focused calls return or throw the typed analyzer envelope.
Within `scan_run::contract::execute`, failure to construct the reusable analyzer
set becomes the run-wide `Initialization` infrastructure stage before logs are
scheduled. FormID Value Lookup is the sole collection exception: malformed or
operational lookup failure is retried with lookup disabled so the report keeps
its FormID/plugin suspects without optional descriptions. Every other failure
while collecting one log becomes that log's `Analysis` failure, persists no
partial Autoscan Report, and does not stop other admitted logs from reaching
their own terminal outcomes. See
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

### Strict FormID Value Lookup errors

`classic-database-core::FormIdValueLookupError` keeps a successful miss out of the error channel. Successful lookup data is `disabled`, `missing`, or `found`; failures use stable code `malformed_result` for blank adapter values and `operational_failure` for initialization, absence of the active game table across all initialized databases, SQL execution, or row-decoding problems. Optional FormID/plugin context is absent for failures that occur before a lookup key is available.

- CXX returns a typed lookup envelope whose error DTO retains code, message, and optional key context instead of flattening the failure into `found: false`.

These strict facade rules are additive. The older raw `DatabasePool` binding methods retain their documented fail-soft sentinel behavior for compatibility.

---

## C++ (CXX Bridge)

The complete Crash Log Scan Run entry is intentionally more strongly typed
than the general bridge convention. `scan_run_contract_execute(...)` returns a
Rust-owned execution operation; callers move out its
`ScanRunContractExecutionResult`. Initial execution sets exactly one of
`has_result` and `has_error`. Settling a pending recovery may instead set
`has_resume_error` to consumed-continuation, reset-conflict, reset-backup, or
reset-replacement variants with stable codes and applicable identity/path/stage
metadata. Its `ScanRunContractInfrastructureError` preserves the
stable stage (`RequestValidation`, `Discovery`, `Intake`,
`FormIdDatabaseAccess`, `Initialization`, or `InternalInvariant`), message, and
optional relevant path. Expected lifecycle states and per-log failures stay in
the terminal result and do not throw. This envelope is required because a CXX
`Result<T>` would flatten the typed core infrastructure error into
`rust::Error` text and discard stage/path data.

`scan_run_pending_recovery_settle(...)` (ADR-0009) returns that same envelope
directly rather than an execution operation, and so cannot hand back a second
continuation or pending recovery. A replay, with or without a decision, sets
`has_resume_error` with code `scan_run_continuation_consumed`. Settling with no
decision narrows it to that one case: cancellation short-circuits ahead of every
stage that produces a reset or infrastructure failure. It is the only recovery
entry point; the separate `scan_run_continuation_resume(...)` /
`scan_run_continuation_abandon(...)` were removed (#282).

It is declared `Result<_>` only because it must reject an out-of-range
`ScanRunLocalIgnoreRecoveryDecision` (when `has_decision` is true) or
`ScanRunObserverFailurePolicy` before anything is claimed. On this bridge a CXX
`Result` means "an argument may be unrepresentable", not "the operation may
fail" — operational failure always travels in the typed envelope.
`scan_run_contract_execution_take_pending_recovery(...)` throws when the run did
not pause or the pending recovery was already taken.

**Pattern:** `rust::Error` exceptions for hard failures, empty-string sentinels for fail-soft returns.

**Example 1 -- empty-string sentinel:** `db_pool_get_entry()` in [`cpp-bindings/classic-cpp-bridge/src/database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs) returns `""` on lookup failure because Qt callers check `.isEmpty()` rather than catching exceptions.

**Example 2 -- DTO with `found: false`:** `db_pool_get_entry_typed()` in the same file returns a `FormIdEntryDto` with `found: false` for lookup misses. The DTO has fields `{formid, plugin, value, found}` where `found` is a `bool`. C++ callers check `dto.found` before using `dto.value`.

**Example 3 -- request-construction `rust::Error`:** The invariant-preserving `scan_run_request_*` factories in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) return CXX `Result` errors when required request facts cannot be represented. Once construction succeeds, complete-run infrastructure failures use the typed execution envelope above.

---

## Explicit YAML Data load errors (`typed-mutation-free-explicit-yaml-data`)

`classic_config_core::load_explicit_yaml_data` keeps unsupported games and every file role attributable without message parsing. Its stable core variants are `UnsupportedGame`, `Read`, `InvalidUtf8`, `Parse`, and `InvalidRoleData`. The binding shapes preserve those distinctions according to each language's normal idiom:

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | Not exposed since the consumer-driven bridge trim (#308): no frontend called the explicit loader. |

The bridge delegates role selection, validation, and error classification to Rust. Callers must not respond to an explicit-file failure by silently selecting installed, cached, bundled, or generated data.

---

## Installed YAML Data inspection errors (`unified-installed-yaml-data-inspection`)

`classic_config_core::inspect_installed_yaml_data` returns `UnsupportedGame` before filesystem inspection or `NoUsableSource { role, diagnostics }` after exhausting the allowed candidates for a required role. Non-terminal candidate failures remain structured diagnostics with optional role, provenance, and path plus a typed stable kind. Rust/CXX use enum variants such as `InvalidRoleData`, Node string enums serialize those same PascalCase variant names, and Python projects stable snake-case tokens such as `invalid_role_data`.

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | Not exposed since the consumer-driven bridge trim (#308): no frontend called the inspection flow. |

Rejected candidates are diagnostic evidence only: adapters do not promote, repair, rewrite, or remove them.

### Installed YAML Data loading outcomes and errors

`classic_config_core::load_installed_yaml_data` returns `InstalledYamlDataLoadOutcome::Ready` for a valid installation with existing Local Ignore YAML Data or after atomic generation from strictly validated selected-Main defaults. Existing Local Ignore bytes that are invalid UTF-8, malformed YAML, or invalid for the selected role return `InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired`; this is expected result data, not an error. The retained plan's `proceed_without_ignore()` path returns an operation-scoped empty ignore list without filesystem mutation. Its consuming `reset_to_default()` path returns `LocalIgnoreResetOutcome::Reset` after verified backup and atomic replacement, or typed `Conflict` when current bytes no longer match the plan.

Fatal Rust errors preserve `UnsupportedGame` and `NoUsableSource { role, diagnostics }` as direct typed variants rather than wrapping inspection errors. `LocalIgnoreRead` identifies unrecoverable filesystem access, `LocalIgnoreDefaultInvalid` fails before generation when a missing Local Ignore has unusable selected-Main defaults, `LocalIgnoreCreate` covers staging/sync/no-clobber publication, and `InvalidSelectedData` covers failure to build the final parsed view. Invalid defaults never turn an existing malformed Local Ignore into a fatal result because Proceed Without Ignore does not use them.

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | Not exposed directly since the consumer-driven bridge trim (#308). Native frontends observe Installed YAML Data loading only through the Crash Log Scan Run envelope (`classic::scanner`). |

Reset operational errors are separate from fatal loading errors. Rust `LocalIgnoreResetError` distinguishes unavailable retained defaults, lock/read/backup-directory failures, backup verification, and backup or replacement publication. Publication variants carry `LocalIgnoreResetPublicationStage::{Create, Write, Flush, Sync, Publish}` and occur before canonical replacement, so the malformed original remains authoritative; replacement failures may leave the already verified backup in place. CXX exposes the equivalent reset operation status/error DTO, Node rejects with stable reset metadata, and Python raises dedicated `LocalIgnoreResetError` subclasses. Conflict is expected outcome data on every surface, not an exception. A post-rename Unix directory-sync failure instead becomes `ReplacementDurabilityUnknown` / `replacement_durability_unknown`: defaults are visible, durability is unconfirmed, and every binding receives canonical and verified-backup paths plus malformed, backup, and replacement identities.

---

## `CLASSIC Main.yaml` version-reader errors (`schema-gated startup read`)

The schema-gated `CLASSIC_Info.version` reader (`classic_config_core::load_main_yaml_version`) returns a typed core error (`MainYamlVersionError`). No binding projects it: the CXX `MainYamlVersionDto` entry point was removed in the consumer-driven bridge trim (#308) because no frontend called it, and the native frontends take their version from configure time instead.

Callers MUST NOT fall back to a raw YAML read on any of these errors — that defeats the whole point of the schema gate. Cross-crate background: [`classic-config-core.md`](classic-config-core.md#schema-gated-classic-mainyaml-version-reader).

---

## User Settings commit errors (`conflict-safe-user-settings-commit`)

A stale content revision and a validation rejection are normal commit outcomes rather than operational errors. Operational lock, reopen, parse, serialization, flush, replacement, or cleanup failures retain the stable `classic_user_settings_core::UserSettingsCommitError::code()` token while adapting to each language's hard-error convention.

| Binding | Expected outcome and operational error shape |
| --- | --- |
| C++ (CXX) | `user_settings_commit_update(...) -> Result<UserSettingsCommitResultDto>` returns `committed`, `conflict`, or `rejected`; operational failures throw `rust::Error` whose message begins with the stable core code. |

The CXX request adapter compares the supplied preview revision and revalidates the raw update before delegating to the locked core commit, so it never trusts flattened preview fields as an accepted Rust artifact.

---

## User Settings migration persistence errors (`apply-and-restore-user-settings-migration`)

Stale apply and restore revisions are normal conflict outcomes, not operational errors. Backup creation/reread verification, atomic publication, reopen verification, rollback, receipt-root mismatch, and restore failures retain the stable `classic_user_settings_core::UserSettingsMigrationError::code()` token while adapting to each language's hard-error convention.

| Binding | Expected outcome and operational error shape |
| --- | --- |
| C++ (CXX) | `user_settings_apply_migration(...)` retains an opaque receipt handle and `user_settings_migration_apply_outcome(...)` reports `applied` or `conflict`; `user_settings_restore_migration(...)` reports `restored` or `conflict`. Invalid approvals and operational failures throw `rust::Error` whose message begins with the stable adapter/core code. |

CXX reopens and reproduces the plan from the supplied root, approved base revision, and exact proposed content; caller-owned DTO bytes are never published. A reversed in-memory plan is review data and cannot substitute for the verified receipt required by restore.

---

## Timing sample errors

`classic_shared_core::performance_core::TimingError` rejects a timing or byte record before any metric changes: no operation entry is created and no existing counter moves. Its stable `code()` tokens are `timing_sample_not_finite` (NaN or ±infinity), `timing_sample_negative` (below zero; `-0.0` is accepted as zero), `timing_sample_out_of_range` (above `u64::MAX` nanoseconds), and `timing_counter_overflow` (the operation's sample count, accumulated duration, or byte total would wrap). Every binding treats all four as an invalid argument.

| Binding | Shape on failure |
| --- | --- |
| C++ (CXX) | `classic::perf::perf_record_timing(...)` is declared `Result<()>` and throws `rust::Error` whose message begins with the stable token (`"timing_sample_negative: ..."`). The bridge's other `perf_*` functions remain infallible. |

A dropped timer cannot raise; an overflowing drop record is logged and skipped rather than wrapped. The bridge uses `TimingError::coded_message()`, so the text before the first `": "` is always the token. Branch on the token, not on the rest of the message.

---

## Notification errors (`app-update-manifest-notification`)

The notification check exposes a different-shape-per-binding failure path while sharing a single underlying Rust error family. Variants on `UpdateError` (`NotificationFetchFailed`, `NotificationDecode`, `NotificationInstalledVersionParse`, `NotificationCacheIo`) project onto each binding according to the per-language idiom below. Shared manifest-validation variants (`ManifestInvalid`, `ManifestUnsupportedVersion`) can also surface from this channel when a notification manifest violates cross-field invariants or advertises a newer `manifest_version` major; bindings treat those as notification-channel failures while preserving their existing catch-all shape.

Absence is not part of this failure path. When Pages returns `404 Not Found` and the Releases fallback finds no matching `app-notification-v*` manifest, core returns `Ok(NotificationStatus { classification: NotPublished, latest_version: "", published_at: "", min_supported_version: None, display: None, parse_error: None })` rather than `UpdateError::NotificationFetchFailed`.

| Binding | Shape on failure |
| --- | --- |
| C++ (CXX) | `NotificationStatusDto { classification: "error", error_message: "<Display of UpdateError>", …empty-string sentinels on every other string field… }`. See [`cpp-bindings/classic-cpp-bridge/src/update.rs::notification_error_dto`](../../cpp-bindings/classic-cpp-bridge/src/update.rs). |

For the absent-manifest success case, CXX emits `NotificationStatusDto { classification: "not_published", error_message: "", ... }`.

Full cross-crate flow context: [`app-update-notification-delivery.md`](app-update-notification-delivery.md) §3.

---

## Why The Bridge Uses Sentinels

**C++ uses empty-string sentinels** because Qt callers (`classic-gui/`) are written to check `.isEmpty()` and display "not found" UI. Changing to exceptions would break existing call sites and require rewriting the GUI error handling flow.

The project's Out of Scope section explicitly excluded standardizing these shapes: "Intentional design -- Qt fail-soft callers depend on empty-string sentinel return."

---

## Conversion Helper Reference

### C++

No dedicated error-conversion helper functions. Each bridge function uses `block_on()` with an inline `match` on `Result`. Errors either propagate as `rust::Error` exceptions or return sentinel values.
