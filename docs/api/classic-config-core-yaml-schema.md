# `classic-config-core` YAML Schema Contract

Runtime-facing schema reference for [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core). This page is the source of truth for the YAML shapes that `ClassicConfig` and `YamlDataCore` consume after the shared loader refactor.

Reference: [`classic-config-core.md`](classic-config-core.md).

---

## Settings Discovery And Path Policy

- `ClassicConfig::load_or_default()` reads settings in this order:
  1. application directory: `CLASSIC Settings.yaml`
  2. application directory: `CLASSIC_Settings.yaml`
  3. user config directory: `dirs::config_dir()/CLASSIC/CLASSIC Settings.yaml`
  4. user config directory: `dirs::config_dir()/CLASSIC/CLASSIC_Settings.yaml`
- If none of those files exist, the crate returns `ClassicConfig::default()`.
- `ClassicConfig::get_config_path()` is best-effort and non-fallible:
  - it first tries to update the first existing writable settings file in the normal search order, including an existing writable legacy `CLASSIC_Settings.yaml`
  - if no existing candidate is writable, it tries to create `CLASSIC Settings.yaml` in the application directory, then in `dirs::config_dir()/CLASSIC/`
  - if those writability checks fail but at least one directory can still be resolved, it returns the preferred `CLASSIC Settings.yaml` target for that resolved directory anyway
  - it falls back to the plain relative filename `CLASSIC Settings.yaml` only when neither the application directory nor the user config directory can be resolved
- `YamlSource::Cache` and cache helpers use the `CLASSIC` base directory, not `CLASSIC-Fallout4`:
  - preferred: `dirs::config_dir()/CLASSIC/cache.yaml`
  - compatibility fallback when no user config dir is available: `<application-dir>/CLASSIC/cache.yaml`
  - final relative fallback: `CLASSIC/cache.yaml`

## Multi-Document Merge Semantics

- `ClassicConfig`, `YamlDataCore`, and `GameLocal` loading all parse the full YAML stream first, then merge it into one document.
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

## `ClassicConfig` Persisted Fields

All keys are read from the merged root mapping. Missing or malformed values usually fall back to defaults instead of failing the load.

| Key | Type / shape | Required | Default / behavior |
|---|---|---|---|
| `fcx_mode` | boolean | no | defaults to `false` |
| `show_formid_values` | boolean | no | defaults to `false` |
| `stat_logging` | boolean | no | defaults to `false` |
| `move_unsolved_logs` | boolean | no | defaults to `false` |
| `simplify_logs` | boolean | no | defaults to `false` |
| `update_check` | boolean | no | defaults to `true` |
| `game_version` | string | no | defaults to `"auto"`; callers interpret values such as `auto`, `Original`, `NextGen`, `AnniversaryEdition`/`AE`, and `VR` |
| `update_source` | string | no | defaults to `"github"` |
| `auto_switch_to_results` | boolean | no | defaults to `true` |
| `auto_refresh_interval_ms` | integer | no | defaults to `5000`; loaded through `as_i64()` then cast to `u64` |
| `paths` | mapping | no | omitted or partial mappings fall back field-by-field |
| `paths.ini_folder` | string path | no | omitted when `None`; usually points at the game documents / INI folder |
| `paths.scan_custom` | string path | no | omitted when `None`; custom crash-log scan folder |
| `paths.mods_folder` | string path | no | omitted when `None`; typically MO2 staging mods folder |
| `paths.game_root` | string path | effectively yes for usable installs | defaults to empty `PathBuf`; `validate_paths()` fails if the resolved path does not exist |
| `paths.docs_root` | string path | no | omitted when `None`; may be backfilled later from `CLASSIC Data/CLASSIC {game} Local.yaml` |
| `formid_databases` | mapping of game name -> sequence of string paths | no | defaults to empty map; non-string game keys or non-string items are skipped |

Persistence notes:

- `save_to_yaml()` always writes all scalar booleans/strings/integers.
- `save_to_yaml()` always writes `paths.game_root`, even when empty.
- Optional path fields are omitted when `None`; they are not written as explicit YAML nulls.
- `formid_databases` is omitted entirely when empty.
- Relative `formid_databases.<game>[]` entries are preserved as strings and resolved by higher layers at runtime.

## `GameLocal` Add-On Data Consumed By `ClassicConfig`

`ClassicConfig::load_local_yaml_paths(game)` loads merged YAML from `CLASSIC Data/CLASSIC {game} Local.yaml` and reads only:

| Key | Type / shape | Required | Behavior |
|---|---|---|---|
| `Game_Info.Root_Folder_Game` | string path | no | when present, replaces `paths.game_root` |
| `Game_Info.Root_Folder_Docs` | string path | no | when present, sets `paths.docs_root` |

If the local YAML file does not exist, the method returns `Ok(())` and leaves the existing config unchanged.

`ClassicConfig::save_local_yaml_paths(game)` and `ClassicConfig::save_local_yaml_paths_to(path)` persist only those same keys. They create the local YAML file when needed, preserve unrelated existing YAML keys, and skip file creation entirely when both `paths.game_root` and `paths.docs_root` are unset.

---

## `YamlDataCore` Sections And Shapes

`YamlDataCore` consumes three merged YAML documents: Main, Game, and Ignore. Missing sections usually become empty strings, empty vectors, or empty maps unless noted otherwise.

### Main YAML

| Section / key | Type / shape | Behavior |
|---|---|---|
| `CLASSIC_Info.version` | string | populates `classic_version` |
| `CLASSIC_Info.version_date` | string | populates `classic_version_date` |
| `catch_log_records` | sequence of strings | populates `classic_records_list` |
| `CLASSIC_Interface.autoscan_text_<Game>` | string | populates `autoscan_text` using the caller-provided game name |

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
| `Mods_FREQ` | mapping of string -> string | populates `game_mods_freq`; key order is preserved |
| `Mods_SOLU` | mapping of string -> string | populates `game_mods_solu`; key order is preserved |
| `Crashgen_Registry` | mapping of crashgen name -> mapping | parsed into `HashMap<String, CrashgenEntryRaw>`; malformed entries are skipped rather than failing the whole file |

`Crashgen_Registry.<name>` entry shape:

| Key | Type / shape | Behavior |
|---|---|---|
| `display_section` | string | display-only header; defaults to empty string |
| `ignore_keys` | sequence of strings | defaults to empty list; used as `crashgen_ignore` fallback |
| `checks` | sequence of strings | defaults to empty list |
| `settings_rules_version` | non-negative integer or numeric string | optional |
| `settings_rules` | mapping | optional; parsed into `CrashgenSettingsRules`; malformed nested rules are skipped/defaulted where possible |

Recognized nested settings-rules keys from current source include:

- `settings_rules.preflight[].action.kind`
- `settings_rules.preflight[].action.bucket`
- `settings_rules.preflight[].action.severity`
- `settings_rules.preflight[].action.message`
- `settings_rules.preflight[].action.fix`

`settings_rules.preflight[].action.bucket` currently accepts:

- `settings` - default bucket when omitted or malformed
- `error_information` - promotes the rendered notice or issue into the autoscan error-information section for bucket-aware callers

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

- If you add or remove consumed keys in `ClassicConfig` or `YamlDataCore`, update this page in the same change.
- If a binding or frontend depends on a new default, note that here even if the Rust API itself does not change.
