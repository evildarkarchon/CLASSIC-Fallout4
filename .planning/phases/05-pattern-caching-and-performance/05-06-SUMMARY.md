---
phase: 05-pattern-caching-and-performance
plan: 06
subsystem: testing
tags: [criterion, benchmarks, aho-corasick, regex, performance-proof]
requires:
  - phase: 05-04
    provides: phase5 benchmark groups and local baseline workflow
provides:
  - Committed Phase 5 benchmark proof artifact with measured hotspot deltas
  - Requirement wording that keeps mmap throughput ownership with SAFE-05 and Phase 6
affects: [phase-05-verification, phase-06-safe-05, perf-regression-triage]
tech-stack:
  added: []
  patterns: [focused phase5_ benchmark save-compare workflow, paired before-after benchmark variants, benchmark-proof artifact tracking]
key-files:
  created:
    - .planning/phases/05-pattern-caching-and-performance/05-06-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md
    - ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs
    - performance_baselines/README.md
key-decisions:
  - "Focused the save/compare workflow on the phase5_ benchmark groups so proof runs stay bounded to the locked hotspots."
  - "Added paired before/after benchmark variants in the existing harness because same-revision Criterion baseline comparisons alone cannot prove hotspot deltas."
  - "Moved mmap throughput ownership out of PERF-04 and into SAFE-05 / Phase 6 to match the roadmap and actual harness scope."
patterns-established:
  - "Benchmark proof artifacts should summarize measured hotspot deltas while leaving raw Criterion directories local-only."
  - "When a save/compare run uses the same checked-out implementation, pair the benchmark group with explicit before/after variants instead of claiming the Criterion change output proves implementation wins."
requirements-completed: [PERF-04]
duration: 43min
completed: 2026-04-06
---

# Phase 05 Plan 06: Benchmark Proof Alignment Summary

**Shareable Phase 5 benchmark proof with paired hotspot deltas, focused `phase5_` reproduction commands, and mmap ownership clarified for Phase 6**

## Performance

- **Duration:** 43 min
- **Started:** 2026-04-06T01:17:00-07:00
- **Completed:** 2026-04-06T02:00:14.1884224-07:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a committed `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` artifact with exact commands, benchmark groups, and measured deltas for the locked Phase 5 hotspots.
- Tightened the benchmark workflow to `phase5_`-only runs and extended the existing harness with paired before/after variants so the proof shows real hotspot deltas instead of same-revision noise.
- Updated `PERF-04` wording so Phase 5 owns only the benchmarked hotspot groups while mmap throughput proof is explicitly deferred to `SAFE-05` / Phase 6.

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate and commit a shareable Phase 5 benchmark proof report** - `fe1e4a26` (docs)
2. **Task 2: Align PERF-04 wording with the roadmap's Phase 6 mmap ownership** - `f7748e1f` (docs)

## Files Created/Modified

- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - Added paired `uncached/cached`, `legacy_regex/current`, and `parser_per_call/cached_parser` proof variants within the existing Phase 5 benchmark groups.
- `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` - Recorded commands, benchmark groups, measured deltas, threshold outcomes, and the mmap ownership clarification.
- `performance_baselines/README.md` - Updated contributors to run focused `phase5_` save/compare commands and pointed them to the committed proof artifact.
- `.planning/REQUIREMENTS.md` - Narrowed `PERF-04` to the actual Phase 5 hotspot proof and assigned mmap throughput work to `SAFE-05` / Phase 6.

## Decisions Made

- Kept all proof work in the existing `scanlog_benchmarks` harness to preserve the locked Phase 5 benchmark-home decision.
- Used benchmark-side paired variants for before/after comparisons because a save/compare run against the same checked-out revision only validates reproducibility, not implementation wins.
- Recorded the important-mod regression honestly in the proof artifact instead of inventing a positive claim that the measurements did not support.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added paired benchmark variants so the proof could show real before/after deltas**
- **Found during:** Task 1 (Generate and commit a shareable Phase 5 benchmark proof report)
- **Issue:** The existing Phase 5 groups only benchmarked the optimized code paths, so a same-revision Criterion save/compare run could not produce meaningful before/after evidence for the hotspot changes.
- **Fix:** Extended the existing harness with benchmark-local uncached, legacy-regex, and parser-per-call variants while keeping all proof in `scanlog_benchmarks` and raw Criterion output local-only.
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs`, `performance_baselines/README.md`, `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md`
- **Verification:** `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_ -- --save-baseline phase5-before`; `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_ -- --baseline phase5-before`; `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test`
- **Committed in:** `fe1e4a26` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The deviation stayed inside the locked Phase 5 benchmark harness and was necessary to produce honest, reproducible proof data.

## Issues Encountered

- A plain `--save-baseline` / `--baseline` run on the same checked-out revision only produced noise-level Criterion comparisons, so the proof needed explicit before/after variants inside the Phase 5 groups.
- The important-mod hotspot did not clear the repo's 5% win threshold; the proof artifact records that regression and explains why the structural change still shipped.

## Deferred Issues

- `phase5_detect_mods_important` remains slower than the benchmark-local legacy regex replica for both the synthetic and fixture surfaces in this environment. Future performance work should optimize or revisit that path if Phase 5's structural cleanup is expected to become a net win.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 now has a committed benchmark-proof artifact that future verification can inspect without raw Criterion directories.
- Phase 6 can own mmap throughput work cleanly under `SAFE-05` without conflicting milestone text.

## Self-Check: PASSED

- FOUND: `.planning/phases/05-pattern-caching-and-performance/05-06-SUMMARY.md`
- FOUND: `fe1e4a26`
- FOUND: `f7748e1f`

---
*Phase: 05-pattern-caching-and-performance*
*Completed: 2026-04-06*
