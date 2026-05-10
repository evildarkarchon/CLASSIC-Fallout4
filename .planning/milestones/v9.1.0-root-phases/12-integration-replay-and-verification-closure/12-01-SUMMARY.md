---
phase: 12-integration-replay-and-verification-closure
plan: "01"
subsystem: testing
tags: [python-bindings, replay, verification, powershell, pytest]
requires:
  - phase: 09-clean-validation-and-ci-refresh
    provides: Phase 9 clean harness, audit contract, and replay validation surfaces.
provides:
  - Durable clean-state bootstrap for python-bindings/.venv before wrapper replay.
  - Stronger Phase 9 audit and pytest guards for replayability and residue-free proof order.
affects: [phase-08-verification, phase-09-verification, milestone-audit]
tech-stack:
  added: []
  patterns: [bindings-local uv bootstrap before wrapper replay, ordered proof-step assertions for clean replay]
key-files:
  created: [.planning/phases/12-integration-replay-and-verification-closure/12-01-SUMMARY.md]
  modified:
    - tests/planning/phase09_clean_run.ps1
    - tests/planning/test_phase09_validation.py
    - .planning/phases/09-clean-validation-and-ci-refresh/09-CLEAN-VALIDATION-AUDIT.md
key-decisions:
  - "Keep rebuild_rust.ps1 fail-fast on a missing python-bindings/.venv and instead recreate the bindings-local environment inside the clean proof harness."
  - "Run the clean proof with an isolated temporary CARGO_TARGET_DIR plus retryable cleanup so wrapper replay proof survives locked local target output without recreating ClassicLib-rs residue."
patterns-established:
  - "Phase 9 clean replay proofs must bootstrap python-bindings/.venv with uv before Python wrapper commands run."
  - "Planning audits and pytest ordering checks should describe the same proof-step sequence verbatim."
requirements-completed: [INTG-01, INTG-04]
duration: 1h 15m
completed: 2026-04-15
---

# Phase 12 Plan 01: integration replay and verification closure Summary

**Phase 9 clean proof now recreates the bindings-local virtualenv before replaying rebuild_rust.ps1, with matching audit and pytest guards for residue-free wrapper replay.**

## Performance

- **Duration:** 1h 15m
- **Started:** 2026-04-15T01:17:15Z
- **Completed:** 2026-04-15T02:32:18Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Repaired the Phase 9 clean harness so it recreates `python-bindings/.venv` before Python wrapper replay.
- Recorded the repaired bootstrap and residue expectations in `09-CLEAN-VALIDATION-AUDIT.md`.
- Tightened `test_phase09_validation.py` so regressions in proof ordering or wrapper replay bootstrap fail immediately.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild the Python binding environment inside the clean-proof harness** - `7409b3ad` (fix)
2. **Task 2: Tighten the Phase 9 audit to prove replayability instead of one-shot success** - `a8768cb5` (test)

**Plan metadata:** Recorded in the final docs commit for this plan.

## Files Created/Modified
- `tests/planning/phase09_clean_run.ps1` - Recreates the bindings-local virtualenv, replays the Python wrapper, and protects the proof run with retryable cleanup plus isolated target output.
- `tests/planning/test_phase09_validation.py` - Verifies the bootstrap commands and proof order required for durable clean replay.
- `.planning/phases/09-clean-validation-and-ci-refresh/09-CLEAN-VALIDATION-AUDIT.md` - Documents the repaired replay contract and residue expectations.
- `.planning/phases/12-integration-replay-and-verification-closure/12-01-SUMMARY.md` - Records plan execution, decisions, and verification evidence.

## Decisions Made
- Kept `rebuild_rust.ps1` unchanged as the authoritative fail-fast gate for missing `python-bindings/.venv`; the fix belongs in the clean harness bootstrap instead of adding compatibility fallback.
- Matched the audit prose and pytest assertions to the same ordered proof sequence so future replay regressions are caught by both human and automated review.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Isolated the clean proof Cargo output and added retryable cleanup**
- **Found during:** Task 1 (Rebuild the Python binding environment inside the clean-proof harness)
- **Issue:** Clean proof cleanup can hit transient Windows file locks on repo-root `target`, which would block the repaired wrapper replay proof even though the plan only asked for venv bootstrap.
- **Fix:** Added a proof-local `target.phase09-proof`, retryable filesystem cleanup, and locked-target fallback handling while preserving the targeted-clean contract and legacy residue checks.
- **Files modified:** `tests/planning/phase09_clean_run.ps1`, `.planning/phases/09-clean-validation-and-ci-refresh/09-CLEAN-VALIDATION-AUDIT.md`
- **Verification:** `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1`
- **Committed in:** `7409b3ad`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The auto-fix kept the requested replay repair durable on Windows without broadening scope beyond the Phase 9 proof harness.

## Issues Encountered
- The clean proof now touches heavyweight parity and packaging commands, so replay durability needed target-isolation and cleanup retries to avoid transient Windows lock failures.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 9 replayability evidence for `INTG-01` and `INTG-04` is now committed and executable.
- Phase 12 can continue into verification-file closure work for the remaining orphaned integration requirements.

## Self-Check: PASSED

- Verified summary and touched proof files exist on disk.
- Verified task commits `7409b3ad` and `a8768cb5` exist in git history.

---
*Phase: 12-integration-replay-and-verification-closure*
*Completed: 2026-04-15*
