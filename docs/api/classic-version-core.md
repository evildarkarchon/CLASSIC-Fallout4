# `classic-version-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-version-core/`](../../ClassicLib-rs/business-logic/classic-version-core).

Crate metadata:

- Crate: `classic-version-core`
- Description: `Version detection and parsing utilities for CLASSIC (no PyO3)`

This crate is CLASSIC's small shared Rust helper layer for version parsing, text extraction, and Windows PE file version reads. It also re-exports a narrow slice of Version Registry access so downstream crates can combine low-level parsing with registry-backed compatibility data.

It is a synchronous business-logic crate. It does not own a Tokio runtime, UI surface, or binding layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- parse loose version strings into `semver::Version`
- compare normalized versions with standard semver ordering
- extract version-like values from filenames, logs, or free-form text
- check whether a parsed version matches known non-VR Fallout 4 game or F4SE versions
- read a Windows PE file's embedded `VS_VERSIONINFO` version tuple from an `.exe` or `.dll`
- access `get_version_registry()` and related registry types directly from the Version Registry owner crate

Do not use this crate for:

- version-family matching or nearest-version fallback logic
- loading registry YAML or managing built-in version defaults
- higher-level XSE compatibility decisions
- async file I/O or runtime ownership
- binding-specific wrapper DTOs

Those concerns live in related crates such as [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core), [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core), and the Node/Python/C++ binding crates.

---

## Module And API Map

This crate exposes one public submodule plus a root-level helper API.

## Root-level API

- `VersionError`, `VersionResult<T>` - error model for parse/extract helpers
- `parse_version()` - normalize a loose version string into `semver::Version`
- `try_parse_version()` - non-throwing parse wrapper
- `compare_versions()` - semver ordering helper
- `is_known_fallout4_version()` - registry-backed check against known non-VR Fallout 4 game versions
- `is_known_f4se_version()` - registry-backed check against known non-VR Fallout 4 XSE compatibility versions
- `extract_version_from_filename()` - first version-like match from a filename
- `extract_version_from_log()` - first log-oriented version match, with filename-style fallback
- `extract_all_versions()` - collect all regex-matched versions from text
- `format_version()` - stringify a parsed version with an optional prefix

## Public submodule

- `pe_version` - PE-specific executable validation and version-resource extraction
  - `is_valid_executable_path()`
  - `extract_pe_version()`
  - `PeVersionError`, `PeVersionResult<T>`

## Root-level re-exports

- `extract_pe_version()`, `PeVersionError`, `PeVersionResult<T>` from `pe_version`
- `VersionInfo`, `VersionRegistry`, `VersionRegistryError`, `get_version_registry()`, and `NULL_VERSION` from [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core)

Contributor note:

- the registry types are only re-exported here; their actual matching/loading behavior lives upstream in [`classic-version-registry-core`](classic-version-registry-core.md)
- there are no public traits in this crate today

---

## Public API Surface

## `VersionError` and `VersionResult<T>`

The root helper functions use `VersionError`.

Variants:

- `ParseError(String)`
- `EmptyVersion`
- `NotFound(String)`
- `InvalidFormat(String)`

Behavior worth knowing:

- `parse_version()` currently returns `EmptyVersion` only for an actually empty string; whitespace-only input becomes `InvalidFormat` after trimming
- `VersionError::NotFound` is part of the public API surface, but current root functions do not visibly construct it

## `parse_version()` and `try_parse_version()`

`parse_version(version_str) -> VersionResult<semver::Version>` is the main normalization entry point.

Accepted source-visible input shapes:

- `1.10.163`
- `1.10.163.0`
- `v1.10.163`
- `V1.10.163`
- `1.10`

Behavior visible in source:

- trims surrounding whitespace
- strips a leading `v` or `V`
- requires at least `major.minor`
- defaults `patch = 0` when only two numeric components are present
- ignores the build component used by many game version strings because `semver::Version` stores only three numeric fields

Important limitation from the implementation:

- the function does not enforce an upper bound on component count; any components after the third numeric part are ignored rather than rejected
- pre-release or build-metadata semver syntax such as `1.2.3-alpha` is not supported here

`try_parse_version()` is just `parse_version().ok()`.

## `compare_versions()`

`compare_versions(v1, v2) -> Ordering` is a thin wrapper over `semver::Version::cmp()`.

- no registry data is involved
- comparison uses the normalized 3-part versions returned by `parse_version()` or other semver constructors

## `is_known_fallout4_version()`

`is_known_fallout4_version(version) -> bool` checks a parsed semver value against Version Registry entries.

Source-visible behavior:

- calls `get_version_registry()`
- queries `registry.get_all_for_game("Fallout4", Some(false))`
- converts each registry `GameVersion` to `semver::Version` by dropping the fourth build component
- returns `true` on exact semver equality only

Contributor note:

- this helper is explicitly non-VR; it does not inspect `Fallout4VR` entries

## `is_known_f4se_version()`

`is_known_f4se_version(version) -> bool` checks a parsed semver value against the registry's `xse.compatible_version` strings for non-VR Fallout 4 entries.

Source-visible behavior:

- calls `get_version_registry()`
- queries the same `registry.get_all_for_game("Fallout4", Some(false))` set as the game-version helper
- reads `info.xse.compatible_version` when present
- parses that string with `try_parse_version()` before comparing

Contributor note:

- this helper is about known registry compatibility strings, not about probing an installed loader or DLL on disk
- like `is_known_fallout4_version()`, it does not currently include VR entries

## Text extraction helpers

### `extract_version_from_filename()`

`extract_version_from_filename(filename) -> Option<Version>` tries regex patterns in this order:

1. `v?major.minor.patch.build`
2. `v?major.minor.patch`
3. `v?major.minor`

Behavior worth knowing:

- returns the first regex match found by the first pattern that matches
- ignores the fourth numeric component when building `semver::Version`
- does not require separators around the version token beyond what the regex naturally matches

### `extract_version_from_log()`

`extract_version_from_log(log_content) -> Option<Version>` first looks for:

- `(?i)version[:\s]+v?major.minor.patch(.build)?`

If that fails, it falls back to `extract_version_from_filename(log_content)`.

Behavior worth knowing:

- it returns only the first matching version
- in mixed-content logs, the first `version ...` line wins even if later lines contain a different version of interest
- the fallback means any free-form text containing a filename-style version can still produce a result even without the word `version`

### `extract_all_versions()`

`extract_all_versions(content) -> Vec<Version>` collects all matches of:

- `v?major.minor.patch(.build)?`

Behavior worth knowing:

- build components are ignored
- duplicate versions are not removed
- matches are returned in regex iteration order

## `format_version()`

`format_version(version, prefix) -> String` returns either:

- `version.to_string()` when `prefix` is `None`
- `format!("{prefix}{version}")` when a prefix is supplied

This is purely formatting; it does not validate or reparse the version.

## `pe_version` module

The `pe_version` module contains the crate's file-format-specific helpers.

### `is_valid_executable_path()`

`is_valid_executable_path(path) -> bool` checks:

- path exists
- path is a file
- extension is `.exe` or `.dll`, case-insensitive

It does not verify that the file is actually a valid PE image.

### `extract_pe_version()`

`extract_pe_version(path) -> PeVersionResult<(u16, u16, u16, u16)>` reads the PE file from disk and extracts the Windows `VS_FIXEDFILEINFO` file version tuple.

Source-visible flow:

1. Validate the path with `is_valid_executable_path()`.
2. Read the full file into memory with `std::fs::read()`.
3. Parse the bytes with `pelite::PeFile::from_bytes()`.
4. Open PE resources.
5. Read `version_info()`.
6. Read `fixed()` and return `(Major, Minor, Patch, Build)`.

This is the crate's only helper that preserves a four-part version instead of converting down to semver.

---

## Version Parsing And Detection Flow

The current source exposes three practical flows.

## Flow 1: Parse and compare loose version strings

1. Call `parse_version()` or `try_parse_version()`.
2. The crate normalizes the input to `semver::Version`.
3. Compare with `compare_versions()` or pass the normalized value into higher-level code.

This is the flow reused by [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core), which parses DLL filename versions through this crate before doing XSE-specific work.

## Flow 2: Extract version-like text from filenames or logs

1. Call `extract_version_from_filename()`, `extract_version_from_log()`, or `extract_all_versions()`.
2. Regex extraction returns one or more `semver::Version` values.
3. Optional caller-side follow-up can compare them, stringify them, or check them with the registry-backed helpers.

These extraction helpers do not validate against known CLASSIC versions by themselves.

## Flow 3: Read executable or DLL file version metadata

1. Call `extract_pe_version(path)` directly or through the root-level re-export.
2. The crate validates the path shape and extension.
3. It parses PE resources and returns the four Windows version components.
4. If the caller needs a semver-compatible value, the caller must decide how to down-convert or compare the tuple.

Contributor note:

- there is no combined helper today that reads a PE version and then matches it against Version Registry metadata in the same API

---

## Error Handling Model

This crate has two public error families.

## Root helper errors: `VersionError`

Used by:

- `parse_version()`
- `try_parse_version()` indirectly through `Option`

Contributor notes:

- extraction helpers return `Option`, not `VersionResult`, so failed regex parsing usually becomes `None` instead of a structured error
- `compare_versions()` and `format_version()` cannot fail once the caller already has a valid `semver::Version`

## PE helper errors: `PeVersionError`

Variants:

- `IoError { path, source }`
- `InvalidPe(String)`
- `NoVersionInfo(PathBuf)`
- `InvalidPath(PathBuf)`

Behavior worth knowing:

- `InvalidPath` covers both nonexistent paths and wrong file extensions because both fail `is_valid_executable_path()` first
- `InvalidPe` means the file passed the extension/file checks but `pelite` could not parse a usable PE image or resources block
- `NoVersionInfo` means the PE parsed, but no readable version resource was found

---

## Platform And File-Format Notes

- the root parse/compare/extract helpers are cross-platform and operate only on strings or text
- PE helpers are Windows-format-specific because they read Portable Executable version resources, but they can still be called on any platform if the caller points at a real PE file
- `extract_pe_version()` reads the entire file into memory before parsing; it is not a streaming API
- `is_valid_executable_path()` uses extension checks only and accepts both `.exe` and `.dll`
- the crate does not inspect ELF, Mach-O, or other non-PE binary metadata formats

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `semver` - normalized 3-part version representation and ordering
- `regex` - filename/log/text extraction
- `pelite` - PE resource parsing for `extract_pe_version()`
- `thiserror` - typed error enums
- `classic-version-registry-core` - source of the crate's registry-related re-exports

Related CLASSIC crates and consumers:

- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) - actual registry implementation and immediate re-export source for `VersionRegistry`, `VersionInfo`, `VersionRegistryError`, `get_version_registry()`, and `NULL_VERSION`
- [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core) - re-exports `parse_version()`, `try_parse_version()`, and `compare_versions()` and uses them during DLL filename parsing
- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) - uses `extract_pe_version()` to expose executable version data to C++ callers
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) and [`classic-version-py`](../../ClassicLib-rs/python-bindings/classic-version-py) - binding layers over the parse/extract/format helpers and PE helpers

In practice, `classic-version-core` is the low-level utility layer beneath XSE detection, bindings, and some executable-version probes.

---

## Usage Example

This example follows the real public API and shows the common contributor pattern: normalize a version string, check it against registry-backed Fallout 4 data, and then inspect a PE file version separately.

```rust,no_run
use classic_version_core::{extract_pe_version, is_known_fallout4_version, parse_version};
use std::path::Path;

let game_version = parse_version("1.10.163.0")?;
assert!(is_known_fallout4_version(&game_version));

let (major, minor, patch, build) = extract_pe_version(
    Path::new("C:/Games/Fallout4/Fallout4.exe"),
)?;

println!("Normalized semver: {game_version}");
println!("PE file version: {major}.{minor}.{patch}.{build}");

# Ok::<(), Box<dyn std::error::Error>>(())
```

If you only need filename or log parsing, use `extract_version_from_filename()` or `extract_version_from_log()` instead of reading PE metadata.

---

## Contributor Notes And Known Limits

- `src/lib.rs` defines almost the entire public surface; `pe_version` is the only public submodule
- registry access in this crate is re-export-only; adding or removing those re-exports changes this crate's public contract without changing registry behavior itself
- `parse_version()` ignores extra numeric components after the patch component instead of rejecting them
- `is_known_fallout4_version()` and `is_known_f4se_version()` currently check only non-VR `Fallout4` registry entries
- extraction helpers are regex-based convenience functions, not strict parsers for any official file or log format
- `extract_version_from_log()` returns the first matching version and may therefore pick an XSE version line before a later game-version line
- `extract_all_versions()` preserves duplicates and match order
- there is no helper today that converts the 4-part PE tuple into `semver::Version` or matches PE versions directly against Version Registry data
- `VersionError::NotFound` is public but not currently used by the source-visible helper implementations

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- regex patterns or extraction precedence
- `parse_version()` acceptance rules
- the scope of the known-version helpers, especially VR behavior
- PE validation or version-resource extraction behavior
