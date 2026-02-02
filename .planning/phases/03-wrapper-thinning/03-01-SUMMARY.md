---
phase: 03-wrapper-thinning
plan: 01
subsystem: integration-rust-wrappers
tags: [file-io, wrapper-thinning, refactor, python-rust]
requires:
  - phase-02 (integration layer simplification)
provides:
  - thin FileIOCore wrapper pattern (template for remaining wrappers)
  - removed SyncWrapper, convenience functions, exception tuple construction
affects:
  - 03-02 (parser_rust thinning follows same pattern)
  - phase-05 (fallback pruning will remove Python fallback paths)
tech-stack:
  added: []
  patterns: [thin-delegation-wrapper]
key-files:
  created: []
  modified:
    - ClassicLib/integration/rust/file_io_rust.py
    - ClassicLib/integration/rust/__init__.py
    - tests/rust_integration/wrappers/test_file_io_rust_wrapper_unit.py
key-decisions:
  - Keep Python fallback paths for walk_directory and read_dds_header (needed until Phase 5)
  - Trailing line strip in read_crash_log stays in Python (simple inline logic, not worth Rust migration)
  - Extension conversion in write_crash_report stays in Python (same reasoning)
duration: ~8m
completed: 2026-02-02
---

# Phase 3 Plan 1: FileIOCore Wrapper Thinning Summary

Reduced file_io_rust.py from 937 lines to 230 lines (75% reduction) by eliminating SyncWrapper, convenience functions, verbose docstrings, and exception tuple construction while preserving identical behavior.

## Performance

- **Duration:** ~8 minutes
- **Started:** 2026-02-02T10:16:48Z
- **Completed:** 2026-02-02
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

1. Thinned FileIOCore wrapper from 937 to 230 lines (75% reduction)
2. Every method follows 3-5 line delegation pattern: convert args, call Rust, convert return
3. Removed SyncWrapper inner class (no production callers, only test usage)
4. Removed `create_file_io_sync()` and `get_rust_file_io()` convenience functions
5. Removed `_ensure_path()`, `_get_rust_exception_types()`, and module-level exception tuples
6. Updated `__init__.py` to remove convenience function exports
7. Updated test suite: 32 tests pass (removed 5 tests for eliminated code)
8. Full test suite: 1893 passed, 17 skipped, 0 failures
9. Rust workspace: all tests pass

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Thin file_io_rust.py + update __init__.py | c9aebcf4 | file_io_rust.py, __init__.py |
| 2 | Update tests + verify regression suite | 3e1def19 | test_file_io_rust_wrapper_unit.py |

## Files Modified

- `ClassicLib/integration/rust/file_io_rust.py` -- 937 -> 230 lines (75% reduction)
- `ClassicLib/integration/rust/__init__.py` -- removed convenience function imports/exports
- `tests/rust_integration/wrappers/test_file_io_rust_wrapper_unit.py` -- 566 -> 418 lines, removed dead tests

## Decisions Made

1. **230 lines vs 200 target**: The 30 excess lines are Python fallback paths for `walk_directory` (recursive traversal) and `read_dds_header` (DDS processor instantiation). These are irreducible fallback logic preserved for Phase 5.
2. **No Rust migration needed**: `read_crash_log` trailing strip and `write_crash_report` extension conversion are trivial inline operations (2-3 lines each), not worth Rust-side migration.
3. **Direct exception imports**: Replaced `_get_rust_exception_types()` and module-level tuple construction with direct `(RustError, RustIOError, RustParseError)` in except clauses.

## Deviations from Plan

None -- plan executed exactly as written.

## Issues

None.

## Next Phase Readiness

Pattern established for thinning remaining wrappers. The delegation pattern (convert args -> call Rust -> convert return) is consistent and can be applied to parser_rust.py, formid_rust.py, etc.
