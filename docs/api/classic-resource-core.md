# `classic-resource-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-resource-core/`](../../ClassicLib-rs/business-logic/classic-resource-core).

Crate metadata:

- Crate: `classic-resource-core`
- Description: `Resource management for game files (no PyO3)`

This crate is the small Rust resource-discovery layer for CLASSIC. It detects resource types from file extensions, enumerates supported files under a directory tree, provides a lightweight `ResourceInfo` struct, and validates that an individual resource path exists and points to a file.

It is a synchronous business-logic crate. It does not parse Bethesda file formats, mount BA2 archives, or own a runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- classify a path as a texture, mesh, script, plugin, sound, animation, interface, strings, archive, config file, or `Other`
- enumerate supported resource files under a game or mod directory
- count supported resources by detected type
- attach basic metadata (`path`, detected type, file size) to resource entries
- validate that a candidate resource path exists and is a readable file

Do not use this crate for:

- parsing plugin, BA2, NIF, DDS, or INI contents
- resolving game-install or documents paths
- validating archive internals or mod compatibility rules
- async I/O, shared runtime ownership, or UI/binding-specific behavior

Those concerns live in related crates such as [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core), [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core), and the Node/Python binding wrappers.

---

## Module And API Map

This crate currently exposes a single public file, `src/lib.rs`. There are no public submodules; the contributor-facing API is all at the crate root.

## Root-level types and aliases

- `ResourceType` - resource-category enum used for extension-based classification
- `ResourceInfo` - small struct holding a path, detected type, and size
- `ResourceError` - crate-specific error enum for validation/enumeration paths
- `ResourceResult<T>` - `Result<T, ResourceError>`

## Root-level free functions

- `detect_resource_type(path)` - extension-based type detection
- `is_supported_resource(path)` - `detect_resource_type(path) != ResourceType::Other`
- `enumerate_resources(root, filter_type)` - recursive supported-file discovery
- `count_resources_by_type(root)` - grouped counts from `enumerate_resources()`
- `validate_resource(path)` - existence + file-kind + metadata access check

## Root-level re-exports

- `PathError`, `PathResult` from [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core)

Contributor note:

- `PathResult` is re-exported but not used by this crate's own public functions today; the crate's native result alias is `ResourceResult<T>`

---

## Public API Surface

## `ResourceType`

`ResourceType` is the main shared enum for classifying game resources.

Variants:

- `Texture`
- `Mesh`
- `Script`
- `Plugin`
- `Sound`
- `Animation`
- `Interface`
- `Strings`
- `Archive`
- `Config`
- `Other`

Important traits and conversions:

- `Serialize`, `Deserialize`, `Clone`, `Copy`, `Hash`, `Eq`
- `FromStr<Err = Infallible>`

Important methods:

- `as_str() -> &'static str`
- `extensions() -> &'static [&'static str]`

Current extension mapping:

- `Texture` -> `dds`, `png`, `jpg`, `tga`
- `Mesh` -> `nif`
- `Script` -> `pex`, `psc`
- `Plugin` -> `esp`, `esm`, `esl`
- `Sound` -> `wav`, `xwm`, `fuz`
- `Animation` -> `hkx`
- `Interface` -> `swf`
- `Strings` -> `strings`, `dlstrings`, `ilstrings`
- `Archive` -> `ba2`, `bsa`
- `Config` -> `ini`
- `Other` -> no extensions

Behavior worth knowing from the source:

- `FromStr` lowercases input and never fails; unrecognized strings map to `ResourceType::Other`
- that means callers cannot use `parse::<ResourceType>()` to distinguish typo input from an intentional `Other` category
- Serde uses Rust variant names because there are no custom `serde` rename attributes in the crate

## `detect_resource_type()` and `is_supported_resource()`

`detect_resource_type(path)` is the low-level classifier.

- it looks only at `path.extension()`
- matching is case-insensitive
- directory names and parent path segments do not affect classification
- files without an extension, or with an unrecognized extension, return `ResourceType::Other`

`is_supported_resource(path)` is the thin convenience wrapper.

- it returns `true` for any non-`Other` type
- it does not check whether the path exists or is readable

Important contributor limit:

- the crate description mentions BA2 archive support, but current source only classifies `.ba2` and `.bsa` by extension; it does not expose archive-reading APIs

## `ResourceInfo`

`ResourceInfo` is the crate's lightweight metadata struct.

Fields:

- `path: PathBuf`
- `resource_type: ResourceType`
- `size: u64`

Important constructors:

- `ResourceInfo::new(path)`
- `ResourceInfo::with_size(path, size)`

Behavior worth knowing:

- both constructors recompute `resource_type` from the supplied path via `detect_resource_type()`
- `new()` sets `size` to `0`; it does not query the filesystem
- `with_size()` trusts the caller-provided size and does not validate it against the filesystem

## `enumerate_resources()`

`enumerate_resources(root, filter_type)` is the main recursive discovery API.

Arguments:

- `root: &Path`
- `filter_type: Option<ResourceType>`

Return value:

- `ResourceResult<Vec<ResourceInfo>>`

Behavior visible in source:

- uses `walkdir::WalkDir` recursively with `follow_links(false)`
- skips non-files
- skips any file whose detected type is `ResourceType::Other`
- if `filter_type` is present, only matching resource types are returned
- file size comes from `DirEntry::metadata().len()` and falls back to `0` when metadata lookup fails for that entry

Source-visible limitation:

- the implementation uses `.filter_map(Result::ok)` on `WalkDir`, so traversal errors are silently dropped rather than surfaced as `ResourceError::IoError`
- because of that, the current implementation is more best-effort than the doc comments in `src/lib.rs` suggest

Practical implication:

- if a caller needs strict path validation before enumeration, validate the directory separately with [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core) helpers first

## `count_resources_by_type()`

`count_resources_by_type(root)` is a small aggregation helper built on `enumerate_resources()`.

- it groups the returned `ResourceInfo` values by `resource_type`
- it returns `Vec<(ResourceType, usize)>`
- the output is sorted by `ResourceType::as_str()`
- resource types with zero matches are omitted from the result

## `validate_resource()`

`validate_resource(path)` is the crate's strictest per-file validator.

It checks, in order:

1. `path.exists()`
2. `path.is_file()`
3. `path.metadata()`

Returned errors:

- missing path -> `ResourceError::NotFound(path)`
- existing non-file path -> `ResourceError::InvalidType("Path is not a file: ...")`
- metadata/readability failure -> `ResourceError::IoError`

Contributor note:

- `validate_resource()` does not require the file to be a supported `ResourceType`; a real file with an unknown extension can still validate successfully

## `ResourceError` and `ResourceResult<T>`

`ResourceError` is the crate-wide error enum.

Variants:

- `NotFound(PathBuf)`
- `InvalidType(String)`
- `ArchiveError(String)`
- `IoError { source: std::io::Error }`
- `PathError(PathError)` via `#[from]`

Behavior worth knowing:

- `ArchiveError` is part of the public API surface, but the current `src/lib.rs` implementation does not construct it anywhere
- `PathError` conversion exists because the crate re-exports path error types, but current root-level functions do not call into `classic-path-core` validators directly

---

## Resource Discovery And Management Flow

The current source supports a simple extension-first flow:

1. Start with a candidate path or root directory.
2. Use `detect_resource_type()` or `is_supported_resource()` for cheap classification.
3. If you need recursive discovery, call `enumerate_resources(root, filter_type)`.
4. For reporting, feed the returned `ResourceInfo` list into `count_resources_by_type()` or your own grouping logic.
5. For a specific file that must exist, call `validate_resource(path)` before consuming it elsewhere.

This crate does not currently add higher-level resource resolution features such as:

- search-order merging between loose files and archives
- game-root or `Data/` path construction
- BA2 member lookup
- resource format inspection beyond filename extension

That is why it fits best as a small shared helper layer, not as a complete resource pipeline.

---

## Error Handling Model

This crate uses one top-level domain error type, `ResourceError`, plus a `ResourceResult<T>` alias.

In practice, the public API splits into two styles:

- pure classification helpers (`detect_resource_type()`, `is_supported_resource()`, `ResourceType::from_str()`) are infallible
- filesystem-touching helpers (`enumerate_resources()`, `count_resources_by_type()`, `validate_resource()`) return `ResourceResult<_>`

Important contributor caveats from the current implementation:

- `enumerate_resources()` and `count_resources_by_type()` are nominally fallible but do not currently preserve `WalkDir` traversal errors because failed entries are filtered out
- `validate_resource()` is the only public function that reliably reports strict per-path failures today
- there is no separate error type for unsupported resource formats; unknown extensions are represented as `ResourceType::Other`, not an error

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `walkdir` - recursive directory traversal for enumeration
- `serde` - serialization/deserialization for `ResourceType`
- `thiserror` - `ResourceError`
- `classic-path-core` - re-exported `PathError` and `PathResult`

Declared dependency with no visible use in current `src/lib.rs`:

- `classic-constants-core`

Related CLASSIC crates and wrappers:

- [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core) - neighboring path-validation layer whose error types are re-exported here
- [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core) - higher-level install and mod scanning crate; it handles real scan orchestration rather than reusing this crate directly in current source
- [`classic-resource-py`](../../ClassicLib-rs/python-bindings/classic-resource-py) - Python wrapper for this crate's public API
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - Node binding surface that forwards this crate's detection, enumeration, count, and validation helpers

Binding collaboration visible in source today:

- both Node and Python wrappers expose `ResourceType`, `ResourceInfo`, `detect_resource_type()`, `is_supported_resource()`, `enumerate_resources()`, `count_resources_by_type()`, and `validate_resource()`
- this makes the root-level Rust API the effective contract for multiple language surfaces

---

## Usage Example

This example stays within the real public API: classify a path, enumerate matching resources, then validate a specific file.

```rust,no_run
use classic_resource_core::{
    ResourceType, count_resources_by_type, detect_resource_type, enumerate_resources,
    validate_resource,
};
use std::path::Path;

let plugins_dir = Path::new("C:/Games/Fallout4/Data");

assert_eq!(
    detect_resource_type(Path::new("Scripts/MyQuest.pex")),
    ResourceType::Script
);

let plugins = enumerate_resources(plugins_dir, Some(ResourceType::Plugin))?;
println!("Found {} plugin files", plugins.len());

for (kind, count) in count_resources_by_type(plugins_dir)? {
    println!("{}: {}", kind.as_str(), count);
}

validate_resource(Path::new("C:/Games/Fallout4/Data/example.esp"))?;
# Ok::<(), classic_resource_core::ResourceError>(())
```

If the caller needs stricter directory validation before enumeration, validate the root separately with [`classic-path-core`](classic-path-core.md) before calling `enumerate_resources()`.

---

## Contributor Notes And Known Limits

- the full public surface lives in `src/lib.rs`; any new `pub` item there changes the crate API directly
- `ResourceType` is extension-based only; it does not inspect file headers or contents
- `ResourceType::from_str()` is intentionally permissive and maps unknown strings to `Other`
- `enumerate_resources()` is best-effort because `WalkDir` entry errors are dropped
- `count_resources_by_type()` omits zero-count categories and inherits the same best-effort traversal behavior
- `validate_resource()` validates file existence/readability only; it does not verify supported type or file format integrity
- `ArchiveError` and the `classic-constants-core` dependency are present in the public/dependency surface, but the current source does not expose real archive-management behavior or visible constants usage
- the crate-level docs mention BA2 archive support and path resolution, but current contributor-visible APIs are narrower than that description

If you extend this crate, update this document when you change:

- the `ResourceType` variants or extension mapping
- `ResourceType` parsing or serialization behavior
- enumeration error semantics or traversal policy
- `ResourceInfo` fields or constructors
- validation rules in `validate_resource()`
- any future archive/path-resolution APIs that make the crate broader than its current extension-based helper role
