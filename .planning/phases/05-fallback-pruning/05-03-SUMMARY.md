---
phase: 05-fallback-pruning
plan: 03
subsystem: integration
tags: [rust, validation, pyinstaller, spec-cleanup, startup]

# Dependency graph
requires:
  - phase: 05-fallback-pruning/02
    provides: All Python fallbacks removed, integration/python/ deleted
provides:
  - Startup Rust module validation in both entry points
  - Clean PyInstaller spec files (no stale hiddenimports)
  - Verified PyInstaller build succeeds and executable launches
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "validate_rust_modules() fail-fast at startup"
    - "collect_all('pyffi') for VERSION file bundling"

key-files:
  created: []
  modified:
    - ClassicLib/integration/factory.py
    - CLASSIC_Interface.py
    - CLASSIC_ScanLogs.py
    - CLASSIC.spec
    - CLASSIC-CLI.spec
    - CLASSIC-GUI-OneFile.spec
    - CLASSIC-QML.spec
    - CLASSIC-QML-Dir.spec
    - CLASSIC-Test.spec

key-decisions:
  - "validate_rust_modules() checks 6 Rust modules: LogParser, PluginAnalyzer, RecordScanner, ReportGenerator, FileIOCore, YamlOperations"
  - "Validation placed in factory.py alongside existing detect_component()"
  - "pyffi VERSION file bundled via collect_all('pyffi') in all 6 spec files (pre-existing packaging gap)"

patterns-established:
  - "Startup validation: entry points call validate_rust_modules() before any other initialization"

# Metrics
duration: 18min
completed: 2026-02-02
---

# Phase 5 Plan 3: Startup Validation + Spec Cleanup Summary

**Added startup Rust module validation, cleaned spec files, verified PyInstaller build**

## Performance

- **Duration:** 18 min (including checkpoint wait)
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 9

## Accomplishments
- Created `validate_rust_modules()` in factory.py that checks all 6 required Rust modules at startup
- Wired validation into both entry points (CLASSIC_Interface.py, CLASSIC_ScanLogs.py)
- Cleaned 3 stale hiddenimports from all 6 spec files (config, status, detector from Phase 2)
- Fixed pre-existing pyffi VERSION file packaging gap (collect_all('pyffi') added to all 6 specs)
- PyInstaller build verified: executable launches GUI without errors

## Task Commits

1. **Task 1: Add startup validation and clean spec files** - `1a6039eb` (feat)
2. **Task 2: PyInstaller build and smoke test** - Human-verified ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pyffi VERSION file missing in PyInstaller bundle**
- **Found during:** Task 2 (PyInstaller build verification)
- **Issue:** pyffi reads a VERSION file at import time; PyInstaller doesn't auto-bundle it
- **Fix:** Added collect_all('pyffi') to all 6 spec files
- **Files modified:** All 6 *.spec files
- **Committed in:** ba4c9f0a

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Pre-existing packaging gap, not a Phase 5 regression. Fix required for build to work.

## Issues Encountered
None beyond the pyffi packaging gap (pre-existing).

## User Setup Required
None.

## Next Phase Readiness
- Phase 5 complete: all 3 plans executed
- Ready for phase verification

---
*Phase: 05-fallback-pruning*
*Completed: 2026-02-02*
