---
phase: 10-docs-guidance-and-tripwires
plan: "09"
subsystem: docs
tags: [planning, docs, codebase-maps, repo-root, validation]
requires:
  - phase: 10-00
    provides: Phase 10 planning audit scaffold and stale-path tripwires.
  - phase: 10-01
    provides: Shared workspace migration matrix and top-level root-path guidance.
provides:
  - Repo-root codebase maps for structure, stack, architecture, integrations, conventions, testing, and concerns.
  - Phase 10 audit coverage for all active `.planning/codebase/*.md` maps.
affects: [phase-10-verification, agent-guidance, planning-docs]
tech-stack:
  added: []
  patterns: [Repo-root documentation contract, file-backed planning audit coverage]
key-files:
  created: []
  modified:
    - .planning/codebase/STRUCTURE.md
    - .planning/codebase/STACK.md
    - .planning/codebase/ARCHITECTURE.md
    - .planning/codebase/INTEGRATIONS.md
    - .planning/codebase/CONVENTIONS.md
    - .planning/codebase/TESTING.md
    - .planning/codebase/CONCERNS.md
    - tests/planning/test_phase10_validation.py
key-decisions:
  - "Treat all seven active `.planning/codebase/*.md` files as one audited guidance surface in `test_phase10_validation.py`."
  - "Keep `ClassicLib-rs/` mentions in codebase maps only for clearly labeled residue context such as legacy `ClassicLib-rs/target/`."
patterns-established:
  - "Codebase maps use repo-root commands and paths, with no live workspace-root `ClassicLib-rs` instruction flow."
  - "Phase 10 codebase-map coverage expands by editing the single `ACTIVE_CODEBASE_MAPS` allowlist."
requirements-completed: [DOCS-01, DOCS-03]
duration: 4min
completed: 2026-04-14
---

# Phase 10 Plan 09: Codebase maps summary

**Repo-root structure, workflow, and risk maps now teach the moved live tree and are locked into the Phase 10 planning audit.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T02:51:39Z
- **Completed:** 2026-04-14T02:55:54Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Rewrote the structure, stack, architecture, and integrations maps to reference the repo-root workspace shell and root-level crate layers.
- Updated conventions, testing, and concerns guidance so examples, commands, test locations, and fragile-area references use the moved live tree.
- Expanded the Phase 10 validation allowlist so all seven active codebase maps are covered by `test_phase10_validation.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update the structure, stack, architecture, and integrations maps** - `341172d8` (docs)
2. **Task 2: Update the conventions, testing, and concerns maps** - `422b7440` (docs)

_Plan metadata commit pending after state updates._

## Files Created/Modified
- `.planning/codebase/STRUCTURE.md` - Rebased the repo layout map to the live root-level crate directories and residue-only legacy notes.
- `.planning/codebase/STACK.md` - Repointed stack, runtime, dependency, and configuration references to `Cargo.toml`, `Cargo.lock`, and root-level binding paths.
- `.planning/codebase/ARCHITECTURE.md` - Updated layer, data-flow, and entrypoint references to the moved repo-root Rust tree.
- `.planning/codebase/INTEGRATIONS.md` - Rebased external integration ownership and environment references to root-level crates and manifests.
- `.planning/codebase/CONVENTIONS.md` - Updated naming, linting, import, and module examples to the repo-root tree.
- `.planning/codebase/TESTING.md` - Replaced stale manifest-path commands and binding paths with repo-root command guidance and current test locations.
- `.planning/codebase/CONCERNS.md` - Refreshed fragile-area and hotspot references to the moved live tree.
- `tests/planning/test_phase10_validation.py` - Expanded `ACTIVE_CODEBASE_MAPS` so all seven maintained codebase maps are covered by the Phase 10 audit.

## Decisions Made
- Treat the codebase-map surface as a single audited allowlist in `ACTIVE_CODEBASE_MAPS` so future Phase 10 regressions fail in one place.
- Keep any remaining `ClassicLib-rs` references in codebase maps explicitly residue-only rather than teaching dual live workspace roots.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added missing Phase 10 audit coverage for integrations and concerns maps**
- **Found during:** Task 1
- **Issue:** `test_phase10_validation.py` only audited five codebase maps, which left `INTEGRATIONS.md` and `CONCERNS.md` outside the plan's required regression scaffold.
- **Fix:** Expanded `ACTIVE_CODEBASE_MAPS` to cover all seven active codebase map files.
- **Files modified:** `tests/planning/test_phase10_validation.py`
- **Verification:** `python -m pytest tests/planning/test_phase10_validation.py -q -k "codebase_maps_contract"`
- **Committed in:** `341172d8`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The deviation closed an audit gap required by the plan and did not expand scope beyond the owned codebase-map surface.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The `.planning/codebase/*.md` agent-consumed maps now match the repo-root workspace contract.
- Phase 10 verification can rely on the expanded `ACTIVE_CODEBASE_MAPS` list for future stale-guidance regressions.

## Self-Check: PASSED

- FOUND: `.planning/phases/10-docs-guidance-and-tripwires/10-09-SUMMARY.md`
- FOUND: `341172d8`
- FOUND: `422b7440`

---
*Phase: 10-docs-guidance-and-tripwires*
*Completed: 2026-04-14*
