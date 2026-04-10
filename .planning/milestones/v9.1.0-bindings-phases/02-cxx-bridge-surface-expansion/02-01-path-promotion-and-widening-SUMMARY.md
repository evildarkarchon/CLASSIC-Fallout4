---
phase: 02-cxx-bridge-surface-expansion
plan: 01
subsystem: cxx-bridge
tags: [cxx-bridge, path-core, classic::path, cxxs-08, d-11, d-09, d-10]
dependency_graph:
  requires:
    - 01-cxx-parity-gate-tooling (Phase 1 complete — gate tooling ready)
  provides:
    - classic::path C++ namespace with full CXXS-08 surface
    - IniCheckResultDto shared struct mirroring checker::IniCheckResult
    - path.rs in build.rs bridges array (D-03 satisfied)
    - Refreshed parity baseline with 222 entries (was 202, +20 path fns)
  affects:
    - classic-gui/pathdialog.cpp (D-11 migration #1)
    - classic-gui/mainwindow.cpp (D-11 migration #2)
    - docs/implementation/cxx_api_parity/baseline/ (D-09 refresh)
tech_stack:
  added:
    - classic::path CXX namespace (path.rs fully bridged)
    - IniCheckResultDto CXX shared struct (flat mirror of IniCheckResult)
  patterns:
    - Bridge String/Path Contract: &str arguments, Path::new() after empty check
    - Fail-soft empty-path policy on all bridge fns
    - D-08 backward-compat shims preserved in game.rs
key_files:
  created: []
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
    - classic-gui/src/app/pathdialog.cpp
    - classic-gui/src/app/mainwindow.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
decisions:
  - "Adapted bridge wrapper signatures from plan's interface spec to REAL classic-path-core API (is_valid_path/is_restricted_path take &Path not &str; parse_xse_log returns GamePathResult<PathBuf> not Result<String,String>; BackupManager is instance-based not static-style)"
  - "GUI D-10 clean build used system-fallback Qt from main repo vcpkg_installed because worktree vcpkg environment doesn't have Qt pre-built — both CLI and GUI tests passed 100%"
metrics:
  duration: 27min
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_changed: 9
---

# Phase 02 Plan 01: Path Promotion and Widening Summary

Promoted `src/path.rs` into the `build.rs::cxx_build::bridges` array and widened it to expose the full CXXS-08 `classic-path-core` surface (validation, restricted-path, real INI checker via `DocumentsChecker`, backup, XSE log, game-path discovery). Migrated both D-11 consumer sites (`pathdialog.cpp` and `mainwindow.cpp`) to `classic::path::check_restricted_path`. Refreshed the CXX parity baseline from 202 to 222 entries.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Promote path.rs to build.rs + widen with REAL CXXS-08 surface | 151c5e97 | Done |
| 2 | D-11 migrations (both sites) + D-10 clean build + D-09 baseline refresh | 9c50b31a | Done |

## Key Changes

### Task 1: path.rs widening (151c5e97)

- Added `"src/path.rs"` to `cxx_build::bridges` array in `build.rs` after `"src/game.rs"` (D-03)
- Extended `src/path.rs` from 3 functions to 20 bridge-exposed functions:
  - **Existing (preserved):** `detect_fallout4_game_path`, `resolve_fallout4_exe_name`, `detect_fallout4_docs_path`
  - **Validation Result helpers:** `path_validate_exists`, `path_validate_is_directory`, `path_validate_is_file`, `path_validate_required_files`, `path_validate_custom_scan`
  - **Predicate helpers:** `is_valid_path`, `is_restricted_path`
  - **Backward-compat aliases (D-08):** `validate_path`, `check_restricted_path`
  - **REAL INI checker surface:** `docs_checker_validate_ini_file`, `docs_checker_run_all_checks` (via `DocumentsChecker::new(game_name)`, NOT fictional `check_ini_files`)
  - **Backup helpers:** `backup_create_timestamped`, `backup_list_existing`
  - **XSE log + game-path:** `parse_xse_log`, `find_game_path`
- Added `IniCheckResultDto` shared struct: `ini_name`, `exists`, `is_valid`, `message`, `issue_or_empty`, `has_issue`
- Added 18 new `#[cfg(test)]` tests (21 total including 3 existing)
- game.rs shims (`check_restricted_path`, `validate_path`, `find_game_path`) preserved per D-08

### Task 2: Consumer migrations + builds + baseline (9c50b31a)

- `pathdialog.cpp`: Added `#include "classic_cxx_bridge/path.h"`; replaced `classic::game::check_restricted_path` with `classic::path::check_restricted_path` in `ManualPathDialog::validateAndAccept()`
- `mainwindow.cpp`: Replaced `classic::game::check_restricted_path` with `classic::path::check_restricted_path` in `validateCustomScanFolder()` (line 1443) — `path.h` was already included
- D-10 clean-build pair: CLI 24/24 tests, GUI 10/10 tests, all passing
- D-09 parity baseline refreshed: 222 entries (was 202), gate exits 0, 0 drift

## Deviations from Plan

### Auto-adapted Issues

**1. [Rule 1 - Bug] Adapted bridge wrapper to REAL classic-path-core API**
- **Found during:** Task 1 implementation
- **Issue:** Plan's `<interfaces>` section specified incorrect function signatures for the real API:
  - `is_valid_path/is_restricted_path` take `&Path` not `&str`
  - `validate_path_exists` takes `&Path` not `&str`
  - `parse_xse_log` returns `GamePathResult<PathBuf>` not `Result<String,String>`
  - `BackupManager` has no `create_timestamped`/`list_existing` static methods; it's instance-based
  - `find_game_path` in `game_path.rs` is a method on `GamePathFinder`, not a free function
- **Fix:** Bridge wrapper functions convert `&str` → `Path::new(s)` after empty-path check; `parse_xse_log` maps `PathBuf` to `String` via `to_string_lossy()`; `backup_create_timestamped`/`backup_list_existing` use `BackupManager::new(backup_root)` with derived backup root path
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`
- **Commit:** 151c5e97

**2. [Rule 3 - Blocking] GUI D-10 clean build used system-fallback Qt from main repo**
- **Found during:** Task 2
- **Issue:** `build_gui.ps1 -Clean -Test` fails because this worktree's vcpkg environment doesn't have Qt pre-built; vcpkg attempts to build Qt6 from source and fails
- **Fix:** Configured cmake with `-DCLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON -DCMAKE_PREFIX_PATH=J:/CLASSIC-Fallout4/classic-gui/build/vcpkg_installed/x64-windows` pointing to the main repo's pre-built Qt, then ran cmake build + ctest directly. All tests passed (10/10)
- **Impact:** D-10 requirement satisfied; Corrosion picked up the updated Rust source including new path.rs bridge and generated `path.h` in build output

**3. [Rule 1 - Bug] parity_contract.json needed generate_baseline.py --write-baseline**
- **Found during:** Task 2
- **Issue:** `check_parity_gate.py --update-baseline` alone doesn't update `parity_contract.json` — it only copies the diff/gate reports. The contract itself must be refreshed via `generate_baseline.py --write-baseline`
- **Fix:** Ran `generate_baseline.py --write-baseline` first, then `check_parity_gate.py --update-baseline`. Gate now exits 0 at 0 drift with 222 entries.
- **Files modified:** `docs/implementation/cxx_api_parity/baseline/parity_contract.json`, `rust_api_surface.json`
- **Commit:** 9c50b31a

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| "src/path.rs" in build.rs bridges array | PASS — verified via git grep |
| IniCheckResultDto has all 6 correct fields | PASS — ini_name, exists, is_valid, message, issue_or_empty, has_issue |
| docs_checker_validate_ini_file present (2 matches: def + extern) | PASS |
| docs_checker_run_all_checks present (2 matches) | PASS |
| No fictional check_ini_files fn | PASS |
| No fictional has_ini/has_custom_ini fields | PASS |
| game.rs check_restricted_path still exists (D-08) | PASS |
| cargo test path::tests exits 0 (21 tests) | PASS |
| cargo build classic-cpp-bridge exits 0 | PASS |
| pathdialog.cpp uses classic::path::check_restricted_path | PASS |
| mainwindow.cpp uses classic::path::check_restricted_path (line 1443) | PASS |
| classic::game::check_restricted_path ZERO matches in mainwindow.cpp | PASS |
| D-10 CLI build_cli.ps1 -Clean -Test exits 0 | PASS (24/24) |
| D-10 GUI build exits 0 | PASS (10/10, via system-fallback) |
| path.h generated in build output | PASS (build-system-fallback/corrosion_generated/...) |
| parity gate exits 0 at 0 drift | PASS |

## Known Stubs

None — all bridge functions are fully wired to classic-path-core implementations.

## Self-Check: PASSED
