---
phase: 10-docs-guidance-and-tripwires
plan: "05"
subsystem: docs
tags: [docs, api, migration, repo-root, tripwires]
requires:
  - phase: 10-docs-guidance-and-tripwires
    provides: Phase 10 validation selectors and repo-root doc policy for active guidance.
provides:
  - Repo-root source and binding links for the path, XSE, setup, file I/O, FormID boundary, and resource API pages.
  - Explicit current-location guidance for group C workflow-style API docs without active `ClassicLib-rs/...` path instructions.
affects: [phase-10-docs-guidance-and-tripwires, docs/api, planning-validation]
tech-stack:
  added: []
  patterns: [active docs use repo-root crate and binding paths, historical notes stay explicitly labeled]
key-files:
  created: [.planning/phases/10-docs-guidance-and-tripwires/10-05-SUMMARY.md]
  modified:
    - docs/api/classic-path-core.md
    - docs/api/classic-xse-core.md
    - docs/api/game-setup-workflow.md
    - docs/api/formid-settings-boundary.md
    - docs/api/classic-file-io-core.md
    - docs/api/classic-resource-core.md
key-decisions:
  - "Keep workflow narratives intact and only rewrite active source, binding, and artifact locations to the repo-root tree."
  - "Treat the final stale `classic-xse-core` link as an inline doc bugfix and correct it in a follow-up fix commit rather than reopening task scope."
patterns-established:
  - "API workflow docs should link to repo-root `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `foundation/`, and `ui-applications/` paths."
requirements-completed: [DOCS-01]
duration: 15 min
completed: 2026-04-14
---

# Phase 10 Plan 05: Path, setup, file, and resource API docs summary

**Repo-root path and binding references for CLASSIC's path, setup, file I/O, FormID boundary, XSE, and resource API workflow pages**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-14T02:35:29Z
- **Completed:** 2026-04-14T02:50:29Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Repointed the path, XSE, and setup workflow docs to repo-root crate and bridge locations.
- Repointed the FormID boundary, file I/O, and resource docs to repo-root crate, binding, and foundation locations.
- Kept historical-layout mentions out of active instructions while preserving the existing workflow narratives.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update the path and setup workflow reference pages** - `eb96c9cf` (feat)
2. **Task 2: Update the boundary, file I/O, and resource reference pages** - `c530525a` (feat)
3. **Follow-up fix: Correct a missed `classic-xse-core` repo-root link** - `6912b940` (fix)

**Plan metadata:** pending state/docs commit

## Files Created/Modified
- `docs/api/classic-path-core.md` - repo-root source, binding, and TUI path references for the path workflow guide
- `docs/api/classic-xse-core.md` - repo-root source, bridge, Node, Python, and version-core references for the XSE guide
- `docs/api/game-setup-workflow.md` - repo-root crate and bridge entrypoint links for the setup workflow page
- `docs/api/formid-settings-boundary.md` - repo-root config, bridge, database, Node, and Python references for the FormID boundary doc
- `docs/api/classic-file-io-core.md` - repo-root consumer and foundation links for the file I/O guide
- `docs/api/classic-resource-core.md` - repo-root crate and binding links for the resource guide
- `.planning/phases/10-docs-guidance-and-tripwires/10-05-SUMMARY.md` - execution record for this plan

## Decisions Made
- Kept scope to the six plan-owned API pages and only changed active path/location guidance.
- Used the existing `api_runtime_group_c_contract` selector as the verification gate for both tasks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected one remaining legacy path in `classic-xse-core`**
- **Found during:** Post-task verification sweep while preparing the summary
- **Issue:** One `classic-version-core` link in `docs/api/classic-xse-core.md` still pointed to `ClassicLib-rs/business-logic/...`
- **Fix:** Replaced the final stale link with the repo-root `business-logic/classic-version-core` path and re-ran the plan validation selector
- **Files modified:** `docs/api/classic-xse-core.md`
- **Verification:** `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_runtime_group_c_contract"`
- **Committed in:** `6912b940`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** Low. The follow-up fix completed the intended repo-root contract without changing scope.

## Issues Encountered
- `git status` showed unrelated in-progress doc and planning changes from other work on the branch, so this plan staged and committed only its six owned API pages.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Group C API workflow docs now teach the repo-root layout consistently.
- Later Phase 10 doc plans can continue updating other API pages without revisiting these six surfaces.

## Known Stubs
None.

---
*Phase: 10-docs-guidance-and-tripwires*
*Completed: 2026-04-14*

## Self-Check: PASSED
FOUND: .planning/phases/10-docs-guidance-and-tripwires/10-05-SUMMARY.md
FOUND: eb96c9cf
FOUND: c530525a
FOUND: 6912b940

