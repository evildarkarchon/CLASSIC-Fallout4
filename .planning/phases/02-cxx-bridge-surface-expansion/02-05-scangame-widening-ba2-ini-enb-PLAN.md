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
    - "src/scangame.rs exposes BA2 sub-domain bridge fns: scangame_run_ba2_check + scangame_get_ba2_tex_dims/tex_frmt/snd_frmt/xse_files (D-06 split per Pitfall 6)"
    - "src/scangame.rs exposes INI sub-domain: scangame_run_ini_check returning Vec<IniConfigIssueDto> (with IssueSeverity shared enum)"
    - "src/scangame.rs exposes ENB sub-domain: scangame_run_enb_check returning EnbValidationResultDto (with EnbResult, EnbConfigResult shared enums)"
    - "All new shared structs are flat (Pitfall 6 CLEAR — verified per RESEARCH.md DTO table)"
    - "Existing scangame fns (run_setup_checks, needs_path_detection) UNCHANGED (D-08)"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0 (NO -Clean required — scangame.rs is already in build.rs)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "GameFilesWorker has at least one new method calling one of the new bridge fns (D-11 consumer migration)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      provides: "Widened scangame bridge with BA2/INI/ENB sub-domain entry points + 3 new CXX shared enums + 5+ new shared struct DTOs (CXXS-04 partial)"
      contains: "scangame_run_ba2_check"
    - path: "classic-gui/src/workers/gamefilesworker.cpp"
      provides: "D-11 consumer — at least one new method calling a new scangame bridge fn (e.g., doDetailedBa2Check or doIniCheck)"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs"
      to: "classic-scangame-core (ba2, ini, enb sub-modules)"
      via: "use classic_scangame_core::{ba2, ini, enb}"
      pattern: "use classic_scangame_core"
    - from: "classic-gui/src/workers/gamefilesworker.cpp"
      to: "classic_cxx_bridge/scangame.h (one of the new fns)"
      via: "C++ method body calling classic::scangame::scangame_run_*"
      pattern: "classic::scangame::scangame_run_"
---

<objective>
Widen `src/scangame.rs` from its current 2 entry points to expose BA2, INI, and ENB sub-domain orchestration via D-06 flattened bridge fns (CXXS-04 part 1 of 2). Add three CXX shared enums (`IssueSeverity`, `EnbResult`, `EnbConfigResult`) per D-04/D-07. Add at least one new D-11 consumer call site in `GameFilesWorker` so the new bridge fns are exercised by production C++ code. Existing fns (`run_setup_checks`, `needs_path_detection`) stay UNCHANGED per D-08.

Purpose: CXXS-04 is the largest widening in Phase 2. Per RESEARCH.md, BA2 / INI / ENB form a cohesive group sharing similar DTO design patterns. Splitting into two plans (05 = BA2/INI/ENB; 06 = TOML/Wrye/integrity/setup/crashgen) keeps each plan within the ~50% context budget. Per RESEARCH.md §"BA2 sub-domain", `BA2Issues` cannot be returned directly because its `Vec<String>` fields would create `Vec<StructWithVec>` if returned in a Vec — D-06 splits it into a summary + 4 per-category getters.

Output: Widened scangame bridge with BA2/INI/ENB surface; one new GameFilesWorker method consuming a new bridge fn (D-11); refreshed parity baseline committed atomically.
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

# Source-of-truth Rust crate (per sub-domain)
@ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/ba2.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/ini.rs
@ClassicLib-rs/business-logic/classic-scangame-core/src/enb.rs

# Bridge file this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs

# Reference patterns
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# D-11 consumer migration site
@classic-gui/src/workers/gamefilesworker.cpp
@classic-gui/src/workers/gamefilesworker.h

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Per RESEARCH.md §"BA2 sub-domain", §"INI sub-domain", §"ENB sub-domain". -->

BA2 (D-06 split — BA2Issues has 4 Vec<String> fields, cannot Vec it):
```rust
pub struct BA2Issues {
    pub tex_dims: Vec<String>,
    pub tex_frmt: Vec<String>,
    pub snd_frmt: Vec<String>,
    pub xse_file: Vec<String>,
}
pub fn run_ba2_check(archive_path: &str) -> BA2Issues; // or similar — verify exact name
```

Bridge approach:
- `Ba2IssuesSummaryDto { tex_dim_count: u32, tex_fmt_count: u32, snd_fmt_count: u32, xse_file_count: u32, total: u32, has_issues: bool }`
- 4 separate getters returning `Vec<String>` per category
- Cache the result inside scangame.rs's run_ba2 helper if the underlying call is expensive (but per D-08 default — keep it simple, recompute per call, fail-soft on missing archive)

INI:
```rust
pub struct ConfigIssue { // scangame::ini::ConfigIssue
    pub key: String,
    pub section: String,
    pub found_value: String,
    pub expected_value: String,
    pub severity: IssueSeverity,
}
pub enum IssueSeverity { Error, Warning, Info }
pub fn run_ini_check(ini_path: &str, game_name: &str) -> Vec<ConfigIssue>;
```

Bridge: `scangame_run_ini_check(ini_path, game_name) -> Vec<IniConfigIssueDto>` with `IniConfigIssueDto { key: String, section: String, found_value: String, expected_value: String, severity: IssueSeverity }` and `IssueSeverity` as CXX shared enum.

NOTE: scangame::ini::ConfigIssue collides naming-wise with scanlog::fcx_handler::ConfigIssue. Use `IniConfigIssueDto` (and later `FcxIssueDto` in plan 02-08) to disambiguate.

ENB:
```rust
pub struct EnbValidationResult {
    pub enb_result: EnbResult,
    pub config_result: EnbConfigResult,
    pub errors: Vec<String>,
}
pub enum EnbResult { NotPresent, PresentNoConfig, PresentWithConfig, PresentWithIniOverride }
pub enum EnbConfigResult { Valid, HasConflicts, Missing, NotApplicable }
pub fn run_enb_check(game_path: &str) -> EnbValidationResult;
```

Bridge: `scangame_run_enb_check(game_path) -> EnbValidationResultDto { enb_result, config_result, errors_csv: String }` (errors flattened to `\n`-joined string to keep the DTO single-return safe). Both `EnbResult` and `EnbConfigResult` as CXX shared enums.

ALL DTOs in this plan are Pitfall 6 CLEAR per RESEARCH.md §"Pitfall 6 DTO Validation".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scangame.rs with BA2 + INI + ENB bridge fns + shared enums + DTOs + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs (READ to confirm which sub-modules are pub re-exported and what their public fn signatures look like)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/ba2.rs (READ ENTIRELY — confirm exact fn name for the BA2 check entry point; confirm BA2Issues field names; confirm whether the fn is sync or async)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/ini.rs (READ ENTIRELY — confirm scangame::ini::ConfigIssue field names and IssueSeverity variant set; confirm run_ini_check signature)
    - ClassicLib-rs/business-logic/classic-scangame-core/src/enb.rs (READ ENTIRELY — confirm EnbResult and EnbConfigResult variant sets; confirm EnbValidationResult fields; confirm run_enb_check signature)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs (current 2-fn surface — KEEP run_setup_checks and needs_path_detection unchanged per D-08; ADD all new fns BELOW the existing block)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs (template for nested-but-flat shared struct using YamlDataModSolutionEntry)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"BA2 sub-domain" §"INI sub-domain" §"ENB sub-domain" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-05, D-06, D-07, D-08, D-12
  </read_first>

  <behavior>
    - Test: `scangame_run_ba2_check("nonexistent.ba2")` returns Ba2IssuesSummaryDto with `has_issues: false` and all counts = 0 (fail-soft on missing archive).
    - Test: `scangame_get_ba2_tex_dims("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `scangame_get_ba2_tex_frmt("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `scangame_get_ba2_snd_frmt("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `scangame_get_ba2_xse_files("nonexistent.ba2")` returns empty Vec<String>.
    - Test: `scangame_run_ini_check("", "")` returns empty Vec<IniConfigIssueDto> (fail-soft).
    - Test: `scangame_run_ini_check("nonexistent.ini", "Fallout4")` returns empty Vec or a Vec containing only existence-check issues — confirm by reading the core fn behavior and assert what it actually does.
    - Test: `scangame_run_enb_check("nonexistent\\path")` returns EnbValidationResultDto with `enb_result: EnbResult::NotPresent` and empty errors_csv.
    - Test: severity enum round-trip — for each `IniConfigIssueDto` returned (when fed valid input), verify the severity field is one of the three known shared enum values.
    - Test (existing — DO NOT BREAK): `run_setup_checks(...)` and `needs_path_detection(...)` still work and return their original SetupCheckResult / PathDetectionNeeds shapes.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`. KEEP the existing module imports, the existing wrapper fns for `run_setup_checks` and `needs_path_detection`, and the existing `#[cxx::bridge(namespace = "classic::scangame")]` block UNCHANGED — only ADD to it.

  Step 1 — Add new core imports near the top:
  ```rust
  use classic_scangame_core::{
      ba2::{run_ba2_check as core_run_ba2_check, BA2Issues as CoreBA2Issues},
      enb::{run_enb_check as core_run_enb_check, EnbValidationResult as CoreEnbValidationResult,
            EnbResult as CoreEnbResult, EnbConfigResult as CoreEnbConfigResult},
      ini::{run_ini_check as core_run_ini_check, ConfigIssue as CoreIniConfigIssue,
            IssueSeverity as CoreIssueSeverity},
  };
  ```
  IMPORTANT: Read `classic-scangame-core/src/lib.rs` to confirm whether `ba2`, `ini`, `enb` are publicly re-exported. If not, use `classic_scangame_core::ba2::*` etc. directly.

  Step 2 — Add wrapper fns + enum mapping helpers ABOVE the bridge block:

  ```rust
  // ─── BA2 ───
  fn scangame_run_ba2_check(archive_path: &str) -> ffi::Ba2IssuesSummaryDto {
      let issues: CoreBA2Issues = match core_run_ba2_check(archive_path) {
          Ok(i) => i,
          Err(_) => return ffi::Ba2IssuesSummaryDto {
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

  fn scangame_get_ba2_tex_dims(archive_path: &str) -> Vec<String> {
      core_run_ba2_check(archive_path).map(|i| i.tex_dims).unwrap_or_default()
  }
  fn scangame_get_ba2_tex_frmt(archive_path: &str) -> Vec<String> {
      core_run_ba2_check(archive_path).map(|i| i.tex_frmt).unwrap_or_default()
  }
  fn scangame_get_ba2_snd_frmt(archive_path: &str) -> Vec<String> {
      core_run_ba2_check(archive_path).map(|i| i.snd_frmt).unwrap_or_default()
  }
  fn scangame_get_ba2_xse_files(archive_path: &str) -> Vec<String> {
      core_run_ba2_check(archive_path).map(|i| i.xse_file).unwrap_or_default()
  }

  // ─── INI ───
  fn map_issue_severity(s: CoreIssueSeverity) -> ffi::IssueSeverity {
      match s {
          CoreIssueSeverity::Error => ffi::IssueSeverity::Error,
          CoreIssueSeverity::Warning => ffi::IssueSeverity::Warning,
          CoreIssueSeverity::Info => ffi::IssueSeverity::Info,
      }
  }

  fn scangame_run_ini_check(ini_path: &str, game_name: &str) -> Vec<ffi::IniConfigIssueDto> {
      core_run_ini_check(ini_path, game_name)
          .unwrap_or_default()
          .into_iter()
          .map(|i: CoreIniConfigIssue| ffi::IniConfigIssueDto {
              key: i.key,
              section: i.section,
              found_value: i.found_value,
              expected_value: i.expected_value,
              severity: map_issue_severity(i.severity),
          })
          .collect()
  }

  // ─── ENB ───
  fn map_enb_result(r: CoreEnbResult) -> ffi::EnbResult {
      match r {
          CoreEnbResult::NotPresent => ffi::EnbResult::NotPresent,
          CoreEnbResult::PresentNoConfig => ffi::EnbResult::PresentNoConfig,
          CoreEnbResult::PresentWithConfig => ffi::EnbResult::PresentWithConfig,
          CoreEnbResult::PresentWithIniOverride => ffi::EnbResult::PresentWithIniOverride,
      }
  }
  fn map_enb_config_result(r: CoreEnbConfigResult) -> ffi::EnbConfigResult {
      match r {
          CoreEnbConfigResult::Valid => ffi::EnbConfigResult::Valid,
          CoreEnbConfigResult::HasConflicts => ffi::EnbConfigResult::HasConflicts,
          CoreEnbConfigResult::Missing => ffi::EnbConfigResult::Missing,
          CoreEnbConfigResult::NotApplicable => ffi::EnbConfigResult::NotApplicable,
      }
  }

  fn scangame_run_enb_check(game_path: &str) -> ffi::EnbValidationResultDto {
      let r: CoreEnbValidationResult = match core_run_enb_check(game_path) {
          Ok(r) => r,
          Err(_) => return ffi::EnbValidationResultDto {
              enb_result: ffi::EnbResult::NotPresent,
              config_result: ffi::EnbConfigResult::NotApplicable,
              errors_csv: String::new(),
          },
      };
      ffi::EnbValidationResultDto {
          enb_result: map_enb_result(r.enb_result),
          config_result: map_enb_config_result(r.config_result),
          errors_csv: r.errors.join("\n"),
      }
  }
  ```

  Step 3 — EXTEND the existing `#[cxx::bridge(namespace = "classic::scangame")]` block. Add the three new shared enums + four new shared structs + nine new extern "Rust" declarations. KEEP all existing items.

  ```rust
  #[cxx::bridge(namespace = "classic::scangame")]
  mod ffi {
      // EXISTING shared structs (KEEP UNCHANGED)
      struct SetupCheckResult { /* unchanged */ }
      struct PathDetectionNeeds { /* unchanged */ }

      // NEW — D-04/D-07 shared enums
      #[repr(u8)]
      enum IssueSeverity { Error = 0, Warning = 1, Info = 2 }

      #[repr(u8)]
      enum EnbResult {
          NotPresent = 0,
          PresentNoConfig = 1,
          PresentWithConfig = 2,
          PresentWithIniOverride = 3,
      }

      #[repr(u8)]
      enum EnbConfigResult {
          Valid = 0,
          HasConflicts = 1,
          Missing = 2,
          NotApplicable = 3,
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

      struct IniConfigIssueDto {
          key: String,
          section: String,
          found_value: String,
          expected_value: String,
          severity: IssueSeverity,
      }

      struct EnbValidationResultDto {
          enb_result: EnbResult,
          config_result: EnbConfigResult,
          errors_csv: String,
      }

      extern "Rust" {
          // EXISTING (KEEP UNCHANGED — D-08)
          fn run_setup_checks(/* unchanged signature */) -> SetupCheckResult;
          fn needs_path_detection(/* unchanged signature */) -> PathDetectionNeeds;

          // NEW — BA2
          fn scangame_run_ba2_check(archive_path: &str) -> Ba2IssuesSummaryDto;
          fn scangame_get_ba2_tex_dims(archive_path: &str) -> Vec<String>;
          fn scangame_get_ba2_tex_frmt(archive_path: &str) -> Vec<String>;
          fn scangame_get_ba2_snd_frmt(archive_path: &str) -> Vec<String>;
          fn scangame_get_ba2_xse_files(archive_path: &str) -> Vec<String>;

          // NEW — INI
          fn scangame_run_ini_check(ini_path: &str, game_name: &str) -> Vec<IniConfigIssueDto>;

          // NEW — ENB
          fn scangame_run_enb_check(game_path: &str) -> EnbValidationResultDto;
      }
  }
  ```

  Step 4 — EXTEND the existing `#[cfg(test)] mod tests` block (or add it if missing) with new tests covering each new fn. Use the behavior list above as test coverage.

  ```rust
  #[cfg(test)]
  mod tests {
      use super::*;

      // Existing tests preserved …

      #[test]
      fn test_scangame_run_ba2_check_nonexistent_returns_no_issues() {
          let r = scangame_run_ba2_check("nonexistent.ba2");
          assert!(!r.has_issues);
          assert_eq!(r.total, 0);
          assert_eq!(r.tex_dim_count, 0);
          assert_eq!(r.tex_fmt_count, 0);
          assert_eq!(r.snd_fmt_count, 0);
          assert_eq!(r.xse_file_count, 0);
      }

      #[test]
      fn test_scangame_get_ba2_categories_empty_for_nonexistent() {
          assert!(scangame_get_ba2_tex_dims("nonexistent.ba2").is_empty());
          assert!(scangame_get_ba2_tex_frmt("nonexistent.ba2").is_empty());
          assert!(scangame_get_ba2_snd_frmt("nonexistent.ba2").is_empty());
          assert!(scangame_get_ba2_xse_files("nonexistent.ba2").is_empty());
      }

      #[test]
      fn test_scangame_run_ini_check_empty_inputs_returns_empty() {
          let r = scangame_run_ini_check("", "");
          assert!(r.is_empty());
      }

      #[test]
      fn test_scangame_run_enb_check_nonexistent_returns_not_present() {
          let r = scangame_run_enb_check("nonexistent\\path");
          assert!(matches!(r.enb_result, ffi::EnbResult::NotPresent));
          assert!(r.errors_csv.is_empty());
      }
  }
  ```

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` and confirm all pass (existing + new). Run `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` and fix any warnings.

  IMPORTANT: If `core_run_ba2_check` / `core_run_ini_check` / `core_run_enb_check` have different exact names or are async (returning `Future` / `Result`), use the actual signatures from the direct read in step 1. For async fns, wrap in `classic_shared_core::get_runtime().block_on(...)` per the existing scangame.rs `run_setup_checks` pattern.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'fn scangame_run_(ba2|ini|enb)_check' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 3+ wrapper definitions and 3+ extern declarations
    - `git grep -nE 'fn scangame_get_ba2_(tex_dims|tex_frmt|snd_frmt|xse_files)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 4+ wrapper definitions and 4+ extern declarations
    - `git grep -nE 'enum (IssueSeverity|EnbResult|EnbConfigResult)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 3+ shared enum declarations
    - `git grep -nE 'struct (Ba2IssuesSummaryDto|IniConfigIssueDto|EnbValidationResultDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` returns 3+ shared struct declarations
    - `git grep -n 'fn run_setup_checks' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'fn needs_path_detection' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` STILL returns the existing fn (D-08 preserved)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` exits 0 with at least 6 passing tests (existing 2 + 4+ new)
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 violations)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scangame.rs` exposes BA2/INI/ENB sub-domain bridge fns + 3 shared enums + 3 new DTOs, all Rust-side tests pass, and no existing fns were modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add D-11 consumer migration in GameFilesWorker, run incremental builds, refresh D-09 baseline, commit</name>

  <files>
    - classic-gui/src/workers/gamefilesworker.cpp
    - classic-gui/src/workers/gamefilesworker.h
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/workers/gamefilesworker.cpp (current scope; find existing methods like `doScan()`; understand how `classic::scangame::run_setup_checks()` is currently called)
    - classic-gui/src/workers/gamefilesworker.h (declared methods)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"D-11 Consumer Migration Enumeration" §"classic-gui/src/workers/gamefilesworker.cpp" (the migration recipe — recommends adding GameFilesWorker::doDetailedScan or similar)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (existing run_setup_checks call stays), D-09, D-11 (consumer migration)
  </read_first>

  <action>
  ## Part A — Add a new GameFilesWorker method that calls one of the new bridge fns

  Edit `classic-gui/src/workers/gamefilesworker.h` to declare a new method, e.g.:

  ```cpp
  // New for D-11 / Phase 2 — exposes the bridge BA2 sub-domain check.
  // Returns the Ba2IssuesSummaryDto for a single archive path.
  classic::scangame::Ba2IssuesSummaryDto doBa2CheckForArchive(const QString& archivePath);

  // OR (alternative):
  // QStringList doIniCheckForGame(const QString& iniPath, const QString& gameName);
  ```

  Edit `classic-gui/src/workers/gamefilesworker.cpp` to implement the method. The simplest production-ready implementation:

  ```cpp
  #include "classic_cxx_bridge/scangame.h"

  classic::scangame::Ba2IssuesSummaryDto GameFilesWorker::doBa2CheckForArchive(const QString& archivePath) {
      const auto archiveStdStr = archivePath.toStdString();
      const auto archiveRustStr = ::rust::Str(archiveStdStr.data(), archiveStdStr.size());
      return classic::scangame::scangame_run_ba2_check(archiveRustStr);
  }
  ```

  The exact CXX-generated namespace path (e.g., `classic::scangame::scangame_run_ba2_check` vs `classic::scangame::scangameRunBa2Check`) depends on the generated header — check the actual generated `include/classic_cxx_bridge/scangame.h` after the build. CXX preserves Rust function names verbatim (snake_case stays snake_case for CXX, unlike NAPI).

  IMPORTANT: This is the D-11 production caller. The exact GUI integration (signal/slot wiring, when this method is called) is OUT OF SCOPE — we only need the method to EXIST, COMPILE, and LINK. A unit test in this plan is OPTIONAL; the build proof comes from the incremental build pass.

  Choose ONE of the new bridge fns to consume. The simplest choice is `scangame_run_ba2_check` (returns a flat scalar DTO).

  ## Part B — Incremental builds (NO -Clean required — scangame.rs is already in build.rs)

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
  ```

  Both must exit 0. The Validation Architecture row 2-05-01 specifies incremental builds for this plan because no new file is added to `build.rs::cxx_build::bridges`.

  If MSVC fails with `C2027 use of undefined type` referencing the new shared enum or struct, fall back to a clean build (`-Clean -Test`) to verify it's not just stale incremental state, then debug further.

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

  Commit message: `Feat(02-05): widen scangame bridge with BA2/INI/ENB sub-domains` — body mentions CXXS-04 (partial), D-04, D-05, D-06, D-07, D-09, D-11.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'classic::scangame::(scangame_run_ba2_check|scangame_run_ini_check|scangame_run_enb_check)' classic-gui/src/workers/gamefilesworker.cpp` returns at least one match
    - `git grep -n 'doBa2CheckForArchive\|doIniCheckForGame\|doEnbCheck' classic-gui/src/workers/gamefilesworker.h` returns the new method declaration
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "scangame"` for the 9 new fns + 3 new enums + 3 new structs
    - `git log -1 --stat` shows the commit touches both Rust source AND the C++ consumer migration AND the parity baseline atomically
  </acceptance_criteria>

  <done>
    Plan 02-05 complete — scangame BA2/INI/ENB sub-domains are bridged, GameFilesWorker has at least one production caller for the new surface, both builds pass, and the parity gate is at 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scangame::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` — exits 0 (incremental OK — no new build.rs entries)
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` — exits 0
4. Parity gate at 0 drift after --update-baseline
5. New scangame_run_* fns appear in `include/classic_cxx_bridge/scangame.h` after the build
6. GameFilesWorker has a new method calling one of the new bridge fns

Validation Architecture (per 02-VALIDATION.md row 2-05-01): `cargo test -p classic-cpp-bridge scangame::tests` + incremental build_cli.ps1 -Test + parity gate.
</verification>

<success_criteria>
- src/scangame.rs widened with BA2/INI/ENB sub-domain entry points using D-06 split (BA2 summary + 4 per-category getters; INI returns Vec; ENB returns single-result DTO)
- 3 new CXX shared enums (IssueSeverity, EnbResult, EnbConfigResult) per D-04/D-07
- 3 new flat shared struct DTOs (Ba2IssuesSummaryDto, IniConfigIssueDto, EnbValidationResultDto) — all Pitfall 6 CLEAR
- Existing fns (run_setup_checks, needs_path_detection) UNCHANGED (D-08)
- GameFilesWorker has a new method calling at least one of the new bridge fns (D-11)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-05-SUMMARY.md` documenting:
- Exact entries added to scangame bridge module (BA2 fns, INI fns, ENB fns; counts of new structs and enums)
- Which GameFilesWorker method was added and which bridge fn it calls (D-11 confirmation)
- Pitfall 6 verification result (no `Vec<StructWithVec>` patterns in any new DTO)
- Incremental build outcome
- Note on D-08 backward-compat: existing run_setup_checks and needs_path_detection unchanged
</output>