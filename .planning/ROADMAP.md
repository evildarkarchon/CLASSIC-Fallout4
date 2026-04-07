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
- [ ] **Phase 4: Bounded Cache Replacement** - Replace three unbounded DashMap caches with bounded quick_cache eviction, expose CacheStats
- [ ] **Phase 5: Pattern Caching and Performance** - Cache compiled regex/AhoCorasick in mod detector hot paths, cache LogParser in bridge, add benchmarks
- [ ] **Phase 6: mmap TOCTOU Safety** - Switch mmap to map_copy_read_only with Windows benchmark validation
- [ ] **Phase 7: Consistency Sweep** - Replace once_cell::sync::Lazy with std::sync::LazyLock across all crates
- [ ] **Phase 8: Workspace and Infrastructure** - Promote workspace deps, wire Proton path, resolve zerovec, commit Node types
- [ ] **Phase 9: Deprecated API Verification Closure** - Re-verify Phase 1 now that requirement bookkeeping is synchronized
- [ ] **Phase 10: Pattern Caching Verification Backfill** - Backfill missing Phase 5 verification coverage for orphaned requirements
- [ ] **Phase 11: Workspace/Infra Verification Completion** - Complete missing Phase 8 verification coverage and restore audit traceability

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
**Plans:** 3 plans
Plans:
- [x] 03-01-PLAN.md -- Harden the core FCX reset contract and add contention coverage (SAFE-01, CONS-02, TEST-01)
- [x] 03-02-PLAN.md -- Expose C++ FCX reset and auto-reset every C++ scan session (SAFE-02)
- [x] 03-03-PLAN.md -- Add Node FCX reset/issues APIs, auto-reset wiring, and carryover coverage (SAFE-03, SAFE-04, TEST-04)

### Phase 4: Bounded Cache Replacement
**Goal**: All global caches have bounded memory with `quick_cache` eviction semantics and expose consistent observability through CacheStats
**Depends on**: Nothing (independent workstream)
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CONS-03
**Success Criteria** (what must be TRUE):
  1. `YAML_CACHE` uses `quick_cache::sync::Cache` with capacity 128 instead of unbounded `DashMap`
  2. `SETTINGS_CACHE` uses `quick_cache::sync::Cache` with capacity 64 instead of unbounded `DashMap`
  3. `HASH_CACHE` uses `quick_cache::sync::Cache` with capacity 1024 instead of unbounded `DashMap`
  4. All three caches expose a consistent `CacheStats` struct with hits, misses, hit_rate, size, and capacity fields
  5. Existing tests pass with bounded caches (clear/reset APIs preserved for test isolation)
**Plans**: 7 plans
Plans:
- [x] 04-01-PLAN.md -- Replace YAML_CACHE with a 128-entry bounded quick_cache and canonical CacheStats
- [x] 04-02-PLAN.md -- Replace SETTINGS_CACHE with a 64-entry bounded quick_cache and canonical CacheStats
- [x] 04-03-PLAN.md -- Replace HASH_CACHE with a 1024-entry bounded quick_cache and add public hash cache stats
- [x] 04-04-PLAN.md -- Align Node YAML/settings/hash cache stats, tests, committed TypeScript contract, and Node parity artifacts to the canonical contract
- [x] 04-05-PLAN.md -- Align Python YAML/settings/hash cache stats, stubs, runtime smoke coverage, and Python parity artifacts to the canonical contract
- [x] 04-06-PLAN.md -- Add C++ YAML/settings/hash cache stats entrypoints and document the new parity surface

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
**Plans**: 6 plans

Plans:
- [x] 05-01-PLAN.md -- Add bounded matcher caches for `detect_mods_single`/`double`/`batch` and move touched static regexes to `LazyLock` (PERF-01, CONS-04)
- [x] 05-02-PLAN.md -- Replace `detect_mods_important` regex-per-entry matching with `Aho-Corasick` guarded by fixture-backed parity coverage (PERF-02)
- [x] 05-03-PLAN.md -- Cache the C++ bridge `detect_crash_pattern` parser with a module-level `LazyLock<LogParser>` and add positive bridge coverage (PERF-03)
- [x] 05-04-PLAN.md -- Extend `scanlog_benchmarks.rs` with Phase 5 hotspot proof and document the local Criterion baseline workflow (PERF-04)
- [x] 05-05-PLAN.md -- Stabilize the `detect_mods_double` matcher-cache reuse proof so grouped detector test runs pass deterministically (PERF-01 gap closure)
- [x] 05-06-PLAN.md -- Commit a reproducible Phase 5 benchmark proof artifact and align PERF-04 wording with Phase 6 mmap ownership (PERF-04 gap closure)
- [x] 05-07-PLAN.md -- Investigate and eliminate the residual `detect_mods_important` benchmark regression without relaxing parity or benchmark-proof requirements (PERF-02, PERF-04)

### Phase 6: mmap TOCTOU Safety
**Goal**: Memory-mapped file reads are safe against time-of-check-to-time-of-use races on Windows
**Depends on**: Nothing (independent)
**Requirements**: SAFE-05
**Success Criteria** (what must be TRUE):
  1. `read_file_mmap` uses `MmapOptions::map_copy_read_only()` instead of `Mmap::map()`
  2. A criterion benchmark compares throughput of `map()`, `map_copy()`, and `map_copy_read_only()` on representative file sizes to confirm acceptable performance
**Plans**: 3 plans
Plans:
- [x] 06-01-PLAN.md -- Swap `read_file_mmap()` to `map_copy_read_only()` and align active docs to the locked Phase 6 contract
- [x] 06-02-PLAN.md -- Add the Phase 6 mmap benchmark group and commit the markdown throughput proof workflow
- [x] 06-03-PLAN.md -- Scope benchmark-only unsafe mmap helpers so the Phase 6 crate lint gate passes (SAFE-05 gap closure)

### Phase 7: Consistency Sweep
**Goal**: The codebase uses only `std::sync::LazyLock` for lazy statics, eliminating the `once_cell` dependency where it is no longer needed
**Depends on**: Phase 4, Phase 5 (both introduce new LazyLock usage; sweep after to catch all remaining sites)
**Requirements**: CONS-01
**Success Criteria** (what must be TRUE):
  1. No crate in the workspace imports `once_cell::sync::Lazy` -- all replaced with `std::sync::LazyLock`
  2. `once_cell` is removed from `[workspace.dependencies]` if no other `once_cell` APIs (e.g., `OnceCell`) are still in use
**Plans**: 2 plans
Plans:
- [x] 07-01-PLAN.md -- Migrate `classic-scanlog-core` from direct `once_cell` usage to `std::sync::{LazyLock, OnceLock}` and drop its direct manifest dependency
- [x] 07-02-PLAN.md -- Finish the registry/perf sweep, remove remaining owned direct `once_cell` manifests, and align touched `docs/api` pages

### Phase 8: Workspace and Infrastructure
**Goal**: Workspace dependency management is clean, Linux Proton path discovery works end-to-end, and Node type definitions are committed with CI freshness checks
**Depends on**: Nothing (independent housekeeping, but logically last)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, TEST-03
**Success Criteria** (what must be TRUE):
  1. `winreg` and `phf` are declared in `[workspace.dependencies]` with crate-level `workspace = true` references and `winreg` gated on `cfg(windows)`
  2. `construct_proton_docs_path` is wired into the Linux docs-path discovery workflow and an integration test using a mock Proton prefix structure passes
  3. The `zerovec` workaround in `classic-shared-core` is either removed (if Slint 1.15+ resolved it) or documented with a tracking comment
   4. Node `index.d.ts` is committed as a snapshot with a CI freshness check that fails if the generated output differs from the committed version
**Plans**: 08-01 workspace dependency promotion + `zerovec` removal proof; 08-02 Proton docs-path wiring + integration proof; 08-03 Node declaration contract + freshness workflow cleanup

### Phase 9: Deprecated API Verification Closure
**Goal**: Phase 1 audit blockers are cleared by re-verifying the deprecated API migration work against the current planning state and evidence
**Depends on**: Phase 1
**Requirements**: DEBT-05, DEBT-06, DEBT-07, DEBT-10
**Gap Closure**: Closes stale Phase 1 verification status from `v1.0-MILESTONE-AUDIT.md`
**Success Criteria** (what must be TRUE):
  1. `01-VERIFICATION.md` is updated from `gaps_found` to a status consistent with the current code and requirements state
  2. Phase 1 requirement coverage explicitly accounts for DEBT-05, DEBT-06, DEBT-07, and DEBT-10 without relying on stale documentation gaps
  3. Any remaining parity or runtime proof needed for Phase 1 verification is captured in the refreshed verification artifact
**Plans**: 1 plan

Plans:
- [x] 09-01-PLAN.md -- Refresh Phase 1 verification evidence, rerun parity/runtime proof, and reconcile Phase 9 requirement bookkeeping

### Phase 10: Pattern Caching Verification Backfill
**Goal**: Phase 5 verification artifacts fully cover all requirements claimed complete by the phase summaries
**Depends on**: Phase 5
**Requirements**: PERF-03, CONS-04
**Gap Closure**: Closes orphaned Phase 5 requirements from `v1.0-MILESTONE-AUDIT.md`
**Success Criteria** (what must be TRUE):
  1. Phase 5 verification coverage explicitly includes PERF-03 for cached C++ `detect_crash_pattern`
  2. Phase 5 verification coverage explicitly includes CONS-04 for static `LazyLock` regex compilation behavior
  3. The final Phase 5 verification story is internally consistent for the requirements still assigned to the phase
**Plans**: TBD

### Phase 11: Workspace/Infra Verification Completion
**Goal**: Phase 8 has complete verification coverage for all workspace and infrastructure requirements claimed by the milestone
**Depends on**: Phase 8
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, TEST-03
**Gap Closure**: Closes missing Phase 8 verification coverage from `v1.0-MILESTONE-AUDIT.md`
**Success Criteria** (what must be TRUE):
  1. `08-VERIFICATION.md` exists and covers all six assigned requirements with evidence
  2. The verification artifact accounts for workspace dependency ownership, Proton docs-path wiring, Node declaration freshness, and the Proton integration test
  3. Milestone audit traceability can map all six Phase 8 requirements to a concrete verification report
**Plans**: TBD

## Progress

**Execution Order:**
Phases 1 and 2 are sequential. Phases 3-6 and 8 can run in parallel after Phase 2. Phase 7 follows Phases 4 and 5.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Deprecated API Migration | 2/2 | Complete | 2026-04-06 |
| 2. Dead Code Removal | 3/3 | Complete | 2026-04-06 |
| 3. FCX State Hardening | 3/3 | Complete | 2026-04-06 |
| 4. Bounded Cache Replacement | 6/6 | Complete | 2026-04-06 |
| 5. Pattern Caching and Performance | 7/7 | Complete | 2026-04-06 |
| 6. mmap TOCTOU Safety | 3/3 | Complete | 2026-04-06 |
| 7. Consistency Sweep | 2/2 | Complete | 2026-04-06 |
| 8. Workspace and Infrastructure | 3/3 | Complete | 2026-04-06 |
| 9. Deprecated API Verification Closure | 0/TBD | Planned | - |
| 10. Pattern Caching Verification Backfill | 0/TBD | Planned | - |
| 11. Workspace/Infra Verification Completion | 0/TBD | Planned | - |
| 5. Pattern Caching and Performance | 0/4 | Planned | - |
| 6. mmap TOCTOU Safety | 0/TBD | Not started | - |
| 7. Consistency Sweep | 0/2 | Planned | - |
| 8. Workspace and Infrastructure | 0/3 | Planned | - |
