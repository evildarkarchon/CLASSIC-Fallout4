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

---

## C++ (CXX Bridge)

The final Crash Log Scan Run entry point is intentionally more strongly typed
than the older general bridge convention. `scan_run_contract_execute(...)`
returns `ScanRunContractExecutionResult`, where exactly one of `has_result` and
`has_error` is true. Its `ScanRunContractInfrastructureError` preserves the
stable stage (`RequestValidation`, `Discovery`, `Intake`,
`FormIdDatabaseAccess`, `Initialization`, or `InternalInvariant`), message, and
optional relevant path. Expected lifecycle states and per-log failures stay in
the terminal result and do not throw. This envelope is required because a CXX
`Result<T>` would flatten the typed core infrastructure error into
`rust::Error` text and discard stage/path data.

**Pattern:** `rust::Error` exceptions for hard failures, empty-string sentinels for fail-soft returns.

**Example 1 -- empty-string sentinel:** `db_pool_get_entry()` in [`cpp-bindings/classic-cpp-bridge/src/database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs) returns `""` on lookup failure because Qt callers check `.isEmpty()` rather than catching exceptions.

**Example 2 -- DTO with `found: false`:** `db_pool_get_entry_typed()` in the same file returns a `FormIdEntryDto` with `found: false` for lookup misses. The DTO has fields `{formid, plugin, value, found}` where `found` is a `bool`. C++ callers check `dto.found` before using `dto.value`.

**Example 3 -- propagated `rust::Error`:** Functions like `orchestrator_process_log()` in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) propagate `rust::Error` for infrastructure failures (runtime not initialized, config not loaded). The scan entry points are `orchestrator_process_log`, `orchestrator_process_logs_batch`, and `orchestrator_process_logs_batch_with_progress`.

---

## Node (NAPI-RS)

**Pattern:** `napi::Error` with a `code` field matching the Rust error variant name (e.g., `"InvalidArg"`, `"ParseError"`).

The final Crash Log Scan Run follows the same typed-envelope rationale as CXX. `scanRunExecute(...)` resolves the generated `JsScanRunSuccess | JsScanRunFailure` union, so `result` and `error` are mutually exclusive by construction; `JsScanRunInfrastructureError` retains the stable lowercase stage, message, and optional path. Expected lifecycle states and per-log failures remain result data. JavaScript observer throws or delivery failures are not core failures; they appear separately as `observerError`, with optional safe cancellation controlled by the caller.

**Example 1:** `config_error_to_napi_err()` in [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs) converts `ConfigError` variants to NAPI errors with structured codes. JavaScript consumers use `catch (e) { if (e.code === "ParseError") ... }`.

**Example 2:** `settings_error_to_napi_err()` in the same file converts `SettingsError` variants with codes like `"NotFound"`, `"YamlError"`, etc.

**Example 3:** `runtime_to_napi_err()` handles `anyhow::Error` wrapping with automatic downcast to typed errors.

Tests verify both `error.message` and `error.code` to ensure the structured error contract holds.

---

## Python (PyO3)

**Pattern:** Typed Python exception classes (e.g., `RustConfigParseError`, `RustConfigIOError`) with message inspection.

The final Crash Log Scan Run is the deliberate structured-operation exception to that general rule. `classic_scanlog.scan_run_execute(...)` returns `ScanRunExecution`, where exactly one of `result` and `error` is populated. `ScanRunInfrastructureError` preserves the six stable lifecycle stages, message, and optional relevant path; expected lifecycle outcomes and per-log failures remain result data. A Python observer exception is reported independently through `observer_error` and requests safe cancellation only when the caller opts into `cancel_on_observer_error`.

**Example 1:** `config_error_to_pyerr()` in [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs) maps each `ConfigError` variant to a specific Python exception class.

**Example 2:** [`foundation/classic-shared-py/src/lib.rs`](../../foundation/classic-shared-py/src/lib.rs) provides `define_exceptions!` and `register_exceptions!` macros plus the `ToPyErr` trait and `ResultExt` extension for consistent exception wiring across all Python binding crates.

**Example 3:** Tests use `pytest.raises(RustConfigParseError)` with message inspection to verify both the exception type and the error context.

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
