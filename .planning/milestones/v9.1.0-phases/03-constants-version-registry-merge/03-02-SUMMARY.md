---
phase: 03-constants-version-registry-merge
plan: 02
subsystem: api
tags: [python, pyo3, classic_version_registry, classic_settings, classic_shared]
requires:
  - phase: 03-01
    provides: Rust-side redistribution of Fallout4Version, YamlFile/settings helpers, and GameId into their semantic owner crates
provides:
  - Python bindings now expose Fallout4Version and NULL_VERSION from classic_version_registry
  - Python bindings now expose YamlFile, SETTINGS_IGNORE_NONE, and must_not_be_none from classic_settings
  - Python bindings now expose GameId from classic_shared and delete the classic_constants crate
affects: [03-03, 03-04, python-bindings, parity]
tech-stack:
  added: []
  patterns: [semantic Python module ownership, bindings-local virtualenv verification]
key-files:
  created:
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/fallout4_version.rs
    - ClassicLib-rs/python-bindings/classic-settings-py/src/yaml_file.rs
    - ClassicLib-rs/foundation/classic-shared-py/src/game_id.rs
  modified:
    - ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs
    - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs
    - ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs
    - ClassicLib-rs/Cargo.toml
key-decisions:
  - "Preserved the Python-facing NULL_VERSION contract as the string '0.0.0' in classic_version_registry instead of exposing a semver object."
  - "Exposed SETTINGS_IGNORE_NONE as a module-level Python list in classic_settings to match the pre-existing stub contract exactly."
  - "Used the bindings-local .venv for rebuild/install/import verification because rebuild_rust.ps1 installs wheels there rather than into the system interpreter."
patterns-established:
  - "Python binding redistributions should retag #[pyclass(module = ...)] to the destination semantic module and register the class in that module's #[pymodule] entrypoint."
  - "When Python smoke tests import many owner modules, verify with a full bindings rebuild so the local .venv matches the live runtime surface."
requirements-completed: [CNST-01, CNST-02, CNST-03]
duration: 9 min
completed: 2026-04-12
---

# Phase 03 Plan 02: Python constants binding redistribution Summary

**PyO3 constants wrappers now live under classic_version_registry, classic_settings, and classic_shared with classic_constants removed from the Python workspace.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-11T17:54:40-07:00
- **Completed:** 2026-04-11T18:03:11-07:00
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Added semantic Python binding modules for `Fallout4Version`, `YamlFile`, and `GameId` in their destination crates.
- Preserved the locked Python contracts for `NULL_VERSION: str` and `SETTINGS_IGNORE_NONE: list[str]` while retagging runtime module ownership.
- Migrated active Python consumers and smoke coverage off `classic_constants`, then removed `classic-constants-py` from workspace membership and disk.

## Task Commits

Each task was committed atomically:

1. **Task 1: Carve constants-py wrappers into semantic Python modules with locked contracts** - `364d9552ce6e624b64acede289a58d353f222f90` (feat)
2. **Task 2: Migrate Python consumers, rebuild scanlog bindings, and remove classic_constants** - `c058207953e1458f5fd9facc8d9e645a07b2768d` (feat)

## Files Created/Modified
- `ClassicLib-rs/python-bindings/classic-version-registry-py/src/fallout4_version.rs` - Registers `PyFallout4Version` and `NULL_VERSION` under `classic_version_registry`.
- `ClassicLib-rs/python-bindings/classic-settings-py/src/yaml_file.rs` - Registers `PyYamlFile`, `SETTINGS_IGNORE_NONE`, and `must_not_be_none` under `classic_settings`.
- `ClassicLib-rs/foundation/classic-shared-py/src/game_id.rs` - Registers `PyGameId` under `classic_shared`.
- `ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi` - Adds the redistributed version enum and `NULL_VERSION` stubs.
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` - Adds the redistributed settings enum/function/constants stubs.
- `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` - Adds the redistributed `GameId` stub.
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs` - Repoints `GameId` usage to `classic_shared_core`.
- `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` - Rewrites smoke imports and calls to the new semantic Python modules.
- `ClassicLib-rs/Cargo.toml` - Removes the `classic-constants-py` workspace member.
- `ClassicLib-rs/python-bindings/classic-constants-py/` - Deleted legacy Python constants crate.

## Decisions Made
- Preserved `NULL_VERSION` as a plain Python string because the deleted `classic_constants` contract promised `NULL_VERSION: str`.
- Preserved `SETTINGS_IGNORE_NONE` as a literal Python list to keep the existing Python-visible contract and verification assertions stable.
- Used the bindings-local virtualenv for import assertions and smoke tests because `rebuild_rust.ps1` installs rebuilt wheels there.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created the missing Python bindings virtualenv**
- **Found during:** Task 1 verification
- **Issue:** `rebuild_rust.ps1` failed because `ClassicLib-rs/python-bindings/.venv` did not exist in the isolated worktree.
- **Fix:** Created the repo-standard virtualenv with `uv venv` and installed `requirements-ci.txt` into that interpreter.
- **Files modified:** None committed
- **Verification:** Task 1 rebuild succeeded after the environment was created.
- **Committed in:** `364d9552ce6e624b64acede289a58d353f222f90` (environment-only blocker, no file changes)

**2. [Rule 3 - Blocking] Switched import assertions to the bindings-local interpreter**
- **Found during:** Task 1 verification
- **Issue:** The planned `python -c` import check used the system interpreter, which could not see wheels installed into `ClassicLib-rs/python-bindings/.venv`.
- **Fix:** Re-ran the import assertions with `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe`.
- **Files modified:** None committed
- **Verification:** The module ownership and constant-contract assertions passed in the bindings-local environment.
- **Committed in:** `364d9552ce6e624b64acede289a58d353f222f90` (verification-only blocker)

**3. [Rule 3 - Blocking] Performed a full Python bindings rebuild before the smoke test**
- **Found during:** Task 2 verification
- **Issue:** `test_promoted_residuals_smoke.py` imports many binding modules, so rebuilding only the four touched modules left `classic_database` and other existing dependencies unavailable in the worktree virtualenv.
- **Fix:** Ran a full `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` before rerunning the smoke test and negative import assertions.
- **Files modified:** None committed
- **Verification:** `154 passed` for `test_promoted_residuals_smoke.py`, no Python sources still imported `classic_constants`, and `classic_constants` was no longer importable.
- **Committed in:** `c058207953e1458f5fd9facc8d9e645a07b2768d` (verification-only blocker)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All deviations were environment/verification blockers required to make the isolated worktree validate correctly. No scope creep.

## Issues Encountered
None beyond the auto-fixed verification blockers above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Python bindings now match the three-way semantic ownership split expected by later parity and bridge work.
- Plan 03-03 can assume `classic_constants` is gone from active Python code and the shared/version/settings module names are the live contract.

## Self-Check: PASSED

- Found `.planning/phases/03-constants-version-registry-merge/03-02-SUMMARY.md`
- Verified commit `364d9552ce6e624b64acede289a58d353f222f90`
- Verified commit `c058207953e1458f5fd9facc8d9e645a07b2768d`
