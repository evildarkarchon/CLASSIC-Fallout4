---
phase: 10-docs-guidance-and-tripwires
plan: "04"
subsystem: api
tags: [docs, api, markdown, repo-root, path-migration]
requires:
  - phase: 10-00
    provides: validation selectors and active-surface tripwires for Phase 10 docs
  - phase: 10-01
    provides: migration-matrix and repo-root contributor guidance baseline
provides:
  - repo-root source links for version, web, update, and config API reference pages
  - historical merge notes relabeled as history instead of live workspace guidance
  - preserved config-to-schema cross-link under the repo-root contract
affects: [phase-10-docs, api-reference-maintenance, validation]
tech-stack:
  added: []
  patterns: [active API docs point at repo-root crate and binding locations, historical ClassicLib-rs mentions must be explicitly labeled]
key-files:
  created: [.planning/phases/10-docs-guidance-and-tripwires/10-04-SUMMARY.md]
  modified:
    - docs/api/classic-version-registry-core.md
    - docs/api/classic-version-core.md
    - docs/api/classic-web-core.md
    - docs/api/classic-update-core.md
    - docs/api/classic-config-core.md
    - docs/api/classic-config-core-yaml-schema.md
key-decisions:
  - "Use repo-root business-logic, foundation, binding, and UI paths in active API docs while keeping merge history only as explicitly labeled historical notes."
  - "Keep classic-config-core and its schema page cross-linked without leaving any ClassicLib-rs operational path examples behind."
patterns-established:
  - "Active API reference pages should link to repo-root crate, binding, and consumer paths from docs/api/."
  - "Absorbed-crate notes stay in the docs only as historical context, never as live workspace instructions."
requirements-completed: [DOCS-01]
duration: 4m 5s
completed: 2026-04-14
---

# Phase 10 Plan 04: Version, config, web, and update API docs Summary

**Repo-root API docs for version, config, web, and update crates with historical merge notes preserved only as labeled history.**

## Performance

- **Duration:** 4m 5s
- **Started:** 2026-04-14T02:47:24Z
- **Completed:** 2026-04-14T02:51:29Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Repointed the version-registry, version, web, and update API pages to live repo-root crate, binding, and UI locations.
- Reworked config and schema references to use root-level `business-logic`, `foundation`, `node-bindings`, and `python-bindings` paths.
- Preserved yaml/crashgen merge history as explicit historical notes instead of stale operational guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update the version, web, and update reference docs** - `d280928b` (feat)
2. **Task 2: Update the config reference and schema docs** - `00bead6c` (feat)

**Plan metadata:** recorded in the final docs/state commit after planning artifacts were updated.

## Files Created/Modified
- `docs/api/classic-version-registry-core.md` - switched active source and binding references to repo-root paths and relabeled yaml merge history.
- `docs/api/classic-version-core.md` - updated root crate and binding links for the version helper guide.
- `docs/api/classic-web-core.md` - replaced stale `ClassicLib-rs` foundation and binding references with repo-root locations.
- `docs/api/classic-update-core.md` - updated repo-root source links for the crate, bindings, and TUI consumer examples.
- `docs/api/classic-config-core.md` - refreshed config, settings, registry, bridge, and binding references to repo-root ownership.
- `docs/api/classic-config-core-yaml-schema.md` - kept the schema contract cross-linked to the repo-root config guide.

## Decisions Made
- Use repo-root relative links throughout active API reference pages because Phase 7 made root-level layer directories authoritative.
- Keep absorbed-crate notes only when clearly marked historical so contributors are not taught stale operational paths.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The next Phase 10 API doc plans can follow the same repo-root linking pattern for remaining reference pages.
- The `api_core_group_b_contract` validation selector passes with the updated pages.

## Self-Check: PASSED

- Found `.planning/phases/10-docs-guidance-and-tripwires/10-04-SUMMARY.md`.
- Found task commits `d280928b` and `00bead6c` in git history.

---
*Phase: 10-docs-guidance-and-tripwires*
*Completed: 2026-04-14*
