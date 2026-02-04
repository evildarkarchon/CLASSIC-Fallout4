# Roadmap: CLASSIC

## Milestones

- SHIPPED **v1.0 Codebase Cleanup** — Phases 1-5 (shipped 2026-02-02)
- SHIPPED **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04)
- PLANNING **v8.3.0** — Performance & Polish (not yet started)

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

### v8.3.0 (Planned)

*Not yet started. Use `/gsd:new-milestone` to begin planning.*

**Potential focus areas:**
- Performance benchmarking (PERF-01 to PERF-03)
- TUI integration with Rust orchestrator (EXT-01)
- Additional INI/settings validators (EXT-02)
- Plugin load order analysis (EXT-03)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | 14/14 | Complete | 2026-02-02 |
| 6-11 | v8.2.0-part2 | 14/14 | Complete | 2026-02-04 |

**Overall:** 2 milestones shipped, 28 plans completed
