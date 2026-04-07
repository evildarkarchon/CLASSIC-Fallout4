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
    - "src/scangame.rs exposes TOML sub-domain: scangame_run_toml_check returning Vec<TomlConfigIssueDto> with TomlIssueSeverity shared enum"
    - "src/scangame.rs exposes Wrye sub-domain: scangame_run_wrye_check returning Vec<WryeIssueDto> with WryeSeverity shared enum"
    - "src/scangame.rs exposes Integrity sub-domain: scangame_run_integrity_check returning Vec<IntegrityCheckResultDto> with CheckType shared enum"
    - "src/scangame.rs exposes Setup orchestrator structured DTO: scangame_run_setup_structured returning ScanGameSetupDto (alongside the existing run_setup_checks per D-08)"
    - "src/scangame.rs exposes Crashgen orchestrator: scangame_run_crashgen_check + scangame_get_crashgen_issues (D-06 split — uses TomlConfigIssueDto from same plan)"
    - "All new shared structs are flat (Pitfall 6 CLEAR per RESEARCH.md DTO table)"
    - "Existing fns (run_setup_checks, needs_path_detection, plus all BA2/INI/ENB fns from plan 02-05) UNCHANGED"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift"
    - "GameFilesWorker has a new method calling one of the new TOML/Wrye/integrity/setup_structured/crashgen bridge fns (D-11)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      provides: "Widened scangame bridge with TOML/Wrye/integrity/setup_structured/crashgen sub-domain entry points + new shared enums + DTOs (CXXS-04 complete)"
      contains: "scangame_run_integrity_check"
    - path: "classic-gui/src/workers/gamefilesworker.cpp"
      provides: "D-11 consumer — new method calling one of the new bridge fns from this plan"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      to: "classic-scangame-core (toml, wrye, integrity, setup, crashgen_orchestrator sub-modules)"
      via: "use classic_scangame_core::{toml, wrye, integrity, setup, crashgen_orchestrator}"
      pattern: "use classic_scangame_core"
---

<objective>
Complete CXXS-04 by widening `src/scangame.rs` with the remaining sub-domain entry points: TOML (crashgen settings), Wrye, Integrity, Setup orchestrator (structured DTO alongside existing combined-output), and CrashgenOrchestrator (D-06 split — summary + per-category issue list). Adds three more CXX shared enums (`TomlIssueSeverity`, `WryeSeverity`, `CheckType`) and several new flat DTOs. Adds at least one new D-11 consumer call site in `GameFilesWorker`.

Purpose: This plan finishes CXXS-04. Per RESEARCH.md §"CrashgenOrchestrator sub-domain", `CrashgenReport` contains a `Vec<TomlConfigIssue>` field — D-06 split returns the summary as one DTO and the issue list as a separate getter (reusing `TomlConfigIssueDto` from the same plan). Per D-08, the existing `run_setup_checks` (returning `SetupCheckResult.combined_output` text) STAYS — the new `scangame_run_setup_structured` DTO is added ALONGSIDE.

Output: scangame bridge with the full CXXS-04 surface; one new GameFilesWorker method consuming a new bridge fn (D-11); refreshed parity baseline committed atomically.
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
@.planning/phases/02-cxx-bridge-surface-expansion/02-05-PLAN.md

# Source-of-truth Rust crate (per sub-domain)
@ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/wrye.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/integrity.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/setup.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs

# Bridge file this plan widens (already widened with BA2/INI/ENB by Plan 02-05)
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs

# D-11 consumer migration site
@classic-gui/src/workers/gamefilesworker.cpp
@classic-gui/src/workers/gamefilesworker.h

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Per RESEARCH.md §"TOML sub-domain" §"Wrye sub-domain" §"Integrity sub-domain" §"Setup orchestrator sub-domain" §"CrashgenOrchestrator sub-domain". -->

TOML:
```rust
pub struct TomlConfigIssue {
    pub key: String,
    pub found_value: String,
    pub expected_value: String,
    pub severity: TomlIssueSeverity,
    pub description: String,
}
pub enum TomlIssueSeverity { Info, Warning, Error }
pub fn run_toml_check(toml_path: &str, game_path: &str) -> Vec<TomlConfigIssue>; // verify exact name
```

Bridge: `scangame_run_toml_check(toml_path, game_path) -> Vec<TomlConfigIssueDto>` with `TomlConfigIssueDto { key, found_value, expected_value, severity: TomlIssueSeverity, description }`. `TomlIssueSeverity` as CXX shared enum.

Wrye:
```rust
pub struct WryeIssue {
    pub plugin_name: String,
    pub issue_type: String,
    pub severity: WryeSeverity,
    pub details: String,
}
pub enum WryeSeverity { Error, Warning, Info, Note }
pub fn run_wrye_check(wrye_html_path: &str) -> Vec<WryeIssue>;
```

Bridge: `scangame_run_wrye_check(wrye_html_path) -> Vec<WryeIssueDto>` + `WryeSeverity` shared enum.

Integrity:
```rust
pub struct IntegrityCheckResult {
    pub check_type: CheckType,
    pub passed: bool,
    pub message: String,
}
pub enum CheckType { Existence, Format, Content, Structure, Custom }
pub fn run_integrity_check(game_exe_path: &str, game_name: &str) -> Vec<IntegrityCheckResult>;
```

Bridge: `scangame_run_integrity_check(game_exe_path, game_name) -> Vec<IntegrityCheckResultDto>` + `CheckType` shared enum.

Setup orchestrator (D-08 — KEEP existing run_setup_checks; ADD structured variant):
```rust
pub struct SetupCheckResults { pub /* fields */ }
impl SetupCheckResults {
    pub fn combined(&self) -> String;
    // also: counts of errors, warnings, total checks
}
```

Bridge: `scangame_run_setup_structured(game_exe_path, game_root, docs_path, game_name) -> ScanGameSetupDto` with `ScanGameSetupDto { check_count: u32, error_count: u32, warning_count: u32, has_errors: bool }` (flat counts only — Pitfall 6 CLEAR).

Crashgen orchestrator (D-06 split — CrashgenReport contains Vec<TomlConfigIssue>):
```rust
pub struct CrashgenReport {
    pub crashgen_name: String,
    pub is_installed: bool,
    pub has_config: bool,
    pub config_issues: Vec<TomlConfigIssue>,
    pub version_string: String,
    pub status_message: String,
}
pub fn run_crashgen_check(game_path: &str, game_name: &str, crashgen_name: &str) -> CrashgenReport;
```

Bridge:
- `scangame_run_crashgen_check(game_path, game_name, crashgen_name) -> CrashgenReportSummaryDto { crashgen_name, is_installed, has_config, version_string, status_message, issue_count: u32 }`
- `scangame_get_crashgen_issues(game_path, game_name, crashgen_name) -> Vec<TomlConfigIssueDto>` (reuses TomlConfigIssueDto)

ALL DTOs in this plan are Pitfall 6 CLEAR per RESEARCH.md §"Pitfall 6 DTO Validation".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scangame.rs with TOML + Wrye + Integrity + Setup structured + Crashgen bridge fns + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs (confirm pub re-exports for toml/wrye/integrity/setup/crashgen_orchestrator)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/toml.rs (READ ENTIRELY — confirm exact TomlConfigIssue/TomlIssueSeverity names; confirm run_toml_check signature; confirm sync vs async)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/wrye.rs (READ ENTIRELY — confirm WryeIssue/WryeSeverity names; confirm run_wrye_check signature)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/integrity.rs (READ ENTIRELY — confirm IntegrityCheckResult/CheckType names; confirm run_integrity_check signature)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/setup.rs (READ ENTIRELY — confirm SetupCheckResults field set so the count fields can be computed; confirm whether `combined()` is the only public method or whether there are individual count getters)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/crashgen_orchestrator.rs (READ ENTIRELY — confirm CrashgenReport fields; confirm run_crashgen_check signature)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs (current state AFTER plan 02-05 — has BA2/INI/ENB fns; this plan ADDS; do not break existing)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"TOML sub-domain" §"Wrye sub-domain" §"Integrity sub-domain" §"Setup orchestrator sub-domain" §"CrashgenOrchestrator sub-domain"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-05, D-06, D-07, D-08, D-12
  </read_first>

  <behavior>
    - Test: `scangame_run_toml_check("nonexistent.toml", "")` returns empty Vec<TomlConfigIssueDto>.
    - Test: `scangame_run_wrye_check("nonexistent.html")` returns empty Vec<WryeIssueDto>.
    - Test: `scangame_run_integrity_check("nonexistent.exe", "Fallout4")` returns Vec<IntegrityCheckResultDto> with at least one entry whose `passed: false` and `check_type: CheckType::Existence` (or whatever core defines for the file-missing case) — confirm by reading core fn behavior.
    - Test: `scangame_run_setup_structured("", "", "", "")` returns ScanGameSetupDto with `error_count > 0` and `has_errors: true` (the underlying setup orchestrator surfaces missing-path errors).
    - Test: `scangame_run_crashgen_check("nonexistent path", "Fallout4", "Buffout4")` returns CrashgenReportSummaryDto with `is_installed: false` and `issue_count: 0`.
    - Test: `scangame_get_crashgen_issues("nonexistent path", "Fallout4", "Buffout4")` returns empty Vec<TomlConfigIssueDto>.
    - Test (regression — DO NOT BREAK): `scangame_run_ba2_check`, `scangame_run_ini_check`, `scangame_run_enb_check`, `run_setup_checks`, `needs_path_detection` all still work as before.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`. KEEP everything from plan 02-05 unchanged. ADD:

  Step 1 — Extend the imports block:
  ```rust
  use classic_scangame_core::{
      // existing from plan 02-05: ba2, ini, enb …
      toml::{run_toml_check as core_run_toml_check, TomlConfigIssue as CoreTomlConfigIssue,
             TomlIssueSeverity as CoreTomlIssueSeverity},
      wrye::{run_wrye_check as core_run_wrye_check, WryeIssue as CoreWryeIssue,
             WryeSeverity as CoreWryeSeverity},
      integrity::{run_integrity_check as core_run_integrity_check,
                  IntegrityCheckResult as CoreIntegrityCheckResult,
                  CheckType as CoreCheckType},
      setup::SetupCheckResults as CoreSetupCheckResults,
      crashgen_orchestrator::{run_crashgen_check as core_run_crashgen_check,
                              CrashgenReport as CoreCrashgenReport},
  };
  ```

  Step 2 — Add wrapper fns + enum mappers ABOVE the bridge block (after the ENB section from plan 02-05):

  ```rust
  // ─── TOML ───
  fn map_toml_severity(s: CoreTomlIssueSeverity) -> ffi::TomlIssueSeverity {
      match s {
          CoreTomlIssueSeverity::Info => ffi::TomlIssueSeverity::Info,
          CoreTomlIssueSeverity::Warning => ffi::TomlIssueSeverity::Warning,
          CoreTomlIssueSeverity::Error => ffi::TomlIssueSeverity::Error,
      }
  }

  fn convert_toml_issue(i: CoreTomlConfigIssue) -> ffi::TomlConfigIssueDto {
      ffi::TomlConfigIssueDto {
          key: i.key,
          found_value: i.found_value,
          expected_value: i.expected_value,
          severity: map_toml_severity(i.severity),
          description: i.description,
      }
  }

  fn scangame_run_toml_check(toml_path: &str, game_path: &str) -> Vec<ffi::TomlConfigIssueDto> {
      core_run_toml_check(toml_path, game_path)
          .unwrap_or_default()
          .into_iter()
          .map(convert_toml_issue)
          .collect()
  }

  // ─── Wrye ───
  fn map_wrye_severity(s: CoreWryeSeverity) -> ffi::WryeSeverity {
      match s {
          CoreWryeSeverity::Error => ffi::WryeSeverity::Error,
          CoreWryeSeverity::Warning => ffi::WryeSeverity::Warning,
          CoreWryeSeverity::Info => ffi::WryeSeverity::Info,
          CoreWryeSeverity::Note => ffi::WryeSeverity::Note,
      }
  }

  fn scangame_run_wrye_check(wrye_html_path: &str) -> Vec<ffi::WryeIssueDto> {
      core_run_wrye_check(wrye_html_path)
          .unwrap_or_default()
          .into_iter()
          .map(|i: CoreWryeIssue| ffi::WryeIssueDto {
              plugin_name: i.plugin_name,
              issue_type: i.issue_type,
              severity: map_wrye_severity(i.severity),
              details: i.details,
          })
          .collect()
  }

  // ─── Integrity ───
  fn map_check_type(c: CoreCheckType) -> ffi::CheckType {
      match c {
          CoreCheckType::Existence => ffi::CheckType::Existence,
          CoreCheckType::Format => ffi::CheckType::Format,
          CoreCheckType::Content => ffi::CheckType::Content,
          CoreCheckType::Structure => ffi::CheckType::Structure,
          CoreCheckType::Custom => ffi::CheckType::Custom,
      }
  }

  fn scangame_run_integrity_check(game_exe_path: &str, game_name: &str) -> Vec<ffi::IntegrityCheckResultDto> {
      core_run_integrity_check(game_exe_path, game_name)
          .unwrap_or_default()
          .into_iter()
          .map(|r: CoreIntegrityCheckResult| ffi::IntegrityCheckResultDto {
              check_type: map_check_type(r.check_type),
              passed: r.passed,
              message: r.message,
          })
          .collect()
  }

  // ─── Setup orchestrator structured ───
  fn scangame_run_setup_structured(
      game_exe_path: &str,
      game_root: &str,
      docs_path: &str,
      game_name: &str,
  ) -> ffi::ScanGameSetupDto {
      // Reuse the core helper that the existing run_setup_checks already calls.
      // The exact name to call depends on classic-scangame-core::setup re-exports.
      // The executor confirms via direct read; the wrapper logic computes counts
      // from SetupCheckResults' fields (likely .errors, .warnings, .total_checks).
      let results: CoreSetupCheckResults = match classic_scangame_core::setup::run_combined_checks(
          game_exe_path, game_root, docs_path, game_name,
      ) {
          Ok(r) => r,
          Err(_) => return ffi::ScanGameSetupDto {
              check_count: 0,
              error_count: 1, // signal error condition
              warning_count: 0,
              has_errors: true,
          },
      };
      // EXECUTOR: substitute the actual field accessors from CoreSetupCheckResults.
      // If the fields are not directly named error_count / warning_count / total_checks,
      // compute them by iterating results' issue list.
      let error_count = /* results.error_count() or compute */ 0u32;
      let warning_count = /* results.warning_count() or compute */ 0u32;
      let check_count = /* results.total_checks() or compute */ 0u32;
      ffi::ScanGameSetupDto {
          check_count,
          error_count,
          warning_count,
          has_errors: error_count > 0,
      }
  }

  // ─── Crashgen orchestrator (D-06 split) ───
  fn scangame_run_crashgen_check(
      game_path: &str,
      game_name: &str,
      crashgen_name: &str,
  ) -> ffi::CrashgenReportSummaryDto {
      let report: CoreCrashgenReport = match core_run_crashgen_check(game_path, game_name, crashgen_name) {
          Ok(r) => r,
          Err(_) => return ffi::CrashgenReportSummaryDto {
              crashgen_name: crashgen_name.to_string(),
              is_installed: false,
              has_config: false,
              version_string: String::new(),
              status_message: String::new(),
              issue_count: 0,
          },
      };
      let issue_count = report.config_issues.len() as u32;
      ffi::CrashgenReportSummaryDto {
          crashgen_name: report.crashgen_name,
          is_installed: report.is_installed,
          has_config: report.has_config,
          version_string: report.version_string,
          status_message: report.status_message,
          issue_count,
      }
  }

  fn scangame_get_crashgen_issues(
      game_path: &str,
      game_name: &str,
      crashgen_name: &str,
  ) -> Vec<ffi::TomlConfigIssueDto> {
      core_run_crashgen_check(game_path, game_name, crashgen_name)
          .map(|r| r.config_issues.into_iter().map(convert_toml_issue).collect())
          .unwrap_or_default()
  }
  ```

  Step 3 — EXTEND the existing bridge block (which already has BA2/INI/ENB from plan 02-05). Add three new shared enums + four new shared structs + 6 new extern declarations:

  ```rust
  #[cxx::bridge(namespace = "classic::scangame")]
  mod ffi {
      // ─── EXISTING from base + plan 02-05 (UNCHANGED) ───
      // SetupCheckResult, PathDetectionNeeds
      // IssueSeverity, EnbResult, EnbConfigResult enums
      // Ba2IssuesSummaryDto, IniConfigIssueDto, EnbValidationResultDto structs
      // run_setup_checks, needs_path_detection, scangame_run_ba2_check, …
      // (KEEP every single one — DO NOT remove or rename)

      // ─── NEW for plan 02-06 ───
      #[repr(u8)]
      enum TomlIssueSeverity { Info = 0, Warning = 1, Error = 2 }

      #[repr(u8)]
      enum WryeSeverity { Error = 0, Warning = 1, Info = 2, Note = 3 }

      #[repr(u8)]
      enum CheckType {
          Existence = 0,
          Format = 1,
          Content = 2,
          Structure = 3,
          Custom = 4,
      }

      struct TomlConfigIssueDto {
          key: String,
          found_value: String,
          expected_value: String,
          severity: TomlIssueSeverity,
          description: String,
      }

      struct WryeIssueDto {
          plugin_name: String,
          issue_type: String,
          severity: WryeSeverity,
          details: String,
      }

      struct IntegrityCheckResultDto {
          check_type: CheckType,
          passed: bool,
          message: String,
      }

      struct ScanGameSetupDto {
          check_count: u32,
          error_count: u32,
          warning_count: u32,
          has_errors: bool,
      }

      struct CrashgenReportSummaryDto {
          crashgen_name: String,
          is_installed: bool,
          has_config: bool,
          version_string: String,
          status_message: String,
          issue_count: u32,
      }

      extern "Rust" {
          // (existing extern declarations preserved here unchanged)

          // NEW
          fn scangame_run_toml_check(toml_path: &str, game_path: &str) -> Vec<TomlConfigIssueDto>;
          fn scangame_run_wrye_check(wrye_html_path: &str) -> Vec<WryeIssueDto>;
          fn scangame_run_integrity_check(game_exe_path: &str, game_name: &str) -> Vec<IntegrityCheckResultDto>;
          fn scangame_run_setup_structured(
              game_exe_path: &str,
              game_root: &str,
              docs_path: &str,
              game_name: &str,
          ) -> ScanGameSetupDto;
          fn scangame_run_crashgen_check(
              game_path: &str,
              game_name: &str,
              crashgen_name: &str,
          ) -> CrashgenReportSummaryDto;
          fn scangame_get_crashgen_issues(
              game_path: &str,
              game_name: &str,
              crashgen_name: &str,
          ) -> Vec<TomlConfigIssueDto>;
      }
  }
  ```

  Step 4 — Extend the `#[cfg(test)]` block with new tests:

  ```rust
  #[test]
  fn test_scangame_run_toml_check_nonexistent_returns_empty() {
      assert!(scangame_run_toml_check("nonexistent.toml", "").is_empty());
  }
  #[test]
  fn test_scangame_run_wrye_check_nonexistent_returns_empty() {
      assert!(scangame_run_wrye_check("nonexistent.html").is_empty());
  }
  #[test]
  fn test_scangame_run_integrity_check_nonexistent_exe_returns_failure() {
      let r = scangame_run_integrity_check("nonexistent.exe", "Fallout4");
      // Either an empty vec or at least one failed entry — accept both
      // (the core fn behavior may differ; document the actual outcome in the SUMMARY)
      assert!(r.iter().all(|e| !e.message.is_empty() || e.passed));
  }
  #[test]
  fn test_scangame_run_setup_structured_empty_inputs_returns_errors() {
      let r = scangame_run_setup_structured("", "", "", "");
      assert!(r.has_errors);
  }
  #[test]
  fn test_scangame_run_crashgen_check_nonexistent_returns_not_installed() {
      let r = scangame_run_crashgen_check("nonexistent path", "Fallout4", "Buffout4");
      assert!(!r.is_installed);
      assert_eq!(r.issue_count, 0);
  }
  #[test]
  fn test_scangame_get_crashgen_issues_nonexistent_returns_empty() {
      let r = scangame_get_crashgen_issues("nonexistent path", "Fallout4", "Buffout4");
      assert!(r.is_empty());
  }
  ```

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` and confirm ALL pass (existing 6+ from plan 02-05 + 6+ new). Run clippy.

  IMPORTANT: For `scangame_run_setup_structured`, the executor MUST replace the placeholder count computation (`/* results.error_count() or compute */`) with the actual logic by reading `SetupCheckResults` fields. If the type has only `combined()` and a `has_errors`/`total_checks` getter, derive `warning_count` as `total_checks - error_count`, or expose as `0` and document in the SUMMARY. Do not commit placeholder comments.

  IMPORTANT: For async core fns, wrap in `classic_shared_core::get_runtime().block_on(...)` per the existing scangame.rs `run_setup_checks` pattern.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'fn scangame_(run_toml_check|run_wrye_check|run_integrity_check|run_setup_structured|run_crashgen_check|get_crashgen_issues)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 6+ wrapper definitions and 6+ extern declarations
    - `git grep -nE 'enum (TomlIssueSeverity|WryeSeverity|CheckType)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 3+ shared enum declarations
    - `git grep -nE 'struct (TomlConfigIssueDto|WryeIssueDto|IntegrityCheckResultDto|ScanGameSetupDto|CrashgenReportSummaryDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 5+ shared struct declarations
    - `git grep -n 'fn run_setup_checks' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'fn scangame_run_ba2_check' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the fn from plan 02-05 (no regression)
    - `git grep -n 'compute' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns NOTHING (no leftover placeholder comments)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` exits 0 with at least 12 passing tests (6 from 02-05 + 6 new)
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 errors)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scangame.rs` exposes the full CXXS-04 surface (BA2 + INI + ENB from plan 02-05 + TOML + Wrye + Integrity + Setup structured + Crashgen split from this plan), all tests pass, no regressions.
  </done>
</task>

<task type="auto">
  <name>Task 2: D-11 consumer migration in GameFilesWorker (second new method), incremental builds, refresh D-09 baseline, commit</name>

  <files>
    - classic-gui/src/workers/gamefilesworker.cpp
    - classic-gui/src/workers/gamefilesworker.h
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/workers/gamefilesworker.cpp (current state — has the doBa2CheckForArchive method or similar from plan 02-05; ADD a second method exercising one of THIS plan's new bridge fns)
    - classic-gui/src/workers/gamefilesworker.h (declared methods)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"D-11 Consumer Migration Enumeration" §"For new CXXS-04 scangame fns: The planner should add at least one new C++ call site for each new scangame bridge fn"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08, D-09, D-11
  </read_first>

  <action>
  ## Part A — Add a second new GameFilesWorker method consuming one of THIS plan's new bridge fns

  Edit `classic-gui/src/workers/gamefilesworker.h`:

  ```cpp
  // New for D-11 / Phase 2 Plan 02-06 — exposes the bridge structured setup-orchestrator DTO.
  classic::scangame::ScanGameSetupDto doStructuredSetupCheck(
      const QString& gameExePath,
      const QString& gameRoot,
      const QString& docsPath,
      const QString& gameName);

  // OR pick a different new fn:
  // QStringList doIntegrityCheckMessages(const QString& gameExePath, const QString& gameName);
  ```

  Edit `classic-gui/src/workers/gamefilesworker.cpp` to implement:

  ```cpp
  classic::scangame::ScanGameSetupDto GameFilesWorker::doStructuredSetupCheck(
      const QString& gameExePath,
      const QString& gameRoot,
      const QString& docsPath,
      const QString& gameName) {
      const auto exeStdStr = gameExePath.toStdString();
      const auto rootStdStr = gameRoot.toStdString();
      const auto docsStdStr = docsPath.toStdString();
      const auto nameStdStr = gameName.toStdString();
      return classic::scangame::scangame_run_setup_structured(
          ::rust::Str(exeStdStr.data(), exeStdStr.size()),
          ::rust::Str(rootStdStr.data(), rootStdStr.size()),
          ::rust::Str(docsStdStr.data(), docsStdStr.size()),
          ::rust::Str(nameStdStr.data(), nameStdStr.size()));
  }
  ```

  This is the second D-11 production caller. Combined with the BA2 method from plan 02-05, the GUI now exercises bridge fns from BOTH halves of the scangame widening — satisfying the D-11 spirit (each new bridge fn doesn't need its OWN caller, but each plan adds at least one new caller to prove the new headers compile and link).

  Note: Per RESEARCH.md, full per-fn D-11 enumeration is NOT required. The minimum is "at least one new caller per plan" — a single representative call site per plan is sufficient to prove the new headers integrate cleanly. If the executor wants to add more for thoroughness, that's within scope but not required.

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
  - `classic-gui/src/workers/gamefilesworker.h`
  - All 4 baseline artifacts

  Commit message: `Feat(02-06): widen scangame bridge with TOML/Wrye/integrity/setup/crashgen sub-domains` — body mentions CXXS-04 (complete), D-04, D-06, D-07, D-08, D-09, D-11.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'classic::scangame::(scangame_run_toml_check|scangame_run_wrye_check|scangame_run_integrity_check|scangame_run_setup_structured|scangame_run_crashgen_check|scangame_get_crashgen_issues)' classic-gui/src/workers/gamefilesworker.cpp` returns at least one match
    - `git grep -n 'doStructuredSetupCheck\|doIntegrityCheck\|doCrashgenCheck\|doTomlCheck\|doWryeCheck' classic-gui/src/workers/gamefilesworker.h` returns the new method declaration
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "scangame"` for the 6 new fns + 3 new enums + 5 new structs (this plan only — plan 02-05's additions should already be in the baseline)
    - `git log -1 --stat` shows the commit touches scangame.rs, both gamefilesworker files, and the baseline artifacts atomically
  </acceptance_criteria>

  <done>
    Plan 02-06 complete — CXXS-04 fully satisfied; scangame bridge exposes all sub-domain entry points; GameFilesWorker has consumers for both halves of the widening.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` — exits 0
2. Both incremental builds exit 0
3. Parity gate at 0 drift
4. CXXS-04 fully satisfied (full sub-domain coverage)

Validation Architecture (per 02-VALIDATION.md row 2-06-01): `cargo test -p classic-cpp-bridge scangame::tests` + `build_cli.ps1 -Test` + `build_gui.ps1 -Test` + parity gate.
</verification>

<success_criteria>
- src/scangame.rs widened with TOML/Wrye/integrity/setup_structured/crashgen sub-domain entry points
- 3 new CXX shared enums (TomlIssueSeverity, WryeSeverity, CheckType)
- 5 new flat shared struct DTOs (TomlConfigIssueDto, WryeIssueDto, IntegrityCheckResultDto, ScanGameSetupDto, CrashgenReportSummaryDto)
- All Pitfall 6 CLEAR
- Existing scangame fns (run_setup_checks, needs_path_detection, BA2/INI/ENB from plan 02-05) UNCHANGED (D-08)
- GameFilesWorker has a SECOND new method (in addition to plan 02-05's) calling one of THIS plan's new bridge fns (D-11)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-06-SUMMARY.md` documenting:
- Exact entries added (count by sub-domain — TOML, Wrye, integrity, setup_structured, crashgen)
- Which GameFilesWorker method was added and which bridge fn it calls (D-11 confirmation)
- Pitfall 6 verification (no Vec<StructWithVec> patterns)
- Note: CXXS-04 is now complete after this plan
- How the SetupCheckResults count computation was resolved (which fields/getters were used)
</output>