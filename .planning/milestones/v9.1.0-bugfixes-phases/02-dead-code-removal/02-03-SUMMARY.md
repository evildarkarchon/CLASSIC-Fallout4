---
phase: 02-dead-code-removal
plan: 03
subsystem: core
tags: [dead-code, legacy-fallback, settings-validator, scanlog, testing]

# Dependency graph
requires:
  - phase: 02-dead-code-removal
    provides: "Plans 01 and 02 completed dead code removal groundwork"
provides:
  - "scan_all_settings_legacy_bucketed method fully removed from settings_validator.rs"
  - "Legacy fallback branch replaced with empty Vec return"
  - "TEST-02 assertion test proving production configs never hit legacy fallback"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-step confidence-then-delete pattern: add assertion test first, then remove dead code"

key-files:
  created: []
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs

key-decisions:
  - "Removed orphaned has_real_buffout_module helper from settings_validator.rs (only called by deleted legacy method; orchestrator.rs has its own copy)"

patterns-established:
  - "Assertion-first deletion: prove an invariant with a test before removing the code path the invariant guards"

requirements-completed: [DEBT-09, TEST-02]

# Metrics
duration: 6min
completed: 2026-04-05
---

# Phase 2 Plan 3: Legacy Settings Fallback Removal Summary

**Assertion test proving production configs never hit legacy fallback, then scan_all_settings_legacy_bucketed method and fallback branch deleted**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-05T10:00:22Z
- **Completed:** 2026-04-05T10:06:34Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added TEST-02 assertion test verifying: default_entry has no checks (never reaches bucketed path), production entries with checks always have settings_rules defined, and rules-driven output is produced
- Deleted scan_all_settings_legacy_bucketed method (~70 lines of dead legacy code)
- Replaced fallback call with empty Vec return for entries without settings_rules
- Removed orphaned has_real_buffout_module private helper that was only used by the deleted legacy method

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TEST-02 assertion test proving production configs never hit legacy fallback** - `f6594185` (test)
2. **Task 2: Remove scan_all_settings_legacy_bucketed and fallback branch** - `4a5cd916` (refactor)

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs` - Added assertion test, deleted legacy fallback method, removed orphaned helper, replaced fallback call with empty return

## Decisions Made
- Removed `has_real_buffout_module` from settings_validator.rs since it was only called by the deleted legacy method; the orchestrator has its own separate copy of this function that remains in use

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed clippy map_flatten lint in assertion test**
- **Found during:** Task 2 (clippy verification)
- **Issue:** The assertion test used `.map(...).flatten()` instead of `.flat_map(...)`, triggering clippy::map_flatten with `-D warnings`
- **Fix:** Replaced `.map(|f| f.fragment.to_list()).flatten()` with `.flat_map(|f| f.fragment.to_list())`
- **Files modified:** ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs
- **Verification:** `cargo clippy --workspace --all-targets --all-features -- -D warnings` passes cleanly
- **Committed in:** 4a5cd916 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial style fix required by workspace lint policy. No scope creep.

## Issues Encountered
- Node parity gate (`bun run parity:gate:local`) failed due to pre-existing environment issue (`napi` CLI not installed globally). This is unrelated to the code changes in this plan -- no binding API surfaces were modified. Python parity gate passes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (dead-code-removal) is now complete: all 3 plans executed
- All DEBT-xx and TEST-02 requirements for this phase are resolved
- Ready for Phase 3 execution

## Self-Check: PASSED

- [x] settings_validator.rs exists
- [x] 02-03-SUMMARY.md exists
- [x] Commit f6594185 found (Task 1)
- [x] Commit 4a5cd916 found (Task 2)
- [x] test_production_configs_never_hit_legacy_fallback present in source
- [x] scan_all_settings_legacy_bucketed fully removed from source
- [x] Ok(Vec::new()) present as fallback return

---
*Phase: 02-dead-code-removal*
*Completed: 2026-04-05*
