# `classic-settings-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-settings-core/`](../../business-logic/classic-settings-core).

Crate metadata:

- Crate: `classic-settings-core`
- Description: `CLASSIC YAML settings facade over classic-shared-core generic YAML and YAML operations, plus YamlFile`

The generic YAML rules this crate used to own now live in [`classic_shared_core::yaml`](classic-shared-core.md#generic-yaml-yaml): parsing, document and merge-key merging, sync/async loaders, scalar validators, schema-version compatibility, and the logical-key settings cache (issue #239), then [`YamlOperations`](classic-shared-core.md#yamloperations) and its [path/mtime-aware YAML-file cache](classic-shared-core.md#yaml-file-cache) (issue #240). This crate re-exports every one of those items unchanged, so `classic_settings_core::load_settings_sync` and `classic_shared_core::yaml::load_settings_sync` are the same function, and `classic_settings_core::YamlOperations::new()` is a shared-core object. Both paths read and clear the **same** default-scope caches, with the same capacities (`64` logical-key, `128` YAML-file), freshness, counters, and errors. The two caches stay distinct from each other.

The [cache scope handles](classic-shared-core.md#cache-scopes) (`LogicalKeyCacheScope`, `YamlFileCacheScope`) and `YamlOperations::with_cache_scope` are new shared-core API and are deliberately **not** re-exported here; reach them through `classic_shared_core::yaml`.

The crate still owns `YamlFile`, CLASSIC's domain-specific YAML file identity, until config becomes the canonical file-policy owner (issue #246).

The crate identity is scheduled for retirement (issue #257) once its remaining callers import the accepted owners directly. Until then its re-exported paths, including `classic_settings_core::validators::*`, stay valid.

Parity ownership: CXX, Node, and Python parity rows for the logical-key cache, loaders, merge, validators, `YamlOperations`, and the YAML-file cache name `classic-shared-core` as the owning Rust crate, because the behavior lives there. Do not restore `classic-settings-core` as the owner of those rows during a baseline refresh. Only `YamlFile` rows, and Rust-only `@rust` proxy rows for items this facade still re-exports, name `classic-settings-core`.

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
- YAML-file operations and cache: `YamlOperations`, `YamlCacheStats`, `yaml_cache_stats`, `reset_yaml_cache_stats`, `clear_global_yaml_cache` (see the shared-core [`YamlOperations`](classic-shared-core.md#yamloperations) and [YAML-file cache](classic-shared-core.md#yaml-file-cache) sections)
- the public module `validators` (`SettingType`, `CoercedValue`, `validate_setting_value`, `coerce_setting_value`), re-exported as a module so `classic_settings_core::validators::SettingType` still resolves

Owned by this crate:

- `YamlFile` - type-safe identifiers for CLASSIC YAML/config files

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

- `classic-shared-core` - owner of every re-exported YAML item
- `serde` - `YamlFile` serialization

Related CLASSIC crates and consumers:

- [`classic-shared-core`](classic-shared-core.md#generic-yaml-yaml) - owner of the generic YAML rules, `YamlOperations`, and both scoped caches
- [`classic-node`](../../node-bindings/classic-node/src/settings.rs) - exposes the caches, loaders, YAML operations, and `YamlFile` to JavaScript/TypeScript
- [`classic-settings-py`](../../python-bindings/classic-settings-py/src/lib.rs) - exposes the generic YAML, YAML operations, scalar-validator, and `YamlFile` surface to Python, using its own shared-core cache scopes
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
- New code should import generic YAML items, including `YamlOperations` and the YAML-file cache functions, from `classic_shared_core::yaml` directly so the eventual retirement of this crate does not need to touch it.
- Root-level re-exports in `src/lib.rs` are still part of the public crate surface; removing one breaks callers that have not migrated.

If you change this crate, update this document when you change:

- root-level re-exports in `src/lib.rs`
- `YamlFile` variants, methods, display, or serialization

Changes to `YamlOperations` or either cache belong in the [shared-core guide](classic-shared-core.md#generic-yaml-yaml).
