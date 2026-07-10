# `classic-user-settings-core` API Guide

Contributor-facing documentation for [`business-logic/classic-user-settings-core/`](../../business-logic/classic-user-settings-core).

## Purpose

`classic-user-settings-core` is the deep Rust owner for CLASSIC User Settings. [`UserSettings::open`](../../business-logic/classic-user-settings-core/src/document.rs) takes an explicit CLASSIC root and returns a typed snapshot without creating, moving, repairing, canonicalizing, or touching either supported source file. Callers may also validate an explicit multi-field [`UserSettingsUpdate`](../../business-logic/classic-user-settings-core/src/update.rs) as a non-persisting preview; persistence remains a separate, caller-approved operation.

This crate is distinct from:

- `classic-settings-core`, which supplies generic YAML parsing/cache utilities
- `classic-config-core::ClassicConfig`, which remains a transitional legacy flat-schema adapter until the later breaking cutovers
- YAML Data, which is curated application data rather than persisted user choices

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
- `diagnostics()` — ordered structured `Diagnostic { code, message }` values
- `original_bytes()` — exact source content retained for later semantic preservation and byte-exact migration backups
- `commit_eligibility()` — `Eligible`, `RequiresMigration`, or `BlockedUntrusted`

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

## User Settings Update preview

`UserSettingsUpdate` is an explicit request builder covering Update Check plus every field in `CrashLogScanSettings`. `UserSettings::preview_update(update)` performs no I/O and returns exactly one of:

- `UserSettingsUpdatePreview::Accepted(AcceptedUserSettingsUpdate)` when every requested field is valid
- `UserSettingsUpdatePreview::Rejected(Vec<UpdateDiagnostic>)` when the base snapshot is not commit-eligible or any requested field is invalid

An accepted preview is anchored to the opened `Revision` and contains only the requested canonical `UserSettingsUpdateField` values. `canonical_path()` reports names such as `/CLASSIC_Settings/Update Check` and `/CLASSIC_Settings/Max Concurrent Scans`. Existing aliases, unknown entries, unrelated known-invalid values, and non-requested settings are never added as repair or normalization work.

Validation is all-or-nothing. The implementation checks every requested field in one pass and returns each field-specific `UpdateDiagnostic { field_path, code, message }`; otherwise-valid fields are not exposed as a partial preview. The accepted preview is the validation artifact that the later conflict-safe commit workflow consumes.

Preview-specific rejection codes include `invalid_enum_game_version`, `invalid_value_formid_databases`, `invalid_path_unsolved_logs_destination`, `invalid_path_custom_scan_input`, `invalid_range_max_concurrent_scans`, and `update_base_not_commit_eligible`.

Stable diagnostic codes currently include:

- `migration_required_previous_location`
- `migration_required_unversioned_document`
- `migration_required_flat_classic_config`
- `invalid_type_update_check`
- `invalid_enum_game_version`
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
- `canonical_alias_conflict_custom_scan_folder`
- `malformed_document`
- `unreadable_document`
- `invalid_schema_version`
- `unsupported_older_schema`
- `unsupported_future_major_schema`
- `commit_blocked_untrusted_document`

## Binding and native CLI surface

- CXX: `classic::settings::user_settings_open_update_preferences(classic_root)` retains the narrow update-policy DTO; `user_settings_open_crash_log_scan_settings(classic_root)` exposes the complete typed scan group; and `user_settings_preview_update(classic_root, update)` returns an all-or-nothing preview DTO.
- Node: `openUserSettings(classicRoot)` returns `JsUserSettingsSnapshot` with both typed groups and exact source bytes as `originalContent`; `previewUserSettingsUpdate(classicRoot, update)` validates a `JsUserSettingsUpdate` without writing.
- Python: `classic_user_settings.open_user_settings(classic_root)` returns `UserSettingsSnapshot` with both typed groups and exact source bytes; `snapshot.preview_update(UserSettingsUpdate)` validates against that opened snapshot and revision without writing.

The native CLI `--check-app-update` path resolves a CLASSIC root, opens this typed group, reports structured diagnostics, and returns before runtime initialization, cache setup, installed-version validation, or network access when the safe value is `false`. YAML Data commands and scan preparation remain on their existing paths until issue #103’s broader native CLI cutover.

## Validation

Focused checks:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo test -p classic-user-settings-core
cargo test -p classic-config-core --test user_settings_compatibility_tests
cargo test -p classic-cpp-bridge test_user_settings_update_preferences_bridge_is_fail_closed_with_diagnostics
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "App update honors disabled typed User Settings before checking the network,App update fails closed for malformed User Settings"
```

The compatibility source of truth remains [`tests/fixtures/user_settings_compatibility/expectations.json`](../../tests/fixtures/user_settings_compatibility/expectations.json), with its prefactoring guard in `classic-config-core` and public-interface behavioral coverage in this crate. The checked-in fixtures cover canonical, alias-only, conflicting-alias, invalid-known-value, and unknown-entry documents.
