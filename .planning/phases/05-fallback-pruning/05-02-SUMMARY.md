---
phase: 05-fallback-pruning
plan: 02
subsystem: integration
tags: [rust, pyo3, fallback-removal, factory-pattern, parser, mod-detector, plugin-analyzer]

# Dependency graph
requires:
  - phase: 05-01
    provides: "Easy fallback files removed, RuntimeError pattern for 4 factory functions"
provides:
  - "integration/python/ directory completely eliminated"
  - "3 hard fallback files removed (parser_py, mod_detector_py, plugin_py)"
  - "3 rust wrappers cleaned of all fallback import paths"
  - "PythonParserWrapper removed from factory.py"
  - "7 factory functions now use RuntimeError pattern (parser, plugin, mod_detector + 4 from 05-01)"
affects: [05-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hard-error pattern: all factory functions raise RuntimeError when Rust unavailable"
    - "Rust wrappers propagate errors via RuntimeError wrapping instead of silent fallback"

key-files:
  created: []
  modified:
    - "ClassicLib/integration/factory.py"
    - "ClassicLib/integration/rust/parser_rust.py"
    - "ClassicLib/integration/rust/mod_detector_rust.py"
    - "ClassicLib/integration/rust/plugin_rust.py"
    - "ClassicLib/integration/types.py"

key-decisions:
  - "RuntimeError wrapping for Rust errors in wrappers (rather than re-raising originals)"
  - "parser_rust.py raises RuntimeError on init if Rust unavailable (fail-fast)"
  - "plugin_rust.py raises RuntimeError on init if Rust unavailable (fail-fast)"
  - "mod_detector_rust.py raises RuntimeError if individual Rust functions unavailable"

patterns-established:
  - "Fail-fast initialization: wrappers raise RuntimeError in __init__ if Rust unavailable"
  - "Error propagation: wrapper methods wrap Rust errors in RuntimeError"

# Metrics
duration: 24min
completed: 2026-02-02
---

# Phase 5 Plan 2: Hard Fallback Removal Summary

**Removed 3 hard Python fallback files (parser_py, mod_detector_py, plugin_py), deleted integration/python/ directory, cleaned 3 rust wrappers of 9 fallback import sites**

## Performance

- **Duration:** 24 min
- **Started:** 2026-02-03T00:15:40Z
- **Completed:** 2026-02-03T00:40:05Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Deleted all 3 remaining Python fallback files (parser_py.py, mod_detector_py.py, plugin_py.py)
- Eliminated ClassicLib/integration/python/ directory entirely
- Eliminated tests/python_fallback/ directory entirely
- Removed PythonParserWrapper class from factory.py
- Converted get_parser(), get_plugin_analyzer(), get_mod_detector() to RuntimeError pattern
- Cleaned 9 fallback import sites across 3 rust wrapper files

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove parser_py.py and mod_detector_py.py** - `6cc34e97` (feat)
2. **Task 2: Remove plugin_py.py and delete integration/python/ directory** - `8074d87b` (feat)

## Files Created/Modified
- `ClassicLib/integration/factory.py` - Removed PythonParserWrapper, converted 3 factory functions to RuntimeError
- `ClassicLib/integration/rust/parser_rust.py` - Removed fallback, fail-fast init, RuntimeError on error
- `ClassicLib/integration/rust/mod_detector_rust.py` - Removed 3 fallback import sites, RuntimeError pattern
- `ClassicLib/integration/rust/plugin_rust.py` - Removed 5 fallback import sites, fail-fast init
- `ClassicLib/integration/types.py` - Updated LogParserProtocol docstring
- `tests/integration/test_factory_parsers_unit.py` - Rewrote for RuntimeError pattern
- `tests/integration/test_factory_analyzers_unit.py` - Updated plugin test for RuntimeError
- `tests/rust_integration/e2e/test_pipeline_e2e.py` - Removed Rust-vs-Python consistency test (Python gone)
- `tests/rust_integration/ffi/test_ffi_error_conditions_integration.py` - Updated exception expectations
- `tests/rust_integration/wrappers/test_plugin_rust_wrapper_unit.py` - Updated fallback tests to RuntimeError

### Deleted Files
- `ClassicLib/integration/python/parser_py.py`
- `ClassicLib/integration/python/mod_detector_py.py`
- `ClassicLib/integration/python/plugin_py.py`
- `ClassicLib/integration/python/__init__.py`
- `tests/python_fallback/test_mod_detector_py_unit.py`
- `tests/python_fallback/test_plugin_py_unit.py`
- `tests/scanlog/parser/test_parser_py_fallback_unit.py`

## Decisions Made
- RuntimeError wrapping for Rust errors in wrappers keeps consistent error type across all failure modes
- Fail-fast initialization in parser_rust.py and plugin_rust.py (raise in __init__) rather than deferred errors
- E2E Rust-vs-Python output consistency test replaced with Rust output validation test (no Python to compare against)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated e2e pipeline test that forced Python fallback via _use_rust=False**
- **Found during:** Task 1
- **Issue:** test_rust_python_output_consistency patched _use_rust=False to force Python fallback, which no longer exists
- **Fix:** Replaced with test_rust_parser_produces_valid_output that validates Rust output structure
- **Files modified:** tests/rust_integration/e2e/test_pipeline_e2e.py
- **Committed in:** 6cc34e97

**2. [Rule 1 - Bug] Updated FFI null pointer test exception expectations**
- **Found during:** Task 1
- **Issue:** test_null_pointer_handling expected TypeError/ValueError/AttributeError but parser now raises RuntimeError
- **Fix:** Added RuntimeError to expected exception tuple
- **Files modified:** tests/rust_integration/ffi/test_ffi_error_conditions_integration.py
- **Committed in:** 6cc34e97

**3. [Rule 1 - Bug] Updated plugin wrapper fallback tests**
- **Found during:** Task 2
- **Issue:** TestRustPluginAnalyzerFallback tested Python fallback behavior that no longer exists
- **Fix:** Replaced with TestRustPluginAnalyzerNoFallback testing RuntimeError on missing Rust
- **Files modified:** tests/rust_integration/wrappers/test_plugin_rust_wrapper_unit.py
- **Committed in:** 8074d87b

**4. [Rule 1 - Bug] Updated FFI corrupted structure test patch path**
- **Found during:** Task 2
- **Issue:** Test patched PythonPluginAnalyzer.loadorder_scan_log which no longer exists
- **Fix:** Removed the Python patch, kept only the Rust patch
- **Files modified:** tests/rust_integration/ffi/test_ffi_error_conditions_integration.py
- **Committed in:** 8074d87b

---

**Total deviations:** 4 auto-fixed (4 bugs -- stale test references to removed Python fallbacks)
**Impact on plan:** All auto-fixes necessary for test suite to pass. No scope creep.

## Issues Encountered
- Benchmark test (test_benchmark_rust_batch_lookup_small) is flaky -- passed individually but failed in full suite. Pre-existing, unrelated to this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 03 (file_io_rust.py fallback removal) is the final plan in Phase 5
- All factory functions except get_yaml_operations, get_database_pool, get_orchestrator, get_yamldata still have some fallback pattern
- integration/python/ directory is fully eliminated -- Plan 03 targets file_io_rust.py internal fallbacks

---
*Phase: 05-fallback-pruning*
*Completed: 2026-02-02*
