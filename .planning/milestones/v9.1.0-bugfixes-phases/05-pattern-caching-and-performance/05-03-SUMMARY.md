---
phase: 05-pattern-caching-and-performance
plan: 03
subsystem: bindings
tags: [rust, cxx, classic-cpp-bridge, lazylock, logparser, performance]
requires: []
provides:
  - module-level LazyLock<LogParser> reuse for bridge crash-pattern detection
  - positive bridge regression coverage for detect_crash_pattern
  - bridge API note documenting cached parser reuse
affects: [PERF-03, classic-cpp-bridge, docs/api]
tech-stack:
  added: []
  patterns: [module-level LazyLock singleton reuse, observable-output bridge regression coverage]
key-files:
  created: [.planning/phases/05-pattern-caching-and-performance/05-03-SUMMARY.md]
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
    - docs/api/classic-cpp-bridge-data-entrypoints.md
key-decisions:
  - Keep bridge regression coverage focused on observable main_error output instead of parser internals.
  - Reuse one module-level default LogParser with LazyLock while preserving empty-string fail-soft behavior for parse failures.
patterns-established:
  - "Bridge parser helpers can cache core parser instances with LazyLock when behavior stays adapter-only."
  - "Bridge tests should prove repeated-call stability through public output rather than cache internals."
requirements-completed: [PERF-03]
duration: 4min
completed: 2026-04-06
---

# Phase 05 Plan 03: Bridge crash-pattern parser reuse Summary

**Cached `detect_crash_pattern` on one shared `LogParser` while adding positive bridge coverage and documenting the unchanged fail-soft contract.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T07:18:20Z
- **Completed:** 2026-04-06T07:22:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added positive `detect_crash_pattern` regression coverage using an existing scanlog benchmark fixture.
- Verified repeated bridge calls keep the same observable crash-pattern result.
- Replaced per-call `LogParser::new(None)` construction with a module-level `LazyLock<LogParser>` and documented that reuse.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bridge coverage for positive crash-pattern detection and parser reuse** - `867b2d67` (test)
2. **Task 2: Cache the bridge parser with a module-level LazyLock and document the helper contract** - `41372c0f` (feat)

## Files Created/Modified
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - added positive bridge tests and switched `detect_crash_pattern` to a shared `LazyLock<LogParser>`.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` - documented cached parser reuse and clarified the helper's current fail-soft behavior.

## Decisions Made
- Kept the bridge adapter-only by caching only the parser instance and still delegating crash-header parsing to `classic_scanlog_core::LogParser`.
- Used observable output assertions for regression coverage so the tests protect behavior without binding to parser-cache internals.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The new positive coverage passed immediately because non-empty crash-header parsing already worked; Task 1 therefore served as regression coverage before the caching change rather than exposing a behavior bug.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PERF-03 is covered with positive bridge tests plus parser reuse.
- The bridge surface remains thin and documented, so later benchmark work can measure this hotspot without widening the C++ adapter.

## Self-Check: PASSED

- Found `.planning/phases/05-pattern-caching-and-performance/05-03-SUMMARY.md`
- Found commit `867b2d67`
- Found commit `41372c0f`
