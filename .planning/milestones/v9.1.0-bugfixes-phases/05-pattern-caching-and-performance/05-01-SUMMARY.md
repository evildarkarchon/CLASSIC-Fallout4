---
phase: 05-pattern-caching-and-performance
plan: 01
subsystem: performance
tags: [rust, regex, quick_cache, lazylock, xxh3, scanlog]
requires:
  - phase: 04-bounded-cache-replacement
    provides: bounded LazyLock + quick_cache cache pattern reused for matcher caches
provides:
  - process-wide bounded matcher caches for mod detector single/double/batch hot paths
  - normalized xxh3 cache keys and focused cache reuse coverage
  - contributor docs for the Phase 5 matcher-cache pattern
affects: [05-02, 07-consistency-sweep, classic-scanlog-core]
tech-stack:
  added: [quick_cache, serial_test]
  patterns: [LazyLock plus quick_cache matcher caches, normalized hash-keyed regex reuse]
key-files:
  created: []
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs
    - docs/api/classic-scanlog-core.md
key-decisions:
  - Keep single, double, and batch matcher caches separate while sharing normalization and compile helpers.
  - Validate bounded matcher caches by reuse and capacity behavior instead of eviction-victim order.
patterns-established:
  - "Hash normalized matcher tokens with xxh3 before looking up process-wide regex caches."
  - "Use LazyLock<quick_cache::sync::Cache<...>> for input-derived hot-path matcher reuse, not ad hoc global HashMaps."
requirements-completed: [PERF-01, CONS-04]
duration: 8min
completed: 2026-04-06
---

# Phase 05 Plan 01: Add bounded matcher caches for mod detector hot paths Summary

**Bounded xxh3-keyed regex matcher caches for mod_detector single/double/batch paths with contributor-facing LazyLock guidance**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-06T07:21:24Z
- **Completed:** 2026-04-06T07:28:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added process-wide bounded `quick_cache` matcher caches for `detect_mods_single`, `detect_mods_double`, and `detect_mods_batch`.
- Reused normalized xxh3 content hashes and shared compile helpers so repeated matcher builds stay cheap across calls.
- Documented that Phase 5 caches input-derived hot-path regexes without broadening into a repo-wide static-regex sweep.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add shared bounded matcher caches for single/double/batch** - `d02a035b` (test), `3ca562c6` (feat)
2. **Task 2: Audit touched mod_detector regex setup and use LazyLock only for true constants** - `7f427d13` (chore)

**Plan metadata:** _pending final docs commit_

_Note: TDD task 1 used separate red and green commits._

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` - added `quick_cache` plus `serial_test` support for matcher-cache coverage.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - introduced bounded matcher caches, normalized hash helpers, and focused reuse/boundedness tests.
- `docs/api/classic-scanlog-core.md` - documented the new bounded matcher-cache pattern for `mod_detector` contributors.

## Decisions Made
- Kept matcher caches family-specific (`single`, `double`, `batch`) while factoring shared normalization and compile helpers, matching the plan's “shared helpers, not one universal cache” guidance.
- Treated only input-invariant regexes as candidates for standalone `LazyLock` statics; the touched hot-path alternation regexes remain on bounded hash-keyed caches because their bodies come from YAML/config inputs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stabilized conflict matcher token ordering before caching**
- **Found during:** Task 1 (Add shared bounded matcher caches for single/double/batch)
- **Issue:** `detect_mods_double` previously built its alternation pattern from a `HashSet`, which made equal-content matcher construction order nondeterministic and a poor fit for stable cache keys.
- **Fix:** Normalized conflict matcher tokens into a deterministic sorted list before hashing and compiling the cached regex.
- **Files modified:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`
- **Verification:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_`; `cargo clippy -p classic-scanlog-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
- **Committed in:** `3ca562c6` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix tightened correctness for cache-key stability without expanding scope beyond the touched hot path.

## Issues Encountered
- Clippy flagged the first helper placement as “items after a test module”; the helpers were moved above `#[cfg(test)]` and re-verified.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `mod_detector` now has the bounded matcher-cache foundation Phase 5 expected for the remaining important-mod optimization work.
- Phase 05-02 can build parity-backed `detect_mods_important` improvements on top of the new cache and documentation pattern.

## Self-Check: PASSED

- FOUND: `.planning/phases/05-pattern-caching-and-performance/05-01-SUMMARY.md`
- FOUND: `d02a035b`
- FOUND: `3ca562c6`
- FOUND: `7f427d13`

---
*Phase: 05-pattern-caching-and-performance*
*Completed: 2026-04-06*
