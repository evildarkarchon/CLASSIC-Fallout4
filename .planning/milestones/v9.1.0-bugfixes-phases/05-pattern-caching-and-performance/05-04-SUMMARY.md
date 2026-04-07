---
phase: 05-pattern-caching-and-performance
plan: 04
subsystem: testing
tags: [criterion, benchmarks, aho-corasick, quick-cache, performance]
requires:
  - phase: 05-01
    provides: cached single/double/batch matcher hot paths
  - phase: 05-02
    provides: important-mod Aho-Corasick path with legacy parity coverage
  - phase: 05-03
    provides: cached bridge crash-pattern parser behavior
provides:
  - Phase 5 Criterion groups for cached regex paths, important-mod matching, and bridge-style crash-pattern parsing
  - Local save/compare baseline workflow for scanlog_benchmarks contributors
affects: [performance-proof, perf-regression-triage]
tech-stack:
  added: []
  patterns: [existing Criterion harness extension, Rust bridge-replica benchmark helper, local-only baseline save/compare workflow]
key-files:
  created: [.planning/phases/05-pattern-caching-and-performance/05-04-SUMMARY.md]
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs
    - performance_baselines/README.md
key-decisions:
  - "Kept Phase 5 performance proof in the existing scanlog Criterion harness and mirrored bridge crash-pattern behavior with a Rust helper instead of an FFI benchmark."
  - "Primed cached single and batch matchers before timed loops and used Criterion iter_batched to avoid timing benchmark input setup."
  - "Scoped the legacy important-mod regex helper to tests after bench verification exposed a dead-code lint failure in non-test builds."
patterns-established:
  - "Criterion hotspot benches should keep parser or matcher setup outside the timed loop unless setup cost is the target measurement."
  - "Bridge-facing perf regressions can be measured in core benches with a Rust-side behavioral replica when the bridge logic stays adapter-only."
requirements-completed: [PERF-04]
duration: 12min
completed: 2026-04-06
---

# Phase 05 Plan 04: Benchmark Proof Summary

**Criterion proof coverage for cached regex matchers, important-mod Aho-Corasick scans, and bridge-style crash-pattern parser reuse with a documented local baseline workflow**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-06T00:38:00-07:00
- **Completed:** 2026-04-06T00:50:34.8966349-07:00
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended the existing `scanlog_benchmarks` Criterion harness with dedicated Phase 5 groups for cached regex paths, important-mod detection, and bridge-style crash-pattern parsing.
- Added a Rust-side bridge replica helper so parser reuse can be measured inside the core harness without turning the benchmark into an FFI test.
- Documented the exact local `--save-baseline` and `--baseline` workflow, the local-only raw baseline policy, and the 5% minimum win threshold guidance for future verification.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend scanlog_benchmarks with Phase 5 hotspot groups** - `b9c8bd9d` (feat)
2. **Task 2: Document the local baseline save/compare flow for Phase 5 proof** - `bdc6175e` (docs)

## Files Created/Modified

- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - Added Phase 5 Criterion groups, synthetic fixture builders, fixture plugin extraction, and the bridge-style crash-pattern replica helper.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - Scoped the legacy important-mod regex helper to tests so bench verification passes without dead-code lint failures.
- `performance_baselines/README.md` - Added explicit Phase 5 save/compare commands, local-only baseline policy reminders, and the measurable-improvement guidance.

## Decisions Made

- Kept all new performance proof in the existing `classic-scanlog-core` harness to follow the locked Phase 5 benchmark-home decision.
- Used both real fixture input and compact synthetic plugin/XSE surfaces so the benches cover realistic behavior and isolated hotspot cost.
- Treated the dead-code failure on the legacy helper as a blocking verification issue and fixed it inline rather than weakening lint settings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Scoped the legacy important-mod regex helper to tests**
- **Found during:** Task 1 (Extend scanlog_benchmarks with Phase 5 hotspot groups)
- **Issue:** `cargo bench -- --test` failed because `detect_mods_important_legacy` is only used by parity tests, so bench builds hit the repo's dead-code lint.
- **Fix:** Added `#[cfg(test)]` to keep the legacy helper available for parity coverage while removing it from non-test bench builds.
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
- **Verification:** `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test`
- **Committed in:** `b9c8bd9d` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was required to let the planned benchmark verification pass and did not expand scope beyond the touched Phase 5 hotspot file.

## Issues Encountered

- Bench verification initially failed on a dead-code lint in `mod_detector.rs`; fixing the helper visibility resolved it without changing runtime behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 now has repeatable benchmark coverage and documented local baseline commands for PERF-04 proof runs.
- Raw Criterion baseline directories remain local-only by default; future verification work can save and compare baselines without changing repo policy.

## Self-Check: PASSED

- FOUND: `.planning/phases/05-pattern-caching-and-performance/05-04-SUMMARY.md`
- FOUND: `b9c8bd9d`
- FOUND: `bdc6175e`

---
*Phase: 05-pattern-caching-and-performance*
*Completed: 2026-04-06*
