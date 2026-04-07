---
phase: 06-mmap-toctou-safety
plan: 02
subsystem: testing
tags: [rust, criterion, memmap2, mmap, windows]
requires:
  - phase: 06-01
    provides: production `map_copy_read_only()` mmap path to validate
provides:
  - `phase6_mmap_variants` benchmark coverage in the existing file-io harness
  - committed Windows-focused mmap throughput proof for `map`, `map_copy`, and `map_copy_read_only`
  - local-only Criterion save/compare workflow documentation for Phase 6 contributors
affects: [SAFE-05, performance_baselines, classic-file-io-core]
tech-stack:
  added: []
  patterns: [existing-harness benchmark proof, local-only Criterion baselines with committed markdown evidence]
key-files:
  created:
    - .planning/phases/06-mmap-toctou-safety/06-02-SUMMARY.md
    - .planning/phases/06-mmap-toctou-safety/06-BENCHMARK-PROOF.md
  modified:
    - ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs
    - performance_baselines/README.md
key-decisions:
  - "Keep the Phase 6 throughput proof in classic-file-io-core's existing file_io_benchmarks harness instead of creating a new benchmark target."
  - "Treat map_copy_read_only() as acceptable for Windows validation because it wins at 1 MiB+4 KiB and 4 MiB and stays below a 10% slowdown even when 16 MiB crosses the 5% warning bar."
patterns-established:
  - "Phase benchmark proofs stay in the crate-local Criterion harness and compare only the locked variants for that requirement."
  - "Raw Criterion baselines remain local under ClassicLib-rs/target/criterion while git tracks a markdown proof artifact with commands, sizes, and results."
requirements-completed: [SAFE-05]
duration: 6 min
completed: 2026-04-06
---

# Phase 6 Plan 2: mmap throughput proof Summary

**Criterion now benchmarks `map`, `map_copy`, and `map_copy_read_only()` in `classic-file-io-core`, with a committed Windows proof showing the safer mapping stays acceptable.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T10:15:10Z
- **Completed:** 2026-04-06T10:21:34Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added the `phase6_mmap_variants` group to the existing file-io Criterion harness with threshold-plus and larger synthetic crash-log inputs.
- Captured a committed Phase 6 benchmark proof with commands, sizes, medians, and a conservative Windows acceptability call.
- Documented the local-only save/compare baseline workflow so contributors can reproduce Phase 6 measurements without committing raw Criterion artifacts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend `file_io_benchmarks.rs` with a Phase 6 three-way mmap throughput group** - `cefc45ab` (feat)
2. **Task 2: Capture the committed Phase 6 benchmark proof and document the local baseline workflow** - `77083571` (docs)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` - adds the `phase6_mmap_variants` group and benchmark-local helpers that mirror the production decode path.
- `.planning/phases/06-mmap-toctou-safety/06-BENCHMARK-PROOF.md` - records the Windows-focused commands, tested sizes, medians, and acceptability call.
- `performance_baselines/README.md` - documents the Phase 6 local save/compare workflow and points contributors to the committed proof artifact.

## Decisions Made
- Kept the mmap throughput evidence in `classic-file-io-core`'s existing `file_io_benchmarks.rs` harness so SAFE-05 follows the repo's established benchmark-proof pattern.
- Called `map_copy_read_only()` acceptable on Windows with conservative wording: it wins at smaller tracked sizes and is ~8.5% slower only at 16 MiB, which exceeds the warning bar but stays below a fail-grade regression threshold.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The Criterion `--baseline` rerun showed normal same-revision noise, so the proof explicitly treats that second pass as a reproducibility check rather than a before/after performance claim.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 now has both the production `map_copy_read_only()` change and the committed benchmark proof required for SAFE-05 verification.
- The phase is complete and ready for verifier review or milestone progression.

## Self-Check: PASSED

- Found summary file on disk.
- Found benchmark proof file on disk.
- Verified task commits `cefc45ab` and `77083571` in git history.
