# classic-settings-core Module Decomposition Plan

## Goal

Decompose the `classic-settings-core` crate
(`business-logic/classic-settings-core/`) into smaller, single-purpose modules
to improve readability, navigability, and maintainability — **without changing
the public API or any observable behavior**.

## Scope decisions (resolved)

- **API/behavior:** Internal reorganization only. `lib.rs`'s flat `pub use`
  surface and the `pub mod validators` path stay **byte-for-byte identical**.
  Only private helpers may be de-duplicated. No downstream crate edits, no
  `docs/api/` changes.
- **Breadth:** Decompose `yaml_ops`, consolidate merge logic into a new `merge`
  module, and split `validators` and `schema_version`. Leave `error.rs`,
  `yaml_file.rs`, and `cache.rs` unchanged.
- **Error types:** Do **not** merge `SettingsError` and `YamlError`. They are
  two layered, shape-incompatible error models (see "Findings"). `YamlError`
  relocates into `yaml_ops/error.rs` unchanged.
- **Convention:** Facade-file pattern matching
  `business-logic/classic-config-core/src/shippable.rs` — a thin `<name>.rs`
  declaring `mod` submodules and `pub use`-ing their public items; submodules
  and their sibling `_tests.rs` live under `<name>/`.

## Findings (context for the implementer)

Current `src/` (source LOC, excluding `_tests.rs`):

| Module | LOC | Concerns bundled |
|---|---|---|
| `yaml_ops.rs` | 1280 | global `YAML_CACHE` + stats, `YamlError`, `CachedYaml`, `YamlOperations` (parse/dump, file I/O, get/set, batch, 6 typed extractors) |
| `cache.rs` | 373 | `SETTINGS_CACHE`, hit/miss counters, `CacheStats`, load/get/invalidate/clear |
| `validators.rs` | 290 | `SettingType`, `CoercedValue`, `ValidationIssue`/`IssueSeverity`, structure + value validation, coercion |
| `schema_version.rs` | 280 | `SchemaVersion`+parse, `SchemaParseError`, `YamlSchemaError`, `SchemaCompat`/`Compatibility`/check, `extract_schema_version` |
| `loader.rs` | 250 | sync/async file load, `parse_yaml_content`, document deep-merge, `yaml_kind` |
| `yaml_merge.rs` | 197 | `merge_keys` (`<<` merge-key extension) |
| `error.rs` | 141 | `SettingsSource` (+From impls), `SettingsError`, `Result` |
| `yaml_file.rs` | 81 | `YamlFile` enum, `SETTINGS_IGNORE_NONE`, `must_not_be_none` |

Structural problems addressed by this plan:
1. `yaml_ops.rs` is a 1280-LOC god-module mixing 5 separable concerns.
2. `get_setting` + 6 typed extractors each re-implement the same dot-path
   `Yaml::Hash` walk (~7 copies).
3. Two merge concepts live apart: stream deep-merge in `loader.rs`
   (`merge_yaml_documents`/`merge_yaml_values`) vs `<<` resolution in
   `yaml_merge.rs` (`merge_keys`).

Explicitly **out of scope** (with rationale):
- **Merging `SettingsError`/`YamlError`** — only ~3 conceptually overlapping
  variants, all shape-incompatible (path/source context + manual impl vs
  `#[from] io::Error` + thiserror); each has unique variants; downstream
  (`classic-config-py`, `classic-node`, `classic-config-core`,
  `classic-version-registry-core`) exhaustively matches each independently and
  relies on `#[from] YamlError` / `downcast_ref::<SettingsError>()`. Merge =
  wide API break for negative info value.
- **Merging the two `Yaml`→type-name helpers** (`loader::yaml_kind` vs
  `validators::yaml_type_name`) — they return **different** strings for the same
  variant and both are pinned by tests: `loader_tests.rs:117` asserts
  `found == "sequence"`; `validators_tests.rs:66/251` assert `"array"`/
  `"integer"`. Merging would change observable strings. Keep both as-is.
- **Unifying the two caches / `CacheStats` vs `YamlCacheStats`** — both are
  public re-exported types with different key/value types and semantics
  (mtime-checked vs not). Out of scope under API-preserving constraint.

## Critical constraints (verified)

- **Wide public consumption** (119 references): node/cpp/python bindings,
  CLI/GUI, and sibling core crates import `YamlOperations`, `SettingsError`,
  `YamlError`, `SchemaCompat`/`SchemaVersion`, `validators::*`, `YamlFile`,
  `merge_yaml_documents`, `parse_yaml_content`, `clear_global_yaml_cache`,
  `yaml_cache_stats`, etc. `classic-settings-py` imports `validators` **by
  path**. All these names/paths must keep resolving unchanged.
- **AGENTS rule 10** (Rust test-module layout): every split source file
  `src/.../<name>.rs` needs a sibling `src/.../<name>_tests.rs` and the parent
  declares `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;`.
- **`tests/yaml_dead_code_audit.rs`** does `include_str!("../src/yaml_ops.rs")`
  and asserts that file contains `pub struct YamlOperations` and
  `cache_enabled: bool`, plus that certain removed tokens stay absent.
  **Splitting `yaml_ops.rs` breaks this audit** — it must be updated (it is an
  in-crate test, so editing it is in scope).
- `ClassicLib-rs/` is the legacy pre-migration tree; **do not touch it**. The
  canonical crate is `business-logic/classic-settings-core/`.

## Target layout

```
src/
  lib.rs                      # re-export PATHS updated to new modules; public NAMES unchanged
  error.rs                    # unchanged (SettingsError, SettingsSource, Result)
  error_tests.rs              # (if present) unchanged
  yaml_file.rs                # unchanged
  yaml_file_tests.rs          # unchanged
  cache.rs                    # unchanged (settings SETTINGS_CACHE / CacheStats)
  cache_tests.rs              # unchanged

  loader.rs                   # SLIMMED: file I/O + parse_yaml_content; load_yaml_merged_* delegate to merge
  loader_tests.rs             # SLIMMED: merge tests moved out

  merge.rs                    # NEW facade: `mod documents; mod merge_keys; pub use ...;`
  merge/
    documents.rs              # merge_yaml_documents (+ _with_source), merge_yaml_values, yaml_kind
    documents_tests.rs        # moved from loader_tests.rs (the merge/structure cases incl. "sequence")
    merge_keys.rs             # merge_keys + merge_keys_recursive (from yaml_merge.rs)
    merge_keys_tests.rs       # renamed/moved from yaml_merge_tests.rs

  yaml_ops.rs                 # NEW facade: `mod error; mod cache; mod operations; mod accessors; pub use ...;`
  yaml_ops/
    error.rs                  # YamlError (thiserror) — unchanged contents
    error_tests.rs            # YamlError-related cases from yaml_ops_tests.rs
    cache.rs                  # YAML_CACHE, CachedYaml, YamlCacheStats, counters,
                              #   yaml_cache_stats, reset_yaml_cache_stats,
                              #   clear_global_yaml_cache, total_cached_bytes
    cache_tests.rs            # cache/stats cases from yaml_ops_tests.rs
    operations.rs             # YamlOperations struct + new/parse_yaml/dump_yaml/
                              #   load_yaml_file/save_yaml_file/load_yaml_files_batch/
                              #   set_cache_enabled/is_cache_enabled/get_cache_stats
    operations_tests.rs       # parse/dump/file-IO cases from yaml_ops_tests.rs
    accessors.rs              # impl YamlOperations: private navigate() helper +
                              #   get_setting/set_setting/get_settings_batch/set_settings_batch/
                              #   get_string_value/get_vec_value/get_hashmap_value/
                              #   get_indexmap_value/get_hashmap_vec_value/get_indexmap_vec_value
    accessors_tests.rs        # get/set + extractor cases from yaml_ops_tests.rs

  validators.rs               # NEW facade: `mod types; mod structure; mod coerce; pub use ...;`
  validators/
    types.rs                  # SettingType, CoercedValue (+ impls)
    types_tests.rs
    structure.rs              # ValidationIssue, IssueSeverity, validate_settings_structure, yaml_type_name
    structure_tests.rs        # incl. existing yaml_type_name + structure tests
    coerce.rs                 # validate_setting_value, coerce_setting_value, parse_bool
    coerce_tests.rs

  schema_version.rs           # NEW facade: `mod version; mod compat; mod extract; pub use ...;`
  schema_version/
    version.rs                # SchemaVersion, SchemaParseError, FromStr/Display
    version_tests.rs
    compat.rs                 # SchemaCompat, Compatibility, schema_compat_check
    compat_tests.rs
    extract.rs                # SCHEMA_VERSION_KEY, YamlSchemaError (+ with_file), extract_schema_version
    extract_tests.rs
```

Note: `src/cache.rs` (settings cache) and `src/yaml_ops/cache.rs` (YAML ops
cache) coexist at different module paths (`crate::cache` vs
`crate::yaml_ops::cache`); same for `src/error.rs` (`SettingsError`) vs
`src/yaml_ops/error.rs` (`YamlError`). Facade re-exports keep the public names
flat and unambiguous.

## Key behavior-preserving refactor: `navigate()` helper

In `yaml_ops/accessors.rs`, add one private helper and route all 7 accessors
through it (collapses ~250 LOC of duplicated path-walking to ~80):

```rust
fn navigate<'a>(root: &'a Yaml, key_path: &str) -> Option<&'a Yaml> {
    let mut current = root;
    for key in key_path.split('.') {
        let Yaml::Hash(hash) = current else { return None };
        current = hash.get(&Yaml::String(key.to_string()))?;
    }
    Some(current)
}
```

- `get_setting` → `navigate(...).cloned()`.
- `get_string_value` → `navigate(...).and_then(Yaml::as_str).unwrap_or(default).to_string()`.
- `get_vec_value`/`get_hashmap_value`/`get_indexmap_value`/`get_hashmap_vec_value`/`get_indexmap_vec_value`
  → `navigate(...)` then existing variant-extraction (return empty collection on `None`).
- Preserve exact current semantics: missing path or non-`Hash` intermediate
  returns the default/empty collection; the final-node type checks stay identical.
- Optional (only if it keeps bodies clearer): a generic `B: FromIterator<(String, String)>`
  extractor shared by `get_hashmap_value`/`get_indexmap_value`, and likewise for
  the `Vec<String>`-valued pair. Skip if it reduces clarity.

## Implementation tasks (ordered)

1. **Branch/baseline.** Confirm a clean build/test baseline of the crate before
   changes (see Validation).
2. **`merge` module.**
   - Create `src/merge.rs` facade: `mod documents; mod merge_keys;` +
     `pub use documents::merge_yaml_documents;` and
     `pub use merge_keys::merge_keys;` (export `merge_yaml_documents_with_source`
     to crate-internal as needed by `loader.rs`).
   - Move `merge_yaml_documents`, `merge_yaml_documents_with_source`,
     `merge_yaml_values`, `yaml_kind` from `loader.rs` into
     `src/merge/documents.rs`. Keep `pub(crate)` visibility on the
     `_with_source` variant so `loader.rs` can still call it.
   - Move `merge_keys` + `merge_keys_recursive` from `yaml_merge.rs` into
     `src/merge/merge_keys.rs` (imports `crate::YamlError`). Delete
     `src/yaml_merge.rs` and `src/yaml_merge_tests.rs`.
   - Add sibling tests: `src/merge/documents_tests.rs` (relocated merge cases
     from `loader_tests.rs`, incl. the `found == "sequence"` assertions) and
     `src/merge/merge_keys_tests.rs` (relocated from `yaml_merge_tests.rs`);
     add `#[cfg(test)] #[path = "..._tests.rs"] mod tests;` in each submodule.
3. **Slim `loader.rs`.** Keep `parse_yaml_content`,
   `parse_yaml_content_with_source`, `load_yaml_sync/async`,
   `load_yaml_batch_sync/async`, `await_batch_result`, and
   `load_yaml_merged_sync/async` (now calling
   `crate::merge::documents::merge_yaml_documents_with_source`). Remove the
   migrated merge code. Trim `loader_tests.rs` to loader-only cases.
4. **Split `yaml_ops.rs`.**
   - Create `src/yaml_ops.rs` facade: `mod error; mod cache; mod operations; mod accessors;`
     + `pub use` for `YamlError`, `YamlCacheStats`, `yaml_cache_stats`,
     `reset_yaml_cache_stats`, `clear_global_yaml_cache`, `YamlOperations`.
   - `yaml_ops/error.rs`: move `YamlError` verbatim.
   - `yaml_ops/cache.rs`: move `YAML_CACHE`, `CACHE_HITS`, `CACHE_MISSES`,
     `CachedYaml`, `YamlCacheStats`, `total_cached_bytes`, `yaml_cache_stats`,
     `reset_yaml_cache_stats`, `clear_global_yaml_cache`. Expose the items
     `operations.rs` needs (`YAML_CACHE`, `CachedYaml`, counters,
     `total_cached_bytes`) as `pub(crate)`/`pub(super)`.
   - `yaml_ops/operations.rs`: `YamlOperations` struct (`cache_enabled: bool`) +
     `new`/`Default`, `parse_yaml`, `dump_yaml`, `load_yaml_file`,
     `save_yaml_file`, `load_yaml_files_batch`, `set_cache_enabled`,
     `is_cache_enabled`, `get_cache_stats`.
   - `yaml_ops/accessors.rs`: second `impl YamlOperations` block with the
     `navigate()` helper + all get/set + batch + typed extractors.
   - Add the four sibling `_tests.rs` files; **partition the existing 1431-LOC
     `yaml_ops_tests.rs`** across them by concern, **preserving each test's
     `#[serial_test::serial]` attribute** (the file moved serialization onto
     per-`fn` attributes after the original inline-mod split). Delete
     `src/yaml_ops_tests.rs` once emptied.
5. **Split `validators.rs`.** Facade `src/validators.rs` keeps `pub mod`
   semantics by `pub use`-ing every public item from `types`/`structure`/
   `coerce` so `validators::SettingType`, `validators::CoercedValue`,
   `validators::IssueSeverity`, `validators::ValidationIssue`,
   `validators::validate_setting_value`, `validators::coerce_setting_value`,
   `validators::validate_settings_structure` all still resolve. Keep
   `yaml_type_name` private inside `structure.rs` (its test moves to
   `structure_tests.rs`). Partition `validators_tests.rs`.
6. **Split `schema_version.rs`.** Facade `src/schema_version.rs` `pub use`-es all
   public items so `SchemaVersion`, `SchemaParseError`, `YamlSchemaError`,
   `SchemaCompat`, `Compatibility`, `schema_compat_check`,
   `extract_schema_version`, `SCHEMA_VERSION_KEY` keep resolving via lib.rs's
   existing re-export. Partition `schema_version_tests.rs`.
7. **Update `lib.rs`.** Change only internal module declarations and re-export
   *source paths*: declare `mod merge;` (remove `mod yaml_merge;`), keep
   `mod yaml_ops; pub mod validators; mod schema_version;` (now facades). Switch
   `pub use yaml_merge::merge_keys;` → `pub use merge::merge_keys;` and
   `pub use loader::{... merge_yaml_documents ...}` → source `merge_yaml_documents`
   from `merge` (e.g. `pub use merge::merge_yaml_documents;` and drop it from the
   `loader` re-export list). **Every exported name stays identical.**
8. **Update `tests/yaml_dead_code_audit.rs`.** Repoint
   `include_str!("../src/yaml_ops.rs")` → `include_str!("../src/yaml_ops/operations.rs")`
   for the `pub struct YamlOperations` / `cache_enabled: bool` assertions; keep
   the forbidden-token checks scanning the relevant file(s). Confirm the
   integration-tests and benchmarks asserts still hold.
9. **Validate** (below) and iterate until green.

## Validation

Use the repo-approved commands (load the `classic-project-guide` skill for exact
forms and the per-shell `PYO3_PYTHON` requirement before any workspace-wide
cargo).

1. **Crate build + tests incl. doctests** (doctests exercise the public
   re-export surface, so they catch any broken `pub use`):
   - `cargo test -p classic-settings-core` (this crate has no PyO3 dependency).
2. **Downstream API-surface check** — build the crates that import the public
   names to prove nothing moved observably:
   - `classic-config-core`, `classic-version-registry-core`,
     `classic-update-core`, `cpp-bindings/classic-cpp-bridge`,
     `node-bindings/classic-node`, and the `python-bindings` (`-py`) crates.
   - These pull in PyO3 transitively, so set
     `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` first,
     per AGENTS, and use the repo wrappers/`rebuild_rust.ps1` as the skill
     prescribes rather than ad-hoc `cargo` for the Python path.
3. **Lint:** `cargo clippy -p classic-settings-core` clean (no new warnings).
4. Confirm `tests/yaml_dead_code_audit.rs`, `tests/yaml_integration_tests.rs`,
   and `benches/yaml_benchmarks.rs` still pass/compile.

## Done criteria

- `lib.rs` public re-export list and `validators::*` paths are byte-for-byte
  unchanged (diff the exported names, not paths).
- `yaml_ops.rs` is a facade; no single source file mixes the 5 former concerns.
- All 7 accessors route through `navigate()`; no duplicated path-walk loops.
- Merge logic lives only under `merge/`; `yaml_merge.rs` is gone.
- Every split source file has a sibling `_tests.rs` with the `#[path]`
  declaration; `#[serial_test::serial]` preserved on relocated tests.
- `cargo test -p classic-settings-core` (incl. doctests) and the downstream
  crate builds are green; the dead-code audit passes against its new target.

## Risks

- **Test partitioning** of the 1431-LOC `yaml_ops_tests.rs` is the largest,
  most error-prone step — keep `serial` attributes and any shared test helpers
  intact; move helpers to whichever submodule test file needs them (or a small
  shared test util if used by several).
- **Visibility wiring** between `yaml_ops/cache.rs` and `yaml_ops/operations.rs`
  (statics/`CachedYaml`/counters must be `pub(crate)`/`pub(super)`), and
  `merge::documents::merge_yaml_documents_with_source` must stay reachable from
  `loader.rs`.
- **Facade re-exports** for `validators`/`schema_version`/`yaml_ops` must export
  exactly the previously public items — missing one silently breaks a downstream
  build (caught by task-2 downstream check).

## Implementation note

This plan requires source edits and build/test commands. Switch to an
implementation-capable agent to execute it.
