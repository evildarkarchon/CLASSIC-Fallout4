---
status: complete
phase: 01-foundation-cleanup
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-02-01T12:00:00Z
updated: 2026-02-01T12:06:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. No deprecated modules remain
expected: `grep -r "DEPRECATED" ClassicLib/ --include="*.py" -l` returns 0 files
result: issue
reported: "grep output: ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py"
severity: minor

### 2. Vulture reports zero violations
expected: `uv run vulture ClassicLib/ vulture_whitelist.py --min-confidence 80` exits cleanly with 0 violations
result: pass

### 3. Rust workspace builds cleanly
expected: `cargo build --workspace` succeeds with no errors or stub crates remaining
result: pass

### 4. Coverage baseline exists
expected: `uv run pytest --cov=ClassicLib --cov-report=term` produces a coverage report; baseline file exists at `.planning/phases/01-foundation-cleanup/coverage-baseline.txt`
result: issue
reported: "FAILED tests/gui/settings/test_settings_persistence_e2e.py::TestPersistenceAcrossInstances::test_settings_persistence_across_instances - RuntimeError: Message handler not initialized. FAILED tests/gui/settings/test_settings_persistence_e2e.py::TestPersistenceAcrossInstances::test_settings_reload_after_save - RuntimeError: Message handler not initialized. FAILED tests/performance/test_async_pipeline_performance.py - RuntimeError: Message handler not initialized. FAILED tests/performance/test_crash_log_processing_performance.py - RuntimeError: Message handler not initialized."
severity: major

### 5. No mutable global flags remain
expected: No `global _*` mutable True/False flags in ClassicLib/. Run `grep -rn "global _" ClassicLib/ --include="*.py"` — all remaining globals should be lazy-init singletons, not mutable boolean flags. The `_VERSION_WARNING_LOGGED` flag specifically should be gone, replaced by lru_cache.
result: pass

### 6. Singleton reset fixture works
expected: `uv run pytest -x -m "unit and not slow" --timeout=60 -q` passes — the autouse `reset_all_singletons` fixture runs on every test without errors
result: pass

### 7. Vulture CI job exists
expected: `.github/workflows/ci.yml` contains a `dead-code` job that runs vulture
result: pass

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "grep -r DEPRECATED ClassicLib/ --include=*.py -l returns 0 files"
  status: failed
  reason: "User reported: grep output: ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py"
  severity: minor
  test: 1
  artifacts: []
  missing: []
- truth: "uv run pytest --cov=ClassicLib produces coverage report with no test failures from reset fixture"
  status: failed
  reason: "User reported: 4 tests FAILED with RuntimeError: Message handler not initialized - settings e2e (2) and performance tests (2)"
  severity: major
  test: 4
  artifacts: []
  missing: []
