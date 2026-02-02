---
phase: 01-foundation-cleanup
plan: 01
subsystem: core
tags: [dead-code, deprecated, coverage, rust-workspace]
dependency-graph:
  requires: []
  provides: [deprecated-code-removed, coverage-baseline, rust-health-verified]
  affects: [01-02, 01-03, phase-2, phase-5]
tech-stack:
  added: []
  patterns: [coverage-baseline-tracking]
key-files:
  created:
    - .planning/phases/01-foundation-cleanup/coverage-baseline.txt
  modified:
    - ClassicLib/core/constants.py
  deleted:
    - ClassicLib/integration/rust/database_rust.py
decisions:
  - id: messaging-shims-dead
    summary: "4 messaging re-export shims identified as dead code candidates (zero callers)"
    context: "cli_progress.py, enums.py, models.py, progress_context.py in ClassicLib/messaging/"
  - id: tui-0pct-expected
    summary: "28 TUI modules at 0% coverage are expected (UI-specific testing, not dead code)"
  - id: ini-fallback-phase5
    summary: "ini_fallback.py is Phase 5 candidate for fallback pruning"
metrics:
  duration: "~13 minutes"
  completed: "2026-02-01"
---

# Phase 01 Plan 01: Remove Deprecated Code and Establish Coverage Baseline Summary

**One-liner:** Removed _DeprecatedVersion class and database_rust.py shim; established 71% coverage baseline with 0% module evaluation.

## What Was Done

### Task 1: Remove deprecated Python code
- **Deleted** `ClassicLib/integration/rust/database_rust.py` -- deprecated re-export shim for database pool classes, zero callers confirmed
- **Removed** `_DeprecatedVersion` class and associated deprecated version constants block from `ClassicLib/core/constants.py` (lines 39-137 removed)
- **Removed** unused `warnings` import from constants.py
- **Fixed** test patch target in `test_rust_database_pool_integration.py` from deleted module path to canonical `ClassicLib.io.database.rust_pool.DB_PATHS`
- **Verified** no DEPRECATED markers remain in any .py file under ClassicLib/
- **All 3231 unit tests pass**

Note: Task 1 changes were already committed as part of commit `798545c4` (feat(01-03)) from a previous execution that combined this work with plan 01-03 tasks. The file states were already correct.

### Task 2: Verify Rust workspace health and establish coverage baseline
- **cargo build --workspace**: All crates compile successfully
- **cargo clippy --workspace -- -D warnings**: Zero warnings (workspace has `unused = "deny"` lint)
- **Coverage baseline**: 71% overall (16259 statements, 4276 missed, 3944 branches, 500 partial)
- **0% module evaluation** documented in coverage-baseline.txt:
  - 28 TUI modules: Expected 0% (UI-specific, not dead code)
  - 4 messaging re-export shims: Dead code candidates (zero callers)
  - 1 scanning fallback (ini_fallback.py): Keep, Phase 5 candidate
  - 1 dev tool (vulture_whitelist.py): Not production code

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Messaging shims are dead code | grep confirmed zero callers for all 4 re-export shim paths |
| TUI 0% is expected | TUI is a separate application requiring Textual testing framework |
| ini_fallback.py kept | Has active caller in scangame_factory.py; Phase 5 pruning candidate |
| Plan path correction | Plan referenced `ClassicLib/io/database/database_rust.py` but actual file was `ClassicLib/integration/rust/database_rust.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan referenced wrong file path for database_rust.py**
- **Found during:** Task 1
- **Issue:** Plan specified `ClassicLib/io/database/database_rust.py` but the deprecated shim was at `ClassicLib/integration/rust/database_rust.py`
- **Fix:** Located and deleted the correct file
- **Files modified:** ClassicLib/integration/rust/database_rust.py (deleted)

**2. [Rule 1 - Bug] Test patch target pointed to deleted module**
- **Found during:** Task 1
- **Issue:** `test_rust_database_pool_integration.py` patched `ClassicLib.integration.rust.database_rust.DB_PATHS` but RustAsyncDatabasePool actually imports DB_PATHS from `ClassicLib.io.database.rust_pool`
- **Fix:** Updated patch target to `ClassicLib.io.database.rust_pool.DB_PATHS`
- **Files modified:** tests/rust_integration/api/test_rust_database_pool_integration.py
- **Commit:** 798545c4 (pre-existing)

**3. [Note] Task 1 work was pre-committed**
- Commit `798545c4` from a previous execution already contained the deprecated code removal. Task 1 execution verified the state was correct rather than making new changes.

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 798545c4 | (pre-existing) Remove deprecated Python code |
| 2 | 55614cd1 | Establish coverage baseline and verify Rust workspace health |

## Performance

- **Duration:** ~13 minutes
- **Start:** 2026-02-02T03:04:57Z
- **End:** 2026-02-02T03:17:32Z
- **Tasks:** 2/2
- **Files created:** 1
- **Files modified:** 1 (constants.py, pre-existing)
- **Files deleted:** 1 (database_rust.py, pre-existing)

## Next Phase Readiness

- All deprecated code removed from ClassicLib/
- Rust workspace verified healthy
- Coverage baseline at 71% provides regression detection
- 4 messaging shims flagged for future cleanup
- ini_fallback.py tracked for Phase 5 evaluation
