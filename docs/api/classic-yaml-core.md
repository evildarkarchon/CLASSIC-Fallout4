# `classic-yaml-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-yaml-core/`](../../ClassicLib-rs/business-logic/classic-yaml-core).

Crate metadata:

- Crate: `classic-yaml-core`
- Description: `Pure Rust YAML business logic for CLASSIC (no PyO3)`

This crate is the shared low-level YAML utility layer used by active Rust business-logic crates in CLASSIC. It provides:

- synchronous YAML parsing and serialization
- dot-path value extraction and mutation helpers over `yaml_rust2::Yaml`
- a global file-backed YAML cache with hit/miss statistics
- YAML merge-key (`<<`) resolution for parsed documents

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- parse a YAML string or file into `yaml_rust2::Yaml`
- read or update nested YAML values with dot-separated key paths
- load frequently reused YAML files through the shared global cache
- preserve YAML mapping order with `IndexMap` extraction helpers
- resolve YAML merge keys (`<<`) after parsing when source data depends on YAML 1.1 merge semantics

Do not use this crate for:

- crate-specific config modeling or schema validation
- async file I/O or runtime ownership
- binding-specific wrapper APIs
- higher-level version selection, config building, or scanlog analysis

Those concerns live in related crates such as [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core), [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), and [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core).

---

## API Map

This crate exposes its public API from the crate root in `src/lib.rs`.

## Cache and cache-control API

- `CacheStats` - typed cache hit/miss snapshot
- `cache_stats()` - returns global cache counters and size information
- `reset_cache_stats()` - resets global hit/miss counters
- `clear_global_yaml_cache()` - clears the global file cache

## Core YAML API

- `YamlOperations` - main entry point for parsing, file loading, extraction, and updates
- `YamlFormatConfig` - stored formatting configuration for `YamlOperations`
- `YamlError` - typed error enum for parse/serialize/file/update failures

## Merge-key support

- `merge_keys(yaml)` - resolves YAML merge-key (`<<`) usage recursively

There are no public modules beyond the crate-root re-export of `merge_keys`.

---

## Public API Surface

## `YamlOperations`

`YamlOperations` is the main contributor-facing integration type.

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

Behavior worth knowing from the source:

- `parse_yaml()` and `load_yaml_file()` always return only the first YAML document from multi-document input.
- Dot-path traversal only walks `Yaml::Hash` nodes. Array indexing is not supported.
- `get_setting()` clones and returns the final `Yaml` value.
- `set_setting()` creates missing intermediate hashes and will replace a non-hash intermediate node with a new hash to complete the requested path.
- `get_string_value()` returns the provided default when the path is missing or the final value is not a YAML string.
- `get_vec_value()` returns only string array items and silently drops non-string items.
- `get_hashmap_value()` and `get_indexmap_value()` include only string-to-string entries.
- `get_hashmap_vec_value()` and `get_indexmap_vec_value()` accept either a single string or an array of strings for each value; other shapes are skipped.

## `YamlFormatConfig`

`YamlFormatConfig` carries formatting preferences for a `YamlOperations` instance.

Fields:

- `preserve_quotes`
- `width`
- `indent_mapping`
- `indent_sequence`
- `indent_offset`

Important trait and constructor behavior:

- `Default` is implemented
- `YamlOperations::new()` uses `YamlFormatConfig::default()`
- `YamlOperations::with_config(...)` stores a caller-provided config

Source-observed limitation:

- The current implementation stores `format_config` but `dump_yaml()` does not consult it; serialization still uses a plain `YamlEmitter` with no visible formatting customization path.

## `CacheStats`, `cache_stats()`, and `reset_cache_stats()`

`CacheStats` is the typed global cache summary returned by `cache_stats()`.

Fields:

- `hits`
- `misses`
- `hit_rate`
- `size`
- `total_bytes`

Contributor notes:

- The counters are global, not per-`YamlOperations` instance.
- `size` and `total_bytes` are derived from the shared `DashMap` cache.
- `reset_cache_stats()` resets only hit/miss counters; it does not clear cached entries.
- `YamlOperations::get_cache_stats()` is a separate legacy-style helper that returns only `cached_files` and `total_bytes` in an untyped `HashMap`.

## `YamlError`

`YamlError` is the crate's public error enum.

Variants:

- `ParseError(String)`
- `SerializeError(String)`
- `IoError(std::io::Error)`
- `EmptyDocument`
- `InvalidValue(String)`
- `UnresolvedAlias`
- `InvalidKeyPath(String)`
- `TypeConversionError(String)`

What contributors should know:

- `parse_yaml()` and `load_yaml_file()` return `ParseError` for YAML syntax failures and `EmptyDocument` when parsing succeeds but no document exists.
- `save_yaml_file()` can surface `SerializeError` or `IoError`.
- `set_setting()` and `set_settings_batch()` can return `InvalidKeyPath` for empty or whitespace-only paths.
- `merge_keys()` returns `InvalidValue` when `<<` does not point to a mapping or a sequence of mappings.

Source-observed limitation:

- `UnresolvedAlias` and `TypeConversionError` are public variants, but the current source does not appear to construct them in the main implementation.

## `merge_keys(yaml)`

`merge_keys()` resolves YAML merge-key (`<<`) usage after parsing.

Semantics visible in `src/merge.rs`:

- a `<<` value may be a single mapping or a sequence of mappings
- merge resolution is recursive, including nested merged mappings and arrays containing merged mappings
- explicitly present keys in the current mapping win over merged keys
- when merging multiple mappings from a sequence, earlier mappings in the sequence win because later inserts do not overwrite existing keys
- the `<<` key is removed from the final result

This is a separate step from parsing. `YamlOperations::parse_yaml()` does not apply merge-key resolution automatically.

---

## YAML Loading And Cache Flow

The source-visible file-loading flow is:

1. Construct or reuse a `YamlOperations` value.
2. Call `load_yaml_file(path)`.
3. If per-instance caching is enabled, the crate checks the global `YAML_CACHE` by the exact `PathBuf` key.
4. If a cached entry exists and the file's current modification time is not newer than the cached timestamp, the crate:
   - increments the global hit counter
   - returns a clone of the cached parsed `Yaml`
5. Otherwise the crate:
   - increments the global miss counter
   - reads the file synchronously with `std::fs::read_to_string`
   - parses YAML with `YamlLoader`
   - keeps only the first document
   - updates the global cache with parsed YAML, modification time, and raw text when file metadata is available
6. Callers optionally inspect cache state through `cache_stats()`, `YamlOperations::get_cache_stats()`, or clear state with `clear_cache()` / `clear_global_yaml_cache()`.

Write flow for `save_yaml_file(path, yaml)`:

1. Serialize with `dump_yaml()`.
2. Write to `path.with_extension("yaml.tmp")`.
3. Rename that temp file onto the target path.
4. Remove the target path from the global cache if caching is enabled for that `YamlOperations` instance.

Important cache notes:

- The cache is process-global, shared by all `YamlOperations` instances.
- `set_cache_enabled(false)` disables cache reads and writes only for that instance; it does not disable the global cache for other instances.
- Cache invalidation is mtime-based. The source does not canonicalize paths before caching, so different path spellings to the same file may produce distinct cache entries.

---

## Error Handling Model

This crate consistently uses `Result<_, YamlError>` for operations that can fail and uses default/empty fallbacks for many typed getters.

## Fallible APIs

These return `YamlError`:

- parsing and serialization
- file load/save operations
- nested writes through `set_setting()` and `set_settings_batch()`
- merge-key resolution through `merge_keys()`

## Fail-soft getters

These do not return errors for missing keys or shape mismatches:

- `get_setting()` returns `None`
- `get_string_value()` returns the caller-supplied default
- `get_vec_value()` returns `Vec::new()`
- map extraction helpers return empty `HashMap` / `IndexMap`
- `load_yaml_files_batch()` skips individual file failures instead of returning an error

That split matters for contributors: callers that need schema validation or strict diagnostics must add those checks in higher layers rather than relying on `classic-yaml-core` to reject every malformed structure.

---

## Async, Runtime, And Concurrency Notes

This crate is synchronous.

- It does not expose async APIs.
- It does not create or own a Tokio runtime.
- File I/O uses `std::fs` directly.
- This matches the repo rule that shared runtime ownership stays outside low-level business-logic crates.

Concurrency notes from the implementation:

- The global cache is backed by `DashMap<PathBuf, CachedYaml>`.
- Cache hit/miss counters use `AtomicU64`.
- Cached parsed YAML values are stored in `Arc<Yaml>` and cloned back out per read.
- The crate's own tests exercise concurrent parsing and concurrent cached file loads across threads.

Contributor rule: keep this crate runtime-agnostic. If you add new behavior here, do not introduce a second runtime or async-only API that downstream sync callers cannot use.

---

## Feature Flags

Contributor-relevant feature flags from `Cargo.toml`:

- default features: none
- `dhat-heap` - enables optional `dhat` dependency for heap profiling builds

Source-observed note:

- `Cargo.toml` declares `dhat-heap`, but the current `src/` files do not show feature-gated public behavior tied to that flag. Treat it as a build/profiling concern, not as a public API switch.

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `yaml-rust2` - parsed YAML AST and emitter used throughout the crate
- `dashmap` and `once_cell` - global lazy cache implementation
- `indexmap` - ordered map extraction helpers for YAML-order-sensitive consumers
- `thiserror` - `YamlError`
- `serde` - `CacheStats` serialization support
- `tracing` - cache hit/miss instrumentation

Related CLASSIC crates:

- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) - upstream consumer of `YamlOperations` for registry YAML parsing and fallback metadata loading
- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - upstream consumer of `YamlOperations` for Main/Game/Ignore YAML extraction and re-exporter of `clear_global_yaml_cache()`
- [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - downstream analysis layer that consumes config data ultimately built from YAML extracted through this crate
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) - binding layers that depend on stable higher-layer behavior built on this crate's extraction and caching rules

In practice, `classic-yaml-core` sits below the version-registry, config-loading, and scanlog crates. Changes here can ripple outward even when the immediate API surface looks small.

---

## Usage Example

This example follows the real public API and shows the two important phases: parse first, then opt into merge-key resolution if the YAML source uses `<<`.

```rust
use classic_yaml_core::{YamlOperations, merge_keys};

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

# Ok::<(), classic_yaml_core::YamlError>(())
```

For file-backed consumers, add `load_yaml_file()` on top of the same extraction helpers when you want cache-aware reads.

---

## Contributor Notes And Known Limits

- The public API is small and root-level; adding or removing public items in `src/lib.rs` materially changes the crate surface.
- `YamlOperations::with_config()` currently stores formatting preferences, but the serializer does not visibly honor them yet.
- `load_yaml_files_batch()` is documented in source comments as a batch helper, but the current implementation iterates sequentially and silently skips failures.
- Typed extraction helpers are intentionally lossy: they filter out non-string keys or values instead of reporting detailed schema errors.
- Dot-path access is hash-only; contributors should not assume support for YAML arrays in path segments.
- Merge-key resolution is opt-in through `merge_keys()` and is not part of normal parse/load calls.
- Cache behavior is global and mtime-based; tests or callers that depend on fresh reads should clear the cache explicitly.
- `classic-shared-core` is declared as a dependency in `Cargo.toml`, but the current public implementation in `src/` does not expose shared-runtime APIs.

If you extend this crate, update this document when you change:

- root-level exports in `src/lib.rs`
- cache invalidation or cache statistics behavior
- typed extraction semantics or lossy fallback rules
- merge-key handling
- sync/runtime assumptions that downstream crates rely on
