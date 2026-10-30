# `classic-xse-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-xse-core/`](../../business-logic/classic-xse-core).

Crate metadata:

- Crate: `classic-xse-core`
- Description: `Script Extender (XSE) utilities for CLASSIC`

This crate is the Rust-side XSE module for CLASSIC. It identifies which script extender a game uses, resolves the XSE Folder used for Crash Log collection, checks whether the expected loader exists in a game directory, and tries to derive an XSE version from sibling DLL filenames.

It is a synchronous business-logic crate. It does not own a Tokio runtime, game-install discovery flow, or binding surface.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- map a supported `GameId` to the expected XSE family (`F4SE`, `F4SEVR`, `SKSE64`, `SFSE`)
- parse or format XSE type identifiers
- check whether an expected XSE loader executable exists in a known game directory
- derive an XSE version from versioned DLL filenames next to the loader
- package installation status and optional detected version into one `XseInfo` value
- resolve the XSE Folder from Local.yaml, an optional configured docs root, or Version Registry-backed documents discovery

Do not use this crate for:

- finding the game installation path in the first place
- registry or YAML-driven compatibility decisions outside XSE Folder resolution
- Address Library validation
- crashgen or broader setup scanning orchestration
- binding-specific wrapper DTOs

Those concerns live in related crates such as [`classic-path-core`](../../business-logic/classic-path-core), [`classic-version-registry-core`](../../business-logic/classic-version-registry-core), [`classic-scangame-core`](../../business-logic/classic-scangame-core), and the C++ bridge.

---

## Module And API Map

This crate currently exposes a single public file, `src/lib.rs`. There are no public modules or public traits; the contributor-facing API is all at the crate root.

## Root-level API

- `XseType` - supported script-extender families and their naming helpers
- `XseInfo` - simple installation-status payload for one game directory and XSE type
- `detect_xse_version()` - version detection from the loader executable's embedded PE version resource
- `detect_xse_runtime_dll_version()` - version detection from one runtime DLL's embedded PE version resource
- `is_xse_installed()` - loader existence check for a game directory
- `get_xse_info()` - combined installation + optional version probe
- `XseGameLocalFacts` - XSE's narrow input for config-owned Game Local facts (`docs_folder_xse`, `root_folder_docs`)
- `resolve_xse_folder_from_game_local_facts()` / `resolve_xse_folder_from_game_local_facts_in_version_registry_scope()` - fail-soft XSE Folder derivation from caller-supplied Game Local facts, reading Version Registry metadata from the default snapshot or a caller-selected scope
- `resolve_xse_log_from_game_local_facts()` / `resolve_xse_log_from_game_local_facts_in_version_registry_scope()` - locate the XSE log inside the XSE Folder the same precedence selects; `Ok(None)` for absence, `XseLogError` for operational failure (see [XSE log](#xse-log-from-game-local-facts))
- `XseLogError` - the XSE log resolvers' typed operational failure (`Inspect { path, source }`)
- `xse_folder_name(acronym)` - the sole owner of the on-disk XSE folder-name rule: maps a Version Registry XSE acronym to the folder used both under the documents root (the XSE Folder) and under `Data/<folder>/Plugins`; `F4SEVR` maps to the shared `F4SE` folder, every other acronym (trimmed) is its own folder. Game Setup Intake's `plugins_path` uses it. Rust-only: no CXX export
- `XseError`, `XseResult<T>` - crate-specific error model

## Root-level re-exports

None. The crate used to re-export `compare_versions()`, `parse_version()`, and `try_parse_version()`; those re-exports ended when the loose version helpers moved to [`classic_shared_core::version`](classic-shared-core.md#loose-versions-and-pe-helpers-version) (issue #243). Import them from shared core.

Contributor note:

- `classic-path-core` supports documents-folder discovery (`DocsPathFinder`); the generic `PathError` carried by `XseError::PathError` is owned by `classic_shared_core::path_core` (#245)
- the crate reads no YAML: the former Local.yaml-reading `resolve_xse_folder_for_scan*` entry points moved to [`classic-scangame-core`](classic-scangame-core.md#xse-folder-from-the-game-local-document) (#252), which reads the facts through config and calls this crate
- the crate does not depend on `classic-config-core`; config-owned Game Local facts arrive as plain `XseGameLocalFacts` values (`tests/dependency_boundary.rs` guards the manifest edge)
- `classic-version-registry-core` is the source of truth for docs folder names, Steam app IDs, and XSE acronyms used by XSE Folder derivation

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
- `XseType::runtime_dll_name(major, minor, patch) -> String` - the runtime DLL built for one game runtime, for example `F4SE.runtime_dll_name(1, 11, 240) == "f4se_1_11_240.dll"`
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
2. Read the loader's PE `VS_FIXEDFILEINFO` file version with `extract_pe_version()` from [`classic_shared_core::version::pe_version`](classic-shared-core.md#loose-versions-and-pe-helpers-version).
3. Drop the leading component and use the remaining three as `major.minor.patch`.
4. If the loader is not a readable PE file or carries no version resource, return `XseError::VersionDetectionFailed`.

Important contributor details:

- every script extender stamps its binaries from one resource template, `FILEVERSION 0, major, minor, beta`, so the leading component is a placeholder zero: F4SE 0.6.23 is stamped `0.0.6.23` and SKSE64 2.2.6 is stamped `0.2.2.6`
- sibling runtime DLLs such as `f4se_1_10_163.dll` are deliberately not consulted. Their filenames name the *game* runtime the build targets, not the extender's version, and one install can carry several of them. An older implementation parsed those filenames and reported the game version as the F4SE version
- the loader's version is the version of the installed extender package; it is not the version of whichever runtime DLL the loader will inject (use `detect_xse_runtime_dll_version()` for that)
- `xse_type` only feeds the diagnostic message

## `detect_xse_runtime_dll_version()`

`detect_xse_runtime_dll_version(dll_path, xse_type) -> XseResult<Version>` reads one runtime DLL's version exactly as `detect_xse_version()` reads the loader's: same `NotFound` and `VersionDetectionFailed` errors, same leading-placeholder conversion. Runtime DLLs carry the same stamp as their release's loader, so F4SE 0.7.9's `f4se_1_11_240.dll` reports `0.7.9`.

Build `dll_path` from the game root and `XseType::runtime_dll_name()` for the detected game runtime. That DLL is the build that actually runs in the game. Game Setup Intake therefore uses its version for the `xse_version` check. A separate `xse_loader_version` check confirms that the loader is the release meant for that runtime, since each release's loader pairs with its own runtime DLLs. A leftover DLL for some other runtime is never read.

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

## XSE Folder from Game Local facts

The Game Local document is config-owned ([Game Local Facts](classic-config-core.md#game-local-facts)), and this crate must not depend on config. So XSE accepts the two facts it needs as a plain value:

```rust
pub struct XseGameLocalFacts {
    pub docs_folder_xse: Option<PathBuf>,  // Game_Info.Docs_Folder_XSE
    pub root_folder_docs: Option<PathBuf>, // Game_Info.Root_Folder_Docs
}
```

`resolve_xse_folder_from_game_local_facts(&facts, game, selected_game_version, configured_docs_root) -> Option<PathBuf>` is the XSE Folder derivation.

Resolution order:

1. Return `docs_folder_xse` when present and non-empty.
2. Derive `<root_folder_docs>/<XSE docs folder>` when `root_folder_docs` is present and non-empty.
3. Derive `<configured_docs_root>/<XSE docs folder>` when the caller supplies a non-empty configured docs root.
4. Use Version Registry metadata plus `DocsPathFinder` to discover the docs root, then append the XSE docs folder.

Behavior worth knowing:

- the function is fail-soft and returns `None` for absent facts, an unknown game/version, or documents discovery failure; empty paths count as absent
- `Fallout4VR` with `selected_game_version = "auto"` resolves as the VR registry entry
- Version Registry XSE metadata selects the XSE family, but the derived documents subfolder uses the on-disk XSE docs folder name from `xse_folder_name()`; Fallout 4 VR uses the shared `F4SE` folder even though its XSE acronym is `F4SEVR`
- an explicit `docs_folder_xse` always wins over derived values, and needs no registry entry
- Version Registry metadata comes from the process default snapshot; `resolve_xse_folder_from_game_local_facts_in_version_registry_scope(..., &VersionRegistryScope)` applies the same order but reads only the caller's [scope](classic-version-registry-core.md#version-registry-scopes), taking its snapshot only for a Fallout 4 game (before the explicit-folder check, as it always has)

Callers that start from an installation's `CLASSIC Data` directory use [`classic_scangame_core::resolve_xse_folder_for_scan`](classic-scangame-core.md#xse-folder-from-the-game-local-document) (and its `_in_version_registry_scope` form), which reads the facts with `classic_config_core::read_game_local_facts` and calls this function. Crash Log collection goes through it (`classic_scanlog_core::LogCollector::new_for_scan(...)` and the Crash Log Scan Run's Standard discovery, which passes the run's scope). Standard crash scans keep custom folders additive to XSE Folder collection.

This crate is the `domainOwner` of the `xse-folder` Binding Compliance Suite family. Its `xse-folder.derive` capability exercises `resolve_xse_folder_from_game_local_facts` directly with supplied facts (Rust only; no binding exposes the facts resolver). The Local.yaml composition is credited separately to `classic-scangame-core` as `xse-folder.resolve`.

## XSE log from Game Local facts

`resolve_xse_log_from_game_local_facts(&facts, game, selected_game_version, configured_docs_root) -> Result<Option<PathBuf>, XseLogError>` is the one Rust owner of the XSE log location (#283). Before it, only the GUI knew the log, through hard-coded `f4se.log`/`f4sevr.log` names and a VR-first probe.

- The log is looked for only in the XSE Folder that `resolve_xse_folder_from_game_local_facts` selects, with the same precedence. A log in a lower-precedence folder is never used instead.
- The file name is the selected version's Version Registry XSE acronym, trimmed and lower-cased, plus `.log`. Fallout 4 gets `F4SE/f4se.log`; Fallout 4 VR (`Fallout4VR` with `auto`, or `VR`) gets its own `F4SE/f4sevr.log` in the shared folder. An edition never borrows the other edition's log.
- `Ok(Some(path))` is an existing log file. `Ok(None)` means no XSE Folder resolved, the version has no XSE metadata (for example an explicit folder for an unknown game), or the folder or log is missing; a directory named like the log is not a log.
- `Err(XseLogError::Inspect { path, source })` means the candidate log could not be inspected for a reason other than absence (for example access denied, or a path that is not a valid file name). Its message starts with `cannot inspect XSE log `.
- `resolve_xse_log_from_game_local_facts_in_version_registry_scope(..., &VersionRegistryScope)` reads Version Registry metadata only from the caller's scope.

Callers that start from `CLASSIC Data` use [`classic_scangame_core::resolve_xse_log_for_scan`](classic-scangame-core.md#xse-folder-from-the-game-local-document), which is what CXX exposes as `classic::xse::resolve_xse_log_for_scan` (the GUI's setup-detection hint calls it). The `xse-folder` family's `xse-folder.log` capability runs on the Rust and CXX participants.

## Version helpers

The crate does not re-export version helpers. When a caller wants to compare a detected XSE version with version strings resolved elsewhere, it uses `parse_version()` and `compare_versions()` from [`classic_shared_core::version`](classic-shared-core.md#loose-versions-and-pe-helpers-version) directly. `classic-xse-core` does not currently expose its own higher-level compatibility-check function.

---

## XSE Detection, Version, And Path Flow

The current crate-level flow is intentionally narrow:

1. For Crash Log collection or the setup-detection hint, the caller supplies Game Local facts to `resolve_xse_folder_from_game_local_facts()` (usually through scangame's `resolve_xse_folder_for_scan()`) and treats `None` as "no XSE Folder".
2. For setup checks, the caller decides which `XseType` to use, either explicitly or through `XseType::from_game_id()`.
3. The caller already has a game root path or a loader path.
4. Installation detection checks only for the expected loader filename in that directory.
5. Version detection scans sibling DLL filenames in the loader's parent directory.
6. Optional caller-side comparison can then use the shared-core `parse_version()` / `compare_versions()` helpers.

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
- `PathError(classic_shared_core::path_core::PathError)`

What contributors should know:

- `FromStr for XseType` returns `InvalidType` for unknown names
- `detect_xse_version()` and `detect_xse_runtime_dll_version()` return `NotFound` when the path is absent and `VersionDetectionFailed` when the file cannot be read as a PE file or has no version resource
- `IoError` exists through `#[from] std::io::Error`, but `detect_xse_version()` folds a loader read failure into `VersionDetectionFailed` rather than surfacing `IoError`
- `PathError` is part of the public API; XSE Folder discovery uses `DocsPathFinder` but returns `None` rather than exposing path-discovery errors
- `IncompatibleVersion` is public API surface, but current `src/lib.rs` does not construct it anywhere

The XSE log resolvers use their own `XseLogError` instead, so absence (`Ok(None)`) and operational failure stay distinct; see [XSE log](#xse-log-from-game-local-facts).

That means the public error enum is slightly broader than the behavior currently exercised by the main functions.

---

## Platform And Path Notes

- the API accepts generic `Path` / `PathBuf` inputs and compiles cross-platform
- current filename assumptions are Windows-flavored: loader names end in `.exe` and versioned companion files end in `.dll`
- existence checks use `Path::exists()` and `Path::is_file()` directly; the crate does not canonicalize paths or normalize case
- version detection assumes the versioned DLL lives in the same directory as the loader executable
- XSE Folder resolution uses Version Registry metadata and `DocsPathFinder`; game-install path discovery remains outside this crate

Contributor note:

- if a future XSE integration needs log parsing, PE version extraction, or registry-backed expected-version lookup, that would be a behavioral expansion beyond the current public contract and should update this document together with the source

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-shared-core` - provides `GameId` for `XseType::from_game_id()`, the `version::pe_version::extract_pe_version()` helper used by `detect_xse_version()`, and the `path_core::PathError` wrapped by `XseError::PathError`
- `classic-path-core` - `DocsPathFinder` for XSE Folder discovery
- `semver` - `XseInfo.version` and `detect_xse_version()` return type
- `serde` - serialization derives on `XseType`
- `thiserror` - `XseError`

Related CLASSIC crates and consumers:

- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - exposes XSE helpers, including XSE Folder resolution, to C++ callers in [`cpp-bindings/classic-cpp-bridge/src/xse.rs`](../../cpp-bindings/classic-cpp-bridge/src/xse.rs)
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
- `detect_xse_version()` reads only the loader's PE version resource; it does not read runtime DLL filenames, registry data, or log content
- `XseError::IncompatibleVersion` and `XseError::PathError` are public, but the current crate code does not visibly produce them in its main detection flow
- version compatibility policy currently lives outside this crate; callers must bring their own expected-version data and compare it themselves
- the public API still mentions several XSE families beyond Fallout 4, but many surrounding CLASSIC workflows remain Fallout 4-oriented

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- `XseType` mappings, loader names, or DLL prefixes
- version-detection rules or filename assumptions
- whether `get_xse_info()` stays fail-soft on version detection
- any new direct integration with Version Registry, path discovery, or setup/scangame orchestration
