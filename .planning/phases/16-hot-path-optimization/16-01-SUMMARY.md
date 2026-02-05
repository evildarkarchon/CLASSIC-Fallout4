---
phase: 16-hot-path-optimization
plan: 01
subsystem: performance
tags: [profiling, cprofile, criterion, benchmarks, optimization]

# Dependency graph
requires:
  - phase: 13-benchmark-infrastructure
    provides: Criterion benchmark suite for yaml-core, scanlog-core, file-io-core
  - phase: 14-hot-path-profiling
    provides: Profiling infrastructure (py-spy scripts, cache instrumentation)
provides:
  - Pre-optimization benchmark baseline (pre-opt-phase16)
  - 5 cProfile profiling runs of CLI scan workflow
  - Hot path analysis with ranked optimization targets
affects: [16-02, 16-03]

# Tech tracking
tech-stack:
  added: [flameprof, gprof2dot]
  patterns: [cProfile-based profiling workflow]

key-files:
  created:
    - .planning/phases/16-hot-path-optimization/16-01-ANALYSIS.md
  modified: []

key-decisions:
  - "Used cProfile instead of py-spy due to Python 3.14 incompatibility"
  - "Threading overhead identified as dominant factor (86%)"
  - "Rust FFI overhead confirmed minimal (0.3%)"
  - "Batch processing identified as primary optimization target"

patterns-established:
  - "Deterministic profiling with cProfile for Python-level hot paths"
  - "Combined profile analysis across multiple runs for statistical validity"

# Metrics
duration: 25min
completed: 2026-02-04
---

# Phase 16 Plan 01: Hot Path Profiling Summary

**cProfile-based analysis identified threading overhead (86%) and 5 optimization targets for 16-02, with 86 Criterion baselines saved as pre-opt-phase16**

## Performance

- **Duration:** 25 min
- **Started:** 2026-02-04T20:00:00Z
- **Completed:** 2026-02-04T20:30:00Z
- **Tasks:** 3
- **Files created:** 1 (16-01-ANALYSIS.md)

## Accomplishments

- Saved 86 pre-optimization benchmark baselines across yaml-core, scanlog-core, and file-io-core
- Collected 5 cProfile profiling runs (601 crash logs each, ~14s per run)
- Identified threading overhead as dominant factor (86% of execution time)
- Documented 5 optimization targets with expected improvements
- Generated JSON export and DOT call graph for interactive analysis

## Task Commits

Each task was committed atomically:

1. **Task 1: Establish Pre-Optimization Benchmark Baseline** - (no commit - data in gitignored target/)
2. **Task 2: Collect py-spy Profiling Data (5 Iterations)** - (no commit - data in gitignored target/)
3. **Task 3: Analyze Flamegraphs and Document Hot Path Rankings** - `6eb22991` (docs)

**Plan metadata:** This commit (docs: complete plan)

_Note: Tasks 1 and 2 produced data artifacts in gitignored target/ directories, not code changes._

## Files Created/Modified

- `.planning/phases/16-hot-path-optimization/16-01-ANALYSIS.md` - Comprehensive hot path analysis with rankings

## Data Artifacts Created (gitignored)

- `rust/target/criterion/*/pre-opt-phase16/` - 86 benchmark baselines
- `target/profiling/cprofile/cli-scan-run-{1-5}.pstats` - cProfile data
- `target/profiling/pyspy/cli-scan-interactive.json` - Top 100 functions analysis
- `target/profiling/pyspy/cli-scan-run-1.dot` - Call graph
- `target/profiling/cache-stats/pre-opt-stats.json` - Cache statistics

## Decisions Made

1. **cProfile instead of py-spy:** py-spy 0.4.1 does not support Python 3.14. Used cProfile for deterministic profiling as alternative.

2. **Threading as primary target:** 86% of execution time in asyncio threading. Batch processing to reduce thread coordination identified as highest-impact optimization.

3. **Rust FFI confirmed efficient:** Only 0.3% overhead in `_handle_rust_result`, confirming previous optimization phases were successful.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] py-spy incompatibility with Python 3.14**
- **Found during:** Task 2 (py-spy profiling)
- **Issue:** py-spy 0.4.1 fails with "Failed to find python version" on Python 3.14
- **Fix:** Used cProfile (built-in deterministic profiler) as alternative
- **Files modified:** None (different tooling choice)
- **Verification:** 5 successful profile runs with cProfile
- **Impact:** No native Rust frames captured, but Python-level hot paths identified

---

**Total deviations:** 1 auto-fixed (blocking tool incompatibility)
**Impact on plan:** Adapted profiling methodology while achieving same analytical goals. Native frame visibility deferred until py-spy supports Python 3.14.

## Issues Encountered

1. **py-spy Python 3.14 incompatibility** - py-spy 0.4.1 does not support Python 3.14 (very new version). Used cProfile as alternative.

2. **flameprof async profile handling** - flameprof couldn't generate flamegraphs from async cProfile data (ZeroDivisionError). Used gprof2dot for DOT format instead.

3. **scalene environment isolation** - scalene runs in isolated environment, couldn't access project dependencies. Not viable for this project.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 16-02 (Optimization Implementation):**
- Baseline benchmarks saved for comparison
- Hot paths identified and ranked
- Optimization targets documented with expected improvements

**Primary optimization targets for 16-02:**
1. Batch Rust calls to reduce threading overhead (10-15% expected)
2. Pre-compile regex patterns (5-10% expected)
3. Optimize result aggregation (3-5% expected)

**Blockers/Concerns:**
- py-spy incompatibility limits native frame visibility
- Threading optimization may require significant refactoring

---
*Phase: 16-hot-path-optimization*
*Completed: 2026-02-04*
