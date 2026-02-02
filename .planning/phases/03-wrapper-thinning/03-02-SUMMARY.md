---
phase: 03-wrapper-thinning
plan: 02
subsystem: integration-wrappers
tags: [rust, python, wrapper, parser, formid, thinning]
requires:
  - phase-02 (integration layer simplification)
provides:
  - thin parser_rust.py (122 lines, delegation-only)
  - thin formid_rust.py (128 lines, delegation-only)
  - updated formid wrapper tests
affects:
  - phase-04 (further wrapper thinning of remaining wrappers)
  - phase-05 (fallback pruning -- wrappers now minimal)
tech-stack:
  added: []
  patterns:
    - thin delegation wrapper (Rust try -> Python fallback)
    - module-level boundary template constants
    - always-init Python analyzer for methods without Rust binding
key-files:
  created: []
  modified:
    - ClassicLib/integration/rust/parser_rust.py
    - ClassicLib/integration/rust/formid_rust.py
    - tests/rust_integration/wrappers/test_formid_rust_wrapper_unit.py
key-decisions:
  - "formid_match delegates to Python always (no Rust PyO3 binding for async formid_match)"
  - "Python analyzer always initialized in formid wrapper (needed for formid_match)"
  - "Segment boundaries extracted as module-level template in parser wrapper"
duration: 10m
completed: 2026-02-02
---

# Phase 3 Plan 2: Parser + FormID Wrapper Thinning Summary

Thinned parser_rust.py and formid_rust.py from 321/326 lines to 122/128 lines respectively, eliminating hasattr feature detection, MD5 caching, multi-path initialization, legacy FFI paths, and exception tuple construction.

## Performance

| Metric | Value |
|--------|-------|
| Duration | 10m |
| Started | 2026-02-02T10:18:26Z |
| Completed | 2026-02-02T10:28:26Z |
| Tasks | 2/2 |
| Files modified | 3 |

## Accomplishments

1. **parser_rust.py**: 321 -> 122 lines (62% reduction)
   - Removed `_parse_crash_header` static method (already in Rust `parse_complete`)
   - Removed `hasattr(self._rust_parser, "parse_complete")` feature detection
   - Removed legacy multi-call FFI path (7+ Python-Rust crossings)
   - Removed `_get_rust_exception_types()` tuple constructor
   - Extracted segment boundaries as module-level template constant

2. **formid_rust.py**: 326 -> 128 lines (61% reduction)
   - Removed multi-path init (`FormIDAnalyzerCore` vs `FormIDAnalyzer` via hasattr)
   - Removed MD5 plugin cache key (`hashlib.md5` for cache invalidation)
   - Removed hasattr for `extract_formids_nocopy`, `cache_plugins`, `process_formids_cached`
   - Removed on-demand Python analyzer creation pattern
   - Always initializes Python analyzer (needed for `formid_match`, no Rust binding)

3. **Tests updated**: Removed plugin caching tests, added Python analyzer initialization test

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 4eb68e02 | Thin parser_rust.py to 122 lines |
| 2 | 200eeecf | Thin formid_rust.py to 128 lines, update tests |

## Decisions Made

1. **formid_match always Python**: The Rust PyO3 bindings don't expose `formid_match` (it's async in Rust core with database pool). The Python analyzer always handles matching.
2. **Python analyzer always init**: Since `formid_match` always needs Python, initialize it upfront rather than lazily.
3. **Segment boundary template**: Extracted as module-level constant with `{xse}` placeholder, resolved at call time.

## Deviations from Plan

None -- plan executed exactly as written.

## Issues

None.

## Next Phase Readiness

- Both scanlog wrapper files now under 150 lines
- Pattern established: thin delegation (try Rust, catch errors, fallback to Python)
- Remaining wrappers in Phase 3 can follow identical pattern
- No blockers for continuing Phase 3
