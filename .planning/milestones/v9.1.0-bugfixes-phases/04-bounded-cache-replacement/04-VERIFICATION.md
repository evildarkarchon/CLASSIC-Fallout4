---
phase: 04-bounded-cache-replacement
verified: 2026-04-06T05:15:30.9604023Z
status: passed
score: 5/5 must-haves verified
---

# Phase 4: Bounded Cache Replacement Verification Report

**Phase Goal:** All global caches have bounded memory with `quick_cache` eviction semantics and expose consistent observability through CacheStats
**Verified:** 2026-04-06T05:15:30.9604023Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `YAML_CACHE` uses bounded `quick_cache` capacity 128 and keeps mtime-aware freshness semantics | ✓ VERIFIED | `classic-yaml-core/src/lib.rs:145`, `:547-558`, `:580-587`; bounded test passed via `cargo test -p classic-yaml-core ... test_cache_size_is_bounded_without_assuming_evicted_key` |
| 2 | `SETTINGS_CACHE` uses bounded `quick_cache` capacity 64 and preserves manual invalidation helpers | ✓ VERIFIED | `classic-settings-core/src/cache.rs:17`, `:261-343`, `:390-392`; bounded test passed via `cargo test -p classic-settings-core ... test_bounded_cache_never_exceeds_capacity_without_asserting_victim_order` |
| 3 | `HASH_CACHE` uses bounded `quick_cache` capacity 1024 and exposes public stats/reset helpers | ✓ VERIFIED | `classic-file-io-core/src/hash.rs:52`, `:106-132`, `:264-309`; bounded test passed via `cargo test -p classic-file-io-core ... test_hash_cache_bounded_eviction` |
| 4 | YAML, settings, and hash caches expose one canonical stats contract (`hits`, `misses`, `hit_rate`, `size`, `capacity`) across Rust, Node, Python, and C++ surfaces | ✓ VERIFIED | Core structs in `classic-yaml-core/src/lib.rs:167-178`, `classic-settings-core/src/cache.rs:38-50`, `classic-file-io-core/src/hash.rs:60-73`; Node adapters in `classic-node/src/yaml.rs:356-372`, `src/settings.rs:77-91`, `:199-210`, `src/fileio.rs:348-370`; Python adapters/stubs in `classic-yaml-py/src/lib.rs:263-271`, `classic_yaml.pyi:40-48,334-354`, `classic-settings-py/src/lib.rs:346-370`, `classic_settings.pyi:39-47,241-267`, `classic-file-io-py/src/hash.rs:162-179`, `classic_file_io.pyi:44-52,844-871`; C++ bridge in `classic-cpp-bridge/src/yaml.rs:190-218`, `src/config.rs:317-339`, `src/files.rs:286-309` |
| 5 | Clear/reset APIs still provide deterministic test isolation with bounded caches | ✓ VERIFIED | YAML `clear_global_yaml_cache()` in `classic-yaml-core/src/lib.rs:1354-1355` and integration tests `tests/integration_tests.rs:210-220`; settings `clear_cache()`/`reset_cache_stats()` in `classic-settings-core/src/cache.rs:342-343,98-101` plus tests `:863-921`; hash `clear_cache()`/`reset_cache_stats()` in `classic-file-io-core/src/hash.rs:264-295` plus tests `:452-545`; Node hash helper test `classic-node/__test__/fileio.spec.ts:466-505`; Python smoke `python-bindings/tests/test_tier1_parity_smoke.py:428-446` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` | 128-entry bounded YAML cache + canonical stats | ✓ VERIFIED | `gsd-tools verify artifacts` passed; `Cache::new(128)` and canonical `CacheStats` present |
| `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs` | 64-entry bounded settings cache + canonical stats | ✓ VERIFIED | `gsd-tools verify artifacts` passed; manual invalidation helpers still exported |
| `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs` | 1024-entry bounded hash cache + public stats/reset APIs | ✓ VERIFIED | `gsd-tools verify artifacts` passed; `FileHasher::cache_stats/reset_cache_stats` present |
| `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` | Node YAML cache stats adapter | ✓ VERIFIED | Adapts canonical YAML stats to exact snake_case keys |
| `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` | Node settings cache stats DTO | ✓ VERIFIED | `SettingsCacheStats` exposes `capacity`, no `keys` field |
| `ClassicLib-rs/node-bindings/classic-node/src/fileio.rs` | Node hash cache stats/reset/clear helpers | ✓ VERIFIED | `get_hash_cache_stats`, `reset_hash_cache_stats`, `clear_hash_cache` wired to `FileHasher` |
| `ClassicLib-rs/node-bindings/classic-node/index.d.ts` | Committed TS contract for canonical cache stats | ✓ VERIFIED | Declares `HashCacheStats`, `SettingsCacheStats`, and `yamlGetCacheStats()` with `hit_rate`/`capacity` |
| `ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi` | Python YAML cache stats contract | ✓ VERIFIED | `YamlCacheStats` typed dict includes canonical five keys |
| `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` | Python settings cache stats contract | ✓ VERIFIED | `SettingsCacheStats` typed dict + `cache_stats()` declared |
| `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` | Python hash cache stats/reset helpers | ✓ VERIFIED | `cache_stats()` and `reset_cache_stats()` present |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/{yaml,config,files}.rs` | C++ cache stats entrypoints | ✓ VERIFIED | Explicit YAML/settings/hash cache stats helpers all present |
| `docs/api/classic-{yaml-core,settings-core,file-io-core}.md` | Updated core cache contracts | ✓ VERIFIED | Docs describe capacities and canonical stats |
| `docs/api/classic-cpp-bridge-data-entrypoints.md` | C++ cache stats docs | ✓ VERIFIED | Documents YAML/settings/hash cache stats helpers and adapters |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `classic-yaml-core/src/lib.rs` | `quick_cache::sync::Cache` | global YAML cache init | ✓ WIRED | `gsd-tools verify key-links` found `Cache::new(128)` |
| `classic-yaml-core/src/lib.rs` | `CachedYaml.modified` | stale-entry invalidation | ✓ WIRED | `load_yaml_file()` checks mtime then removes stale entries |
| `classic-settings-core/src/cache.rs` | `quick_cache::sync::Cache` | `SETTINGS_CACHE` init | ✓ WIRED | `gsd-tools verify key-links` found `Cache::new(64)` |
| `classic-settings-core/src/cache.rs` | invalidate/clear/reset helpers | public lifecycle surface | ✓ WIRED | `invalidate`, `clear_cache`, `reset_cache_stats` still exported |
| `classic-file-io-core/src/hash.rs` | `quick_cache::sync::Cache` | `HASH_CACHE` init | ✓ WIRED | `gsd-tools verify key-links` found `Cache::new(1024)` |
| `classic-node/src/yaml.rs` | `classic_yaml_core::cache_stats()` | `yaml_get_cache_stats()` | ✓ WIRED | `yaml_get_cache_stats()` directly reads core stats |
| `classic-node/src/fileio.rs` | `classic_file_io_core::hash::FileHasher` | Node hash cache helpers | ✓ WIRED | `get/reset/clear_hash_cache*` call `FileHasher` helpers |
| `classic-yaml-py/src/lib.rs` | `classic_yaml_core::cache_stats()` | PyO3 dict adapter | ✓ WIRED | `get_cache_stats()` builds dict from core stats |
| `classic-file-io-py/src/hash.rs` | `FileHasher` | Python hash cache helpers | ✓ WIRED | `cache_stats/reset_cache_stats/clear_cache` forward directly |
| `classic-cpp-bridge/src/yaml.rs` | `classic_yaml_core::cache_stats()` | `yaml_ops_cache_stats()` | ✓ WIRED | CXX DTO built from core stats |
| `classic-cpp-bridge/src/config.rs` | `classic_settings_core::cache_stats()` | `settings_cache_stats()` | ✓ WIRED | CXX DTO built from settings core stats |
| `classic-cpp-bridge/src/files.rs` | `FileHasher::cache_stats()` | `hash_cache_stats()` | ✓ WIRED | CXX DTO built from hash cache stats |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `classic-yaml-core/src/lib.rs` | `hits/misses/size/capacity` | `CACHE_HITS`, `CACHE_MISSES`, `YAML_CACHE.len()/capacity()` | Real runtime counters + bounded cache state | ✓ FLOWING |
| `classic-settings-core/src/cache.rs` | `hits/misses/size/capacity` | `CACHE_HITS`, `CACHE_MISSES`, `SETTINGS_CACHE.len()/capacity()` | Real runtime counters + bounded cache state | ✓ FLOWING |
| `classic-file-io-core/src/hash.rs` | `hits/misses/size/capacity` | `CACHE_HITS`, `CACHE_MISSES`, `HASH_CACHE.len()/capacity()` | Real runtime counters + bounded cache state | ✓ FLOWING |
| `classic-node/src/yaml.rs` | `stats` | `yaml_cache_stats()` | Directly forwards core YAML stats | ✓ FLOWING |
| `classic-node/src/settings.rs` | `stats` | `core::cache_stats()` | Directly forwards settings core stats | ✓ FLOWING |
| `classic-node/src/fileio.rs` | `stats` | `FileHasher::cache_stats()` | Directly forwards hash core stats | ✓ FLOWING |
| `classic-yaml-py/src/lib.rs` / `classic-settings-py/src/lib.rs` | Python dict stats | `core::cache_stats()` | Direct dict adapters over core stats | ✓ FLOWING |
| `classic-file-io-py/src/hash.rs` / C++ bridge helpers | Python/C++ stats DTOs | `FileHasher::cache_stats()` / core cache stats | Direct adapters over real core data | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| YAML cache stays bounded under eviction pressure | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml test_cache_size_is_bounded_without_assuming_evicted_key` | `1 passed` | ✓ PASS |
| Settings cache stays bounded under eviction pressure | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml test_bounded_cache_never_exceeds_capacity_without_asserting_victim_order` | `1 passed` | ✓ PASS |
| Hash cache stays bounded at 1024 entries | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml test_hash_cache_bounded_eviction` | `1 passed` | ✓ PASS |
| Node hash binding exposes canonical stats contract | `bun test __test__/fileio.spec.ts -t "report canonical stats for first miss then repeated hit"` | `1 pass` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `CACHE-01` | `04-01-PLAN.md` | Replace unbounded `DashMap` in `YAML_CACHE` with `quick_cache::sync::Cache` (capacity 128) | ✓ SATISFIED | `classic-yaml-core/src/lib.rs:145`, `:547-558`, `:580-587`; YAML bounded test passed |
| `CACHE-02` | `04-02-PLAN.md` | Replace unbounded `DashMap` in `SETTINGS_CACHE` with `quick_cache::sync::Cache` (capacity 64) | ✓ SATISFIED | `classic-settings-core/src/cache.rs:17`, `:261-343`, `:364-392`; settings bounded test passed |
| `CACHE-03` | `04-03-PLAN.md` | Replace unbounded `DashMap` in `HASH_CACHE` with `quick_cache::sync::Cache` (capacity 1024) | ✓ SATISFIED | `classic-file-io-core/src/hash.rs:52`, `:106-132`, `:264-309`; hash bounded test passed |
| `CONS-03` | `04-01`..`04-06` plans | Expose consistent `CacheStats` struct (hits, misses, hit rate, size, capacity) on all three bounded caches | ✓ SATISFIED | Canonical core structs plus Node/Python/C++ adapters and tests/contracts all match the five-field shape |

**Orphaned requirements:** None. `REQUIREMENTS.md` maps only `CACHE-01`, `CACHE-02`, `CACHE-03`, and `CONS-03` to Phase 4, and all four appear in Phase 4 plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs` | 68 | Stale comment still says cache uses `DashMap` | ⚠️ Warning | Documentation drift only; implementation is correctly on `quick_cache` |
| `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` | 11 | Stale stub doc still says settings cache uses `DashMap` | ⚠️ Warning | Static docs drift only; runtime/stub contract itself is correct |

### Gaps Summary

No blocking gaps found. The phase goal is achieved: all three global caches are bounded with `quick_cache`, the canonical five-field cache stats contract exists in Rust core and is surfaced consistently through Node, Python, and C++ adapters, and clear/reset isolation behavior remains covered by tests.

Minor non-blocking documentation drift remains in two Python binding comments that still mention `DashMap`, but this does not affect the implemented cache behavior or published cache-stats contract.

---

_Verified: 2026-04-06T05:15:30.9604023Z_
_Verifier: the agent (gsd-verifier)_
