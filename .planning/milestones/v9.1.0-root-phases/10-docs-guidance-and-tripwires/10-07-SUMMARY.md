---
phase: 10-docs-guidance-and-tripwires
plan: "07"
subsystem: docs
tags: [agents, claude, skills, docs, migration]
requires:
  - phase: 10-00
    provides: Phase 10 validation scaffold and active-surface tripwires.
  - phase: 10-01
    provides: Workspace migration matrix used as the shared translation reference.
provides:
  - Repo-root always-on guidance in AGENTS.md and CLAUDE.md.
  - Synchronized classic-project-guide entrypoint mirrors across agent environments.
affects: [phase-10-validation, agent-guidance, repo-root-docs]
tech-stack:
  added: []
  patterns: [migration-matrix routing, synchronized agent entrypoints]
key-files:
  created: [.planning/phases/10-docs-guidance-and-tripwires/10-07-SUMMARY.md]
  modified: [AGENTS.md, CLAUDE.md, .agents/skills/classic-project-guide/SKILL.md, .opencode/skills/classic-project-guide/SKILL.md, .claude/skills/classic-project-guide/SKILL.md, .agent/skills/classic-project-guide/SKILL.md]
key-decisions:
  - "Keep AGENTS.md policy text intact while swapping live location examples to the repo-root layer directories."
  - "Route every always-on agent entrypoint to docs/workspace-migration-matrix.md instead of duplicating old-to-new translations."
patterns-established:
  - "Agent entrypoints must describe the repo-root layer layout and binding paths as the live contract."
  - "Mirrored skill entrypoints stay materially identical across .agents, .opencode, .claude, and .agent."
requirements-completed: [DOCS-01, DOCS-02]
duration: 12 min
completed: 2026-04-14
---

# Phase 10 Plan 07: Agent entrypoints Summary

**Repo-root AGENTS/CLAUDE guidance plus synchronized classic-project-guide entrypoints routed through the workspace migration matrix**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-14T02:37:50Z
- **Completed:** 2026-04-14T02:49:50Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Updated `AGENTS.md` and `CLAUDE.md` so both always-on agent surfaces teach the repo-root workspace contract.
- Repointed active path examples to `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/`.
- Synchronized all four `classic-project-guide` entrypoint mirrors and added explicit routing to `docs/workspace-migration-matrix.md`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update AGENTS.md and CLAUDE.md to the post-move contract** - `018a2eeb` (feat)
2. **Task 2: Sync all classic-project-guide entrypoint mirrors** - `9d4837e5` (feat)

## Files Created/Modified
- `AGENTS.md` - Reframed the always-on repository contract around the repo-root workspace layout.
- `CLAUDE.md` - Updated generated guidance sections so path, stack, and architecture examples match the repo-root contract.
- `.agents/skills/classic-project-guide/SKILL.md` - Updated the primary skill entrypoint to repo-root Rust layer and binding paths.
- `.opencode/skills/classic-project-guide/SKILL.md` - Synced the OpenCode mirror to the same contract.
- `.claude/skills/classic-project-guide/SKILL.md` - Synced the Claude mirror to the same contract.
- `.agent/skills/classic-project-guide/SKILL.md` - Synced the generic agent mirror to the same contract.

## Decisions Made
- Kept the existing AGENTS/skill guardrails and ownership guidance intact, changing only the stale live-path examples and workspace-root wording.
- Added migration-matrix links to every active agent entrypoint surface covered by this plan so legacy-path translation stays centralized.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Agent entrypoints now agree on the repo-root contract and can support the deeper repo-guide mirror refresh in later Phase 10 work.
- No blockers identified for subsequent docs-guidance plans.

## Self-Check: PASSED

- FOUND: `.planning/phases/10-docs-guidance-and-tripwires/10-07-SUMMARY.md`
- FOUND: `018a2eeb`
- FOUND: `9d4837e5`
