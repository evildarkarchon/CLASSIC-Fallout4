# Roadmap: CLASSIC Codebase Health Milestone

## Overview

This milestone resolves every concern from the codebase audit: deprecated APIs, dead code, global state bugs, unbounded caches, hot-path allocations, TOCTOU unsafe mmap, and workspace housekeeping. The work proceeds in dependency order -- deprecated API callers migrate first (unblocking dead code removal), then three independent workstreams (FCX state, bounded caches, pattern caching) execute in parallel, followed by isolated safety and housekeeping work. Every change is internal; no user-facing APIs change shape.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Deprecated API Migration** - Migrate all callers off deprecated methods and add binding-surface deprecation warnings
- [ ] **Phase 2: Dead Code Removal** - Delete dead code items, remove deprecated methods, eliminate legacy fallback path
- [ ] **Phase 3: FCX State Hardening** - Fix silent reset bug, expose FCX reset/issues in all binding surfaces, add contention tests
- [ ] **Phase 4: Bounded Cache Replacement** - Replace three unbounded DashMap caches with quick_cache LRU, expose CacheStats
- [ ] **Phase 5: Pattern Caching and Performance** - Cache compiled regex/AhoCorasick in mod detector hot paths, cache LogParser in bridge, add benchmarks
- [ ] **Phase 6: mmap TOCTOU Safety** - Switch mmap to map_copy_read_only with Windows benchmark validation
- [ ] **Phase 7: Consistency Sweep** - Replace once_cell::sync::Lazy with std::sync::LazyLock across all crates
- [ ] **Phase 8: Workspace and Infrastructure** - Promote workspace deps, wire Proton path, resolve zerovec, commit Node types

## Phase Details

### Phase 1: Deprecated API Migration
**Goal**: All binding surfaces use current APIs with deprecation warnings emitted for end-users still calling legacy Python methods
**Depends on**: Nothing (first phase)
**Requirements**: DEBT-05, DEBT-06, DEBT-07, DEBT-10
**Success Criteria** (what must be TRUE):
  1. Python `parse_segments_parallel` wrapper internally delegates to `parse_all_sections_arc` and the `.pyi` contract is updated
  2. Python `generate_suspect_section` legacy method internally calls the two-method replacement (`generate_suspect_section_header` + `generate_suspect_found_footer`)
  3. All tests formerly using `#[allow(deprecated)]` on `is_outdated` now exercise `check_version_status()` instead
  4. `PyFormIDAnalyzerCore::new` emits a `DeprecationWarning` when receiving legacy `PyDict` format for `mods_single`
  5. Python and Node parity gates pass after all migrations
**Plans:** 2 plans
Plans:
- [x] 01-01-PLAN.md -- Replace is_outdated tests with expanded check_version_status coverage (DEBT-07)
- [x] 01-02-PLAN.md -- Migrate Python binding deprecated API callers and add deprecation warnings (DEBT-05, DEBT-06, DEBT-10)

### Phase 2: Dead Code Removal
**Goal**: No dead code remains in the workspace and no legacy fallback paths exist in production code
**Depends on**: Phase 1
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04, DEBT-08, DEBT-09, TEST-02
**Success Criteria** (what must be TRUE):
  1. `SEGMENT_BOUNDARIES`, `YamlFormatConfig`, `PluginAnalyzer.case_cache`, and `PyGpuDetector.inner` are deleted from source with no `#[allow(dead_code)]` annotations remaining
  2. `parse_segments`, `parse_segments_parallel`, and `is_outdated` methods are deleted from core crates with no `#[allow(deprecated)]` guards remaining in the workspace
  3. `scan_all_settings_legacy_bucketed` fallback path is removed and an assertion test confirms production configs never hit it
  4. `PyGpuDetector` is converted to a stateless Python class
  5. `cargo build --workspace` and all parity gates pass cleanly
**Plans:** 3 plans
Plans:
- [x] 02-01-PLAN.md -- Migrate deprecated shim tests and delete deprecated methods/dead code from parser.rs and version.rs (DEBT-01, DEBT-08)
- [x] 02-02-PLAN.md -- Delete YamlFormatConfig, remove PluginAnalyzer.case_cache, convert PyGpuDetector to stateless (DEBT-02, DEBT-03, DEBT-04)
- [x] 02-03-PLAN.md -- Add legacy fallback assertion test, then remove scan_all_settings_legacy_bucketed (DEBT-09, TEST-02)

### Phase 3: FCX State Hardening
**Goal**: FCX global state resets reliably under contention and all binding surfaces can reset state and inspect issues between scan sessions
**Depends on**: Nothing (independent workstream, but benefits from Phase 1/2 reducing noise)
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, CONS-02, TEST-01, TEST-04
**Success Criteria** (what must be TRUE):
  1. `reset_global_state()` uses blocking `lock()` instead of `try_lock()` and returns `Result<(), FcxResetError>` distinguishing success, unnecessary, and failure
  2. C++ bridge exposes `fcx_reset_global_state()` in the CXX extern block and it is callable before each scan session
  3. Node bindings expose `resetFcxGlobalState()` and `getFcxConfigIssues()` NAPI functions
  4. A test demonstrates FCX reset succeeds even when another thread holds the mutex (contention scenario)
  5. A test demonstrates Node binding FCX state does not carry over between sequential scan calls in a single process
**Plans**: TBD

### Phase 4: Bounded Cache Replacement
**Goal**: All global caches have bounded memory with LRU eviction and expose consistent observability through CacheStats
**Depends on**: Nothing (independent workstream)
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CONS-03
**Success Criteria** (what must be TRUE):
  1. `YAML_CACHE` uses `quick_cache::sync::Cache` with capacity 128 instead of unbounded `DashMap`
  2. `SETTINGS_CACHE` uses `quick_cache::sync::Cache` with capacity 64 instead of unbounded `DashMap`
  3. `HASH_CACHE` uses `quick_cache::sync::Cache` with capacity 1024 instead of unbounded `DashMap`
  4. All three caches expose a consistent `CacheStats` struct with hits, misses, hit_rate, size, and capacity fields
  5. Existing tests pass with bounded caches (clear/reset APIs preserved for test isolation)
**Plans**: TBD

### Phase 5: Pattern Caching and Performance
**Goal**: Hot-path regex compilation and LogParser allocation happen once, not per-call, with criterion benchmarks proving the improvement
**Depends on**: Nothing (independent workstream)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, CONS-04
**Success Criteria** (what must be TRUE):
  1. `detect_mods_single`, `detect_mods_double`, and `detect_mods_batch` cache compiled regex patterns keyed by mod list content hash
  2. `detect_mods_important` uses `str::contains` or AhoCorasick with `LeftmostLongest` instead of per-entry `Regex::new`, producing identical detection results to the prior implementation
  3. C++ bridge `detect_crash_pattern` uses a module-level `LazyLock<LogParser>` instead of per-call `LogParser::new(None)`
  4. Static regex patterns in `mod_detector` use `LazyLock` with `Regex::new().unwrap()` to move compilation failure to startup
  5. Criterion benchmarks exist for `detect_mods_important`, `detect_mods_single`/`batch`, `detect_crash_pattern`, and show measurable improvement over baseline
**Plans**: TBD

### Phase 6: mmap TOCTOU Safety
**Goal**: Memory-mapped file reads are safe against time-of-check-to-time-of-use races on Windows
**Depends on**: Nothing (independent)
**Requirements**: SAFE-05
**Success Criteria** (what must be TRUE):
  1. `read_file_mmap` uses `MmapOptions::map_copy_read_only()` instead of `Mmap::map()`
  2. A criterion benchmark compares throughput of `map()`, `map_copy()`, and `map_copy_read_only()` on representative file sizes to confirm acceptable performance
**Plans**: TBD

### Phase 7: Consistency Sweep
**Goal**: The codebase uses only `std::sync::LazyLock` for lazy statics, eliminating the `once_cell` dependency where it is no longer needed
**Depends on**: Phase 4, Phase 5 (both introduce new LazyLock usage; sweep after to catch all remaining sites)
**Requirements**: CONS-01
**Success Criteria** (what must be TRUE):
  1. No crate in the workspace imports `once_cell::sync::Lazy` -- all replaced with `std::sync::LazyLock`
  2. `once_cell` is removed from `[workspace.dependencies]` if no other `once_cell` APIs (e.g., `OnceCell`) are still in use
**Plans**: TBD

### Phase 8: Workspace and Infrastructure
**Goal**: Workspace dependency management is clean, Linux Proton path discovery works end-to-end, and Node type definitions are committed with CI freshness checks
**Depends on**: Nothing (independent housekeeping, but logically last)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, TEST-03
**Success Criteria** (what must be TRUE):
  1. `winreg` and `phf` are declared in `[workspace.dependencies]` with crate-level `workspace = true` references and `winreg` gated on `cfg(windows)`
  2. `construct_proton_docs_path` is wired into the Linux docs-path discovery workflow and an integration test using a mock Proton prefix structure passes
  3. The `zerovec` workaround in `classic-shared-core` is either removed (if Slint 1.15+ resolved it) or documented with a tracking comment
  4. Node `index.d.ts` is committed as a snapshot with a CI freshness check that fails if the generated output differs from the committed version
**Plans**: TBD

## Progress

**Execution Order:**
Phases 1 and 2 are sequential. Phases 3-6 and 8 can run in parallel after Phase 2. Phase 7 follows Phases 4 and 5.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Deprecated API Migration | 1/2 | In Progress | - |
| 2. Dead Code Removal | 0/3 | Not started | - |
| 3. FCX State Hardening | 0/TBD | Not started | - |
| 4. Bounded Cache Replacement | 0/TBD | Not started | - |
| 5. Pattern Caching and Performance | 0/TBD | Not started | - |
| 6. mmap TOCTOU Safety | 0/TBD | Not started | - |
| 7. Consistency Sweep | 0/TBD | Not started | - |
| 8. Workspace and Infrastructure | 0/TBD | Not started | - |
