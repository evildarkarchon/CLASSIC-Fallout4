# `classic-file-io-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-file-io-core/`](../../business-logic/classic-file-io-core).

Crate metadata:

- Crate: `classic-file-io-core`
- Description: `Pure Rust file I/O operations for CLASSIC (no PyO3)`

This crate is the shared Rust file-system utility layer for CLASSIC business-logic crates. It combines async text and byte I/O, directory walking, DDS header parsing, and hash utilities in one crate.

YAML Data install, rollback, and self-heal (`install_atomic`, `rollback`, `self_heal`, `InstallOutcome`, `RollbackOutcome`, `SelfHealOutcome`) and Ignore/Local YAML generation (`FileGenerator`, `FileGeneratorConfig`, `generate_ignore_file`, `generate_local_yaml`) moved to [`classic-config-core`](classic-config-core.md#yaml-data-install-rollback-self-heal-and-generation) (#248). The old `classic_file_io_core::atomic_install` and `classic_file_io_core::generation` modules and their root re-exports are gone, with no forwarding re-export: config depends on file I/O, so a re-export would close a dependency cycle. Rust callers import the same names from `classic_config_core` (root, `atomic_install`, or `generation` module). The moved APIs still return this crate's `FileIOError`, so error codes and binding projections are unchanged. With that path gone, this crate no longer depends on `classic-durable-publication`.

The game-target backup (`BackupManager`, `BackupType`, `BackupInfo`) and game-file operations (`GameFilesManager`, `FileOperation`, `FileOperationResult`) moved to [`classic-resource-core`](classic-resource-core.md#game-target-backup-and-game-file-operations) (#250). The old `classic_file_io_core::backup` and `classic_file_io_core::game_files` modules and their root re-exports are gone, with no forwarding re-export: resource depends on file I/O, so a re-export would close a dependency cycle. Rust callers import the same names from `classic_resource_core`. The moved APIs still report failures as this crate's `FileIOError`.

Crash Log collection (`LogCollector`, `CRASH_LOG_PATTERN`, `CRASH_AUTOSCAN_PATTERN`) and Targeted input resolution (`resolve_targeted_inputs`, `TargetedResolution`, `RejectedInput`) moved to [`classic-scanlog-core`](classic-scanlog-core.md#crash-log-collection-and-targeted-input-resolution) (#254). The old `classic_file_io_core::log_collection` module and its root re-exports are gone, with no forwarding re-export: scanlog depends on file I/O, so a re-export would close a dependency cycle. Rust callers import the same names from `classic_scanlog_core`. The moved APIs still report filesystem failures as this crate's `FileIOError`.

Game-target DDS rules (`DDSAnalyzer`, `DDSIssue`, `GameTarget`) moved to [`classic-resource-core`](classic-resource-core.md#game-target-dds-rules-dds) (#249). This crate keeps only neutral DDS header parsing (`DDSHeader` and `FileIOCore`'s cached header readers). The old `classic_file_io_core::dds::{DDSAnalyzer, DDSIssue, GameTarget}` paths and their root re-exports are gone, with no forwarding re-export: resource core depends on file I/O, so a re-export would close a dependency cycle. Rust callers import the same names from `classic_resource_core` (root or `dds` module); values, issue messages, and the `Fallout4` default are unchanged.

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- read or write text and bytes with CLASSIC's shared file-I/O helpers
- batch-read or batch-write files with bounded async concurrency
- walk directories or normalize cached path values
- parse DDS headers (game-target DDS validation is owned by `classic-resource-core`)
- hash files or compare file similarity

Do not use this crate for:

- creating or owning a Tokio runtime
- YAML schema parsing or config modeling
- scanlog analysis logic
- Crash Log collection or Targeted input resolution (owned by `classic-scanlog-core`)
- YAML Data install/rollback/self-heal or Ignore/Local YAML generation (owned by `classic-config-core`)
- game-target backup or game-file backup/restore/remove operations (owned by `classic-resource-core`)
- database lookup logic
- binding-specific wrapper APIs

Those concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), and [`classic-database-core`](../../business-logic/classic-database-core).

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

Neutral texture header parsing.

- `DDSHeader` - parsed header summary

Game-target validation (`DDSAnalyzer`, `DDSIssue`, `GameTarget`) lives in `classic_resource_core::dds`.

### `hash`

File hashing helpers.

- `FileHasher` - SHA256 hashing with a process default cache and Rayon batch helpers
- `FileHashScope` - opaque handle to one hash-cache store and its statistics, for callers that need their own cache


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
- `read_file()` always delegates to `read_file_mmap()`, which uses regular async reads below 1 MB and `MmapOptions::map_copy_read_only()` at 1 MB or above.
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
- `Io(String)` is used by scanlog core's `LogCollector` for formatted glob or directory-setup failures rather than as a wrapped `std::io::Error`; Crash Log collection kept this error type when it moved so binding error projections stay unchanged.

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

Game-target validation over a parsed `DDSHeader` (`DDSAnalyzer`, `DDSIssue`, `GameTarget`) is documented in [`classic-resource-core`](classic-resource-core.md#game-target-dds-rules-dds).

Contributor notes:

- `DDSHeader::from_bytes()` returns `Ok(None)` for files that are too small, have the wrong magic, or fail DDS parsing; it does not treat every invalid DDS as a hard error.
- `FileIOCore::read_dds_header()` caches only successful header parses.

## `FileHasher`

`FileHasher` exposes SHA256 helpers backed by the process default `FileHashScope`.

- `hash_file(path) -> Result<String, FileIOError>`
- `hash_files_parallel(paths) -> Result<Vec<(PathBuf, Option<String>)>, FileIOError>`
- `hash_files_to_map(paths) -> Result<HashMap<PathBuf, String>, FileIOError>`
- `cache_stats() -> CacheStats`
- `reset_cache_stats()`
- `clear_cache()`
- `cache_size() -> usize`

`CacheStats` exposes the canonical Phase 4 cache contract:

- `hits: u64`
- `misses: u64`
- `hit_rate: f64`
- `size: usize`
- `capacity: usize`

Contributor notes:

- the unscoped `FileHasher` cache is the process default scope and is keyed only by `PathBuf`
- the hash cache is bounded to 1024 entries through `quick_cache::sync::Cache`
- the implementation does not compare mtimes or file size before returning a cached hash
- callers that hash mutable files should clear the cache explicitly when freshness matters
- `clear_cache()` empties cached entries only; `reset_cache_stats()` clears hit/miss counters without dropping entries
- Phase 4 validates bounded `quick_cache` eviction semantics rather than strict LRU victim order, because the locked cache implementation is `quick_cache`
- batch hashing is fail-soft per file: the overall call succeeds and failed files get `None`

## File Hash Scopes

Every hash-cache store sits behind an opaque `FileHashScope` handle, so a
binding adapter can give each caller its own cached hashes and statistics
while unscoped callers keep the process default.

- `FileHashScope::default_scope()` - the store behind every unscoped `FileHasher` function
- `FileHashScope::new_isolated()` - a fresh, empty store that shares no entries or counters with any other scope
- `hash_file`, `hash_files_parallel`, `hash_files_to_map`, `cache_stats`, `reset_cache_stats`, `clear_cache`, `cache_size` - same contract as the `FileHasher` function of the same name, applied to this scope only

Contract:

- cloning a handle shares its store; two handles compare equal exactly when they name the same store
- every scope has the same 1024-entry bounded capacity, eviction, hit/miss counting, and clear/reset rules; filling one scope never evicts another scope's entries
- hashing, clearing, and resetting through one scope never changes another scope's entries or statistics, including the default scope
- handles are `Send + Sync + 'static` and keep naming the same store when moved into Rayon or async work

Current owners: the Rust, CXX, and Node `FileHasher` surfaces use the default
scope. In the one Python native extension, three facades each hold their own
isolated scope, so their caches and statistics stay independent: the
`classic_file_io.FileHasher` facade, Game Setup Intake runs started through
`classic_scangame`, and the FCX setup step of Crash Log Scan Runs started
through `classic_scanlog`. Game Setup Intake selects a scope with
`GameSetupIntake::run_in_hash_scope` / `run_in_scopes` (see
`classic-scangame-core.md`); a Crash Log Scan Run carries one through
`scan_run::contract::execute_in_scopes` (see `classic-scanlog-core.md`), while
the unscoped `execute` keeps the default scope. No Python facade reads, clears,
or resets the default scope; a Python facade that later needs hash-cache
controls must select its own isolated scope rather than expose the default one.

## Similarity helpers

Ignore/Local YAML generation is documented in [`classic-config-core`](classic-config-core.md#yaml-data-install-rollback-self-heal-and-generation).

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
   - files at or above 1 MB -> `memmap2::MmapOptions::map_copy_read_only()`
5. Encoding detection runs over the bytes:
   - UTF-8 BOM -> UTF-8
   - otherwise valid UTF-8 -> UTF-8
   - otherwise -> Windows-1252
6. If decoding reports errors and `default_errors != "ignore"`, the call returns `FileIOError::EncodingError`.
7. On success, decoded text is inserted into the read cache and returned.

Important implications:

- the current implementation does not validate that a cached text entry still matches the on-disk file
- Phase 6 treats `map_copy_read_only()` as this repo's safer snapshot-style mitigation for large-file reads, while still keeping the existing decode/error contract and the upstream `unsafe` constructor boundary in mind
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

---

## Error Handling Model

The crate uses a few different error styles depending on API family.

## `Result<_, FileIOError>` APIs

Most operational APIs use `FileIOError`, including:

- `FileIOCore`
- `FileHasher`

`FileIOError` is also the error type of APIs that moved out of this crate and kept it so binding error projections stay unchanged: scanlog core's Crash Log collection, resource core's `BackupManager` and `GameFilesManager`, and config core's YAML Data install/rollback/self-heal and Ignore/Local YAML generation.

## Fail-soft APIs

Several APIs intentionally avoid failing the entire batch:

- `FileHasher::hash_files_parallel()` returns `None` for files that fail to hash
- `FileIOCore::read_dds_headers_batch()` maps per-file failures to `None`
- `walk_directory()` skips per-entry traversal errors instead of surfacing them

## Non-`FileIOError` APIs

- `DDSHeader::from_bytes()` returns `anyhow::Result<Option<DDSHeader>>`
- `calculate_similarity()` returns `std::io::Result<f64>`

That split matters for contributors: this crate mixes strict top-level I/O errors with intentionally tolerant batch helpers. New APIs should be explicit about which style they follow.

---

## Async, Runtime, And Concurrency Notes

This crate exposes async APIs but does not create its own runtime.

- async entry points include most of `FileIOCore`
- synchronous helpers still exist where they fit better, including `walk_directory()`, `stream_lines_sync()`, `FileHasher`, `DDSHeader::from_bytes()`, and similarity helpers
- the crate depends on Tokio but does not construct or export a runtime, and it no longer depends on `classic-operation-context`: scoped discovery cancellation moved with Crash Log collection to `classic-scanlog-core`
- that matches the repo rule that runtime ownership stays outside low-level crates and should remain compatible with the shared CLASSIC runtime model

Concurrency and caching patterns visible in source:

- `FileIOCore` uses separate semaphores for batch reads and batch writes
- text reads use `quick_cache::sync::Cache<PathBuf, String>`
- metadata and path caches use `DashMap`
- DDS headers use an async `RwLock<LruCache<...>>`
- `read_multiple_files()` and `write_multiple_files()` use adaptive `buffer_unordered()` concurrency
- DDS header batch reads and hash batch operations use Rayon
- `FileHasher` uses the process default `FileHashScope`; isolated scopes and `FileIOCore` caches are per-handle but shared across clones because the internals live behind `Arc`

Contributor rule: keep runtime ownership outside this crate. If you add new async work here, do not introduce a second independent Tokio runtime.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `tokio` and `futures` - async file operations and bounded batch concurrency
- `memmap2` - large-file memory-mapped reads
- `quick_cache`, `dashmap`, `parking_lot`, and `lru` - caching and shared-state primitives
- `walkdir` - directory traversal
- `encoding_rs` - UTF-8 and Windows-1252 decoding
- `ddsfile` - DDS header parsing
- `rayon` - parallel hashing and DDS header batch reads
- `sha2` - SHA256 hashing

Related CLASSIC crates:

- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - downstream consumer of `FileIOCore` for reading crash logs and writing `-AUTOSCAN.md` reports, and owner of Crash Log collection and Targeted input resolution
- [`classic-resource-core`](classic-resource-core.md) - downstream owner of game-target DDS rules applied to this crate's `DDSHeader`
- [`classic-scangame-core`](../../business-logic/classic-scangame-core) - downstream consumer of file I/O helpers for game-file checks
- [`classic-config-core`](classic-config-core.md) - downstream owner of YAML Data install/rollback/self-heal and Ignore/Local YAML generation, which return this crate's `FileIOError`
- [`classic-resource-core`](classic-resource-core.md) - downstream owner of the game-target backup and game-file operations, which return this crate's `FileIOError`
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) and [`classic-node`](../../node-bindings/classic-node) - binding layers that depend on stable higher-level behavior built on top of these helpers

Source-observed notes:

- `Cargo.toml` declares a dependency on [`classic-shared-core`](../../foundation/classic-shared-core), but the current `src/` files do not visibly expose or call shared-runtime APIs directly.
- The crate has no `classic-xse-core`, `classic-operation-context`, or `classic-durable-publication` dependency; `tests/dependency_boundary.rs` guards that inward boundary.

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
- `FileHasher` and every `FileHashScope` have the same freshness limitation; the cache key is only the path.
- `default_encoding` is stored in `FileIOCore`, but current read logic visibly relies on automatic detection instead of using that configured encoding as an override.
- `write_file()` does not create parent directories even though some other write helpers do.
- `walk_directory()` can hide unreadable-entry problems because it drops traversal errors.
- `calculate_similarity()` is text-oriented and uses lossy UTF-8 conversion, so it is not a binary diff API.

If you extend this crate, update this document when you change:

- `src/lib.rs` re-exports or public modules
- cache invalidation or freshness rules
- file-read decoding behavior or mmap thresholds
- batch ordering or concurrency behavior
