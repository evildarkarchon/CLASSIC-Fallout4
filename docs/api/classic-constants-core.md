# `classic-constants-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-constants-core/`](../../ClassicLib-rs/business-logic/classic-constants-core).

Crate metadata:

- Crate: `classic-constants-core`
- Description: `Application constants and enumerations for CLASSIC (no PyO3)`

This crate is the small shared constants layer for CLASSIC's Rust business-logic crates and binding wrappers. It provides a handful of enums and constants for YAML file identifiers, supported games, Fallout 4 version variants, and a few settings keys.

Unlike older constant-only layers, part of its public surface is intentionally upstream of the Version Registry: `Fallout4Version` is a convenience enum, but its metadata comes from [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) rather than from hardcoded per-version tables inside this crate.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- refer to CLASSIC YAML file roles with a typed enum instead of raw strings
- represent supported games with a small shared `GameId` enum
- work with contributor-facing Fallout 4 version variants (`Original`, `NextGen`, `AnniversaryEdition`, `Vr`)
- derive common Fallout 4 version metadata through Version Registry-backed helpers
- reuse a small shared list of settings keys that must not be `None`

Do not use this crate for:

- parsing or loading YAML files
- discovering installation paths
- matching arbitrary detected game versions to registry entries
- defining a new source of truth for version metadata
- owning async or Tokio runtime behavior

Those concerns live in related crates such as [`classic-yaml-core`](../../ClassicLib-rs/business-logic/classic-yaml-core), [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core), [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core), and higher layers that consume them.

---

## Module And API Map

This crate currently exposes a single public file, `src/lib.rs`. There are no public submodules; the contributor-facing API is all at the crate root.

## Root-level constants and enums

- `NULL_VERSION` - semver `0.0.0` sentinel
- `Fallout4Version` - Fallout 4 version-family enum backed by Version Registry lookups
- `YamlFile` - type-safe identifiers for CLASSIC YAML/config files
- `GameId` - supported game identifiers used across crates
- `SETTINGS_IGNORE_NONE` - settings keys that must not be `None`
- `must_not_be_none()` - convenience membership check over `SETTINGS_IGNORE_NONE`

## Root-level re-exports

- `VersionRegistry`, `VersionInfo`, `MatchResult`, `MatchConfidence`, `VersionRegistryError`
- `get_version_registry()`

Contributor note:

- these re-exports make the crate partly a convenience entry point into Version Registry types, but it does not wrap or redefine those types

---

## Public API Surface

## `NULL_VERSION`

`NULL_VERSION` is a plain constant:

- type: `semver::Version`
- value: `0.0.0`

It is a sentinel value only. The crate does not attach extra semantics to it beyond "null/invalid version identifier" in the source docs.

## `Fallout4Version`

`Fallout4Version` is the main contributor-facing enum in this crate.

Variants:

- `Original`
- `NextGen`
- `AnniversaryEdition`
- `Vr`

Important traits and conversions:

- `Serialize`, `Deserialize`, `Default`, `Display`, `FromStr`, `Clone`, `Copy`, `Hash`
- `Default` is `Original`
- `Display` uses `display_name()`
- `FromStr` returns `Result<Fallout4Version, String>`

Important methods:

- `registry_id() -> &'static str`
- `get_version_info() -> Option<&'static VersionInfo>`
- `is_vr() -> bool`
- `is_standard() -> bool`
- `exe_name() -> &'static str`
- `docs_folder_name() -> &'static str`
- `steam_app_id() -> u32`
- `game_version() -> classic_version_registry_core::GameVersion`
- `version_semver() -> semver::Version`
- `xse_acronym() -> &'static str`
- `xse_acronym_string() -> String`
- `display_name() -> &'static str`
- `display_name_string() -> String`
- `short_name() -> &'static str`
- `as_str() -> &'static str`
- `all() -> [Fallout4Version; 4]`
- `address_library() -> Option<&'static AddressLibraryConfig>`
- `xse_config() -> Option<&'static XseConfig>`

Version Registry relationship:

- `registry_id()` hardcodes the registry IDs `FO4_OG`, `FO4_NG`, `FO4_AE`, and `FO4_VR`
- `get_version_info()` is the primary metadata lookup and delegates directly to `get_version_registry().get_by_id(...)`
- `game_version()`, `address_library()`, and `xse_config()` all depend on the corresponding registry entry being present
- this crate does not own a separate version table for Address Library, XSE, or full display metadata

Behavior worth knowing from the source:

- `exe_name()`, `docs_folder_name()`, and `steam_app_id()` are derived from VR/non-VR status, not fetched from the registry
- `game_version()` returns a zeroed `GameVersion::new(0, 0, 0, 0)` if the registry lookup fails
- `version_semver()` drops the fourth game-version component because `semver::Version` is 3-part
- `xse_acronym()` and `display_name()` return narrow static mappings for backward-compatible string behavior; `xse_acronym_string()` and `display_name_string()` return the actual registry strings
- `display_name()` matches on `VersionInfo.short_name`, not `VersionInfo.display_name`

`FromStr` aliases accepted today:

- `Original`: `original`, `og`, `1.10.163`
- `NextGen`: `nextgen`, `next-gen`, `ng`, `1.10.984`
- `AnniversaryEdition`: `anniversaryedition`, `anniversary-edition`, `anniversary`, `ae`, and any string starting with `1.11.`
- `Vr`: `vr`, `1.2.72`
- `auto`: resolves to `Default::default()`, which is `Original`

Source-visible limit:

- `FromStr` lowercases the input, but it does not parse arbitrary 4-part game versions; it only recognizes the exact aliases above plus the `1.11.` prefix rule for Anniversary Edition

## `YamlFile`

`YamlFile` is a small enum for internal file roles used across config-related code and bindings.

Variants:

- `Main`
- `Settings`
- `Ignore`
- `Game`
- `GameLocal`
- `Test`
- `Cache`

Important methods and traits:

- `as_str() -> &'static str`
- `description() -> &'static str`
- `all() -> [YamlFile; 7]`
- `Display`, `Serialize`, `Deserialize`, `Clone`, `Copy`, `Hash`

Descriptions exposed by `description()` are contributor-relevant because they encode the intended file role:

- `Main` -> `CLASSIC Data/databases/CLASSIC Main.yaml`
- `Settings` -> `CLASSIC Settings.yaml`
- `Ignore` -> `CLASSIC Ignore.yaml`
- `Game` -> `CLASSIC Data/databases/CLASSIC {Game}.yaml`
- `GameLocal` -> `CLASSIC Data/CLASSIC {Game} Local.yaml`
- `Test` -> `tests/test_settings.yaml`
- `Cache` -> `User config dir/CLASSIC/cache.yaml`

Contributor notes:

- this enum does not build real paths; it only labels file roles
- there is no `FromStr` implementation in current source
- `all()` returns a fixed array in declaration order

## `GameId`

`GameId` is the shared game identifier enum used by other crates for basic routing.

Variants:

- `Fallout4`
- `Fallout4VR`
- `Skyrim`
- `Starfield`

Important methods and traits:

- `as_str() -> &'static str`
- `exe_name() -> &'static str`
- `is_vr() -> bool`
- `all() -> [GameId; 4]`
- `Display`, `FromStr`, `Serialize`, `Deserialize`, `Clone`, `Copy`, `Hash`

Behavior worth knowing:

- `exe_name()` hardcodes `Fallout4.exe`, `Fallout4VR.exe`, `SkyrimSE.exe`, and `Starfield.exe`
- `is_vr()` is only true for `Fallout4VR`
- `FromStr` is exact and case-sensitive; it accepts only `Fallout4`, `Fallout4VR`, `Skyrim`, and `Starfield`
- unlike `Fallout4Version`, `GameId` does not have alias parsing

That distinction matters in higher layers: `GameId` treats Fallout 4 VR as a separate game, while `Fallout4Version` treats VR as a Fallout 4 version family.

## `SETTINGS_IGNORE_NONE` and `must_not_be_none()`

`SETTINGS_IGNORE_NONE` is a slice constant containing the current keys that must not be stored as `None`:

- `SCAN Custom Path`
- `MODS Folder Path`
- `INI Folder Path`
- `Root_Folder_Game`
- `Root_Folder_Docs`

`must_not_be_none(key) -> bool` is a convenience wrapper that performs `SETTINGS_IGNORE_NONE.contains(&key)`.

Contributor notes:

- membership is a simple linear scan over a short slice
- this crate does not define how these settings are validated or persisted; it only exposes the shared key list used by consumers

---

## Serialization And String Behavior

All three enums derive `Serialize` and `Deserialize` through Serde, and there are no `#[serde(rename = ...)]` attributes in current source.

Contributor-visible implications:

- unit variants serialize using their Rust variant names, not the custom `as_str()` or `Display` output
- `YamlFile::Settings` serializes as `"Settings"`
- `GameId::Fallout4` serializes as `"Fallout4"`
- `Fallout4Version::Vr` serializes as `"Vr"`, even though `as_str()` returns `"VR"`

That last point is easy to miss. If a caller needs the uppercase short form, use `as_str()` or `short_name()` explicitly rather than relying on Serde output.

---

## How Higher Layers Use This Crate

This crate sits upstream of a few small but important integration points:

- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) is the source of truth for `Fallout4Version` metadata; this crate re-exports registry types and delegates per-version lookups to it
- [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core) uses `GameId` in `XseType::from_game_id()` to choose the expected script-extender family
- [`classic-web-core`](../../ClassicLib-rs/business-logic/classic-web-core) uses `GameId` to map games to site-specific URL slugs
- [`classic-registry-core`](../../ClassicLib-rs/business-logic/classic-registry-core) stores and retrieves the active Fallout 4 version as `Fallout4Version`
- [`classic-constants-py`](../../ClassicLib-rs/python-bindings/classic-constants-py) wraps `YamlFile`, `GameId`, `Fallout4Version`, and the settings helpers for Python callers

In practice:

- use `GameId` for coarse game-family branching
- use `Fallout4Version` when CLASSIC logic needs FO4-specific OG/NG/AE/VR distinctions
- use `VersionInfo` from `get_version_info()` when downstream code needs real registry-backed metadata instead of convenience strings

---

## Error Handling Model

This crate does not define its own crate-wide error enum.

Current public error behavior is split across three patterns:

- `Fallout4Version::from_str()` returns `Result<_, String>`
- `GameId::from_str()` returns `Result<_, String>`
- most other helpers are infallible and return plain values or `Option<_>`

Version Registry errors only appear through the re-exported `VersionRegistryError` type and direct registry APIs such as `get_version_registry()` consumers call themselves.

Important contributor note:

- `Fallout4Version::get_version_info()` does not surface a loading error; it returns `Option<&'static VersionInfo>` based on the already-initialized registry singleton behavior in `classic-version-registry-core`

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-version-registry-core` - required for `Fallout4Version` metadata and re-exported registry types
- `semver` - `NULL_VERSION` and `version_semver()`
- `serde` - enum serialization/deserialization derives
- `phf` - declared dependency, but current `src/lib.rs` does not visibly expose a PHF-backed public API

Related crates and wrappers:

- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) - upstream metadata source and matching logic
- [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core) - consumes `GameId`
- [`classic-web-core`](../../ClassicLib-rs/business-logic/classic-web-core) - consumes `GameId`
- [`classic-registry-core`](../../ClassicLib-rs/business-logic/classic-registry-core) - stores `Fallout4Version` in shared runtime state
- [`classic-constants-py`](../../ClassicLib-rs/python-bindings/classic-constants-py) - Python wrapper crate over this surface

---

## Usage Example

This example sticks to the real public API: use `Fallout4Version` for FO4-specific branching, then pull the full registry-backed metadata only when needed.

```rust
use classic_constants_core::{Fallout4Version, GameId, YamlFile, must_not_be_none};
use std::str::FromStr;

let version = Fallout4Version::from_str("NG")?;
assert!(version.is_standard());
assert_eq!(version.registry_id(), "FO4_NG");
assert_eq!(version.exe_name(), "Fallout4.exe");

if let Some(info) = version.get_version_info() {
    println!("Matched registry entry: {} ({})", info.id, info.display_name);

    if let Some(xse) = version.xse_config() {
        println!("Expected XSE family: {}", xse.acronym);
    }
}

assert_eq!(GameId::Fallout4VR.exe_name(), "Fallout4VR.exe");
assert_eq!(YamlFile::Cache.description(), "User config dir/CLASSIC/cache.yaml");
assert!(must_not_be_none("Root_Folder_Game"));

# Ok::<(), String>(())
```

---

## Contributor Notes And Known Limits

- the full public surface is in `src/lib.rs`; changing re-exports or adding a public item there changes the crate API
- `Fallout4Version` is convenience-oriented, not a complete version-matching API; arbitrary version detection and nearest/range matching belong in [`classic-version-registry-core`](classic-version-registry-core.md)
- some `Fallout4Version` helpers return simplified static strings even though the underlying registry stores richer values; use `get_version_info()`, `display_name_string()`, or `xse_acronym_string()` when exact registry text matters
- `GameId::FromStr` is stricter than `Fallout4Version::FromStr`; do not assume the same alias behavior
- Serde output for `Fallout4Version` follows Rust variant names, so `Vr` serializes as `"Vr"`, not `"VR"`
- the crate description mentions "constants and enumerations," but version metadata is intentionally delegated upstream to Version Registry rather than duplicated here
- `phf` is present in `Cargo.toml`, but current source does not visibly use it in the public API

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- `Fallout4Version` alias parsing or default behavior
- any string/serialization contract for the enums
- the contents of `SETTINGS_IGNORE_NONE`
- how Version Registry-backed metadata is surfaced through `Fallout4Version`
