# `classic-file-io-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-file-io-core/`](../../ClassicLib-rs/business-logic/classic-file-io-core).

Crate metadata:

- Crate: `classic-file-io-core`
- Description: `Pure Rust file I/O operations for CLASSIC (no PyO3)`

This crate is the shared Rust file-system utility layer for CLASSIC business-logic crates. It combines async text and byte I/O, directory walking, DDS header parsing, hash utilities, crash-log collection helpers, backup workflows, and config-file generation helpers in one crate.

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- read or write text and bytes with CLASSIC's shared file-I/O helpers
- batch-read or batch-write files with bounded async concurrency
- walk directories or normalize cached path values
- parse DDS headers or validate DDS files for supported game targets
- collect crash logs into the standard `Crash Logs` folder layout
- hash files, compare file similarity, or generate default CLASSIC support files
- back up, restore, or remove game-adjacent files through shared Rust utilities

Do not use this crate for:

- creating or owning a Tokio runtime
- YAML schema parsing or config modeling
- scanlog analysis logic
- database lookup logic
- binding-specific wrapper APIs

Those concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core), and [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core).

---

## Module Map

This crate exposes public modules directly and also re-exports the main integration types from `src/lib.rs`.

### `core`

General file-I/O entry point.

- `FileIOCore` - main async/sync file helper with caches, encoding detection, DDS header reads, path caching, and batch APIs

### `error`

Shared file-I/O error model.

- `FileIOError` - typed error enum used by most crate APIs
- `error::Result<T>` - module-local alias for `Result<T, FileIOError>`

### `encoding`

Text decoding support.

- `EncodingDetector` - UTF-8/BOM-first detector with Windows-1252 fallback

### `dds`

Texture header parsing and validation.

- `DDSHeader` - parsed header summary
- `DDSAnalyzer` - validation helper for game-specific DDS rules
- `DDSIssue` - human-readable validation issue
- `GameTarget` - `Fallout4` or `SkyrimSE`

### `hash`

File hashing helpers.

- `FileHasher` - SHA256 hashing with a process-global cache and Rayon batch helpers

### `log_collection`

Crash-log organization helpers.

- `LogCollector` - moves/copies logs into the standard `Crash Logs` layout
- `CRASH_LOG_PATTERN` and `CRASH_AUTOSCAN_PATTERN` - glob patterns used by collection helpers

### `backup`

Fixed-type backup helpers for game-side files.

- `BackupType` - `XSE`, `ReShade`, `Vulkan`, or `ENB`
- `BackupInfo` - backup metadata snapshot
- `BackupManager` - create, inspect, restore, and remove typed backups

### `game_files`

Pattern-based backup/restore/remove operations.

- `GameFilesManager` - generalized file-group operations over a game root
- `FileOperation` - `Backup`, `Restore`, or `Remove`
- `FileOperationResult` - per-operation summary with partial-failure reporting

### `generation`

Default CLASSIC file generation.

- `FileGeneratorConfig` and `FileGenerator`
- `generate_ignore_file()`
- `generate_local_yaml()`

### `similarity`

Text-file similarity helpers.

- `calculate_similarity()` - file-backed LCS ratio
- `similarity_ratio()` - in-memory string ratio

---

## Public API Surface

## `FileIOCore`

`FileIOCore` is the main contributor-facing integration type for general file work.

Construction:

- `FileIOCore::new(encoding, errors, cache_size, max_concurrent_io)`
- `FileIOCore::default()` -> `FileIOCore::new("utf-8", "ignore", 100, 50)`

Core text and byte I/O:

- `read_file(path) -> Result<String, FileIOError>`
- `write_file(path, content) -> Result<(), FileIOError>`
- `read_lines(path) -> Result<Vec<String>, FileIOError>`
- `stream_lines(path)` and `stream_lines_sync(path)`
- `read_bytes(path) -> Result<Vec<u8>, FileIOError>`
- `write_lines(path, lines) -> Result<(), FileIOError>`
- `write_bytes(path, content) -> Result<(), FileIOError>`
- `append_file(path, content) -> Result<(), FileIOError>`

Traversal, metadata, and cache helpers:

- `clear_cache()`
- `file_exists(path) -> bool`
- `get_file_size(path) -> Option<u64>`
- `is_directory(path) -> bool`
- `metadata_cache_size() -> usize`
- `walk_directory(path, pattern, max_depth) -> Result<Vec<PathBuf>, FileIOError>`
- `ensure_path(path) -> Arc<PathBuf>`

DDS helpers:

- `read_dds_header(path) -> Result<Option<DDSHeader>, FileIOError>`
- `read_dds_headers_batch(paths) -> Vec<(PathBuf, Option<DDSHeader>)>`

Batch I/O:

- `read_multiple_files(paths) -> Vec<(PathBuf, Result<String, FileIOError>)>`
- `write_multiple_files(files) -> Vec<(PathBuf, Result<(), FileIOError>)>`

Behavior worth knowing from the source:

- `read_file()` checks the instance-local read cache first and does not validate mtimes, so external file changes are invisible until the caller clears that `FileIOCore` instance's cache or writes through the same instance.
- `read_file()` always delegates to `read_file_mmap()`, which uses regular async reads below 1 MB and memory mapping at 1 MB or above.
- `write_file()` does not create parent directories; `write_bytes()`, `append_file()`, and `write_multiple_files()` do.
- `write_file()` invalidates both metadata and text-read cache entries for that path; `write_bytes()` invalidates only metadata cache entries.
- `walk_directory()` filters by file name only, not full path, and silently skips traversal entries that `walkdir` returns as errors.
- `read_multiple_files()` and `write_multiple_files()` use `buffer_unordered()`, so result order is not guaranteed to match input order.
- `ensure_path()` caches by the exact input string, not by canonicalized filesystem identity.

## `FileIOError`

`FileIOError` is the shared public error enum for most crate APIs.

Variants:

- `IoError(std::io::Error)`
- `EncodingError(String)`
- `NotFound(String)`
- `InvalidPath(String)`
- `DDSError(String)`
- `JoinError(tokio::task::JoinError)`
- `CacheError(String)`
- `Io(String)`
- `WriteError { path, source }`
- `CreateDirectoryError { path, source }`

Contributor notes:

- `IoError` is the common path for plain `tokio::fs` and `std::fs` failures converted through `#[from]`.
- `EncodingError` is returned by text reads when decoding reports errors and the `FileIOCore` instance was configured with `default_errors != "ignore"`.
- `InvalidPath` is used both for malformed paths and for invalid regex patterns passed to `walk_directory()`.
- `Io(String)` is used in `LogCollector` for formatted glob or directory-setup failures rather than as a wrapped `std::io::Error`.

## `EncodingDetector`

`EncodingDetector` is intentionally simple.

- `new()` and `Default`
- `detect(bytes) -> &'static Encoding`
- `detect_name(bytes) -> String`

Semantics visible in source:

- a UTF-8 BOM forces UTF-8
- otherwise the detector tries UTF-8 decode first
- invalid UTF-8 falls back to Windows-1252

Source-observed limitation:

- `FileIOCore::new()` stores a `default_encoding`, but current read paths visibly consult the detector, not the configured default encoding string.

## DDS API

`DDSHeader` is a lightweight parsed summary with public fields:

- `width`, `height`, `depth`, `mipmap_count`, `format`

Key helpers:

- `DDSHeader::from_bytes(bytes) -> anyhow::Result<Option<DDSHeader>>`
- `has_power_of_2_dimensions()`
- `has_valid_bc_dimensions()`
- `is_reasonable_size()`
- `has_mipmaps()`
- `is_bc_compressed()`

`DDSAnalyzer` adds higher-level validation:

- `DDSAnalyzer::new(game)` and `Default` (`Fallout4`)
- `validate_file(path) -> Vec<DDSIssue>`
- `validate_header(header) -> Vec<DDSIssue>`
- `validate_dimensions(width, height) -> Vec<DDSIssue>`
- `validate_batch(paths) -> Vec<(PathBuf, Vec<DDSIssue>)>`

Contributor notes:

- `DDSHeader::from_bytes()` returns `Ok(None)` for files that are too small, have the wrong magic, or fail DDS parsing; it does not treat every invalid DDS as a hard error.
- `FileIOCore::read_dds_header()` caches only successful header parses.
- `validate_batch()` omits files with zero issues.

## `FileHasher`

`FileHasher` exposes process-wide SHA256 helpers.

- `hash_file(path) -> Result<String, FileIOError>`
- `hash_files_parallel(paths) -> Result<Vec<(PathBuf, Option<String>)>, FileIOError>`
- `hash_files_to_map(paths) -> Result<HashMap<PathBuf, String>, FileIOError>`
- `clear_cache()`
- `cache_size() -> usize`

Contributor notes:

- the hash cache is global and keyed only by `PathBuf`
- the implementation does not compare mtimes or file size before returning a cached hash
- callers that hash mutable files should clear the cache explicitly when freshness matters
- batch hashing is fail-soft per file: the overall call succeeds and failed files get `None`

## `LogCollector`

`LogCollector` handles the standard crash-log collection workflow.

Construction and accessors:

- `LogCollector::new(base_folder, xse_folder, custom_folder)`
- `with_current_dir(xse_folder, custom_folder)`
- `crash_logs_dir()`
- `pastebin_dir()`

Workflow methods:

- `move_from_base_folder() -> Result<usize, FileIOError>`
- `copy_from_xse_folder() -> Result<usize, FileIOError>`
- `collect_crash_logs() -> Result<Vec<PathBuf>, FileIOError>`
- `collect_all() -> Result<Vec<PathBuf>, FileIOError>`

Behavior worth knowing:

- `collect_all()` creates `Crash Logs/` and `Crash Logs/Pastebin/`, then moves base-folder crash logs and autoscan reports, then copies crash logs from the optional XSE folder, then enumerates `crash-*.log` paths.
- base-folder files are moved only when the destination path does not already exist.
- XSE-folder files are copied only when the destination path does not already exist.
- `collect_crash_logs()` searches `Crash Logs` recursively, but the optional custom folder only with a non-recursive `crash-*.log` glob.
- autoscan markdown files are organized by `move_from_base_folder()`, but `collect_crash_logs()` returns only `.log` files.

## Backup and game-file management APIs

There are two separate file-group APIs.

### `BackupManager`

Typed backup workflow for known modding-related file groups.

- `BackupType` variants: `XSE`, `ReShade`, `Vulkan`, `ENB`
- `BackupType::display_name()`, `file_patterns()`, `backup_dir_name()`, `all()`
- `BackupManager::new(game_root, backup_base)`
- `backup_exists(type) -> Result<bool, FileIOError>`
- `get_backup_info(type) -> Result<BackupInfo, FileIOError>`
- `create_backup(type) -> Result<BackupInfo, FileIOError>`
- `restore_backup(type) -> Result<usize, FileIOError>`
- `remove_backup(type) -> Result<(), FileIOError>`

Behavior worth knowing:

- default backup root is `game_root/CLASSIC_Backups`
- backup matching uses a simple `*` prefix/suffix matcher over top-level file names only
- `create_backup()` replaces an existing typed backup directory before copying
- if no files match the backup type's patterns, `create_backup()` removes the newly created backup directory and returns `FileIOError::NotFound`

### `GameFilesManager`

Generalized pattern-based file-group operations.

- `GameFilesManager::new(game_root, backup_root)`
- `backup(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `restore(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `remove(label, patterns) -> Result<FileOperationResult, FileIOError>`
- `FileOperationResult::is_success()` and `is_partial()`

Behavior worth knowing:

- matching is case-insensitive substring matching on top-level entry names in `game_root`
- matching covers both files and directories
- operations run in chunks with bounded Tokio-task concurrency
- per-entry failures are accumulated in `FileOperationResult.errors` instead of failing the whole operation after matching succeeds
- `restore()` restores only entries that both match the requested patterns and exist in the labeled backup directory

## File generation and similarity helpers

`FileGeneratorConfig` has three public fields:

- `ignore_file_content`
- `local_yaml_content`
- `game_name`

`FileGenerator` methods:

- `FileGenerator::new(config)`
- `generate_ignore_file_async() -> Result<bool, FileIOError>`
- `generate_local_yaml_async() -> Result<bool, FileIOError>`
- `generate_all_files_async() -> Result<(bool, bool), FileIOError>`
- `ignore_file_path()`
- `local_yaml_path()`
- `config()`

Standalone helpers:

- `generate_ignore_file(content)`
- `generate_local_yaml(content, game_name)`

Semantics visible in source:

- these helpers write to the current working directory
- returning `false` means the target file already existed and was left unchanged
- `generate_all_files_async()` uses `tokio::try_join!`, so one generation error fails the combined call

Similarity helpers:

- `calculate_similarity(path1, path2) -> Result<f64, std::io::Error>`
- `similarity_ratio(text1, text2) -> f64`

The similarity ratio uses a line-based LCS formula matching the source comments: `(2 * lcs_len) / (len_a + len_b)`.

---

## File Read, Decode, And Traversal Flow

The main source-visible `FileIOCore` text-read flow is:

1. Call `read_file(path)`.
2. The instance-local `quick_cache` read cache is checked by exact `PathBuf` key.
3. On cache miss, the crate caches metadata when possible.
4. `read_file_mmap(path)` chooses the read strategy:
   - files smaller than 1 MB -> `read_file_with_encoding()` using `tokio::fs::read`
   - files at or above 1 MB -> `memmap2::Mmap`
5. Encoding detection runs over the bytes:
   - UTF-8 BOM -> UTF-8
   - otherwise valid UTF-8 -> UTF-8
   - otherwise -> Windows-1252
6. If decoding reports errors and `default_errors != "ignore"`, the call returns `FileIOError::EncodingError`.
7. On success, decoded text is inserted into the read cache and returned.

Important implications:

- the current implementation does not validate that a cached text entry still matches the on-disk file
- mmap reads assume the file is not externally modified during the mapping lifetime
- callers that need a fresh on-disk snapshot should clear caches explicitly before re-reading

Directory traversal flow for `walk_directory()`:

1. Build a `WalkDir` over the requested root, with optional `max_depth`.
2. Compile the optional regex once.
3. Skip traversal errors with `filter_map(|e| e.ok())`.
4. Keep only file entries.
5. If a regex was provided, match it against the file name only.
6. Return collected `PathBuf` values.

DDS header flow for `read_dds_header()`:

1. Check the instance-local DDS LRU cache.
2. Read up to 2048 bytes from the file.
3. Parse with `DDSHeader::from_bytes()`.
4. Cache successful parsed headers and return `Some(header)`.
5. Return `Ok(None)` for non-DDS or invalid DDS content.

Crash-log collection flow for `LogCollector::collect_all()`:

1. Ensure `Crash Logs/` and `Crash Logs/Pastebin/` exist.
2. Move `crash-*.log` and `crash-*-AUTOSCAN.md` from the base folder into `Crash Logs/`.
3. Copy `crash-*.log` from the optional XSE folder into `Crash Logs/`.
4. Return all `crash-*.log` files found under `Crash Logs/` plus the optional custom folder.

---

## Error Handling Model

The crate uses a few different error styles depending on API family.

## `Result<_, FileIOError>` APIs

Most operational APIs use `FileIOError`, including:

- `FileIOCore`
- `BackupManager`
- `GameFilesManager`
- `FileGenerator` and the standalone generation helpers
- `LogCollector`
- `FileHasher`

## Fail-soft APIs

Several APIs intentionally avoid failing the entire batch:

- `FileHasher::hash_files_parallel()` returns `None` for files that fail to hash
- `FileIOCore::read_dds_headers_batch()` maps per-file failures to `None`
- `DDSAnalyzer::validate_file()` returns an issue list instead of an error enum
- `GameFilesManager` stores per-entry failures in `FileOperationResult.errors`
- `walk_directory()` skips per-entry traversal errors instead of surfacing them

## Non-`FileIOError` APIs

- `DDSHeader::from_bytes()` returns `anyhow::Result<Option<DDSHeader>>`
- `calculate_similarity()` returns `std::io::Result<f64>`

That split matters for contributors: this crate mixes strict top-level I/O errors with intentionally tolerant batch helpers. New APIs should be explicit about which style they follow.

---

## Async, Runtime, And Concurrency Notes

This crate exposes async APIs but does not create its own runtime.

- async entry points include most of `FileIOCore`, all of `LogCollector`, all of `BackupManager`, all of `GameFilesManager`, and all generation helpers
- synchronous helpers still exist where they fit better, including `walk_directory()`, `stream_lines_sync()`, `FileHasher`, DDS validation helpers, and similarity helpers
- the crate depends on Tokio, but source in this crate does not visibly construct or export a runtime
- that matches the repo rule that runtime ownership stays outside low-level crates and should remain compatible with the shared CLASSIC runtime model

Concurrency and caching patterns visible in source:

- `FileIOCore` uses separate semaphores for batch reads and batch writes
- text reads use `quick_cache::sync::Cache<PathBuf, String>`
- metadata and path caches use `DashMap`
- DDS headers use an async `RwLock<LruCache<...>>`
- `read_multiple_files()` and `write_multiple_files()` use adaptive `buffer_unordered()` concurrency
- DDS batch validation and hash batch operations use Rayon
- `FileHasher` cache is process-global; `FileIOCore` caches are per-instance but shared across clones because the internals live behind `Arc`

Contributor rule: keep runtime ownership outside this crate. If you add new async work here, do not introduce a second independent Tokio runtime.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `tokio` and `futures` - async file operations and bounded batch concurrency
- `memmap2` - large-file memory-mapped reads
- `quick_cache`, `dashmap`, `parking_lot`, and `lru` - caching and shared-state primitives
- `walkdir` and `glob` - directory traversal and pattern-based collection
- `encoding_rs` - UTF-8 and Windows-1252 decoding
- `ddsfile` - DDS header parsing
- `rayon` - parallel hashing and DDS batch validation
- `sha2` - SHA256 hashing

Related CLASSIC crates:

- [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - downstream consumer of `FileIOCore` for reading crash logs and writing `-AUTOSCAN.md` reports
- [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core) - downstream consumer of `DDSAnalyzer` for texture and game-file checks
- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - neighboring loader crate; both participate in file-backed business logic but at different layers
- [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) and [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - binding layers that depend on stable higher-level behavior built on top of these helpers

Source-observed note:

- `Cargo.toml` declares a dependency on [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core), but the current `src/` files do not visibly expose or call shared-runtime APIs directly.

---

## Usage Example

This example follows the real public API and shows the common contributor path: use `FileIOCore` for cache-aware reads and `walk_directory()` for file discovery.

```rust
use classic_file_io_core::FileIOCore;
use std::path::{Path, PathBuf};

# async fn example() -> Result<(), classic_file_io_core::FileIOError> {
let file_io = FileIOCore::default();

let logs = file_io.walk_directory(
    Path::new("Crash Logs"),
    Some(r"^crash-.*\.log$"),
    Some(2),
)?;

let batch = file_io
    .read_multiple_files(logs.into_iter().take(3).collect::<Vec<PathBuf>>())
    .await;

for (path, result) in batch {
    match result {
        Ok(content) => println!("{} -> {} bytes", path.display(), content.len()),
        Err(err) => eprintln!("{} -> {err}", path.display()),
    }
}

# Ok(())
# }
```

If the caller needs a guaranteed fresh read after out-of-band file changes, call `file_io.clear_cache().await` before re-reading.

---

## Contributor Notes And Known Limits

- The public API is a mix of direct modules plus root-level re-exports; adding or removing exports in `src/lib.rs` changes the contributor-facing surface.
- `FileIOCore` caches are freshness-blind today. They do not compare mtimes or file contents before returning cached text or DDS headers.
- `FileHasher` has the same freshness limitation at process scope; its cache key is only the path.
- `default_encoding` is stored in `FileIOCore`, but current read logic visibly relies on automatic detection instead of using that configured encoding as an override.
- `write_file()` does not create parent directories even though some other write helpers do.
- `walk_directory()` can hide unreadable-entry problems because it drops traversal errors.
- `LogCollector::collect_crash_logs()` does not deduplicate paths across sources.
- `BackupManager` and `GameFilesManager` only scan top-level entries of their configured roots; they do not recursively discover nested matches before copying a matched directory tree.
- `calculate_similarity()` is text-oriented and uses lossy UTF-8 conversion, so it is not a binary diff API.

If you extend this crate, update this document when you change:

- `src/lib.rs` re-exports or public modules
- cache invalidation or freshness rules
- file-read decoding behavior or mmap thresholds
- batch ordering or concurrency behavior
- log-collection directory rules
- backup matching semantics or generated-file paths
