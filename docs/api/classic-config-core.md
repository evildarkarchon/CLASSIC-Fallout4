# `classic-config-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-config-core/`](../../ClassicLib-rs/business-logic/classic-config-core).

Crate metadata:

- Crate: `classic-config-core`
- Description: `Pure Rust configuration loading business logic for CLASSIC`

This crate is the Rust-side configuration loader for CLASSIC. It does two related jobs:

1. Load the user/runtime settings YAML used by UI surfaces such as the CLI and TUI.
2. Load the main/game/ignore YAML dataset used by crash-log analysis and related bindings.

Schema reference: [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

It is a pure Rust business-logic crate. It does not own a runtime, UI, or FFI layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- read or persist `CLASSIC Settings.yaml`
- resolve standard CLASSIC YAML file locations
- load the three-file CLASSIC YAML dataset into a single Rust struct
- apply version-registry-backed metadata fallbacks while building config data
- hand configuration data to higher layers such as scanlog orchestration or bindings

Do not use this crate for:

- UI-specific state management
- creating a Tokio runtime
- converting config data into binding-specific wrapper types
- crash-log analysis itself

Those concerns live in related crates such as [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core), [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node), and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge).

---

## Module Map

### `config`

Runtime settings API for CLI/TUI-style application configuration.

- `YamlSource` - enum of standard CLASSIC YAML locations
- `ClassicConfig` - persisted user/runtime settings
- `PathConfig` - nested path settings used by `ClassicConfig`

### `yamldata`

Bulk YAML dataset loader for scanlog/business logic.

- `YamlDataCore` - combined view of Main/Game/Ignore YAML data
- `CrashgenEntryRaw` - raw per-crashgen registry entry extracted from merged game YAML
- `ConfigError` - typed errors for bulk YAML loading/parsing
- `resolve_registry_version_info()` - version-registry lookup helper
- `format_registry_game_version()` - formatting helper for registry versions

### Re-exports from `lib.rs`

- `get_runtime` from [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core)
- `clear_global_yaml_cache` from [`classic-yaml-core`](../../ClassicLib-rs/business-logic/classic-yaml-core)

`clear_global_yaml_cache` is re-exported mainly for tests and cache-sensitive consumers.

---

## Public API Surface

## `YamlSource`

`YamlSource` is the source-of-truth enum for standard CLASSIC YAML file locations.

Variants:

- `Main` -> `CLASSIC Data/databases/CLASSIC Main.yaml`
- `Settings` -> `CLASSIC Settings.yaml`
- `Ignore` -> `CLASSIC Ignore.yaml`
- `Game` -> `CLASSIC Data/databases/CLASSIC {game}.yaml`
- `GameLocal` -> `CLASSIC Data/CLASSIC {game} Local.yaml`
- `Test` -> `tests/test_settings.yaml`
- `Cache` -> `User config dir/CLASSIC/cache.yaml` with application-relative compatibility fallback

Important methods:

- `path(&self, game: &str) -> PathBuf`
- `display_name(&self) -> &'static str`
- `display_name_with_game(&self, game: &str) -> String`
- `load(&self, game: &str) -> anyhow::Result<yaml_rust2::Yaml>`

Contributor notes:

- `YamlSource::Game` and `YamlSource::GameLocal` require a non-empty `game` string and will panic otherwise.
- `YamlSource::Cache` uses the `CLASSIC` base directory for user config/cache paths.
- `load()` reads the full YAML stream, merges documents with `classic-settings-core`, and returns one merged mapping.

## `ClassicConfig`

`ClassicConfig` is the persisted settings struct shared by application surfaces.

Key fields include:

- feature flags such as `fcx_mode`, `show_formid_values`, `stat_logging`, `simplify_logs`
- update settings such as `update_check` and `update_source`
- game mode selection in `game_version`
- UI behavior like `auto_switch_to_results` and `auto_refresh_interval_ms`
- nested paths in `paths: PathConfig`
- per-game FormID DB configuration in `formid_databases: HashMap<String, Vec<PathBuf>>`

Important methods:

- `load_from_yaml(path: &Path) -> anyhow::Result<Self>`
- `save_to_yaml(&self, path: &Path) -> anyhow::Result<()>`
- `load_or_default() -> anyhow::Result<Self>`
- `get_config_path(&self) -> PathBuf`
- `validate_paths(&self) -> anyhow::Result<()>`
- `load_local_yaml_paths(&mut self, game: &str) -> anyhow::Result<()>`
- `save_local_yaml_paths(&self, game: &str) -> anyhow::Result<()>`
- `save_local_yaml_paths_to(&self, path: &Path) -> anyhow::Result<()>`

Behavior worth knowing:

- missing scalar keys mostly fall back to defaults instead of erroring
- `load_or_default()` searches in this order:
  - `CLASSIC Settings.yaml`
  - `CLASSIC_Settings.yaml` (legacy fallback)
  - `dirs::config_dir()/CLASSIC/CLASSIC Settings.yaml`
  - `dirs::config_dir()/CLASSIC/CLASSIC_Settings.yaml`
- `get_config_path()` is best-effort: it prefers the first writable existing settings file in that order, otherwise the preferred `CLASSIC Settings.yaml` target for the resolved application or user config directory, with a final relative fallback only when neither directory can be resolved
- `save_to_yaml()` creates parent directories if needed
- `save_to_yaml()` serializes YAML in `spawn_blocking()` because `YamlEmitter` is not `Send`
- `load_local_yaml_paths()` is non-fatal when `CLASSIC Data/CLASSIC {game} Local.yaml` does not exist
- `save_local_yaml_paths()` creates `CLASSIC Data/CLASSIC {game} Local.yaml` when needed and updates only `Game_Info.Root_Folder_Game` / `Game_Info.Root_Folder_Docs`
- `save_local_yaml_paths_to()` does the same work for an explicit caller-provided local-YAML path, which is useful for frontends that resolve `CLASSIC Data/` outside the process working directory
- field-level YAML shape and default details live in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md)

## `PathConfig`

`PathConfig` stores path-oriented runtime settings.

Fields:

- `ini_folder: Option<PathBuf>`
- `scan_custom: Option<PathBuf>`
- `mods_folder: Option<PathBuf>`
- `game_root: PathBuf`
- `docs_root: Option<PathBuf>`

The default `game_root` is intentionally empty. The source explicitly avoids hardcoded paths.

## `YamlDataCore`

`YamlDataCore` is the main bulk-loaded configuration struct used by analysis-oriented code.

It combines values from:

- `CLASSIC Main.yaml`
- `CLASSIC {game}.yaml`
- `CLASSIC Ignore.yaml`

Representative field groups:

- CLASSIC metadata: `classic_version`, `classic_version_date`, `classic_records_list`
- game metadata: `game_root_name`, `game_version`, `xse_acronym`
- crashgen data: `crashgen_name`, `crashgen_latest_og`, `crashgen_ignore`, `crashgen_registry`
- warnings and UI text: `warn_noplugins`, `warn_outdated`, `autoscan_text`
- ignore lists: `game_ignore_plugins`, `game_ignore_records`, `ignore_list`
- suspect maps and mod DB maps stored as `IndexMap` to preserve YAML key order

Important methods:

- `load_from_yaml_files(yaml_dirs, game, selected_game_version) -> Result<YamlDataCore, ConfigError>`
- `from_yaml_content(main_content, game_content, ignore_content, game, selected_game_version) -> Result<YamlDataCore, ConfigError>`
- `get_crashgen_name(&self) -> &str`
- `get_crashgen_ignore(&self) -> &[String]`
- `get_game_root_name(&self) -> &str`

Two accepted directory layouts for `load_from_yaml_files()`:

- preferred 2-dir API: `[root_dir, data_dir]`
  - expects `CLASSIC Ignore.yaml` under `root_dir`
  - expects `databases/CLASSIC Main.yaml` and `databases/CLASSIC {game}.yaml` under `data_dir`
- legacy 3-dir API: `[main_dir, game_dir, ignore_dir]`

If `yaml_dirs` has any other length, the function returns `ConfigError::InvalidInput`.

## `CrashgenEntryRaw`

`CrashgenEntryRaw` is a transport struct for raw `Crashgen_Registry` data parsed from the game YAML.

Fields:

- `display_section: String`
- `ignore_keys: Vec<String>`
- `checks: Vec<String>`
- `settings_rules_version: Option<u32>`
- `settings_rules: Option<CrashgenSettingsRules>`

This type is intentionally still raw. Downstream crates such as [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) convert it into analysis-layer types.

## `ConfigError`

Typed error enum used by `YamlDataCore` loading APIs.

Variants:

- `InvalidInput(String)`
- `IOError { context, source }`
- `ParseError { context, message }`
- `EmptyDocument(String)`

## Registry Helpers

- `resolve_registry_version_info(main_root_name, selected_game_version) -> Option<VersionInfo>`
- `format_registry_game_version(version: &RegistryGameVersion) -> String`

These helpers bridge the config layer to [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core). They are used both inside this crate and by downstream analysis code.

---

## Loading And Processing Flow

## `ClassicConfig` flow

1. A caller loads `CLASSIC Settings.yaml` with `ClassicConfig::load_from_yaml()` or `load_or_default()`.
2. The crate parses and merges every YAML document in the stream.
3. YAML scalar fields are read with tolerant defaults.
4. Nested `paths` and `formid_databases` are reconstructed.
5. Optional post-processing may call:
   - `load_local_yaml_paths(game)` to fill `game_root` and `docs_root` from merged `GameLocal`
   - `save_local_yaml_paths(game)` or `save_local_yaml_paths_to(path)` to persist detected runtime paths back into `GameLocal`
   - `validate_paths()` to fail fast on missing directories
6. The config can be persisted again with `save_to_yaml()`.

Read/write path policy is defined in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

## `YamlDataCore` flow

1. The caller provides either the 2-dir or legacy 3-dir layout plus `game` and `selected_game_version`.
2. The crate resolves file paths and checks that all three YAML files exist.
3. It reads all three files in parallel with `tokio::join!`.
4. It parses and merges every YAML document from each file.
5. `YamlOperations` from [`classic-yaml-core`](../../ClassicLib-rs/business-logic/classic-yaml-core) extracts nested values.
6. `Crashgen_Registry` is parsed into `HashMap<String, CrashgenEntryRaw>`.
7. Metadata fallbacks are applied from [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core):
   - `crashgen_name`
   - `crashgen_latest_og`
   - `xse_acronym`
   - `game_version`
8. If `Game_Info.CRASHGEN_Ignore` is missing, the crate may fall back to `Crashgen_Registry.<selected|default>.ignore_keys`.

The exact consumed keys and merge rules are documented in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

One subtle rule from the implementation: explicit values already present in `Game_Info` win over registry fallback values, and a present-but-malformed `Game_Info.CRASHGEN_Ignore` path still blocks registry fallback.

---

## Error Handling Model

The crate uses two error styles, depending on API family.

## `ClassicConfig` / `YamlSource`

These APIs return `anyhow::Result<_>` and add human-readable context with `anyhow::Context`.

This is convenient for application-facing code, but it means callers generally match on strings or root causes rather than a dedicated enum.

## `YamlDataCore`

These APIs return `Result<_, ConfigError>`.

Use `ConfigError` when you need to distinguish:

- bad caller input
- missing files / I/O failures
- YAML syntax errors
- empty YAML documents

Malformed optional substructures inside `Crashgen_Registry` are usually not fatal. The parser logs debug messages and skips or defaults malformed pieces instead of rejecting the whole document.

---

## Async And Runtime Notes

This crate performs async file I/O and assumes the shared CLASSIC Tokio runtime model.

- The crate exposes async APIs such as `YamlSource::load()`, `ClassicConfig::load_from_yaml()`, `ClassicConfig::save_to_yaml()`, `ClassicConfig::load_or_default()`, and `YamlDataCore::load_from_yaml_files()`.
- `lib.rs` re-exports `get_runtime` from [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core).
- The crate-level docs explicitly say it should use the shared global runtime rather than creating its own runtime.
- FFI/binding layers in this repo call these async APIs via `get_runtime().block_on(...)` rather than constructing separate runtimes.

That shared-runtime rule matters for contributors: if you extend this crate, keep new async work compatible with the existing runtime model.

---

## Related Crates And Integration Points

- [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core) - shared Tokio runtime via `get_runtime`
- [`classic-yaml-core`](../../ClassicLib-rs/business-logic/classic-yaml-core) - YAML extraction helpers and cache management
- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) - version metadata and fallback resolution
- [`classic-crashgen-settings-core`](../../ClassicLib-rs/business-logic/classic-crashgen-settings-core) - typed crashgen settings rules embedded in `CrashgenEntryRaw`
- [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - converts `YamlDataCore` and `CrashgenEntryRaw` into analysis configuration
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - wraps this crate for JavaScript/TypeScript
- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) - wraps `YamlDataCore` for C++ via the shared runtime

In practice, `classic-config-core` is the data-loading layer between raw YAML files and higher-level analysis/UI/binding code.

---

## Usage Examples

### Load the three-file YAML dataset

This example matches the preferred 2-directory API used in tests and bindings.

```rust
use classic_config_core::YamlDataCore;
use std::path::PathBuf;

# async fn example() -> Result<(), classic_config_core::ConfigError> {
let yaml_dirs = vec![
    PathBuf::from("C:/CLASSIC"),
    PathBuf::from("C:/CLASSIC/CLASSIC Data"),
];

let yaml = YamlDataCore::load_from_yaml_files(
    yaml_dirs,
    "Fallout4".to_string(),
    "auto".to_string(),
)
.await?;

println!("CLASSIC version: {}", yaml.classic_version);
println!("Crashgen: {}", yaml.get_crashgen_name());
println!("Game root name: {}", yaml.get_game_root_name());
# Ok(())
# }
```

Expected file layout for that call:

```text
C:/CLASSIC/CLASSIC Ignore.yaml
C:/CLASSIC/CLASSIC Data/databases/CLASSIC Main.yaml
C:/CLASSIC/CLASSIC Data/databases/CLASSIC Fallout4.yaml
```

### Load or create runtime settings

```rust
use classic_config_core::ClassicConfig;

# async fn example() -> anyhow::Result<()> {
let mut config = ClassicConfig::load_or_default().await?;
config.load_local_yaml_paths("Fallout4").await?;

if let Err(err) = config.validate_paths() {
    eprintln!("Path validation warning: {err}");
}

config.save_to_yaml(&config.get_config_path()).await?;
# Ok(())
# }
```

---

## Contributor Notes And Known Limits

- `ClassicConfig::from_yaml()` and `to_yaml()` are internal helpers, not public API.
- `YamlDataCore` is a broad data container with many public fields; consumers often read fields directly instead of going through accessor methods.
- The source documents a 15-30x speedup claim for parallel loading, but this page does not restate that as a benchmark guarantee.
- the stable YAML shape contract now lives in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md)

If you extend the crate, update this document when you change:

- exported types or re-exports
- accepted directory layout rules
- fallback precedence between YAML and version registry data
- runtime assumptions
- behavior that bindings depend on
