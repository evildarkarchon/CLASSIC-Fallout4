---
phase: 10-docs-guidance-and-tripwires
plan: "08"
subsystem: docs
tags: [repo-root, agent-guidance, parity-workflows, migration-matrix]
requires:
  - phase: 10-02
    provides: Updated binding workflow docs and repo-root contract references.
  - phase: 10-07
    provides: Repo-root skill entrypoints and mirrored classic-project-guide surfaces.
provides:
  - Synchronized repo-guide mirrors with repo-root architecture and command guidance.
  - Repo-guide parity workflow checklists aligned with current Node and Python binding docs.
affects: [phase-10-validation, classic-project-guide, agent-guidance]
tech-stack:
  added: []
  patterns: [mirror-synchronized guidance, repo-root parity checklists]
key-files:
  created: [.planning/phases/10-docs-guidance-and-tripwires/10-08-SUMMARY.md]
  modified:
    - .agents/skills/classic-project-guide/references/repo-guide.md
    - .opencode/skills/classic-project-guide/references/repo-guide.md
    - .claude/skills/classic-project-guide/references/repo-guide.md
    - .agent/skills/classic-project-guide/references/repo-guide.md
key-decisions:
  - "Keep all four repo-guide mirrors textually synchronized so validation and agent behavior stay aligned."
  - "Point parity workflow checklists back to docs/api binding guidance and the workspace migration matrix instead of duplicating legacy-path explanations."
patterns-established:
  - "Repo-guide mirrors teach repo-root layer directories and package-local binding commands."
  - "Node and Python parity sections use repo-root trigger paths plus binding-local artifact locations."
requirements-completed: [DOCS-01, DOCS-02]
duration: 15 min
completed: 2026-04-14
---

# Phase 10 Plan 08: Repo Guide Mirrors Summary

**Repo-guide mirrors now teach the repo-root layer layout, binding-local command flows, and repo-root parity checklists across all four agent surfaces.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-14T02:50:03Z
- **Completed:** 2026-04-14T03:05:03Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Rewrote the mirrored Architecture Map sections to describe the live repo-root workspace layout.
- Replaced stale Node and Python command examples with the live `node-bindings/classic-node` and `python-bindings/.venv` workflows.
- Rewired Node and Python parity workflow sections to current repo-root trigger paths, artifacts, validation commands, and doc pointers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite the architecture and command sections in every repo-guide mirror** - `e3594d90` (docs)
2. **Task 2: Rewire the Node and Python parity workflow sections in every repo-guide mirror** - `34850bf1` (docs)

## Files Created/Modified
- `.agents/skills/classic-project-guide/references/repo-guide.md` - Updated the long-form repo guide mirror to repo-root architecture, commands, and parity guidance.
- `.opencode/skills/classic-project-guide/references/repo-guide.md` - Mirrored the same repo-root architecture, commands, and parity guidance.
- `.claude/skills/classic-project-guide/references/repo-guide.md` - Mirrored the same repo-root architecture, commands, and parity guidance.
- `.agent/skills/classic-project-guide/references/repo-guide.md` - Mirrored the same repo-root architecture, commands, and parity guidance.

## Decisions Made
- Kept the four repo-guide mirrors synchronized on the same wording so future agent entrypoints do not drift.
- Routed parity workflow translation back through `docs/workspace-migration-matrix.md` and the updated `docs/api` binding workflow pages instead of duplicating migration prose.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 now has synchronized long-form classic-project-guide mirrors on all active agent surfaces.
- The remaining closeout work is metadata/state bookkeeping for this completed docs plan.

## Self-Check: PASSED

- Found `.planning/phases/10-docs-guidance-and-tripwires/10-08-SUMMARY.md`.
- Verified task commits `e3594d90` and `34850bf1` exist in git history.
- Re-ran `python -m pytest tests/planning/test_phase10_validation.py -q -k "repo_guide_mirrors_contract"` successfully.
