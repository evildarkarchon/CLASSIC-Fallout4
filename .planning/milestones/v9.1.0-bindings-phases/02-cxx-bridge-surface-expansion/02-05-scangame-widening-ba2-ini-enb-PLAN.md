---
phase: 02-cxx-bridge-surface-expansion
plan: 05
type: execute
wave: 3
depends_on:
  - 02-cxx-bridge-surface-expansion/01
  - 02-cxx-bridge-surface-expansion/02
  - 02-cxx-bridge-surface-expansion/03
  - 02-cxx-bridge-surface-expansion/04
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  - classic-gui/src/workers/gamefilesworker.cpp
  - classic-gui/src/workers/gamefilesworker.h
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-04
  - CXXS-10
must_haves:
  truths:
    - "src/scangame.rs exposes BA2 sub-domain bridge fns: ba2_scanner_new + ba2_scan_archive (uses BA2Scanner::new() / scan_archive(&Path) — REAL classic-scangame-core/src/ba2.rs API, NOT a fictional run_ba2_check)"
    - "BA2 DTO is a flat summary (Ba2IssuesSummaryDto with counts) PLUS per-category getters that re-run the scan and return Vec<String> for tex_dims/tex_frmt/snd_frmt/xse_file (D-06 split per Pitfall 6)"
    - "src/scangame.rs exposes INI sub-domain via IniValidator wrapper: ini_validator_validate_inis(game_name, game_root) returning the full validation report string; ini_validator_detect_all_issues(game_name, config_paths_keys, config_paths_values) returning Vec<IniConfigIssueDto> with the REAL ConfigIssue field set (file_path, section, setting, current_value, recommended_value, description, severity)"
    - "src/scangame.rs exposes ENB sub-domain via EnbChecker wrapper: enb_checker_validate(game_path) returning EnbValidationResultDto with REAL fields (binaries: EnbResult, config: EnbConfigResult — NO errors_csv, NO `errors` Vec)"
    - "EnbResult shared enum has REAL variants: Present, Partial, NotInstalled (NOT NotPresent / PresentNoConfig / PresentWithConfig / PresentWithIniOverride from the fictional version)"
    - "EnbConfigResult shared enum has REAL variants: Valid, NotFound, Unreadable (NOT Valid / HasConflicts / Missing / NotApplicable from the fictional version)"
    - "All new shared structs are flat (Pitfall 6 CLEAR — IniConfigIssueDto has only String + enum fields; Ba2IssuesSummaryDto has only u32 + bool fields; EnbValidationResultDto has only enum + enum fields)"
    - "Existing scangame fns (run_setup_checks, needs_path_detection) UNCHANGED (D-08)"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0 (NO -Clean required — scangame.rs is already in build.rs)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "GameFilesWorker doScan body has been extended to invoke at least one of the new bridge fns alongside the existing run_setup_checks call (D-11 consumer migration — exercised in a real product flow, NOT a dormant helper method)"
    - "Cross-binding parity check task confirms the bridged BA2/INI/ENB surface mirrors what classic-scangame-py and classic-node already expose for the same sub-domains (CXXS-04 success criterion 4)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      provides: "Widened scangame bridge with REAL BA2/INI/ENB API mirrors + 2 new CXX shared enums + 4+ new shared struct DTOs (CXXS-04 partial)"
      contains: "ba2_scan_archive"
    - path: "classic-gui/src/workers/gamefilesworker.cpp"
      provides: "D-11 consumer — doScan body extended to invoke at least one new bridge fn (e.g., enb_checker_validate) AS PART OF the existing scan flow"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      to: "classic-scangame-core::{ba2::BA2Scanner, ini::IniValidator, enb::EnbChecker}"
      via: "use classic_scangame_core::{ba2, ini, enb}"
      pattern: "use classic_scangame_core"
    - from: "classic-gui/src/workers/gamefilesworker.cpp"
      to: "classic_cxx_bridge/scangame.h (one of the new fns)"
      via: "C++ method body in doScan calling one of classic::scangame::{ba2_scan_archive, ini_validator_*, enb_checker_validate}"
      pattern: "classic::scangame::(ba2_|ini_|enb_)"
---

<objective>
Widen `src/scangame.rs` from its current 2 entry points to expose BA2, INI, and ENB sub-domain functionality via the REAL `classic-scangame-core` APIs (CXXS-04 part 1 of 2). Add CXX shared enums for `EnbResult`, `EnbConfigResult`, and `IssueSeverity` per D-04/D-07. Add D-11 consumer migration that exercises one of the new bridge fns FROM WITHIN the existing GameFilesWorker::doScan flow (not a dormant helper). Existing fns (`run_setup_checks`, `needs_path_detection`) stay UNCHANGED per D-08.

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan assumed top-level `run_ba2_check`, `run_ini_check`, `run_enb_check` free functions that DO NOT EXIST in `classic-scangame-core`. The REAL APIs are:
- BA2: `BA2Scanner::new()` → `.scan_archive(path: &Path) -> Result<BA2Issues>` (verified at `classic-scangame-core/src/ba2.rs:118-210`)
- INI: `IniValidator::new(game_name)` → `.validate_inis(game_root: &Path) -> Result<String>` for the full report, OR `.detect_all_issues(&HashMap<String, PathBuf>) -> Vec<ConfigIssue>` for structured issues (verified at `classic-scangame-core/src/ini.rs:120-456`)
- ENB: `EnbChecker::new(game_path)` → `.validate() -> EnbValidationResult` (verified at `classic-scangame-core/src/enb.rs:65-141`)
This plan now uses these REAL APIs.

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan defined `IniConfigIssueDto { key, section, found_value, expected_value, severity }`. The REAL `classic_scangame_core::ini::ConfigIssue` (verified at `classic-scangame-core/src/ini.rs:55-78`) has DIFFERENT fields: `file_path: PathBuf`, `section: String`, `setting: String`, `current_value: String`, `recommended_value: String`, `description: String`, `severity: IssueSeverity`. There is no `key`, `found_value`, or `expected_value` — those were invented. This plan now mirrors the REAL field set field-for-field (with `file_path: PathBuf` flattened to `file_path: String` at the bridge boundary).

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan defined `EnbResult` with variants `NotPresent`, `PresentNoConfig`, `PresentWithConfig`, `PresentWithIniOverride` and `EnbConfigResult` with variants `Valid`, `HasConflicts`, `Missing`, `NotApplicable`, plus an `errors: Vec<String>` field on `EnbValidationResult`. The REAL `classic_scangame_core::enb` (verified at `classic-scangame-core/src/enb.rs:21-51`) defines:
- `EnbResult { Present, Partial, NotInstalled }` (3 variants, NOT 4)
- `EnbConfigResult { Valid, NotFound, Unreadable }` (3 variants, NOT 4)
- `EnbValidationResult { binaries: EnbResult, config: EnbConfigResult }` (2 fields, NO `errors` Vec)
This plan now uses the REAL variant sets and the REAL DTO shape.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan added a `doBa2CheckForArchive` helper method to GameFilesWorker that no existing UI flow calls — a dormant helper, not a real consumer. This plan now extends `GameFilesWorker::doScan` itself to invoke at least one new bridge fn AS PART OF the existing scan flow (e.g., calling `enb_checker_validate(gameRoot)` and including the result in the emitted `finished` signal, OR logging a BA2 archive count via `qDebug`). The build proof remains compile + link, but the bridge fn is now exercised by every actual scan run.

**REVIEWS-MODE NOTE (Codex review LOW — CXXS-04 success criterion 4):** A previous version of this plan did not validate against what `classic-scangame-py` and `classic-node` already expose. CXXS-04's literal wording is "orchestration entry points used by Python/Node bindings". This plan adds a cross-binding parity check task: grep both binding crates for BA2/INI/ENB exposure and confirm the bridged surface includes equivalent entry points.

Purpose: CXXS-04 is the largest widening in Phase 2. Splitting into two plans (05 = BA2/INI/ENB; 06 = TOML/Wrye/integrity/setup/crashgen) keeps each plan within the ~50% context budget. Per D-06, sub-domains that produce structured results with potential `Vec<StructWithVec>` patterns are split into row-oriented or scalar-summary DTOs.

Output: Widened scangame bridge with the REAL BA2/INI/ENB surface; one new GameFilesWorker doScan extension consuming a new bridge fn (D-11); cross-binding parity verified; refreshed parity baseline committed atomically.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md

# Source-of-truth Rust crate (REAL APIs — verified by direct read)
@ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/ba2.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/ini.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/enb.rs

# Bridge file this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs

# Reference patterns
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# D-11 consumer migration site (extend doScan body itself)
@classic-gui/src/workers/gamefilesworker.cpp
@classic-gui/src/workers/gamefilesworker.h

# Cross-binding parity check sources (CXXS-04 success criterion 4)
@ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs
@ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs
@ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs
@ClassicLib-rs/node-bindings/classic-node/src/scangame.rs

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- REAL classic-scangame-core surface verified by direct read. -->
<!-- Codex HIGH corrections: BA2 / INI / ENB all use real entry points, real types, real fields. -->

BA2 — REAL API at `classic-scangame-core/src/ba2.rs`:
```rust
pub struct BA2Issues {
    pub tex_dims: Vec<String>,
    pub tex_frmt: Vec<String>,
    pub snd_frmt: Vec<String>,
    pub xse_file: Vec<String>,
}
impl BA2Issues {
    pub fn has_issues(&self) -> bool;
    pub fn total_count(&self) -> usize;
}

pub struct BA2Scanner { /* private */ }
impl BA2Scanner {
    pub fn new() -> Self;
    pub fn with_xse_patterns(xse_patterns: Vec<String>) -> Self;
    pub fn scan_archive(&self, path: &Path) -> Result<BA2Issues>;
    pub fn scan_archives_batch(&self, paths: &[PathBuf]) -> Vec<Result<BA2Issues>>;
    pub fn find_ba2_files(&self, dir: &Path) -> Vec<PathBuf>;
}
```

INI — REAL API at `classic-scangame-core/src/ini.rs`:
```rust
pub enum IssueSeverity { Error, Warning, Info }

pub struct ConfigIssue {
    pub file_path: PathBuf,        // NOT String, NOT key
    pub section: String,
    pub setting: String,            // NOT key, NOT found_value
    pub current_value: String,      // NOT found_value
    pub recommended_value: String,  // NOT expected_value
    pub description: String,        // EXISTS — was dropped by previous plan
    pub severity: IssueSeverity,
}

pub struct IniValidator { /* private */ }
impl IniValidator {
    pub fn new(game_name: impl Into<String>) -> Self;
    pub fn load_ini(&mut self, file_path: &Path) -> Result<()>;
    pub fn detect_all_issues(&self, config_files: &HashMap<String, PathBuf>) -> Vec<ConfigIssue>;
    pub fn validate_inis(&mut self, game_root: &Path) -> Result<String>;  // returns full report text
    pub fn scan_config_files(&self, game_root: &Path) -> Result<HashMap<String, PathBuf>>;
}
```

ENB — REAL API at `classic-scangame-core/src/enb.rs`:
```rust
pub enum EnbResult { Present, Partial, NotInstalled }   // 3 variants
pub enum EnbConfigResult { Valid, NotFound, Unreadable }  // 3 variants

pub struct EnbValidationResult {
    pub binaries: EnbResult,    // NOT enb_result
    pub config: EnbConfigResult, // NOT config_result
    // NO `errors: Vec<String>` field
}

pub struct EnbChecker { /* private */ }
impl EnbChecker {
    pub fn new(game_path: impl AsRef<Path>) -> Self;
    pub fn check_binaries(&self) -> EnbResult;
    pub fn check_config(&self) -> EnbConfigResult;
    pub fn validate(&self) -> EnbValidationResult;
    pub fn format_message(&self, result: &EnbValidationResult) -> String;
}
```

Bridge approach:
- BA2: Free fns that construct a BA2Scanner internally — `ba2_scan_archive_summary(path) -> Ba2IssuesSummaryDto` (counts only) + 4 per-category getters returning `Vec<String>`. Each call re-runs the scan; this is acceptable because per-archive scans are bounded.
- INI: Free fns that construct an IniValidator internally — `ini_validator_validate_inis(game_name, game_root) -> Result<String>` (returns the full report text) + `ini_validator_detect_all_issues_for_root(game_name, game_root) -> Vec<IniConfigIssueDto>` (does the scan + detect in one call, returning structured issues using REAL field set).
- ENB: Free fn `enb_checker_validate(game_path) -> EnbValidationResultDto { binaries, config }` (REAL field set, no fictional `errors` Vec).
- Bridge `IniConfigIssueDto` mirrors REAL `ConfigIssue` field-for-field (with `file_path: PathBuf` → `file_path: String`).

ALL DTOs in this plan are Pitfall 6 CLEAR:
- Ba2IssuesSummaryDto: only u32 + bool fields
- IniConfigIssueDto: only String + IssueSeverity (shared enum) fields — no Vec
- EnbValidationResultDto: only EnbResult + EnbConfigResult (shared enums) — no Vec
- The 4 BA2 per-category getters return `Vec<String>` directly (NOT `Vec<StructWithVec>`)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scangame.rs with REAL BA2 + INI + ENB APIs (Codex HIGH corrections) + shared enums + DTOs + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs (READ — confirm pub re-exports for ba2, ini, enb sub-modules)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/ba2.rs (READ ENTIRELY — confirm BA2Scanner::new() / scan_archive(&Path) API; confirm BA2Issues field names: tex_dims, tex_frmt, snd_frmt, xse_file)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/ini.rs (READ ENTIRELY — confirm IniValidator::new(game_name) / validate_inis(&Path) / detect_all_issues(&HashMap) API; confirm REAL ConfigIssue fields: file_path, section, setting, current_value, recommended_value, description, severity; confirm IssueSeverity variants)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/enb.rs (READ ENTIRELY — confirm EnbChecker::new(path) / validate() API; confirm EnbResult variants: Present, Partial, NotInstalled; confirm EnbConfigResult variants: Valid, NotFound, Unreadable; confirm EnbValidationResult { binaries, config } — NO errors Vec)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs (current 2-fn surface — KEEP run_setup_checks and needs_path_detection unchanged per D-08; ADD all new fns BELOW the existing block)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs (template for nested-but-flat shared struct using YamlDataModSolutionEntry)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 05" (Codex HIGH corrections)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-05, D-06, D-07, D-08, D-12
  </read_first>

  <behavior>
    - Test: `ba2_scan_archive_summary("nonexistent.ba2")` returns Ba2IssuesSummaryDto with `has_issues: false` and all counts = 0 (fail-soft on missing archive — BA2Scanner::scan_archive returns Err which the bridge catches).
    - Test: `ba2_get_tex_dims_for_archive("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `ba2_get_tex_frmt_for_archive("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `ba2_get_snd_frmt_for_archive("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `ba2_get_xse_files_for_archive("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `ini_validator_validate_inis("Fallout4", "nonexistent\\dir")` returns Err with non-empty message OR Ok with a report describing missing files (depends on real validator behavior — assert one or the other holds).
    - Test: `ini_validator_detect_all_issues_for_root("Fallout4", "nonexistent\\dir")` returns empty Vec or a Vec containing only file-not-found issues.
    - Test: `enb_checker_validate("nonexistent\\path")` returns EnbValidationResultDto with `binaries: EnbResult::NotInstalled` (REAL variant name) and `config: EnbConfigResult::NotFound` (REAL variant name).
    - Test: `enb_checker_validate(temp_dir_with_d3d11_and_compiler_and_enbseries)` returns EnbValidationResultDto with `binaries: EnbResult::Present` and `config: EnbConfigResult::Valid` (verified end-to-end against the same fixture pattern as classic-scangame-core/src/enb.rs::test_enb_present).
    - Test (existing — DO NOT BREAK): `run_setup_checks(...)` and `needs_path_detection(...)` still work and return their original SetupCheckResult / PathDetectionNeeds shapes.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`. KEEP the existing module imports, the existing wrapper fns for `run_setup_checks` and `needs_path_detection`, and the existing `#[cxx::bridge(namespace = "classic::scangame")]` block UNCHANGED — only ADD to it.

  Step 1 — Add new core imports near the top:
  ```rust
  use std::collections::HashMap;
  use std::path::{Path, PathBuf};
  use classic_scangame_core::{
      ba2::{BA2Scanner, BA2Issues as CoreBA2Issues},
      ini::{IniValidator, ConfigIssue as CoreIniConfigIssue, IssueSeverity as CoreIniIssueSeverity},
      enb::{EnbChecker, EnbValidationResult as CoreEnbValidationResult,
            EnbResult as CoreEnbResult, EnbConfigResult as CoreEnbConfigResult},
  };
  ```

  Step 2 — Add wrapper fns + enum mapping helpers ABOVE the bridge block (after the existing run_setup_checks/needs_path_detection):

  ```rust
  // ─────────────────────────────────────────────────────────────────────
  // BA2 sub-domain — REAL BA2Scanner API (Codex HIGH correction)
  // ─────────────────────────────────────────────────────────────────────

  fn run_ba2_scan(path_str: &str) -> Option<CoreBA2Issues> {
      if path_str.is_empty() {
          return None;
      }
      let scanner = BA2Scanner::new();
      scanner.scan_archive(Path::new(path_str)).ok()
  }

  fn ba2_scan_archive_summary(archive_path: &str) -> ffi::Ba2IssuesSummaryDto {
      let issues = match run_ba2_scan(archive_path) {
          Some(i) => i,
          None => return ffi::Ba2IssuesSummaryDto {
              tex_dim_count: 0,
              tex_fmt_count: 0,
              snd_fmt_count: 0,
              xse_file_count: 0,
              total: 0,
              has_issues: false,
          },
      };
      let tex = issues.tex_dims.len() as u32;
      let fmt = issues.tex_frmt.len() as u32;
      let snd = issues.snd_frmt.len() as u32;
      let xse = issues.xse_file.len() as u32;
      let total = tex + fmt + snd + xse;
      ffi::Ba2IssuesSummaryDto {
          tex_dim_count: tex,
          tex_fmt_count: fmt,
          snd_fmt_count: snd,
          xse_file_count: xse,
          total,
          has_issues: total > 0,
      }
  }

  fn ba2_get_tex_dims_for_archive(archive_path: &str) -> Vec<String> {
      run_ba2_scan(archive_path).map(|i| i.tex_dims).unwrap_or_default()
  }
  fn ba2_get_tex_frmt_for_archive(archive_path: &str) -> Vec<String> {
      run_ba2_scan(archive_path).map(|i| i.tex_frmt).unwrap_or_default()
  }
  fn ba2_get_snd_frmt_for_archive(archive_path: &str) -> Vec<String> {
      run_ba2_scan(archive_path).map(|i| i.snd_frmt).unwrap_or_default()
  }
  fn ba2_get_xse_files_for_archive(archive_path: &str) -> Vec<String> {
      run_ba2_scan(archive_path).map(|i| i.xse_file).unwrap_or_default()
  }

  // ─────────────────────────────────────────────────────────────────────
  // INI sub-domain — REAL IniValidator API + REAL ConfigIssue field set
  // (Codex HIGH correction)
  // ─────────────────────────────────────────────────────────────────────

  fn map_ini_severity(s: CoreIniIssueSeverity) -> ffi::IssueSeverity {
      match s {
          CoreIniIssueSeverity::Error => ffi::IssueSeverity::Error,
          CoreIniIssueSeverity::Warning => ffi::IssueSeverity::Warning,
          CoreIniIssueSeverity::Info => ffi::IssueSeverity::Info,
      }
  }

  fn convert_ini_issue(issue: CoreIniConfigIssue) -> ffi::IniConfigIssueDto {
      // REAL ConfigIssue fields per classic-scangame-core/src/ini.rs:55-78
      ffi::IniConfigIssueDto {
          file_path: issue.file_path.to_string_lossy().to_string(),
          section: issue.section,
          setting: issue.setting,
          current_value: issue.current_value,
          recommended_value: issue.recommended_value,
          description: issue.description,
          severity: map_ini_severity(issue.severity),
      }
  }

  fn ini_validator_validate_inis(game_name: &str, game_root: &str) -> Result<String, String> {
      if game_root.is_empty() {
          return Err("ini_validator_validate_inis: empty game_root".to_string());
      }
      let mut validator = IniValidator::new(game_name);
      validator
          .validate_inis(Path::new(game_root))
          .map_err(|e| e.to_string())
  }

  fn ini_validator_detect_all_issues_for_root(
      game_name: &str,
      game_root: &str,
  ) -> Vec<ffi::IniConfigIssueDto> {
      if game_root.is_empty() {
          return Vec::new();
      }
      let validator = IniValidator::new(game_name);
      let config_files = match validator.scan_config_files(Path::new(game_root)) {
          Ok(map) => map,
          Err(_) => return Vec::new(),
      };
      validator
          .detect_all_issues(&config_files)
          .into_iter()
          .map(convert_ini_issue)
          .collect()
  }

  // ─────────────────────────────────────────────────────────────────────
  // ENB sub-domain — REAL EnbChecker API (Codex HIGH correction)
  // ─────────────────────────────────────────────────────────────────────

  fn map_enb_result(r: CoreEnbResult) -> ffi::EnbResult {
      // REAL variants: Present, Partial, NotInstalled
      match r {
          CoreEnbResult::Present => ffi::EnbResult::Present,
          CoreEnbResult::Partial => ffi::EnbResult::Partial,
          CoreEnbResult::NotInstalled => ffi::EnbResult::NotInstalled,
      }
  }
  fn map_enb_config_result(r: CoreEnbConfigResult) -> ffi::EnbConfigResult {
      // REAL variants: Valid, NotFound, Unreadable
      match r {
          CoreEnbConfigResult::Valid => ffi::EnbConfigResult::Valid,
          CoreEnbConfigResult::NotFound => ffi::EnbConfigResult::NotFound,
          CoreEnbConfigResult::Unreadable => ffi::EnbConfigResult::Unreadable,
      }
  }

  fn enb_checker_validate(game_path: &str) -> ffi::EnbValidationResultDto {
      let path_arg = if game_path.is_empty() { "." } else { game_path };
      let checker = EnbChecker::new(path_arg);
      let result: CoreEnbValidationResult = checker.validate();
      // REAL field set: binaries + config (NO errors Vec)
      ffi::EnbValidationResultDto {
          binaries: map_enb_result(result.binaries),
          config: map_enb_config_result(result.config),
      }
  }
  ```

  Step 3 — EXTEND the existing `#[cxx::bridge(namespace = "classic::scangame")]` block. Add the three new shared enums + four new shared structs + new extern "Rust" declarations. KEEP all existing items.

  ```rust
  #[cxx::bridge(namespace = "classic::scangame")]
  mod ffi {
      // EXISTING shared structs (KEEP UNCHANGED — D-08)
      struct SetupCheckResult { /* unchanged from current scangame.rs */ }
      struct PathDetectionNeeds { /* unchanged */ }

      // NEW — D-04/D-07 shared enums (REAL variants per Codex HIGH correction)
      #[repr(u8)]
      enum IssueSeverity {
          Error = 0,
          Warning = 1,
          Info = 2,
      }

      // REAL EnbResult variants (Present / Partial / NotInstalled)
      #[repr(u8)]
      enum EnbResult {
          Present = 0,
          Partial = 1,
          NotInstalled = 2,
      }

      // REAL EnbConfigResult variants (Valid / NotFound / Unreadable)
      #[repr(u8)]
      enum EnbConfigResult {
          Valid = 0,
          NotFound = 1,
          Unreadable = 2,
      }

      // NEW — flat DTOs (Pitfall 6 CLEAR)
      struct Ba2IssuesSummaryDto {
          tex_dim_count: u32,
          tex_fmt_count: u32,
          snd_fmt_count: u32,
          xse_file_count: u32,
          total: u32,
          has_issues: bool,
      }

      // REAL ConfigIssue field set (Codex HIGH correction):
      // file_path, section, setting, current_value, recommended_value, description, severity
      // file_path: PathBuf → String at the bridge boundary
      struct IniConfigIssueDto {
          file_path: String,
          section: String,
          setting: String,
          current_value: String,
          recommended_value: String,
          description: String,
          severity: IssueSeverity,
      }

      // REAL EnbValidationResult field set (Codex HIGH correction):
      // binaries + config (NO errors Vec)
      struct EnbValidationResultDto {
          binaries: EnbResult,
          config: EnbConfigResult,
      }

      extern "Rust" {
          // EXISTING (KEEP UNCHANGED — D-08)
          fn run_setup_checks(/* unchanged signature */) -> SetupCheckResult;
          fn needs_path_detection(/* unchanged signature */) -> PathDetectionNeeds;

          // NEW — BA2 (REAL BA2Scanner API behind the scenes)
          fn ba2_scan_archive_summary(archive_path: &str) -> Ba2IssuesSummaryDto;
          fn ba2_get_tex_dims_for_archive(archive_path: &str) -> Vec<String>;
          fn ba2_get_tex_frmt_for_archive(archive_path: &str) -> Vec<String>;
          fn ba2_get_snd_frmt_for_archive(archive_path: &str) -> Vec<String>;
          fn ba2_get_xse_files_for_archive(archive_path: &str) -> Vec<String>;

          // NEW — INI (REAL IniValidator API behind the scenes)
          fn ini_validator_validate_inis(game_name: &str, game_root: &str) -> Result<String>;
          fn ini_validator_detect_all_issues_for_root(
              game_name: &str,
              game_root: &str,
          ) -> Vec<IniConfigIssueDto>;

          // NEW — ENB (REAL EnbChecker API behind the scenes)
          fn enb_checker_validate(game_path: &str) -> EnbValidationResultDto;
      }
  }
  ```

  Step 4 — EXTEND (or add) `#[cfg(test)] mod tests` block with new tests:

  ```rust
  #[cfg(test)]
  mod tests {
      use super::*;
      use std::fs;
      use tempfile::TempDir;

      // Existing tests preserved …

      #[test]
      fn test_ba2_scan_archive_summary_nonexistent_returns_no_issues() {
          let r = ba2_scan_archive_summary("nonexistent.ba2");
          assert!(!r.has_issues);
          assert_eq!(r.total, 0);
      }

      #[test]
      fn test_ba2_get_categories_empty_for_nonexistent() {
          assert!(ba2_get_tex_dims_for_archive("nonexistent.ba2").is_empty());
          assert!(ba2_get_tex_frmt_for_archive("nonexistent.ba2").is_empty());
          assert!(ba2_get_snd_frmt_for_archive("nonexistent.ba2").is_empty());
          assert!(ba2_get_xse_files_for_archive("nonexistent.ba2").is_empty());
      }

      #[test]
      fn test_ini_validator_validate_inis_empty_root_errors() {
          assert!(ini_validator_validate_inis("Fallout4", "").is_err());
      }

      #[test]
      fn test_ini_validator_detect_all_issues_empty_root_returns_empty() {
          assert!(ini_validator_detect_all_issues_for_root("Fallout4", "").is_empty());
      }

      #[test]
      fn test_enb_checker_validate_nonexistent_real_variants() {
          // Codex HIGH correction: REAL EnbResult/EnbConfigResult variants
          let temp_dir = TempDir::new().unwrap();
          let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
          assert!(matches!(r.binaries, ffi::EnbResult::NotInstalled));
          assert!(matches!(r.config, ffi::EnbConfigResult::NotFound));
      }

      #[test]
      fn test_enb_checker_validate_present_real_variants() {
          // Codex HIGH correction: mirrors classic-scangame-core/src/enb.rs::test_enb_present
          let temp_dir = TempDir::new().unwrap();
          fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
          fs::write(temp_dir.path().join("d3dcompiler_46e.dll"), b"x").unwrap();
          fs::write(temp_dir.path().join("enbseries.ini"), b"[ENB]\n").unwrap();
          let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
          assert!(matches!(r.binaries, ffi::EnbResult::Present));
          assert!(matches!(r.config, ffi::EnbConfigResult::Valid));
      }

      #[test]
      fn test_enb_checker_validate_partial_real_variant() {
          let temp_dir = TempDir::new().unwrap();
          fs::write(temp_dir.path().join("d3d11.dll"), b"x").unwrap();
          // Missing d3dcompiler → Partial
          let r = enb_checker_validate(&temp_dir.path().to_string_lossy());
          assert!(matches!(r.binaries, ffi::EnbResult::Partial));
      }
  }
  ```

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` and confirm all pass (existing + new). Run `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`.

  IMPORTANT: Add `tempfile = { workspace = true }` to `classic-cpp-bridge/Cargo.toml [dev-dependencies]` if not present.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'fn ba2_scan_archive_summary|fn ba2_get_(tex_dims|tex_frmt|snd_frmt|xse_files)_for_archive' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 5+ wrapper definitions and 5+ extern declarations
    - `git grep -n 'BA2Scanner::new' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least one match (proves REAL API is used)
    - `git grep -nE 'fn ini_validator_validate_inis|fn ini_validator_detect_all_issues' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 2+ wrapper definitions
    - `git grep -n 'IniValidator::new' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least one match
    - `git grep -nE 'file_path: String|setting: String|current_value: String|recommended_value: String|description: String' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least 5 lines (proves REAL ConfigIssue field set)
    - `git grep -n 'fn enb_checker_validate' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 2+ matches (definition + extern)
    - `git grep -n 'EnbChecker::new' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least one match
    - `git grep -nE 'Present = 0|Partial = 1|NotInstalled = 2' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns the REAL EnbResult variants (Codex HIGH correction)
    - `git grep -nE 'Valid = 0|NotFound = 1|Unreadable = 2' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns the REAL EnbConfigResult variants
    - `git grep -nE 'NotPresent|PresentNoConfig|PresentWithConfig|HasConflicts|NotApplicable|errors_csv' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (the fictional variants/fields are gone)
    - `git grep -nE 'key:|found_value:|expected_value:' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (the fictional ConfigIssue field names are gone)
    - `git grep -n 'fn run_setup_checks' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'fn needs_path_detection' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` exits 0 with at least 9 passing tests
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 violations)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scangame.rs` exposes BA2/INI/ENB sub-domain bridge fns using REAL classic-scangame-core APIs (Codex HIGH corrections), all Rust-side tests pass, and no existing fns were modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Cross-binding parity check + D-11 consumer migration in GameFilesWorker::doScan body itself + incremental builds + D-09 baseline refresh + commit</name>

  <files>
    - classic-gui/src/workers/gamefilesworker.cpp
    - classic-gui/src/workers/gamefilesworker.h
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/workers/gamefilesworker.cpp (current state — has doScan calling classic::scangame::run_setup_checks; this plan EXTENDS doScan body, NOT adds a separate dormant helper)
    - classic-gui/src/workers/gamefilesworker.h (declared methods)
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs (cross-check — what BA2 API does Python expose?)
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs (cross-check — what INI API does Python expose?)
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs (cross-check — what ENB API does Python expose?)
    - ClassicLib-rs/node-bindings/classic-node/src/scangame.rs (cross-check — what scangame API does Node expose? Look for `JsBa2Scanner`, `check_enb`, etc.)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 05" Codex MEDIUM (D-11 dormant helper) and LOW (cross-binding parity)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08, D-09, D-11
  </read_first>

  <action>
  ## Part A — Cross-binding parity check (Codex LOW correction — CXXS-04 success criterion 4)

  Run these greps to confirm the bridged surface mirrors what Python and Node expose:

  ```bash
  # Python BA2 exposure
  grep -nE '#\[pyfunction\]|#\[pymethods\]|fn (scan|check)' ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs
  # Python INI exposure
  grep -nE '#\[pyfunction\]|#\[pymethods\]|fn (validate|detect)' ClassicLib-rs/python-bindings/classic-scangame-py/src/ini.rs
  # Python ENB exposure
  grep -nE '#\[pyfunction\]|#\[pymethods\]|fn (check|validate)' ClassicLib-rs/python-bindings/classic-scangame-py/src/enb.rs

  # Node BA2/INI/ENB exposure
  grep -nE '#\[napi\]|fn (scan_|check_|validate_)' ClassicLib-rs/node-bindings/classic-node/src/scangame.rs
  ```

  Document the result in the SUMMARY.md: confirm that the bridged BA2/INI/ENB entry points correspond to the Python/Node exposed entry points (modulo API style differences — Node exposes `JsBa2Scanner` class; CXX exposes free fns that internally construct a BA2Scanner; both surfaces wrap the same core type).

  If a Python or Node binding exposes a sub-domain method that the CXX bridge does NOT cover (e.g., batch scan), document it in the SUMMARY.md as a known follow-up — but do NOT block this plan on it. Phase 2's CXXS-04 success criterion is "exposes the same orchestration entry points", which means the same per-domain checker functionality is reachable from C++; not strict 1:1 method parity.

  ## Part B — D-11 consumer migration in doScan body (Codex MEDIUM correction — exercise FROM the existing flow)

  Edit `classic-gui/src/workers/gamefilesworker.h`. NO new public method is added — the new bridge fns are invoked inside the existing `doScan` method body. Add a new private helper signature ONLY if needed for code organization.

  Edit `classic-gui/src/workers/gamefilesworker.cpp`. Modify the existing `doScan` method body to call at least one new bridge fn AND surface the result via the existing emission flow:

  ```cpp
  #include "gamefilesworker.h"
  #include "core/rust_qt_bridge.h"

  #include "rust/cxx.h"
  #include "classic_cxx_bridge/scangame.h"

  GameFilesWorker::GameFilesWorker(QObject* parent)
      : QObject(parent) {}

  void GameFilesWorker::doScan(const QString& gameExePath,
                               const QString& gameRoot,
                               const QString& docsPath,
                               const QString& gameName) {
      emit progress(-1.0f, QStringLiteral("Running game file setup checks..."));

      try {
          // EXISTING (D-08 preserved) — combined-output text from setup orchestrator
          auto result = classic::scangame::run_setup_checks(
              classic::toRustString(gameExePath),
              classic::toRustString(gameRoot),
              classic::toRustString(docsPath),
              classic::toRustString(gameName)
          );

          // D-11 / CXXS-04 consumer migration (Codex MEDIUM correction):
          // Exercise the new ENB structured DTO bridge as part of the
          // existing scan flow. The result is appended to the combined
          // output so users see it in the same Results view.
          auto enb_result = classic::scangame::enb_checker_validate(
              classic::toRustString(gameRoot)
          );
          QString enbSummary;
          switch (enb_result.binaries) {
              case classic::scangame::EnbResult::Present:
                  enbSummary = QStringLiteral("\n[ENB] Binaries: PRESENT");
                  break;
              case classic::scangame::EnbResult::Partial:
                  enbSummary = QStringLiteral("\n[ENB] Binaries: PARTIAL (some files missing)");
                  break;
              case classic::scangame::EnbResult::NotInstalled:
                  enbSummary = QStringLiteral("\n[ENB] Binaries: NOT INSTALLED");
                  break;
              default:
                  enbSummary = QStringLiteral("\n[ENB] Binaries: UNKNOWN");
                  break;
          }
          switch (enb_result.config) {
              case classic::scangame::EnbConfigResult::Valid:
                  enbSummary += QStringLiteral(" | Config: VALID");
                  break;
              case classic::scangame::EnbConfigResult::NotFound:
                  enbSummary += QStringLiteral(" | Config: NOT FOUND");
                  break;
              case classic::scangame::EnbConfigResult::Unreadable:
                  enbSummary += QStringLiteral(" | Config: UNREADABLE");
                  break;
              default:
                  enbSummary += QStringLiteral(" | Config: UNKNOWN");
                  break;
          }

          QString combinedText = classic::toQString(result.combined_output) + enbSummary;

          emit progress(100.0f, QStringLiteral("Complete"));
          emit finished(
              combinedText,
              result.has_errors,
              result.total_checks
          );

      } catch (const rust::Error& e) {
          emit error(QString::fromUtf8(e.what()));
      } catch (const std::exception& e) {
          emit error(QString::fromUtf8(e.what()));
      }
  }
  ```

  This change EXTENDS the existing doScan flow — every actual game-files scan now exercises `enb_checker_validate` and the user sees the ENB summary in the Results tab. This is a meaningful consumer migration, not a dormant helper.

  ## Part C — Incremental builds (NO -Clean required)

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
  ```

  Both must exit 0.

  ## Part D — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part E — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`
  - `classic-gui/src/workers/gamefilesworker.cpp`
  - `classic-gui/src/workers/gamefilesworker.h` (only if signature changed; otherwise omit)
  - All 4 baseline artifacts

  Commit message: `Feat(02-05): widen scangame bridge with REAL BA2/INI/ENB sub-domain APIs` — body mentions CXXS-04 (partial), D-04, D-05, D-06, D-07, D-09, D-11 and explicitly notes the Codex HIGH corrections for the BA2/INI/ENB API alignment plus the D-11 in-flow consumer migration.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'classic::scangame::(ba2_scan_archive_summary|ini_validator_validate_inis|ini_validator_detect_all_issues_for_root|enb_checker_validate)' classic-gui/src/workers/gamefilesworker.cpp` returns at least one match
    - `git grep -n 'enb_checker_validate' classic-gui/src/workers/gamefilesworker.cpp` returns at least one match (the new in-flow consumer)
    - `git grep -n 'EnbResult::Present\|EnbResult::Partial\|EnbResult::NotInstalled' classic-gui/src/workers/gamefilesworker.cpp` returns at least 3 matches (proves the REAL variants are switched on)
    - `git grep -n 'doBa2CheckForArchive\|doIniCheckForGame' classic-gui/src/workers/gamefilesworker.h` returns NOTHING (the dormant-helper-method approach is replaced)
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "scangame"` for the new fns + 3 new enums + 3 new structs
    - `git log -1 --stat` shows the commit touches both Rust source AND the C++ consumer migration AND the parity baseline atomically
  </acceptance_criteria>

  <done>
    Plan 02-05 complete — scangame BA2/INI/ENB sub-domains are bridged using REAL classic-scangame-core APIs (Codex HIGH corrections), GameFilesWorker::doScan body itself exercises enb_checker_validate as part of every scan run (Codex MEDIUM correction — not a dormant helper), cross-binding parity is documented (Codex LOW correction), both builds pass, parity gate at 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` — exits 0 (incremental OK — no new build.rs entries)
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` — exits 0
4. Parity gate at 0 drift after --update-baseline
5. New BA2/INI/ENB fns appear in `include/classic_cxx_bridge/scangame.h` after the build
6. GameFilesWorker::doScan body itself calls enb_checker_validate (D-11 in-flow consumer)
7. Cross-binding parity check confirms the bridged surface mirrors Python/Node coverage

Validation Architecture (per 02-VALIDATION.md row 2-05-01): `cargo test -p classic-cpp-bridge scangame::tests` + incremental build_cli.ps1 -Test + parity gate.
</verification>

<success_criteria>
- src/scangame.rs widened with BA2/INI/ENB sub-domain entry points using REAL classic-scangame-core APIs (Codex HIGH corrections — BA2Scanner / IniValidator / EnbChecker)
- IniConfigIssueDto mirrors REAL ConfigIssue fields (file_path, section, setting, current_value, recommended_value, description, severity)
- EnbValidationResultDto has REAL field set (binaries + config; NO errors Vec)
- EnbResult shared enum has REAL variants (Present, Partial, NotInstalled)
- EnbConfigResult shared enum has REAL variants (Valid, NotFound, Unreadable)
- All Pitfall 6 CLEAR
- Existing fns (run_setup_checks, needs_path_detection) UNCHANGED (D-08)
- GameFilesWorker::doScan body itself extends to call enb_checker_validate (D-11 in-flow consumer migration — Codex MEDIUM correction)
- Cross-binding parity check documented (Codex LOW correction)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-05-SUMMARY.md` documenting:
- Confirmation that the bridged surface uses REAL classic-scangame-core APIs (BA2Scanner, IniValidator, EnbChecker — Codex HIGH corrections)
- Confirmation that IniConfigIssueDto matches REAL ConfigIssue field-for-field
- Confirmation that EnbResult/EnbConfigResult use REAL variants
- Confirmation that GameFilesWorker::doScan body itself exercises enb_checker_validate (D-11 in-flow, NOT dormant helper — Codex MEDIUM correction)
- Cross-binding parity check results: list which Python/Node entry points correspond to which CXX bridge fns; note any Python/Node exposure not covered by CXX (follow-up backlog)
- Pitfall 6 verification result (no `Vec<StructWithVec>` patterns in any new DTO)
- Incremental build outcome
</output>
