---
phase: 10-docs-guidance-and-tripwires
plan: "06"
subsystem: api
tags: [docs, api, migration, cpp, gui, scanlog, database]
requires:
  - phase: 10-docs-guidance-and-tripwires
    provides: Shared Phase 10 migration policy that treats repo-root paths as canonical and keeps ClassicLib-rs references historical-only.
provides:
  - Repo-root path routing for remaining scan, database, and bridge API docs.
  - Updated active C++ bridge callback and entrypoint references under `cpp-bindings/`.
affects: [docs/api/README.md, phase-10-validation, agent-guidance]
tech-stack:
  added: []
  patterns: [repo-root API source links, explicitly labeled historical notes]
key-files:
  created: [.planning/phases/10-docs-guidance-and-tripwires/10-06-SUMMARY.md]
  modified:
    - docs/api/classic-database-core.md
    - docs/api/formid-sqlite-conventions.md
    - docs/api/classic-scangame-core.md
    - docs/api/classic-scanlog-core.md
    - docs/api/classic-cpp-bridge-game-entrypoints.md
    - docs/api/classic-cpp-bridge-data-entrypoints.md
    - docs/api/classic-cpp-bridge-scan-progress-callback.md
key-decisions:
  - "Limit this plan to active scan/database/bridge API pages and replace live ClassicLib-rs source links with repo-root business-logic, foundation, cpp-bindings, node-bindings, and python-bindings paths."
  - "Keep historical rename and absorbed-crate notes, but only as explicitly labeled history rather than live operational guidance."
patterns-established:
  - "API doc path routing: contributor-facing source links should point at repo-root crates and bindings."
  - "Historical mentions are allowed only when labeled as migration or rename context."
requirements-completed: [DOCS-01]
duration: 1 min
completed: 2026-04-13
---

# Phase 10 Plan 06: Scan/database/bridge API repo-root doc refresh Summary

**Repo-root scan, database, and bridge API references now point at live business-logic and cpp-bindings sources without teaching ClassicLib-rs as an active workspace root.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-13T19:50:24-07:00
- **Completed:** 2026-04-13T19:51:06.7163481-07:00
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Repointed the remaining scan and database API pages to repo-root `business-logic/`, `foundation/`, `node-bindings/`, `python-bindings/`, and `cpp-bindings/` locations.
- Updated active C++ bridge entrypoint and scan-progress callback docs to use repo-root `cpp-bindings/classic-cpp-bridge` source links.
- Re-ran the Phase 10 runtime-group D validation selector and kept historical notes as labeled history instead of active workspace guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update the database and scan reference pages** - `4f8548f4` (docs)
2. **Task 2: Update the CXX bridge and GUI-consumer reference pages** - `ebe52c8d` (docs)

## Files Created/Modified
- `docs/api/classic-database-core.md` - repointed scan/database integration links to repo-root crate and binding locations.
- `docs/api/formid-sqlite-conventions.md` - repointed source-backed schema/path references to repo-root scanlog, config, and bridge sources.
- `docs/api/classic-scangame-core.md` - repointed related-crate and rule-model references to repo-root business-logic and foundation crates.
- `docs/api/classic-scanlog-core.md` - repointed config, database, file I/O, runtime, and binding references to repo-root locations.
- `docs/api/classic-cpp-bridge-game-entrypoints.md` - repointed bridge source ownership links to repo-root `cpp-bindings` files.
- `docs/api/classic-cpp-bridge-data-entrypoints.md` - repointed data-entrypoint source links to repo-root `cpp-bindings` files.
- `docs/api/classic-cpp-bridge-scan-progress-callback.md` - repointed callback contract links to repo-root header and scanner sources.

## Decisions Made
- Limit this plan to the remaining active runtime-group D API pages covered by the plan and validation selector.
- Preserve rename and absorbed-crate history only as labeled notes while removing stale live workspace-root path teaching.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The remaining active runtime-group D API pages now align with the repo-root source tree expected by Phase 10 validation.
- No blockers found for later docs/guidance cleanup plans.

## Self-Check: PASSED

- Found `.planning/phases/10-docs-guidance-and-tripwires/10-06-SUMMARY.md`.
- Found task commit `4f8548f4`.
- Found task commit `ebe52c8d`.

---
*Phase: 10-docs-guidance-and-tripwires*
*Completed: 2026-04-13*
