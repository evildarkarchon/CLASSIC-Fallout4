---
phase: 05-pattern-caching-and-performance
plan: 07
subsystem: performance
tags: [rust, aho-corasick, quick-cache, criterion, scanlog]
requires:
  - phase: 05-02
    provides: important-mod Aho-Corasick parity coverage and retained legacy comparator
  - phase: 05-06
    provides: committed benchmark-proof workflow and paired important-mod benchmark variants
provides:
  - cost-center benchmark slices for important-mod compile, haystack, uncached, and cached matcher work
  - bounded process-wide matcher reuse for detect_mods_important
  - refreshed proof showing synthetic and real-fixture important-mod paths beat the legacy comparator
affects: [PERF-02, PERF-04, classic-scanlog-core, phase-05-verification]
tech-stack:
  added: []
  patterns: [bounded Aho-Corasick matcher reuse, one-pass lowercase haystack construction, hotspot-specific benchmark slice proof]
key-files:
  created:
    - .planning/phases/05-pattern-caching-and-performance/05-07-SUMMARY.md
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs
    - .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md
key-decisions:
  - "Reused the Phase 4 bounded-cache pattern for important-mod matcher construction once the benchmark slices showed compile cost dominated the synthetic regression."
  - "Kept the legacy regex comparator in the benchmark harness and used paired benchmark variants, not Criterion same-revision change output, as the pass/fail proof source."
  - "Skipped plugin-name set construction unless an important-mod entry actually uses exclude_when, because the real-fixture slices showed haystack preparation dominated the remaining cost."
patterns-established:
  - "When an Aho-Corasick migration regresses, add compile-only, haystack-only, uncached, and cached-match slices before changing the production path."
  - "Important-mod detection should cache the matcher process-wide and build its lowercase haystack in one pass, while leaving exclusion semantics intact."
requirements-completed: [PERF-02, PERF-04]
duration: 17min
completed: 2026-04-06
---

# Phase 05 Plan 07: Important-Mod Regression Follow-Up Summary

**Important-mod detection now reuses a bounded cached Aho-Corasick matcher, trims real-fixture haystack setup cost, and has proof showing both tracked surfaces beat the legacy regex comparator.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-06T02:13:00-07:00
- **Completed:** 2026-04-06T02:30:32.8008142-07:00
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added focused `phase5_detect_mods_important` slices that separate matcher compilation, haystack construction, uncached full-path cost, and cached match-only cost.
- Moved `detect_mods_important` onto a bounded process-wide Aho-Corasick cache and reduced haystack allocation overhead by building the lowercase surface in one pass.
- Refreshed the benchmark proof with follow-up medians showing the synthetic surface is 79.6% faster and the real-fixture surface is 22.8% faster than the legacy comparator.

## Task Commits

Each task was committed atomically:

1. **Task 1: Isolate the important-mod slowdown with benchmark slices tied to the existing Phase 5 harness** - `4096af02` (feat)
2. **Task 2: Optimize detect_mods_important without violating the locked parity and matcher decisions** - `b5b16712` (feat)
3. **Task 3: Refresh the proof artifact and enforce the no-regression bar for the important-mod hotspot** - `99351ddf` (docs)

**Plan metadata:** pending

## Files Created/Modified

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - Added bounded important-mod matcher caching, bench-visible helper hooks, reuse coverage, and one-pass haystack construction with conditional exclude-set work.
- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - Extended the existing Phase 5 important-mod group with root-cause slices and real-fixture haystack attribution.
- `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` - Recorded the follow-up commands, root-cause findings, final medians, and pass calls against the 5% threshold.
- `.planning/phases/05-pattern-caching-and-performance/05-07-SUMMARY.md` - Execution summary and plan metadata.

## Decisions Made

- Reused the repo-standard `LazyLock + quick_cache` bounded cache pattern for important-mod matcher reuse once the synthetic compile-only slice proved per-call automaton construction was the main regression source.
- Preserved the existing Aho-Corasick, `LeftmostLongest`, and combined plugin/XSE haystack semantics; the optimization targeted setup cost rather than altering parity-sensitive matching behavior.
- Treated real-fixture haystack preparation as the remaining hotspot and removed unnecessary plugin-name set work unless `exclude_when` is present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Relaxed the new matcher-reuse test away from a globally exact compile-count assertion**
- **Found during:** Task 2 (Optimize detect_mods_important without violating the locked parity and matcher decisions)
- **Issue:** The first reuse test assumed an exact compile delta of `1`, but the grouped `detect_mods_important` test run is parallel and other important-mod tests can legitimately touch the shared compile counter.
- **Fix:** Kept the pointer-identity reuse assertion and changed the compile-count check to verify forward progress instead of a grouped-run-fragile absolute delta.
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
- **Verification:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important`
- **Committed in:** `b5b16712` (part of Task 2 commit)

**2. [Rule 3 - Blocking] Removed an unused compatibility wrapper after clippy-style dead-code enforcement rejected the optimization build**
- **Found during:** Task 2 (Optimize detect_mods_important without violating the locked parity and matcher decisions)
- **Issue:** After the new conditional haystack helper replaced all call sites, the old wrapper became dead code and blocked both test and bench compilation under the repo's strict unused-code policy.
- **Fix:** Deleted the unused wrapper and routed all production and benchmark callers through the optimized helper directly.
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
- **Verification:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important`; `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_detect_mods_important -- --test`
- **Committed in:** `b5b16712` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes stayed inside the important-mod hotspot work and were necessary to keep the grouped verification path stable and compilable.

## Issues Encountered

- The first benchmark slices showed that caching solved the synthetic regression but the real-fixture path still spent most of its time lowercasing and concatenating the large plugin/XSE surface.
- Same-revision Criterion `change:` output remained a reproducibility signal only, so the proof continued to rely on the paired legacy/current variants for the actual threshold verdict.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 now has a committed follow-up proof showing the important-mod hotspot clears the existing `warning > 5%` bar on both tracked surfaces.
- Later performance work can reuse the new slice pattern if another matcher path needs root-cause isolation without weakening parity or benchmark requirements.

## Self-Check: PASSED

- FOUND: `.planning/phases/05-pattern-caching-and-performance/05-07-SUMMARY.md`
- FOUND: `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
- FOUND: `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs`
- FOUND: `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md`
- FOUND: `4096af02`
- FOUND: `b5b16712`
- FOUND: `99351ddf`

---
*Phase: 05-pattern-caching-and-performance*
*Completed: 2026-04-06*
