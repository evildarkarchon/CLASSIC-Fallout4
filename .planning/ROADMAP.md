# Roadmap: CLASSIC

## Milestones

- ✅ **v1.0 Codebase Cleanup** — Phases 1-5 (shipped 2026-02-02)
- ✅ **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04)
- ✅ **v8.3.0 Performance & Polish** — Phases 12-18 (shipped 2026-02-05)

## Phases

<details>
<summary>✅ v1.0 Codebase Cleanup (Phases 1-5) — SHIPPED 2026-02-02</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for full details.

- [x] Phase 1: Foundation Cleanup (4/4 plans)
- [x] Phase 2: Integration Layer Simplification (2/2 plans)
- [x] Phase 3: Wrapper Thinning (2/2 plans)
- [x] Phase 4: Interface Consolidation (3/3 plans)
- [x] Phase 5: Fallback Pruning (3/3 plans)

**Accomplishments:** Removed 11,993 net lines, 8 Python fallbacks eliminated, factory.py consolidated with 13 Protocol types.

</details>

<details>
<summary>✅ v8.2.0-part2 Rust Migration (Phases 6-11) — SHIPPED 2026-02-04</summary>

See `.planning/milestones/v8.2.0-part2-ROADMAP.md` for full details.

- [x] Phase 6: Foundation & Settings (2/2 plans)
- [x] Phase 7: Game Detection (2/2 plans)
- [x] Phase 8: Report Generation (2/2 plans)
- [x] Phase 9: Orchestration Migration (4/4 plans)
- [x] Phase 10: Parity Validation (2/2 plans)
- [x] Phase 11: Integration & Cleanup (2/2 plans)

**Accomplishments:** Python is now UI-only shell. All business logic in Rust. 7 Python analyzers deleted, 19 Rust modules bundled.

</details>

<details>
<summary>✅ v8.3.0 Performance & Polish (Phases 12-18) — SHIPPED 2026-02-05</summary>

See `.planning/milestones/v8.3.0-ROADMAP.md` for full details.

- [x] Phase 12: GIL Release Audit (1/1 plan)
- [x] Phase 13: Benchmark Infrastructure (3/3 plans)
- [x] Phase 14: Hot Path Profiling (3/3 plans)
- [x] Phase 15: Bug Fixes (2/2 plans)
- [x] Phase 16: Hot Path Optimization (2/2 plans)
- [x] Phase 17: CI Regression Detection (3/3 plans)
- [x] Phase 18: Tech Debt Cleanup (1/1 plan)

**Accomplishments:** 77+ Criterion benchmarks established, CI regression detection (10% threshold), GIL release audit (65 without_gil), profiling tooling (flamegraph/py-spy/dhat), O(1) membership optimization, both pre-existing bugs fixed.

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | 14/14 | Complete | 2026-02-02 |
| 6-11 | v8.2.0-part2 | 14/14 | Complete | 2026-02-04 |
| 12-18 | v8.3.0 | 15/15 | Complete | 2026-02-05 |

**Overall:** 3 milestones shipped, 43 plans completed
