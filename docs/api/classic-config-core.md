# `classic-config-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-config-core/`](../../business-logic/classic-config-core).

Crate metadata:

- Crate: `classic-config-core`
- Description: `Pure Rust configuration loading business logic for CLASSIC`

This crate loads curated CLASSIC YAML Data and generic non-User-Settings YAML sources. Canonical persisted user choices for every maintained interface are owned exclusively by `classic-user-settings-core`.

Schema reference: [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

It is a pure Rust business-logic crate. It does not own a runtime, UI, or FFI layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- resolve standard CLASSIC YAML file locations
- load the three-file CLASSIC YAML dataset into a single Rust struct
- load three explicitly identified YAML Data files deterministically for tests and tooling
- apply version-registry-backed metadata fallbacks while building config data
- hand configuration data to higher layers such as scanlog orchestration or bindings
- load generic Main, Game, Game Local, Ignore, Test, and Cache YAML sources

Do not use this crate for:

- UI-specific state management
- creating a Tokio runtime
- converting config data into binding-specific wrapper types
- crash-log analysis itself
- locating, defaulting, validating, serializing, or persisting `CLASSIC Settings.yaml`

Those concerns live in related crates such as [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), [`classic-node`](../../node-bindings/classic-node), and [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

---

## Module Map

### `yaml_source`

Generic non-User-Settings CLASSIC YAML locations.

- `YamlSource` - enum of Main, Ignore, Game, Game Local, Test, and Cache locations

### `game_local`

Independent persistence for runtime-discovered paths in a caller-selected Game Local YAML document.

- `persist_game_local_paths(path, game_root, docs_root)` - root-reexported writer that updates supplied Game Local path keys without opening User Settings

### `yamldata`

Bulk YAML dataset loader for scanlog/business logic.

- `YamlDataCore` - combined view of Main/Game/Ignore YAML data
- `CrashgenEntryRaw` - raw per-crashgen registry entry extracted from merged game YAML
- `ConfigError` - typed errors for bulk YAML loading/parsing
- `resolve_registry_version_info()` - version-registry lookup helper
- `format_registry_game_version()` - formatting helper for registry versions

### `explicit_yaml_data`

Typed, mutation-free loading for caller-selected Main, game, and Local Ignore YAML Data files.

- `ExplicitYamlDataRequest` - the three exact paths, typed game identity, and existing game-version mode
- `ExplicitYamlDataSnapshot` - immutable parsed YAML Data backed by the exact retained source bytes
- `YamlDataContentIdentity` - SHA-256 and byte length derived from one retained file
- `GameDataRole` - the registered YAML Data role selected from `GameId`
- `ExplicitYamlDataRole` - Main, game, or Local Ignore error attribution
- `ExplicitYamlDataLoadError` - typed unsupported-game, read, decoding, parse, and role-validation failures
- `load_explicit_yaml_data()` - async entry point for the deterministic explicit-file operation

### `installed_yaml_data`

Config-owned selection and immutable loading of Installed YAML Data.

- `InstalledYamlDataInspectionRequest` - one installation root plus typed game identity
- `InstalledYamlDataInspection` / `InspectedYamlDataFile` - independently selected Main/game provenance, schema, and exact-byte identity
- `InstalledYamlDataDiagnostic` / `InstalledYamlDataDiagnosticKind` - structured cache, rejected-candidate, and Local Ignore generation/recovery attribution
- `InstalledYamlDataInspectionError` - typed unsupported-game or no-usable-source terminal failure
- `inspect_installed_yaml_data()` - production inspection entry point used by first-party update freshness
- `inspect_installed_yaml_data_with_env()` - deterministic Rust tooling seam for cache-environment injection
- `InstalledYamlDataLoadRequest` - one installation root, typed game identity, and separate game-version mode
- `InstalledYamlDataLoadOutcome::{Ready, LocalIgnoreRecoveryRequired}` - separates usable snapshots and expected malformed-Local-Ignore decisions from fatal failures
- `InstalledYamlDataSnapshot` - parsed Main/game data plus existing, generated, or operation-scoped-empty Local Ignore behavior backed by retained exact bytes
- `LocalIgnoreRecoveryPlan` - immutable retained selection/default/malformed-file proposal with a consuming, mutation-free `proceed_without_ignore()` decision
- `LocalIgnoreYamlDataState::{Existing, Generated, ProceedWithoutIgnore}` - distinguishes preserved user content, successful initialization, and operation-scoped empty ignores
- `InstalledYamlDataLoadError` - typed fatal selection, I/O, default, publication, and parsed-data failures
- `load_installed_yaml_data()` - production installed snapshot entry point
- `load_installed_yaml_data_with_env()` - deterministic Rust test/tooling seam for cache-environment injection

### Re-exports from `lib.rs`

- `get_runtime` from [`classic-shared-core`](../../foundation/classic-shared-core)
- `clear_global_yaml_cache` from [`classic-settings-core`](../../business-logic/classic-settings-core) (historical note: that owner absorbed the former `classic-yaml-core` crate in v9.1.0 Phase 1)
- crashgen rule-model and Crashgen Expectation Parser types/functions from `crashgen_rules` and `crashgen_expectation_parser`
- Installed YAML Data request/result/snapshot/provenance/diagnostic/error types and loading/inspection functions from `installed_yaml_data`

`clear_global_yaml_cache` is re-exported mainly for tests and cache-sensitive consumers.

---

## Public API Surface

## `YamlSource`

`YamlSource` identifies generic CLASSIC YAML file locations that are not User Settings. `classic-user-settings-core` separately owns the source and root-relative location of `CLASSIC Settings.yaml`.

Variants:

- `Main` -> `CLASSIC Data/databases/CLASSIC Main.yaml`
- `Ignore` -> `CLASSIC Ignore.yaml`
- `Game` -> `CLASSIC Data/databases/CLASSIC {game}.yaml`; `Fallout4VR` resolves to the shared `CLASSIC Fallout4.yaml`
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

## Game Local Path Persistence

`classic_config_core::persist_game_local_paths(path, game_root, docs_root)` writes runtime-discovered paths to an explicit Game Local YAML path. `game_root` and `docs_root` are independent `Option<&Path>` updates: `None` leaves the corresponding key unchanged, and supplying neither path is a no-op that does not create a file.

The writer creates parent directories when needed, merges an existing multi-document YAML stream, updates only `Game_Info.Root_Folder_Game` and `Game_Info.Root_Folder_Docs`, and preserves unrelated content. It never reads or writes `CLASSIC Settings.yaml`.

Binding adapters expose the same operation as CXX `save_local_yaml_paths(...)`, Node `persistGameLocalPaths(...) -> Promise<void>`, and Python `persist_game_local_paths(...) -> None`. Each adapter only converts optional path values and delegates document behavior to the Rust writer.

## Explicit YAML Data Loading

`load_explicit_yaml_data(request) -> Result<ExplicitYamlDataSnapshot, ExplicitYamlDataLoadError>` is the typed tooling and test seam for loading exactly three caller-selected files. It is deliberately separate from Installed YAML Data selection: the caller supplies each complete file identity rather than an installation root or positional directory vector.

`ExplicitYamlDataRequest` contains:

| Field | Meaning |
|---|---|
| `main_path: PathBuf` | exact Main YAML Data file |
| `game_path: PathBuf` | exact game YAML Data file |
| `ignore_path: PathBuf` | exact Local Ignore YAML Data file |
| `game: GameId` | typed game identity used to select a registered YAML Data role |
| `selected_game_version: String` | existing Version Registry selection mode; it affects metadata fallback, not file selection |

The current registered `GameDataRole` is `Fallout4`. Both `GameId::Fallout4` and `GameId::Fallout4VR` select that shared role, so they use `Fallout4`-keyed data such as `CLASSIC_Ignore_Fallout4`. `GameId::Skyrim` and `GameId::Starfield` have no registered YAML Data role in this client and return `ExplicitYamlDataLoadError::UnsupportedGame` before any requested path is read.

### Snapshot And Content Identity

`ExplicitYamlDataSnapshot` privately retains the exact bytes read for all three roles and exposes:

- `yaml_data() -> &YamlDataCore` - the combined model parsed and built from those retained bytes
- `game() -> GameId` - the caller's typed game identity
- `game_data_role() -> GameDataRole` - the registered role used for keyed parsing and validation
- `main_identity()`, `game_identity()`, and `ignore_identity()` - identities of the retained role bytes

Each `YamlDataContentIdentity` reports `sha256_hex()` and `byte_len()`. The loader reads each requested path once, then derives UTF-8 decoding, merged YAML, role validation, model construction, SHA-256, and byte length from the resulting owned bytes. Replacing or deleting a source path after loading therefore cannot change either the snapshot's parsed data or its identities.

The snapshot does not expose raw YAML documents or its retained byte buffers as general-purpose APIs. Consumers receive the typed `YamlDataCore` view and content identities rather than a path-backed live view.

### Explicit Role Validation

All three files must be valid UTF-8 YAML streams that satisfy the repository's multi-document merge rules. Main and game are shippable roles, so the loader extracts `schema_version` and checks it against config-owned `client_schemas::MAIN_YAML` or `client_schemas::GAME_FALLOUT4_YAML`; callers cannot supply a compatibility range.

After schema compatibility succeeds, the implemented semantic checks are:

- Main requires a `CLASSIC_Info` mapping whose non-empty string `version` satisfies the schema-2 release-SemVer shape: optional leading `v`/`V`, no `CLASSIC ` display prefix, prerelease suffix, or build metadata. Present `version_date`, Fallout 4 autoscan text, and `catch_log_records` values must retain the scalar or string-list shapes consumed by the typed model.
- Game requires a `Game_Info` mapping with a non-empty string `Main_Root_Name`; after normalization to lowercase ASCII alphanumeric characters, that value must equal `fallout4` and identify the registered Fallout 4 data role. Every consumed scalar, string-list, `Mods_CONF`, `Mods_CORE`, `Mods_FREQ`, `Mods_SOLU`, `Crashlog_Error_Check`, `Crashlog_Stack_Check`, and `Crashgen_Registry` value is validated before model construction, including nested criteria, count rules, registry metadata, and settings-rule diagnostics, so malformed entries cannot be silently discarded or defaulted by the general production parser.
- Local Ignore requires `CLASSIC_Ignore_Fallout4` to be a sequence containing only strings. An empty sequence is valid; a missing key, scalar, mapping, null, or sequence containing a non-string is malformed.

The remaining keys are interpreted by `YamlDataCore` according to the schema and fallback rules below. Optional fields remain optional, but any consumed field that is present must have the strict shape and semantics expected by the typed model.

### No Installed Policy Or Mutation

Explicit loading performs no source selection beyond the three supplied paths. It never:

- resolves an installation layout, bundled-data directory, platform cache, or `YamlSource`
- consults or promotes a `.prev` cache sibling
- retries with a bundled, cached, or alternate file
- creates a missing Local Ignore file
- generates, repairs, resets, replaces, or backs up any selected file
- deletes or rewrites a rejected file

A missing or rejected explicit file is returned as a typed failure for that exact role and path. Installed selection, recovery, and fallback policy must not be reconstructed around this operation.

### `ExplicitYamlDataLoadError`

| Variant | Meaning |
|---|---|
| `UnsupportedGame { game }` | the typed game has no registered YAML Data role; no paths are read |
| `Read { role, path, source }` | the exact role path could not be read |
| `InvalidUtf8 { role, path, source }` | retained bytes are not valid UTF-8 |
| `Parse { role, path, message }` | the UTF-8 content is not a valid mergeable YAML stream |
| `InvalidRoleData { role, path, reason }` | parsed YAML fails schema compatibility or semantic role validation |

`ExplicitYamlDataRole::{Main, Game, LocalIgnore}` keeps file-specific failures attributable without parsing messages. `reason` and `message` are human-readable diagnostic details; callers should branch on the typed variant and role.

## Installed YAML Data Inspection

`inspect_installed_yaml_data(InstalledYamlDataInspectionRequest { installation_root, game })` is the side-effect-limited Installed YAML Data seam used by the first-party update channel. It inspects only update-eligible Main and selected-game YAML Data; it never reads, creates, repairs, or validates Local Ignore YAML Data.

Main and game select independently. For each role, config core tries the canonical per-user updated candidate first. A `.prev` sibling participates only when the canonical path is absent, and inspection reads it without promotion. A present canonical candidate that fails UTF-8, parsing, config-owned schema compatibility, or strict role validation is preserved, reported as a structured diagnostic, and followed by bundled fallback; it never causes `.prev` selection. If no usable candidate remains, `InstalledYamlDataInspectionError::NoUsableSource` identifies the failed role and retains the diagnostics. `UnsupportedGame` is returned before path or cache resolution; Fallout 4 VR maps to the shared Fallout 4 role.

Each `InspectedYamlDataFile` exposes its `InstalledYamlDataRole`, `InstalledYamlDataProvenance::{Updated, Previous, Bundled}`, compatible `SchemaVersion`, and `YamlDataContentIdentity`. Candidate bytes are read once, then UTF-8 decoding, YAML parsing, semantic validation, schema extraction, SHA-256, and byte length all use that same owned buffer. `InstalledYamlDataDiagnostic` supplies optional role/candidate/path attribution, a typed `InstalledYamlDataDiagnosticKind`, and an actionable message. Cache-root resolution failure is a structured `CacheUnavailable` diagnostic and leaves bundled data eligible.

`inspect_installed_yaml_data_with_env` is the deterministic Rust test/tooling form. Its environment callback controls cache-root resolution without process-environment mutation; bundled paths still derive only from the explicit installation root.

## Installed YAML Data Loading

`load_installed_yaml_data(InstalledYamlDataLoadRequest { installation_root, game, selected_game_version })` loads an immutable runtime snapshot and initializes missing user-owned `CLASSIC Data/CLASSIC Ignore.yaml` when necessary. `game` selects the registered YAML Data role; the separate `selected_game_version` string retains its existing Version Registry metadata interpretation and does not affect file selection.

Main and game use the same private selector as [`inspect_installed_yaml_data`](#installed-yaml-data-inspection), including independent updated/previous/bundled precedence, config-owned compatibility, strict role validation, and structured fallback diagnostics. The selected bytes and parsed YAML documents are retained privately. Existing Local Ignore is read and retained byte-for-byte; valid content is used directly, while malformed content becomes expected recovery result data and is never rewritten automatically.

When Local Ignore is absent, config core extracts `CLASSIC_Info.default_ignorefile` from the already retained selected Main document. The scalar must be a non-empty string whose embedded YAML parses and satisfies the selected Local Ignore role contract; this validation finishes before any staging file is created. Config core then writes and syncs a same-directory temporary file and atomically publishes the complete bytes with no-clobber semantics. If another caller wins the publication race, its canonical file is preserved. Every caller rereads `CLASSIC Ignore.yaml` after the publish attempt, so parsing, identity, and the returned snapshot use the authoritative winner rather than a losing caller's default.

The successful publisher returns `LocalIgnoreYamlDataState::Generated` and appends a path-attributed `InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated` diagnostic. Its role and candidate are absent because Local Ignore is not an update-eligible Main/game candidate. A concurrent loser returns `Existing` for the winner it reread and does not claim generation.

A valid installation returns `InstalledYamlDataLoadOutcome::Ready(InstalledYamlDataSnapshot)`. The snapshot exposes:

- the parsed `YamlDataCore` and requested typed game;
- the registered shared game-data role;
- Main and game provenance, schema versions, SHA-256 identities, and byte lengths through `main()` and `game_file()`;
- `LocalIgnoreYamlDataState::{Existing, Generated}` plus the exact authoritative Local Ignore SHA-256 identity and byte length (reset results additionally use `ResetToDefault`);
- structured cache, rejected-candidate, and Local Ignore generation/reset diagnostics.

Raw retained bytes and parsed YAML documents are not public APIs, and the snapshot's custom `Debug` output includes metadata only. Replacing any selected path after loading cannot change the snapshot's parsed data or identities.

If retained Local Ignore bytes are invalid UTF-8, malformed YAML, or invalid for the selected game-data role, loading instead returns `InstalledYamlDataLoadOutcome::LocalIgnoreRecoveryRequired(LocalIgnoreRecoveryPlan)`. The immutable plan retains the selected Main/game bytes and metadata, selected game-version mode, selected-Main default state, malformed path and exact-byte identity, and all selection plus malformed-content diagnostics. Valid defaults expose an identity; invalid or unavailable defaults remain explicitly unavailable for a future reset decision but never block the non-mutating Proceed Without Ignore path. Its custom `Debug` output exposes metadata only.

`LocalIgnoreRecoveryPlan::proceed_without_ignore()` consumes the plan and returns the already prepared snapshot without selection, rereads, generation, backup, or writes. The snapshot uses `LocalIgnoreYamlDataState::ProceedWithoutIgnore`, exposes the malformed installed identity for attribution, and supplies an empty `ignore_list` only to that in-memory operation. Main and game still come from the retained selection even if their paths changed while the caller decided. Because the malformed file is unchanged, a later installed load returns recovery required again.

`LocalIgnoreRecoveryPlan::reset_to_default()` is the consuming, synchronous reset decision and the explicit non-interruptible critical section used by later scan cancellation coordination. It acquires the config-owned installation-root `.classic-local-ignore-reset.lock`, rereads and byte-compares the canonical file with the malformed bytes retained by the plan, and returns `LocalIgnoreResetOutcome::Conflict` with expected/current identities when the file or its containing directory changed or disappeared. Conflict before backup publishes no backup or replacement. The zero-byte lock file is intentionally retained so concurrent processes never race lock-file deletion.

For an unchanged file, reset publishes the malformed bytes at a uniquely owned `CLASSIC Backup/YAML Data/Local Ignore/CLASSIC Ignore.yaml.<sha256>.<unique>.bak` path. It synchronizes the complete staging file, uses a no-clobber durable final-name move (`fsync`-backed directory publication on Unix and write-through move on Windows), and rereads the owned backup for byte-exact verification; pre-existing regular files, symlinks, and directories are never reused as proof. It then stages and synchronizes the defaults retained from the selected Main snapshot, rechecks the canonical bytes immediately beside the atomic replacement, and replaces the canonical path without creating `.prev` rollback state. A late conflict retains the verified backup and returns its path. `LocalIgnoreResetResult` returns the reset-ready retained snapshot, canonical and backup paths, malformed/backup/replacement identities, `LocalIgnoreYamlDataState::ResetToDefault`, and an `InstalledYamlDataDiagnosticKind::LocalIgnoreReset` diagnostic. No Main, game, or default path is reselected or reopened.

`LocalIgnoreResetError` distinguishes unavailable retained defaults, lock/read/backup-directory failures, backup verification, and backup or replacement publication. Publication failures carry `LocalIgnoreResetPublicationStage::{Create, Write, Flush, Sync, Publish}`. Every fallible backup, verification, and replacement preparation step completes before atomic replacement; failure leaves the original canonical bytes authoritative, while a replacement-stage failure may retain the already verified backup. There is deliberately no post-replacement fallible verification that could report failure after the original stopped being authoritative.

`InstalledYamlDataLoadError::UnsupportedGame` is returned before cache or installation file access. `NoUsableSource { role, diagnostics }` identifies a required Main or game role after every allowed candidate is exhausted. Unrecoverable Local Ignore reads remain `LocalIgnoreRead`; malformed content is not a fatal error. `LocalIgnoreDefaultInvalid` rejects an unusable selected-Main template only when a missing Local Ignore must be generated; it does not replace a recovery-required outcome for an existing malformed file. `LocalIgnoreCreate` reports staging or no-clobber publication failure, and `InvalidSelectedData` covers an invalid final projection into `YamlDataCore`. No failure publishes a partial snapshot.

`load_installed_yaml_data_with_env` injects only cache-environment lookup for isolated tests and tooling. It never consults the developer's process cache when the caller supplies an isolated environment callback; bundled and Local Ignore paths always derive from the request's one installation root.

## `YamlDataCore`

`YamlDataCore` is the main bulk-loaded configuration struct used by analysis-oriented code.

It combines values from:

- `CLASSIC Main.yaml`
- `CLASSIC {game}.yaml` (`Fallout4VR` uses `CLASSIC Fallout4.yaml`)
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
  - expects `databases/CLASSIC Main.yaml` and `databases/CLASSIC {game}.yaml` under `data_dir`; Fallout 4 VR uses the Fallout 4 filename and keyed data identity
- legacy 3-dir API: `[main_dir, game_dir, ignore_dir]`

If `yaml_dirs` has any other length, the function returns `ConfigError::InvalidInput`.

## `CrashgenEntryRaw`

`CrashgenEntryRaw` is a transport struct for raw `Crashgen_Registry` data parsed from the game YAML.

Fields:

- `display_section: String`
- `ignore_keys: Vec<String>`
- `checks: Vec<String>` (deprecated inert compatibility metadata)
- `settings_rules_version: Option<u32>`
- `settings_rules: Option<CrashgenSettingsRules>`

This type is intentionally still raw. Downstream crates such as [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) convert it into analysis-layer types. `settings_rules` carries Crashgen Expectations; `checks` is accepted for YAML compatibility but does not drive current scan-time behavior.

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

These helpers bridge the config layer to [`classic-version-registry-core`](../../business-logic/classic-version-registry-core). They are used both inside this crate and by downstream analysis code.

---

## Loading And Processing Flow

### Explicit YAML Data flow

1. Validate that the request's `GameId` has a registered `GameDataRole`; unsupported games fail before file I/O.
2. Read the exact Main, game, and Local Ignore paths once each, concurrently on the shared Tokio runtime.
3. Retain each byte buffer and derive its SHA-256 and byte length.
4. Decode and merge each YAML stream from its retained bytes.
5. Enforce config-owned Main/game schema compatibility and semantic validation for all three roles.
6. Build one `YamlDataCore` from the validated documents using the registered data key and caller-supplied game-version mode.
7. Return an immutable snapshot that owns the parsed model, registered role, retained bytes, and their identities.

## Game Local persistence flow

1. A caller supplies an explicit Game Local YAML path and either or both runtime path updates.
2. `persist_game_local_paths()` returns without I/O when neither update is supplied; otherwise it creates the parent directory and merges only the Game Local document when it already exists.
3. The supplied path keys are updated and unrelated Game Local keys are preserved before the document is saved.

This flow is independent from User Settings and never opens or saves that document.

## `YamlDataCore` flow

1. The caller provides either the 2-dir or legacy 3-dir layout plus `game` and `selected_game_version`.
2. The crate resolves file paths and checks that all three YAML files exist.
3. It reads all three files in parallel with `tokio::join!`.
4. It parses and merges every YAML document from each file.
5. `YamlOperations` from [`classic-settings-core`](../../business-logic/classic-settings-core) extracts nested values.
6. `Crashgen_Registry` is parsed into `HashMap<String, CrashgenEntryRaw>`.
7. Metadata fallbacks are applied from [`classic-version-registry-core`](../../business-logic/classic-version-registry-core):
   - `crashgen_name`
   - `crashgen_latest_og`
   - `xse_acronym`
   - `game_version`
8. If `Game_Info.CRASHGEN_Ignore` is missing, the crate may fall back to `Crashgen_Registry.<selected|default>.ignore_keys`.

The exact consumed keys and merge rules are documented in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md).

One subtle rule from the implementation: explicit values already present in `Game_Info` win over registry fallback values, and a present-but-malformed `Game_Info.CRASHGEN_Ignore` path still blocks registry fallback.

---

## Error Handling Model

The crate uses distinct error styles depending on API family.

### Explicit YAML Data

`load_explicit_yaml_data()` returns `ExplicitYamlDataLoadError`. It preserves the typed game or file role and exact requested path wherever applicable, and it separates filesystem, UTF-8, YAML parsing, and role-validation failures. Model-construction errors originate in consumed Game data and are therefore returned as Game-role validation failures rather than as an unattributed category. The loader does not hide a failed explicit source behind fallback.

## `YamlSource`

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

- The crate exposes async APIs such as `YamlSource::load()` and `YamlDataCore::load_from_yaml_files()`.
- `lib.rs` re-exports `get_runtime` from [`classic-shared-core`](../../foundation/classic-shared-core).
- The crate-level docs explicitly say it should use the shared global runtime rather than creating its own runtime.
- FFI/binding layers in this repo call these async APIs via `get_runtime().block_on(...)` rather than constructing separate runtimes.

That shared-runtime rule matters for contributors: if you extend this crate, keep new async work compatible with the existing runtime model.

---

## Related Crates And Integration Points

- [`classic-shared-core`](../../foundation/classic-shared-core) - shared Tokio runtime via `get_runtime`
- [`classic-settings-core`](../../business-logic/classic-settings-core) - YAML extraction helpers, mtime-aware file cache, and settings-cache management (historical note: this owner absorbed the former `classic-yaml-core` crate in v9.1.0 Phase 1)
- [`classic-version-registry-core`](../../business-logic/classic-version-registry-core) - version metadata and fallback resolution
- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - converts `YamlDataCore` and `CrashgenEntryRaw` into analysis configuration, and evaluates the crashgen rule model through `CrashgenSettingsAnalyzer`
- [`classic-node`](../../node-bindings/classic-node) - wraps this crate for JavaScript/TypeScript
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - wraps `YamlDataCore` for C++ via the shared runtime

In practice, `classic-config-core` is the data-loading layer between raw YAML files and higher-level analysis/UI/binding code.

---

## Usage Examples

### Load three exact tooling files

```rust
use classic_config_core::{ExplicitYamlDataRequest, load_explicit_yaml_data};
use classic_shared_core::GameId;
use std::path::PathBuf;

# async fn example() -> Result<(), classic_config_core::ExplicitYamlDataLoadError> {
let snapshot = load_explicit_yaml_data(ExplicitYamlDataRequest {
    main_path: PathBuf::from("fixtures/CLASSIC Main.yaml"),
    game_path: PathBuf::from("fixtures/CLASSIC Fallout4.yaml"),
    ignore_path: PathBuf::from("fixtures/CLASSIC Ignore.yaml"),
    game: GameId::Fallout4VR,
    selected_game_version: "VR".to_string(),
})
.await?;

assert_eq!(snapshot.yaml_data().classic_version, "9.1.0");
println!("Main SHA-256: {}", snapshot.main_identity().sha256_hex());
# Ok(())
# }
```

The paths may use arbitrary fixture or tooling filenames. Their basenames and directories do not participate in role selection; the request fields declare each role, and the document content must validate for that role.

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

## Contributor Notes And Known Limits

- `YamlDataCore` is a broad data container with many public fields; consumers often read fields directly instead of going through accessor methods.
- The source documents a 15-30x speedup claim for parallel loading, but this page does not restate that as a benchmark guarantee.
- the stable YAML shape contract now lives in [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md)

If you extend the crate, update this document when you change:

- exported types or re-exports
- explicit request, snapshot, identity, role-validation, or mutation-free behavior
- accepted directory layout rules
- fallback precedence between YAML and version registry data
- runtime assumptions
- behavior that bindings depend on

---

## Crashgen rule model

The crashgen rule model lives in `classic-config-core::crashgen_rules` (module `src/crashgen_rules.rs`, absorbed from the former `classic-crashgen-settings-core` crate in v9.1.0 Phase 2). `lib.rs` re-exports the full rule-model surface via `pub use crashgen_rules::*;`, so downstream callers use the flat `classic_config_core::` path.

This section defines the shared Rust rule model used for crashgen settings validation and documents the core evaluator that higher layers call. It is pure business-logic code with no YAML loading, report formatting, UI, FFI, or Tokio runtime ownership — those concerns live in the config loaders, scanlog/scangame orchestrators, and binding layers. The model is the sole behavioral source for per-crashgen expectations; legacy `Crashgen_Registry.*.checks` metadata and scanlog `CheckId` routing are not behavioral inputs.

### Purpose and scope

Use the crashgen rule model when you need to:

- represent crashgen settings rules as typed Rust data
- parse Crashgen Expectation payloads from YAML Data or binding adapters into typed Rust data
- evaluate those rules against installed plugins, section-aware settings, config layout facts, and optional crashgen version data
- share one rule model across config loading, scanlog analysis, TOML/config validation, and bindings
- build or transform `CrashgenSettingsRules` values in tests, registry builders, or binding adapters

Do not use this module for parsing TOML settings files, formatting final autoscan reports, deciding game-version family ownership for scan-time config building, or creating a Tokio runtime. Those live in sibling modules and the [`classic-scanlog-core`](classic-scanlog-core.md) / [`classic-scangame-core`](classic-scangame-core.md) crates.

### Rule model types

- `CrashgenSettingsRules` - top-level rules block with `version`, `preflight`, and `checks`
- `CrashgenSettingsSnapshot` - section-aware setting values used by rule evaluation
- `PreflightRule` and `PreflightAction` - early rules that emit notices/issues before setting checks run
- `CheckRule` - one setting expectation with target metadata, predicate, and messages
- `RuleTarget` - section/key/value-type metadata for a setting check
- `RuleMessages` - fail/fix/pass message templates
- `Predicate` - condition tree used by both preflight and check rules
- `ExpectedValue` and `TargetValueType` - typed expectation model

### Evaluation types

- `EvaluationContext` - caller-provided facts used during evaluation
- `EvaluationOutcome` - one emitted notice, issue, or success
- `EvaluationResult` - ordered outcomes plus `skip_remaining`
- `OutcomeKind` - `Notice`, `Issue`, or `Success`

### Supporting enums

- `RuleSeverity` - `Info`, `Warning`, `Error`
- `PreflightActionKind` - `NoticeAndSkipRemaining`, `Notice`, `Issue`
- `ConfigLayout` - `Og`, `Vr`, `Unknown`
- `AutoscanReportPlacement` - `Settings` (default) or `ErrorInformation` (promoted destination)
- `RuleReportBucket` - deprecated compatibility alias for `AutoscanReportPlacement`

### Main function

- `evaluate_rules(rules, context) -> EvaluationResult`

### Crashgen Expectation Parser

`crashgen_expectation_parser` owns the carrier-neutral parsing seam for Crashgen Expectations. YAML loading, Node bindings, and Python bindings translate their local carrier shape into a JSON-like `serde_json::Value`, then call:

- `parse_crashgen_expectations(document, default_version) -> CrashgenExpectationParseResult`

`CrashgenExpectationParseResult` contains:

- `rules: Option<CrashgenSettingsRules>` - `None` only when the root payload is not a mapping
- `diagnostics: Vec<CrashgenExpectationParseDiagnostic>` - non-fatal parse diagnostics for skipped/defaulted fields

Parser behavior is intentionally tolerant. Malformed optional values are defaulted, malformed individual rules are skipped, and the parser returns diagnostics rather than failing the whole Crashgen Registry entry. `default_version` carries the YAML sibling `settings_rules_version`; a `version` value inside the parsed document wins when present.

Canonical document field names follow YAML Data: `placement` for Autoscan Report Placement and `target.type` for target value type. Compatibility aliases `bucket` and `target.value_type` are still accepted. Precedence is valid canonical field first, then valid compatibility alias, then the historical default.

### `CrashgenSettingsRules`

Top-level model shared between config loading and validation layers. Fields:

- `version: u32`
- `preflight: Vec<PreflightRule>`
- `checks: Vec<CheckRule>`

The module does not interpret `version` beyond storing it — today it is schema metadata carried from upstream loaders.

### `Predicate`

Condition tree used to decide whether a rule applies. Variants:

- `Always`
- `PluginAny(Vec<String>)`
- `ConfigLayoutIs(ConfigLayout)`
- `CrashgenVersionLt((u32, u32, u32))`
- `All(Vec<Predicate>)`
- `Any(Vec<Predicate>)`
- `Not(Box<Predicate>)`

Source-visible behavior:

- `PluginAny` compares against `EvaluationContext.installed_plugins` after trimming and lowercasing the predicate entries at evaluation time
- `ConfigLayoutIs` is strict equality against the caller-provided `ConfigLayout`
- `CrashgenVersionLt` returns `false` when `crashgen_version` is `None`, so callers that cannot provide a real detected version safely skip version-gated rules
- `All`, `Any`, and `Not` compose recursively

### `EvaluationContext`

The only input to the evaluator besides the rules. Fields:

- `crashgen_name: String`
- `display_section: String`
- `installed_plugins: HashSet<String>`
- `settings: CrashgenSettingsSnapshot`
- `config_layout: ConfigLayout`
- `crashgen_version: Option<(u32, u32, u32)>`

Contributor notes:

- `installed_plugins` is expected to contain lowercase DLL/plugin names; downstream callers such as scanlog build it that way
- `settings` is section-aware; `evaluate_rules()` looks up by `RuleTarget.section` and `RuleTarget.key`
- `CrashgenSettingsSnapshot` normalizes section names by trimming whitespace, accepting either `Compatibility` or `[Compatibility]`, and comparing case-insensitively after removing one bracket pair
- setting keys are trimmed but otherwise exact and case-sensitive
- unscoped settings do not satisfy sectioned Crashgen Expectations; missing targeted sections or settings produce no outcome

### `PreflightRule` and `PreflightAction`

Preflight rules run before check rules. Fields:

- `PreflightRule`: `id`, `when`, `action`
- `PreflightAction`: `kind`, `bucket`, `severity`, `message`, `fix`

`PreflightAction.bucket` is a deprecated compatibility field name that carries an `AutoscanReportPlacement` value. New YAML and binding payloads should call this concept `placement`; the Rust field name stays `bucket` for one transition.

`AutoscanReportPlacement` meanings:

- `Settings` - default settings-related destination used by ordinary checks and preflight notices
- `ErrorInformation` - promoted destination for notices or issues that callers want to render under `Error Information`

`PreflightActionKind` meanings:

- `NoticeAndSkipRemaining` - emit a notice and stop before all remaining checks
- `Notice` - emit a notice and continue
- `Issue` - emit an issue and continue

### `CheckRule`

Models one expected setting value. Fields: `id`, `target: RuleTarget`, `when: Predicate`, `expect: ExpectedValue`, `messages: RuleMessages`, `severity: RuleSeverity`.

Important behavior:

- a check rule only runs when its predicate is true
- if the target key is missing from `context.settings`, the rule is skipped silently
- a failed expectation emits an `Issue`
- a passing expectation emits a `Success` only when `messages.pass` is present

### `ExpectedValue`, `TargetValueType`, and value matching

Supported expected values: `ExpectedValue::Bool(bool)`, `ExpectedValue::Int(i64)`, `ExpectedValue::String(String)`.

Supported target types: `TargetValueType::Bool`, `TargetValueType::Int`, `TargetValueType::String`.

Matching behavior from `value_matches()`:

- bool parsing accepts `true/1/yes/on` and `false/0/no/off`
- int parsing trims and parses as `i64`
- string comparisons compare trimmed current values to the expected string
- if `target.value_type` and `expect` differ, the evaluator still falls back to matching on the `ExpectedValue` variant instead of erroring

### `EvaluationOutcome` and `EvaluationResult`

`EvaluationOutcome` is the emitted result unit. Fields: `id`, `kind`, `bucket`, `severity`, `message`, `fix`, `section`, `setting`, `expected`, `actual`. `EvaluationOutcome.bucket` is the same deprecated compatibility field name carrying an `AutoscanReportPlacement` value.

`EvaluationResult` contains:

- `outcomes: Vec<EvaluationOutcome>` in evaluation order
- `skip_remaining: bool`

There is no separate summary or error channel. Callers interpret `outcomes` directly.

### Parse helpers on enums

- `RuleSeverity::parse(&str) -> Option<RuleSeverity>`
- `ConfigLayout::parse(&str) -> Option<ConfigLayout>`
- `TargetValueType::parse(&str) -> Option<TargetValueType>`
- `PreflightActionKind::parse(&str) -> Option<PreflightActionKind>`
- `AutoscanReportPlacement::parse(&str) -> Option<AutoscanReportPlacement>`
- `RuleReportBucket::parse(&str) -> Option<AutoscanReportPlacement>` through the deprecated alias

These return `None` for unsupported strings. Useful in loaders and binding adapters, but they do not report detailed parse errors.

### Rule evaluation flow

The source-visible evaluation order:

1. Start with an empty `EvaluationResult`.
2. Evaluate all `preflight` rules in declaration order.
3. For each matching preflight rule: render `message` and optional `fix`, emit a `Notice` or `Issue` outcome based on `PreflightActionKind`, copy `PreflightAction.bucket` / Autoscan Report Placement into the emitted `EvaluationOutcome`.
4. If a preflight action is `NoticeAndSkipRemaining`, set `skip_remaining = true` and return immediately.
5. Evaluate all `checks` in declaration order.
6. For each matching check rule: look up `context.settings[rule.target.key]`, skip the rule if the key is absent, compare the current value to `expect`, emit an `Issue` on mismatch, emit a `Success` on match only when `messages.pass` exists, emit `AutoscanReportPlacement::Settings` for those check outcomes.
7. Return the ordered `EvaluationResult`.

Template rendering is intentionally small in scope. `apply_template()` only replaces `{crashgen_name}`, `{display_section}`, and `{setting}`. If `display_section` is empty, the evaluator substitutes `[Compatibility]`.

### Error handling model for the rule evaluator and parser

The rule evaluator does not expose a dedicated error enum and `evaluate_rules()` is intentionally infallible. Contributor-facing implications:

- enum parse helpers return `Option<_>`, not `Result<_>`
- malformed or incomplete Crashgen Expectation payloads are filtered or defaulted by `parse_crashgen_expectations()`
- missing settings do not produce an evaluator error; the corresponding check is skipped
- unsupported template tokens remain unchanged because only three placeholders are recognized

Diagnostics for malformed rule definitions belong to the Crashgen Expectation Parser, not the evaluator. Existing loaders and binding adapters may ignore diagnostics for compatibility, but conformance tests should assert them when parser behavior changes.

### Current ownership boundaries

The rule model is shared infrastructure. It owns the typed rule model and evaluator, but not the higher-level meaning of every fact.

`ConfigLayout` still includes `Vr`, and the evaluator fully supports `Predicate::ConfigLayoutIs(ConfigLayout::Vr)`. Current source-backed usage differs by downstream crate:

- in [`classic-scanlog-core`](classic-scanlog-core.md), `derive_scanlog_config_layout()` currently returns `Og` when a detected game version parses and `Unknown` otherwise; it does not use `Vr` as the primary OG/VR selector
- scanlog currently treats `ConfigLayout` mostly as a coarse valid/invalid fact for settings evaluation
- OG/VR selection for scanlog is handled earlier during Version Registry-backed config building, not inside this evaluator
- in [`classic-scangame-core`](classic-scangame-core.md), TOML validation still infers `Og` vs `Vr` from the config file path and passes that fact into `EvaluationContext`

Keep `Vr` support intact unless the downstream callers and rule schema are changed together.

### YAML ownership for the rule schema

- `classic-config-core` (this crate) parses `Crashgen_Registry.*.settings_rules` YAML into `CrashgenSettingsRules` via `CrashgenEntryRaw`; those rules, not deprecated `checks`, drive scanlog/scangame validation
- Node and Python binding layers convert their own transport shapes into a neutral document and call the same Crashgen Expectation Parser
- keep the rule-model module focused on typed parsing/evaluation, not binding-specific wrappers or TOML settings parsing

### Rule-model usage example

```rust
use classic_config_core::{
    AutoscanReportPlacement,
    CheckRule, ConfigLayout, CrashgenSettingsRules, CrashgenSettingsSnapshot,
    EvaluationContext, ExpectedValue, Predicate, PreflightAction, PreflightActionKind,
    PreflightRule, RuleMessages, RuleSeverity, RuleTarget, TargetValueType, evaluate_rules,
};
use std::collections::HashSet;

let rules = CrashgenSettingsRules {
    version: 1,
    preflight: vec![PreflightRule {
        id: "addictol_skip".to_string(),
        when: Predicate::PluginAny(vec!["addictol.dll".to_string()]),
        action: PreflightAction {
            kind: PreflightActionKind::NoticeAndSkipRemaining,
            bucket: AutoscanReportPlacement::ErrorInformation,
            severity: RuleSeverity::Info,
            message: "Addictol detected - skipping {crashgen_name} checks".to_string(),
            fix: None,
        },
    }],
    checks: vec![CheckRule {
        id: "f4ee_enabled".to_string(),
        target: RuleTarget {
            section: "Compatibility".to_string(),
            key: "F4EE".to_string(),
            value_type: TargetValueType::Bool,
        },
        when: Predicate::PluginAny(vec!["f4ee.dll".to_string()]),
        expect: ExpectedValue::Bool(true),
        messages: RuleMessages {
            fail: "{setting} is disabled".to_string(),
            fix: Some("Enable the compatibility toggle.".to_string()),
            pass: Some("{setting} is enabled".to_string()),
        },
        severity: RuleSeverity::Warning,
    }],
};

let mut installed_plugins = HashSet::new();
installed_plugins.insert("f4ee.dll".to_string());

let mut settings = CrashgenSettingsSnapshot::new();
settings.insert("Compatibility", "F4EE", "false".to_string());

let context = EvaluationContext {
    crashgen_name: "Buffout 4".to_string(),
    display_section: "[Compatibility]".to_string(),
    installed_plugins,
    settings,
    config_layout: ConfigLayout::Og,
    crashgen_version: Some((1, 28, 6)),
};

let result = evaluate_rules(&rules, &context);

assert!(!result.skip_remaining);
assert_eq!(result.outcomes.len(), 1);
assert_eq!(result.outcomes[0].message, "F4EE is disabled");
```

Note the import path: the types come from `classic_config_core::`, not the former `classic_crashgen_settings_core::` path.

### Rule-model contributor notes and known limits

- The rule-model public surface is whatever stays `pub` in `src/crashgen_rules.rs` and is re-exported from `lib.rs`; there are no facade modules or selective re-exports.
- The evaluator is synchronous and runtime-agnostic.
- Rule lookup uses both `RuleTarget.section` and `RuleTarget.key`; section-scoped settings with the same key name do not collide.
- `CrashgenVersionLt` treats a missing crashgen version as non-matching so local-file scans do not apply version-gated advice without evidence.
- Only `{crashgen_name}`, `{display_section}`, and `{setting}` are recognized in message templates.
- There is no built-in loader validation API; schema validation currently happens upstream inside the same crate.
- `classic-scanlog-core` still consumes this rule model even though its current `ConfigLayout` use is mostly `Og` vs `Unknown`.

If you extend the rule model, update this section when you change:

- public types or enum variants in `src/crashgen_rules.rs`
- public parser result or diagnostic types in `src/crashgen_expectation_parser.rs`
- accepted Crashgen Expectation field names or compatibility aliases
- predicate semantics or evaluation order
- value-coercion rules in `value_matches()`
- template placeholder behavior
- `ConfigLayout` ownership expectations across config, scanlog, and scangame layers

## Shippable schema metadata

The `client_schemas` module owns the accepted schema ranges for first-party
shippable YAML files:

- `MAIN_YAML` — accepted range for `CLASSIC Main.yaml`
- `GAME_FALLOUT4_YAML` — accepted range for `CLASSIC Fallout4.yaml`
- `shippable_schema_entries()` — returns `ShippableSchemaEntry { file, accepted }`
  for the current first-party shippable set, pairing each `ShippableFile` with
  its governing `SchemaCompat`

`classic-update-core` consumes `shippable_schema_entries()` for the first-party
YAML Data Update Channel so native callers do not duplicate the file list or
schema ranges. If a new first-party shippable YAML file is added, update this
metadata and the schema drift guard together.

## Schema-gated `CLASSIC Main.yaml` version reader

The `shippable` module exports a narrow startup-path reader,
`load_main_yaml_version`, that loads `CLASSIC Main.yaml` via
`shippable::load_shippable_yaml` (so both the per-user YAML cache and the
bundled install-tree copy are candidates) and returns the trimmed
`CLASSIC_Info.version` value. It enforces `client_schemas::MAIN_YAML`, which
means a stale `schema_version: 1.x` payload still carrying the legacy
`CLASSIC v…` decoration is rejected at this boundary instead of flowing
through to `QApplication::applicationVersion()` (GUI) or the binary-release
update-check input (CLI). Callers MUST NOT fall back to a raw `yaml_ops`
read on failure — that reintroduces the silent-degradation behavior the
gate exists to prevent.

Entry points:

- `load_main_yaml_version()` — production default; resolves the bundled
  copy against the process working directory.
- `load_main_yaml_version_with_bundled_dir(bundled_dir: Option<&Path>)` —
  native-frontend variant that takes the install-tree directory discovered
  by the caller (e.g. the GUI's `findDataDir()` result joined with
  `/databases`). Passing `None` keeps the default relative-path behavior.
- `load_main_yaml_version_with_env(bundled_dir, env)` — test-only variant
  that threads an `env` closure through to `yaml_cache_dir_with_env`; used
  by the sibling `shippable/main_version_tests.rs` to drive the reader
  against a mocked `LOCALAPPDATA` / `XDG_CACHE_HOME` without touching process
  env.

Error type: `MainYamlVersionError` (`#[non_exhaustive]`). Variants:

- `Load(YamlLoadError)` — the generic shippable-loader rejection. Covers
  file missing, YAML parse failure, missing / malformed `schema_version`,
  and incompatible-schema cases via the per-candidate
  `CandidateRejection.reason` strings.
- `VersionKeyMissing { source_path }` — the YAML loaded and schema-gated,
  but `CLASSIC_Info.version` (or the `CLASSIC_Info` section) is absent or
  explicitly `null`.
- `VersionEmpty { source_path }` — the key is present but empty or
  whitespace-only after trimming.
- `VersionNotString { source_path }` — the key is present but not a YAML
  scalar string (e.g. a sequence or mapping).

Field naming note: `source_path` rather than `source` is deliberate;
`thiserror` reserves the `source` field name for the error-chain link and
would demand `StdError` on the field type.

Binding surfaces (see [`error-contract.md`](error-contract.md) for shape
rationale):

- C++ CXX bridge exposes `classic::config::load_main_yaml_version(bundled_yaml_dir: &str)`
  returning `MainYamlVersionDto { version, error_kind, error_message }`.
  Empty-string sentinels on success; `error_kind` is one of `"load"`,
  `"version_key_missing"`, `"version_empty"`, `"version_not_string"`, or
  `"unknown"` (reserved for future non-exhaustive variants).
- Node binding exposes `loadMainYamlVersion(bundledYamlDir?: string | null): Promise<string>`.
  Rejects with an `Error` whose `message` is prefixed with the variant
  code (`LOAD:`, `VERSION_KEY_MISSING:`, `VERSION_EMPTY:`,
  `VERSION_NOT_STRING:`, `UNKNOWN:`), matching the `check_app_notification`
  precedent for async napi-rs surfaces.
- Python binding exposes `load_main_yaml_version(bundled_yaml_dir=None)`
  and the typed exception hierarchy rooted at
  `ClassicMainYamlVersionError`, with one subclass per core variant
  (`ClassicMainYamlVersionLoadError`,
  `ClassicMainYamlVersionKeyMissingError`,
  `ClassicMainYamlVersionEmptyError`,
  `ClassicMainYamlVersionNotStringError`).
