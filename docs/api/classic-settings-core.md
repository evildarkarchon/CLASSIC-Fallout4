# `classic-settings-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-settings-core/`](../../ClassicLib-rs/business-logic/classic-settings-core).

Crate metadata:

- Crate: `classic-settings-core`
- Description: `Core YAML settings cache with dual sync/async API`

This crate is a small YAML settings utility layer with two distinct responsibilities:

1. Load YAML documents from disk through synchronous or asynchronous helpers.
2. Parse and merge YAML streams for higher-level callers that want one mapping result.
3. Cache loaded YAML documents behind caller-chosen string keys for later reuse.

It also exposes a public `validators` module for lightweight settings-shape checks and string-to-type coercion.

This is not the main CLASSIC config-modeling crate. It works at the level of raw `yaml_rust2::Yaml` documents and simple validation helpers rather than typed application settings structs.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- read one or more YAML files into `Vec<Yaml>`
- merge a multi-document YAML stream into one mapping with deterministic override rules
- cache parsed YAML documents under a logical string key
- expose the same YAML-loading behavior through sync and async Rust APIs
- inspect or clear cache state from tests, bindings, or startup code
- run lightweight validation or coercion for settings-like scalar values

Do not use this crate for:

- typed CLASSIC config modeling such as `ClassicConfig` or `YamlDataCore`
- automatic file freshness checks or mtime-based cache invalidation
- owning a Tokio runtime
- deep schema validation or business-rule enforcement for scan/config workflows

Those higher-level concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), and binding crates that wrap this cache for JS or Python consumers.

---

## Module And API Map

This crate exposes most of its API from the crate root and one public module.

## Root-level re-exports from `lib.rs`

- `SettingsError`, `Result<T>` - crate error type and alias
- `SettingsSource` - distinguishes path-backed and label-backed parse sources
- `Yaml` - re-export of `yaml_rust2::Yaml`
- loader functions:
  - `parse_yaml_content(source, content)`
  - `merge_yaml_documents(source, docs)`
  - `load_yaml_sync(path)`
  - `load_yaml_merged_sync(path)`
  - `load_yaml_async(path)`
  - `load_yaml_merged_async(path)`
  - `load_yaml_batch_sync(paths)`
  - `load_yaml_batch_async(paths)`
- cache-facing functions:
  - `load_settings_sync(key, path)`
  - `load_settings_async(key, path)`
  - `load_batch_sync(paths)`
  - `load_batch_async(paths)`
  - `get_cached(key)`
  - `is_cached(key)`
  - `invalidate(key)`
  - `clear_cache()`
  - `cache_size()`
  - `cache_keys()`
  - `cache_stats()`
  - `reset_cache_stats()`
- `CacheStats` - cache hit/miss snapshot

## Public module

### `validators`

- `SettingType` - expected scalar type for validation/coercion
- `CoercedValue` - typed coercion result
- `ValidationIssue` - structure-validation finding
- `IssueSeverity` - `Warning` or `Error`
- `validate_settings_structure(yaml)` - top-level settings-document checks
- `validate_setting_value(value, expected_type)` - fast string validation
- `coerce_setting_value(value, target_type)` - string-to-typed-value coercion

Important layout note: `cache`, `loader`, and `error` are internal modules. Their public items are available through crate-root re-exports, while `validators` remains a public module path such as `classic_settings_core::validators::SettingType`.

---

## Public API Surface

## `SettingsSource`

Variants:

- `Path(PathBuf)` - filesystem-backed source used by path-based loaders
- `Label(String)` - logical source name for in-memory content

Helpers and conversions:

- `path() -> Option<&PathBuf>` returns the path only for `Path`
- `label() -> Option<&str>` returns the label only for `Label`
- `From<PathBuf>`, `From<&Path>`, `From<String>`, and `From<&str>` are implemented
- `Display` prints the filesystem path or label text used in error messages

## `SettingsError`

Variants:

- `IoError { path, source }` - disk read failure for a path-backed load
- `YamlParseError { source, message }` - YAML syntax failure tagged with `SettingsSource`
- `EmptyDocument { source }` - empty YAML stream or stream where every document is `BadValue`
- `KeyNotFound(String)` - cache lookup miss for APIs that treat a missing key as an error
- `InvalidYamlStructure { source, index, found }` - merge-time failure when any document is not a mapping
- `TaskJoinError { path, source }` - async batch task failed to join

Behavior worth knowing:

- `EmptyDocument`, `InvalidYamlStructure`, and `TaskJoinError` are part of the public error surface now, not internal-only details
- only `IoError` and `TaskJoinError` expose an underlying `source()` error through `std::error::Error`
- parse and merge helpers use `SettingsSource::Label(...)` for in-memory content and `SettingsSource::Path(...)` for file-backed content

## Loader API

These functions read or normalize YAML without touching the cache.

## `parse_yaml_content(source, content)`

- parses YAML from an in-memory string and preserves the caller-supplied logical source label in parse errors
- returns `Vec<Yaml>` so higher layers can decide whether to inspect raw documents or merge them
- uses `SettingsSource::Label(...)` under the hood

## `merge_yaml_documents(source, docs)`

- reduces a `Vec<Yaml>` into one merged mapping
- requires every document to be a mapping
- merges nested mappings recursively
- replaces sequences, scalars, and type-conflict values with the later document's value
- returns `SettingsError::EmptyDocument` for an empty stream and `SettingsError::InvalidYamlStructure` when any document is not a mapping
- document indexes in `InvalidYamlStructure` are zero-based, matching the implementation

## `load_yaml_sync(path)`

- reads the file with `std::fs::read_to_string`
- parses all YAML documents with `yaml_rust2::YamlLoader::load_from_str`
- returns `Vec<Yaml>` so multi-document YAML files stay intact
- returns `SettingsError::IoError` or `SettingsError::YamlParseError` on failure

## `load_yaml_async(path)`

- reads the file with `tokio::fs::read_to_string`
- uses the same YAML parsing path and error variants as the sync loader
- is the async equivalent for callers already running on the shared Tokio runtime

## `load_yaml_merged_sync(path)` and `load_yaml_merged_async(path)`

- thin wrappers over `load_yaml_*` plus `merge_yaml_documents`
- return one merged `Yaml::Hash` value instead of `Vec<Yaml>`
- are the preferred entry points for crates such as [`classic-config-core`](classic-config-core.md) that consume multi-document settings files as one mapping

## Batch loader helpers

- `load_yaml_batch_sync(paths)` loads files sequentially and returns `Vec<(String, Vec<Yaml>)>`
- `load_yaml_batch_async(paths)` spawns one Tokio task per path, then collects the same tuple shape
- both batch APIs stop and return an error if any input file fails
- tuple keys are `path.display().to_string()`, not caller-supplied logical names
- async batch loading reports join failures as `SettingsError::TaskJoinError` instead of disguising them as parse failures

Source-observed note:

- the raw loader functions do not reduce input to the first document; multi-document YAML remains a `Vec<Yaml>` until a caller explicitly merges it

  (This is a notable contrast with the historical ``yaml-core`` single-doc behavior that was absorbed into this crate during Phase 1 of the v9.1.0 consolidation milestone.)

## Cache API

The cache stores parsed YAML documents in a global bounded concurrent cache:

- key type: `String`
- value type: `Arc<Vec<Yaml>>`
- backing store: `std::sync::LazyLock<quick_cache::sync::Cache<String, Arc<Vec<Yaml>>>>`
- configured capacity: `64`

That means callers can cheaply clone cached values and compare `Arc` identity across reads.

Phase 4 note:

- the roadmap's older "LRU" shorthand is implemented here through the repo-standard `quick_cache` crate
- `quick_cache` uses bounded eviction semantics, so contributors should test that the cache stays within capacity rather than asserting an exact victim order

## `load_settings_sync(key, path)` and `load_settings_async(key, path)`

These are the main cache-populating entry points.

- they first load the file through `load_yaml_sync` or `load_yaml_async`
- they wrap the returned `Vec<Yaml>` in `Arc`
- they insert the value into the global cache under `key.to_string()`
- inserting with an existing key replaces the previous cached value
- they return the same `Arc<Vec<Yaml>>` that was inserted
- they do not consult file mtimes or other freshness signals; callers still control reload timing explicitly

## `load_batch_sync(paths)` and `load_batch_async(paths)`

- they load many files, then insert each result into the cache
- each cache key is the path string from `path.display().to_string()`
- they return `Result<usize>` and, on success, currently return `paths.len()`

Contributor note:

- the success count is the number of requested paths, not a separately computed count of inserted entries

## Cache access and management

- `get_cached(key) -> Option<Arc<Vec<Yaml>>>` returns a cloned `Arc` if present
- `is_cached(key) -> bool` checks existence without touching hit/miss counters
- `invalidate(key) -> bool` removes one entry and reports whether it existed
- `clear_cache()` removes all entries
- `cache_size() -> usize` returns entry count
- `cache_keys() -> Vec<String>` returns all keys; ordering is not stable and this helper is now the only public API that exposes key listings

## `CacheStats`, `cache_stats()`, and `reset_cache_stats()`

`CacheStats` fields:

- `hits`
- `misses`
- `hit_rate`
- `size`
- `capacity`

Behavior worth knowing:

- hit/miss counters are process-global `AtomicU64` values
- only `get_cached()` updates those counters
- loading functions do not count as cache hits or misses
- `cache_stats()` reports the canonical five-field Phase 4 contract only; key listings stay on `cache_keys()`
- `capacity` is the configured bounded cache size and currently reports `64`
- `reset_cache_stats()` resets counters only; it does not clear cached entries

---

## Settings Cache And Sync/Async Flow

The source-visible flow is split into two layers.

## Raw load flow

1. A caller chooses `load_yaml_sync()` or `load_yaml_async()`.
2. The file is read from disk.
3. `YamlLoader::load_from_str()` parses the full YAML stream.
4. The caller receives `Vec<Yaml>` with every parsed document.

## Cache-backed flow

1. A caller chooses `load_settings_sync(key, path)` or `load_settings_async(key, path)`.
2. The crate performs the same disk read + parse flow as the raw loader.
3. The parsed `Vec<Yaml>` is wrapped in `Arc`.
4. The crate inserts that `Arc<Vec<Yaml>>` into the global bounded `quick_cache::sync::Cache<String, ...>`.
5. Later callers retrieve it with `get_cached(key)`.

## Batch flow

- sync batch: one file after another
- async batch: one spawned Tokio task per path, then join all results
- cache insertion happens only after successful load results are collected

Important cache boundary:

- this cache does not automatically consult disk freshness, file mtimes, or file content hashes
- if a source file changes, callers must explicitly reload or invalidate the cache entry

Unlike the legacy `YamlOperations` file-backed cache (see [YAML Operations](#yaml-operations) below), this settings cache is key-based rather than path-based, and it does not consult mtime for freshness.

---

## Validators API

The `validators` module is independent from the cache and loader helpers.

## `SettingType`

Variants:

- `Int`
- `Bool`
- `Float`
- `Path`
- `String`

These are used only for scalar string validation and coercion.

## `CoercedValue`

Variants:

- `Int(i64)`
- `Bool(bool)`
- `Float(f64)`
- `Path(String)`
- `String(String)`

Accessor helpers:

- `as_i64()`
- `as_bool()`
- `as_f64()`
- `as_str()` for `String` and `Path`

## `validate_settings_structure(yaml)`

This performs lightweight top-level checks intended for settings-style YAML documents.

Rules visible in the source:

- a root `Yaml::Hash` is considered the expected shape
- an empty mapping produces a `Warning`
- a mapping without the `CLASSIC_Settings` root key produces a `Warning`
- `Yaml::Null` and `Yaml::BadValue` produce an `Error`
- any non-mapping root value produces an `Error`

Contributor note:

- missing `CLASSIC_Settings` is not fatal in current source; it is a warning, not an error

## `validate_setting_value(value, expected_type)`

- `Int` uses `parse::<i64>()`
- `Bool` accepts `true/false`, `yes/no`, `1/0`, and `on/off`, case-insensitive
- `Float` uses `parse::<f64>()`, so integer strings also validate as float
- `Path` accepts any non-empty string
- `String` always validates

## `coerce_setting_value(value, target_type)`

- returns `Result<CoercedValue, String>` rather than `SettingsError`
- follows the same parsing rules as `validate_setting_value`
- `Path` rejects only the empty string
- `String` always succeeds by cloning the input

---

## Error Handling Model

The crate uses two error styles depending on API family.

## `SettingsError` for loader/cache APIs

`Result<T>` is an alias for `std::result::Result<T, SettingsError>`.

Public variants:

- `IoError { path, source }`
- `YamlParseError { source, message }`
- `EmptyDocument { source }`
- `KeyNotFound(String)`
- `InvalidYamlStructure { source, index, found }`
- `TaskJoinError { path, source }`

Source-observed behavior:

- `IoError` and `YamlParseError` are used by raw load helpers
- `EmptyDocument` and `InvalidYamlStructure` are used by merge helpers
- `TaskJoinError` is used by async batch loading when a spawned task fails to join
- `KeyNotFound` remains part of the public error surface for cache-oriented APIs

That means contributors should treat all of these variants as live public API, even when a specific call path uses only a subset of them.

## `String` errors for coercion

`validators::coerce_setting_value()` returns `Result<CoercedValue, String>`.

That makes the validators module lightweight and binding-friendly, but it also means coercion failures do not carry typed error variants.

---

## Runtime And Concurrency Notes

This crate exposes both sync and async APIs, but it does not create a Tokio runtime in its current source.

- sync loading uses `std::fs`
- async loading uses `tokio::fs`
- async batch loading uses `tokio::spawn`
- cache storage uses `DashMap<String, Arc<Vec<Yaml>>>`
- cache counters use `AtomicU64`

Repo-level runtime note:

- `Cargo.toml` and crate docs say this crate follows the shared-runtime rule from [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core)
- the current `src/` files do not directly call `classic_shared_core::get_runtime()`
- in practice, callers and bindings are expected to run async APIs on the shared runtime rather than creating a new one

Contributor rule: keep new async behavior compatible with the repo's shared Tokio runtime assumption even though this crate does not currently own runtime entry points itself.

---

## Important Dependencies And Related Crates

Important direct dependencies visible in current behavior:

- `yaml-rust2` - YAML parsing and exposed `Yaml` type
- `tokio` - async file I/O and spawned async batch tasks
- `quick_cache` and `std::sync::LazyLock` - bounded process-global concurrent cache
- `serde` - `CacheStats` serialization support
- `thiserror` - `SettingsError`
- `tracing` - cache hit/miss instrumentation in `get_cached()`

Related CLASSIC crates and consumers:

- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/settings.rs) - exposes the cache, loaders, and stats to JavaScript/TypeScript
- [`classic-settings-py`](../../ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs) - exposes the same surface plus validator helpers to Python
- [`classic-config-core`](../../docs/api/classic-config-core.md) - higher-level typed config loader; use it when raw `Yaml` documents are not enough
- [`classic-shared-core`](../../docs/api/classic-shared-core.md) - repo-wide shared Tokio runtime policy this crate is expected to follow

Source-observed limitation:

- `Cargo.toml` declares `classic-shared-core` and `classic-perf-core`, but the current public `src/` implementation does not visibly expose runtime helpers or performance APIs from those crates

---

## Usage Example

This example stays within the real public API and shows the common contributor pattern: load settings into the cache, inspect structure, then reuse the cached documents.

```rust
use classic_settings_core::{get_cached, load_settings_sync};
use classic_settings_core::validators::{IssueSeverity, validate_settings_structure};
use std::path::Path;

let docs = load_settings_sync(
    "settings",
    Path::new("CLASSIC Settings.yaml"),
)?;

if let Some(first_doc) = docs.first() {
    let issues = validate_settings_structure(first_doc);

    for issue in &issues {
        if issue.severity == IssueSeverity::Error {
            eprintln!("settings structure error: {}", issue.message);
        }
    }
}

let cached = get_cached("settings").expect("settings should be cached after load");
assert!(std::sync::Arc::ptr_eq(&docs, &cached));

# Ok::<(), classic_settings_core::SettingsError>(())
```

For async callers, replace `load_settings_sync()` with `load_settings_async(...).await` and keep the same cache access pattern.

---

## Contributor Notes And Known Limits

- cache entries are invalidated manually only; there is no automatic reload when a file changes on disk
- batch-loading helpers use path strings as cache keys, while single-file helpers accept any logical key the caller chooses
- `get_cached()` is the only API that updates hit/miss counters
- cache key ordering from `cache_keys()` is not stable
- multi-document YAML is preserved rather than collapsed to the first document
- validator coercion errors use plain `String`, not `SettingsError`
- crate docs mention shared-runtime integration, but current source does not provide a root-level runtime helper or direct `classic-shared-core` call site

If you extend this crate, update this document when you change:

- root-level re-exports in `src/lib.rs`
- cache key rules or invalidation behavior
- sync vs async loading semantics
- `SettingsError` variant usage
- validator rules for accepted settings structure or scalar coercion

---

## YAML Operations

This section documents the `YamlOperations` surface and the path-backed YAML file cache that were absorbed into `classic-settings-core` during Phase 1 of the v9.1.0 consolidation milestone (see `.planning/phases/01-yaml-settings-merge/`). Before the merge these lived in a separate ``yaml-core`` crate; that crate no longer exists and all its symbols are now re-exported from the `classic-settings-core` crate root.

### Purpose

`YamlOperations` is the contributor-facing integration type for the older path-backed YAML file-cache model. Use it when you need:

- synchronous YAML parsing and serialization with `yaml_rust2::Yaml`
- dot-path value extraction and mutation helpers over parsed YAML
- a global file-backed YAML cache with hit/miss statistics and mtime-based invalidation
- YAML merge-key (`<<`) resolution for parsed documents

The `YamlOperations` cache is distinct from the `Arc<Vec<Yaml>>` settings cache documented above — it is path-keyed, mtime-aware, and has a fixed capacity of `128` entries (vs. the settings cache's `64`).

### `YamlOperations`

Construction and cache control:

- `YamlOperations::new()`
- `YamlOperations::with_config(format_config)`
- `set_cache_enabled(enabled)`
- `is_cache_enabled() -> bool`
- `clear_cache()`
- `get_cache_stats() -> HashMap<String, usize>`

Parsing and file I/O:

- `parse_yaml(content) -> Result<Yaml, YamlError>`
- `dump_yaml(yaml) -> Result<String, YamlError>`
- `load_yaml_file(path) -> Result<Yaml, YamlError>`
- `save_yaml_file(path, yaml) -> Result<(), YamlError>`
- `load_yaml_files_batch(paths) -> HashMap<String, Yaml>`

Generic nested access helpers:

- `get_setting(yaml, key_path) -> Option<Yaml>`
- `set_setting(yaml, key_path, value) -> Result<Yaml, YamlError>`
- `get_settings_batch(yaml, key_paths) -> HashMap<String, Yaml>`
- `set_settings_batch(yaml, settings) -> Result<Yaml, YamlError>`

Typed extraction helpers:

- `get_string_value(data, key_path, default) -> String`
- `get_vec_value(data, key_path) -> Vec<String>`
- `get_hashmap_value(data, key_path) -> HashMap<String, String>`
- `get_indexmap_value(data, key_path) -> IndexMap<String, String>`
- `get_hashmap_vec_value(data, key_path) -> HashMap<String, Vec<String>>`
- `get_indexmap_vec_value(data, key_path) -> IndexMap<String, Vec<String>>`

Behavior worth knowing:

- `parse_yaml()` and `load_yaml_file()` always return only the first YAML document from multi-document input (unlike the `load_yaml_*` loader helpers earlier in this document, which preserve all documents).
- Dot-path traversal only walks `Yaml::Hash` nodes. Array indexing is not supported.
- `get_setting()` clones and returns the final `Yaml` value.
- `set_setting()` creates missing intermediate hashes and will replace a non-hash intermediate node with a new hash to complete the requested path.
- Typed extraction helpers are intentionally lossy: they silently drop non-string items and type mismatches instead of raising errors.

### `YamlFormatConfig`

Formatting preferences stored on a `YamlOperations` instance.

Fields: `preserve_quotes`, `width`, `indent_mapping`, `indent_sequence`, `indent_offset`.

Source-observed limitation: the current implementation stores `format_config` but `dump_yaml()` does not consult it; serialization still uses a plain `YamlEmitter`.

### `YamlCacheStats`, `yaml_cache_stats()`, `reset_yaml_cache_stats()`

The yaml-file cache has its own observability surface, distinct from the settings cache:

- `YamlCacheStats` — struct with `hits`, `misses`, `hit_rate`, `size`, `capacity`
- `yaml_cache_stats() -> YamlCacheStats` — process-global counters plus current size and capacity
- `reset_yaml_cache_stats()` — resets hit/miss counters only; does not clear cached entries
- `clear_global_yaml_cache()` — removes all cached YAML documents

Notes:

- Counters are global across all `YamlOperations` instances.
- `capacity` is fixed at `128` entries for the process-global YAML cache (vs. `64` for the settings cache).
- The D-03 rename in Phase 1 was chosen to keep the two caches unambiguously distinct: `yaml_cache_stats` / `YamlCacheStats` for the path-keyed yaml file cache, and `cache_stats` / `CacheStats` (above) for the key-based settings cache.

### `YamlError`

Variants:

- `ParseError(String)`
- `SerializeError(String)`
- `IoError(std::io::Error)`
- `EmptyDocument`
- `InvalidValue(String)`
- `UnresolvedAlias`
- `InvalidKeyPath(String)`
- `TypeConversionError(String)`

Notes:

- `parse_yaml()` and `load_yaml_file()` return `ParseError` for YAML syntax failures and `EmptyDocument` when parsing succeeds but no document exists.
- `set_setting()` and `set_settings_batch()` can return `InvalidKeyPath` for empty or whitespace-only paths.
- `merge_keys()` returns `InvalidValue` when `<<` does not point to a mapping or a sequence of mappings.

### `merge_keys(yaml)`

Resolves YAML merge-key (`<<`) usage after parsing. Semantics:

- `<<` value may be a single mapping or a sequence of mappings
- merge resolution is recursive, including nested merged mappings and arrays containing merged mappings
- explicitly present keys in the current mapping win over merged keys
- when merging multiple mappings from a sequence, earlier mappings win because later inserts do not overwrite existing keys
- the `<<` key is removed from the final result

`YamlOperations::parse_yaml()` does not apply merge-key resolution automatically; it is opt-in via `merge_keys()`.

### YAML Loading And Cache Flow

For the path-backed cache, the source-visible file-loading flow is:

1. Construct or reuse a `YamlOperations` value.
2. Call `load_yaml_file(path)`.
3. If per-instance caching is enabled, check the global bounded `YAML_CACHE` by exact `PathBuf` key.
4. If a cached entry exists and the file's current modification time is not newer than the cached timestamp, increment the hit counter and return a clone.
5. Otherwise remove any stale cached entry, increment the miss counter, read the file synchronously with `std::fs::read_to_string`, parse with `YamlLoader`, keep only the first document, and insert the fresh parsed result.
6. Callers optionally inspect cache state through `yaml_cache_stats()` or clear state with `clear_global_yaml_cache()`.

Write flow for `save_yaml_file(path, yaml)`:

1. Serialize with `dump_yaml()`.
2. Write to `path.with_extension("yaml.tmp")`.
3. Rename onto the target path.
4. Remove the target path from the global cache if caching is enabled for that instance.

The backing store is `quick_cache::sync::Cache<PathBuf, CachedYaml>`. The cache is process-global, shared by all `YamlOperations` instances. Cache invalidation is mtime-based and path-spelling is NOT canonicalized before caching.

### Usage Example

```rust
use classic_settings_core::{YamlOperations, merge_keys};

let ops = YamlOperations::new();

let yaml = ops.parse_yaml(
    r#"
defaults: &defaults
  crashgen: Buffout 4
  ignore:
    - foo
    - bar

profile:
  <<: *defaults
  crashgen: Buffout 4 NG
"#,
)?;

let merged = merge_keys(yaml)?;

assert_eq!(
    ops.get_string_value(&merged, "profile.crashgen", ""),
    "Buffout 4 NG"
);

assert_eq!(ops.get_vec_value(&merged, "profile.ignore"), vec!["foo", "bar"]);

# Ok::<(), classic_settings_core::YamlError>(())
```

### C++ Bridge Surface

The C++ bridge module `classic::settings` (formerly `classic::yaml`; renamed during Phase 1 Plan 2 of the v9.1.0 merge) exposes both the YAML operations surface AND the new settings-core cache ops and validators (the D-09 expansion). Contributors targeting C++ callers should consult [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md) for the full entry point list. A brief summary:

- `yaml_ops_*` — path-backed YAML cache operations (parse, load, save, get_setting, cache_stats)
- `settings_load_sync`, `settings_load_async_blocking`, `settings_load_batch_sync`, `settings_load_batch_async_blocking` — cache-populating loaders that return document counts (the full `Arc<Vec<Yaml>>` does not cross the CXX boundary)
- `settings_cache_stats`, `settings_cache_size`, `settings_cache_keys`, `settings_is_cached`, `settings_invalidate`, `settings_clear_cache`, `settings_reset_cache_stats` — key-based settings cache observability
- `settings_validate_structure`, `settings_validate_value`, `settings_coerce_value` — validator helpers mirroring the Python surface
- Shared structs: `SettingsCacheStats`, `SettingsValidationIssue`, `SettingsCoercedValue`, `YamlCacheStatsDto`

Two type-system exceptions apply at the CXX boundary (bridge-internal design notes):

- `get_cached()` returning `Option<Arc<Vec<Yaml>>>` cannot cross CXX; callers fall back to `yaml_ops_*` for parsed docs.
- `load_settings_*()` returns only a `u32` doc count instead of the `Arc<Vec<Yaml>>`.

### Contributor Notes For The Absorbed YAML Surface

- The public YAML API is root-level on `classic-settings-core`; adding or removing items in `src/lib.rs` materially changes the crate surface.
- `YamlOperations::with_config()` currently stores formatting preferences but the serializer does not visibly honor them.
- `load_yaml_files_batch()` iterates sequentially and silently skips failures.
- Dot-path access is hash-only; contributors should not assume support for YAML arrays in path segments.
- Merge-key resolution is opt-in through `merge_keys()` and is not part of normal parse/load calls.
- The yaml-file cache behavior is global and mtime-based; tests or callers that depend on fresh reads should clear the cache explicitly.

Update this section when you change:

- the yaml-file cache invalidation or observability behavior
- typed extraction semantics or lossy fallback rules
- merge-key handling
- the C++ bridge surface for `classic::settings`
