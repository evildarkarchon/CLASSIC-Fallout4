# `classic-user-settings-core` API Guide

Contributor-facing documentation for [`business-logic/classic-user-settings-core/`](../../business-logic/classic-user-settings-core).

## Purpose

`classic-user-settings-core` is the deep Rust owner for CLASSIC User Settings. Its initial public slice is deliberately read-only: [`UserSettings::open`](../../business-logic/classic-user-settings-core/src/document.rs) takes an explicit CLASSIC root and returns a typed snapshot without creating, moving, repairing, canonicalizing, or touching either supported source file.

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

Stable diagnostic codes currently include:

- `migration_required_previous_location`
- `migration_required_unversioned_document`
- `migration_required_flat_classic_config`
- `invalid_type_update_check`
- `malformed_document`
- `unreadable_document`
- `invalid_schema_version`
- `unsupported_older_schema`
- `unsupported_future_major_schema`
- `commit_blocked_untrusted_document`

## Binding and native CLI surface

- CXX: `classic::settings::user_settings_open_update_preferences(classic_root)` returns `UpdatePreferencesDto` with the safe boolean, provenance, source/classification, schema, revision, commit policy, structured diagnostics, and exact original bytes.
- Node: `openUserSettings(classicRoot)` returns `JsUserSettingsSnapshot`, including exact source bytes as `originalContent`.
- Python: `classic_user_settings.open_user_settings(classic_root)` returns `UserSettingsSnapshot`, including exact source bytes.

The native CLI `--check-app-update` path resolves a CLASSIC root, opens this typed group, reports structured diagnostics, and returns before runtime initialization, cache setup, installed-version validation, or network access when the safe value is `false`. YAML Data commands and scan preparation remain on their existing paths until issue #103’s broader native CLI cutover.

## Validation

Focused checks:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo test -p classic-user-settings-core
cargo test -p classic-cpp-bridge test_user_settings_update_preferences_bridge_is_fail_closed_with_diagnostics
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "App update honors disabled typed User Settings before checking the network,App update fails closed for malformed User Settings"
```

The compatibility source of truth remains [`tests/fixtures/user_settings_compatibility/expectations.json`](../../tests/fixtures/user_settings_compatibility/expectations.json), with its prefactoring guard in `classic-config-core` and public-interface behavioral coverage in the new crate.
