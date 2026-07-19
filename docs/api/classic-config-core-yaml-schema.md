# `classic-config-core` YAML Schema Contract

Runtime-facing schema reference for [`classic-config-core`](../../business-logic/classic-config-core). This page is the source of truth for the non-User-Settings YAML shapes consumed by explicit YAML Data loading, `YamlDataCore`, and Game Local persistence.

Reference: [`classic-config-core.md`](classic-config-core.md).

---

## Generic Source And Cache Path Policy

- User Settings discovery and path policy belongs exclusively to [`classic-user-settings-core`](classic-user-settings-core.md).
- Fallout 4 and Fallout 4 VR share the `Fallout4` YAML data identity. `Fallout4VR` therefore resolves to `CLASSIC Data/databases/CLASSIC Fallout4.yaml` and shared keys such as `CLASSIC_Ignore_Fallout4`; its executable, documents, and version-selection identities remain VR-specific.
- `load_explicit_yaml_data` does not use generic source or cache path policy. Its three request fields are the complete Main, game, and Local Ignore file identities for that operation.
- `YamlSource::Cache` and cache helpers use the `CLASSIC` base directory, not `CLASSIC-Fallout4`:
  - preferred: `dirs::config_dir()/CLASSIC/cache.yaml`
  - compatibility fallback when no user config dir is available: `<application-dir>/CLASSIC/cache.yaml`
  - final relative fallback: `CLASSIC/cache.yaml`

## Multi-Document Merge Semantics

- Explicit YAML Data, `YamlDataCore`, and Game Local loading parse the full YAML stream first, then merge it into one document.
- Every document in the stream must be a mapping. Any sequence, scalar, or null document is rejected.
- Nested mappings merge recursively.
- Sequences are replaced wholesale by the later document.
- Scalars replace earlier values.
- Type conflicts also resolve to the later value.
- An empty stream is an error.

Example:

```yaml
paths:
  nested:
    a: 1
items:
  - first
---
paths:
  nested:
    b: 2
items:
  - second
```

Result:

```yaml
paths:
  nested:
    a: 1
    b: 2
items:
  - second
```

---

## Explicit YAML Data Role Contract

`classic_config_core::load_explicit_yaml_data` accepts an `ExplicitYamlDataRequest` whose `main_path`, `game_path`, and `ignore_path` identify exactly one file for each role. The operation reads each path once, retains those bytes, and derives parsing, validation, the combined `YamlDataCore`, SHA-256, and byte length from the retained copies. The resulting `ExplicitYamlDataSnapshot` remains stable if the paths later change.

Every explicit role must be valid UTF-8 and satisfy the multi-document merge rules above. Validation then applies the following role contract:

| Role | Schema gate | Required semantic shape |
|---|---|---|
| Main | root `schema_version` must satisfy `client_schemas::MAIN_YAML` | `CLASSIC_Info` is a mapping and `CLASSIC_Info.version` is a non-empty string satisfying the [bare release-SemVer contract](#classic_infoversion-bare-semver-contract) |
| Game | root `schema_version` must satisfy `client_schemas::GAME_FALLOUT4_YAML` | `Game_Info` is a mapping and `Game_Info.Main_Root_Name` is a non-empty string that normalizes to `fallout4` when only lowercase ASCII alphanumeric characters are retained |
| Local Ignore | no shippable schema header | `CLASSIC_Ignore_Fallout4` is a sequence and every entry is a string; the sequence may be empty |

Main and game compatibility ranges are owned by config core. An explicit caller cannot provide a different range or cause an incompatible file to fall back to another source.

### Typed Game And Shared Fallout 4 Role

`ExplicitYamlDataRequest.game` is `classic_shared_core::GameId`, not a filename fragment. `GameId::Fallout4` and `GameId::Fallout4VR` both map to `GameDataRole::Fallout4`; both therefore validate the selected game document as Fallout 4 YAML Data and read the `CLASSIC_Ignore_Fallout4` key. The request's separate `selected_game_version` still controls Version Registry metadata selection, so VR runtime/version semantics remain distinct from the shared YAML Data role.

`GameId::Skyrim` and `GameId::Starfield` are not registered YAML Data roles in this client. Explicit loading returns `ExplicitYamlDataLoadError::UnsupportedGame` before reading any supplied path; it never constructs an arbitrary game filename.

### Valid Empty And Malformed Local Ignore

This is a valid empty Local Ignore document:

```yaml
CLASSIC_Ignore_Fallout4: []
```

It produces an empty `YamlDataCore::ignore_list`. These documents are malformed for the Local Ignore role and return `InvalidRoleData`:

```yaml
# Missing required key.
unrelated: []
```

```yaml
# Required key has the wrong shape.
CLASSIC_Ignore_Fallout4: not-a-sequence
```

```yaml
# Sequence entries must all be strings.
CLASSIC_Ignore_Fallout4:
  - valid-entry
  - 42
```

Missing, null, mapping, and mixed-type values are not treated as an empty ignore list.

### Exact-Byte Identity And No Mutation

`ExplicitYamlDataSnapshot::{main_identity, game_identity, ignore_identity}` each return a `YamlDataContentIdentity` with the lowercase SHA-256 and byte length of the exact retained source bytes. Identity is not computed from reserialized YAML, merged document structure, a later path read, or a settings cache.

Explicit loading has no installed-source behavior. It does not resolve or consult the YAML update cache, inspect or promote `.prev`, select bundled data, fall back, generate a missing Local Ignore document, repair/reset a malformed document, create a backup, or write/delete any file. Missing, unreadable, incompatible, or semantically invalid caller-selected content fails with an error attributed to its exact `ExplicitYamlDataRole` and path.

### Installed Snapshot And Malformed Local Ignore Recovery

`classic_config_core::load_installed_yaml_data` accepts one installation root, typed `GameId`, and the separate existing game-version mode. Main and game are independently selected through config-owned installed policy, while Local Ignore is read from `CLASSIC Data/CLASSIC Ignore.yaml` under that root and validated against the same Local Ignore role contract above.

If Local Ignore is absent, the exact retained selected Main document must contain a non-empty string at `CLASSIC_Info.default_ignorefile`. Its embedded YAML is parsed and strictly validated against the selected Local Ignore role before any staging file is created. Complete bytes are staged and synced in the destination directory, then atomically published without overwriting an existing or concurrently created file. Every caller rereads the canonical destination, making the concurrent winner authoritative; defaults are never reopened from a later version of the installed Main path.

On `InstalledYamlDataLoadOutcome::Ready`, `InstalledYamlDataSnapshot` privately owns the exact bytes selected for all three roles. Its public surface exposes parsed `YamlDataCore`, Main/game provenance and compatible schema versions, exact SHA-256/byte-length identities for all three files, `LocalIgnoreYamlDataState::{Existing, Generated}`, and structured selection/generation diagnostics. It does not expose raw YAML documents or byte buffers. Existing valid Local Ignore bytes are never replaced during ordinary loading, and later path changes cannot alter the snapshot.

An existing Local Ignore document that is invalid UTF-8, syntactically malformed, or invalid for the selected game role returns `InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired`. Its opaque `LocalIgnoreRecoveryPlan` retains the exact selected Main/game snapshot, selected-Main default state, malformed path and identity, selected game-version mode, and diagnostics without exposing raw documents. Valid defaults expose an identity; invalid or unavailable defaults are retained as unavailable for a future reset decision and do not block Proceed Without Ignore. `proceed_without_ignore()` consumes that plan and returns the retained snapshot with `LocalIgnoreYamlDataState::ProceedWithoutIgnore` and an empty operation-scoped `ignore_list`. It performs no filesystem operation, so every installed file remains byte-identical and the next load encounters the same malformed document again.

---

## `GameLocal` Runtime Path Data

Game Local readers and `persist_game_local_paths` use only these keys in `CLASSIC Data/CLASSIC {game} Local.yaml`:

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `Game_Info.Root_Folder_Game` | string path | no | persisted runtime-discovered game root |
| `Game_Info.Root_Folder_Docs` | string path | no | persisted runtime-discovered documents root |

`classic_config_core::persist_game_local_paths(path, game_root, docs_root)` creates the local YAML file when needed, preserves unrelated existing YAML keys, leaves a key unchanged when its update is `None`, and skips file creation entirely when both updates are `None`. The operation does not read or write `CLASSIC Settings.yaml`.

---

## `YamlDataCore` Sections And Shapes

`YamlDataCore` consumes three merged YAML documents: Main, Game, and Ignore. Missing sections usually become empty strings, empty vectors, or empty maps unless noted otherwise.

### Main YAML

| Section / key | Type / shape | Behavior |
|---|---|---|
| `CLASSIC_Info.version` | string (bare SemVer, e.g. `v9.1.0`) | populates `classic_version`; see [Bare-SemVer contract](#classic_infoversion-bare-semver-contract) below |
| `CLASSIC_Info.version_date` | string | populates `classic_version_date` |
| `catch_log_records` | sequence of strings | populates `classic_records_list` |
| `CLASSIC_Interface.autoscan_text_<Game>` | string | populates `autoscan_text` using the caller-provided game name |

`CLASSIC Main.yaml` `schema_version: "2.1"` added optional `CLASSIC_Settings.Unsolved Logs Destination` to the shipped `CLASSIC_Info.default_settings` template. The template is a generated compatibility artifact, not a runtime bootstrap or a second source of User Settings defaults.

`schema_version: "2.2"` makes that template a deterministic compatibility mirror of the Rust-owned User Settings registry. It additively includes all canonical Crash Log Scan, Game Setup, and frontend defaults while retaining compatibility-only fields required by older clients. No production path may read it as User Settings defaults; regenerate and check the artifact through the `classic-user-settings-core` generator documented in [`classic-user-settings-core.md`](classic-user-settings-core.md#published-default-registry-and-compatibility-mirror).

#### `CLASSIC_Info.version` bare-SemVer contract

Under `schema_version: "2.0"` and later, `CLASSIC_Info.version` stores a bare SemVer string of the form `<MAJOR>.<MINOR>.<PATCH>` with an optional leading `v` or `V` (e.g., `v9.1.0`, `9.1.0`). SemVer prerelease suffixes (`-beta.N`, `-rc.N`, `-alpha`, etc.) and build metadata (`+build.N`) are forbidden in this field and are rejected by `load_main_yaml_version` / `validate_release_semver_shape` in `classic-config-core`. The value SHALL NOT contain display-only decoration such as the `CLASSIC ` product-name prefix. Consumers that need the decorated form (e.g., the scanlog report header `**AUTOSCAN REPORT GENERATED BY CLASSIC v9.1.0**`) prepend the product-name prefix at format time; consumers that need bare SemVer (Qt `setApplicationVersion`, CMake `PROJECT_VERSION` guard, update-check comparisons) consume it directly without stripping.

Prerelease status for a given published version is signaled through the sibling `CLASSIC_Info.is_prerelease` boolean together with the monotonic `CLASSIC_Info.version_date` (`YY.MM.DD`), not by annotating the version string — the maintainer workflow is `set_version.ps1 -Version "X.Y.Z" -IsPrerelease $true -Date "YY.MM.DD"`, and the `publish-yaml-data` workflow mirrors the same boolean through `gh release --prerelease=true/false`. See the "Prerelease status is signaled via `is_prerelease` + `version_date`" requirement in [`openspec/specs/yaml-app-version-field/spec.md`](../../openspec/specs/yaml-app-version-field/spec.md).

Under legacy `schema_version: "1.x"` the value was decorated (`CLASSIC v9.1.0`); the `MAIN_YAML` [`SchemaCompat`](classic-config-core.md) constant rejects 1.x files in current clients. Full contract: [`openspec/specs/yaml-app-version-field/spec.md`](../../openspec/specs/yaml-app-version-field/spec.md).

### Game YAML

| Section / key | Type / shape | Behavior |
|---|---|---|
| `Game_Hints` | sequence of strings | populates `classic_game_hints` |
| `Game_Info.Main_Root_Name` | string | populates `game_root_name`; drives Version Registry fallback lookups |
| `Game_Info.CRASHGEN_LogName` | string | populates `crashgen_name`; if empty, falls back to Version Registry crashgen metadata |
| `Game_Info.CRASHGEN_LatestVer` | string | populates `crashgen_latest_og`; if empty, falls back to Version Registry crashgen metadata |
| `Game_Info.CRASHGEN_Ignore` | sequence of strings | populates `crashgen_ignore`; fallback to `Crashgen_Registry.<selected-or-default>.ignore_keys` only happens when this path is missing, not when it exists but is null or malformed |
| `Game_Info.XSE_Acronym` | string | populates `xse_acronym`; if empty, falls back to Version Registry XSE metadata |
| `Game_Info.GameVersion` | string | populates `game_version`; if empty, falls back to Version Registry version text |
| `Warnings_CRASHGEN.Warn_NOPlugins` | string | populates `warn_noplugins` |
| `Warnings_CRASHGEN.Warn_Outdated` | string | populates `warn_outdated` |
| `Crashlog_Plugins_Exclude` | sequence of strings | populates `game_ignore_plugins` |
| `Crashlog_Records_Exclude` | sequence of strings | populates `game_ignore_records` |
| `Crashlog_Error_Check` | sequence of `SuspectErrorRule` mappings | populates `suspect_error_rules`; source order is preserved |
| `Crashlog_Stack_Check` | sequence of `SuspectStackRule` mappings | populates `suspect_stack_rules`; source order is preserved |

`SuspectErrorRule` entry shape:

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `id` | string | yes | stable machine-readable identifier |
| `name` | string | yes | report display name |
| `severity` | integer or numeric string | yes | severity used for sorting and display |
| `main_error_contains_any` | sequence of strings | yes | rule matches when any listed main-error substring is present |

`SuspectStackRule` entry shape:

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `id` | string | yes | stable machine-readable identifier |
| `name` | string | yes | report display name |
| `severity` | integer or numeric string | yes | severity used for sorting and display |
| `main_error_required_any` | sequence of strings | no | if non-empty, any listed main-error substring must be present before the rule can match |
| `main_error_optional_any` | sequence of strings | no | optional main-error hints that can trigger the rule when no required list is present |
| `stack_contains_any` | sequence of strings | no | stack substrings where any match can trigger the rule |
| `exclude_if_stack_contains_any` | sequence of strings | no | suppresses the rule when any listed stack substring is present |
| `stack_contains_at_least` | sequence of `SuspectStackCountRule` mappings | no | minimum occurrence stack checks |

`SuspectStackCountRule` entry shape:

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `substring` | string | yes | substring counted inside the stack dump |
| `count` | positive integer or numeric string | yes | minimum number of occurrences required |
| `Mods_CONF` | sequence of `ModConflictEntry` mappings | populates `game_mods_conf` (`Vec<ModConflictEntry>`); deduplicated at parse time by canonical pair order |
| `Mods_CORE` | sequence of `CoreModEntry` mappings | populates `game_mods_core` (`Vec<CoreModEntry>`); entries with missing required fields are skipped |
| `Mods_FREQ` | sequence of `ModSolutionEntry` mappings | populates `game_mods_freq` (`Vec<ModSolutionEntry>`); YAML order is preserved |
| `Mods_SOLU` | sequence of `ModSolutionEntry` mappings | populates `game_mods_solu` (`Vec<ModSolutionEntry>`); YAML order is preserved |
| `Crashgen_Registry` | mapping of crashgen name -> mapping | parsed into `HashMap<String, CrashgenEntryRaw>`; malformed entries are skipped rather than failing the whole file |

`Crashgen_Registry.<name>` entry shape:

| Key | Type / shape | Behavior |
|---|---|---|
| `display_section` | string | display-only header; defaults to empty string |
| `ignore_keys` | sequence of strings | defaults to empty list; used as `crashgen_ignore` fallback |
| `checks` | sequence of strings | deprecated inert compatibility metadata; defaults to empty list and does not select scan-time checks |
| `settings_rules_version` | non-negative integer or numeric string | optional |
| `settings_rules` | mapping | optional; parsed by the Crashgen Expectation Parser into `CrashgenSettingsRules`; malformed nested rules are skipped/defaulted where possible |

`settings_rules` is the behavioral source of Crashgen Expectations. Recognized nested settings-rules keys from current source include:

- `settings_rules.preflight[].id`
- `settings_rules.preflight[].when`
- `settings_rules.preflight[].action.kind`
- `settings_rules.preflight[].action.placement`
- `settings_rules.preflight[].action.bucket`
- `settings_rules.preflight[].action.severity`
- `settings_rules.preflight[].action.message`
- `settings_rules.preflight[].action.fix`
- `settings_rules.checks[].id`
- `settings_rules.checks[].target.section`
- `settings_rules.checks[].target.key`
- `settings_rules.checks[].target.type`
- `settings_rules.checks[].target.value_type`
- `settings_rules.checks[].when`
- `settings_rules.checks[].expect.equals`
- `settings_rules.checks[].messages.fail`
- `settings_rules.checks[].messages.fix`
- `settings_rules.checks[].messages.pass`
- `settings_rules.checks[].severity`

Recognized predicate keys are `plugin_any`, `config_layout_is`, `crashgen_version_lt`, `all`, `any`, and `not`; omitted or malformed predicates default to always-applicable at the rule level. Supported action kinds are `notice_and_skip_remaining`, `notice`, and `issue`. Supported severities are `info`, `warning`, and `error`. Supported target types are `bool`, `int`, and `string`.

`settings_rules.checks[].target.type` is the canonical YAML Data key for target value type. `settings_rules.checks[].target.value_type` is accepted as a binding compatibility alias by the shared parser, but first-party YAML Data should prefer `type`. Current precedence is:

1. valid `type`
2. valid `value_type`
3. default `bool`

`settings_rules.preflight[].action.placement` is the preferred Autoscan Report Placement key. `settings_rules.preflight[].action.bucket` remains a compatibility alias for older clients during the transition. Current shipped YAML dual-writes both keys when a non-default placement is required.

Placement parse precedence is:

1. valid `placement`
2. valid `bucket`
3. default `settings`

Accepted placement values are:

- `settings` - default placement when omitted or malformed
- `error_information` - promotes the rendered notice or issue into the Autoscan Report `Error Information` section for placement-aware callers

`Mods_CONF[]` entry shape (`ModConflictEntry`):

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `mod_a` | string | yes | identifier matched case-insensitively as substring against plugin filenames |
| `mod_b` | string | yes | identifier matched case-insensitively as substring against plugin filenames |
| `name_a` | string | yes | human-readable display name for mod A |
| `name_b` | string | yes | human-readable display name for mod B |
| `description` | string | yes | why the conflict matters |
| `fix` | string | yes | what the user should do |
| `link` | string | no | optional URL for patch or alternative |

Deduplication: at parse time each pair is canonicalized to `(min(mod_a, mod_b), max(mod_a, mod_b))` using case-insensitive comparison. If a duplicate canonical pair is found, it is skipped with a warning log.

`Mods_CORE[]` entry shape (`CoreModEntry`):

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `detect` | string | yes | substring matched case-insensitively against plugin / XSE module names |
| `name` | string | yes | human-readable display name shown in the report |
| `description` | string | yes | recommendation text shown when the mod is missing |
| `gpu` | string | no | GPU vendor this mod is for (`"nvidia"` or `"amd"`); used for GPU-specific install/uninstall logic |
| `gpu_mismatch_warning` | string | no | custom warning text shown when the mod is installed but the user does NOT have the GPU specified by `gpu`; falls back to a generic message when absent |
| `exclude_when` | mapping | no | condition under which this entry is skipped entirely |

`Mods_FREQ[]` entry shape (`ModSolutionEntry`):

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `id` | string | yes | stable machine-readable identifier for the frequent-crash entry |
| `criteria` | mapping with exactly one of `any` or `all` | yes | grouped plugin-substring matcher used for detection |
| `exceptions` | sequence of strings | no | suppresses the entry when any listed substring matches an installed plugin filename |
| `name` | string | yes | human-readable title rendered directly in reports |
| `description` | string | yes | report body rendered directly without first-line splitting |

`Mods_FREQ[].criteria` currently supports:

| Key | Type / shape | Behavior |
|---|---|---|
| `any` | sequence of strings | reports the entry when at least one listed substring matches an installed plugin filename |
| `all` | sequence of strings | reports the entry only when every listed substring matches an installed plugin filename |

`Mods_SOLU[]` entry shape (`ModSolutionEntry`):

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `id` | string | yes | stable machine-readable identifier for the solution entry |
| `criteria` | mapping with exactly one of `any` or `all` | yes | grouped plugin-substring matcher used for detection |
| `exceptions` | sequence of strings | no | suppresses the entry when any listed substring matches an installed plugin filename |
| `name` | string | yes | human-readable title rendered directly in reports |
| `description` | string | yes | report body rendered directly without first-line splitting |

`Mods_SOLU[].criteria` currently supports:

| Key | Type / shape | Behavior |
|---|---|---|
| `any` | sequence of strings | reports the entry when at least one listed substring matches an installed plugin filename |
| `all` | sequence of strings | reports the entry only when every listed substring matches an installed plugin filename |

`exclude_when` currently supports one predicate:

| Key | Type / shape | Behavior |
|---|---|---|
| `plugin_any` | sequence of strings | exclude when any of the listed plugins are present (case-insensitive) |

### Ignore YAML

| Section / key | Type / shape | Behavior |
|---|---|---|
| `CLASSIC_Ignore_<Game>` | sequence of strings | populates `ignore_list` using the caller-provided game name |

## `YamlDataCore` Fallback Rules

- YAML values already present in `Game_Info` win over Version Registry metadata.
- Version Registry fallback only runs when `Game_Info.Main_Root_Name` is present and non-empty.
- `selected_game_version` affects which registry entry is preferred:
  - explicit non-VR selections prefer matching non-VR `short_name`
  - VR mode prefers registry entries marked VR
  - registry-configured defaults are checked before a generic first-match fallback
- `crashgen_ignore` falls back only when the `Game_Info.CRASHGEN_Ignore` path is absent and the extracted list is still empty.
- If `Game_Info.CRASHGEN_Ignore` exists but is null, malformed, or otherwise not a usable string list, that still counts as configured for fallback purposes, so registry fallback does not run.

---

## Contributor Notes

- If you add or remove consumed keys in explicit role validation, `YamlDataCore`, or Game Local persistence, update this page in the same change.
- If a binding or frontend depends on a new default, note that here even if the Rust API itself does not change.
