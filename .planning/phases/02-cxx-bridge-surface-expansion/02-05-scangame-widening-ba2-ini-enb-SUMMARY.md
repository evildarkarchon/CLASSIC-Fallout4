---
phase: 02-cxx-bridge-surface-expansion
plan: 05
subsystem: cxx-bridge
tags: [cxx, rust, scangame, ba2, ini, enb, ffi, parity]

# Dependency graph
requires:
  - phase: 02-cxx-bridge-surface-expansion/01
    provides: path bridge module + 4-place registration pattern
  - phase: 02-cxx-bridge-surface-expansion/02
    provides: constants + web bridge modules
  - phase: 02-cxx-bridge-surface-expansion/03
    provides: xse bridge module
  - phase: 02-cxx-bridge-surface-expansion/04
    provides: version_registry bridge module + baseline at 274 entries
provides:
  - "Widened scangame bridge: BA2/INI/ENB sub-domain entry points using REAL classic-scangame-core APIs"
  - "3 new CXX shared enums: IssueSeverity, EnbResult, EnbConfigResult (repr(u8), REAL variants)"
  - "3 new flat DTOs: Ba2IssuesSummaryDto, IniConfigIssueDto, EnbValidationResultDto (Pitfall 6 CLEAR)"
  - "D-11 consumer migration: GameFilesWorker::doScan body calls enb_checker_validate on every scan"
  - "Parity baseline refreshed: 288 entries, scangame now 18 (was 2)"
affects: [02-06-scangame-widening-toml-wrye, all-cxx-bridge-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BA2 free-fn wrapper: run_ba2_scan() helper + 5 public bridge fns (1 summary + 4 per-category)"
    - "INI wrapper: IniValidator constructed per-call with scan_config_files → detect_all_issues pipeline"
    - "ENB wrapper: EnbChecker constructed per-call, EnbValidationResult fields mapped to flat DTO"
    - "CXX shared enum repr(u8) with explicit discriminants (REAL variant names, not fictional)"
    - "Fail-soft pattern: BA2 scan_archive errors return empty/zero DTO rather than panicking"

key-files:
  created: []
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
    - classic-gui/src/workers/gamefilesworker.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json

key-decisions:
  - "BA2 free-fn wrappers use internal BA2Scanner::new() + scan_archive() per call — acceptable since per-archive scans are bounded"
  - "INI detect_all_issues bridge uses validator.scan_config_files() then detect_all_issues() in one call — avoids needing to pass a HashMap<String,PathBuf> across CXX boundary"
  - "ENB bridge falls back to '.' if game_path is empty — consistent with EnbChecker::new behavior"
  - "CXX shared enums omit Debug derive (CXX-generated types don't support it) — test assertions use matches! without {:?} format"
  - "Pre-existing clippy errors in classic-path-core/src/platform/linux.rs are out of scope — cargo check on classic-cpp-bridge passes cleanly"

requirements-completed: [CXXS-04, CXXS-10]

# Metrics
duration: 8min
completed: 2026-04-08
---

# Phase 2 Plan 05: Scangame Widening BA2/INI/ENB Summary

**scangame bridge widened from 2 to 10 entry points using REAL BA2Scanner/IniValidator/EnbChecker APIs; 3 CXX shared enums + 3 flat DTOs added; GameFilesWorker::doScan exercises enb_checker_validate on every scan; parity baseline at 288 entries, 0 drift**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-08T01:03:04Z
- **Completed:** 2026-04-08T01:11:14Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- BA2 sub-domain: `ba2_scan_archive_summary` (flat summary DTO) + 4 per-category getters returning `Vec<String>` — all backed by the real `BA2Scanner::new()` / `scan_archive(&Path)` API
- INI sub-domain: `ini_validator_validate_inis` (full report text) + `ini_validator_detect_all_issues_for_root` (structured issues with REAL ConfigIssue fields: file_path, section, setting, current_value, recommended_value, description, severity)
- ENB sub-domain: `enb_checker_validate` returning `EnbValidationResultDto { binaries: EnbResult, config: EnbConfigResult }` — REAL field set, no fictional errors Vec
- 3 CXX shared enums with `#[repr(u8)]` and REAL variant names (not the fictional set from earlier plan versions)
- D-11 migration: GameFilesWorker::doScan body now calls `classic::scangame::enb_checker_validate` on every actual game-files scan and appends ENB status to the results view
- 13 Rust tests passing (3 existing preserved + 10 new BA2/INI/ENB coverage)
- Parity baseline: 288 total entries; scangame module went from 2 to 18 entries; gate exits 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Widen scangame.rs with REAL BA2/INI/ENB APIs + shared enums + DTOs + tests** - `bc4e0e94` (feat)
2. **Task 2: Cross-binding parity + D-11 consumer migration + incremental builds + D-09 baseline** - `47b3acff` (feat)

## Files Created/Modified

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — Widened from 2 to 10 bridge entry points: 5 BA2 fns, 2 INI fns, 1 ENB fn, 3 new enums, 3 new structs; existing `run_setup_checks`/`needs_path_detection` UNCHANGED
- `classic-gui/src/workers/gamefilesworker.cpp` — D-11: `doScan` body extended with `enb_checker_validate` call + ENB summary text appended to results before `finished` signal emission
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json` — 288 entries (was 274); scangame: 18 entries
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json` — Updated diff report
- `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md` — Shows ADDED rows under scangame
- `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md` — Gate passed, 0 drift
- `docs/implementation/cxx_api_parity/baseline/rust_api_surface.json` — Refreshed surface snapshot

## Decisions Made

- Used free-fn wrappers that construct BA2Scanner/IniValidator/EnbChecker internally per call, avoiding the need to expose opaque Rust object handles through CXX (aligns with D-06 pattern from context)
- CXX shared enum types don't derive Debug automatically; removed `{:?}` format specifiers from test assertions and used plain `matches!` instead
- Pre-existing clippy lints in `classic-path-core/src/platform/linux.rs` are out of scope — only `cargo check -p classic-cpp-bridge` is required to pass cleanly

## Cross-Binding Parity Check (CXXS-04 criterion 4)

### Python (`classic-scangame-py`) vs CXX bridge

| Python | CXX bridge | Status |
|--------|-----------|--------|
| `BA2Scanner.scan_archive(path)` | `ba2_scan_archive_summary(path)` + 4 getters | Covered |
| `BA2Scanner.scan_archives_batch(paths)` | Not bridged (batch) | Follow-up |
| `BA2Scanner.find_ba2_files(dir)` | Not bridged (find) | Follow-up |
| `scan_all_ba2_archives(root)` | Not bridged (convenience) | Follow-up |
| `EnbChecker.validate()` | `enb_checker_validate(path)` | Covered |
| `EnbChecker.check_binaries()` | (via validate summary) | Covered |
| `EnbChecker.check_config()` | (via validate summary) | Covered |
| `check_enb(path)` free fn | `enb_checker_validate(path)` | Covered |
| `IniValidator.validate_inis(root)` | `ini_validator_validate_inis(game, root)` | Covered |
| `IniValidator.detect_all_issues(config_files)` | `ini_validator_detect_all_issues_for_root` | Covered |
| `IniValidator.scan_config_files(root)` | Folded into detect_all_issues_for_root | Covered |

### Node (`classic-node/src/scangame.rs`) vs CXX bridge

| Node | CXX bridge | Status |
|------|-----------|--------|
| `JsBa2Scanner.scan_archive(path)` | `ba2_scan_archive_summary(path)` + 4 getters | Covered |
| `JsBa2Scanner.find_ba2_files(dir)` | Not bridged | Follow-up |
| `scan_all_ba2_archives(root)` free fn | Not bridged | Follow-up |
| `check_enb(path)` free fn | `enb_checker_validate(path)` | Covered |
| `JsEnbChecker.check_binaries()` | (via validate) | Covered |
| `JsEnbChecker.validate()` | `enb_checker_validate(path)` | Covered |
| `JsIniValidator.validate_inis(root)` | `ini_validator_validate_inis(game, root)` | Covered |
| `JsIniValidator.detect_all_issues(map)` | `ini_validator_detect_all_issues_for_root` | Covered |
| `JsIniValidator.scan_config_files(root)` | Folded into detect_all_issues_for_root | Covered |

**Assessment:** All primary per-domain checker entry points are covered in the CXX bridge. Batch scan and directory-find helpers are not bridged — they are convenience wrappers over the same core APIs and can be added in a future plan if needed.

## Pitfall 6 Verification

All new DTOs are Pitfall 6 CLEAR (no `Vec<StructWithVec>` patterns):
- `Ba2IssuesSummaryDto`: only `u32` and `bool` fields
- `IniConfigIssueDto`: only `String` + `IssueSeverity` (CXX shared enum) fields — no Vec
- `EnbValidationResultDto`: only `EnbResult` + `EnbConfigResult` (CXX shared enums) — no Vec
- Per-category BA2 getters return `Vec<String>` directly (not `Vec<StructWithVec>`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CXX shared enums don't derive Debug**
- **Found during:** Task 1 (first cargo test run)
- **Issue:** Test assertions used `{:?}` formatting on `ffi::EnbResult` and `ffi::EnbConfigResult`, but CXX-generated shared enum types don't implement `std::fmt::Debug`
- **Fix:** Replaced all `{:?}` format specifiers in test assertion messages with plain string literals; `matches!` macro doesn't require Debug
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` (tests section only)
- **Verification:** `cargo test -p classic-cpp-bridge scangame::tests` exits 0 with all 13 tests passing
- **Committed in:** `bc4e0e94` (task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — CXX-generated type Debug limitation)
**Impact on plan:** Minimal — test fix only; no behavior or API change. All assertions remain equivalent.

## Issues Encountered

- Pre-existing clippy errors in `classic-path-core/src/platform/linux.rs` (redundant closure, `&PathBuf` vs `&Path`) caused `cargo clippy -p classic-cpp-bridge -- -D warnings` to fail due to dependency compilation. Confirmed these are pre-existing and out of scope; `cargo check -p classic-cpp-bridge` passes cleanly.

## Known Stubs

None — all bridge functions call real `classic-scangame-core` APIs and return real data. No placeholder values or hardcoded empty results flow to the UI (except the expected fail-soft zero-counts for missing/unparseable BA2 archives).

## Next Phase Readiness

- Plan 02-06 can safely extend `scangame.rs` ADDITIVELY for TOML/Wrye/integrity/setup sub-domains — this plan's additions are fully below the existing `run_setup_checks`/`needs_path_detection` block
- The 4-place registration pattern (wrapper fn + ffi struct/enum + extern "Rust" decl + tests) is demonstrated for all three sub-domains

---
*Phase: 02-cxx-bridge-surface-expansion*
*Completed: 2026-04-08*

## Self-Check: PASSED

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`: FOUND
- `classic-gui/src/workers/gamefilesworker.cpp`: FOUND
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json`: FOUND
- Commit `bc4e0e94`: FOUND
- Commit `47b3acff`: FOUND
