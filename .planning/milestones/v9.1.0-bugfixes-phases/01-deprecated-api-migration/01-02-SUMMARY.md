---
phase: 01-deprecated-api-migration
plan: 02
subsystem: bindings
tags: [pyo3, deprecation-warning, python-bindings, scanlog, formid]

# Dependency graph
requires:
  - phase: none
    provides: n/a
provides:
  - Python parse_segments_parallel delegated to parse_all_sections_arc returning dict
  - Python generate_suspect_section delegated to header + footer replacement methods
  - PyFormIDAnalyzerCore emits DeprecationWarning for legacy PyDict mods_single
  - pytest.warns(DeprecationWarning) test coverage for all three migrated methods
  - Updated .pyi stub and API docs reflecting new return types
affects: [02-dead-code-removal]

# Tech tracking
tech-stack:
  added: []
  patterns: [PyErr::warn with c-string literal for DeprecationWarning emission in PyO3 0.27]

key-files:
  created:
    - .planning/phases/01-deprecated-api-migration/01-02-SUMMARY.md
  modified:
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
    - ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py
    - docs/api/classic-scanlog-core.md

key-decisions:
  - "Use #[allow(unused_variables)] instead of underscore prefix for chunk_size param -- PyO3 signature attribute requires matching Rust parameter name"
  - "ReportGenerator test uses default constructor (new()) rather than from_config -- simpler and sufficient for deprecation warning validation"
  - "Parity artifacts regenerated and committed to reflect updated API surface"

patterns-established:
  - "PyErr::warn pattern: use c-string literal message, stacklevel=1, py.get_type::<PyDeprecationWarning>() for category"

requirements-completed: [DEBT-05, DEBT-06, DEBT-10]

# Metrics
duration: 15min
completed: 2026-04-05
---

# Phase 01 Plan 02: Migrate Python Binding Deprecated API Callers Summary

**Three Python binding methods migrated off deprecated scanlog-core APIs with DeprecationWarning emission via PyO3 PyErr::warn, pytest coverage, and updated .pyi/API docs**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-05T08:29:36Z
- **Completed:** 2026-04-05T08:44:42Z
- **Tasks:** 3/3
- **Files modified:** 9 (3 Rust sources, 1 .pyi stub, 1 test file, 1 API doc, 3 parity artifacts)

## Accomplishments
- Migrated parse_segments_parallel from deprecated core API to parse_all_sections_arc, changing return type from list[list[str]] to dict[str, list[str]]
- Migrated generate_suspect_section to delegate to generate_suspect_section_header + generate_suspect_found_footer replacement methods
- Added DeprecationWarning to PyFormIDAnalyzerCore::new when receiving legacy PyDict for mods_single
- All three methods emit explicit DeprecationWarning with replacement API names via PyErr::warn
- Three pytest.warns(DeprecationWarning) tests verify actual warning emission (Nyquist compliance)
- Python parity gate passes, cargo clippy clean with -D warnings

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate parse_segments_parallel, generate_suspect_section, and FormID constructor** - `57ef843a` (feat)
2. **Task 2: Add DeprecationWarning emission tests for migrated methods** - `8c136b79` (test)
3. **Task 3: Update .pyi stub, API docs, and run parity gates** - `ca5dd5a8` (docs)

## Files Created/Modified
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs` - Rewired parse_segments_parallel to parse_all_sections_arc with dict return and deprecation warning
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` - Rewired generate_suspect_section to header+footer with deprecation warning
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs` - Added deprecation warning for legacy PyDict mods_single parameter
- `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` - Updated return type and added deprecation notices
- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` - Three new deprecation warning tests
- `docs/api/classic-scanlog-core.md` - Updated deprecated parser APIs section and contributor notes

## Decisions Made
- Used `#[allow(unused_variables)]` on chunk_size parameter instead of underscore prefix because PyO3 signature attribute requires matching Rust parameter name
- Used `ReportGenerator::new()` (default constructor) in deprecation test rather than constructing from AnalysisConfig -- simpler and sufficient for verifying warning emission
- Committed regenerated parity artifacts alongside the .pyi and doc changes to keep them in sync

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PyO3 signature/parameter name mismatch**
- **Found during:** Task 1 (parser.rs migration)
- **Issue:** Renaming chunk_size to _chunk_size caused PyO3 signature attribute error: "expected argument from function definition _chunk_size but got argument chunk_size"
- **Fix:** Used `#[allow(unused_variables)] chunk_size` instead of `_chunk_size` to keep the PyO3 signature happy
- **Files modified:** ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs
- **Verification:** cargo build -p classic-scanlog-py succeeds
- **Committed in:** 57ef843a (Task 1 commit)

**2. [Rule 1 - Bug] Removed unused PyString import**
- **Found during:** Task 1 (parser.rs migration)
- **Issue:** After migration, PyString was no longer used in parser.rs (clippy would warn)
- **Fix:** Removed PyString from the import line
- **Files modified:** ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs
- **Verification:** cargo clippy -p classic-scanlog-py -- -D warnings clean
- **Committed in:** 57ef843a (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- Two pre-existing test failures in config-tier1-smoke and scanlog-tier1-smoke due to APPDATA path resolution in fresh worktree venv (resolves to pytest.exe path). Not related to plan changes. All 22 non-failing tests pass including the 3 new deprecation warning tests.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEBT-05, DEBT-06, DEBT-10 are complete
- Phase 2 (Dead Code Removal) can now safely delete deprecated parse_segments, parse_segments_parallel, and is_outdated methods since all callers are migrated
- The deprecated attribute on the core methods can be changed to deny in Phase 2

## Self-Check: PASSED

All 7 key files verified present. All 3 task commit hashes verified in git log.

---
*Phase: 01-deprecated-api-migration*
*Completed: 2026-04-05*
