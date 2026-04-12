# Phase 1: YAML -> Settings Merge - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Absorb classic-yaml-core into classic-settings-core so that classic-yaml-core no longer exists as a separate crate. All of its public API surface becomes available from classic-settings-core with no consumer-visible behavior change. All binding crates (C++, Node, Python) are updated to import from settings-core. All three parity gates pass after the merge.

</domain>

<decisions>
## Implementation Decisions

### Module layout inside settings-core
- **D-01:** Add yaml-core's code as new submodules: `yaml_ops.rs` (from yaml-core `lib.rs` -- YamlOperations struct, YamlError, YamlCacheStats, global YAML_CACHE, cache hit/miss tracking) and `yaml_merge.rs` (from yaml-core `merge.rs` -- merge_keys function). Existing settings-core modules (`cache.rs`, `loader.rs`, `error.rs`, `validators.rs`) stay untouched.

### Error type handling
- **D-02:** Keep both `YamlError` (in `yaml_ops.rs`) and `SettingsError` (in `error.rs`) as separate types. Both re-exported at the crate root. Zero churn for consumers since names don't change.

### CacheStats collision resolution
- **D-03:** Rename yaml-core's `CacheStats` to `YamlCacheStats`. Rename `cache_stats()` to `yaml_cache_stats()`. Rename `reset_cache_stats()` to `reset_yaml_cache_stats()`. Settings-core's `CacheStats` and `cache_stats()` stay as-is (surviving crate owns the unprefixed name).

### Re-export strategy
- **D-04:** Flat re-exports at the crate root. All yaml-core public types (YamlOperations, YamlError, YamlCacheStats, merge_keys, etc.) re-exported from `classic_settings_core` root via `pub use`. Consumers migrate by swapping `classic_yaml_core::X` to `classic_settings_core::X`.

### Python binding consolidation
- **D-05:** Fold classic-yaml-py's YAML operations into the existing classic-settings-py crate. Delete classic-yaml-py crate entirely (Cargo.toml workspace member, directory, and all contents).
- **D-06:** Python module name becomes `classic_settings` (already the name of the existing settings-py module). Python consumers migrate from `import classic_yaml` to `import classic_settings`.
- **D-07:** Merge classic_yaml.pyi type stubs into the existing classic_settings.pyi. Delete classic_yaml.pyi.

### Node binding consolidation
- **D-08:** Merge `yaml.rs` module content into `settings.rs` in classic-node. Delete `yaml.rs`. JS exports for yaml operations come from the settings module.

### C++ bridge consolidation and expansion
- **D-09:** Rename `yaml.rs` to `settings.rs` in classic-cpp-bridge. Change C++ namespace from `classic::yaml` to `classic::settings`. In addition to migrating existing yaml bridge functions, add new bridge functions covering the full classic-settings-core surface (cache ops, validators, etc.) to close the parity gap with Python and Node bindings.

### Test and benchmark migration
- **D-10:** Move yaml-core's integration tests and benchmarks as-is into settings-core with updated imports: `tests/yaml_integration_tests.rs`, `tests/yaml_dead_code_audit.rs`, `benches/yaml_benchmarks.rs`. Settings-core gains `tests/` and `benches/` directories.
- **D-11:** Node binding tests: merge `__test__/yaml.spec.ts` content into `__test__/settings.spec.ts`, delete `yaml.spec.ts`. Python binding tests: update imports from `classic_yaml` to `classic_settings` in `test_promoted_residuals_smoke.py`.

### Parity gate timing
- **D-12:** Regenerate all three parity gate baselines (CXX, Python, Node) at the end of Phase 1. Ensures the merge is clean before Phases 2 and 3 proceed. Phase 4 does final cross-merge validation.

### API documentation
- **D-13:** Merge classic-yaml-core.md content into classic-settings-core.md (add yaml ops section). Delete classic-yaml-core.md. Update docs/api/README.md index to remove the yaml entry and update the settings entry.

### Cross-reference cleanup scope
- **D-14:** Update references in active docs only (~15 files): CLAUDE.md, docs/api/*.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md, .planning/codebase/*.md. Skip archived milestone plans and historical docs (.planning/milestones/*, docs/plans/*, docs/prd/complete/*) -- they are snapshots in time.

### Git history preservation
- **D-15:** Use `git mv` for file moves (lib.rs -> yaml_ops.rs, merge.rs -> yaml_merge.rs, tests, benchmarks) to preserve blame history. Content edits (import changes, CacheStats rename, etc.) go in a separate commit after the rename commit.

### Claude's Discretion
- Workspace Cargo.toml dependency cleanup when removing yaml-core
- Cargo feature flag deduplication (both crates have `dhat-heap`)
- Internal import organization within moved files
- Exact ordering of operations within each commit
- Any mechanical details not covered by the decisions above

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rust crate sources (merge targets)
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` -- Full source of yaml-core (YamlOperations, YamlError, CacheStats, YAML_CACHE)
- `ClassicLib-rs/business-logic/classic-yaml-core/src/merge.rs` -- YAML merge-key resolution (merge_keys function)
- `ClassicLib-rs/business-logic/classic-yaml-core/Cargo.toml` -- yaml-core dependencies to absorb
- `ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs` -- settings-core current API surface and re-exports
- `ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml` -- settings-core current dependencies

### Binding crates (update targets)
- `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs` -- Python yaml binding code to fold into settings-py
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` -- Existing Python settings binding (fold target)
- `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` -- Node yaml module to merge into settings.rs
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` -- Node settings module (merge target)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` -- C++ bridge yaml module to rename to settings.rs

### Consumer crates (import path updates)
- `ClassicLib-rs/business-logic/classic-config-core/Cargo.toml` -- depends on classic-yaml-core
- `ClassicLib-rs/business-logic/classic-version-registry-core/Cargo.toml` -- depends on classic-yaml-core
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` -- depends on classic-yaml-core
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` -- depends on classic-yaml-core
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` -- depends on classic-yaml-core

### Parity gates
- `tools/cxx_api_parity/` -- CXX parity gate tooling (baseline regeneration)
- `tools/python_api_parity/check_parity_gate.py` -- Python parity gate
- Node parity: `bun run parity:gate:local` from `ClassicLib-rs/node-bindings/classic-node/`

### API documentation
- `docs/api/classic-yaml-core.md` -- YAML core API doc (merge into settings doc, then delete)
- `docs/api/classic-settings-core.md` -- Settings core API doc (expand with yaml ops section)
- `docs/api/README.md` -- API doc index (update entry)
- `docs/api/binding-parity-overview.md` -- Binding surface reference (update for merged crate)

### Type stubs
- `ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi` -- Python yaml stubs (merge, then delete)
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` -- Python settings stubs (expand)

### Tests
- `ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs` -- Integration tests to migrate
- `ClassicLib-rs/business-logic/classic-yaml-core/tests/phase2_yaml_dead_code_audit.rs` -- Audit tests to migrate
- `ClassicLib-rs/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs` -- Benchmarks to migrate
- `ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts` -- Node yaml tests (merge into settings.spec.ts)
- `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` -- Python test referencing classic_yaml

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classic-settings-py/src/lib.rs` already has a `yaml_to_py()` helper for converting Rust Yaml to Python objects -- can be reused for the yaml-py fold-in
- `classic-settings-core` already re-exports `yaml_rust2::Yaml` at crate root -- yaml-core consumers using `yaml_rust2::Yaml` via settings-core get this for free

### Established Patterns
- Binding crate convention: one `-py` crate per `-core` crate, with `#[pymodule]` function named after the Python module
- Node binding convention: one `.rs` module per domain in classic-node, all NAPI types prefixed with `Js`
- C++ bridge convention: one `.rs` module per domain, `#[cxx::bridge]` with `namespace = "classic::{domain}"`
- Error handling: each crate owns its error enum via `thiserror`, binding layers convert with `to_napi_err()`/`PyErr::new_err()`

### Integration Points
- `classic-config-core` is the heaviest consumer of yaml-core (imports YamlOperations, YamlError, merge_keys)
- `classic-version-registry-core` imports yaml-core for YAML loading during registry initialization
- C++ bridge `scanner.rs` and `config.rs` import yaml-core types alongside their primary domain imports
- CXX parity gate in `tools/cxx_api_parity/` uses `build.rs` to enumerate bridge surface -- will detect the rename

</code_context>

<specifics>
## Specific Ideas

- User wants the C++ bridge to close the parity gap with Python/Node by adding full settings-core bindings (cache ops, validators) during the rename, not just migrating existing yaml functions
- git mv for rename tracking is important -- separate commit for moves vs content edits to preserve blame history
- Archived milestone plans should NOT be updated (they are historical snapshots) -- only active docs get cross-reference cleanup

</specifics>

<deferred>
## Deferred Ideas

- Expand C++ bridge to cover full classic-settings-core surface (cache ops, validators) -- FOLDED into Phase 1 scope per user decision (D-09)

None -- all ideas raised during discussion were either resolved as decisions or folded into Phase 1 scope.

</deferred>

---

*Phase: 01-yaml-settings-merge*
*Context gathered: 2026-04-10*
