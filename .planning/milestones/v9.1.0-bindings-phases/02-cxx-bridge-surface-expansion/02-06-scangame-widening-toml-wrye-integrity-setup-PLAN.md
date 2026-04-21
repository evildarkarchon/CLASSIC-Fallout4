---
phase: 02-cxx-bridge-surface-expansion
plan: 06
type: execute
wave: 3
depends_on:
  - 02-cxx-bridge-surface-expansion/05
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  - classic-gui/src/workers/gamefilesworker.cpp
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
    - "src/scangame.rs exposes TOML sub-domain via CrashgenChecker wrapper: crashgen_checker_check(plugins_path, crashgen_name) returning the (report_text, issues) tuple flattened into a CrashgenCheckResultDto + per-call get_crashgen_issues helper returning Vec<TomlConfigIssueDto>"
    - "TomlConfigIssueDto mirrors REAL classic_scangame_core::toml::TomlConfigIssue field-for-field: file_path, section, setting, current_value, recommended_value, description, severity (NOT the fictional key/found_value/expected_value field set)"
    - "src/scangame.rs exposes Wrye sub-domain via WryeBashParser wrapper. To clear Pitfall 6 (Vec<StructWithVec>), Wrye returns ROW-ORIENTED data: wrye_parse_html_rows(html_content) returns Vec<WryeIssueRowDto> where each row has section_title + plugin + warning_message + severity (one row per (issue, plugin) pair). NO Vec<String> field nested inside a returned struct vec."
    - "src/scangame.rs exposes Integrity sub-domain via GameIntegrityChecker wrapper: integrity_run_all_checks(game_exe_path, valid_hashes, root_name) returning Vec<IntegrityCheckResultDto> with REAL fields (is_valid: bool, message: String, check_type: CheckType) — NOT the fictional `passed: bool`"
    - "CheckType shared enum has the REAL 2 variants (ExecutableVersion, InstallationLocation) — NOT the fictional 5-variant Existence/Format/Content/Structure/Custom set"
    - "src/scangame.rs exposes Setup orchestrator structured DTO: scangame_run_setup_structured(SetupCheckConfig args) returning ScanGameSetupDto computed from REAL SetupCheckResults vector lengths (integrity_results.len + xse_results.len + docs_results.len, plus errors.len)"
    - "src/scangame.rs exposes Crashgen orchestrator: crashgen_orchestrator_check(plugins_path, crashgen_name) returning CrashgenReportSummaryDto with REAL CrashgenReport field set (message, crashgen_name, config_path, issue_count, installed_plugin_count) + crashgen_orchestrator_get_issues helper returning Vec<TomlConfigIssueDto>"
    - "All new shared structs are flat (Pitfall 6 CLEAR — verified per the Wrye flattening to row-DTO and the per-getter split for Vec<String> fields)"
    - "Existing fns (run_setup_checks, needs_path_detection, plus all BA2/INI/ENB fns from plan 02-05) UNCHANGED"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift"
    - "GameFilesWorker::doScan body further extends to call one of THIS plan's new bridge fns (e.g., crashgen_orchestrator_check) — D-11 in-flow consumer #2"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      provides: "Widened scangame bridge with REAL TOML/Wrye/Integrity/Setup/Crashgen sub-domain APIs (CXXS-04 complete)"
      contains: "crashgen_orchestrator_check"
    - path: "classic-gui/src/workers/gamefilesworker.cpp"
      provides: "D-11 in-flow consumer #2 — doScan body extended to call one of THIS plan's new bridge fns"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      to: "classic-scangame-core::{toml::CrashgenChecker, wrye::WryeBashParser, integrity::GameIntegrityChecker, setup::run_combined_checks, crashgen_orchestrator::CrashgenCheckOrchestrator}"
      via: "use classic_scangame_core::{toml, wrye, integrity, setup, crashgen_orchestrator}"
      pattern: "use classic_scangame_core"
---

<objective>
Complete CXXS-04 by widening `src/scangame.rs` with the remaining sub-domain entry points using the REAL `classic-scangame-core` APIs: TOML (CrashgenChecker), Wrye (WryeBashParser), Integrity (GameIntegrityChecker), Setup orchestrator (run_combined_checks structured DTO alongside existing combined-output), and CrashgenOrchestrator (CrashgenCheckOrchestrator). Adds CXX shared enums for `TomlIssueSeverity`, `WryeSeverity`, `CheckType` per D-04/D-07. Per Pitfall 6, Wrye is flattened to a row-oriented DTO (one row per `(WryeIssue, plugin)` pair) to avoid `Vec<StructWithVec>`. Adds at least one new D-11 consumer call site IN THE doScan FLOW (not a dormant helper).

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan defined `run_toml_check`, `run_wrye_check`, `run_integrity_check`, and `run_crashgen_check` as free functions that DO NOT EXIST in `classic-scangame-core`. The REAL APIs are:
- TOML: `CrashgenChecker::new(plugins_path: &Path, crashgen_name)` → `.check() -> Result<(String, Vec<TomlConfigIssue>)>` (verified at `classic-scangame-core/src/toml.rs:131-663`)
- Wrye: `WryeBashParser::new(wrye_warnings: HashMap<String, String>)` → `.parse(html_content: &str) -> Vec<WryeIssue>` (verified at `classic-scangame-core/src/wrye.rs:88-117`)
- Integrity: `GameIntegrityChecker::new(IntegrityConfig)` → `.run_all_checks() -> Result<Vec<IntegrityCheckResult>, _>` (verified at `classic-scangame-core/src/integrity.rs:122-297`)
- Setup orchestrator: `run_combined_checks(config: &SetupCheckConfig) -> SetupCheckResults` (verified at `classic-scangame-core/src/setup.rs:165`)
- Crashgen: `CrashgenCheckOrchestrator::check(plugins_path: &Path, crashgen_name: &str) -> Result<CrashgenReport>` (verified at `classic-scangame-core/src/crashgen_orchestrator.rs:104`)
This plan now uses the REAL APIs.

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan defined fictional struct field sets:
- `WryeIssue { plugin_name, issue_type, severity, details }` — REAL is `WryeIssue { section_title: String, plugins: Vec<String>, warning_message: Option<String>, severity: WryeSeverity }` (verified at `wrye.rs:53-65`)
- `IntegrityCheckResult { check_type, passed, message }` — REAL is `IntegrityCheckResult { is_valid: bool, message: String, check_type: CheckType }` (verified at `integrity.rs:89-98`)
- `CheckType { Existence, Format, Content, Structure, Custom }` — REAL is `CheckType { ExecutableVersion, InstallationLocation }` (verified at `integrity.rs:101-108`)
- `CrashgenReport { crashgen_name, is_installed, has_config, config_issues, version_string, status_message }` — REAL is `CrashgenReport { message: String, issues: Vec<TomlConfigIssue>, crashgen_name: String, config_path: Option<PathBuf>, installed_plugins: Vec<String> }` (verified at `crashgen_orchestrator.rs:49-65`)
- `SetupCheckResults` was assumed to have `combined()` and `error_count()` getters — REAL has fields `integrity_results: Vec<String>`, `xse_results: Vec<String>`, `docs_results: Vec<String>`, `errors: Vec<String>` and methods `combined()`, `has_errors()`, `total_checks()` (computed from vec lengths) (verified at `setup.rs:88-129`)

This plan uses the REAL field sets.

**REVIEWS-MODE NOTE (Codex review HIGH — Pitfall 6):** The REAL `WryeIssue` contains `plugins: Vec<String>`. Returning `Vec<WryeIssueDto>` with that Vec field nested is the forbidden `Vec<StructWithVec>` pattern. This plan flattens Wrye to a ROW-ORIENTED `WryeIssueRowDto { section_title, plugin, warning_message_or_empty, has_warning_message, severity }` with one row per (issue, plugin) pair. The bridge fn returns `Vec<WryeIssueRowDto>` directly — no nested Vec.

**REVIEWS-MODE NOTE (Codex review LOW):** A previous version of this plan referenced `02-05-PLAN.md` in the dependency chain. The valid dependency reference is `02-cxx-bridge-surface-expansion/05` (the wave assignment). This plan uses the proper canonical reference.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan added a dormant `doStructuredSetupCheck` helper to GameFilesWorker. This plan extends `GameFilesWorker::doScan` body itself to call one of this plan's new bridge fns (alongside the BA2/ENB call from plan 02-05) — proving the new namespace is exercised by every actual scan, not just compile-tested.

Purpose: Finish CXXS-04. Each sub-domain wraps the REAL core API behind a free fn that constructs the necessary checker/parser/orchestrator type internally.

Output: scangame bridge with the full CXXS-04 surface using REAL APIs and Pitfall-6-clean DTOs; another in-flow D-11 consumer migration in doScan; refreshed parity baseline committed atomically.
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
@.planning/phases/02-cxx-bridge-surface-expansion/02-05-scangame-widening-ba2-ini-enb-PLAN.md

# Source-of-truth Rust crate (REAL APIs — verified by direct read)
@ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/wrye.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/integrity.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/setup.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs

# Bridge file this plan widens (already widened with BA2/INI/ENB by Plan 02-05)
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs

# D-11 consumer migration site (extend doScan body further)
@classic-gui/src/workers/gamefilesworker.cpp

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- REAL classic-scangame-core surface verified by direct read. -->

TOML — REAL API at `classic-scangame-core/src/toml.rs`:
```rust
pub enum TomlIssueSeverity { Error, Warning, Info }

pub struct TomlConfigIssue {
    pub file_path: PathBuf,        // SAME shape as INI ConfigIssue
    pub section: String,
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: TomlIssueSeverity,
}

pub struct CrashgenChecker { /* private */ }
impl CrashgenChecker {
    pub fn new(plugins_path: &Path, crashgen_name: impl Into<String>) -> Self;
    pub fn config_file(&self) -> Option<&PathBuf>;
    pub fn installed_plugins(&self) -> &[String];
    pub fn check(&mut self) -> Result<(String, Vec<TomlConfigIssue>)>;  // returns (report_text, issues)
}
```

Wrye — REAL API at `classic-scangame-core/src/wrye.rs`:
```rust
pub enum WryeSeverity { Error, Warning, Info, Note }

pub struct WryeIssue {
    pub section_title: String,
    pub plugins: Vec<String>,         // <<< Pitfall 6 hazard if returned in a Vec<WryeIssueDto>
    pub warning_message: Option<String>,
    pub severity: WryeSeverity,
}

pub struct WryeBashParser { /* private */ }
impl WryeBashParser {
    pub fn new(wrye_warnings: HashMap<String, String>) -> Self;
    pub fn parse(&self, html_content: &str) -> Vec<WryeIssue>;
    pub fn format_report(issues: &[WryeIssue]) -> String;
}
```

Integrity — REAL API at `classic-scangame-core/src/integrity.rs`:
```rust
pub enum CheckType {
    ExecutableVersion,        // REAL — only 2 variants
    InstallationLocation,
}

pub struct IntegrityCheckResult {
    pub is_valid: bool,       // NOT `passed`
    pub message: String,
    pub check_type: CheckType,
}

pub struct IntegrityConfig {
    pub game_exe_path: PathBuf,
    pub valid_exe_hashes: Vec<String>,
    pub steam_ini_path: Option<PathBuf>,
    pub root_name: String,
    pub root_warn: Option<String>,
}

pub struct GameIntegrityChecker { /* private */ }
impl GameIntegrityChecker {
    pub fn new(config: IntegrityConfig) -> Self;
    pub fn check_executable_version(&self) -> Result<IntegrityCheckResult, IntegrityError>;
    pub fn check_installation_location(&self) -> Result<IntegrityCheckResult, IntegrityError>;
    pub fn run_all_checks(&self) -> Result<Vec<IntegrityCheckResult>, IntegrityError>;
    pub fn run_full_check(&self) -> Result<String, IntegrityError>;
}
```

Setup — REAL API at `classic-scangame-core/src/setup.rs`:
```rust
pub struct SetupCheckConfig {
    pub integrity: IntegrityConfig,
    pub game_name: String,
    pub docs_path: Option<String>,
    pub xse_hashes: Vec<(String, String)>,
}

pub struct SetupCheckResults {
    pub integrity_results: Vec<String>,  // NOT pre-counted; lengths give counts
    pub xse_results: Vec<String>,
    pub docs_results: Vec<String>,
    pub errors: Vec<String>,
}
impl SetupCheckResults {
    pub fn combined(&self) -> String;
    pub fn has_errors(&self) -> bool;     // !self.errors.is_empty()
    pub fn total_checks(&self) -> usize;  // sum of integrity/xse/docs lengths
}

pub fn run_combined_checks(config: &SetupCheckConfig) -> SetupCheckResults;
```

CrashgenOrchestrator — REAL API at `classic-scangame-core/src/crashgen_orchestrator.rs`:
```rust
pub struct CrashgenReport {
    pub message: String,
    pub issues: Vec<TomlConfigIssue>,       // NOT config_issues
    pub crashgen_name: String,
    pub config_path: Option<PathBuf>,
    pub installed_plugins: Vec<String>,     // <<< second Vec<String> field
}

pub struct CrashgenCheckOrchestrator;
impl CrashgenCheckOrchestrator {
    pub fn check(plugins_path: &Path, crashgen_name: &str) -> Result<CrashgenReport>;
    pub fn check_with_rules(/* ... */) -> Result<CrashgenReport>;
    pub fn detect_plugins(plugins_path: &Path) -> Result<Vec<String>>;
    pub fn resolve_config_path(plugins_path: &Path) -> Option<PathBuf>;
}
```

Bridge approach:
- TOML: `crashgen_checker_check(plugins_path, crashgen_name) -> CrashgenCheckResultDto { report_text, issue_count }` + `crashgen_checker_get_issues(plugins_path, crashgen_name) -> Vec<TomlConfigIssueDto>`. The internal CrashgenChecker is constructed twice (once per fn). Acceptable cost; the alternative is opaque CXX types which add complexity.
- Wrye: ROW-ORIENTED — `wrye_parse_html_rows(html_content, warnings_keys, warnings_values) -> Vec<WryeIssueRowDto>` where `WryeIssueRowDto { issue_index: u32, section_title: String, plugin: String, warning_message_or_empty: String, has_warning_message: bool, severity: WryeSeverity }`. One row per (issue, plugin) pair. The `issue_index` lets C++ callers group rows back into issues if needed. NO nested Vec.
- Integrity: `integrity_run_all_checks(game_exe_path, valid_hashes_csv, root_name) -> Vec<IntegrityCheckResultDto>` constructs IntegrityConfig internally; passes valid_hashes as `&[String]`.
- Setup orchestrator: `scangame_run_setup_structured(game_exe_path, valid_hashes, root_name, game_name, docs_path) -> ScanGameSetupDto` constructs SetupCheckConfig internally; counts come from REAL `SetupCheckResults` vector lengths.
- Crashgen: `crashgen_orchestrator_check_summary(plugins_path, crashgen_name) -> CrashgenReportSummaryDto { message, crashgen_name, config_path_or_empty, has_config_path, issue_count, installed_plugin_count }` + two getters: `crashgen_orchestrator_get_issues(plugins_path, crashgen_name) -> Vec<TomlConfigIssueDto>` AND `crashgen_orchestrator_get_installed_plugins(plugins_path, crashgen_name) -> Vec<String>`. Both Vec<...> fields are accessible via separate getters — no nested Vec inside the summary DTO.

ALL DTOs in this plan are Pitfall 6 CLEAR by construction:
- TomlConfigIssueDto: only String + enum fields — no Vec
- WryeIssueRowDto: only String + bool + enum fields — no Vec; the row split eliminates the embedded `plugins: Vec<String>`
- IntegrityCheckResultDto: only String + bool + enum fields — no Vec
- ScanGameSetupDto: only u32 + bool fields — no Vec
- CrashgenReportSummaryDto: only String + bool + u32 fields — no Vec; the two Vec fields (issues, installed_plugins) are exposed via separate getters
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scangame.rs with REAL TOML + Wrye (row-oriented) + Integrity + Setup structured + Crashgen APIs (Codex HIGH corrections) + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs (confirm pub re-exports for toml/wrye/integrity/setup/crashgen_orchestrator)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs (READ ENTIRELY — confirm CrashgenChecker::new(plugins_path, crashgen_name) / check() -> Result<(String, Vec<TomlConfigIssue>)>; confirm REAL TomlConfigIssue field set: file_path, section, setting, current_value, recommended_value, description, severity)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/wrye.rs (READ ENTIRELY — confirm WryeBashParser::new(HashMap) / parse(&str) -> Vec<WryeIssue>; confirm REAL WryeIssue field set: section_title, plugins: Vec<String>, warning_message: Option<String>, severity)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/integrity.rs (READ ENTIRELY — confirm REAL IntegrityCheckResult { is_valid: bool, message: String, check_type: CheckType }; confirm REAL CheckType variants ExecutableVersion + InstallationLocation only; confirm GameIntegrityChecker::run_all_checks() signature)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/setup.rs (READ ENTIRELY — confirm REAL SetupCheckResults vec-based fields; confirm run_combined_checks(&SetupCheckConfig) signature)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs (READ ENTIRELY — confirm REAL CrashgenReport fields: message, issues, crashgen_name, config_path: Option<PathBuf>, installed_plugins: Vec<String>; confirm CrashgenCheckOrchestrator::check signature)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs (current state AFTER plan 02-05 — has BA2/INI/ENB fns; this plan ADDS more)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 06" (Codex HIGH corrections + Pitfall 6 Wrye flatten)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-05, D-06, D-07, D-08, D-12
  </read_first>

  <behavior>
    - Test: `crashgen_checker_check("nonexistent\\plugins", "Buffout4")` returns CrashgenCheckResultDto with `issue_count: 0` and a non-empty `report_text` containing an error or "not installed" message (whatever the real CrashgenChecker::check returns for missing path).
    - Test: `crashgen_checker_get_issues("nonexistent\\plugins", "Buffout4")` returns empty Vec<TomlConfigIssueDto>.
    - Test: `wrye_parse_html_rows("", &[], &[])` returns empty Vec<WryeIssueRowDto>.
    - Test: `wrye_parse_html_rows("<html></html>", &[], &[])` returns empty Vec or only top-level rows (parser-dependent).
    - Test: When given a synthetic HTML containing one issue with two plugins, `wrye_parse_html_rows` returns 2 row entries with the same `issue_index` and the same `section_title`/`severity` but DIFFERENT `plugin` values (validates the row split works).
    - Test: `integrity_run_all_checks("nonexistent.exe", &[], "Fallout4")` returns Vec<IntegrityCheckResultDto> with at least one entry whose `is_valid: false` and whose `check_type` is `CheckType::ExecutableVersion` (REAL variant — confirmed by reading core fn behavior at integrity.rs:158-205 which returns this exact case for missing executable).
    - Test: every IntegrityCheckResultDto field uses `is_valid` (REAL field name), NOT `passed`.
    - Test: `scangame_run_setup_structured("", &[], "", "", "")` returns ScanGameSetupDto with `error_count > 0` (the underlying SetupCheckResults captures errors for missing paths). The exact behavior depends on `run_combined_checks`'s tolerance — confirm by reading setup.rs:165 onwards and assert what it actually does.
    - Test: `crashgen_orchestrator_check_summary("nonexistent\\plugins", "Buffout4")` returns CrashgenReportSummaryDto with `issue_count: 0` and `installed_plugin_count: 0`.
    - Test: `crashgen_orchestrator_get_issues("nonexistent\\plugins", "Buffout4")` returns empty Vec<TomlConfigIssueDto>.
    - Test: `crashgen_orchestrator_get_installed_plugins("nonexistent\\plugins", "Buffout4")` returns empty Vec<String>.
    - Test (regression — DO NOT BREAK): all plan 02-05 BA2/INI/ENB fns plus run_setup_checks/needs_path_detection still work.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`. KEEP everything from plan 02-05 unchanged. ADD:

  Step 1 — Extend the imports block:
  ```rust
  use std::collections::HashMap;
  use std::path::{Path, PathBuf};
  use classic_scangame_core::{
      // existing from plan 02-05: ba2, ini, enb …
      toml::{CrashgenChecker, TomlConfigIssue as CoreTomlConfigIssue,
             TomlIssueSeverity as CoreTomlIssueSeverity},
      wrye::{WryeBashParser, WryeIssue as CoreWryeIssue, WryeSeverity as CoreWryeSeverity},
      integrity::{
          GameIntegrityChecker, IntegrityCheckResult as CoreIntegrityCheckResult,
          IntegrityConfig, CheckType as CoreCheckType,
      },
      setup::{SetupCheckConfig, SetupCheckResults, run_combined_checks},
      crashgen_orchestrator::{CrashgenCheckOrchestrator, CrashgenReport as CoreCrashgenReport},
  };
  ```

  Step 2 — Add wrapper fns + enum mappers ABOVE the bridge block (after the ENB section from plan 02-05):

  ```rust
  // ─────────────────────────────────────────────────────────────────────
  // TOML sub-domain — REAL CrashgenChecker API (Codex HIGH correction)
  // ─────────────────────────────────────────────────────────────────────

  fn map_toml_severity(s: CoreTomlIssueSeverity) -> ffi::TomlIssueSeverity {
      match s {
          CoreTomlIssueSeverity::Info => ffi::TomlIssueSeverity::Info,
          CoreTomlIssueSeverity::Warning => ffi::TomlIssueSeverity::Warning,
          CoreTomlIssueSeverity::Error => ffi::TomlIssueSeverity::Error,
      }
  }

  fn convert_toml_issue(i: CoreTomlConfigIssue) -> ffi::TomlConfigIssueDto {
      // REAL field set per classic-scangame-core/src/toml.rs:61-82
      ffi::TomlConfigIssueDto {
          file_path: i.file_path.to_string_lossy().to_string(),
          section: i.section,
          setting: i.setting,
          current_value: i.current_value,
          recommended_value: i.recommended_value,
          description: i.description,
          severity: map_toml_severity(i.severity),
      }
  }

  fn run_crashgen_checker(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> Option<(String, Vec<CoreTomlConfigIssue>)> {
      if plugins_path.is_empty() {
          return None;
      }
      let mut checker = CrashgenChecker::new(Path::new(plugins_path), crashgen_name);
      checker.check().ok()
  }

  fn crashgen_checker_check(plugins_path: &str, crashgen_name: &str) -> ffi::CrashgenCheckResultDto {
      match run_crashgen_checker(plugins_path, crashgen_name) {
          Some((text, issues)) => ffi::CrashgenCheckResultDto {
              report_text: text,
              issue_count: issues.len() as u32,
          },
          None => ffi::CrashgenCheckResultDto {
              report_text: String::new(),
              issue_count: 0,
          },
      }
  }

  fn crashgen_checker_get_issues(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> Vec<ffi::TomlConfigIssueDto> {
      run_crashgen_checker(plugins_path, crashgen_name)
          .map(|(_, issues)| issues.into_iter().map(convert_toml_issue).collect())
          .unwrap_or_default()
  }

  // ─────────────────────────────────────────────────────────────────────
  // Wrye sub-domain — REAL WryeBashParser API + ROW-oriented flattening
  // (Codex HIGH correction + Pitfall 6 Vec<StructWithVec> elimination)
  // ─────────────────────────────────────────────────────────────────────

  fn map_wrye_severity(s: CoreWryeSeverity) -> ffi::WryeSeverity {
      match s {
          CoreWryeSeverity::Error => ffi::WryeSeverity::Error,
          CoreWryeSeverity::Warning => ffi::WryeSeverity::Warning,
          CoreWryeSeverity::Info => ffi::WryeSeverity::Info,
          CoreWryeSeverity::Note => ffi::WryeSeverity::Note,
      }
  }

  fn wrye_parse_html_rows(
      html_content: &str,
      warnings_keys: &[String],
      warnings_values: &[String],
  ) -> Vec<ffi::WryeIssueRowDto> {
      // Build the HashMap input from parallel string slices (parallel-vec
      // pattern — same as web.rs build_url_with_query and config db helpers).
      if warnings_keys.len() != warnings_values.len() {
          return Vec::new();
      }
      let warnings: HashMap<String, String> = warnings_keys
          .iter()
          .cloned()
          .zip(warnings_values.iter().cloned())
          .collect();

      let parser = WryeBashParser::new(warnings);
      let issues: Vec<CoreWryeIssue> = parser.parse(html_content);

      // Pitfall 6 elimination: flatten each (issue, plugin) into a row.
      // The row contains a stable issue_index so C++ callers can group rows
      // back into issues if they need to.
      let mut rows = Vec::new();
      for (issue_index, issue) in issues.into_iter().enumerate() {
          let row_index_u32 = issue_index as u32;
          let warning_text = issue.warning_message.clone().unwrap_or_default();
          let has_warning = issue.warning_message.is_some();
          let severity = map_wrye_severity(issue.severity);
          if issue.plugins.is_empty() {
              // Issue with no plugins — emit a single row with empty plugin
              rows.push(ffi::WryeIssueRowDto {
                  issue_index: row_index_u32,
                  section_title: issue.section_title.clone(),
                  plugin: String::new(),
                  warning_message_or_empty: warning_text.clone(),
                  has_warning_message: has_warning,
                  severity: severity.clone(),
              });
          } else {
              for plugin in &issue.plugins {
                  rows.push(ffi::WryeIssueRowDto {
                      issue_index: row_index_u32,
                      section_title: issue.section_title.clone(),
                      plugin: plugin.clone(),
                      warning_message_or_empty: warning_text.clone(),
                      has_warning_message: has_warning,
                      severity: severity.clone(),
                  });
              }
          }
      }
      rows
  }

  // ─────────────────────────────────────────────────────────────────────
  // Integrity sub-domain — REAL GameIntegrityChecker API + REAL CheckType
  // (Codex HIGH correction)
  // ─────────────────────────────────────────────────────────────────────

  fn map_check_type(c: CoreCheckType) -> ffi::CheckType {
      // REAL: only 2 variants
      match c {
          CoreCheckType::ExecutableVersion => ffi::CheckType::ExecutableVersion,
          CoreCheckType::InstallationLocation => ffi::CheckType::InstallationLocation,
      }
  }

  fn integrity_run_all_checks(
      game_exe_path: &str,
      valid_hashes: &[String],
      root_name: &str,
  ) -> Vec<ffi::IntegrityCheckResultDto> {
      if game_exe_path.is_empty() || root_name.is_empty() {
          return Vec::new();
      }
      let config = IntegrityConfig::new(
          PathBuf::from(game_exe_path),
          valid_hashes.to_vec(),
          root_name.to_string(),
      );
      let checker = GameIntegrityChecker::new(config);
      checker
          .run_all_checks()
          .unwrap_or_default()
          .into_iter()
          .map(|r: CoreIntegrityCheckResult| ffi::IntegrityCheckResultDto {
              is_valid: r.is_valid,        // REAL field name (NOT `passed`)
              message: r.message,
              check_type: map_check_type(r.check_type),
          })
          .collect()
  }

  // ─────────────────────────────────────────────────────────────────────
  // Setup orchestrator structured DTO — REAL run_combined_checks (Codex HIGH)
  // ─────────────────────────────────────────────────────────────────────

  fn scangame_run_setup_structured(
      game_exe_path: &str,
      valid_hashes: &[String],
      root_name: &str,
      game_name: &str,
      docs_path: &str,
  ) -> ffi::ScanGameSetupDto {
      if game_exe_path.is_empty() || game_name.is_empty() {
          return ffi::ScanGameSetupDto {
              check_count: 0,
              error_count: 1,
              has_errors: true,
          };
      }
      let integrity = IntegrityConfig::new(
          PathBuf::from(game_exe_path),
          valid_hashes.to_vec(),
          root_name.to_string(),
      );
      let docs = if docs_path.is_empty() { None } else { Some(docs_path.to_string()) };
      let config = SetupCheckConfig {
          integrity,
          game_name: game_name.to_string(),
          docs_path: docs,
          xse_hashes: Vec::new(),
      };
      let results: SetupCheckResults = run_combined_checks(&config);
      // Counts come from REAL Vec field lengths (Codex HIGH correction)
      let total_checks = results.total_checks() as u32;       // sum of integrity/xse/docs lengths
      let error_count = results.errors.len() as u32;          // direct errors vec length
      let has_errors = results.has_errors();
      ffi::ScanGameSetupDto {
          check_count: total_checks,
          error_count,
          has_errors,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // CrashgenOrchestrator — REAL CrashgenCheckOrchestrator + REAL CrashgenReport
  // Two Vec fields (issues, installed_plugins) → exposed via separate getters
  // (Pitfall 6 — no nested Vec in the summary DTO)
  // ─────────────────────────────────────────────────────────────────────

  fn run_crashgen_orchestrator(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> Option<CoreCrashgenReport> {
      if plugins_path.is_empty() {
          return None;
      }
      CrashgenCheckOrchestrator::check(Path::new(plugins_path), crashgen_name).ok()
  }

  fn crashgen_orchestrator_check_summary(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> ffi::CrashgenReportSummaryDto {
      match run_crashgen_orchestrator(plugins_path, crashgen_name) {
          Some(report) => {
              let config_path_str = report
                  .config_path
                  .as_ref()
                  .map(|p| p.to_string_lossy().to_string())
                  .unwrap_or_default();
              let has_config_path = report.config_path.is_some();
              ffi::CrashgenReportSummaryDto {
                  message: report.message,
                  crashgen_name: report.crashgen_name,
                  config_path_or_empty: config_path_str,
                  has_config_path,
                  issue_count: report.issues.len() as u32,
                  installed_plugin_count: report.installed_plugins.len() as u32,
              }
          }
          None => ffi::CrashgenReportSummaryDto {
              message: String::new(),
              crashgen_name: crashgen_name.to_string(),
              config_path_or_empty: String::new(),
              has_config_path: false,
              issue_count: 0,
              installed_plugin_count: 0,
          },
      }
  }

  fn crashgen_orchestrator_get_issues(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> Vec<ffi::TomlConfigIssueDto> {
      run_crashgen_orchestrator(plugins_path, crashgen_name)
          .map(|r| r.issues.into_iter().map(convert_toml_issue).collect())
          .unwrap_or_default()
  }

  fn crashgen_orchestrator_get_installed_plugins(
      plugins_path: &str,
      crashgen_name: &str,
  ) -> Vec<String> {
      run_crashgen_orchestrator(plugins_path, crashgen_name)
          .map(|r| r.installed_plugins)
          .unwrap_or_default()
  }
  ```

  Step 3 — EXTEND the existing bridge block (which already has BA2/INI/ENB from plan 02-05). Add the new shared enums + new shared structs + new extern declarations:

  ```rust
  #[cxx::bridge(namespace = "classic::scangame")]
  mod ffi {
      // ─── EXISTING from base + plan 02-05 (UNCHANGED) ───
      // SetupCheckResult, PathDetectionNeeds
      // IssueSeverity, EnbResult (Present/Partial/NotInstalled), EnbConfigResult (Valid/NotFound/Unreadable)
      // Ba2IssuesSummaryDto, IniConfigIssueDto, EnbValidationResultDto
      // run_setup_checks, needs_path_detection, ba2_*, ini_*, enb_checker_validate

      // ─── NEW for plan 02-06 ───
      #[repr(u8)]
      enum TomlIssueSeverity {
          Info = 0,
          Warning = 1,
          Error = 2,
      }

      #[repr(u8)]
      enum WryeSeverity {
          Error = 0,
          Warning = 1,
          Info = 2,
          Note = 3,
      }

      // REAL CheckType — only 2 variants (Codex HIGH correction)
      #[repr(u8)]
      enum CheckType {
          ExecutableVersion = 0,
          InstallationLocation = 1,
      }

      // TomlConfigIssueDto mirrors REAL TomlConfigIssue field-for-field
      // (Codex HIGH correction — NOT key/found_value/expected_value)
      struct TomlConfigIssueDto {
          file_path: String,
          section: String,
          setting: String,
          current_value: String,
          recommended_value: String,
          description: String,
          severity: TomlIssueSeverity,
      }

      // Wrye row-oriented DTO (Pitfall 6 fix — flattens plugins: Vec<String>)
      // Each (issue, plugin) pair becomes one row.
      struct WryeIssueRowDto {
          issue_index: u32,
          section_title: String,
          plugin: String,
          warning_message_or_empty: String,
          has_warning_message: bool,
          severity: WryeSeverity,
      }

      // REAL IntegrityCheckResult fields (Codex HIGH correction)
      // NOTE: `is_valid: bool` (NOT `passed: bool`)
      struct IntegrityCheckResultDto {
          is_valid: bool,
          message: String,
          check_type: CheckType,
      }

      // ScanGameSetupDto computed from REAL SetupCheckResults vec lengths
      struct ScanGameSetupDto {
          check_count: u32,
          error_count: u32,
          has_errors: bool,
      }

      // CrashgenChecker.check() returns (String, Vec<TomlConfigIssue>)
      // Bridge: a single summary DTO + a separate getter for the issues
      struct CrashgenCheckResultDto {
          report_text: String,
          issue_count: u32,
      }

      // CrashgenReport summary — REAL field set with two Vec fields exposed
      // via separate getters (no nested Vec in this struct).
      struct CrashgenReportSummaryDto {
          message: String,
          crashgen_name: String,
          config_path_or_empty: String,
          has_config_path: bool,
          issue_count: u32,
          installed_plugin_count: u32,
      }

      extern "Rust" {
          // (existing extern declarations preserved here unchanged)

          // NEW — TOML
          fn crashgen_checker_check(plugins_path: &str, crashgen_name: &str) -> CrashgenCheckResultDto;
          fn crashgen_checker_get_issues(plugins_path: &str, crashgen_name: &str) -> Vec<TomlConfigIssueDto>;

          // NEW — Wrye (row-oriented)
          fn wrye_parse_html_rows(
              html_content: &str,
              warnings_keys: &[String],
              warnings_values: &[String],
          ) -> Vec<WryeIssueRowDto>;

          // NEW — Integrity
          fn integrity_run_all_checks(
              game_exe_path: &str,
              valid_hashes: &[String],
              root_name: &str,
          ) -> Vec<IntegrityCheckResultDto>;

          // NEW — Setup orchestrator structured
          fn scangame_run_setup_structured(
              game_exe_path: &str,
              valid_hashes: &[String],
              root_name: &str,
              game_name: &str,
              docs_path: &str,
          ) -> ScanGameSetupDto;

          // NEW — CrashgenOrchestrator
          fn crashgen_orchestrator_check_summary(
              plugins_path: &str,
              crashgen_name: &str,
          ) -> CrashgenReportSummaryDto;
          fn crashgen_orchestrator_get_issues(
              plugins_path: &str,
              crashgen_name: &str,
          ) -> Vec<TomlConfigIssueDto>;
          fn crashgen_orchestrator_get_installed_plugins(
              plugins_path: &str,
              crashgen_name: &str,
          ) -> Vec<String>;
      }
  }
  ```

  Step 4 — Extend the `#[cfg(test)]` block with new tests:

  ```rust
  #[test]
  fn test_crashgen_checker_check_nonexistent_returns_zero_issues() {
      let r = crashgen_checker_check("nonexistent\\plugins", "Buffout4");
      assert_eq!(r.issue_count, 0);
  }

  #[test]
  fn test_crashgen_checker_get_issues_nonexistent_returns_empty() {
      assert!(crashgen_checker_get_issues("nonexistent\\plugins", "Buffout4").is_empty());
  }

  #[test]
  fn test_wrye_parse_html_rows_empty_returns_empty() {
      assert!(wrye_parse_html_rows("", &[], &[]).is_empty());
  }

  #[test]
  fn test_wrye_parse_html_rows_warnings_length_mismatch_returns_empty() {
      assert!(wrye_parse_html_rows("<html/>", &["a".to_string()], &[]).is_empty());
  }

  #[test]
  fn test_integrity_run_all_checks_real_field_names() {
      let r = integrity_run_all_checks("nonexistent.exe", &[], "Fallout4");
      // REAL field is `is_valid`, not `passed` — Codex HIGH correction
      // For nonexistent exe, run_all_checks returns at least one entry with is_valid=false
      assert!(r.iter().any(|e| !e.is_valid));
      // REAL CheckType variants — Codex HIGH correction
      assert!(r.iter().any(|e| matches!(e.check_type, ffi::CheckType::ExecutableVersion)));
  }

  #[test]
  fn test_scangame_run_setup_structured_empty_inputs_returns_errors() {
      let r = scangame_run_setup_structured("", &[], "", "", "");
      assert!(r.has_errors);
      assert!(r.error_count > 0);
  }

  #[test]
  fn test_crashgen_orchestrator_check_summary_nonexistent_real_fields() {
      let r = crashgen_orchestrator_check_summary("nonexistent\\plugins", "Buffout4");
      // REAL field set: message + crashgen_name + config_path_or_empty + has_config_path + issue_count + installed_plugin_count
      assert_eq!(r.issue_count, 0);
      assert_eq!(r.installed_plugin_count, 0);
      assert!(!r.has_config_path);
  }

  #[test]
  fn test_crashgen_orchestrator_get_issues_nonexistent_returns_empty() {
      assert!(crashgen_orchestrator_get_issues("nonexistent\\plugins", "Buffout4").is_empty());
  }

  #[test]
  fn test_crashgen_orchestrator_get_installed_plugins_nonexistent_returns_empty() {
      assert!(crashgen_orchestrator_get_installed_plugins("nonexistent\\plugins", "Buffout4").is_empty());
  }
  ```

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` and confirm ALL pass (existing 9+ from plan 02-05 + 9+ new). Run clippy.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'fn (crashgen_checker_check|crashgen_checker_get_issues|wrye_parse_html_rows|integrity_run_all_checks|scangame_run_setup_structured|crashgen_orchestrator_(check_summary|get_issues|get_installed_plugins))' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 8+ wrapper definitions
    - `git grep -nE 'CrashgenChecker::new|WryeBashParser::new|GameIntegrityChecker::new|run_combined_checks|CrashgenCheckOrchestrator::check' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least 5 lines (proves REAL APIs are used)
    - `git grep -n 'is_valid: bool' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least one line in IntegrityCheckResultDto (Codex HIGH correction proof)
    - `git grep -n 'passed: bool' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (the fictional field name is gone)
    - `git grep -nE 'ExecutableVersion|InstallationLocation' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns at least 2 enum-variant lines
    - `git grep -nE 'Existence|Format|Content|Structure|Custom' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (fictional 5-variant CheckType is gone)
    - `git grep -nE 'struct WryeIssueRowDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns the row-oriented DTO
    - `git grep -n 'plugins: Vec<String>' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (Pitfall 6 — the embedded plugins Vec is flattened)
    - `git grep -nE 'struct (TomlConfigIssueDto|IntegrityCheckResultDto|ScanGameSetupDto|CrashgenCheckResultDto|CrashgenReportSummaryDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 5+ struct declarations
    - `git grep -n 'issues: Vec<' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING in any DTO (the issues Vec is exposed via separate getter)
    - `git grep -n 'fn run_setup_checks' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'fn ba2_scan_archive_summary' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the fn from plan 02-05 (no regression)
    - `git grep -nE 'compute|todo!|EXECUTOR:' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (no leftover placeholders)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` exits 0 with at least 18 passing tests (9 from 02-05 + 9 new)
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 errors)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scangame.rs` exposes the full CXXS-04 surface using REAL classic-scangame-core APIs (Codex HIGH corrections); Wrye is row-oriented (Pitfall 6 cleared); IntegrityCheckResultDto uses `is_valid` (REAL field name); CheckType has only 2 variants (REAL set); all tests pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: D-11 in-flow consumer migration in GameFilesWorker::doScan body (second sub-domain) + incremental builds + D-09 baseline refresh + commit</name>

  <files>
    - classic-gui/src/workers/gamefilesworker.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/workers/gamefilesworker.cpp (current state — has the doScan method extended by plan 02-05 to call enb_checker_validate; this plan extends doScan FURTHER to also call one of THIS plan's new bridge fns)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 06" Codex MEDIUM concern about helper-method dormancy
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08, D-09, D-11
  </read_first>

  <action>
  ## Part A — Extend doScan body to also call one of THIS plan's new bridge fns

  Edit `classic-gui/src/workers/gamefilesworker.cpp`. The doScan body already calls `enb_checker_validate` (added by plan 02-05). Now ALSO add a call to one of this plan's new fns. The simplest, most user-visible target: `crashgen_orchestrator_check_summary` — appending the crashgen plugin count to the same combined output text.

  Modify the existing doScan body:

  ```cpp
  void GameFilesWorker::doScan(const QString& gameExePath,
                               const QString& gameRoot,
                               const QString& docsPath,
                               const QString& gameName) {
      emit progress(-1.0f, QStringLiteral("Running game file setup checks..."));

      try {
          // EXISTING (D-08 preserved)
          auto result = classic::scangame::run_setup_checks(
              classic::toRustString(gameExePath),
              classic::toRustString(gameRoot),
              classic::toRustString(docsPath),
              classic::toRustString(gameName)
          );

          // From plan 02-05 — ENB summary
          auto enb_result = classic::scangame::enb_checker_validate(
              classic::toRustString(gameRoot)
          );
          // (existing enbSummary construction from plan 02-05) ...

          // D-11 / CXXS-04 (plan 02-06) consumer migration:
          // Append crashgen plugin count to the same combined output via the
          // new typed orchestrator API. The plugins path is conventionally
          // {gameRoot}/Data/F4SE/Plugins for Fallout 4 (Buffout 4 install dir).
          QString pluginsPath = QDir(gameRoot).filePath(QStringLiteral("Data/F4SE/Plugins"));
          auto crashgenSummary = classic::scangame::crashgen_orchestrator_check_summary(
              classic::toRustString(pluginsPath),
              ::rust::Str("Buffout4", 8)
          );
          QString crashgenLine = QStringLiteral("\n[Crashgen] Buffout4 plugins detected: %1, config issues: %2")
              .arg(crashgenSummary.installed_plugin_count)
              .arg(crashgenSummary.issue_count);

          QString combinedText = classic::toQString(result.combined_output)
              + enbSummary
              + crashgenLine;

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

  Add `#include <QDir>` if not already present.

  This change EXTENDS the existing doScan flow to also exercise `crashgen_orchestrator_check_summary` — every actual scan now reads and displays the Buffout4 crashgen state.

  ## Part B — Incremental builds (NO -Clean — no new build.rs entries)

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
  ```

  Both must exit 0.

  ## Part C — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part D — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`
  - `classic-gui/src/workers/gamefilesworker.cpp`
  - All 4 baseline artifacts

  Commit message: `Feat(02-06): widen scangame bridge with REAL TOML/Wrye/Integrity/Setup/Crashgen sub-domains` — body mentions CXXS-04 (complete), D-04, D-06, D-07, D-08, D-09, D-11 and explicitly notes the Codex HIGH corrections (real APIs, real field sets, real CheckType variants, Wrye row-oriented flattening) plus the D-11 in-flow consumer extension.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'classic::scangame::crashgen_orchestrator_check_summary' classic-gui/src/workers/gamefilesworker.cpp` returns at least one match
    - `git grep -nE 'doStructuredSetupCheck|doIntegrityCheck|doCrashgenCheck' classic-gui/src/workers/gamefilesworker.h` returns NOTHING (the dormant-helper-method approach is replaced)
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "scangame"` for the 8 new fns + 3 new enums + 5 new structs (this plan only — plan 02-05's additions should already be in the baseline)
    - `git log -1 --stat` shows the commit touches scangame.rs, gamefilesworker.cpp, and the baseline artifacts atomically
  </acceptance_criteria>

  <done>
    Plan 02-06 complete — CXXS-04 fully satisfied with REAL classic-scangame-core APIs (Codex HIGH corrections); scangame bridge exposes all sub-domain entry points; Wrye is row-oriented (Pitfall 6 cleared); GameFilesWorker::doScan body itself has consumers for both halves of the widening (Codex MEDIUM correction).
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` — exits 0
2. Both incremental builds exit 0
3. Parity gate at 0 drift
4. CXXS-04 fully satisfied (full sub-domain coverage with REAL APIs)
5. Wrye is row-oriented (no `Vec<StructWithVec>`)
6. IntegrityCheckResult uses `is_valid` (REAL field name) and only ExecutableVersion + InstallationLocation CheckType variants
7. CrashgenReport's two Vec fields are exposed via separate getters

Validation Architecture (per 02-VALIDATION.md row 2-06-01): `cargo test -p classic-cpp-bridge scangame::tests` + `build_cli.ps1 -Test` + `build_gui.ps1 -Test` + parity gate.
</verification>

<success_criteria>
- src/scangame.rs widened with REAL TOML/Wrye/integrity/setup_structured/crashgen sub-domain APIs (Codex HIGH corrections)
- 3 new CXX shared enums (TomlIssueSeverity, WryeSeverity, CheckType — REAL 2 variants)
- 5 new flat shared struct DTOs (TomlConfigIssueDto with REAL field set, WryeIssueRowDto row-oriented to clear Pitfall 6, IntegrityCheckResultDto with `is_valid`, ScanGameSetupDto, CrashgenReportSummaryDto with REAL CrashgenReport fields)
- All Pitfall 6 CLEAR (Wrye flattened, CrashgenReport's two Vec fields exposed via separate getters)
- Existing scangame fns (run_setup_checks, needs_path_detection, BA2/INI/ENB from plan 02-05) UNCHANGED (D-08)
- GameFilesWorker::doScan body itself extends to call crashgen_orchestrator_check_summary (D-11 in-flow consumer #2 — Codex MEDIUM correction)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- depends_on uses canonical `02-cxx-bridge-surface-expansion/05` reference (Codex LOW correction)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-06-SUMMARY.md` documenting:
- Confirmation that the bridged surface uses REAL classic-scangame-core APIs (Codex HIGH corrections — TOML/Wrye/Integrity/Setup/Crashgen)
- Confirmation that TomlConfigIssueDto matches REAL TomlConfigIssue field-for-field (file_path, section, setting, current_value, recommended_value, description, severity)
- Confirmation that WryeIssueRowDto is row-oriented and the embedded `plugins: Vec<String>` is gone (Pitfall 6 cleared)
- Confirmation that IntegrityCheckResultDto uses `is_valid` (NOT `passed`) and CheckType has only ExecutableVersion + InstallationLocation
- Confirmation that GameFilesWorker::doScan body itself exercises crashgen_orchestrator_check_summary (D-11 in-flow consumer #2)
- Exact entries added (count by sub-domain — TOML, Wrye, integrity, setup_structured, crashgen)
- Pitfall 6 verification (no Vec<StructWithVec> patterns; Wrye is row-oriented; CrashgenReport Vec fields exposed via separate getters)
- Note: CXXS-04 is now complete after this plan
</output>
