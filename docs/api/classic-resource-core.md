# `classic-resource-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-resource-core/`](../../business-logic/classic-resource-core).

Crate metadata:

- Crate: `classic-resource-core`
- Description: `Resource management for game files (no PyO3)`

This crate is the small Rust resource-discovery layer for CLASSIC. It detects resource types from file extensions, enumerates supported files under a directory tree, provides a lightweight `ResourceInfo` struct, and validates that an individual resource path exists and points to a file.

It also owns the game-target backup (`backup`: `BackupManager`, `BackupType`, `BackupInfo`) and game-file operations (`game_files`: `GameFilesManager`, `FileOperation`, `FileOperationResult`), which moved here from `classic-file-io-core` in #250. See [Game-Target Backup And Game-File Operations](#game-target-backup-and-game-file-operations).

Resource discovery is synchronous; the backup and game-file operations are async and run on the caller's (shared) Tokio runtime. The crate does not parse Bethesda file formats, mount BA2 archives, or own a runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- classify a path as a texture, mesh, script, plugin, sound, animation, interface, strings, archive, config file, or `Other`
- enumerate supported resource files under a game or mod directory
- count supported resources by detected type
- attach basic metadata (`path`, detected type, file size) to resource entries
- validate that a candidate resource path exists and is a readable file
- back up, restore, or remove a fixed game-target file group (XSE, ReShade, Vulkan, ENB) under the game root
- back up, restore, or remove pattern-matched game-root entries under a labeled backup directory

Do not use this crate for:

- parsing plugin, BA2, NIF, DDS, or INI contents
- resolving game-install or documents paths
- validating archive internals or mod compatibility rules
- general async file I/O, shared runtime ownership, or UI/binding-specific behavior

Those concerns live in related crates such as [`classic-path-core`](../../business-logic/classic-path-core), [`classic-scangame-core`](../../business-logic/classic-scangame-core), and the Node/Python binding wrappers.

---

## Module And API Map

Resource discovery lives at the crate root in `src/lib.rs`. The `backup` and `game_files` public submodules hold the game-target backup and game-file operations; their main types are also re-exported from the crate root.

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

- `backup::{BackupInfo, BackupManager, BackupType}` and `game_files::{FileOperation, FileOperationResult, GameFilesManager}` (#250)

The former `PathError` / `PathResult` re-exports from `classic-path-core` ended in #245: the generic path error is owned by `classic_shared_core::path_core`, which callers import directly. `ResourceError::PathError` wraps that shared-core type, and the crate's native result alias is `ResourceResult<T>`.

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

- if a caller needs strict path validation before enumeration, validate the directory separately with the [`classic_shared_core::path_core`](classic-shared-core.md#generic-path-primitives-path_core) helpers first

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
- `PathError` conversion wraps `classic_shared_core::path_core::PathError`, but current root-level functions do not call the shared-core path validators directly

## Game-Target Backup And Game-File Operations

These two file-group operations moved here from `classic-file-io-core` in #250. The old `classic_file_io_core::backup` and `classic_file_io_core::game_files` modules and their root re-exports are gone, with no forwarding re-export: resource depends on file I/O, so a re-export would close a dependency cycle. Rust callers import the same names from `classic_resource_core`. Both operations still report failures as [`classic_file_io_core::FileIOError`](classic-file-io-core.md#fileioerror), not `ResourceError`, so every CXX, Node, and Python error projection is unchanged. Neither uses Durable Publication.

The game-target backup is distinct from the version-labelled XSE backup: it keeps one fixed directory per backup type under the game root and does not label backups by version.

### `backup` - game-target backup

Typed backup workflow for known modding-related file groups.

- `BackupType` variants: `XSE`, `ReShade`, `Vulkan`, `ENB`
- `BackupType::display_name()`, `file_patterns()`, `backup_dir_name()`, `all()`
- `BackupInfo` - `backup_type`, `backup_dir`, `created_at`, `file_count`, `exists`
- `BackupManager::new(game_root, backup_base)`
- `backup_exists(type) -> Result<bool, FileIOError>`
- `get_backup_info(type) -> Result<BackupInfo, FileIOError>`
- `create_backup(type) -> Result<BackupInfo, FileIOError>`
- `restore_backup(type) -> Result<usize, FileIOError>`
- `remove_backup(type) -> Result<(), FileIOError>`

Destination, conflict, and recovery behavior:

- default backup root is `game_root/CLASSIC_Backups`; each type uses its own fixed directory (`XSE_Backup`, `ReShade_Backup`, `Vulkan_Backup`, `ENB_Backup`)
- backup matching uses a simple `*` prefix/suffix matcher over top-level file names only
- `create_backup()` replaces an existing typed backup directory before copying
- if no files match the backup type's patterns, `create_backup()` removes the newly created backup directory and returns `FileIOError::NotFound`
- `restore_backup()` copies every top-level file in the typed backup directory back into the game root, overwriting existing files, and returns `FileIOError::NotFound` when no backup exists
- `remove_backup()` succeeds when the backup directory is already absent

### `game_files` - game-file operations

Generalized pattern-based file-group operations.

- `GameFilesManager::new(game_root, backup_root)`
- `backup(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `restore(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `remove(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `FileOperation` - `Backup`, `Restore`, or `Remove` (displayed as `BACKUP`, `RESTORE`, `REMOVE`)
- `FileOperationResult` - `operation`, `label`, `files_affected`, `errors`; `is_success()` and `is_partial()`

Behavior worth knowing:

- matching is case-insensitive substring matching on top-level entry names in `game_root`, and covers both files and directories
- a missing `game_root` returns `FileIOError::NotFound`
- `backup()` copies into `backup_root/<label>/`, overwriting files and replacing matched directories
- operations run in chunks with bounded Tokio-task concurrency
- per-entry failures are accumulated in `FileOperationResult.errors` instead of failing the whole operation after matching succeeds
- `restore()` restores only entries that both match the requested patterns and exist in the labeled backup directory
- `remove()` treats an already-missing entry as success

Both managers scan only top-level entries of their configured roots; they do not recursively discover nested matches before copying a matched directory tree.

Callers: the CXX bridge (`files.rs`: `backup_manager_*`, `game_files_*`), the Node binding (`JsBackupManager`, `JsGameFilesManager`), and the TUI backup workflow. Python does not expose either operation.

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

Resource discovery uses one top-level domain error type, `ResourceError`, plus a `ResourceResult<T>` alias.

In practice, the public API splits into two styles:

- pure classification helpers (`detect_resource_type()`, `is_supported_resource()`, `ResourceType::from_str()`) are infallible
- filesystem-touching helpers (`enumerate_resources()`, `count_resources_by_type()`, `validate_resource()`) return `ResourceResult<_>`
- the game-target backup and game-file operations return `Result<_, classic_file_io_core::FileIOError>`, the error type they had before moving here, so binding error projections stay unchanged

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
- `classic-shared-core` - `path_core::PathError` wrapped by `ResourceError::PathError`
- [`classic-file-io-core`](classic-file-io-core.md) - `FileIOError`, returned by the game-target backup and game-file operations (file I/O never depends back on this crate)
- `tokio`, `tracing`, and `chrono` - async file operations, operation logging, and backup timestamps for `backup` and `game_files`

Declared dependency with no visible use in current `src/lib.rs`:

- none after Phase 3 cleanup

Related CLASSIC crates and wrappers:

- [`classic-path-core`](../../business-logic/classic-path-core) - neighboring game/documents path layer (this crate no longer depends on it)
- [`classic-scangame-core`](../../business-logic/classic-scangame-core) - higher-level install and mod scanning crate; it handles real scan orchestration rather than reusing this crate directly in current source
- [`classic-resource-py`](../../python-bindings/classic-resource-py) - Python wrapper for this crate's public API
- [`classic-node`](../../node-bindings/classic-node) - Node binding surface that forwards this crate's detection, enumeration, count, and validation helpers, plus `JsBackupManager` and `JsGameFilesManager`
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - CXX `files` bridge module that wraps `BackupManager` and `GameFilesManager`

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

If the caller needs stricter directory validation before enumeration, validate the root separately with [`classic_shared_core::path_core`](classic-shared-core.md#generic-path-primitives-path_core) before calling `enumerate_resources()`.

---

## Contributor Notes And Known Limits

- the public surface is `src/lib.rs` plus the `backup` and `game_files` modules; any new `pub` item there changes the crate API directly
- `tests/game_file_dependency_boundary.rs` guards that this crate keeps no Durable Publication edge for the game-file policy and that file I/O never depends back on it
- `ResourceType` is extension-based only; it does not inspect file headers or contents
- `ResourceType::from_str()` is intentionally permissive and maps unknown strings to `Other`
- `enumerate_resources()` is best-effort because `WalkDir` entry errors are dropped
- `count_resources_by_type()` omits zero-count categories and inherits the same best-effort traversal behavior
- `validate_resource()` validates file existence/readability only; it does not verify supported type or file format integrity
- `ArchiveError` is present in the public/dependency surface, but the current source does not expose real archive-management behavior
- the crate-level docs mention BA2 archive support and path resolution, but current contributor-visible APIs are narrower than that description

If you extend this crate, update this document when you change:

- the `ResourceType` variants or extension mapping
- `ResourceType` parsing or serialization behavior
- enumeration error semantics or traversal policy
- `ResourceInfo` fields or constructors
- validation rules in `validate_resource()`
- any future archive/path-resolution APIs that make the crate broader than its current extension-based helper role
