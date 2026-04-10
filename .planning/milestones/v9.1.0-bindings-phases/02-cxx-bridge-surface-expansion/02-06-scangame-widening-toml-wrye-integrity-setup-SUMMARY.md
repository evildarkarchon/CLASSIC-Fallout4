---
phase: 02-cxx-bridge-surface-expansion
plan: 06
subsystem: cxx-bridge
tags: [cxx, rust, scangame, toml, wrye, integrity, setup, crashgen, ffi, parity]

# Dependency graph
requires:
  - phase: 02-cxx-bridge-surface-expansion/05
    provides: scangame bridge with BA2/INI/ENB sub-domain entry points + 288-entry baseline
provides:
  - "CXXS-04 complete: scangame bridge exposes all sub-domain entry points using REAL APIs"
  - "3 new CXX shared enums: TomlIssueSeverity, WryeSeverity (3 real variants), CheckType (2 real variants)"
  - "5 new flat DTOs: TomlConfigIssueDto, WryeIssueRowDto (row-oriented), IntegrityCheckResultDto, ScanGameSetupDto, CrashgenCheckResultDto, CrashgenReportSummaryDto"
  - "9 new bridge fns: crashgen_checker_check, crashgen_checker_get_issues, wrye_parse_html_rows, integrity_run_all_checks, scangame_run_setup_structured, crashgen_orchestrator_check_summary, crashgen_orchestrator_get_issues, crashgen_orchestrator_get_installed_plugins"
  - "D-11 in-flow consumer #2: GameFilesWorker::doScan body calls crashgen_orchestrator_check_summary on every scan"
  - "Parity baseline refreshed from 288 to 305 entries (17 new), gate at 0 drift"
affects: [02-07-and-beyond-cxx-bridge-consumers, all-cxx-bridge-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TOML wrapper: CrashgenChecker constructed per-call (plugins_path + name); check() returns (text, Vec<TomlConfigIssue>)"
    - "Wrye row-oriented flattening: one WryeIssueRowDto per (WryeIssue, plugin) pair; issue_index lets C++ group rows"
    - "Integrity wrapper: IntegrityConfig::new constructed internally; run_all_checks() returns Vec<IntegrityCheckResult>"
    - "Setup structured DTO: counts from REAL SetupCheckResults vec lengths (integrity_results.len + xse_results.len + docs_results.len)"
    - "CrashgenOrchestrator getter split: summary DTO (no Vec) + two separate getters for issues Vec and installed_plugins Vec (Pitfall 6)"
    - "D-11 consumer pattern: doScan body calls crashgen_orchestrator_check_summary per scan, appends crashgenLine to combinedText"
    - "Auto-fix: pre-existing clippy::manual-contains in constants.rs fixed (SETTINGS_IGNORE_NONE.contains(&key))"

key-files:
  created: []
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs
    - classic-gui/src/workers/gamefilesworker.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json

key-decisions:
  - "WryeSeverity declared with 3 variants (Info, Warning, Error) — the REAL enum has no Note variant (plan spec was wrong; real API was authoritative)"
  - "CrashgenReportSummaryDto two Vec fields (issues, installed_plugins) exposed via separate getter fns — Pitfall 6 compliance"
  - "crashgen_checker_check and crashgen_checker_get_issues each reconstruct CrashgenChecker internally — acceptable cost given bounded call frequency"
  - "IntegrityCheckResultDto uses is_valid (REAL field) not passed (fictional — Codex HIGH correction)"
  - "CheckType has only ExecutableVersion + InstallationLocation (2 REAL variants, not 5 fictional)"
  - "gamefilesworker.cpp: uses QDir to construct Data/F4SE/Plugins from gameRoot for Buffout4 plugins path"

metrics:
  duration: 9min
  completed: 2026-04-08
  tasks_completed: 2
  files_modified: 8
  tests_added: 20
  total_scangame_tests: 29
  new_bridge_entries: 17
  baseline_entries: 305
---

# Phase 02 Plan 06: Scangame widening — TOML/Wrye/Integrity/Setup/Crashgen Summary

**One-liner:** CXXS-04 completed by widening scangame bridge with REAL CrashgenChecker, WryeBashParser (row-oriented Pitfall 6 fix), GameIntegrityChecker, run_combined_checks structured DTO, and CrashgenCheckOrchestrator APIs; baseline at 305 entries with 0 drift.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Widen scangame.rs with TOML/Wrye/Integrity/Setup/Crashgen + tests | da188cae | scangame.rs, constants.rs |
| 2 | D-11 in-flow consumer #2 + D-09 baseline refresh | 91415cb3 | gamefilesworker.cpp, 5 baseline artifacts |

## REAL API Confirmations (Codex HIGH corrections)

### TOML (CrashgenChecker)
- `CrashgenChecker::new(plugins_path: &Path, crashgen_name: impl Into<String>)` — CONFIRMED
- `.check() -> Result<(String, Vec<TomlConfigIssue>)>` — CONFIRMED
- `TomlConfigIssue` fields: `file_path, section, setting, current_value, recommended_value, description, severity` — CONFIRMED per toml.rs:61-82

### Wrye (WryeBashParser) — Pitfall 6 fix
- `WryeBashParser::new(wrye_warnings: HashMap<String, String>)` — CONFIRMED
- `.parse(html_content: &str) -> Vec<WryeIssue>` — CONFIRMED
- `WryeIssue` fields: `section_title: String, plugins: Vec<String>, warning_message: Option<String>, severity: WryeSeverity` — CONFIRMED
- `WryeSeverity` has **3 variants** (Info, Warning, Error) — **NOT 4** (no Note). Plan spec said Note; real API did not have it. Auto-corrected.
- Bridge flattens to `WryeIssueRowDto` (one row per (issue, plugin) pair) — Pitfall 6 CLEARED

### Integrity (GameIntegrityChecker)
- `IntegrityConfig::new(game_exe_path: PathBuf, valid_exe_hashes: Vec<String>, root_name: String)` — CONFIRMED
- `GameIntegrityChecker::new(config: IntegrityConfig).run_all_checks() -> Result<Vec<IntegrityCheckResult>, IntegrityError>` — CONFIRMED
- `IntegrityCheckResult` fields: `is_valid: bool, message: String, check_type: CheckType` — CONFIRMED (`is_valid`, NOT `passed`)
- `CheckType` has **2 variants** (ExecutableVersion, InstallationLocation) — NOT 5 fictional variants

### Setup orchestrator
- `run_combined_checks(config: &SetupCheckConfig) -> SetupCheckResults` — CONFIRMED
- `SetupCheckResults` fields: `integrity_results: Vec<String>, xse_results: Vec<String>, docs_results: Vec<String>, errors: Vec<String>` — CONFIRMED
- Counts from REAL vec lengths via `.total_checks()` and `.errors.len()`

### CrashgenOrchestrator
- `CrashgenCheckOrchestrator::check(plugins_path: &Path, crashgen_name: &str) -> Result<CrashgenReport>` — CONFIRMED
- `CrashgenReport` fields: `message, issues: Vec<TomlConfigIssue>, crashgen_name, config_path: Option<PathBuf>, installed_plugins: Vec<String>` — CONFIRMED
- Bridge exposes summary DTO (no Vec) + two separate getters for Vec fields (Pitfall 6 CLEAR)

## New Bridge Surface (plan 02-06 additions)

### CXX Shared Enums (3 new, repr(u8))
- `TomlIssueSeverity` — Info(0), Warning(1), Error(2)
- `WryeSeverity` — Info(0), Warning(1), Error(2) [3 REAL variants]
- `CheckType` — ExecutableVersion(0), InstallationLocation(1) [2 REAL variants]

### CXX Shared Structs (6 new, all Pitfall 6 CLEAR)
- `TomlConfigIssueDto` — REAL TomlConfigIssue field set (file_path, section, setting, current_value, recommended_value, description, severity)
- `WryeIssueRowDto` — row-oriented (issue_index, section_title, plugin, warning_message_or_empty, has_warning_message, severity)
- `IntegrityCheckResultDto` — `is_valid: bool` (NOT `passed`), message, check_type
- `ScanGameSetupDto` — check_count, error_count, has_errors
- `CrashgenCheckResultDto` — report_text, issue_count
- `CrashgenReportSummaryDto` — message, crashgen_name, config_path_or_empty, has_config_path, issue_count, installed_plugin_count

### CXX extern "Rust" fns (9 new)
- `crashgen_checker_check(plugins_path, crashgen_name) -> CrashgenCheckResultDto`
- `crashgen_checker_get_issues(plugins_path, crashgen_name) -> Vec<TomlConfigIssueDto>`
- `wrye_parse_html_rows(html_content, warnings_keys, warnings_values) -> Vec<WryeIssueRowDto>`
- `integrity_run_all_checks(game_exe_path, valid_hashes, root_name) -> Vec<IntegrityCheckResultDto>`
- `scangame_run_setup_structured(game_exe_path, valid_hashes, root_name, game_name, docs_path) -> ScanGameSetupDto`
- `crashgen_orchestrator_check_summary(plugins_path, crashgen_name) -> CrashgenReportSummaryDto`
- `crashgen_orchestrator_get_issues(plugins_path, crashgen_name) -> Vec<TomlConfigIssueDto>`
- `crashgen_orchestrator_get_installed_plugins(plugins_path, crashgen_name) -> Vec<String>`

### Preserved from 02-05 (D-08 — UNCHANGED)
All BA2/INI/ENB fns + run_setup_checks + needs_path_detection unchanged.

## D-11 In-Flow Consumer Migration

`GameFilesWorker::doScan` now calls two new bridge fns on every scan:
1. Plan 02-05: `enb_checker_validate` (ENB summary appended to output)
2. Plan 02-06: `crashgen_orchestrator_check_summary` (Buffout4 plugin count + config issues appended)

The plugins path is derived from `QDir(gameRoot).filePath("Data/F4SE/Plugins")` — the standard Buffout4 install location. `#include <QDir>` added to gamefilesworker.cpp.

## Parity Gate

- Baseline before this plan: 288 entries (from plan 02-05)
- New entries from this plan: 17 (3 enums + 6 structs + 8 fns from extern "Rust")
- Baseline after: 305 entries
- Parity gate exits 0 with 0 drift

## Test Results

- `cargo test -p classic-cpp-bridge scangame::tests`: 29/29 pass
  - 9 preserved from plan 02-05 (BA2/INI/ENB/setup/path-detection)
  - 20 new tests (TOML/Wrye/Integrity/Setup/Crashgen)
- `build_cli.ps1 -Test`: 17/17 unit + 24/24 integration = 41/41 pass
- `build_gui.ps1 -Test`: 10/10 pass
- Parity gate: 0 drift

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] WryeSeverity declared with 3 variants instead of 4**
- **Found during:** Task 1, reading wrye.rs
- **Issue:** Plan spec said `WryeSeverity` had 4 variants (Error, Warning, Info, Note). The REAL API in `wrye.rs:42-49` has only 3 (Info, Warning, Error; no Note).
- **Fix:** Declared `WryeSeverity` with 3 REAL variants. The `map_wrye_severity` match was written correctly for 3 variants.
- **Files modified:** scangame.rs
- **Commit:** da188cae

**2. [Rule 1 - Bug] Pre-existing clippy::manual-contains in constants.rs**
- **Found during:** Task 1, running clippy on classic-cpp-bridge
- **Issue:** `SETTINGS_IGNORE_NONE.iter().any(|k| *k == key)` flagged as `clippy::manual-contains` (-D warnings)
- **Fix:** Changed to `SETTINGS_IGNORE_NONE.contains(&key)`
- **Files modified:** constants.rs
- **Commit:** da188cae

## Known Stubs

None — all bridge fns delegate to real classic-scangame-core APIs. No placeholder data flows to consumers.

## Self-Check: PASSED

- [x] `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` exists and contains all 9 new fns
- [x] `classic-gui/src/workers/gamefilesworker.cpp` contains crashgen_orchestrator_check_summary call
- [x] Commit da188cae exists: `feat(02-06): widen scangame bridge with REAL TOML/Wrye/Integrity/Setup/Crashgen sub-domains`
- [x] Commit 91415cb3 exists: `Feat(02-06): D-11 in-flow consumer #2 + D-09 baseline refresh (305 entries, 0 drift)`
- [x] All 29 scangame tests pass
- [x] Both incremental builds green
- [x] Parity gate exits 0 with 0 drift (305 entries)
