---
phase: 01-foundation-cleanup
plan: 02
subsystem: tooling
tags: [vulture, dead-code, ci, static-analysis]
dependency_graph:
  requires: []
  provides: [dead-code-detection, vulture-ci-job, vulture-whitelist]
  affects: [01-01, 01-03]
tech_stack:
  added: [vulture-2.14]
  patterns: [dead-code-detection-in-ci]
key_files:
  created:
    - vulture_whitelist.py
  modified:
    - pyproject.toml
    - .github/workflows/ci.yml
    - ClassicLib/support/docs_path.py
decisions:
  - id: vulture-confidence-80
    description: "min-confidence 80 balances detection vs false positives"
    rationale: "Lower values produce too many uncertain results; 80 is vulture's recommended threshold"
  - id: whitelist-over-comments
    description: "Use separate whitelist file rather than inline vulture comments"
    rationale: "Centralized whitelist is easier to audit and maintain"
metrics:
  duration: 5m 11s
  completed: 2026-02-02
---

# Phase 01 Plan 02: Dead Code Detection with Vulture Summary

Vulture 2.14 installed as dev dependency with curated whitelist of 8 false positives (TYPE_CHECKING imports and Qt stub parameters), one true dead code removal (`if True:` block), and CI enforcement job.

## What Was Done

### Task 1: Install vulture and run initial scan
- Installed vulture 2.14 via `uv add --dev vulture`
- Ran initial scan: 11 findings at min-confidence 80
- Categorized findings into 3 buckets:
  - **True dead code (1):** Redundant `if True:` block in `docs_path.py` line 169
  - **False positives (10):** 4 TYPE_CHECKING imports used in string annotations, 6 Qt stub constructor parameters matching PySide6 API
- Removed the `if True:` dead code (de-indented the block)
- Created `vulture_whitelist.py` with categorized sections for all false positives
- Verified clean run: 0 violations

### Task 2: Add vulture to CI pipeline
- Added `dead-code` job to `.github/workflows/ci.yml`
  - Runs on `windows-latest` (matching existing CI pattern)
  - Uses uv + Python 3.12 setup (matching existing jobs)
  - Runs `uv run vulture ClassicLib/ vulture_whitelist.py --min-confidence 80`
  - Fails CI on any violations
- Added `[tool.vulture]` configuration section to `pyproject.toml`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| min-confidence 80 | Vulture's recommended threshold; balances detection sensitivity with false positive rate |
| Separate whitelist file | Centralized `vulture_whitelist.py` is easier to audit than inline comments |
| Whitelist organized by category | Sections for TYPE_CHECKING, Qt stubs, PyO3 imports aid maintainability |
| CI job runs independently | No `needs:` dependencies; dead-code check runs in parallel with other linting |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed redundant `if True:` block in docs_path.py**
- **Found during:** Task 1 vulture scan
- **Issue:** Line 169 had `if True:` wrapping code that always executes
- **Fix:** Removed the `if True:` and de-indented the contained block
- **Files modified:** `ClassicLib/support/docs_path.py`
- **Commit:** 47c76c86

## Performance

| Metric | Value |
|--------|-------|
| Duration | 5m 11s |
| Start | 2026-02-02T03:05:56Z |
| End | 2026-02-02T03:11:07Z |
| Tasks | 2/2 |
| Files created | 1 |
| Files modified | 3 |

## Task Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 47c76c86 | feat(01-02): install vulture and curate dead code whitelist |
| 2 | 0dab89a7 | feat(01-02): add vulture dead code detection to CI pipeline |

## Verification Results

- vulture clean run: 0 violations (exit code 0)
- CI YAML valid syntax with dead-code job
- vulture_whitelist.py exists with documented categories
- pyproject.toml lists vulture in dev dependencies
- All 3231 unit tests pass (7 skipped, 1236 deselected)

## Next Phase Readiness

No blockers. Vulture is now enforced in CI -- any future dead code introduction will fail the pipeline. Plan 01-01 (ruff unused code) and plan 01-03 can proceed independently.
