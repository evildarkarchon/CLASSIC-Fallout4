# Roadmap: CLASSIC

## Milestones

- SHIPPED **v1.0 Codebase Cleanup** — Phases 1-5 (shipped 2026-02-02)
- SHIPPED **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04)
- ACTIVE **v8.3.0 Performance & Polish** — Phases 12-17 (in progress)

## Phases

<details>
<summary>v1.0 Codebase Cleanup (Phases 1-5) — SHIPPED 2026-02-02</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for full details.

- [x] Phase 1: Foundation Cleanup (4/4 plans)
- [x] Phase 2: Integration Layer Simplification (2/2 plans)
- [x] Phase 3: Wrapper Thinning (2/2 plans)
- [x] Phase 4: Interface Consolidation (3/3 plans)
- [x] Phase 5: Fallback Pruning (3/3 plans)

**Accomplishments:** Removed 11,993 net lines, 8 Python fallbacks eliminated, factory.py consolidated with 13 Protocol types.

</details>

<details>
<summary>v8.2.0-part2 Rust Migration (Phases 6-11) — SHIPPED 2026-02-04</summary>

See `.planning/milestones/v8.2.0-part2-ROADMAP.md` for full details.

- [x] Phase 6: Foundation & Settings (2/2 plans)
- [x] Phase 7: Game Detection (2/2 plans)
- [x] Phase 8: Report Generation (2/2 plans)
- [x] Phase 9: Orchestration Migration (4/4 plans)
- [x] Phase 10: Parity Validation (2/2 plans)
- [x] Phase 11: Integration & Cleanup (2/2 plans)

**Accomplishments:** Python is now UI-only shell. All business logic in Rust. 7 Python analyzers deleted, 19 Rust modules bundled.

</details>

### v8.3.0 Performance & Polish (In Progress)

**Milestone Goal:** Establish performance baselines, optimize hot paths based on profiling data, and fix pre-existing bugs. Data-driven optimization, not premature.

- [x] **Phase 12: GIL Release Audit** - Add py.allow_threads() to Rust operations, measure FFI overhead
- [x] **Phase 13: Benchmark Infrastructure** - Establish Criterion benchmarks with statistical output and baselines
- [x] **Phase 14: Hot Path Profiling & Cache Instrumentation** - Profile hot paths, instrument DashMap caches
- [ ] **Phase 15: Bug Fixes & Test Stabilization** - Fix test_clear_cache and classic_settings() path resolution
- [ ] **Phase 16: Hot Path Optimization (Data-Driven)** - Optimize based on profiling data from Phase 14
- [ ] **Phase 17: CI Regression Detection** - Automated performance regression detection in CI

## Phase Details

### Phase 12: GIL Release Audit
**Goal**: Rust operations release Python GIL correctly; FFI overhead measured
**Depends on**: Phase 11 (completed)
**Requirements**: GIL-01, GIL-02
**Success Criteria** (what must be TRUE):
  1. All Rust operations taking >1ms release Python GIL via py.allow_threads()
  2. FFI type conversion overhead is measured separately from Rust compute time
**Plans**: 1 plan

Plans:
- [x] 12-01-PLAN.md - Comprehensive FFI audit, py.detach() implementation, Criterion benchmarks, GIL verification tests

### Phase 13: Benchmark Infrastructure
**Goal**: Criterion benchmark infrastructure established with statistical output and historical baselines
**Depends on**: Phase 12 (GIL release required for accurate benchmarks)
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04, BENCH-06
**Success Criteria** (what must be TRUE):
  1. Running `cargo bench` in release mode produces statistical output (min/mean/median/stddev/p95/p99)
  2. Benchmark results export to JSON and are stored as historical baselines
  3. Benchmarks run multiple iterations with configurable warmup
  4. Historical baselines stored for comparison across commits
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — Criterion workspace configuration, quick/thorough modes, benchmark runner script
- [x] 13-02-PLAN.md — Core crate benchmarks (yaml-core, scanlog-core, file-io-core) with realistic fixtures
- [x] 13-03-PLAN.md — Baseline management scripts (percentile extraction, cleanup, comparison)

### Phase 14: Hot Path Profiling & Cache Instrumentation
**Goal**: Hot paths identified via flamegraphs; cache behavior observable
**Depends on**: Phase 13
**Requirements**: PROF-01, PROF-02, PROF-03, GIL-03
**Success Criteria** (what must be TRUE):
  1. Developer can generate flamegraph for any Rust hot path
  2. py-spy captures combined Python+Rust stack traces
  3. Memory allocation profiling available via dhat for Rust code
  4. DashMap cache hit/miss rates are logged and reportable
**Plans**: 3 plans

Plans:
- [x] 14-01-PLAN.md — Flamegraph and py-spy profiling setup (cargo aliases, PowerShell scripts)
- [x] 14-02-PLAN.md — dhat memory profiling and DashMap cache instrumentation
- [x] 14-03-PLAN.md — Gap closure: Export cache_stats() from classic-settings-py to Python

### Phase 15: Bug Fixes & Test Stabilization
**Goal**: Pre-existing bugs fixed, test suite stable
**Depends on**: Phase 13 (can run in parallel with Phase 14)
**Requirements**: BUG-01, BUG-02
**Success Criteria** (what must be TRUE):
  1. test_clear_cache passes reliably in parallel test runs (no test pollution)
  2. classic_settings() returns correct paths regardless of current working directory
  3. All tests in tests/rust_integration/ pass consistently
**Plans**: 2 plans

Plans:
- [x] 15-01-PLAN.md — Fix test_clear_cache parallel test pollution (add #[serial], regression tests)
- [ ] 15-02-PLAN.md — Fix classic_settings() path resolution (ResourceLoader-based paths)

### Phase 16: Hot Path Optimization (Data-Driven)
**Goal**: Hot paths optimized based on profiling data; measurable performance gains
**Depends on**: Phase 14 (profiling data required)
**Requirements**: None (optimization work informed by profiling, not requirement-driven)
**Success Criteria** (what must be TRUE):
  1. Top 3 hot paths identified in Phase 14 show measurable improvement
  2. Benchmark results compared against Phase 13 baselines show improvement
  3. No performance regressions in non-optimized paths
**Plans**: TBD (defined after Phase 14 profiling completes)

Plans:
- [ ] 16-01: Optimize based on profiling findings (scope TBD after Phase 14)

### Phase 17: CI Regression Detection
**Goal**: CI automatically detects performance regressions
**Depends on**: Phase 13 (baselines), Phase 16 (optimizations validated)
**Requirements**: BENCH-05
**Success Criteria** (what must be TRUE):
  1. CI pipeline runs benchmarks on PRs
  2. Performance regression >10% fails the build with clear diagnostic
  3. Historical baselines are automatically updated on main branch merges
**Plans**: TBD

Plans:
- [ ] 17-01: CI benchmark integration and regression detection

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | 14/14 | Complete | 2026-02-02 |
| 6-11 | v8.2.0-part2 | 14/14 | Complete | 2026-02-04 |
| 12. GIL Release Audit | v8.3.0 | 1/1 | Complete | 2026-02-04 |
| 13. Benchmark Infrastructure | v8.3.0 | 3/3 | Complete | 2026-02-05 |
| 14. Hot Path Profiling | v8.3.0 | 3/3 | Complete | 2026-02-05 |
| 15. Bug Fixes | v8.3.0 | 1/2 | In progress | - |
| 16. Hot Path Optimization | v8.3.0 | 0/1 | Not started | - |
| 17. CI Regression Detection | v8.3.0 | 0/1 | Not started | - |

**Overall:** 2 milestones shipped, 36 plans completed, 4 plans remaining for v8.3.0
