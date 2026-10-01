# `classic-settings-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-settings-core/`](../../business-logic/classic-settings-core).

Crate metadata:

- Crate: `classic-settings-core`
- Description: `CLASSIC YAML settings facade over classic-shared-core generic YAML, plus YamlFile and YamlOperations`

The generic YAML rules this crate used to own now live in [`classic_shared_core::yaml`](classic-shared-core.md#generic-yaml-yaml) (issue #239): parsing, document and merge-key merging, sync/async loaders, scalar validators, schema-version compatibility, and the logical-key settings cache. This crate re-exports every one of those items unchanged, so `classic_settings_core::load_settings_sync` and `classic_shared_core::yaml::load_settings_sync` are the same function and read and clear the **same** cache, with the same capacity (`64`), freshness, counters, and errors.

The crate still owns two things until their own migrations land:

1. `YamlFile`, CLASSIC's domain-specific YAML file identity, until config becomes the canonical file-policy owner (issue #246).
2. `YamlOperations` and its path/mtime-aware YAML-file cache, documented under [YAML Operations](#yaml-operations), until it moves to shared core (issue #240).

The crate identity is scheduled for retirement (issue #257) once its remaining callers import the accepted owners directly. Until then its re-exported paths, including `classic_settings_core::validators::*`, stay valid.

Parity ownership: CXX, Node, and Python parity rows for the logical-key cache, loaders, merge, and validators name `classic-shared-core` as the owning Rust crate, because the behavior lives there. Do not restore `classic-settings-core` as the owner of those rows during a baseline refresh. Rows for `YamlOperations`, the YAML-file cache, and `YamlFile` still name `classic-settings-core`.

The Node `yamlGetIndexmapValue` adapter preserves the core map's insertion order
for ordinary string keys by inserting them directly into its returned JavaScript
object. JavaScript enumerates integer-index keys numerically, so that language
rule still applies to numeric-looking YAML keys.

This crate does not interpret raw User Settings key paths or own the `CLASSIC Settings.yaml` schema. That contract belongs exclusively to [`classic-user-settings-core`](classic-user-settings-core.md).

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Root-Level Public API

Re-exported from `classic_shared_core::yaml` (see the [shared-core guide](classic-shared-core.md#generic-yaml-yaml) for full semantics):

- `SettingsError`, `Result<T>`, `SettingsSource`, `Yaml`
- loaders: `parse_yaml_content`, `merge_yaml_documents`, `load_yaml_sync`, `load_yaml_merged_sync`, `load_yaml_async`, `load_yaml_merged_async`, `load_yaml_batch_sync`, `load_yaml_batch_async`
- logical-key cache: `load_settings_sync`, `load_settings_async`, `load_batch_sync`, `load_batch_async`, `get_cached`, `is_cached`, `invalidate`, `clear_cache`, `cache_size`, `cache_keys`, `cache_stats`, `reset_cache_stats`, `CacheStats`
- schema compatibility: `SchemaVersion`, `SchemaParseError`, `SchemaCompat`, `Compatibility`, `schema_compat_check`, `extract_schema_version`, `YamlSchemaError`, `SCHEMA_VERSION_KEY`
- `merge_keys`, `YamlError`
- the public module `validators` (`SettingType`, `CoercedValue`, `validate_setting_value`, `coerce_setting_value`), re-exported as a module so `classic_settings_core::validators::SettingType` still resolves

Owned by this crate:

- `YamlFile` - type-safe identifiers for CLASSIC YAML/config files
- `YamlOperations`, `YamlCacheStats`, `yaml_cache_stats`, `reset_yaml_cache_stats`, `clear_global_yaml_cache` - see [YAML Operations](#yaml-operations)

---

## `YamlFile`

`YamlFile` is the contributor-facing enum for CLASSIC YAML file roles.

Variants:

- `Main`
- `Ignore`
- `Game`
- `GameLocal`
- `Test`
- `Cache`

Important methods and traits:

- `as_str() -> &'static str`
- `description() -> &'static str`
- `all() -> [YamlFile; 6]`
- `Display`, `Serialize`, `Deserialize`, `Clone`, `Copy`, `Hash`

Contributor note:

- this enum labels file roles only; it does not build real paths
- it moved here from the retired constants crate because the enum is part of the settings domain rather than the version domain
- it is domain-specific, so it did not move to shared core with the generic YAML rules; config will take ownership of it

---

## Important Dependencies And Related Crates

Important direct dependencies visible in current behavior:

- `classic-shared-core` - owner of every re-exported generic YAML item
- `yaml-rust2` - YAML parsing for `YamlOperations`
- `quick_cache` - bounded process-global path/mtime-aware YAML-file cache
- `rayon`, `indexmap`, `serde`, `tracing` - `YamlOperations` batch loading, ordered extraction, stats serialization, and cache instrumentation

Related CLASSIC crates and consumers:

- [`classic-shared-core`](classic-shared-core.md#generic-yaml-yaml) - owner of the generic YAML rules and logical-key cache
- [`classic-node`](../../node-bindings/classic-node/src/settings.rs) - exposes the cache, loaders, and stats to JavaScript/TypeScript
- [`classic-settings-py`](../../python-bindings/classic-settings-py/src/lib.rs) - exposes the generic YAML and scalar-validator surface to Python
- [`classic-config-core`](../../docs/api/classic-config-core.md) - higher-level CLASSIC YAML Data loader; use it when raw `Yaml` documents are not enough
- [`classic-user-settings-core`](../../docs/api/classic-user-settings-core.md) - exclusive owner of typed User Settings

---

## Usage Example

The re-exported paths behave exactly like the shared-core ones. Use a non-User-Settings document; first-party production code must use `classic-user-settings-core` for `CLASSIC Settings.yaml`.

```rust
use classic_settings_core::{get_cached, load_settings_sync};
use std::path::Path;

let docs = load_settings_sync(
    "ignore",
    Path::new("CLASSIC Ignore.yaml"),
)?;

// The facade and the shared-core owner see the same cache entry.
let cached = classic_shared_core::yaml::get_cached("ignore")
    .expect("document should be cached after load");
assert!(std::sync::Arc::ptr_eq(&docs, &cached));
assert!(get_cached("ignore").is_some());

# Ok::<(), classic_settings_core::SettingsError>(())
```

---

## Contributor Notes And Known Limits

- Do not add new generic YAML behavior here; add it to `classic_shared_core::yaml` and, only if a current caller needs the old path, re-export it.
- New code should import generic YAML items from `classic_shared_core::yaml` directly so the eventual retirement of this crate does not need to touch it.
- Root-level re-exports in `src/lib.rs` are still part of the public crate surface; removing one breaks callers that have not migrated.

If you change this crate, update this document when you change:

- root-level re-exports in `src/lib.rs`
- `YamlFile` variants, methods, display, or serialization
- the `YamlOperations` surface or its cache behavior

---

## YAML Operations

This section documents the `YamlOperations` surface and the path-backed YAML file cache that were absorbed into `classic-settings-core` during Phase 1 of the v9.1.0 consolidation milestone (see `.planning/phases/01-yaml-settings-merge/`). Before the merge these lived in a separate ``yaml-core`` crate; that crate no longer exists and all its symbols are now re-exported from the `classic-settings-core` crate root.

### Purpose

`YamlOperations` is the contributor-facing integration type for the older path-backed YAML file-cache model. Use it when you need:

- synchronous YAML parsing and serialization with `yaml_rust2::Yaml`
- dot-path value extraction and mutation helpers over parsed YAML
- a global file-backed YAML cache with hit/miss statistics and mtime-based invalidation
- YAML merge-key (`<<`) resolution for parsed documents, through the re-exported shared-core `merge_keys()`

The `YamlOperations` cache is distinct from the `Arc<Vec<Yaml>>` logical-key cache owned by [`classic_shared_core::yaml`](classic-shared-core.md#logical-key-cache) — it is path-keyed, mtime-aware, and has a fixed capacity of `128` entries (vs. the logical-key cache's `64`).

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

- `parse_yaml()` and `load_yaml_file()` always return only the first YAML document from multi-document input (unlike the shared-core `load_yaml_*` loader helpers, which preserve all documents).
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
- The D-03 rename in Phase 1 was chosen to keep the two caches unambiguously distinct: `yaml_cache_stats` / `YamlCacheStats` for the path-keyed yaml file cache, and `cache_stats` / `CacheStats` (re-exported from shared core) for the key-based logical-key cache.

### `YamlError`

`YamlError` is owned by [`classic_shared_core::yaml`](classic-shared-core.md#yamlerror) and re-exported here; `YamlOperations` uses it for all of its errors.

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

Owned by [`classic_shared_core::yaml`](classic-shared-core.md#merging) and re-exported here. Resolves YAML merge-key (`<<`) usage after parsing. Semantics:

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
- `settings_validate_value`, `settings_coerce_value` — generic scalar validator helpers mirroring the Python surface
- Shared structs: `SettingsCacheStats`, `SettingsCoercedValue`, `YamlCacheStatsDto`

Two type-system exceptions apply at the CXX boundary (bridge-internal design notes):

- `get_cached()` returning `Option<Arc<Vec<Yaml>>>` cannot cross CXX; callers fall back to `yaml_ops_*` for parsed docs.
- `load_settings_*()` returns only a `u32` doc count instead of the `Arc<Vec<Yaml>>`.

### Contributor Notes For The Absorbed YAML Surface

- The `YamlOperations` API is root-level on `classic-settings-core`; adding or removing items in `src/lib.rs` materially changes the crate surface.
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
