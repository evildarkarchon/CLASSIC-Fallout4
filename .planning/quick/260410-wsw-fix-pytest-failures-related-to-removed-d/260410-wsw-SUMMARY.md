---
phase: 260410-wsw
plan: 01
subsystem: python-bindings-tests
tags: [quick, test-fix, parity-gate, catch-up]
requires: []
provides:
  - "test_parity_gate_tooling.py passing 3/3 after --deferred-registry removal"
affects:
  - "ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py"
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - "ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py"
decisions:
  - "Pure deletion fix — no replacement flag, mirrors pattern in commit 12acb63e"
  - "Line 102 (deferred_total: 0) preserved — still emitted by downstream coverage summary"
metrics:
  duration: "~5 min"
  completed: "2026-04-10"
  tasks: 1
  files: 1
  deletions: 4
  additions: 0
---

# Quick Task 260410-wsw: Fix pytest failures from removed --deferred-registry Summary

**One-liner:** Deleted 4 orphan lines in `test_parity_gate_tooling.py` that referenced the `--deferred-registry` parity-gate CLI flag removed in commit 12acb63e, restoring the file to 3/3 passing.

## Root Cause

Commit `12acb63e` (2026-04-10, Refactor 06-01) eliminated the `--deferred-registry` flag, the `deferred_registry.json` registry concept, and the Tier-1/Tier-2 deferred classification entirely as part of the v9.1.0 Phase 6 parity-tier collapse. The sibling test file `test_binding_coverage_tooling.py` was updated in that same commit, but `test_parity_gate_tooling.py` was overlooked. The result was 2 failing parametrized cases in `test_update_baseline_flag_refreshes_stale_baseline` (argparse raising `SystemExit: 2` on unrecognized arguments) plus 1 pre-existing passing test.

## What Changed

Deleted exactly 4 lines from `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py`:

1. Line 131: `    deferred_rel = "deferred_registry.json"`
2. Line 137: `    write_json(tmp_path / deferred_rel, {"entries": []})`
3. Line 178: `        "--deferred-registry",`
4. Line 179: `        deferred_rel,`

No additions, no renames, no reorders. Line 102 (`"deferred_total": 0,` in the `minimal_coverage_summary` fixture) was intentionally preserved — the downstream check script still emits this key with value 0 as part of the diff report.

## Verification

```
pwsh -ExecutionPolicy Bypass -Command "Set-Location 'J:\CLASSIC-Fallout4'; uv run pytest ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q"
```

Result: `3 passed in 0.26s` (up from 2 failed, 1 passed before the fix).

Grep check for stray references — `deferred[-_]registry|deferred_rel` in the file: **no matches**. `deferred_total` still present on line 102 as required.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

- `f0b6aa17` — Fix(quick-260410-wsw): Remove --deferred-registry references from parity gate tooling test

## Self-Check: PASSED

- File exists and modified: `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py` — FOUND
- Commit `f0b6aa17` — FOUND in `git log`
- Pytest result: `3 passed` — matches `<done>` criteria
- Grep for `deferred-registry|deferred_rel` — no hits (matches `<done>` criteria)
- Line 102 `deferred_total` preserved — confirmed via targeted grep
- Exactly 4 deletions, 0 additions — confirmed via `git show --stat` (1 file changed, 4 deletions)
