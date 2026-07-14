# `classic-user-settings-core` API Guide

Contributor-facing documentation for [`business-logic/classic-user-settings-core/`](../../business-logic/classic-user-settings-core).

## Purpose

`classic-user-settings-core` is the deep Rust owner for CLASSIC User Settings. [`UserSettings::open`](../../business-logic/classic-user-settings-core/src/document.rs) takes an explicit CLASSIC root and returns a typed snapshot without creating, moving, repairing, canonicalizing, or touching either supported source file. [`UserSettings::plan_migration`](../../business-logic/classic-user-settings-core/src/migration.rs) derives a deterministic, reversible proposal from that retained snapshot without touching disk; callers explicitly apply an approved plan and may explicitly restore its verified retained backup. Callers separately validate a multi-field [`UserSettingsUpdate`](../../business-logic/classic-user-settings-core/src/update.rs) as a non-persisting preview, then explicitly commit its accepted artifact through the same conflict-safe persistence seam.

This crate is distinct from:

- `classic-settings-core`, which supplies generic YAML parsing/cache utilities
- `classic-config-core::ClassicConfig`, which remains a transitional legacy flat-schema adapter until the later breaking cutovers
- YAML Data, which is curated application data rather than persisted user choices

## Published-default registry and compatibility mirror

[`src/default_settings.rs`](../../business-logic/classic-user-settings-core/src/default_settings.rs) is the single Rust authority for the current User Settings schema metadata, canonical paths and labels, published defaults, and default-file guidance. Typed open paths consume the same registry values used by the renderer, including Crash Log Scan, Game Setup, frontend defaults, and the compatibility `Update Source` selection. The registry keeps `INI Folder Path`, `Audio Notifications`, `Update Source`, and `Disable CLI Progress` in the generated compatibility mirror for older clients; `Update Source` is additionally exposed through typed reads and explicit User Settings Updates for maintained compatibility adapters.

`UserSettings::published_defaults()` projects those values as a read-only missing-source snapshot without probing the filesystem. Interface reset actions use this seam, so Qt and other wrappers do not duplicate Rust-owned default policy or create a document before the user confirms a commit.

`CLASSIC_Info.default_settings` in [`CLASSIC Main.yaml`](../../CLASSIC%20Data/databases/CLASSIC%20Main.yaml) is a checked-in generated compatibility mirror. Regenerate or verify it from the repository root with:

```powershell
cargo run -p classic-user-settings-core --bin generate-user-settings-default-mirror
cargo run -p classic-user-settings-core --bin generate-user-settings-default-mirror -- --check
```

Generation replaces only the literal-scalar body, preserves the outer YAML's newline convention and all surrounding bytes, and is byte-idempotent. `--check` first parses and semantically compares every canonical registered path and YAML value, then requires the checked-in text—including generated ordering and guidance—to match exactly. The crate's integration test runs this check against the real repository so Rust CI fails on drift.

The compatibility direction is deliberately one-way: registry → generated mirror. `UserSettings::open` never reads `CLASSIC Main.yaml` or `CLASSIC_Info.default_settings`; it still probes only the canonical and legacy User Settings documents below. Explicit bootstrap commits build their complete document directly from this registry, so the GUI no longer reads the compatibility mirror to create User Settings.

## Root-relative discovery

Open probes sources in this order:

1. `<CLASSIC root>/CLASSIC Settings.yaml` (`SourceLocation::Canonical`)
2. `<CLASSIC root>/CLASSIC Data/CLASSIC Settings.yaml` (`SourceLocation::Legacy`), but only when the canonical path is not found
3. no source (`SourceLocation::Missing`)

A canonical file that is unreadable or malformed still wins. Rust returns a degraded canonical view rather than silently falling through to a valid legacy file and bypassing an untrusted current source.

Open reads bytes directly and never uses `Path::exists()`, so permission failures are not collapsed into “missing.” Missing settings do not cause either a file or `CLASSIC Data` directory to be created.

## Snapshot model

`UserSettings` exposes:

- `source()` — selected location and path
- `classification()` — document/schema classification
- `schema_version()` — parsed `(major, minor)` when present and valid
- `revision()` — `Revision::ContentSha256` over exact source bytes, `Missing`, or `Unavailable`
- `update_preferences()` — typed `UpdatePreferences`
- `crash_log_scan_settings()` — typed `CrashLogScanSettings`
- `game_setup_settings()` — typed `GameSetupSettings`
- `frontend_state()` — typed, namespaced `FrontendState`
- `diagnostics()` — ordered structured `Diagnostic { code, message }` values
- `original_bytes()` — exact source content retained for later semantic preservation and byte-exact migration backups
- `commit_eligibility()` — `Eligible`, `RequiresMigration`, or `BlockedUntrusted`
- `plan_migration()` — `NotRequired`, a revision-anchored `UserSettingsMigrationPlan`, or structured unsupported diagnostics

Retaining exact bytes keeps unknown root and nested mappings, sequences, nulls, booleans, numbers, strings, and untouched invalid known values available to later User Settings Update commits. Semantic preservation does not promise to retain comments, quoting style, or whitespace after a future explicit commit.

## Document classifications and trust

The current schema is `1.0`.

| Classification | Meaning | Typed read | Commit eligibility |
| --- | --- | --- | --- |
| `Missing` | neither supported path exists | published defaults | `Eligible` |
| `Current` | version `1.0` nested document | known values with per-setting validation | `Eligible` |
| `NewerCompatible` | same major, higher minor (`1.x`) | additive fields tolerated; unknown content retained | `Eligible` |
| `Unversioned` | recognized nested document without `schema_version` | known values projected | `RequiresMigration` |
| `LegacyFlat` | recognized flat `ClassicConfig` shape | known legacy values projected | `RequiresMigration` |
| `Older` | schema major older than `1` | degraded safe fallbacks | `BlockedUntrusted` |
| `FutureMajor` | schema major newer than `1` | degraded safe fallbacks | `BlockedUntrusted` |
| `Malformed` | unreadable, invalid UTF-8/YAML/schema, or wrong document count | degraded safe fallbacks | `BlockedUntrusted` |

The Rust API publishes `CURRENT_USER_SETTINGS_SCHEMA_VERSION` as an explicit `UserSettingsSchemaVersion { major, minor }`. There are currently no supported older versioned schema edges: recognized unversioned nested documents and the flat `ClassicConfig` shape are supported legacy origins, while an explicit `0.x` document returns `unsupported_schema_version_gap`. Same-major newer documents retain their installed minor version and are never downgraded.

Legacy-location documents also require migration even when their content is otherwise understood.

## Update Preferences policy

`UpdatePreferences::update_check()` is already safety-adjusted for consumers:

| Input | Value | `PreferenceOrigin` |
| --- | --- | --- |
| valid boolean in a trusted document | document value | `Document` |
| missing document or absent setting | published default `true` | `Default` |
| invalid setting value | fail-closed `false` | `DegradedFallback` |
| malformed, unreadable, older-incompatible, or future-major document | fail-closed `false` | `DegradedFallback` |

The default and degraded fallback are intentionally different. A first-run user with no document receives the published default, while a source that may contain an unreadable opt-out never enables network access.

`UpdatePreferences::update_source()` returns the typed `UpdateSource::GitHub` or `UpdateSource::Both` compatibility selection, with provenance from `update_source_origin()`. Canonical and case-insensitive legacy spellings are accepted. Missing values use the published `GitHub` default; invalid or untrusted values also fall back to `GitHub` with `DegradedFallback` provenance and a structured diagnostic.

## Crash Log Scan settings

`CrashLogScanSettings` projects the persisted choices needed to prepare a Crash Log Scan Run without loading or changing User Settings downstream. Every getter has a matching `*_origin()` accessor so consumers can distinguish a valid document value, a published default, and a safety-oriented fallback.

| Canonical YAML label | Typed getter | Published default | Invalid or untrusted fallback |
| --- | --- | --- | --- |
| `Game Version` | `game_version_selection()` | `GameVersionSelection::Auto` | `Auto` |
| `FCX Mode` | `fcx_mode()` | `false` | `false` |
| `Simplify Logs` | `simplify_logs()` | `false` | `false` |
| `Show Statistics` | `show_statistics()` | `false` | `false` |
| `Show FormID Values` | `formid_value_lookup()` | `false` | `false` |
| `FormID Databases` | `formid_databases()` | empty game map | empty game map |
| `Move Unsolved Logs` | `move_unsolved_logs()` | `true` | `false` |
| `Unsolved Logs Destination` | `unsolved_logs_destination()` | `None` | `None` |
| `SCAN Custom Path` | `custom_scan_input()` | `None` | `None` |
| `Max Concurrent Scans` | `max_concurrent_scans()` | `0` (adaptive) | `0` |

`GameVersionSelection` keeps `auto` distinct from concrete Original, NextGen, Anniversary Edition, and VR selections. Concurrency is valid from `0` through `32`. An Unsolved Logs Destination and a `SCAN Custom Path` / `Custom Scan Folder` value must be empty/null or absolute; Windows drive and UNC spellings remain accepted on every build platform. FormID database strings remain unresolved and unnormalized because Crash Log Scan preparation later resolves relative database paths against CLASSIC Data.

The published `SCAN Custom Path` label is canonical. The GUI-era `Custom Scan Folder` alias remains readable for compatibility. When both values are valid and conflict, the canonical value wins, `canonical_alias_conflict_custom_scan_folder` is reported, and both original nodes remain retained. An alias-only document is projected without being rewritten.

## Game Setup settings

`GameSetupSettings` projects the saved facts needed to prepare Game Setup Intake without making intake load or persist User Settings. It contains the managed `GameId`, the shared `GameVersionSelection`, and the following optional path strings:

| User Settings label | Typed getter | Flat `ClassicConfig` source |
| --- | --- | --- |
| `Game Folder Path` | `game_root()` | `paths.game_root` |
| `Game EXE Path` | `game_executable()` | none |
| `Documents Folder Path` | `documents_root()` (effective canonical value) | `paths.docs_root` |
| `INI Folder Path` | `ini_folder()` (typed compatibility-alias value) | `paths.ini_folder` |
| `MODS Folder Path` | `mods_root()` | `paths.mods_folder` |
| `SCAN Custom Path` | `custom_scan_input()` | `paths.scan_custom` |
| `Papyrus Log Path` | `papyrus_log()` | none |

Every getter has a matching `*_origin()` accessor. Missing settings use Fallout 4, `GameVersionSelection::Auto`, and absent paths as published defaults. An untrusted document exposes the same safe values with `DegradedFallback` provenance. `Managed Game` accepts the supported human-facing labels and stable `GameId` spellings.

Paths are validated lexically without existence checks. Native, Windows drive, UNC, Unix, and Proton spellings are accepted on every build platform and retained exactly as persisted; opening never rewrites separators. `Documents Folder Path` is canonical and `INI Folder Path` is its compatibility alias. The effective `documents_root()` getter applies precedence before intake is built; a valid canonical null or empty value therefore remains an explicit clear and cannot resurrect a stale INI alias. `ini_folder()` still exposes the separately typed alias fact for transitional consumers.

The published `Documents Folder Path`, `MODS Folder Path`, and `SCAN Custom Path` labels take precedence over their `INI Folder Path`, `Staging Mods Folder`, and `Custom Scan Folder` compatibility aliases. Two valid conflicting document paths report `canonical_alias_conflict_ini_folder`; mods and custom-scan conflicts report their corresponding codes. An invalid canonical value may fall back to a valid alias while retaining the canonical-field diagnostic; alias nodes are never rewritten by open or ordinary update preview.

## Frontend state

`FrontendState` is a widget-independent projection of remembered presentation state. Rust owns the persisted value shapes, defaults, validation, provenance, and diagnostics; Qt and Ratatui keep control of widget sizing, rendering, and interaction behavior.

| Namespace | Typed values | Published and invalid fallback |
| --- | --- | --- |
| `UI.preferences` | `auto_switch_after_scan`, `auto_refresh_interval_ms` | `true`, `5000` ms |
| `UI.window_geometry.main_tab` | positive `u32` width/height, boolean maximized | `640 x 500`, not maximized |
| `UI.window_geometry.backups_tab` | positive `u32` width/height, boolean maximized | `750 x 580`, not maximized |
| `UI.window_geometry.articles_tab` | positive `u32` width/height, boolean maximized | `550 x 350`, not maximized |
| `UI.window_geometry.results_tab` | positive `u32` width/height, boolean maximized | `750 x 450`, not maximized |
| `UI.tui` | active tab `0..=3`, `u16` Results-panel width, boolean ascending sort | `0`, `30`, `false` |

Every leaf has a matching `*_origin()` accessor. A missing leaf uses `PreferenceOrigin::Default`; an invalid leaf uses the documented value with `DegradedFallback` while valid sibling leaves remain available. A malformed, unreadable, older-incompatible, or future-major document exposes the same presentation-safe values with `DegradedFallback` provenance. The Results-panel width deliberately accepts the full `u16` range, including zero, so the canonical representation can import the legacy TUI document without inventing a new widget constraint; a frontend may still clamp it while rendering.

`UI.preferences.auto_switch_after_scan` is canonical. The live GUI-era `CLASSIC_Settings.Auto Switch After Scan` label remains readable as a compatibility alias so the existing settings-dialog writer continues to affect later reads. When both booleans are valid and conflict, the canonical value wins and `canonical_alias_conflict_auto_switch_after_scan` is reported. The legacy flat `auto_switch_to_results` and `auto_refresh_interval_ms` fields are also projected for a later explicit migration.

Opening User Settings never probes or imports the retired TUI platform-config `state.json`; `UI.tui` is its canonical shared destination. `import_legacy_tui_state(classic_root, legacy_state_path)` is the explicit import seam available to every maintained interface. It validates the three known JSON leaves, retains and rereads a byte-exact content-addressed source backup under `CLASSIC Backup/User Settings/TUI State Imports/`, retains the exact existing settings base when present, then bootstraps or commits one all-or-nothing `UI.tui` transition. Migration-required and untrusted User Settings bases remain unchanged, conflicts never overwrite newer bytes, and the legacy source is left dormant in place. Unknown legacy JSON is retained in the exact backup. The applied receipt reports both backup paths and supports conflict-safe explicit restore to either the exact prior document or the prior missing state; all backups remain retained. Unknown `UI` namespaces and unknown entries within `preferences`, `window_geometry`, individual tab mappings, and `tui` remain in `original_bytes()` unchanged. Invalid known nodes are likewise retained rather than repaired during open.

The maintained Qt geometry path consumes the revision-cohesive GUI snapshot. `MainWindow::saveTabGeometry(...)` records an accepted frontend-state transition through a typed `GuiWindow` update, and `restoreTabGeometry(...)` reads the same snapshot without reopening or interpreting raw keys. `UserSettings::commit_frontend_geometry_transition(...)` owns the one explicit reopen/re-preview retry for a stale automatic geometry save; the thin `GuiUserSettings::commitFrontendTransition(...)` adapter refreshes the caller's snapshot after success. Rejection or a second conflict is surfaced in GUI status instead of overwriting a newer revision.

## User Settings Migration Plan

`UserSettings::plan_migration()` operates only on the opened snapshot's retained bytes and revision. It performs no filesystem reads after open and never creates directories, writes or relocates documents, changes timestamps, or creates backups. Applying and restoring a caller-approved plan are separate explicit persistence operations.

The planning outcome is one of:

- `NotRequired` for missing settings, canonical current documents, and same-major newer documents with no explicit cleanup to propose
- `Planned(UserSettingsMigrationPlan)` for the previous location, recognized unversioned nested documents, the flat `ClassicConfig` shape, or optional explicit alias/value canonicalization
- `Unsupported(Vec<MigrationDiagnostic>)` for malformed/unreadable sources, future-major documents, and older version gaps with no registered transition

A plan reports whether migration is required before ordinary commits, its base `Revision`, source and target `MigrationEndpoint` values, ordered `MigrationChange` rows, exact original bytes, and deterministic proposed bytes. `reverse_in_memory()` swaps endpoints and byte payloads and reverses the ordered changes without I/O; it is a review tool, not a restore credential. Binding adapters may reconstruct this review data through the plan's standard `From` conversion so reversal remains core-owned. Such reconstructed plans are deliberately unattested and `apply()` rejects them; only a plan produced by `UserSettings::plan_migration()` can authorize persistence.

Required plans target `<CLASSIC root>/CLASSIC Settings.yaml`. Unversioned and flat inputs target schema `1.0`; a legacy-location document that already carries a supported `1.x` schema retains that version. Flat planning maps every characterized leaf to the golden nested document. Optional plans canonicalize known key aliases (`Staging Mods Folder`, `Custom Scan Folder`, and GUI-era `Auto Switch After Scan`) and recognized enum spellings without changing ordinary open or commit behavior. The transitional `INI Folder Path` fact remains preserved because the current flat golden contract still carries both INI and Documents paths.

Stable migration-planning diagnostics are `unsupported_schema_version_gap`, `future_major_schema_read_only`, `migration_source_untrusted`, `migration_source_unavailable`, and `migration_plan_failed`.

## Apply, verified backup, and restore

`UserSettingsMigrationPlan::apply(classic_root)` is the only core operation that begins a migration. It holds the same persistent `CLASSIC Settings.yaml.commit.lock` used by accepted User Settings Updates, reopens the selected source, and compares both its exact-byte revision and location before creating any backup. A stale plan returns `UserSettingsMigrationApplyOutcome::Conflict { expected_revision, actual_revision }`; it creates no backup and performs no publication.

For a matching plan, apply publishes the exact original bytes to a content-addressed file under `<CLASSIC root>/CLASSIC Backup/User Settings/Migrations/`, durably flushes it, and rereads it byte-for-byte. Only then does it atomically publish the approved proposed bytes at the canonical destination. Success is reported only after `UserSettings::open` returns the expected destination location, exact bytes, and SHA-256 revision. A post-publication verification failure restores the last accepted source before returning an error.

`UserSettingsMigrationApplyOutcome::Applied` carries an opaque `UserSettingsMigrationReceipt`. Its getters report the concrete source, destination, and backup paths; source and target version/location endpoints; verified backup revision; and reopened published revision. The receipt is bound to the CLASSIC root that produced those paths and is the only restore credential.

`UserSettingsMigrationReceipt::restore(classic_root)` reacquires the same lock, refuses a migrated revision conflict, rereads and verifies the retained backup, and restores it through the same durable atomic publisher. Canonical-to-canonical restore republishes the backup over the current document. For a legacy-to-canonical migration, restore also verifies the dormant legacy source has not changed, republishes the verified bytes there, retires the canonical winner, and reopens from the legacy location. The retained backup is never deleted. A stale document or legacy source returns `UserSettingsMigrationRestoreOutcome::Conflict` rather than overwriting newer bytes.

Operational apply/restore failures return `UserSettingsMigrationError { code, message }`. Stable code families are:

- `migration_plan_unattested` / `migration_plan_direction_unsupported`
- `migration_lock_open_failed` / `migration_lock_failed`
- `migration_backup_directory_failed`, `migration_backup_{create,write,flush,sync,replace,cleanup,verify}_failed`
- `migration_publish_{create,write,flush,sync,replace,cleanup}_failed`
- `migration_reopen_verify_failed`, `migration_rollback_failed`, and `migration_rollback_verify_failed`
- `migration_restore_root_mismatch`, `migration_restore_source_unavailable`, and `migration_restore_source_read_failed`
- `migration_restore_backup_read_failed` / `migration_restore_backup_verify_failed`
- `migration_restore_{create,write,flush,sync,replace,cleanup}_failed`
- `migration_restore_remove_destination_failed`, `migration_restore_reopen_verify_failed`, `migration_restore_rollback_failed`, and `migration_restore_rollback_verify_failed`

Backup, publication, verification, or restore interruption leaves the last accepted active document intact. A successfully created backup may remain after a later publication failure because it is a valid recovery artifact, not temporary state.

## User Settings Update preview

`UserSettingsUpdate` is an explicit request builder covering Update Check, Update Source, Auto Switch After Scan, typed `GuiWindow` geometry transitions, one complete TUI remembered-state transition, and every field in `CrashLogScanSettings` and `GameSetupSettings`. `UserSettings::preview_update(update)` performs no I/O and returns exactly one of:

- `UserSettingsUpdatePreview::Accepted(AcceptedUserSettingsUpdate)` when every requested field is valid
- `UserSettingsUpdatePreview::Rejected(Vec<UpdateDiagnostic>)` when the base snapshot is not commit-eligible or any requested field is invalid

An accepted preview is anchored to the opened `Revision` and contains only the requested canonical `UserSettingsUpdateField` values. `with_window_geometry(window, maximized, width, height)` expands one accepted window transition into the canonical maximized, width, and height fields; dimensions must be positive `u32` values after validation. `with_tui_remembered_state(active_tab, results_panel_width, sort_ascending)` expands one complete transition into `/UI/tui/active_tab`, `/UI/tui/results_panel_width`, and `/UI/tui/sort_ascending`; the tab must be `0..=3` and width must fit `u16`, including zero. Existing aliases, unknown entries, unrelated known-invalid values, and non-requested settings are never added as repair or normalization work.

A missing snapshot rejects ordinary `preview_update` with `update_base_requires_bootstrap`. First-run callers must use `preview_bootstrap(update)`, which accepts only `Revision::Missing`, remains side-effect-free, and marks the accepted artifact to create a complete schema `1.0` document from the Rust-owned published-default registry. Any requested fields are then patched into that same one-shot bootstrap commit. Calling bootstrap preview for an existing or untrusted document returns `bootstrap_base_not_missing`.

Validation is all-or-nothing. The implementation checks every requested field in one pass and returns each field-specific `UpdateDiagnostic { field_path, code, message }`; otherwise-valid fields are not exposed as a partial preview. The accepted preview is the only Rust artifact that can enter the commit workflow.

## Conflict-safe commit

`AcceptedUserSettingsUpdate::commit(classic_root)` holds an exclusive cross-process lock on the persistent `CLASSIC Settings.yaml.commit.lock` sibling, reopens the latest canonical document, and compares its exact-byte SHA-256 `Revision` with the preview revision before doing any patch or publication work. A mismatch returns `UserSettingsCommitOutcome::Conflict { expected_revision, actual_revision }` and leaves the newer document unchanged. A matching revision patches only the accepted canonical fields and returns `Committed { revision }`; rejected previews never produce an accepted artifact and therefore cannot call this operation.

Publication serializes the freshly reopened and semantically preserved YAML tree into a randomized same-directory temporary file, writes and flushes it, calls `sync_all()`, and atomically replaces the canonical path. On write/flush/sync/replace failure it explicitly closes and attempts to remove the temporary file; a removal failure returns `commit_temp_cleanup_failed` with the primary failure retained as context and may leave the artifact for external cleanup. The lock file is intentionally retained so deleting it cannot race another process opening the same coordination path. Directory metadata synchronization is best-effort where the platform exposes it. Comments, quoting, whitespace, and mapping order may change, but unknown structures, compatibility aliases, and untouched invalid known values remain semantically intact.

Operational failures return `UserSettingsCommitError { code, message }`. Stable publication codes are `commit_lock_open_failed`, `commit_lock_failed`, `commit_source_unavailable`, `commit_parse_failed`, `commit_patch_failed`, `commit_serialize_failed`, `commit_temp_create_failed`, `commit_temp_write_failed`, `commit_temp_flush_failed`, `commit_temp_sync_failed`, `commit_replace_failed`, and `commit_temp_cleanup_failed`. A cleanup failure message retains the primary stage failure as context.

Preview-specific rejection codes include `invalid_enum_update_source`, `invalid_enum_game_version`, `invalid_range_gui_geometry_width`, `invalid_range_gui_geometry_height`, the `invalid_path_*` codes for every optional setup path, `invalid_value_formid_databases`, `invalid_path_unsolved_logs_destination`, `invalid_path_custom_scan_input`, `invalid_range_max_concurrent_scans`, `update_base_requires_bootstrap`, `bootstrap_base_not_missing`, and `update_base_not_commit_eligible`. The CXX adapter also returns `invalid_enum_gui_window` when a caller supplies an unknown stable tab token.

Stable diagnostic codes currently include:

- `migration_required_previous_location`
- `migration_required_unversioned_document`
- `migration_required_flat_classic_config`
- `invalid_type_update_check`
- `invalid_enum_managed_game`
- `invalid_enum_game_version`
- `invalid_type_game_root` / `invalid_path_game_root`
- `invalid_type_game_executable` / `invalid_path_game_executable`
- `invalid_type_documents_root` / `invalid_path_documents_root`
- `invalid_type_ini_folder` / `invalid_path_ini_folder`
- `invalid_type_mods_folder` / `invalid_path_mods_folder`
- `invalid_type_papyrus_log` / `invalid_path_papyrus_log`
- `invalid_type_fcx_mode`
- `invalid_type_simplify_logs`
- `invalid_type_show_statistics`
- `invalid_type_show_formid_values`
- `invalid_type_formid_databases`
- `invalid_type_move_unsolved_logs`
- `invalid_type_unsolved_logs_destination`
- `invalid_path_unsolved_logs_destination`
- `invalid_type_custom_scan_input`
- `invalid_path_custom_scan_input`
- `invalid_type_max_concurrent_scans`
- `invalid_range_max_concurrent_scans`
- `invalid_value_formid_databases`
- `canonical_alias_conflict_ini_folder`
- `canonical_alias_conflict_mods_folder`
- `canonical_alias_conflict_custom_scan_folder`
- `canonical_alias_conflict_auto_switch_after_scan`
- `invalid_type_frontend_state`
- `invalid_type_frontend_preferences`
- `invalid_type_frontend_auto_switch_after_scan`
- `invalid_type_frontend_auto_refresh_interval_ms` / `invalid_range_frontend_auto_refresh_interval_ms`
- `invalid_type_gui_window_geometry` / `invalid_type_gui_geometry_tab`
- `invalid_type_gui_geometry_width` / `invalid_range_gui_geometry_width`
- `invalid_type_gui_geometry_height` / `invalid_range_gui_geometry_height`
- `invalid_type_gui_geometry_maximized`
- `invalid_type_tui_remembered_state`
- `invalid_type_tui_active_tab` / `invalid_range_tui_active_tab`
- `invalid_type_tui_results_panel_width` / `invalid_range_tui_results_panel_width`
- `invalid_type_tui_sort_ascending`
- `malformed_document`
- `unreadable_document`
- `invalid_schema_version`
- `unsupported_older_schema`
- `unsupported_future_major_schema`
- `commit_blocked_untrusted_document`

## Binding and native CLI surface

- CXX: `classic::settings::user_settings_open_update_preferences(classic_root)` retains the narrow update-policy DTO; `user_settings_open_crash_log_scan_settings(classic_root)`, `user_settings_open_game_setup_settings(classic_root)`, and `user_settings_open_frontend_state(classic_root)` expose cohesive consumer groups. `UserSettingsUpdateDto` carries complete GUI geometry and TUI remembered-state transitions. `user_settings_preview_update(...)` / `user_settings_commit_update(...)` and their bootstrap variants own ordinary persistence. `user_settings_import_legacy_tui_state(...)` returns an opaque handle whose outcome reports verified backup/revision evidence, and `user_settings_restore_legacy_tui_import(...)` explicitly restores its receipt. Versioned YAML migration continues through the separate migration handle/apply/restore surface.
- Node: `openUserSettings(classicRoot)` returns `JsUserSettingsSnapshot` with all four typed groups and exact source bytes. `JsUserSettingsUpdate` accepts optional typed `windowGeometry` and `tui` transitions; preview/commit and bootstrap calls remain read-only then explicit. `importLegacyTuiStateIntoUserSettings(classicRoot, legacyStatePath)` returns structured status, conflict, revision, backup, and opaque receipt data; `receipt.restore(classicRoot)` performs conflict-safe restoration. Operational failures retain stable core error codes on the thrown Node error.
- Python: `classic_user_settings.open_user_settings(classic_root)` returns `UserSettingsSnapshot` with all four typed groups and exact source bytes. `UserSettingsUpdate.set_window_geometry(...)` and `set_tui_remembered_state(...)` request cohesive frontend transitions before snapshot preview/commit or bootstrap. `import_legacy_tui_state_into_user_settings(classic_root, legacy_state_path)` returns typed outcome/receipt objects, and `receipt.restore(classic_root)` performs explicit restoration; import failures raise `LegacyTuiStateImportError` with the stable core code.

All maintained bindings expose the pure migration planner: CXX uses `user_settings_plan_migration(classic_root)`, Node uses `planUserSettingsMigration(classicRoot)`, and Python uses `UserSettingsSnapshot.plan_migration()`. Their result DTOs carry status, requiredness, version/location endpoints, ordered changes, exact original/proposed content, and structured diagnostics. CXX `user_settings_reverse_migration_plan(...)`, Node `reverseUserSettingsMigrationPlan(...)`, and Python `UserSettingsMigrationPlan.reverse_in_memory()` expose the same pure inverse review operation. Each binding also exposes explicit apply and opaque-receipt restore adapters; CXX and Node reopen and compare the caller-approved base revision plus exact proposed content before they invoke the core plan, while Python retains the immutable core plan directly.

The native CLI scan path opens `CrashLogScanSettingsDto` and `GameSetupSettingsDto`, reports structured validation/migration diagnostics, and projects their safety-adjusted values into explicit Crash Log Scan facts. Parser-presence bits distinguish explicit `--game`, `--game-version`, and `--max-concurrent` overrides from CLI defaults; enable-only scan flags are additive. Configured FormID rows, custom scan input, setup paths, and Unsolved Logs policy therefore reach scan intake without any raw User Settings read downstream.

The destination-setting scan action uses the CXX preview/commit seam and reopens the typed snapshot after a successful commit. The native CLI YAML Data and app-update checks both open Update Preferences and honor its safety-adjusted policy; disabled/degraded reads preserve their established exit behavior while diagnostics remain actionable. The GUI Game Setup path opens the typed group without writing, offers explicit bootstrap and verified migration/restore actions, runs intake from that group, and commits all caller-accepted detected and manual paths as one revision-anchored update. A successful startup-path commit immediately refreshes the cohesive GUI snapshot consumed by same-session scans. Staging and custom-scan actions select only the path changed by that user action and commit against the displayed GUI revision. GUI geometry read/write uses the cohesive typed GUI snapshot and update adapter.

The native TUI now opens that same revision-cohesive store. Crash Log Scan and Game Setup facts, path inputs, backup roots, result discovery/refresh policy, automatic Results switching, and remembered presentation state all come from the typed groups. Path and presentation saves use explicit all-or-nothing updates and reopen after success; migration requirements, degraded reads, invalid values, import failures, and revision conflicts use the existing status/Settings-overlay conventions. `state.json` is never a runtime store after the cutover and is read only by the explicit verified import action. No maintained frontend constructs or persists first-party User Settings through generic YAML operations.

## Validation

Focused checks:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo test -p classic-user-settings-core
cargo test -p classic-user-settings-core --test migration_planning_behavior
cargo test -p classic-user-settings-core --test migration_persistence_behavior
cargo test -p classic-config-core --test user_settings_compatibility_tests
cargo test -p classic-cpp-bridge test_user_settings_frontend_state_bridge
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "App update honors disabled typed User Settings before checking the network,App update fails closed for malformed User Settings"
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-mainwindow-geometry
```

The compatibility source of truth remains [`tests/fixtures/user_settings_compatibility/expectations.json`](../../tests/fixtures/user_settings_compatibility/expectations.json), with its prefactoring guard in `classic-config-core` and public-interface behavioral coverage in this crate. The checked-in fixtures cover canonical, alias-only, conflicting-alias, invalid-known-value, and unknown-entry documents.
