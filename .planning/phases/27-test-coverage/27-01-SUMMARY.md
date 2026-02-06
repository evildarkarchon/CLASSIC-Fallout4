---
phase: 27-test-coverage
plan: 01
subsystem: coverage-tooling
tags: [cargo-llvm-cov, coverage, powershell, baseline]
dependency-graph:
  requires: []
  provides: [coverage-scripts, baseline-measurements, gap-analysis]
  affects: [27-02, 27-03, 27-04]
tech-stack:
  added: []
  patterns: [two-phase-coverage-run, per-crate-json-parsing, pyO3-exclusion]
key-files:
  created:
    - rust/coverage_report.ps1
    - rust/coverage_summary.ps1
    - .planning/phases/27-test-coverage/27-BASELINE.md
  modified: []
decisions:
  - id: "27-01-01"
    title: "Exclude PyO3 crates from test run"
    choice: "Use --exclude flags for all 19 PyO3 binding crates"
    rationale: "PyO3 crates require Python DLL at runtime; STATUS_DLL_NOT_FOUND without it"
  - id: "27-01-02"
    title: "Use --ignore-run-fail for coverage collection"
    choice: "Allow test failures without aborting coverage data collection"
    rationale: "Pre-existing flaky test (test_cache_stats_empty) in classic-yaml-core would block coverage measurement"
  - id: "27-01-03"
    title: "Separate test run from report generation"
    choice: "Two-phase: --no-report for test run, then report commands for HTML/JSON/lcov"
    rationale: "--ignore-filename-regex is report-only flag; cannot combine with --no-report"
metrics:
  duration: "~9m"
  completed: "2026-02-06"
---

# Phase 27 Plan 01: Coverage Tooling and Baseline Summary

PowerShell coverage scripts wrapping cargo-llvm-cov with proper exclusions (Slint generated code, build artifacts, PyO3 crates), producing HTML/JSON/lcov reports and per-crate gap analysis table.

## What Was Done

### Task 1: Create Coverage Measurement Scripts
Created two PowerShell scripts in `rust/`:

**coverage_report.ps1** -- Main coverage runner:
- Accepts optional `-Package` parameter for per-crate runs
- Without `-Package`, runs workspace-wide coverage excluding 19 PyO3 crates
- Two-phase approach: `cargo llvm-cov --no-report` (test run), then 3 report generation commands
- Exclusion regex `(target[/\\]|build[/\\]|\.slint)` for report generation
- Enables `--features gui-bridge` for classic-shared-core AsyncBridge tests
- Uses `--ignore-run-fail` to collect coverage even with flaky tests
- Outputs HTML, JSON, and lcov reports to `target/llvm-cov/`

**coverage_summary.ps1** -- Per-crate gap analysis:
- Parses `target/llvm-cov/coverage.json` to extract per-crate line coverage
- Groups files by crate path (foundation, business-logic, ui-applications, python-bindings)
- Outputs formatted table with crate name, lines covered/total, percentage, PASS/GAP status
- Separates PyO3 binding crates as informational-only
- Gap prioritization section sorted by impact (lines_total * gap_to_60%)

### Task 2: Baseline Measurement and Gap Documentation
Ran coverage scripts and produced baseline document:

**Baseline Results:**
- 21 crates measured (2 foundation + 18 business-logic + 1 GUI)
- 18 crates already at/above 60%: strong existing test coverage
- 3 crates below 60%: classic-yaml-core (19.6%), classic-gui (37.4%), classic-shared-core (49.2%)
- Workspace aggregate: 72.0% line coverage (15,615 / 21,679 lines)

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Exclude all 19 PyO3 binding crates from test run | They require Python DLL at runtime (STATUS_DLL_NOT_FOUND); thin adapters whose logic is in -core crates |
| 2 | Use --ignore-run-fail flag | Pre-existing flaky test_cache_stats_empty in classic-yaml-core blocks coverage without this |
| 3 | Two-phase coverage approach | --ignore-filename-regex cannot be combined with --no-report; must separate test run from report generation |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] --ignore-filename-regex incompatible with --no-report**
- **Found during:** Task 1 initial run
- **Issue:** cargo-llvm-cov warns that `--ignore-filename-regex` cannot be used with `--no-report`
- **Fix:** Moved `--ignore-filename-regex` to report-generation phase only (Phase 2a/2b/2c)
- **Files modified:** `rust/coverage_report.ps1`
- **Commit:** 8cf0d614

**2. [Rule 3 - Blocking] PyO3 crates cause STATUS_DLL_NOT_FOUND**
- **Found during:** Task 1 initial run
- **Issue:** classic-shared-py (and all PyO3 crates) fail with exit code 0xc0000135 because they need the Python DLL
- **Fix:** Added `--exclude` flags for all 19 PyO3 binding crates in workspace-wide runs
- **Files modified:** `rust/coverage_report.ps1`
- **Commit:** 8cf0d614

**3. [Rule 3 - Blocking] Pre-existing flaky test blocks coverage collection**
- **Found during:** Task 1 second run
- **Issue:** `classic-yaml-core::tests::test_cache_stats_empty` fails due to global state contamination from parallel tests (DashMap cache not truly isolated despite `#[serial]` attribute)
- **Fix:** Added `--ignore-run-fail` flag to collect coverage data even when tests fail
- **Files modified:** `rust/coverage_report.ps1`
- **Commit:** 8cf0d614

**4. [Rule 1 - Bug] HTML report output directory nesting**
- **Found during:** Task 1 verification
- **Issue:** `cargo llvm-cov report --html --output-dir target/llvm-cov/html` creates `target/llvm-cov/html/html/index.html` (nested html directory)
- **Fix:** Changed output-dir to `target/llvm-cov` so HTML report lands at `target/llvm-cov/html/index.html`
- **Files modified:** `rust/coverage_report.ps1`
- **Commit:** 8cf0d614

**5. [Rule 1 - Bug] PowerShell format string syntax error**
- **Found during:** Task 1 summary script run
- **Issue:** Used `{1,>10}` syntax (Python-style) which is invalid in PowerShell; correct syntax is `{1,10}` for right-alignment
- **Fix:** Removed `>` characters from all format strings in coverage_summary.ps1
- **Files modified:** `rust/coverage_summary.ps1`
- **Commit:** 8cf0d614

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 8cf0d614 | Create coverage measurement scripts (coverage_report.ps1, coverage_summary.ps1) |
| 2 | e188f2d0 | Document coverage baseline with per-crate gap analysis (27-BASELINE.md) |

## Key Findings

1. **Most crates already pass.** 18 of 21 measurable crates exceed 60% line coverage -- only 3 need gap-filling.
2. **Five crates at near-100% coverage:** classic-message-core (100%), classic-pybridge-core (100%), classic-perf-core (99.6%), classic-web-core (99.4%), classic-settings-core (97.3%).
3. **classic-yaml-core has the largest gap** (19.6%) despite having 65 inline tests -- the cache management and I/O paths dominate line count.
4. **PyO3 crates are unmeasurable at Rust level** without a Python interpreter. Their business logic is tested via `-core` crate coverage.
5. **Flaky test identified:** `test_cache_stats_empty` needs `serial_test` across all cache-touching tests, not just itself.

## Next Phase Readiness

All subsequent plans (27-02 through 27-04) can reference `27-BASELINE.md` for:
- Which 3 crates need gap-filling work
- Prioritization order by impact score
- Current line counts for planning test scope

## Self-Check: PASSED
