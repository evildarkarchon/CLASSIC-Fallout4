---
phase: 05-pattern-caching-and-performance
plan: 02
subsystem: performance
tags: [rust, aho-corasick, regex, parity, scanlog]
requires:
  - phase: 05-01
    provides: bounded matcher-cache helpers and LazyLock-based hot-path cleanup in mod_detector
provides:
  - fixture-backed parity coverage for important-mod detection
  - private legacy regex helper retained beside the new matcher path
  - Aho-Corasick LeftmostLongest important-mod detection over the combined lowercase haystack
affects: [05-04, classic-scanlog-core, mod_detector]
tech-stack:
  added: []
  patterns: [fixture-backed parity before matcher swaps, combined lowercase haystack matching, retained legacy helper for semantic proof]
key-files:
  created: [.planning/phases/05-pattern-caching-and-performance/05-02-SUMMARY.md]
  modified: [ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs]
key-decisions:
  - "Kept the legacy regex path as a private helper so fixture-backed parity can remain executable while the public function moves to Aho-Corasick."
  - "Used the large crash-log fixture because the smaller fixture does not contain a plugin section suitable for important-mod parity coverage."
  - "Compiled the Aho-Corasick automaton once per call for this plan; cache reuse was deferred to keep the matcher swap tightly scoped to PERF-02."
patterns-established:
  - "Performance-sensitive matcher swaps in scanlog-core should land behind direct old-vs-new parity assertions in the inline Rust test module."
  - "Literal important-mod detection should operate over one lowercased plugin-plus-XSE text surface with MatchKind::LeftmostLongest semantics."
requirements-completed: [PERF-02]
duration: 9min
completed: 2026-04-06
---

# Phase 05 Plan 02: Important-Mod Aho-Corasick Summary

**Important-mod detection now uses a LeftmostLongest Aho-Corasick literal matcher with fixture-backed parity tests and a retained legacy regex helper for semantic proof.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-06T07:31:48Z
- **Completed:** 2026-04-06T07:40:38Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added inline parity coverage that compares the legacy regex path to the new Aho-Corasick path on a real crash-log fixture.
- Added a synthetic overlap test proving `MatchKind::LeftmostLongest` chooses the longest literal at the same start offset.
- Switched `detect_mods_important` to search one combined lowercase plugin/XSE haystack with Aho-Corasick while preserving GPU, exclusion, and output-format branches.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add fixture-backed parity coverage for important-mod detection** - `0473329f` (test), `f45074ad` (feat)
2. **Task 2: Switch detect_mods_important to Aho-Corasick over the combined lowercase haystack** - `ff00b0c9` (feat)

**Plan metadata:** pending

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - added legacy and Aho helpers, fixture-backed parity tests, and the public Aho-backed implementation.
- `.planning/phases/05-pattern-caching-and-performance/05-02-SUMMARY.md` - execution summary and plan metadata.

## Decisions Made
- Kept the legacy regex path as a private helper so parity can remain executable after the public function switches to Aho-Corasick.
- Used the large crash-log fixture for parity because the smaller fixture lacks a plugin section, making it unsuitable for fixture-backed important-mod coverage.
- Kept the Aho automaton one-per-call in this plan to avoid broadening PERF-02 into another matcher-cache change; the summary documents that tradeoff for later benchmark work.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The first chosen fixture (`crash-0DB9300.log`) had no plugin section, so the parity test could not exercise real important-mod entries. Switching to the existing large crash-log fixture resolved this without changing scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `detect_mods_important` now has direct semantic guardrails for follow-on benchmark work in 05-04.
- The retained legacy helper gives future verification a stable oracle if benchmark or cache follow-up reveals unexpected behavior.

## Self-Check: PASSED

- Verified `.planning/phases/05-pattern-caching-and-performance/05-02-SUMMARY.md` exists.
- Verified `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` exists.
- Verified task commits `0473329f`, `f45074ad`, and `ff00b0c9` exist in git history.

---
*Phase: 05-pattern-caching-and-performance*
*Completed: 2026-04-06*
