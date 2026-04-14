# `classic-xse-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-xse-core/`](../../business-logic/classic-xse-core).

Crate metadata:

- Crate: `classic-xse-core`
- Description: `Script Extender (XSE) utilities for CLASSIC (no PyO3)`

This crate is the small Rust-side XSE detection layer for CLASSIC. It identifies which script extender a game uses, checks whether the expected loader exists in a game directory, and tries to derive an XSE version from sibling DLL filenames.

It is a synchronous business-logic crate. It does not own a Tokio runtime, registry-driven game-path discovery flow, or binding surface.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- map a supported `GameId` to the expected XSE family (`F4SE`, `F4SEVR`, `SKSE64`, `SFSE`)
- parse or format XSE type identifiers
- check whether an expected XSE loader executable exists in a known game directory
- derive an XSE version from versioned DLL filenames next to the loader
- package installation status and optional detected version into one `XseInfo` value
- reuse common version helpers re-exported from [`classic-version-core`](../../business-logic/classic-version-core)

Do not use this crate for:

- finding the game installation path in the first place
- registry or YAML-driven compatibility decisions
- Address Library validation
- crashgen or broader setup scanning orchestration
- binding-specific wrapper DTOs

Those concerns live in related crates such as [`classic-path-core`](../../business-logic/classic-path-core), [`classic-version-registry-core`](../../business-logic/classic-version-registry-core), [`classic-scangame-core`](../../business-logic/classic-scangame-core), and the C++/Node/Python binding layers.

---

## Module And API Map

This crate currently exposes a single public file, `src/lib.rs`. There are no public modules or public traits; the contributor-facing API is all at the crate root.

## Root-level API

- `XseType` - supported script-extender families and their naming helpers
- `XseInfo` - simple installation-status payload for one game directory and XSE type
- `detect_xse_version()` - version detection from a loader path plus sibling DLL filenames
- `is_xse_installed()` - loader existence check for a game directory
- `get_xse_info()` - combined installation + optional version probe
- `XseError`, `XseResult<T>` - crate-specific error model

## Root-level re-exports

- `compare_versions()`, `parse_version()`, `try_parse_version()` from [`classic-version-core`](../../business-logic/classic-version-core)

Contributor note:

- `classic-path-core` is a direct dependency, but in current source it is only visible in the public error surface through `XseError::PathError`

---

## Public API Surface

## `XseType`

`XseType` is the crate's main identifier enum.

Variants:

- `F4SE`
- `F4SEVR`
- `SKSE`
- `SKSE64`
- `SKSEVR`
- `SFSE`

Important methods and traits:

- `XseType::as_str() -> &'static str`
- `XseType::from_game_id(game_id) -> XseType`
- `XseType::loader_name() -> &'static str`
- `XseType::dll_prefix() -> &'static str`
- `FromStr` with `type Err = XseError`

Behavior worth knowing:

- `FromStr` is case-insensitive because it uppercases the input before matching
- `from_game_id()` maps `GameId::Skyrim` to `SKSE64`; there is no separate `GameId` variant for classic Skyrim or Skyrim VR in `classic-shared-core`
- loader and DLL naming are hardcoded by enum variant, for example `F4SE -> f4se_loader.exe` and `f4se_`

## `XseInfo`

`XseInfo` is the crate's basic integration struct.

Fields:

- `xse_type: XseType`
- `path: PathBuf`
- `version: Option<semver::Version>`
- `installed: bool`

Important constructors and methods:

- `XseInfo::new(xse_type, path)`
- `XseInfo::with_version(xse_type, path, version, installed)`
- `check_installed() -> bool`
- `loader_path() -> PathBuf`

Behavior worth knowing:

- `check_installed()` only checks whether `<path>/<loader_name>` exists and is a file
- `loader_path()` is a pure path join; it does not validate the path or probe the filesystem
- `get_xse_info()` mutates an `XseInfo` built with `new()`, then fills `installed` and maybe `version`

## `detect_xse_version()`

`detect_xse_version(loader_path, xse_type) -> XseResult<Version>` is the crate's version-detection entry point.

Source-visible flow:

1. Fail with `XseError::NotFound` if `loader_path` does not exist.
2. Read the loader's parent directory.
3. Scan directory entries for filenames that:
   - start with `xse_type.dll_prefix()`
   - end with `.dll`
4. Strip the prefix and `.dll`, then replace `_` with `.`.
5. Parse the resulting string with `parse_version()`.
6. Return the first parseable version found.
7. If no parseable match is found, return `XseError::VersionDetectionFailed`.

Important contributor details:

- detection uses DLL filenames, not PE metadata and not log parsing
- the loader filename itself is not parsed for version information
- `parse_version()` comes from [`classic-version-core`](../../business-logic/classic-version-core) and ignores a fourth version component, so `1_10_163_0` becomes semver `1.10.163`
- directory iteration comes from `std::fs::read_dir()`, so if multiple matching DLLs exist, the returned version is simply the first parseable one encountered

## `is_xse_installed()`

`is_xse_installed(game_path, xse_type) -> bool` is the low-level presence check.

- it joins `game_path` with `xse_type.loader_name()`
- it returns `true` only when that joined path exists and is a file
- it does not inspect DLLs, parse versions, or validate compatibility

## `get_xse_info()`

`get_xse_info(game_path, xse_type) -> XseInfo` is the crate's convenience wrapper.

Behavior visible in source:

1. Build `XseInfo::new(xse_type, game_path.to_path_buf())`.
2. Set `installed` from `check_installed()`.
3. If installed, call `detect_xse_version(info.loader_path(), xse_type)`.
4. If version detection succeeds, store `Some(version)`.
5. If version detection fails, leave `version = None` and still return `XseInfo`.

That last point matters for callers: `get_xse_info()` is fail-soft for version detection.

## Re-exported version helpers

The crate re-exports three helpers from [`classic-version-core`](../../ClassicLib-rs/business-logic/classic-version-core):

- `parse_version()`
- `try_parse_version()`
- `compare_versions()`

These are useful when a caller wants to compare a detected XSE version with version strings resolved elsewhere, but `classic-xse-core` does not currently expose its own higher-level compatibility-check function.

---

## XSE Detection, Version, And Path Flow

The current crate-level flow is intentionally narrow:

1. The caller decides which `XseType` to use, either explicitly or through `XseType::from_game_id()`.
2. The caller already has a game root path or a loader path.
3. Installation detection checks only for the expected loader filename in that directory.
4. Version detection scans sibling DLL filenames in the loader's parent directory.
5. Optional caller-side comparison can then use the re-exported `parse_version()` / `compare_versions()` helpers.

What this crate does not do today:

- it does not discover the game path from registry, logs, or Steam metadata
- it does not resolve the expected XSE version from `VersionRegistry`
- it does not compare a detected version against a registry-backed compatibility matrix
- it does not inspect Address Library state

That makes this crate scangame-adjacent rather than a full validation/orchestration layer.

---

## Error Handling Model

The crate uses `XseError` plus the alias `XseResult<T> = Result<T, XseError>`.

Variants:

- `NotFound(PathBuf)`
- `InvalidType(String)`
- `VersionDetectionFailed(String)`
- `IncompatibleVersion { found, expected }`
- `IoError { source }`
- `PathError(classic_path_core::PathError)`

What contributors should know:

- `FromStr for XseType` returns `InvalidType` for unknown names
- `detect_xse_version()` returns `NotFound` when the loader path is absent and `VersionDetectionFailed` when no parseable matching DLL is found
- `IoError` exists through `#[from] std::io::Error`, but the current `detect_xse_version()` implementation swallows `read_dir()` failure by using `if let Ok(entries) = ...`; not every directory-read problem becomes an error today
- `PathError` is part of the public API, but the current crate source does not visibly call any `classic-path-core` function that would produce it
- `IncompatibleVersion` is public API surface, but current `src/lib.rs` does not construct it anywhere

That means the public error enum is slightly broader than the behavior currently exercised by the main functions.

---

## Platform And Path Notes

- the API accepts generic `Path` / `PathBuf` inputs and compiles cross-platform
- current filename assumptions are Windows-flavored: loader names end in `.exe` and versioned companion files end in `.dll`
- existence checks use `Path::exists()` and `Path::is_file()` directly; the crate does not canonicalize paths or normalize case
- version detection assumes the versioned DLL lives in the same directory as the loader executable
- there is no path-discovery, registry, or documents-folder logic in this crate

Contributor note:

- if a future XSE integration needs log parsing, PE version extraction, or registry-backed expected-version lookup, that would be a behavioral expansion beyond the current public contract and should update this document together with the source

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-shared-core` - provides `GameId` for `XseType::from_game_id()`
- `classic-version-core` - provides the re-exported version parsing/comparison helpers used by `detect_xse_version()`
- `classic-path-core` - currently visible only through `XseError::PathError`
- `semver` - `XseInfo.version` and `detect_xse_version()` return type
- `serde` - serialization derives on `XseType`
- `thiserror` - `XseError`

Related CLASSIC crates and consumers:

- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - exposes `detect_xse_version()` and `is_xse_installed()` to C++ callers in [`cpp-bindings/classic-cpp-bridge/src/game.rs`](../../cpp-bindings/classic-cpp-bridge/src/game.rs)
- [`classic-node`](../../node-bindings/classic-node) - wraps the same core APIs for JavaScript in [`node-bindings/classic-node/src/xse.rs`](../../node-bindings/classic-node/src/xse.rs)
- [`classic-xse-py`](../../python-bindings/classic-xse-py) - wraps the same core APIs for Python in [`python-bindings/classic-xse-py/src/lib.rs`](../../python-bindings/classic-xse-py/src/lib.rs)
- [`classic-scangame-core`](../../business-logic/classic-scangame-core) - adjacent higher-level scan/setup crate; current source does not directly call `classic-xse-core`, but both participate in setup-time XSE-related workflows
- [`classic-version-registry-core`](../../business-logic/classic-version-registry-core) - upstream source of expected XSE metadata for other layers, even though this crate does not query it directly today

---

## Usage Example

This example follows the real public API and shows the common contributor pattern: derive the XSE family from a game, check presence, then request the combined info payload.

```rust
use classic_shared_core::GameId;
use classic_xse_core::{XseType, get_xse_info, is_xse_installed};
use std::path::Path;

let xse_type = XseType::from_game_id(GameId::Fallout4);
let game_root = Path::new("C:/Games/Fallout4");

if is_xse_installed(game_root, xse_type) {
    let info = get_xse_info(game_root, xse_type);

    println!("Loader: {}", info.loader_path().display());
    println!("Installed: {}", info.installed);
    println!("Version: {:?}", info.version);
}
```

If the caller already has a loader path, call `detect_xse_version()` directly instead of first building `XseInfo`.

---

## Contributor Notes And Known Limits

- the full public surface is in `src/lib.rs`; there are no public modules to extend independently
- `get_xse_info()` intentionally hides version-detection failures by returning `version: None` instead of an `XseError`
- `detect_xse_version()` uses filename parsing only; it does not read PE metadata, registry data, or log content
- if multiple matching DLLs exist beside the loader, the returned version depends on `read_dir()` iteration order
- `XseError::IncompatibleVersion` and `XseError::PathError` are public, but the current crate code does not visibly produce them in its main detection flow
- version compatibility policy currently lives outside this crate; callers must bring their own expected-version data and compare it themselves
- the public API still mentions several XSE families beyond Fallout 4, but many surrounding CLASSIC workflows remain Fallout 4-oriented

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- `XseType` mappings, loader names, or DLL prefixes
- version-detection rules or filename assumptions
- whether `get_xse_info()` stays fail-soft on version detection
- any new direct integration with Version Registry, path discovery, or setup/scangame orchestration
