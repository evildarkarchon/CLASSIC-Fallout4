---
phase: 02-dead-code-removal
plan: 01
subsystem: scanlog
tags: [dead-code, deprecated-api, parser, version, rust]

# Dependency graph
requires:
  - phase: 01-deprecated-api-migration
    provides: All deprecated API callers migrated to current APIs
provides:
  - parse_segments, parse_segments_parallel, is_outdated methods deleted from scanlog-core
  - SEGMENT_BOUNDARIES static, fast_contains method, named_sections_to_positional helper deleted
  - 3 deprecated shim tests migrated to parse_all_sections_arc with segment_key constants
affects: [02-dead-code-removal, binding-parity]

# Tech tracking
tech-stack:
  added: []
  patterns: [test-migration-before-deletion, segment_key-constants-in-tests]

key-files:
  created: []
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs

key-decisions:
  - "Removed unused memchr::{memchr, memmem} import after fast_contains deletion (only consumer)"
  - "Kept once_cell::sync::Lazy import -- still used by COMMON_PATTERNS and CRASHGEN_HEADER_PATTERN"

patterns-established:
  - "Module-level segment_key import in test module for cleaner test assertions"

requirements-completed: [DEBT-01, DEBT-08]

# Metrics
duration: 11min
completed: 2026-04-05
---

# Phase 02 Plan 01: Scanlog Deprecated Method and Dead Code Removal Summary

**Migrated 3 deprecated shim tests to parse_all_sections_arc, then deleted parse_segments, parse_segments_parallel, is_outdated, SEGMENT_BOUNDARIES, fast_contains, and named_sections_to_positional from scanlog-core**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-05T09:46:48Z
- **Completed:** 2026-04-05T09:58:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Migrated 3 deprecated test shims to use parse_all_sections_arc with segment_key constants, preserving coverage for basic segmentation, patches-in-settings, and XSE module slot preservation behaviors
- Deleted 6 dead/deprecated items from parser.rs: SEGMENT_BOUNDARIES static, named_sections_to_positional helper, parse_segments, parse_segments_parallel, and fast_contains
- Deleted is_outdated deprecated method from version.rs
- Workspace builds, tests (342 total), and clippy all pass cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate deprecated shim tests to parse_all_sections_arc** - `379bbc46` (refactor)
2. **Task 2: Delete deprecated methods, dead code, and is_outdated** - `24925a48` (refactor)

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` - Migrated 3 tests, deleted SEGMENT_BOUNDARIES, named_sections_to_positional, parse_segments, parse_segments_parallel, fast_contains, and unused memchr imports
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` - Deleted is_outdated deprecated method with doc examples

## Decisions Made
- Removed `memchr::{memchr, memmem}` import since `fast_contains` was its only consumer -- workspace `unused-imports` lint would error otherwise
- Kept `once_cell::sync::Lazy` import as it is still used by `COMMON_PATTERNS` and `CRASHGEN_HEADER_PATTERN` statics

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed unused memchr imports**
- **Found during:** Task 2 (dead code deletion)
- **Issue:** Deleting `fast_contains` left `memchr::{memchr, memmem}` as unused imports, which fails the workspace `unused-imports = "deny"` lint
- **Fix:** Removed the `use memchr::{memchr, memmem};` import line
- **Files modified:** ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs
- **Verification:** `cargo build --workspace` and `cargo clippy --workspace` pass cleanly
- **Committed in:** 24925a48 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Import cleanup was necessary for compilation. No scope creep.

## Issues Encountered
- Transient Windows linker error (LNK1105: cannot close file) on first test run; resolved on retry. Not related to code changes.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code paths are fully wired.

## Next Phase Readiness
- parser.rs and version.rs are clean of deprecated methods and dead code
- Remaining 02-dead-code-removal plans (02-02 YamlFormatConfig/PluginAnalyzer/PyGpuDetector, 02-03 legacy fallback) can proceed independently
- Python binding `parse_segments_parallel` shim still exists in classic-scanlog-py as a separate deprecation concern (calls parse_all_sections_arc internally, not the deleted core method)

---
*Phase: 02-dead-code-removal*
*Completed: 2026-04-05*

## Self-Check: PASSED
- parser.rs: FOUND
- version.rs: FOUND
- 02-01-SUMMARY.md: FOUND
- Commit 379bbc46: FOUND
- Commit 24925a48: FOUND
