# `classic-version-registry-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-version-registry-core/`](../../business-logic/classic-version-registry-core).

Crate metadata:

- Crate: `classic-version-registry-core`
- Description: `Pure Rust version registry for CLASSIC - game version detection and matching`

This crate is the Rust-side source of truth for known game versions, version matching, known-version queries, and per-version metadata such as Address Library, XSE, and crashgen compatibility data. It is the sole policy owner of the known-version queries `is_known_fallout4_version()` and `is_known_f4se_version()` (issue #244; they used to live in [`classic-version-core`](classic-version-core.md), which now only re-exports them until it retires in #258).

Every registry snapshot sits behind a `VersionRegistryScope` handle. The unscoped accessors read one process default scope, which is what Rust, CXX, and Node callers have always observed; the Python facades that read the registry each select their own isolated scope (see [Version Registry Scopes](#version-registry-scopes)).

It is a pure Rust business-logic crate. It does not own a UI surface, FFI layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- look up known game versions by ID, exact version, or short name
- ask whether a game or F4SE version is a known (non-VR) Fallout 4 version
- keep an independent, lazily taken registry snapshot per caller-selected scope
- match a detected game version to the nearest supported registry entry
- distinguish non-VR and VR version families
- retrieve per-version metadata used by higher layers, including Address Library, XSE, and crashgen data
- access registry-backed defaults that downstream crates use for OG/NG/AE/VR selection and metadata fallback

Do not use this crate for:

- loading arbitrary user config or scanlog YAML datasets
- performing crash-log analysis
- owning or creating a Tokio runtime
- exposing binding-specific wrapper types

Those concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), [`classic-node`](../../node-bindings/classic-node), and [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

---

## API Map

This crate does not expose its modules directly. `lib.rs` re-exports the public surface.

## Core registry API

- `VersionRegistry` - one immutable registry snapshot for lookup, filtering, matching, and known-version queries
- `VersionRegistryScope` - opaque handle to one lazily taken snapshot; `default_scope()` backs the unscoped accessors
- `get_version_registry()` - convenience accessor for the process default scope's snapshot
- `is_known_fallout4_version()` / `is_known_f4se_version()` - known-version queries against the default snapshot

## Version and matching types

- `NULL_VERSION` - semver `0.0.0` sentinel used by consumers that need a null/invalid version marker
- `Fallout4Version` - contributor-facing Fallout 4 version-family enum backed by Version Registry lookups
- `GameVersion` - 4-component game version type used throughout the crate
- `VersionMatcher` - explicit matcher wrapper over a `VersionRegistry`
- `MatchResult` - result payload for a version match attempt
- `MatchConfidence` - `Exact`, `Range`, `Nearest`, `Default`, or `Unknown`

## Metadata models

- `VersionInfo` - complete metadata for one known game version
- `AddressLibraryConfig` and `AddressLibFormat` - Address Library metadata
- `XseConfig` - Script Extender metadata and optional script hashes
- `CrashgenConfig` - per-crashgen compatibility/config metadata
- `CompatibleRange` - inclusive version range used by version and crashgen matching
- `UnknownVersionHandling`, `UnknownVersionStrategy`, `LogLevel` - parsed registry config for unknown-version policy metadata

## Error type

- `VersionRegistryError` - typed error enum used by parsing/loading internals and `GameVersion::parse()`

---

## Public API Surface

## `NULL_VERSION`

`NULL_VERSION` is a plain root-level `semver::Version` constant with value `0.0.0`.

Contributor note:

- it is a sentinel only; it does not change registry behavior on its own
- downstream crates such as [`classic-version-core`](classic-version-core.md) re-export it directly from this crate now that the dedicated constants crate is gone

## `Fallout4Version`

`Fallout4Version` is the crate's contributor-facing enum for Fallout 4 release families.

Variants:

- `Original`
- `NextGen`
- `AnniversaryEdition`
- `Vr`

Important methods and traits:

- `registry_id() -> &'static str`
- `get_version_info() -> Option<&'static VersionInfo>`
- `version_info_in(&VersionRegistry) -> Option<&VersionInfo>`
- `is_vr() -> bool`
- `is_standard() -> bool`
- `exe_name() -> &'static str`
- `docs_folder_name() -> &'static str`
- `steam_app_id() -> u32`
- `game_version() -> GameVersion`
- `game_version_in(&VersionRegistry) -> GameVersion`
- `version_semver() -> semver::Version`
- `xse_acronym() -> &'static str`
- `xse_acronym_in(&VersionRegistry) -> &'static str`
- `xse_acronym_string() -> String`
- `display_name() -> &'static str`
- `display_name_in(&VersionRegistry) -> &'static str`
- `display_name_string() -> String`
- `short_name() -> &'static str`
- `as_str() -> &'static str`
- `all() -> [Fallout4Version; 4]`
- `address_library() -> Option<&'static AddressLibraryConfig>`
- `xse_config() -> Option<&'static XseConfig>`
- `Serialize`, `Deserialize`, `Default`, `Display`, `FromStr`, `Clone`, `Copy`, `Hash`

Behavior worth knowing:

- `get_version_info()` delegates to `get_version_registry().get_by_id(...)`
- each `*_in(registry)` method answers from the caller's snapshot (for example `scope.registry()`) and borrows from it; the unscoped form is the same method applied to the default snapshot
- `game_version()`, `address_library()`, and `xse_config()` all depend on a registry entry being available
- `exe_name()`, `docs_folder_name()`, and `steam_app_id()` are still convenience mappings derived from VR/non-VR status rather than registry YAML
- `version_semver()` drops the fourth game-version component because `semver::Version` is three-part
- `FromStr` accepts the contributor-facing aliases `og`, `ng`, `ae`, `vr`, `auto`, and the documented version-string shortcuts

## `GameVersion`

`GameVersion` is the crate's basic version type.

Fields:

- `major`, `minor`, `patch`, `build`

Important methods and traits:

- `GameVersion::new(major, minor, patch, build)`
- `GameVersion::parse(s) -> Result<GameVersion, VersionRegistryError>`
- `semantic_distance(&self, other) -> u64`
- `same_major(&self, other) -> bool`
- `Display`, `FromStr`, `Ord`, `Hash`, `Default`

Behavior worth knowing:

- `parse()` accepts either `major.minor.patch` or `major.minor.patch.build`; 3-part input gets `build = 0`
- `Display` always formats back to 4 parts
- `semantic_distance()` ignores build differences and weights major/minor/patch as `1_000_000 / 1_000 / 1`

## `VersionInfo`

`VersionInfo` is the main metadata container returned by registry lookups.

Important fields include:

- identity and versioning: `id`, `game`, `is_vr`, `version`, `display_name`, `short_name`
- integration metadata: `docs_name`, `steam_id`, `address_library`, `xse`, `exe_hash`
- matching metadata: `compatible_range`, `priority`, `deprecated`
- crashgen metadata: `crashgen_versions`

Important methods:

- `version_string() -> String`
- `is_compatible_with(detected) -> bool`
- `get_crashgen_version_strings() -> Vec<&str>` returns non-`exact_match` crashgen versions
  suitable for floor-based validation
- `get_crashgen_for_version(crashgen_version) -> Option<&CrashgenConfig>`
- `get_compatible_crashgens(game_version) -> Vec<&CrashgenConfig>`

Contributor notes:

- `is_compatible_with()` uses `compatible_range` when present, otherwise exact version equality
- crashgen compatibility is finer-grained than version compatibility because each `CrashgenConfig` may also carry its own `compatible_range`
- crashgen entries marked `exact_match` remain available through `VersionInfo.crashgen_versions`,
  `VersionInfo::get_crashgen_for_version()`, and `VersionRegistry::get_crashgen_versions()`, but
  are excluded from `get_crashgen_version_strings()` so legacy exception builds do not lower
  validation floors

## `VersionRegistry`

`VersionRegistry` is the main contributor-facing integration point.

Important lookup methods:

- `VersionRegistry::get_instance() -> &'static VersionRegistry`
- `get_by_id(id) -> Option<&VersionInfo>`
- `get_by_version(version) -> Option<&VersionInfo>`
- `get_by_short_name(short_name) -> Option<&VersionInfo>`

Important filtering methods:

- `get_all() -> Vec<&VersionInfo>`
- `get_all_for_game(game, is_vr) -> Vec<&VersionInfo>`
- `get_correct_versions(is_vr) -> Vec<&VersionInfo>`
- `get_wrong_versions(is_vr) -> Vec<&VersionInfo>`

Important matching/helpers:

- `match_version(detected, game, is_vr) -> MatchResult`
- `is_known_fallout4_version(&semver::Version) -> bool`
- `is_known_f4se_version(&semver::Version) -> bool`
- `get_address_library_filename(version, is_vr) -> Option<String>`
- `unknown_version_handling() -> &UnknownVersionHandling`

Crashgen-specific helpers:

- `get_crashgen_versions(id) -> Vec<&CrashgenConfig>`
- `get_crashgen_version_strings(id) -> Vec<&str>` returns non-`exact_match` crashgen versions
  suitable for floor-based validation
- `get_crashgen_for_version(id, crashgen_version) -> Option<&CrashgenConfig>`

Behavior worth knowing from the source:

- every snapshot is taken lazily, on the first `VersionRegistryScope::registry()` call for its scope; `get_instance()` and `get_version_registry()` read the process default scope
- initialization tries runtime YAML first, then falls back to the embedded copy of `CLASSIC Main.yaml`
- `get_all()` and `get_all_for_game()` sort by `priority` descending
- `get_correct_versions()` and `get_wrong_versions()` filter `HashMap` values directly and do not apply an explicit sort
- `get_by_short_name()` compares `short_name` exactly; it is not case-insensitive
- `get_address_library_filename()` currently hardcodes the game argument as `"Fallout4"`

## Known-version queries

`VersionRegistry::is_known_fallout4_version(&semver::Version) -> bool` and `VersionRegistry::is_known_f4se_version(&semver::Version) -> bool` answer from that snapshot; the root-level free functions of the same name answer from the default snapshot.

Source-visible behavior:

- both consider only `get_all_for_game("Fallout4", Some(false))`, so VR entries are never known versions
- the game query compares each entry's `major.minor.patch`, dropping the fourth (build) component, by exact equality
- the F4SE query parses each entry's `xse.compatible_version` with the lenient shared-core `try_parse_version()`; entries without an XSE section or with an unparseable string never match

These were `classic_version_core::is_known_fallout4_version()` / `is_known_f4se_version()` until issue #244. That crate re-exports the free functions unchanged until it retires (#258); new callers import this crate.

## Version Registry Scopes

`VersionRegistryScope` is an opaque, `Send + Sync + 'static` handle to one registry snapshot.

- `VersionRegistryScope::default_scope()` - the process default scope behind `get_version_registry()` and `VersionRegistry::get_instance()`
- `VersionRegistryScope::new_isolated()` - a scope whose snapshot is shared with no other scope
- `registry(&self) -> &VersionRegistry` - the scope's snapshot, taken now if this is the first use
- `Clone` shares the snapshot; `==` is true exactly when two handles name the same snapshot

Snapshot rules:

- **Lazy.** Creating a handle loads nothing. The first `registry()` call searches the relative `CLASSIC Main.yaml` locations against the working directory at that moment, then falls back to the embedded YAML.
- **Stable.** After the first use the snapshot is immutable: later working-directory or file changes never reload it, and there is no reset operation.
- **Isolated.** A scope never reads another scope's snapshot, including the default one. The snapshot load reads and parses `CLASSIC Main.yaml` directly rather than through the shared path/mtime YAML-file cache: a scope loads its file once, so that cache would save nothing, and going through it would add entries to and move the counters of the YAML cache scope another owner uses, and could hand a scope first used from one root another root's cached parse of the same relative path.
- **Explicit.** Nothing selects a scope through thread-local or ambient state. Callers hold a handle and pass it, or move it into async or blocking work, which keeps naming the same snapshot on any worker thread.

Scoped entry points in downstream owners take either a snapshot (`&VersionRegistry`, the `*_in` helpers) for pure lookups or a `&VersionRegistryScope` for workflows, so a workflow that never needs registry data never takes the snapshot:

- [`classic-config-core`](classic-config-core.md): `resolve_registry_version_info_in()`, `YamlDataCore::from_yaml_content_in_version_registry_scope()`, `load_installed_yaml_data_in_version_registry_scope()`, `load_explicit_yaml_data_in_version_registry_scope()`
- [`classic-xse-core`](classic-xse-core.md): `resolve_xse_folder_from_game_local_facts_in_version_registry_scope()`
- [`classic-scangame-core`](classic-scangame-core.md): `resolve_xse_folder_for_scan_in_version_registry_scope()`, `AddressLibInfo::*_in()`, `XseChecker::with_version_registry_scope()`, `GameSetupIntake::run_in_scopes()`, `GameScanOrchestrator::with_version_registry_scope()`
- [`classic-scanlog-core`](classic-scanlog-core.md): `PluginAnalyzer::with_version_registry_scope()`, `scan_run::contract::execute_in_version_registry_scope()`

Rust, CXX, and Node callers keep using the unscoped paths and therefore the default scope. The Python `classic_version_registry`, `classic_version`, `classic_config`, `classic_scangame`, and `classic_scanlog` facades each hold their own isolated scope and pass it at facade entry or object construction, so once the facades share one native library (#259) each keeps the snapshot of its own first use.

## `MatchResult` and `MatchConfidence`

`MatchResult` captures the outcome of `match_version()`.

Fields:

- `version_info: Option<VersionInfo>`
- `confidence: MatchConfidence`
- `detected: GameVersion`
- `message: String`

Useful helpers:

- `is_exact()`
- `is_fallback()`
- `should_warn()`
- `is_valid()`

Confidence meanings:

- `Exact` - exact version entry found
- `Range` - version matched an entry's `compatible_range`
- `Nearest` - same-major nearest fallback by semantic distance
- `Default` - highest-priority fallback for the selected game/mode
- `Unknown` - no match found

## Metadata model constructors

The model types expose constructor helpers that are useful in tests, defaults, and future registry builders:

- `AddressLibraryConfig::new(...)`
- `XseConfig::new(...)`
- `XseConfig::with_script_hashes(...)`
- `CompatibleRange::new(...)`
- `CompatibleRange::from_strings(...)`
- `CrashgenConfig::new(...)`
- `CrashgenConfig::with_range(...)`
- `CrashgenConfig::from_version_string(...)`
- `UnknownVersionHandling::new(...)`

---

## Registry Loading And Matching Flow

The source-visible flow is:

1. Call `get_version_registry()` or `VersionRegistry::get_instance()` (the default scope), or `registry()` on a `VersionRegistryScope`.
2. On that scope's first use, it tries to load `CLASSIC Main.yaml` from one of these paths, resolved against the current working directory:
   - `CLASSIC Data/databases/CLASSIC Main.yaml`
   - `databases/CLASSIC Main.yaml`
   - `CLASSIC Main.yaml`
3. If loading succeeds, it reads `Version_Registry.versions` and optionally `Version_Registry.unknown_version_handling`.
4. If runtime YAML loading fails or no valid entries are parsed, the crate parses the checked-in `CLASSIC Data/databases/CLASSIC Main.yaml` embedded at compile time.
5. Matching then proceeds in this order:
   - exact version lookup
   - `compatible_range` match
   - nearest same-major match by `semantic_distance()`
   - default fallback to the highest-priority version for that game/mode
   - `Unknown` if nothing matches

One important integration detail: downstream crates use this registry as the source of OG/NG/AE/VR metadata selection. In current scanlog flow, `ConfigLayout` is no longer the OG/VR selector; scanlog treats it as a coarse valid/invalid gate while version-family selection is resolved earlier from Version Registry-backed config building.

---

## YAML Shape And Fallback Behavior

The crate's YAML loader is internal, but the expected source shape is visible from `registry.rs`.

Contributor-relevant keys for each `Version_Registry.versions[]` entry include:

- `id`, `game`, `version`, `display_name`, `short_name`, `description`
- `docs_name`, `steam_id`, `priority`, `is_vr`, `deprecated`, `exe_hash`
- `address_library.{filename, format, nexus_url}`
- `xse.{acronym, full_name, compatible_version, loader, file_count, script_hashes}`
- `compatible_range.{min, max}`
- `crashgen_versions`

`crashgen_versions` supports two formats:

- simple strings like `"1.38.1"`
- structured objects with fields such as `version`, `name`, `acronym`, `dll_file`, `description`, `download_url`, optional `compatible_range`, and optional `exact_match`

Fallback rules visible in source:

- invalid or missing `compatible_range` values are ignored with `.ok()` rather than failing the whole entry
- structured crashgen entries without `version` are skipped
- invalid runtime YAML causes a scope's first use to take the embedded `CLASSIC Main.yaml` fallback
- if runtime YAML omits `Version_Registry.unknown_version_handling`, the embedded `CLASSIC Main.yaml` fallback supplies that section
- if the embedded `CLASSIC Main.yaml` fallback is invalid or omits required registry sections, initialization fails fast because the checked-in source-of-truth file no longer matches the parser

The embedded YAML fallback inherits these notable priorities/defaults from `CLASSIC Main.yaml`:

- `FO4_AE` has the highest non-VR priority and therefore becomes the default non-VR fallback
- `Fallout4 -> FO4_AE` and `Fallout4VR -> FO4_VR` are the YAML-owned unknown-version defaults

---

## Error Handling Model

Public parsing/loading errors use `VersionRegistryError`.

Variants:

- `InvalidVersion(String)`
- `NotFound(String)`
- `YamlError(classic_settings_core::YamlError)` (the `YamlError` type was relocated from the former ``yaml-core`` into `classic-settings-core` during v9.1.0 Phase 1; it is now owned by `classic_shared_core::yaml` and re-exported under the same `classic_settings_core` path)
- `NotInitialized`
- `InvalidConfig(String)`

What contributors should know:

- `GameVersion::parse()` returns `InvalidVersion` for malformed version strings
- public registry access through `get_version_registry()` does not expose runtime YAML initialization failure because it falls back to embedded YAML
- runtime YAML parsing failures matter mainly to internal initialization logic and tests; production callers usually observe embedded fallback behavior instead of an error

Source-observed limitation:

- `UnknownVersionHandling.strategy` and `log_level` are parsed and exposed, but `VersionMatcher::match_version()` does not currently switch behavior based on those fields; it always uses the built-in exact/range/nearest/default flow

---

## Async And Runtime Notes

This crate is synchronous.

- It does not expose async APIs.
- It does not construct a Tokio runtime.
- Registry initialization uses synchronous YAML loading through [`classic-settings-core`](../../business-logic/classic-settings-core) (historical note: the former `classic-yaml-core` crate was absorbed into `classic-settings-core` in v9.1.0 Phase 1).
- This fits the repo rule that runtime ownership stays in shared higher layers rather than inside business-logic crates.

Contributor rule: if you extend this crate, keep it runtime-agnostic and compatible with the shared-runtime assumptions used elsewhere in CLASSIC.

---

## Related Crates And Integration Points

- [`classic-settings-core`](../../business-logic/classic-settings-core) - YAML loading and extraction used during registry initialization (historical note: this owner absorbed the former `classic-yaml-core` crate in v9.1.0 Phase 1)
- [`classic-config-core`](../../business-logic/classic-config-core) - resolves registry-backed version metadata for config building and fallback values
- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - consumes registry-backed version data when building analysis configuration
- [`classic-node`](../../node-bindings/classic-node) - exposes registry lookups and snapshots to JavaScript/TypeScript
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - exposes registry lookups to C++ frontends
- [`classic-version-registry-py`](../../python-bindings/classic-version-registry-py) - maintained Python-facing integration layer for registry lookups and version metadata

In practice, this crate sits upstream of config-building and scanlog-analysis decisions.

---

## Usage Example

This example follows the real public API and mirrors the crate docs.

```rust
use classic_version_registry_core::{GameVersion, get_version_registry};

let registry = get_version_registry();

let detected = GameVersion::parse("1.10.500.0")?;
let matched = registry.match_version(&detected, "Fallout4", false);

println!("Detected: {}", matched.detected);
println!("Confidence: {:?}", matched.confidence);
println!("Message: {}", matched.message);

if let Some(info) = &matched.version_info {
    println!("Matched ID: {}", info.id);
    println!("Display: {}", info.display_name);

    for crashgen in info.get_compatible_crashgens(Some(&detected)) {
        println!("Crashgen {} -> {}", crashgen.name, crashgen.version);
    }
}

# Ok::<(), classic_version_registry_core::VersionRegistryError>(())
```

On the embedded YAML fallback, `1.10.500.0` resolves to the `FO4_OG` entry as the nearest same-major non-VR match.

---

## Contributor Notes And Known Limits

- The public API is entirely re-export based; adding or removing re-exports in `src/lib.rs` changes the crate surface.
- YAML loading functions such as `load_from_yaml()` and YAML parsing helpers in `registry.rs` are internal, not public extension points.
- The embedded fallback is Fallout 4-specific today because `CLASSIC Main.yaml` currently owns Fallout 4 registry data, even though some APIs are named generically by `game`.
- `get_correct_versions()` and `get_wrong_versions()` do not guarantee sorted output.
- `unknown_version_handling.defaults` is used by downstream config code, but the core matcher itself does not currently honor `strategy` or `log_level` as behavioral switches.
- `VersionRegistryError::NotInitialized` is public but does not appear in the normal accessor paths because `get_instance()` and `VersionRegistryScope::registry()` always initialize.
- A scope's snapshot depends on the working directory at its first use. Callers that need a predictable snapshot should take it (call `registry()`) while the intended root is current.
- `get_address_library_filename()` is a Fallout 4 convenience helper, not a game-agnostic lookup API.

If you extend this crate, update this document when you change:

- re-exports in `src/lib.rs`
- the known-version query rules or the scope snapshot rules
- version matching order or priority rules
- YAML schema expectations for `Version_Registry`
- embedded fallback behavior or unknown-version defaults
- the relationship between Version Registry, config building, and scanlog OG/VR selection
