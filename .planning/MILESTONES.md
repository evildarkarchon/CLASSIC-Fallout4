# Project Milestones: CLASSIC

## v8.3.0 Performance & Polish (Shipped: 2026-02-05)

**Delivered:** Established comprehensive performance infrastructure — Criterion benchmarks across all Rust crates, GIL release audit, profiling tooling, hot path optimization based on data, and CI-based regression detection.

**Phases completed:** 12-18 (15 plans total)

**Key accomplishments:**

- Comprehensive GIL release audit with 65 without_gil occurrences, enabling true Python thread parallelism for CPU-bound Rust operations (GIL-01, GIL-02)
- Criterion benchmark infrastructure with quick/thorough modes, statistical output, and PowerShell runner scripts (BENCH-01 to BENCH-06)
- Profiling tooling: Flamegraph, py-spy (Python+Rust combined stacks), dhat memory profiling, DashMap cache instrumentation (PROF-01 to PROF-03, GIL-03)
- Fixed test_clear_cache parallel pollution with #[serial] and classic_settings() path resolution bug (BUG-01, BUG-02)
- Data-driven optimization: Profiling revealed 86% time in Python threading (not Rust FFI at 0.3%); implemented O(1) membership via set-backed lists
- CI regression detection: GitHub Actions workflow with 10% threshold, PR comments, bypass labels, and branch protection documentation

**Stats:**

- 80 commits over 2 days (2026-02-04 → 2026-02-05)
- 111 files changed, +18,578 / -175 lines
- 7 phases, 15 plans, 14 requirements satisfied
- 77+ Criterion benchmarks across yaml-core, scanlog-core, file-io-core crates
- All tech debt from milestone audit addressed in Phase 18

**Git range:** `feat(12-01)` → `docs(18)`

**What's next:** New milestone — user-facing features, additional Rust acceleration, or maintenance work now that performance infrastructure is in place.

---

## v8.2.0-part2 Rust Migration (Shipped: 2026-02-04)

**Delivered:** Completed Rust migration — Python is now a thin UI shell while Rust owns all business logic (settings, game detection, report generation, orchestration, analysis).

**Phases completed:** 6-11 (14 plans total)

**Key accomplishments:**

- Migrated settings cache to Rust DashMap-based lock-free caching via classic_settings module (SETT-01 to SETT-05)
- Created golden file parity infrastructure with 16 crash logs captured (32 files) for Python-Rust comparison (VAL-01)
- Game detection fully delegated to Rust GamePathFinder with no Python fallback, GlobalRegistry integration (GAME-01 to GAME-04)
- Removed Python orchestrators (1,223 lines); all scanning via Rust OrchestratorCore with parallel processing (ORCH-01 to ORCH-05)
- Report generation through Rust ReportGenerator/ReportComposer for all markdown output (REPT-01 to REPT-04)
- Deleted 7 Python analyzer files; factory returns Rust components directly (INTG-01 to INTG-05)

**Stats:**

- 143 commits over 3 days (2026-02-02 → 2026-02-04)
- 88,594 lines Python, 65,277 lines Rust
- 6 phases, 14 plans, 23 requirements satisfied
- 3,849 tests passing with Rust as primary code path
- PyInstaller build verified with 19 Rust modules bundled

**Git range:** `feat(06-01)` → `feat(11-02)`

**What's next:** Performance benchmarking milestone (PERF-01 to PERF-03) or new features now that Rust foundation is complete.

---

## v1.0 Codebase Cleanup (Shipped: 2026-02-02)

**Delivered:** Eliminated all redundancies across the Python-Rust hybrid codebase — every piece of logic now lives in exactly one place with clear ownership boundaries, ready for progressive Rust migration.

**Phases completed:** 1-5 (14 plans total)

**Key accomplishments:**

- Removed deprecated code, established 71% coverage baseline, Vulture CI enforcement, and comprehensive singleton reset fixture covering 19+ globals
- Collapsed 3-layer factory/detector/status into single flat factory.py with 13 Protocol types and zero pyright errors
- Reduced file_io/parser/formid wrappers by 60-75% using consistent thin delegation pattern
- Eliminated all sync wrappers and dual-interface patterns; AsyncBridge.run_async() is sole GUI sync mechanism
- Removed all 8 Python fallback implementations and CLASSIC_DISABLE_RUST mechanism; factory raises RuntimeError on missing Rust
- Added validate_rust_modules() startup validation for 6 required Rust modules; PyInstaller build verified

**Stats:**

- 252 files changed across 70 commits
- Net -11,993 lines (10,374 added / 22,367 removed)
- 48,342 lines Python (ClassicLib/)
- 5 phases, 14 plans
- ~23 hours wall clock, ~2.8 hours execution time

**Git range:** `feat(01-02)` → `docs(05)`

**What's next:** Rust migration milestone — migrate remaining Python business logic to Rust -core crates, flatten integration layer, progressive UI migration.

---
