# Error Contract Conventions

Documents the per-binding error shape conventions for Rust error types as they cross FFI boundaries. These conventions are intentional design choices, not inconsistencies to fix.

Reference: [`AGENTS.md`](../../AGENTS.md).

Need an old-to-new path translation first? Use the shared [`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Scope

Each binding surface adapts Rust `Result<T, E>` errors into the idiom expected by its consumers. This document covers the three active surfaces:

- C++ (CXX bridge) -- `rust::Error` exceptions and empty-string sentinels
- Node (NAPI-RS) -- `napi::Error` with structured `code` fields
- Python (PyO3) -- typed Python exception classes

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
- Node throws `napi::Error` with `error.analyzerKind`, `error.code`, and
  `error.message` set to the exact stable Rust analyzer kind, code, and message.
- Python raises `classic_scanlog.AnalyzerError` with `analyzer_kind`, `code`,
  and `message` attributes.

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
- Node rejects with `napi::Error` carrying `code`, `formid`, `plugin`, and `message` properties.
- Python raises `classic_database.FormIdValueLookupError` with the same four attributes.

These strict facade rules are additive. The older raw `DatabasePool` binding methods retain their documented fail-soft sentinel behavior for compatibility.

---

## C++ (CXX Bridge)

The complete Crash Log Scan Run entry is intentionally more strongly typed
than the general bridge convention. `scan_run_contract_execute(...)` returns a
Rust-owned execution operation; callers move out its
`ScanRunContractExecutionResult`. Initial execution sets exactly one of
`has_result` and `has_error`. Recovery resume may instead set
`has_resume_error` to consumed-continuation, reset-conflict, reset-backup, or
reset-replacement variants with stable codes and applicable identity/path/stage
metadata. Its `ScanRunContractInfrastructureError` preserves the
stable stage (`RequestValidation`, `Discovery`, `Intake`,
`FormIdDatabaseAccess`, `Initialization`, or `InternalInvariant`), message, and
optional relevant path. Expected lifecycle states and per-log failures stay in
the terminal result and do not throw. This envelope is required because a CXX
`Result<T>` would flatten the typed core infrastructure error into
`rust::Error` text and discard stage/path data.

**Pattern:** `rust::Error` exceptions for hard failures, empty-string sentinels for fail-soft returns.

**Example 1 -- empty-string sentinel:** `db_pool_get_entry()` in [`cpp-bindings/classic-cpp-bridge/src/database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs) returns `""` on lookup failure because Qt callers check `.isEmpty()` rather than catching exceptions.

**Example 2 -- DTO with `found: false`:** `db_pool_get_entry_typed()` in the same file returns a `FormIdEntryDto` with `found: false` for lookup misses. The DTO has fields `{formid, plugin, value, found}` where `found` is a `bool`. C++ callers check `dto.found` before using `dto.value`.

**Example 3 -- request-construction `rust::Error`:** The invariant-preserving `scan_run_request_*` factories in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) return CXX `Result` errors when required request facts cannot be represented. Once construction succeeds, complete-run infrastructure failures use the typed execution envelope above.

---

## Node (NAPI-RS)

**Pattern:** `napi::Error` with a `code` field matching the Rust error variant name (e.g., `"InvalidArg"`, `"ParseError"`).

Node Crash Log Scan Run execution follows the same typed-envelope rationale as CXX. `scanRunExecute(...)` and successful `scanRunResume(...)` resolve the generated `JsScanRunSuccess | JsScanRunFailure` union, so `result` and `error` are mutually exclusive by construction; `JsScanRunInfrastructureError` retains the stable lowercase stage, message, and optional path. Expected lifecycle states and per-log failures remain result data. Consuming a continuation more than once rejects with an `Error` whose `code` is `scan_run_continuation_consumed`; Reset To Default conflict/backup/replacement failures reject with their stable reset code plus applicable identities, backup path, affected path, and publication stage. These are not infrastructure failures. JavaScript observer throws or delivery failures are reported separately as `observerError`, with optional safe cancellation controlled by the caller. No analysis-only, batch, report-writer, or global-FCX export is an alternative error channel.

**Example 1:** `config_error_to_napi_err()` in [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs) converts `ConfigError` variants to NAPI errors with structured codes. JavaScript consumers use `catch (e) { if (e.code === "ParseError") ... }`.

**Example 2:** `settings_error_to_napi_err()` in the same file converts `SettingsError` variants with codes like `"NotFound"`, `"YamlError"`, etc.

**Example 3:** `runtime_to_napi_err()` handles `anyhow::Error` wrapping with automatic downcast to typed errors.

Tests verify both `error.message` and `error.code` to ensure the structured error contract holds.

---

## Python (PyO3)

**Pattern:** Typed Python exception classes (e.g., `RustConfigParseError`, `RustConfigIOError`) with message inspection.

Python Crash Log Scan Run execution is the deliberate structured-operation exception to that general rule. `classic_scanlog.scan_run_execute(...)` and successful `scan_run_resume(...)` return `ScanRunExecution`, where exactly one of `result` and `error` is populated. `ScanRunInfrastructureError` preserves the six stable lifecycle stages, message, and optional relevant path; expected lifecycle outcomes and per-log failures remain result data. Continuation replay raises `ScanRunContinuationConsumedError`; Reset To Default conflict, backup, and replacement failures raise dedicated `ScanRunLocalIgnoreReset*Error` subclasses. Every exception exposes a stable lowercase code and the reset subclasses preserve applicable identity/path/stage metadata; all remain distinct from infrastructure failure. A Python observer exception is reported independently through `observer_error` and requests safe cancellation only when the caller opts into `cancel_on_observer_error`. Python exposes no orchestration, resettable batch cancellation, report-writer, or global-FCX compatibility error path.

**Example 1:** `config_error_to_pyerr()` in [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs) maps each `ConfigError` variant to a specific Python exception class.

**Example 2:** [`foundation/classic-shared-py/src/lib.rs`](../../foundation/classic-shared-py/src/lib.rs) provides `define_exceptions!` and `register_exceptions!` macros plus the `ToPyErr` trait and `ResultExt` extension for consistent exception wiring across all Python binding crates.

**Example 3:** Tests use `pytest.raises(RustConfigParseError)` with message inspection to verify both the exception type and the error context.

---

## Explicit YAML Data load errors (`typed-mutation-free-explicit-yaml-data`)

`classic_config_core::load_explicit_yaml_data` keeps unsupported games and every file role attributable without message parsing. Its stable core variants are `UnsupportedGame`, `Read`, `InvalidUtf8`, `Parse`, and `InvalidRoleData`. The binding shapes preserve those distinctions according to each language's normal idiom:

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | `explicit_yaml_data_load_status()` returns `ExplicitYamlDataLoadErrorDto { kind, has_role, role, has_path, path, message }`. Callers inspect the status before consuming a ready load with `explicit_yaml_data_load_take_snapshot()`; expected load failures are not flattened into `rust::Error`. |
| Node (NAPI-RS) | `loadExplicitYamlData(...)` rejects with an `Error` whose stable lowercase `code` is `unsupported_game`, `read`, `invalid_utf8`, `parse`, or `invalid_role_data`. File-specific failures also carry `yamlRole` (`main`, `game`, or `local_ignore`) and `path`. |
| Python (PyO3) | `classic_config.load_explicit_yaml_data(...)` raises a subclass of `ExplicitYamlDataLoadError`: `ExplicitYamlDataUnsupportedGameError`, `ExplicitYamlDataReadError`, `ExplicitYamlDataInvalidUtf8Error`, `ExplicitYamlDataParseError`, or `ExplicitYamlDataInvalidRoleDataError`. Every instance exposes the matching lowercase `code`; file-specific failures also expose `yaml_role` and `path`, while non-file failures set them to `None`. |

All three surfaces delegate role selection, validation, and error classification to Rust. Callers must not respond to an explicit-file failure by silently selecting installed, cached, bundled, or generated data.

---

## Installed YAML Data inspection errors (`unified-installed-yaml-data-inspection`)

`classic_config_core::inspect_installed_yaml_data` returns `UnsupportedGame` before filesystem inspection or `NoUsableSource { role, diagnostics }` after exhausting the allowed candidates for a required role. Non-terminal candidate failures remain structured diagnostics with optional role, provenance, and path plus a typed stable kind. Rust/CXX use enum variants such as `InvalidRoleData`, Node string enums serialize those same PascalCase variant names, and Python projects stable snake-case tokens such as `invalid_role_data`.

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | `installed_yaml_data_inspection_status()` returns `InstalledYamlDataInspectionErrorDto` with a typed error kind, optional failed role, message, and diagnostic DTOs. Expected selection failures are consumed through status/take rather than flattened into `rust::Error`. |
| Node (NAPI-RS) | `inspectInstalledYamlData(...)` rejects with an `Error` whose `code` is `unsupported_game` or `no_usable_source`; the latter also carries `yamlRole` and structured `diagnostics`. |
| Python (PyO3) | `classic_config.inspect_installed_yaml_data(...)` raises `InstalledYamlDataUnsupportedGameError` or `InstalledYamlDataNoUsableSourceError` under `InstalledYamlDataInspectionError`. Instances expose `code`, optional `yaml_role`, and structured `diagnostics`. |

Rejected candidates are diagnostic evidence only: adapters do not promote, repair, rewrite, or remove them.

### Installed YAML Data loading outcomes and errors

`classic_config_core::load_installed_yaml_data` returns `InstalledYamlDataLoadOutcome::Ready` for a valid installation with existing Local Ignore YAML Data or after atomic generation from strictly validated selected-Main defaults. Existing Local Ignore bytes that are invalid UTF-8, malformed YAML, or invalid for the selected role return `InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired`; this is expected result data, not an error. The retained plan's `proceed_without_ignore()` path returns an operation-scoped empty ignore list without filesystem mutation. Its consuming `reset_to_default()` path returns `LocalIgnoreResetOutcome::Reset` after verified backup and atomic replacement, or typed `Conflict` when current bytes no longer match the plan.

Fatal Rust errors preserve `UnsupportedGame` and `NoUsableSource { role, diagnostics }` as direct typed variants rather than wrapping inspection errors. `LocalIgnoreRead` identifies unrecoverable filesystem access, `LocalIgnoreDefaultInvalid` fails before generation when a missing Local Ignore has unusable selected-Main defaults, `LocalIgnoreCreate` covers staging/sync/no-clobber publication, and `InvalidSelectedData` covers failure to build the final parsed view. Invalid defaults never turn an existing malformed Local Ignore into a fatal result because Proceed Without Ignore does not use them.

| Binding | Failure shape |
| --- | --- |
| C++ (CXX) | `installed_yaml_data_load_status()` distinguishes Ready, Local Ignore Recovery Required, and fatal error before the operation is consumed. Fatal `InstalledYamlDataLoadErrorDto` values retain an exhaustive kind, optional load-specific Main/game/Local Ignore role, optional path, no-usable-source diagnostics, and message. |
| Node (NAPI-RS) | `loadInstalledYamlData(...)` resolves malformed content as a typed recovery-required outcome. Fatal rejections use `unsupported_game`, `no_usable_source`, `local_ignore_read`, `local_ignore_default_invalid`, `local_ignore_create`, or `invalid_selected_data`, plus applicable `yamlRole`, `path`, and `diagnostics`. |
| Python (PyO3) | `classic_config.load_installed_yaml_data(...)` returns a typed recovery-required outcome for malformed content. Fatal failures raise the matching dedicated `InstalledYamlDataLoadError` subclass; every instance exposes the same lowercase `code` and applicable `yaml_role`, `path`, and `diagnostics` attributes. |

Reset operational errors are separate from fatal loading errors. Rust `LocalIgnoreResetError` distinguishes unavailable retained defaults, lock/read/backup-directory failures, backup verification, and backup or replacement publication. Publication variants carry `LocalIgnoreResetPublicationStage::{Create, Write, Flush, Sync, Publish}`. CXX exposes the equivalent reset operation status/error DTO, Node rejects with stable reset `code`, `path`, and `stage` properties, and Python raises dedicated `LocalIgnoreResetError` subclasses with the same metadata. Conflict is expected outcome data on every surface, not an exception. Every operational error occurs before canonical replacement, so the malformed original remains authoritative; replacement failures may leave the already verified backup in place.

---

## `CLASSIC Main.yaml` version-reader errors (`schema-gated startup read`)

The schema-gated `CLASSIC_Info.version` reader (`classic_config_core::load_main_yaml_version`) is the native-frontend startup path that replaced the raw `yaml_ops` read in `classic-gui/src/main.cpp`. Its typed core error (`MainYamlVersionError`) projects onto each binding according to the per-language idiom below. Same-family, different-shape-per-binding, just like the notification channel.

| Binding | Shape on failure |
| --- | --- |
| C++ (CXX) | `MainYamlVersionDto { version: "", error_kind: "<kind>", error_message: "<Display of MainYamlVersionError>" }`. Empty-string sentinel on the `version` field when `error_kind` is non-empty. `error_kind` values: `"load"` (schema-incompatible or file missing / unparseable), `"version_key_missing"`, `"version_empty"`, `"version_not_string"`, `"version_invalid"` (schema-2.0 shape violation: legacy `CLASSIC ` prefix, prerelease/build suffix, or non-semver garbage), or `"unknown"` (reserved for future `#[non_exhaustive]` variants). See [`cpp-bindings/classic-cpp-bridge/src/config.rs::main_yaml_version_error_kind`](../../cpp-bindings/classic-cpp-bridge/src/config.rs). |
| Node (NAPI-RS) | `Promise.reject(new Error(...))` whose `message` is prefixed with one of `"LOAD: "`, `"VERSION_KEY_MISSING: "`, `"VERSION_EMPTY: "`, `"VERSION_NOT_STRING: "`, `"VERSION_INVALID: "`, or `"UNKNOWN: "`. **Shape matches the notification channel**: the `#[napi] async fn` surface threads `napi::Error<Status>`, where `Status` is a fixed C-style enum with no room for per-variant codes — the message prefix is the only representation that round-trips through the async bridge while preserving a stable discriminator. See [`node-bindings/classic-node/src/config.rs::main_yaml_version_error_to_napi`](../../node-bindings/classic-node/src/config.rs). |
| Python (PyO3) | Raises a `ClassicMainYamlVersionError` subclass whose name encodes the variant (`ClassicMainYamlVersionLoadError`, `ClassicMainYamlVersionKeyMissingError`, `ClassicMainYamlVersionEmptyError`, `ClassicMainYamlVersionNotStringError`, `ClassicMainYamlVersionInvalidError`). Consumers that want to catch any failure use `except ClassicMainYamlVersionError`. See [`python-bindings/classic-config-py/src/main_yaml_version.rs`](../../python-bindings/classic-config-py/src/main_yaml_version.rs). |

Callers MUST NOT fall back to a raw YAML read on any of these errors — that defeats the whole point of the schema gate. Cross-crate background: [`classic-config-core.md`](classic-config-core.md#schema-gated-classic-mainyaml-version-reader).

---

## User Settings commit errors (`conflict-safe-user-settings-commit`)

A stale content revision and a validation rejection are normal commit outcomes rather than operational errors. Operational lock, reopen, parse, serialization, flush, replacement, or cleanup failures retain the stable `classic_user_settings_core::UserSettingsCommitError::code()` token while adapting to each language's hard-error convention.

| Binding | Expected outcome and operational error shape |
| --- | --- |
| C++ (CXX) | `user_settings_commit_update(...) -> Result<UserSettingsCommitResultDto>` returns `committed`, `conflict`, or `rejected`; operational failures throw `rust::Error` whose message begins with the stable core code. |
| Node (NAPI-RS) | `commitUserSettingsUpdate(...)` returns `committed`, `conflict`, or `rejected`; operational failures reject with `napi::Error` whose `code` is the stable core code and whose message carries context. |
| Python (PyO3) | An accepted `UserSettingsUpdatePreview.commit(...)` returns `UserSettingsCommitOutcome` (`committed` or `conflict`); operational failures raise the typed `classic_user_settings.UserSettingsCommitError`, with the stable code prefixed in its message. Calling `commit` on a rejected preview raises `ValueError` before filesystem work. |

The CXX and Node request adapters compare the supplied preview revision and revalidate the raw update before delegating to the locked core commit, so they never trust flattened preview fields as an accepted Rust artifact. Python retains its exact core `AcceptedUserSettingsUpdate` inside the preview wrapper and calls it directly.

---

## User Settings migration persistence errors (`apply-and-restore-user-settings-migration`)

Stale apply and restore revisions are normal conflict outcomes, not operational errors. Backup creation/reread verification, atomic publication, reopen verification, rollback, receipt-root mismatch, and restore failures retain the stable `classic_user_settings_core::UserSettingsMigrationError::code()` token while adapting to each language's hard-error convention.

| Binding | Expected outcome and operational error shape |
| --- | --- |
| C++ (CXX) | `user_settings_apply_migration(...)` retains an opaque receipt handle and `user_settings_migration_apply_outcome(...)` reports `applied` or `conflict`; `user_settings_restore_migration(...)` reports `restored` or `conflict`. Invalid approvals and operational failures throw `rust::Error` whose message begins with the stable adapter/core code. |
| Node (NAPI-RS) | `applyUserSettingsMigration(...)` and `JsUserSettingsMigrationReceipt.restore(...)` return conflict data. Mutated approvals reject with `error.code == "migration_plan_approval_mismatch"`; malformed review DTO tokens reject with `error.code == "migration_plan_review_invalid"`; core operational failures reject with `error.code` set to the stable migration code. |
| Python (PyO3) | `UserSettingsMigrationPlan.apply(...)` and `UserSettingsMigrationReceipt.restore(...)` return applied/restored or conflict outcomes. Operational failures raise the typed `classic_user_settings.UserSettingsMigrationError`, with the stable code prefixed in its message. |

CXX and Node reopen and reproduce the plan from the supplied root, approved base revision, and exact proposed content; caller-owned DTO bytes are never published. Python retains the immutable core plan and receipt directly. A reversed in-memory plan is review data and cannot substitute for the verified receipt required by restore.

---

## Notification errors (`app-update-manifest-notification`)

The notification check exposes a different-shape-per-binding failure path while sharing a single underlying Rust error family. Variants on `UpdateError` (`NotificationFetchFailed`, `NotificationDecode`, `NotificationInstalledVersionParse`, `NotificationCacheIo`) project onto each binding according to the per-language idiom below. Shared manifest-validation variants (`ManifestInvalid`, `ManifestUnsupportedVersion`) can also surface from this channel when a notification manifest violates cross-field invariants or advertises a newer `manifest_version` major; bindings treat those as notification-channel failures while preserving their existing catch-all shape.

Absence is not part of this failure path. When Pages returns `404 Not Found` and the Releases fallback finds no matching `app-notification-v*` manifest, core returns `Ok(NotificationStatus { classification: NotPublished, latest_version: "", published_at: "", min_supported_version: None, display: None, parse_error: None })` rather than `UpdateError::NotificationFetchFailed`.

| Binding | Shape on failure |
| --- | --- |
| C++ (CXX) | `NotificationStatusDto { classification: "error", error_message: "<Display of UpdateError>", …empty-string sentinels on every other string field… }`. See [`cpp-bindings/classic-cpp-bridge/src/update.rs::notification_error_dto`](../../cpp-bindings/classic-cpp-bridge/src/update.rs). |
| Node (NAPI-RS) | `Promise.reject(new Error(...))` whose `message` is prefixed with one of `"FETCH_FAILED: "`, `"DECODE: "`, `"INSTALLED_VERSION_PARSE: "`, `"CACHE_IO: "`, or `"UPDATE_ERROR: "` (catch-all). Consumers discriminate with `err.message.startsWith("FETCH_FAILED:")`. **Shape divergence from the general Node-binding rule is intentional**: the `#[napi] async fn` surface threads `napi::Error<Status>` through `execute_tokio_future_with_finalize_callback`, and `Status` is a fixed C-style enum with no room for custom per-variant codes. A message prefix is the only representation that round-trips through the async bridge while preserving the variant-keyed discriminator the spec promises. See [`node-bindings/classic-node/src/update.rs::notification_error_to_napi`](../../node-bindings/classic-node/src/update.rs) and the matching JSDoc in [`node-bindings/classic-node/index.d.ts`](../../node-bindings/classic-node/index.d.ts). |
| Python (PyO3) | Raises a `ClassicNotificationError` subclass whose name encodes the variant (e.g. `ClassicNotificationFetchFailed`), or the `ClassicNotificationError` base for shared notification-channel failures such as `ManifestInvalid` and `ManifestUnsupportedVersion`. Subclass of `ClassicUpdateError` so existing catch blocks keep working. |

For the absent-manifest success case, CXX emits `NotificationStatusDto { classification: "not_published", error_message: "", ... }`; Node resolves with `classification: "notPublished"`; Python returns `NotificationStatus.classification == "notPublished"`.

Full cross-crate flow context: [`app-update-notification-delivery.md`](app-update-notification-delivery.md) §3.

---

## Why They Differ

The three binding surfaces intentionally use different error shapes because each consumer ecosystem has established idioms:

- **C++ uses empty-string sentinels** because Qt callers (`classic-gui/`) are written to check `.isEmpty()` and display "not found" UI. Changing to exceptions would break existing call sites and require rewriting the GUI error handling flow.

- **Node uses `error.code` strings** because the Node ecosystem convention is `catch (e) { if (e.code === "ParseError") ... }`. This is idiomatic for JS/TS consumers and integrates naturally with error-handling middleware.

- **Python uses typed exception classes** because the Python ecosystem convention is `except RustConfigParseError as e:` with `isinstance` checks. This is idiomatic for Python consumers and enables fine-grained exception handling.

The project's Out of Scope section explicitly excluded standardizing these shapes: "Intentional design -- Qt fail-soft callers depend on empty-string sentinel return."

---

## Conversion Helper Reference

### C++

No dedicated error-conversion helper functions. Each bridge function uses `block_on()` with an inline `match` on `Result`. Errors either propagate as `rust::Error` exceptions or return sentinel values.

### Node

- `config_error_to_napi_err()` -- converts `ConfigError` variants to `napi::Error` with structured codes
- `settings_error_to_napi_err()` -- converts `SettingsError` variants
- `runtime_to_napi_err()` -- wraps `anyhow::Error` with automatic downcast

Source: [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs)

### Python

- `define_exceptions!` -- creates the standard 3-tier exception hierarchy per module
- `register_exceptions!` -- registers exception classes in a Python module
- `ToPyErr` trait -- standard interface for error-to-`PyErr` conversion
- `ResultExt` -- extension trait for converting `Result<T, E>` to `PyResult<T>`
- `without_gil` -- GIL release helper for blocking operations

Source: [`foundation/classic-shared-py/src/lib.rs`](../../foundation/classic-shared-py/src/lib.rs)

Per-module converters like `config_error_to_pyerr()` live alongside each binding crate: [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs)
