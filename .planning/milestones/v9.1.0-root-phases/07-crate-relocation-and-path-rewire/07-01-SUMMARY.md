---
phase: 07-crate-relocation-and-path-rewire
plan: 01
subsystem: rust-workspace
tags: [cargo, planning, audit, validation]
requires:
  - phase: 06-repo-root-workspace-cutover
    provides: repo-root workspace shell and cargo-root proof surface
provides:
  - checked-in Phase 7 relocation audit artifact
  - stable Phase 7 validation contract for relocation and legacy-boundary checks
affects: [07-02, 07-03, planning-audit]
tech-stack:
  added: []
  patterns: [deterministic relocation audit, unittest-under-pytest phase validation]
key-files:
  created: [.planning/phases/07-crate-relocation-and-path-rewire/07-01-SUMMARY.md]
  modified: [.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md, tests/planning/test_phase07_validation.py]
key-decisions:
  - "Create one checked-in relocation audit artifact before and after the move instead of relying on ad hoc notes."
  - "Reserve the final Phase 7 validation hooks up front so later relocation work fills named checks instead of inventing a new audit surface mid-phase."
patterns-established:
  - "Phase-level relocation work should pair Cargo proof with a deterministic old-to-new mapping artifact."
  - "Planning audits can bootstrap with the final contract shape even before all post-move assertions are populated."
requirements-completed: []
duration: current session
completed: 2026-04-12
---

# Phase 7 Plan 1: Relocation audit and validation scaffold summary

**Phase 7 now has a durable audit surface: one checked-in relocation artifact and one planning test file that define the final closure contract.**

## Performance

- **Duration:** current session
- **Completed:** 2026-04-12
- **Tasks:** 2

## Accomplishments

- Created `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` as the canonical Phase 7 relocation proof artifact.
- Added `tests/planning/test_phase07_validation.py` with stable checks for workspace relocation, representative manifest paths, relocation audit completeness, cargo root detection, and the legacy `ClassicLib-rs` boundary.
- Established the audit surfaces that later Phase 7 work reused for the final move and closure proof.

## Task Commits

No task commits were created. The user did not request commits during execution.

## Files Created/Modified

- `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` - checked-in relocation mapping and closure-proof artifact.
- `tests/planning/test_phase07_validation.py` - Phase 7 audit contract for relocation, cargo-root proof, and legacy-boundary checks.

## Decisions Made

- Chose a checked-in Markdown audit as the canonical relocation proof instead of transient command output or task notes.
- Named the final validation hooks up front so the relocation work could fill the contract without renaming tests later.

## Deviations from Plan

None.

## Issues Encountered

None in the scaffold step.

## User Setup Required

None.

## Next Phase Readiness

- Phase 7 had a stable audit and test surface before the physical crate relocation proceeded.
- Ready for `07-02-PLAN.md` to move the six layer directories and rewire the live workspace graph.

## Self-Check: PASSED

- Found `.planning/phases/07-crate-relocation-and-path-rewire/07-01-SUMMARY.md` on disk.
- Found `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` on disk.
- Found `tests/planning/test_phase07_validation.py` on disk.

---
*Phase: 07-crate-relocation-and-path-rewire*
*Completed: 2026-04-12*
