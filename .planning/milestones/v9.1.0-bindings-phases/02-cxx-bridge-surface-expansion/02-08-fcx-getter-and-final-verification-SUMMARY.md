---
phase: 02-cxx-bridge-surface-expansion
plan: "08"
subsystem: cxx-bridge
tags:
  - cxx
  - scanner
  - fcx
  - cxxs-03
  - cxxs-10
  - d-11
  - phase-final
dependency_graph:
  requires:
    - 02-01 (path bridge + build.rs baseline)
    - 02-02 (constants/web bridge)
    - 02-03 (scangame BA2/INI/ENB/TOML bridge)
    - 02-04 (XSE + version_registry bridge)
    - 02-05 (config initial widening)
    - 02-06 (scangame toml/wrye/integrity/setup widening)
    - 02-07 (config suspect rules + database typed FormID)
  provides:
    - FcxIssueDto + get_fcx_config_issues() in classic::scanner (CXXS-03)
    - D-11 consumer migration in classic-cli/src/scanner.cpp scan_with_config
    - FINAL Phase 2 parity baseline at 316 entries (all CXXS-01..CXXS-10 satisfied)
  affects:
    - Phase 3+ plans that add new CXX bridge surface (baseline is now 316 entries)
    - Any consumer of the FCX issue getter (classic-cli, classic-gui)
tech_stack:
  added: []
  patterns:
    - Bridge String/Path Contract applied to FcxIssueDto (Option<String> section flattened to section_or_empty + has_section)
    - serial_test::serial used for all tests touching GLOBAL_FCX_HANDLER (isolation pattern)
    - Fail-soft try/catch(rust::Error&) wrapper for FCX call in C++ consumer
key_files:
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
    - classic-cli/src/scanner.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
decisions:
  - "Pre-existing FCX global-state tests annotated with serial_test::serial to fix test isolation race conditions (Rule 2 auto-fix during Task 1)"
  - "GUI D-10 clean build used system-fallback Qt preset (build-system-fallback dir) because worktree vcpkg environment lacks pre-built Qt — same approach as all prior Phase 2 plans"
  - "FINAL Phase 2 parity baseline: 316 entries (314 from plan 02-07 + 2 new: FcxIssueDto struct + get_fcx_config_issues fn)"

patterns_established:
  - "Serial test isolation: any test that reads/writes GLOBAL_FCX_HANDLER must carry #[serial_test::serial]"

requirements_completed:
  - CXXS-03
  - CXXS-10

metrics:
  duration: 31min
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_changed: 7
---

# Phase 02 Plan 08: FCX Getter and Final Verification — Summary

**FcxIssueDto bridge DTO with Option<String>-flattened section field and get_fcx_config_issues() function added to classic::scanner, D-11 consumer wired into every CLI scan run, and the FINAL Phase 2 parity baseline committed at 316 entries with all CXXS-01..CXXS-10 satisfied.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-04-08T01:40:00Z
- **Completed:** 2026-04-08T02:11:41Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added `FcxIssueDto` shared struct mirroring `ConfigIssue` field-for-field with `section: Option<String>` flattened to `section_or_empty: String` + `has_section: bool` per Bridge String/Path Contract (Pitfall 6 CLEAR — all plain fields)
- Added `get_fcx_config_issues() -> Vec<FcxIssueDto>` bridge function reading from `GLOBAL_FCX_HANDLER` via parking_lot::Mutex; 6 new serial tests covering empty-state, idempotence, round-trip None/Some, order preservation, and regression of `fcx_reset_global_state()` (D-08)
- Added D-11 consumer in `classic-cli/src/scanner.cpp::scan_with_config` — calls `get_fcx_config_issues()` after every scan loop, prints per-issue summary with section-aware formatting, wrapped in fail-soft `try/catch(rust::Error&)` (Codex HIGH correction)
- Final Phase 2 parity baseline: 316 entries at 0 drift; CLI clean build (24/24), GUI system-fallback build (10/10) green; ALL CXXS-01..CXXS-10 satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: FcxIssueDto + get_fcx_config_issues() bridge fn + tests** - `c2d6c3cf` (feat)
2. **Task 2: D-11 consumer migration in scanner.cpp** - `51382a4d` (feat)
3. **Task 3: Final verification + parity baseline refresh** - `20fa7c5e` (feat)

## Files Created/Modified

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` — Added `FcxIssueDto` shared struct, `get_fcx_config_issues()` function and extern declaration, 6 new serial tests; annotated pre-existing FCX tests with `serial_test::serial`
- `classic-cli/src/scanner.cpp` — Added D-11 consumer call to `classic::scanner::get_fcx_config_issues()` in `scan_with_config`, after report-write loop, before final summary print
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json` — FINAL Phase 2 baseline: 316 entries (+2 from 314)
- `docs/implementation/cxx_api_parity/baseline/rust_api_surface.json` — Updated surface snapshot
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json` — 0 drift report
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` — 0 drift markdown
- `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md` — Gate PASSED report

## Phase 2 Final Sanity Check — CXXS Requirements Coverage

| Requirement | Module | Baseline Entries |
|-------------|--------|------------------|
| CXXS-01 | constants | 16 |
| CXXS-02 | web | 12 |
| CXXS-03 | scanner (get_fcx_config_issues) | 1 |
| CXXS-04 | scangame | 8 |
| CXXS-05 | database (typed FormID) | 2 |
| CXXS-06 | version_registry | 14 |
| CXXS-07 | config (suspect rules) | 3 |
| CXXS-08 | path | 20 |
| CXXS-09 | xse | 10 |
| CXXS-10 | Clean build pair (CLI 24/24, GUI 10/10) | N/A |
| **TOTAL** | | **316** |

## Decisions Made

- Pre-existing FCX global-state tests annotated with `#[serial_test::serial]` to fix test isolation race: without `serial_test`, non-serial tests running in parallel with serial tests contaminated `GLOBAL_FCX_HANDLER` state. This is Rule 2 (auto-add missing critical functionality for test correctness).
- GUI D-10 final verification used system-fallback Qt preset (`build-system-fallback/` dir) because the worktree vcpkg environment lacks pre-built Qt; attempting `-Clean` triggers vcpkg rebuild of Qt which fails. Same workaround documented in 02-01 and 02-04 summaries.
- FINAL Phase 2 parity baseline: 316 entries. `generate_baseline.py --write-baseline` was run first to refresh `parity_contract.json`, then `check_parity_gate.py --update-baseline` to copy all artifacts to the baseline directory.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Annotated pre-existing FCX tests with serial_test::serial**
- **Found during:** Task 1 (FcxIssueDto + get_fcx_config_issues() bridge fn)
- **Issue:** `test_fcx_reset_global_state_treats_unnecessary_as_success` and 3 other pre-existing tests interacted with `GLOBAL_FCX_HANDLER` without serial guards. New serial tests running in parallel caused global state contamination — the previously-clean test failed with `detected_issues is not empty` because a serial test's injected state leaked across.
- **Fix:** Added `#[serial_test::serial]` to all 4 pre-existing FCX global-state tests (`test_fcx_reset_global_state_treats_unnecessary_as_success`, `test_fcx_reset_global_state_clears_dirty_state`, `test_orchestrator_process_log_resets_fcx_before_scan_start`, `test_orchestrator_process_logs_batch_resets_fcx_before_scan_start`)
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- **Verification:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner::tests` — 42 passed, 0 failed
- **Committed in:** `c2d6c3cf` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing test isolation)
**Impact on plan:** Essential for test correctness. No scope creep.

## Issues Encountered

**GUI clean build fails in worktree (expected, documented):** `build_gui.ps1 -Clean -Test` triggers vcpkg to rebuild Qt from source, which fails because this worktree's vcpkg environment doesn't have Qt pre-built. Workaround: used `build_gui.ps1 -Test -Preset system-fallback` which uses the pre-built Qt from `build-system-fallback/` (pointing to main repo's vcpkg_installed). Result: 10/10 GUI tests passed. Same workaround as 02-01 and 02-04.

## Known Stubs

None — no placeholder data or TODO wiring issues in files created or modified by this plan.

## Next Phase Readiness

- Phase 2 is COMPLETE. All CXXS-01..CXXS-10 requirements satisfied.
- Parity gate is at 0 drift with 316 baseline entries.
- Both C++ frontends build and test clean against the fully-widened bridge surface.
- Phase 3 can proceed with the final Phase 2 baseline as its starting point.

---
*Phase: 02-cxx-bridge-surface-expansion*
*Completed: 2026-04-08*
