---
phase: 06-repo-root-workspace-cutover
plan: 00
subsystem: testing
tags: [planning, validation, cargo, powershell]
requires: []
provides:
  - Phase 6 planning audit scaffold with stable named hooks for later waves
  - Clean repo-root Cargo proof helper that quarantines ClassicLib-rs/target before validation
affects: [phase-06-01, phase-06-02, phase-06-03, repo-root-cargo]
tech-stack:
  added: []
  patterns: [file-backed planning audits with unittest under pytest, clean-run proof helpers that temporarily isolate legacy target outputs]
key-files:
  created: [tests/planning/test_phase06_validation.py, tests/planning/phase06_clean_run.ps1, .planning/phases/06-repo-root-workspace-cutover/06-00-SUMMARY.md]
  modified: []
key-decisions:
  - "Reserve the full Phase 6 audit hook surface up front with skipped tests so later plans can fill the contract without renaming it."
  - "Rename ClassicLib-rs/target during clean proof runs so stale legacy artifacts cannot mask repo-root Cargo failures."
patterns-established:
  - "Phase validation scaffolds should claim later-wave audit names early, then replace skipped placeholders with concrete assertions as the phase lands."
  - "Clean proof helpers for workspace-root migrations should quarantine the old target directory before running root-detection and build commands."
requirements-completed: [ROOT-01, ROOT-02]
duration: 0min
completed: 2026-04-12
---

# Phase 6 Plan 00: Validation Scaffold Bootstrap Summary

**Phase 6 now has a stable planning audit scaffold and a reusable clean-run helper for repo-root Cargo proof.**

## Performance

- **Duration:** 0 min
- **Started:** 2026-04-12T03:56:02-07:00
- **Completed:** 2026-04-12T03:56:02-07:00
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added `tests/planning/test_phase06_validation.py` with the bootstrap audit and the full named hook contract for later Phase 6 waves.
- Added `tests/planning/phase06_clean_run.ps1` with the clean repo-root Cargo validation sequence required by the phase.
- Locked in the legacy-target quarantine pattern so later clean proof runs cannot accidentally reuse `ClassicLib-rs/target` outputs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the Phase 6 audit scaffold and clean-state helper** - `fdf9ee9d` (feat)

**Plan metadata:** recorded in the final docs commit that captures SUMMARY/STATE/ROADMAP updates.

## Files Created/Modified
- `tests/planning/test_phase06_validation.py` - Phase 6 planning audit scaffold with bootstrap coverage and reserved later-wave hook names.
- `tests/planning/phase06_clean_run.ps1` - Clean-state helper that renames `ClassicLib-rs/target` and runs the repo-root Cargo proof sequence.

## Decisions Made
- Reserved every planned Phase 6 audit hook up front as a stable contract so later plans can replace placeholders without renaming tests.
- Made the clean helper quarantine `ClassicLib-rs/target` during proof runs to ensure later root-cutover validation cannot pass on stale outputs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Wave 0 validation assets are in place and the targeted bootstrap verification passes.
- Phase 6 can proceed to `06-01` to promote the repo-root workspace shell and helper scripts.

## Self-Check: PASSED

---
*Phase: 06-repo-root-workspace-cutover*
*Completed: 2026-04-12*
