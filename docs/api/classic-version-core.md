# `classic-version-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-version-core/`](../../business-logic/classic-version-core).

Crate metadata:

- Crate: `classic-version-core`
- Description: `Transitional facade over shared-core version helpers and Version Registry known-version queries for CLASSIC (no PyO3)`

This crate owns no behavior. It is a transitional facade that keeps two groups of historical import paths resolving until the crate identity retires (issue #258):

- The loose version and PE helpers now live in [`classic_shared_core::version`](classic-shared-core.md#loose-versions-and-pe-helpers-version) (issue #243): `parse_version()`, `try_parse_version()`, `compare_versions()`, `format_version()`, the three text-extraction helpers, `VersionError` / `VersionResult<T>`, and the `pe_version` submodule with `is_valid_executable_path()`, `extract_pe_version()`, and `PeVersionError` / `PeVersionResult<T>`.
- The known-version queries `is_known_fallout4_version()` and `is_known_f4se_version()` now live in [`classic-version-registry-core`](classic-version-registry-core.md#known-version-queries) (issue #244), the Version Registry that is their sole policy owner.

Every re-export is the owner's item unchanged, so `classic_version_core::parse_version` and `classic_shared_core::version::parse_version` are the same function, `classic_version_core::pe_version::PeVersionError` is the shared-core type, and `classic_version_core::is_known_fallout4_version` is `classic_version_registry_core::is_known_fallout4_version`. Values, error variants, and messages did not change. The known-version re-exports answer from the Version Registry's process default snapshot.

New callers should import the owners directly. Workspace callers in `classic-xse-core`, `classic-scangame-core`, `classic-scanlog-core` (including its Rust conformance participant), `classic-cpp-bridge`, `classic-node`, and `classic-version-py` already do; none of them depends on this crate.

Parity ownership: CXX, Node, and Python rows for the loose and PE helpers name `classic-shared-core`, and the known-version rows name `classic-version-registry-core`, because the behavior lives there. Do not restore `classic-version-core` as the owner of those rows during a baseline refresh. Only Rust-only `@rust` proxy rows for items this facade still re-exports name `classic-version-core`. The `version-f4se` conformance pack and the `version-extraction.known-fallout4` capability name `classic-version-registry-core`; the other version packs name `classic-shared-core`.

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

- `is_known_fallout4_version()`, `is_known_f4se_version()` (see [Known-version queries](classic-version-registry-core.md#known-version-queries))
- `VersionInfo`, `VersionRegistry`, `VersionRegistryError`, `get_version_registry()`, `NULL_VERSION`

There are no items owned by this crate and no public traits.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-shared-core` - owner of the re-exported loose version and PE helpers
- `classic-version-registry-core` - owner of the re-exported known-version queries and registry types

Related CLASSIC crates and consumers:

- [`classic-shared-core`](classic-shared-core.md#loose-versions-and-pe-helpers-version) - loose parsing, extraction, formatting, and PE extraction
- [`classic-version-registry-core`](classic-version-registry-core.md) - registry implementation, matching, loading, known-version queries, and `VersionRegistryScope`
- [`classic-node`](../../node-bindings/classic-node) and [`classic-version-py`](../../python-bindings/classic-version-py) - call the known-version queries on the Version Registry and the loose/PE helpers in shared core; the Python facade answers from its own `VersionRegistryScope`

---

## Usage Example

New code imports the owners:

```rust,no_run
use classic_shared_core::version::parse_version;
use classic_version_registry_core::{is_known_f4se_version, is_known_fallout4_version};

let game_version = parse_version("1.10.163.0")?;
assert!(is_known_fallout4_version(&game_version));

let f4se_version = parse_version("0.6.23")?;
assert!(is_known_f4se_version(&f4se_version));

# Ok::<(), Box<dyn std::error::Error>>(())
```

The historical `classic_version_core::{parse_version, is_known_fallout4_version, ...}` paths name the same items until #258.

---

## Contributor Notes And Known Limits

- every root item is a re-export; adding or removing one changes this crate's public contract without changing behavior
- do not add new behavior here: put domain-neutral helpers in `classic_shared_core::version` and known-version policy in `classic-version-registry-core`
- there is no helper that converts the 4-part PE tuple into `semver::Version` or matches PE versions directly against Version Registry data

If you change this crate, update this document when you change:

- root-level re-exports in `src/lib.rs`
- the retirement plan (#258)
