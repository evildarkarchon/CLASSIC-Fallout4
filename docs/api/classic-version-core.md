# `classic-version-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-version-core/`](../../business-logic/classic-version-core).

Crate metadata:

- Crate: `classic-version-core`
- Description: `Known game-version queries and a transitional facade over shared-core version helpers for CLASSIC (no PyO3)`

The loose version and PE helpers this crate used to own now live in [`classic_shared_core::version`](classic-shared-core.md#loose-versions-and-pe-helpers-version) (issue #243): `parse_version()`, `try_parse_version()`, `compare_versions()`, `format_version()`, the three text-extraction helpers, `VersionError` / `VersionResult<T>`, and the `pe_version` submodule with `is_valid_executable_path()`, `extract_pe_version()`, and `PeVersionError` / `PeVersionResult<T>`. This crate re-exports every one of those items unchanged, so `classic_version_core::parse_version` and `classic_shared_core::version::parse_version` are the same function, and `classic_version_core::pe_version::PeVersionError` is the shared-core type. Values, error variants, and messages did not change.

What this crate still owns is the known-version policy: `is_known_fallout4_version()` and `is_known_f4se_version()`. They answer from the Version Registry and move to that owner in issue #244.

The crate identity is scheduled for retirement (issue #258). Until then its re-exported paths, including `classic_version_core::pe_version::*`, stay valid; new callers should import `classic_shared_core::version` directly. Workspace callers in `classic-xse-core`, `classic-scangame-core`, `classic-cpp-bridge`, `classic-node`, `classic-version-py`, and the scanlog Rust conformance participant already do.

Parity ownership: CXX, Node, and Python rows for the loose and PE helpers name `classic-shared-core`, because the behavior lives there. Do not restore `classic-version-core` as the owner of those rows during a baseline refresh. Only the known-version rows, and Rust-only `@rust` proxy rows for items this facade still re-exports, name `classic-version-core`. The `version-f4se` conformance pack keeps this crate as its `domainOwner`; the other version packs name `classic-shared-core`.

It is a synchronous business-logic crate. It does not own a Tokio runtime, UI surface, or binding layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Root-Level Public API

Re-exported from `classic_shared_core::version` (see the [shared-core guide](classic-shared-core.md#loose-versions-and-pe-helpers-version) for full semantics):

- `VersionError`, `VersionResult<T>`
- `parse_version()`, `try_parse_version()`, `compare_versions()`, `format_version()`
- `extract_version_from_filename()`, `extract_version_from_log()`, `extract_all_versions()`
- `extract_pe_version()`, `is_valid_executable_path()`, `PeVersionError`, `PeVersionResult<T>`
- the public module `pe_version`, re-exported as a module so `classic_version_core::pe_version::extract_pe_version` still resolves

Re-exported from [`classic-version-registry-core`](classic-version-registry-core.md):

- `VersionInfo`, `VersionRegistry`, `VersionRegistryError`, `get_version_registry()`, `NULL_VERSION`

Owned by this crate:

- `is_known_fallout4_version()`
- `is_known_f4se_version()`

There are no public traits in this crate.

---

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
- parses that string with the shared-core `try_parse_version()` before comparing

Contributor note:

- this helper is about known registry compatibility strings, not about probing an installed loader or DLL on disk
- like `is_known_fallout4_version()`, it does not currently include VR entries

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-shared-core` - owner of the re-exported loose version and PE helpers
- `classic-version-registry-core` - source of the known-version data and the registry re-exports
- `semver` - the `semver::Version` values the known-version helpers compare

Related CLASSIC crates and consumers:

- [`classic-shared-core`](classic-shared-core.md#loose-versions-and-pe-helpers-version) - loose parsing, extraction, formatting, and PE extraction
- [`classic-version-registry-core`](classic-version-registry-core.md) - actual registry implementation, matching, and loading
- [`classic-node`](../../node-bindings/classic-node) and [`classic-version-py`](../../python-bindings/classic-version-py) - call `is_known_fallout4_version()` (and, for Python, `is_known_f4se_version()`) here and the loose/PE helpers in shared core

---

## Usage Example

```rust,no_run
use classic_shared_core::version::parse_version;
use classic_version_core::{is_known_f4se_version, is_known_fallout4_version};

let game_version = parse_version("1.10.163.0")?;
assert!(is_known_fallout4_version(&game_version));

let f4se_version = parse_version("0.6.23")?;
assert!(is_known_f4se_version(&f4se_version));

# Ok::<(), Box<dyn std::error::Error>>(())
```

---

## Contributor Notes And Known Limits

- the loose/PE re-exports and the registry re-exports are facades; adding or removing them changes this crate's public contract without changing behavior
- `is_known_fallout4_version()` and `is_known_f4se_version()` currently check only non-VR `Fallout4` registry entries
- there is no helper that converts the 4-part PE tuple into `semver::Version` or matches PE versions directly against Version Registry data

If you change this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- the scope of the known-version helpers, especially VR behavior
