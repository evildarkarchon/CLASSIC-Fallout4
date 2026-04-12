# Phase 1: YAML -> Settings Merge - Research

**Researched:** 2026-04-10
**Domain:** Rust workspace crate consolidation (merge classic-yaml-core into classic-settings-core), binding layer updates, parity gate regeneration
**Confidence:** HIGH

## Summary

Phase 1 absorbs `classic-yaml-core` (a pure Rust YAML operations library) into `classic-settings-core` (YAML settings cache). Both crates already share the same foundation layer (`classic-shared-core`), the same key dependencies (`yaml-rust2`, `quick_cache`, `dashmap`), and the same threading model. The merge is structurally clean because yaml-core is a leaf dependency consumed by five crates and three binding layers.

The primary risk areas are: (1) the `CacheStats` name collision between yaml-core and settings-core, resolved by decision D-03 (rename yaml-core's to `YamlCacheStats`); (2) the C++ bridge namespace change from `classic::yaml` to `classic::settings` requires updating `build.rs`, the CXX `#[cxx::bridge]` attribute, the `lib.rs` module declaration, and all C++ consumers; (3) the Python binding merge requires combining two `#[pymodule]` functions into one and merging type stubs; (4) git history preservation via `git mv` requires careful commit sequencing (moves first, then content edits).

**Primary recommendation:** Execute as a sequence of well-separated commits: (1) `git mv` file renames, (2) Rust core content edits and Cargo.toml dependency migration, (3) binding layer consolidation, (4) test/benchmark migration, (5) doc consolidation, (6) parity gate regeneration. Each commit should leave the workspace in a compilable state.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Add yaml-core's code as new submodules: `yaml_ops.rs` (from yaml-core `lib.rs` -- YamlOperations struct, YamlError, YamlCacheStats, global YAML_CACHE, cache hit/miss tracking) and `yaml_merge.rs` (from yaml-core `merge.rs` -- merge_keys function). Existing settings-core modules (`cache.rs`, `loader.rs`, `error.rs`, `validators.rs`) stay untouched.
- D-02: Keep both `YamlError` (in `yaml_ops.rs`) and `SettingsError` (in `error.rs`) as separate types. Both re-exported at the crate root. Zero churn for consumers since names don't change.
- D-03: Rename yaml-core's `CacheStats` to `YamlCacheStats`. Rename `cache_stats()` to `yaml_cache_stats()`. Rename `reset_cache_stats()` to `reset_yaml_cache_stats()`. Settings-core's `CacheStats` and `cache_stats()` stay as-is (surviving crate owns the unprefixed name).
- D-04: Flat re-exports at the crate root. All yaml-core public types (YamlOperations, YamlError, YamlCacheStats, merge_keys, etc.) re-exported from `classic_settings_core` root via `pub use`. Consumers migrate by swapping `classic_yaml_core::X` to `classic_settings_core::X`.
- D-05: Fold classic-yaml-py's YAML operations into the existing classic-settings-py crate. Delete classic-yaml-py crate entirely (Cargo.toml workspace member, directory, and all contents).
- D-06: Python module name becomes `classic_settings` (already the name of the existing settings-py module). Python consumers migrate from `import classic_yaml` to `import classic_settings`.
- D-07: Merge classic_yaml.pyi type stubs into the existing classic_settings.pyi. Delete classic_yaml.pyi.
- D-08: Merge `yaml.rs` module content into `settings.rs` in classic-node. Delete `yaml.rs`. JS exports for yaml operations come from the settings module.
- D-09: Rename `yaml.rs` to `settings.rs` in classic-cpp-bridge. Change C++ namespace from `classic::yaml` to `classic::settings`. In addition to migrating existing yaml bridge functions, add new bridge functions covering the full classic-settings-core surface (cache ops, validators, etc.) to close the parity gap with Python and Node bindings.
- D-10: Move yaml-core's integration tests and benchmarks as-is into settings-core with updated imports: `tests/yaml_integration_tests.rs`, `tests/yaml_dead_code_audit.rs`, `benches/yaml_benchmarks.rs`. Settings-core gains `tests/` and `benches/` directories.
- D-11: Node binding tests: merge `__test__/yaml.spec.ts` content into `__test__/settings.spec.ts`, delete `yaml.spec.ts`. Python binding tests: update imports from `classic_yaml` to `classic_settings` in `test_promoted_residuals_smoke.py`.
- D-12: Regenerate all three parity gate baselines (CXX, Python, Node) at the end of Phase 1.
- D-13: Merge classic-yaml-core.md content into classic-settings-core.md (add yaml ops section). Delete classic-yaml-core.md. Update docs/api/README.md index to remove the yaml entry and update the settings entry.
- D-14: Update references in active docs only (~15 files): CLAUDE.md, docs/api/*.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md, .planning/codebase/*.md. Skip archived milestone plans and historical docs.
- D-15: Use `git mv` for file moves (lib.rs -> yaml_ops.rs, merge.rs -> yaml_merge.rs, tests, benchmarks) to preserve blame history. Content edits (import changes, CacheStats rename, etc.) go in a separate commit after the rename commit.

### Claude's Discretion
- Workspace Cargo.toml dependency cleanup when removing yaml-core
- Cargo feature flag deduplication (both crates have `dhat-heap`)
- Internal import organization within moved files
- Exact ordering of operations within each commit
- Any mechanical details not covered by the decisions above

### Deferred Ideas (OUT OF SCOPE)
None -- all ideas raised during discussion were either resolved as decisions or folded into Phase 1 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| YAML-01 | classic-yaml-core source modules are relocated into classic-settings-core with the same public API surface preserved | D-01 defines module layout; full API inventory below identifies all 20+ public items to re-export |
| YAML-02 | All workspace crates that imported from classic-yaml-core import from classic-settings-core instead | Consumer audit identifies 5 crates (config-core, version-registry-core, scanlog-core, cpp-bridge, classic-node) plus exact import sites |
| YAML-03 | classic-yaml-core crate is removed from Cargo.toml workspace members and its directory deleted | Workspace Cargo.toml member list and dependency references documented |
| YAML-04 | Binding crates (C++, Node, Python) that referenced yaml-core types are updated to the settings-core import path | All three binding layers fully inventoried with exact files, imports, and migration paths |
</phase_requirements>

## Architecture Patterns

### Source Module Layout After Merge

```
ClassicLib-rs/business-logic/classic-settings-core/src/
  lib.rs          # Existing: mod declarations + pub use re-exports (expanded)
  cache.rs        # Existing: SETTINGS_CACHE, CacheStats (settings cache)
  error.rs        # Existing: SettingsError, SettingsSource
  loader.rs       # Existing: sync/async YAML file loaders
  validators.rs   # Existing: settings validation helpers
  yaml_ops.rs     # NEW: YamlOperations, YamlError, YamlCacheStats, YAML_CACHE, merge_keys
  yaml_merge.rs   # NEW: merge_keys_recursive (YAML merge key extension)
```

### yaml-core Complete Public API Inventory (YAML-01)

These items MUST be re-exported from `classic_settings_core` after the merge:

**Types and structs:**
- `YamlOperations` (struct with methods: `new`, `parse_yaml`, `dump_yaml`, `load_yaml_file`, `save_yaml_file`, `get_setting`, `set_setting`, `get_string_value`, `get_vec_value`, `get_hashmap_value`, `get_indexmap_value`, `get_hashmap_vec_value`, `get_indexmap_vec_value`, `get_settings_batch`, `set_settings_batch`, `load_yaml_files_batch`, `get_cache_stats`, `set_cache_enabled`, `is_cache_enabled`, `clear_cache`)
- `YamlError` (enum: `ParseError`, `SerializeError`, `IoError`, `EmptyDocument`, `InvalidValue`, `UnresolvedAlias`, `InvalidKeyPath`, `TypeConversionError`)
- `CacheStats` -> renamed to `YamlCacheStats` per D-03 (struct: `hits`, `misses`, `hit_rate`, `size`, `capacity`)

**Free functions:**
- `cache_stats()` -> renamed to `yaml_cache_stats()` per D-03
- `reset_cache_stats()` -> renamed to `reset_yaml_cache_stats()` per D-03
- `clear_global_yaml_cache()`
- `merge_keys()` (from merge.rs)

**Re-exports:**
- `yaml_rust2::Yaml` (already re-exported by settings-core too)

**Statics (internal but structurally important):**
- `YAML_CACHE: LazyLock<Cache<PathBuf, CachedYaml>>` (128-entry quick_cache)
- `CACHE_HITS: AtomicU64`
- `CACHE_MISSES: AtomicU64`

### Consumer Import Migration Map (YAML-02)

| Crate | File | Current Import | New Import |
|-------|------|----------------|------------|
| classic-config-core | `src/lib.rs:27` | `pub use classic_yaml_core::clear_global_yaml_cache` | `pub use classic_settings_core::clear_global_yaml_cache` |
| classic-config-core | `src/yamldata.rs:18` | `use classic_yaml_core::YamlOperations` | `use classic_settings_core::YamlOperations` |
| classic-config-core | `src/config.rs:8` | `use classic_yaml_core::YamlOperations` | `use classic_settings_core::YamlOperations` |
| classic-version-registry-core | `src/registry.rs:11` | `use classic_yaml_core::YamlOperations` | `use classic_settings_core::YamlOperations` |
| classic-version-registry-core | `src/error.rs:24` | `classic_yaml_core::YamlError` (in `#[from]`) | `classic_settings_core::YamlError` |
| classic-scanlog-core | `Cargo.toml` | `classic-yaml-core = { path = "..." }` | Remove (scanlog-core uses yaml-core transitively, verify no direct `use` statements) |
| classic-cpp-bridge | `src/yaml.rs:10` | `use classic_yaml_core::{CacheStats as YamlCacheStats, ...}` | `use classic_settings_core::{YamlCacheStats, ...}` |
| classic-cpp-bridge | `src/scanner.rs:15` | `use classic_yaml_core::YamlOperations` | `use classic_settings_core::YamlOperations` |
| classic-cpp-bridge | `src/config.rs:682` | `classic_yaml_core::YamlOperations::new()` | `classic_settings_core::YamlOperations::new()` |
| classic-node | `src/yaml.rs:11` | `use classic_yaml_core::{YamlError, YamlOperations, ...}` | `use classic_settings_core::{YamlError, YamlOperations, ...}` |

### Cargo.toml Dependency Changes (YAML-02, YAML-03)

**Workspace Cargo.toml (`ClassicLib-rs/Cargo.toml`):**
- Remove `"business-logic/classic-yaml-core"` from `members`
- Remove `"python-bindings/classic-yaml-py"` from `members`

**Consumer Cargo.toml changes (remove `classic-yaml-core` dependency):**
- `classic-config-core/Cargo.toml`: Remove `classic-yaml-core = { path = "..." }`, already has `classic-settings-core`
- `classic-version-registry-core/Cargo.toml`: Remove `classic-yaml-core = { path = "..." }`, add `classic-settings-core = { path = "..." }`
- `classic-scanlog-core/Cargo.toml`: Remove `classic-yaml-core = { path = "..." }` (verify it doesn't directly use any yaml-core types -- grep shows no direct `use classic_yaml_core` in scanlog-core source)
- `classic-cpp-bridge/Cargo.toml`: Remove `classic-yaml-core = { path = "..." }`, already has `classic-settings-core`
- `classic-node/Cargo.toml`: Remove `classic-yaml-core = { path = "..." }`, already has `classic-settings-core`

**settings-core/Cargo.toml: Dependencies to absorb from yaml-core:**
- `indexmap = { workspace = true }` -- NEEDED (yaml-core uses IndexMap; settings-core does not currently have it)
- `serde_json = { workspace = true }` -- NEEDED (yaml-core has it for CacheStats serialization)
- `dhat-heap` feature already exists in both -- deduplicate (keep one)
- `serde = { workspace = true }` -- already present in settings-core
- `dashmap = { workspace = true }` -- already present in settings-core
- `quick_cache = { workspace = true }` -- already present in settings-core
- `thiserror = { workspace = true }` -- already present in settings-core
- `tracing = { workspace = true }` -- already present in settings-core
- `yaml-rust2 = { workspace = true }` -- already present in settings-core
- `classic-shared-core` -- already present in settings-core

**settings-core/Cargo.toml: Dev-dependencies to absorb from yaml-core:**
- `tempfile = { workspace = true }` -- already present
- `criterion = { version = "0.6.0", features = ["html_reports"] }` -- NEEDED for benchmark harness
- `serial_test = "3.2"` -- already present

### CacheStats Name Collision Resolution (D-03)

Both crates define a `CacheStats` struct and `cache_stats()` function. They track different caches:

| Item | yaml-core (YAML_CACHE) | settings-core (SETTINGS_CACHE) |
|------|----------------------|-------------------------------|
| Cache type | `Cache<PathBuf, CachedYaml>` (128 entries) | `Cache<String, Arc<Vec<Yaml>>>` (64 entries) |
| Struct | `CacheStats` -> rename to `YamlCacheStats` | `CacheStats` (keep) |
| Getter | `cache_stats()` -> rename to `yaml_cache_stats()` | `cache_stats()` (keep) |
| Reset | `reset_cache_stats()` -> rename to `reset_yaml_cache_stats()` | `reset_cache_stats()` (keep) |

The existing C++ bridge already uses the alias pattern: `use classic_yaml_core::{CacheStats as YamlCacheStats, ...}`. After D-03, this becomes a direct import of the renamed struct.

### Binding Layer Consolidation

#### Python (D-05, D-06, D-07)

**Current state:**
- `classic-yaml-py`: `#[pymodule] fn classic_yaml(m: ...)` -- exposes `PyYamlOperations` class + 3 exception types
- `classic-settings-py`: `#[pymodule] fn classic_settings(m: ...)` -- exposes 12 free functions + 3 validator functions

**After merge:**
- `classic-settings-py` gains: `PyYamlOperations` class, `yaml_to_python`/`python_to_yaml` converters, 3 exception types
- `classic-yaml-py` crate deleted entirely
- `classic_yaml.pyi` merged into `classic_settings.pyi`, then deleted
- Python test `test_promoted_residuals_smoke.py` lines 44, 457-478: change `import classic_yaml` to `import classic_settings`, change `classic_yaml.YamlOperations()` to `classic_settings.YamlOperations()`

**Key integration point:** `classic-settings-py` already has a `yaml_to_py()` helper. The yaml-py crate has a separate `yaml_to_python()` and `python_to_yaml()` helper. These are functionally equivalent -- consolidate into one pair of conversion functions.

**New dependencies for classic-settings-py/Cargo.toml:**
- `classic-shared-core` (for PathLike, define_exceptions, etc.)
- `classic-shared-py` (for shared PyO3 utilities)

#### Node (D-08)

**Current state:**
- `yaml.rs`: 17 NAPI functions + `YamlDocument` class, imports from `classic_yaml_core`
- `settings.rs`: 10 NAPI functions + `SettingsCacheStats` struct, imports from `classic_settings_core`

**After merge:**
- All yaml.rs content moves into settings.rs
- yaml.rs is deleted
- `src/lib.rs` line 32 (`mod yaml;`) is removed
- yaml.rs imports change from `classic_yaml_core` to `classic_settings_core`
- `__test__/yaml.spec.ts` content merges into `__test__/settings.spec.ts`
- `yaml.spec.ts` is deleted
- Node `index.d.ts` and exports must be regenerated (NAPI build handles this automatically)

#### C++ Bridge (D-09)

**Current state:**
- `src/yaml.rs`: `#[cxx::bridge(namespace = "classic::yaml")]` with `YamlOps` opaque type, 15 bridge functions, `CacheStats` and `YamlValue` shared structs
- `build.rs`: lists `"src/yaml.rs"` in `cxx_build::bridges([])`
- `src/lib.rs`: `pub mod yaml;`

**After merge:**
- `yaml.rs` renamed to `settings.rs` via `git mv`
- `build.rs`: `"src/yaml.rs"` -> `"src/settings.rs"`
- `src/lib.rs`: `pub mod yaml;` -> `pub mod settings;`
- CXX bridge attribute: `namespace = "classic::yaml"` -> `namespace = "classic::settings"`
- Import: `use classic_yaml_core::{...}` -> `use classic_settings_core::{...}`
- D-09 additionally requires adding bridge functions for the full settings-core surface (cache ops, validators) to close parity gap

**C++ consumer impact:** Any C++ code using `classic::yaml::*` must change to `classic::settings::*`. This affects `classic-cli/` and `classic-gui/` source files.

### Test and Benchmark Migration (D-10, D-11)

**Rust tests to migrate:**
1. `classic-yaml-core/tests/integration_tests.rs` -> `classic-settings-core/tests/yaml_integration_tests.rs`
   - Imports: `use classic_yaml_core::{...}` -> `use classic_settings_core::{...}`
   - Function name changes: `cache_stats` -> `yaml_cache_stats`, `reset_cache_stats` -> `reset_yaml_cache_stats`, `clear_global_yaml_cache` stays same
2. `classic-yaml-core/tests/phase2_yaml_dead_code_audit.rs` -> `classic-settings-core/tests/yaml_dead_code_audit.rs`
   - Uses `include_str!("../src/lib.rs")` -- path needs updating to `include_str!("../src/yaml_ops.rs")`
   - Benchmark path reference also needs updating
3. `classic-yaml-core/benches/yaml_benchmarks.rs` -> `classic-settings-core/benches/yaml_benchmarks.rs`
   - Imports: `use classic_yaml_core::YamlOperations` -> `use classic_settings_core::YamlOperations`
   - Criterion group and `[[bench]]` entry needed in settings-core Cargo.toml
   - Benchmark uses shared `#[path = "../../../benches/common/mod.rs"]` -- path still valid after move

**settings-core inline tests (lib.rs):** Stay as-is. No changes needed.

**yaml-core inline tests (moved yaml_ops.rs):** These use `super::*` and will work after the module becomes part of settings-core.

### Documentation Changes (D-13, D-14)

**Files requiring updates (active docs only):**

| File | Change |
|------|--------|
| `docs/api/classic-yaml-core.md` | Merge content into `classic-settings-core.md`, then delete |
| `docs/api/classic-settings-core.md` | Add yaml operations section |
| `docs/api/README.md` | Remove yaml-core entry (line 6), update settings-core entry |
| `docs/api/binding-parity-overview.md` | Update crate references |
| `docs/api/classic-shared-core.md` | Minor reference updates |
| `docs/api/classic-config-core.md` | Update yaml-core references |
| `docs/api/classic-version-registry-core.md` | Update yaml-core references |
| `docs/api/classic-constants-core.md` | Update yaml-core references |
| `docs/api/classic-cpp-bridge-data-entrypoints.md` | Update namespace references |
| `CLAUDE.md` | Update crate count, dependency descriptions |
| `AGENTS.md` | Update if it references yaml-core |

### git mv Strategy (D-15)

**Commit 1: File moves (git mv)**
```
git mv ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs \
       ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs
git mv ClassicLib-rs/business-logic/classic-yaml-core/src/merge.rs \
       ClassicLib-rs/business-logic/classic-settings-core/src/yaml_merge.rs
git mv ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs \
       ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_integration_tests.rs
git mv ClassicLib-rs/business-logic/classic-yaml-core/tests/phase2_yaml_dead_code_audit.rs \
       ClassicLib-rs/business-logic/classic-settings-core/tests/yaml_dead_code_audit.rs
git mv ClassicLib-rs/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs \
       ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs
```

**Commit 2: Content edits** (import path changes, CacheStats rename, lib.rs mod declarations, Cargo.toml updates)

This preserves `git log --follow` blame history through the rename.

### Parity Gate Regeneration (D-12)

**CXX parity gate:**
- `tools/cxx_api_parity/generate_baseline.py` -- regenerate baseline
- The gate uses `build.rs` to enumerate bridge surface; the `yaml.rs` -> `settings.rs` rename will be detected
- Run: `python tools/cxx_api_parity/check_parity_gate.py` to verify

**Python parity gate:**
- `python tools/python_api_parity/check_parity_gate.py --repo-root .`
- The merged `classic_settings` module will have a larger surface (yaml ops + settings ops)
- `deferred_total` should remain at 0 after merge

**Node parity gate:**
- From `ClassicLib-rs/node-bindings/classic-node/`: `bun run parity:gate:local`
- The merged settings module exports will include yaml functions

## Common Pitfalls

### Pitfall 1: CacheStats Collision in Re-exports
**What goes wrong:** Both `yaml_ops.rs` and `cache.rs` define `CacheStats`. If both are `pub use`d at root, compilation fails with duplicate definitions.
**Why it happens:** Two crates being merged both chose the same name for their stats struct.
**How to avoid:** Apply D-03 rename BEFORE adding the `pub use` re-exports. In `yaml_ops.rs`, rename the struct to `YamlCacheStats` and the function to `yaml_cache_stats()`.
**Warning signs:** Compilation error about duplicate items in scope.

### Pitfall 2: git mv with Content Changes in Same Commit
**What goes wrong:** If `git mv` and content edits (import changes) happen in the same commit, git may not track the rename, breaking `git log --follow`.
**Why it happens:** Git's rename detection has a similarity threshold (~50%). Large content changes alongside the move cause git to see it as a delete+add instead of a rename.
**How to avoid:** D-15 mandates separate commits: first commit does only `git mv` (file moves), second commit does content edits.
**Warning signs:** `git log --follow <new-path>` does not show pre-rename history.

### Pitfall 3: Incomplete Workspace Member Removal
**What goes wrong:** After deleting the crate directory, `cargo build` fails with "failed to read member" if the workspace `members` list still references it.
**Why it happens:** Forgetting to update the workspace Cargo.toml when removing a crate.
**How to avoid:** Always update `ClassicLib-rs/Cargo.toml` members list AND remove the crate directory in the same commit.
**Warning signs:** `cargo build --workspace` fails immediately with path-not-found.

### Pitfall 4: C++ Consumer Namespace Change
**What goes wrong:** After renaming `classic::yaml` to `classic::settings`, C++ code in `classic-cli/` and `classic-gui/` that uses `classic::yaml::*` types/functions fails to compile.
**Why it happens:** The CXX bridge generates C++ headers from the namespace attribute; changing the Rust namespace changes the C++ namespace.
**How to avoid:** Search C++ source for `classic::yaml` references and update them. Check both `#include` directives for generated headers and qualified name usage.
**Warning signs:** C++ linker errors about undefined symbols in `classic::yaml` namespace.

### Pitfall 5: Python Module Name Mismatch
**What goes wrong:** After merging yaml-py into settings-py, Python test code using `import classic_yaml` fails with `ModuleNotFoundError`.
**Why it happens:** The `classic_yaml` Python module no longer exists; it was absorbed into `classic_settings`.
**How to avoid:** Grep all Python files for `classic_yaml` imports and update to `classic_settings`.
**Warning signs:** `pytest` import failures.

### Pitfall 6: Dead Code Audit Test Path References
**What goes wrong:** The `phase2_yaml_dead_code_audit.rs` test uses `include_str!("../src/lib.rs")` which pointed to yaml-core's lib.rs. After the move, the file is now `yaml_ops.rs` and the path is relative to a different crate.
**Why it happens:** `include_str!` uses paths relative to the source file's location.
**How to avoid:** Update the `include_str!` paths in the dead code audit test to reference `../src/yaml_ops.rs` and `../benches/yaml_benchmarks.rs`.
**Warning signs:** Compilation error on `include_str!` -- file not found.

### Pitfall 7: Two Different yaml_to_py / yaml_to_python Functions
**What goes wrong:** After merging yaml-py into settings-py, there are two nearly-identical Yaml-to-Python conversion functions with slightly different names and implementations.
**Why it happens:** Each binding crate independently implemented the same conversion.
**How to avoid:** During the merge, consolidate into a single `yaml_to_py()` function. The existing `classic-settings-py` version uses `PyList::empty(py)` while `classic-yaml-py` uses `PyList::new(py, items)`. Pick one and use it consistently.
**Warning signs:** Clippy warning about duplicate code, or subtle conversion differences.

### Pitfall 8: Benchmark Common Module Path
**What goes wrong:** The yaml benchmarks reference a shared config module via `#[path = "../../../benches/common/mod.rs"]`. After moving the benchmark file, this relative path may be wrong.
**Why it happens:** The benchmark file moves to a different directory depth.
**How to avoid:** Verify the `#[path]` attribute resolves correctly from the new location. The path `../../../benches/common/mod.rs` means "three levels up from the current file's directory" -- from `ClassicLib-rs/business-logic/classic-settings-core/benches/` this resolves to `ClassicLib-rs/benches/common/mod.rs`, which is the same resolution as from yaml-core's benches directory.
**Warning signs:** Compilation error about missing module.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom parser | `yaml_rust2::YamlLoader` | Already the standard throughout the codebase |
| Cache statistics | Custom tracking | Existing `CacheStats` / `YamlCacheStats` patterns | Both crates have battle-tested patterns |
| CXX header generation | Manual headers | `cxx-build` in `build.rs` | CXX generates correct headers from bridge definitions |
| Python type stubs | Manual `.pyi` | Copy and merge existing stubs | Both stubs follow the same conventions |
| Parity gate baselines | Manual counting | `generate_baseline.py`, `parity:gate:local` | Automated tools detect drift |

## Code Examples

### settings-core lib.rs After Merge (D-01, D-04)

```rust
// Existing modules (unchanged)
mod cache;
mod error;
mod loader;
pub mod validators;

// NEW: yaml operations (absorbed from classic-yaml-core)
mod yaml_ops;
mod yaml_merge;

// Existing re-exports (unchanged)
pub use cache::{
    CacheStats, cache_keys, cache_size, cache_stats, clear_cache, get_cached, invalidate,
    is_cached, load_batch_async, load_batch_sync, load_settings_async, load_settings_sync,
    reset_cache_stats,
};
pub use error::{Result, SettingsError, SettingsSource};
pub use loader::{
    load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_merged_async,
    load_yaml_merged_sync, load_yaml_sync, merge_yaml_documents, parse_yaml_content,
};

// NEW: yaml operations re-exports (D-04 flat re-exports)
pub use yaml_ops::{
    YamlCacheStats, YamlError, YamlOperations,
    clear_global_yaml_cache, yaml_cache_stats, reset_yaml_cache_stats,
};
pub use yaml_merge::merge_keys;

// Re-export yaml_rust2 types for convenience (already present)
pub use yaml_rust2::Yaml;
```

### CacheStats Rename in yaml_ops.rs (D-03)

```rust
// BEFORE (in yaml-core lib.rs):
pub struct CacheStats { ... }
pub fn cache_stats() -> CacheStats { ... }
pub fn reset_cache_stats() { ... }

// AFTER (in yaml_ops.rs inside settings-core):
pub struct YamlCacheStats { ... }
pub fn yaml_cache_stats() -> YamlCacheStats { ... }
pub fn reset_yaml_cache_stats() { ... }
```

### C++ Bridge Module After Rename (D-09)

```rust
// src/settings.rs (renamed from yaml.rs)
use classic_settings_core::{
    YamlCacheStats, YamlOperations, yaml_cache_stats,
};

// ...existing bridge functions with updated imports...

#[cxx::bridge(namespace = "classic::settings")]
mod ffi {
    // Same structs and functions, but now under classic::settings namespace
    struct CacheStats { ... }
    struct YamlValue { ... }
    extern "Rust" {
        type YamlOps;
        // ... all existing functions ...
        // NEW: settings-core cache/validator bridge functions for parity gap closure
    }
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust `cargo test` + Criterion 0.6 benchmarks |
| Config file | `ClassicLib-rs/Cargo.toml` (workspace) |
| Quick run command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| YAML-01 | yaml-core public API available from settings-core | unit | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | Wave 0 (tests migrate with source) |
| YAML-02 | All consumer crates compile with new import paths | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (build check) |
| YAML-03 | yaml-core removed, workspace builds without it | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (build check) |
| YAML-04 | Binding crates compile and pass tests | integration | Node: `bun run test:bun` from classic-node; Python: `uv run pytest ClassicLib-rs/python-bindings/tests -q`; C++: `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` | Existing test files |

### Sampling Rate
- **Per task commit:** `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Per wave merge:** Full suite + clippy + fmt check
- **Phase gate:** Full suite green + all three parity gates pass before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `ClassicLib-rs/business-logic/classic-settings-core/tests/` directory needs creation
- [ ] `ClassicLib-rs/business-logic/classic-settings-core/benches/` directory needs creation
- [ ] `[[bench]]` entry in settings-core `Cargo.toml` for `yaml_benchmarks`
- [ ] Criterion `0.6.0` dev-dependency in settings-core `Cargo.toml`

## Project Constraints (from CLAUDE.md)

- **Build commands:** Use `cargo build/test/fmt/clippy --workspace --manifest-path ClassicLib-rs/Cargo.toml` for Rust workspace operations
- **C++ tests:** Always use PowerShell build wrappers (`build_cli.ps1 -Test`, `build_gui.ps1 -Test`), never raw ctest
- **Node bindings:** From `ClassicLib-rs/node-bindings/classic-node/`: `bun install && bun run build && bun run parity:gate:local`
- **Python bindings:** Use venv at `ClassicLib-rs/python-bindings/.venv`, run `uv run pytest ClassicLib-rs/python-bindings/tests -q`
- **Git Bash + Rust:** Source `tools/use_msvc_from_git_bash.sh` before Rust or MSVC C++ commands
- **No `nul` writes:** Never output to `nul` on Windows
- **Commit convention:** Prefix commits with `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`
- **GSD workflow:** Start work through GSD commands, not direct repo edits
- **Formatting:** Run `cargo fmt` and `uv run ruff format .` before commits
- **API docs:** Consult and update `docs/api/` when changing public APIs

## Sources

### Primary (HIGH confidence)
- Direct source code inspection of all affected files (yaml-core, settings-core, all binding crates, all consumer crates)
- `ClassicLib-rs/Cargo.toml` workspace member list and dependency graph
- Grep audit for all `classic_yaml_core` and `classic-yaml-core` references across workspace
- All Cargo.toml dependency lists for affected crates

### Secondary (MEDIUM confidence)
- Project CLAUDE.md, AGENTS.md, and docs/api/README.md for conventions
- `.agents/skills/classic-project-guide/SKILL.md` for repo guardrails

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies are existing workspace members, no new external libraries needed
- Architecture: HIGH - Direct source code inspection of all 30+ affected files, complete import/export mapping
- Pitfalls: HIGH - Based on concrete code analysis, not hypothetical scenarios

**Research date:** 2026-04-10
**Valid until:** Indefinite (codebase-specific structural analysis, not library version dependent)
