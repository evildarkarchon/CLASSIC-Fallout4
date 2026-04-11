# `classic-version-registry-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-version-registry-core/`](../../ClassicLib-rs/business-logic/classic-version-registry-core).

Crate metadata:

- Crate: `classic-version-registry-core`
- Description: `Pure Rust version registry for CLASSIC - game version detection and matching`

This crate is the Rust-side source of truth for known game versions, version matching, and per-version metadata such as Address Library, XSE, and crashgen compatibility data.

It is a pure Rust business-logic crate. It does not own a UI surface, FFI layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- look up known game versions by ID, exact version, or short name
- match a detected game version to the nearest supported registry entry
- distinguish non-VR and VR version families
- retrieve per-version metadata used by higher layers, including Address Library, XSE, and crashgen data
- access registry-backed defaults that downstream crates use for OG/NG/AE/VR selection and metadata fallback

Do not use this crate for:

- loading arbitrary user config or scanlog YAML datasets
- performing crash-log analysis
- owning or creating a Tokio runtime
- exposing binding-specific wrapper types

Those concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core), [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node), and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge).

---

## API Map

This crate does not expose its modules directly. `lib.rs` re-exports the public surface.

## Core registry API

- `VersionRegistry` - singleton-backed registry for lookup, filtering, and matching
- `get_version_registry()` - convenience accessor for the global registry instance

## Version and matching types

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
- `get_crashgen_version_strings() -> Vec<&str>`
- `get_crashgen_for_version(crashgen_version) -> Option<&CrashgenConfig>`
- `get_compatible_crashgens(game_version) -> Vec<&CrashgenConfig>`

Contributor notes:

- `is_compatible_with()` uses `compatible_range` when present, otherwise exact version equality
- crashgen compatibility is finer-grained than version compatibility because each `CrashgenConfig` may also carry its own `compatible_range`

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
- `get_address_library_filename(version, is_vr) -> Option<String>`
- `unknown_version_handling() -> &UnknownVersionHandling`

Crashgen-specific helpers:

- `get_crashgen_versions(id) -> Vec<&CrashgenConfig>`
- `get_crashgen_version_strings(id) -> Vec<&str>`
- `get_crashgen_for_version(id, crashgen_version) -> Option<&CrashgenConfig>`

Behavior worth knowing from the source:

- the global registry is initialized lazily through `OnceLock`
- initialization tries to load YAML first, then falls back to hardcoded defaults
- `get_all()` and `get_all_for_game()` sort by `priority` descending
- `get_correct_versions()` and `get_wrong_versions()` filter `HashMap` values directly and do not apply an explicit sort
- `get_by_short_name()` compares `short_name` exactly; it is not case-insensitive
- `get_address_library_filename()` currently hardcodes the game argument as `"Fallout4"`

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

1. Call `get_version_registry()` or `VersionRegistry::get_instance()`.
2. The singleton tries to load `CLASSIC Main.yaml` from one of these relative paths:
   - `CLASSIC Data/databases/CLASSIC Main.yaml`
   - `databases/CLASSIC Main.yaml`
   - `CLASSIC Main.yaml`
3. If loading succeeds, it reads `Version_Registry.versions` and optionally `Version_Registry.unknown_version_handling`.
4. If loading fails or no valid entries are parsed, the crate falls back to hardcoded Fallout 4 defaults.
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

- simple strings like `"1.37.0"`
- structured objects with fields such as `version`, `name`, `acronym`, `dll_file`, `description`, `download_url`, and optional `compatible_range`

Fallback rules visible in source:

- invalid or missing `compatible_range` values are ignored with `.ok()` rather than failing the whole entry
- structured crashgen entries without `version` are skipped
- if `Version_Registry.unknown_version_handling` is missing, built-in defaults are used
- if YAML loading/parsing fails entirely, the crate loads built-in Fallout 4 defaults for `FO4_OG`, `FO4_NG`, `FO4_AE`, and `FO4_VR`

The current built-in defaults include these notable priorities/defaults:

- `FO4_AE` has the highest non-VR priority and therefore becomes the default non-VR fallback
- `Fallout4 -> FO4_AE` and `Fallout4VR -> FO4_VR` are the built-in unknown-version defaults

---

## Error Handling Model

Public parsing/loading errors use `VersionRegistryError`.

Variants:

- `InvalidVersion(String)`
- `NotFound(String)`
- `YamlError(classic_settings_core::YamlError)` (the `YamlError` type was relocated from the former ``yaml-core`` into `classic-settings-core` during v9.1.0 Phase 1)
- `NotInitialized`
- `InvalidConfig(String)`

What contributors should know:

- `GameVersion::parse()` returns `InvalidVersion` for malformed version strings
- public registry access through `get_version_registry()` does not expose initialization failure because it silently falls back to built-in defaults
- YAML parsing failures matter mainly to internal initialization logic and tests; production callers usually observe fallback behavior instead of an error

Source-observed limitation:

- `UnknownVersionHandling.strategy` and `log_level` are parsed and exposed, but `VersionMatcher::match_version()` does not currently switch behavior based on those fields; it always uses the built-in exact/range/nearest/default flow

---

## Async And Runtime Notes

This crate is synchronous.

- It does not expose async APIs.
- It does not construct a Tokio runtime.
- Registry initialization uses synchronous YAML loading through [`classic-settings-core`](../../ClassicLib-rs/business-logic/classic-settings-core) (the former ``yaml-core`` was absorbed into `classic-settings-core` in v9.1.0 Phase 1).
- This fits the repo rule that runtime ownership stays in shared higher layers rather than inside business-logic crates.

Contributor rule: if you extend this crate, keep it runtime-agnostic and compatible with the shared-runtime assumptions used elsewhere in CLASSIC.

---

## Related Crates And Integration Points

- [`classic-settings-core`](../../ClassicLib-rs/business-logic/classic-settings-core) - YAML loading and extraction used during registry initialization (absorbed the former ``yaml-core`` in v9.1.0 Phase 1)
- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - resolves registry-backed version metadata for config building and fallback values
- [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - consumes registry-backed version data when building analysis configuration
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - exposes registry lookups and snapshots to JavaScript/TypeScript
- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) - exposes registry lookups to C++ frontends
- [`classic-constants-py`](../../ClassicLib-rs/python-bindings/classic-constants-py) and [`classic-version-registry-py`](../../ClassicLib-rs/python-bindings/classic-version-registry-py) - maintained Python-facing integration layers

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

On built-in defaults, `1.10.500.0` resolves to the `FO4_OG` entry as the nearest same-major non-VR match.

---

## Contributor Notes And Known Limits

- The public API is entirely re-export based; adding or removing re-exports in `src/lib.rs` changes the crate surface.
- YAML loading functions such as `load_from_yaml()` and YAML parsing helpers in `registry.rs` are internal, not public extension points.
- The built-in defaults are Fallout 4-specific today even though some APIs are named generically by `game`.
- `get_correct_versions()` and `get_wrong_versions()` do not guarantee sorted output.
- `unknown_version_handling.defaults` is used by downstream config code, but the core matcher itself does not currently honor `strategy` or `log_level` as behavioral switches.
- `VersionRegistryError::NotInitialized` is public but does not appear in the normal singleton path because `get_instance()` always initializes.
- `get_address_library_filename()` is a Fallout 4 convenience helper, not a game-agnostic lookup API.

If you extend this crate, update this document when you change:

- re-exports in `src/lib.rs`
- version matching order or priority rules
- YAML schema expectations for `Version_Registry`
- built-in defaults or unknown-version defaults
- the relationship between Version Registry, config building, and scanlog OG/VR selection
