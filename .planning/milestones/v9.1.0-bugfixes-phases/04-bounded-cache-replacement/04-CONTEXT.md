# Phase 4: Bounded Cache Replacement - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the three global unbounded caches with bounded `quick_cache::sync::Cache` implementations and expose a consistent cache-observability contract through `CacheStats`. This phase is about bounding memory and aligning cache visibility, not redesigning cache semantics or broadening into unrelated performance work.

</domain>

<decisions>
## Implementation Decisions

### Capacity Targets
- **D-01:** Treat `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` as the source of truth for cache capacities and phase numbering. Implement `YAML_CACHE=128`, `SETTINGS_CACHE=64`, and `HASH_CACHE=1024`. Ignore the older conflicting values in `.planning/research/SUMMARY.md`.

### CacheStats Contract
- **D-02:** The canonical typed `CacheStats` contract for all three caches is exactly: `hits`, `misses`, `hit_rate`, `size`, and `capacity`.
- **D-03:** Cache-specific detail stays outside that canonical struct. If YAML still needs byte totals or settings still needs key listings, expose those through separate helpers or adapter-specific surfaces rather than expanding the shared `CacheStats` contract.

### Binding Exposure
- **D-04:** Phase 4 aligns cache stats across all binding surfaces now, not just Rust core. Where a binding already exposes cache stats, update it to match the new shared contract. Where a binding lacks cache-stat exposure for one of these caches, add it in this phase.
- **D-05:** Existing public cache helpers may remain, but they should derive from or stay consistent with the canonical Phase 4 `CacheStats` contract instead of defining competing shapes.

### Behavior Preservation
- **D-06:** Preserve each cache's current runtime behavior while replacing the backing store. YAML remains mtime-aware, settings remains caller-managed/manual invalidation, and the hash cache remains path-keyed with explicit clear behavior. Phase 4 does not harmonize freshness rules across the three caches.

### Test Isolation
- **D-07:** Keep the existing public clear/reset entrypoints as the supported test-isolation surface. Do not add a new public `reset_for_tests()` API.
- **D-08:** Rewrite tests to assert through public behavior and stats rather than `DashMap` internals like iteration or `contains_key()`. Internal or `#[cfg(test)]` helpers are acceptable only if strictly necessary to preserve deterministic test isolation.

### the agent's Discretion
- The exact `quick_cache` wiring per crate, as long as it honors the locked capacities above and keeps concurrency-friendly reads.
- The internal accounting approach used to produce `size` and `capacity` consistently across all three caches.
- The exact DTO/function naming for new binding-facing cache-stat helpers, as long as all bindings converge on the same canonical stats shape.

</decisions>

<specifics>
## Specific Ideas

- Treat `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` as canonical over the stale `.planning/research/SUMMARY.md` entries for this phase.
- All bindings should be aligned in Phase 4, including adding new cache-stat exposure where it does not exist today.
- The shared `CacheStats` shape should stay small and uniform; extra cache-specific detail belongs on separate helpers.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Contract
- `.planning/ROADMAP.md` - Phase 4 goal, success criteria, and locked capacities (`128`, `64`, `1024`)
- `.planning/PROJECT.md` - milestone-level constraints: health-only scope, avoid unnecessary user-facing API reshaping, and LRU eviction as a milestone decision
- `.planning/REQUIREMENTS.md` - `CACHE-01`, `CACHE-02`, `CACHE-03`, and `CONS-03`
- `.planning/STATE.md` - current milestone note that `CONS-03` is paired with Phase 4

### Public API Docs
- `docs/api/README.md` - required doc-update rule for public Rust and binding-facing API changes
- `docs/api/classic-yaml-core.md` - current YAML cache stats contract, legacy `get_cache_stats()` helper, and cache invalidation behavior
- `docs/api/classic-settings-core.md` - current settings cache stats contract and cache-management helper behavior
- `docs/api/classic-file-io-core.md` - current `FileHasher` cache boundary and hash-cache behavior
- `docs/api/classic-config-core.md` - `clear_global_yaml_cache()` re-export boundary for YAML cache-sensitive callers

### Core Cache Implementations
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` - `YAML_CACHE`, current typed `CacheStats`, legacy `get_cache_stats()`, and YAML cache tests that currently depend on `DashMap` internals
- `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs` - `SETTINGS_CACHE`, current typed `CacheStats`, and helper APIs like `cache_keys()`, `clear_cache()`, and `reset_cache_stats()`
- `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs` - `HASH_CACHE`, current hash-cache API surface, and tests
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` - existing `quick_cache::sync::Cache` usage pattern already established in the repo

### Binding And Contract Surfaces
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs` - current C++ YAML cache clear/size bridge and likely C++ integration point for cache stats
- `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` - current Node YAML cache helpers returning `{ cachedFiles, totalBytes }`
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` - current Node `SettingsCacheStats` DTO and cache-stat exports
- `ClassicLib-rs/node-bindings/classic-node/src/fileio.rs` - current Node hash-cache entrypoints via `FileHasher`
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` - existing Node public cache-stat and file-I/O contract
- `ClassicLib-rs/node-bindings/classic-node/__test__/settings.spec.ts` - settings cache-stat contract tests
- `ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts` - YAML cache-stat contract tests
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` - current Python settings cache-stat dict surface
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` - Python settings stub contract
- `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs` - current Python YAML cache helper surface
- `ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi` - Python YAML stub contract
- `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` - current Python hash-cache surface through `PyFileHasher`
- `ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi` - Python hash-cache stub contract

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`: already uses `quick_cache::sync::Cache` for `FileIOCore.read_cache`, giving Phase 4 an in-repo replacement pattern.
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs`: already has atomic hit/miss counters, a typed `CacheStats`, and legacy helper paths that can be preserved alongside the shared contract.
- `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs`: already has the same hit/miss counter pattern plus helper functions like `cache_keys()`, `clear_cache()`, and `reset_cache_stats()`.
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs`: already shows the repo's Node DTO/export pattern for cache stats.
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs`: already shows the repo's Python dict-style cache-stat adapter pattern.

### Established Patterns
- Business logic stays in Rust core; bindings adapt Rust state rather than inventing separate cache behavior.
- Public API and binding contract files are expected to move with source changes (`docs/api/*.md`, `index.d.ts`, `.pyi`, and contract tests).
- Existing clear/reset functions are already used as test-isolation hooks; Phase 4 should preserve that pattern.
- `quick_cache` is already a workspace dependency and already accepted in repo code, so this phase should reuse that established dependency rather than introducing a different cache mechanism.

### Integration Points
- YAML cache work centers on `classic-yaml-core`, plus adapter updates in C++ `src/yaml.rs`, Node `src/yaml.rs`, and Python `classic-yaml-py`.
- Settings cache work centers on `classic-settings-core/src/cache.rs`, plus Node `src/settings.rs` and Python `classic-settings-py`.
- Hash cache work centers on `classic-file-io-core/src/hash.rs`, with existing Node integration in `classic-node/src/fileio.rs` and Python integration in `classic-file-io-py/src/hash.rs`.
- C++ currently only exposes YAML cache management directly; if "all bindings" is interpreted literally during planning, the C++ bridge may need new explicit cache-stat entrypoints rather than just updates to existing contracts.

</code_context>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 04-bounded-cache-replacement*
*Context gathered: 2026-04-05*
