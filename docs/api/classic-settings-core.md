# `classic-settings-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-settings-core/`](../../ClassicLib-rs/business-logic/classic-settings-core).

Crate metadata:

- Crate: `classic-settings-core`
- Description: `Core YAML settings cache with dual sync/async API`

This crate is a small YAML settings utility layer with two distinct responsibilities:

1. Load YAML documents from disk through synchronous or asynchronous helpers.
2. Cache loaded YAML documents behind caller-chosen string keys for later reuse.

It also exposes a public `validators` module for lightweight settings-shape checks and string-to-type coercion.

This is not the main CLASSIC config-modeling crate. It works at the level of raw `yaml_rust2::Yaml` documents and simple validation helpers rather than typed application settings structs.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- read one or more YAML files into `Vec<Yaml>`
- cache parsed YAML documents under a logical string key
- expose the same YAML-loading behavior through sync and async Rust APIs
- inspect or clear cache state from tests, bindings, or startup code
- run lightweight validation or coercion for settings-like scalar values

Do not use this crate for:

- typed CLASSIC config modeling such as `ClassicConfig` or `YamlDataCore`
- automatic file freshness checks or mtime-based cache invalidation
- owning a Tokio runtime
- deep schema validation or business-rule enforcement for scan/config workflows

Those higher-level concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-yaml-core`](../../ClassicLib-rs/business-logic/classic-yaml-core), and binding crates that wrap this cache for JS or Python consumers.

---

## Module And API Map

This crate exposes most of its API from the crate root and one public module.

## Root-level re-exports from `lib.rs`

- `SettingsError`, `Result<T>` - crate error type and alias
- `Yaml` - re-export of `yaml_rust2::Yaml`
- loader functions:
  - `load_yaml_sync(path)`
  - `load_yaml_async(path)`
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

## Loader API

These functions read YAML from disk and return parsed documents without touching the cache.

## `load_yaml_sync(path)`

- reads the file with `std::fs::read_to_string`
- parses all YAML documents with `yaml_rust2::YamlLoader::load_from_str`
- returns `Vec<Yaml>` so multi-document YAML files stay intact
- returns `SettingsError::IoError` or `SettingsError::YamlParseError` on failure

## `load_yaml_async(path)`

- reads the file with `tokio::fs::read_to_string`
- uses the same YAML parsing path and error variants as the sync loader
- is the async equivalent for callers already running on the shared Tokio runtime

## Batch loader helpers

- `load_yaml_batch_sync(paths)` loads files sequentially and returns `Vec<(String, Vec<Yaml>)>`
- `load_yaml_batch_async(paths)` spawns one Tokio task per path, then collects the same tuple shape
- both batch APIs stop and return an error if any input file fails
- tuple keys are `path.display().to_string()`, not caller-supplied logical names

Source-observed note:

- unlike `classic-yaml-core`, these loader functions do not reduce input to the first document; multi-document YAML remains a `Vec<Yaml>` of every parsed document

## Cache API

The cache stores parsed YAML documents in a global concurrent map:

- key type: `String`
- value type: `Arc<Vec<Yaml>>`

That means callers can cheaply clone cached values and compare `Arc` identity across reads.

## `load_settings_sync(key, path)` and `load_settings_async(key, path)`

These are the main cache-populating entry points.

- they first load the file through `load_yaml_sync` or `load_yaml_async`
- they wrap the returned `Vec<Yaml>` in `Arc`
- they insert the value into the global cache under `key.to_string()`
- inserting with an existing key replaces the previous cached value
- they return the same `Arc<Vec<Yaml>>` that was inserted

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
- `cache_keys() -> Vec<String>` returns all keys; ordering is not stable because storage uses `DashMap`

## `CacheStats`, `cache_stats()`, and `reset_cache_stats()`

`CacheStats` fields:

- `hits`
- `misses`
- `hit_rate`
- `size`
- `keys`

Behavior worth knowing:

- hit/miss counters are process-global `AtomicU64` values
- only `get_cached()` updates those counters
- loading functions do not count as cache hits or misses
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
4. The crate inserts that `Arc<Vec<Yaml>>` into the global `DashMap<String, ...>`.
5. Later callers retrieve it with `get_cached(key)`.

## Batch flow

- sync batch: one file after another
- async batch: one spawned Tokio task per path, then join all results
- cache insertion happens only after successful load results are collected

Important cache boundary:

- this cache does not automatically consult disk freshness, file mtimes, or file content hashes
- if a source file changes, callers must explicitly reload or invalidate the cache entry

That is the main behavioral difference from the file-backed cache in [`classic-yaml-core`](../../docs/api/classic-yaml-core.md).

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
- `YamlParseError { path, message }`
- `KeyNotFound(String)`
- `InvalidYamlStructure { path, expected, found }`

Source-observed behavior:

- `IoError` and `YamlParseError` are actively used by the loader functions
- current crate-root APIs do not appear to construct `KeyNotFound` or `InvalidYamlStructure`

That means contributors should treat those two variants as public but currently unused parts of the error surface unless they add new APIs that actually return them.

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
- `dashmap` and `once_cell` - process-global concurrent cache
- `serde` - `CacheStats` serialization support
- `thiserror` - `SettingsError`
- `tracing` - cache hit/miss instrumentation in `get_cached()`

Related CLASSIC crates and consumers:

- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/settings.rs) - exposes the cache, loaders, and stats to JavaScript/TypeScript
- [`classic-settings-py`](../../ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs) - exposes the same surface plus validator helpers to Python
- [`classic-yaml-core`](../../docs/api/classic-yaml-core.md) - neighboring YAML utility crate with a different cache model based on file paths and mtimes
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
- `SettingsError::KeyNotFound` and `SettingsError::InvalidYamlStructure` are public, but current crate-root APIs do not visibly return them
- validator coercion errors use plain `String`, not `SettingsError`
- crate docs mention shared-runtime integration, but current source does not provide a root-level runtime helper or direct `classic-shared-core` call site

If you extend this crate, update this document when you change:

- root-level re-exports in `src/lib.rs`
- cache key rules or invalidation behavior
- sync vs async loading semantics
- `SettingsError` variant usage
- validator rules for accepted settings structure or scalar coercion
