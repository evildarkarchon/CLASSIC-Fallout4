---
phase: 10-docs-guidance-and-tripwires
plan: "00"
subsystem: testing
tags: [docs, guidance, tripwires, unittest, powershell]
requires:
  - phase: 06-repo-root-workspace-cutover
    provides: repo-root validation patterns and active-guidance sync precedent
  - phase: 09-clean-validation-and-ci-refresh
    provides: scoped audit structure and path-sensitive tripwire patterns
provides:
  - grouped Phase 10 planning audit constants and named target tests
  - parse-backed PowerShell wrapper-script stale-path tripwire scaffold
affects: [10-01, 10-02, 10-03, 10-04, 10-05, 10-06, 10-07, docs, skills]
tech-stack:
  added: [Python unittest, PowerShell Parser.ParseFile]
  patterns: [explicit active-surface allowlists, line-based historical-note exemptions, parse-first script tripwires]
key-files:
  created:
    - tests/planning/test_phase10_validation.py
    - tests/powershell/phase10_guidance_tripwires.test.ps1
  modified: []
key-decisions:
  - "Use named Phase 10 audit groups so later plans can target stable tests without renaming validation hooks."
  - "Scope stale-path enforcement to explicit active-surface allowlists plus line-based historical markers instead of a repo-wide ClassicLib-rs ban."
  - "Parse wrapper scripts before applying stale-path assertions so guidance tripwires fail on syntax drift as well as forbidden phrases."
patterns-established:
  - "Pattern 1: Phase docs work starts with file-backed validation scaffolds before content rewrites land."
  - "Pattern 2: Historical ClassicLib-rs mentions are allowed only on explicitly prefixed lines or per-file exemptions."
requirements-completed: [DOCS-03]
duration: 3min
completed: 2026-04-14
---

# Phase 10 Plan 00: Bootstrap validation scaffold summary

**Grouped Phase 10 audit hooks and parse-backed wrapper tripwires now exist before any active guidance rewrites begin.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-14T02:36:38Z
- **Completed:** 2026-04-14T02:39:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added a new `unittest` planning audit scaffold with explicit Phase 10 surface groups and named tests for later plans.
- Encoded the stale-path policy as explicit forbidden phrases plus line-based historical note markers and per-file exemptions.
- Added a PowerShell tripwire that parses active wrapper scripts before scanning for legacy live-root guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the grouped Phase 10 planning audit scaffold** - `707f790c` (test)
2. **Task 2: Add the wrapper-script PowerShell tripwire scaffold** - `dd85db0b` (test)

## Files Created/Modified
- `tests/planning/test_phase10_validation.py` - Groups active Phase 10 doc, skill, codebase-map, script, and sweep surfaces into stable named audit hooks.
- `tests/powershell/phase10_guidance_tripwires.test.ps1` - Parses active wrapper scripts and fails on stale `ClassicLib-rs` live-root phrases.

## Decisions Made
- Use one grouped audit file with direct test names for each later Phase 10 slice so downstream plans can target stable hooks.
- Keep stale-path enforcement narrow: explicit active-surface allowlists, explicit forbidden phrases, and exact allowed historical line prefixes.
- Include `CLAUDE.md` and `.agent` skill mirrors in the scaffold because they remain active guidance surfaces called out during review.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- PowerShell inline verification needed shell-safe command chaining in this environment; reran the parse check with PowerShell-native sequencing and verification passed.
- `docs/workspace-migration-matrix.md` was already untracked in the shared branch from parallel work and was intentionally left untouched because it is outside this plan's file list.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 10 now has stable named test hooks for top-level docs, API doc groups, agent entrypoints, repo-guide mirrors, codebase maps, and the scoped active-guidance sweep.
- Later documentation plans can update their owned files and verify against these pre-created hooks instead of waiting for a late end-of-phase audit.

## Self-Check: PASSED

- FOUND: `tests/planning/test_phase10_validation.py`
- FOUND: `tests/powershell/phase10_guidance_tripwires.test.ps1`
- FOUND commit: `707f790c`
- FOUND commit: `dd85db0b`

---
*Phase: 10-docs-guidance-and-tripwires*
*Completed: 2026-04-14*
