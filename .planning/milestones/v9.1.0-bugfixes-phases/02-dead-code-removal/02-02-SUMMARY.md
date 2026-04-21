---
phase: 02-dead-code-removal
plan: 02
subsystem: core
tags: [dead-code, yaml, scanlog, pyo3, cleanup]

# Dependency graph
requires:
  - phase: 01-deprecated-api-migration
    provides: "All deprecated callers migrated, safe to remove dead code"
provides:
  - "YamlFormatConfig struct fully removed from classic-yaml-core"
  - "PluginAnalyzer.case_cache field removed from classic-scanlog-core"
  - "PyGpuDetector converted to stateless unit struct in classic-scanlog-py"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unit struct pattern for stateless PyO3 wrappers"

key-files:
  created: []
  modified:
    - ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs
    - ClassicLib-rs/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs

key-decisions:
  - "Renamed yaml_config_benchmarks to yaml_operations_benchmarks since config variants no longer exist"

patterns-established:
  - "Stateless unit struct for PyO3 wrappers when inner field serves no purpose"

requirements-completed: [DEBT-02, DEBT-03, DEBT-04]

# Metrics
duration: 9min
completed: 2026-04-05
---

# Phase 2 Plan 2: Dead Struct/Field Removal Summary

**Removed YamlFormatConfig struct, PluginAnalyzer.case_cache field, and converted PyGpuDetector to stateless unit struct across three crates**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-05T09:33:50Z
- **Completed:** 2026-04-05T09:43:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Deleted YamlFormatConfig struct, Default impl, with_config() method, format_config field, and all test/benchmark/doc references from classic-yaml-core
- Removed PluginAnalyzer.case_cache field with unused DashMap/Arc imports from classic-scanlog-core
- Converted PyGpuDetector from wrapper struct to stateless unit struct in classic-scanlog-py
- Eliminated all #[allow(dead_code)] annotations from the three modified files
- Full workspace builds, tests, and clippy pass cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete YamlFormatConfig struct and all cascade references** - `4b4a1470` (chore)
2. **Task 2: Remove PluginAnalyzer.case_cache and convert PyGpuDetector to stateless** - `00ee05bf` (chore)

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` - Removed YamlFormatConfig struct, Default impl, format_config field, with_config() method, and related tests
- `ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs` - Removed YamlFormatConfig import and test_custom_format_config test
- `ClassicLib-rs/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs` - Removed YamlFormatConfig import, simplified config variant benchmarks to yaml_operations_benchmarks
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs` - Removed case_cache field, unused DashMap/Arc imports
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs` - Converted PyGpuDetector to unit struct, simplified Default and constructor

## Decisions Made
- Renamed yaml_config_benchmarks to yaml_operations_benchmarks since config variant comparison is no longer meaningful
- Kept DashMap as a crate dependency for classic-scanlog-core since it is used in parser.rs, formid.rs, report.rs, and patterns.rs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all changes are deletions/simplifications with no new stubs introduced.

## Next Phase Readiness
- Dead struct/field removal complete for DEBT-02, DEBT-03, DEBT-04
- Ready for 02-03 plan (remaining dead code removal tasks in phase 2)

## Self-Check: PASSED

- All 5 modified files confirmed present
- Both task commits (4b4a1470, 00ee05bf) confirmed in git history
- SUMMARY.md file confirmed present

---
*Phase: 02-dead-code-removal*
*Completed: 2026-04-05*
