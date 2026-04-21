---
phase: 02-cxx-bridge-surface-expansion
plan: 08
type: execute
wave: 4
depends_on:
  - 02-cxx-bridge-surface-expansion/01
  - 02-cxx-bridge-surface-expansion/02
  - 02-cxx-bridge-surface-expansion/03
  - 02-cxx-bridge-surface-expansion/04
  - 02-cxx-bridge-surface-expansion/05
  - 02-cxx-bridge-surface-expansion/06
  - 02-cxx-bridge-surface-expansion/07
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
  - classic-cli/src/scanner.cpp
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-03
  - CXXS-10
must_haves:
  truths:
    - "src/scanner.rs exposes get_fcx_config_issues() returning Vec<FcxIssueDto> alongside the existing fcx_reset_global_state() (CXXS-03)"
    - "FcxIssueDto mirrors classic_scanlog_core::fcx_handler::ConfigIssue field-for-field — file_path, section_or_empty/has_section, setting, current_value, recommended_value, description, severity (Pitfall 6 CLEAR — only String + bool fields; the Option<String> section is flattened to section_or_empty + has_section per the Bridge String/Path Contract from plan 02-01)"
    - "get_fcx_config_issues() empty-state behavior is explicitly documented and tested: after fcx_reset_global_state(), the next get_fcx_config_issues() call returns an empty Vec — matching the fail-soft reset semantics in classic-scanlog-core/src/fcx_handler.rs and classic-cpp-bridge/src/scanner.rs (Codex review MEDIUM correction)"
    - "Existing fcx_reset_global_state() UNCHANGED (D-08)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (FINAL CXXS-10 proof — clean build pair as the phase-final verification)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "classic-cli/src/scanner.cpp scan_with_config invokes classic::scanner::get_fcx_config_issues() after the scan completes and prints a summary to stdout when any issues are detected — D-11 in-flow consumer migration (Codex review HIGH correction)"
    - "ALL CXXS-01..CXXS-10 are satisfied — phase complete"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs"
      provides: "Widened scanner bridge with FcxIssueDto + get_fcx_config_issues() (CXXS-03)"
      contains: "FcxIssueDto"
    - path: "classic-cli/src/scanner.cpp"
      provides: "D-11 consumer — scan_with_config calls get_fcx_config_issues() after the scan and prints a summary"
      contains: "classic::scanner::get_fcx_config_issues"
    - path: "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
      provides: "FINAL Phase 2 baseline with all CXXS-01..CXXS-10 surface entries committed"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs"
      to: "classic-scanlog-core::fcx_handler (GLOBAL_FCX_HANDLER + ConfigIssue + get_detected_issues)"
      via: "use classic_scanlog_core::fcx_handler::*"
      pattern: "GLOBAL_FCX_HANDLER"
    - from: "classic-cli/src/scanner.cpp"
      to: "classic_cxx_bridge/scanner.h (get_fcx_config_issues)"
      via: "C++ call to classic::scanner::get_fcx_config_issues() inside scan_with_config"
      pattern: "classic::scanner::get_fcx_config_issues"
---

<objective>
Add the FCX issue getter (CXXS-03) to `src/scanner.rs` alongside the existing `fcx_reset_global_state()`. Per RESEARCH.md §"FCX getter (CXXS-03)", `ConfigIssue` from `classic_scanlog_core::fcx_handler` has 7 fields with one `Option<String>` (`section`) — bridge as `FcxIssueDto` with `section_or_empty: String` (`""` when None) plus `has_section: bool` flag (matches the Bridge String/Path Contract from plan 02-01). Per D-08, the existing `fcx_reset_global_state()` stays unchanged. This is the LAST plan in Phase 2 — it ALSO performs the FINAL phase verification (clean builds on both frontends) AND adds a real D-11 consumer migration in `classic-cli/src/scanner.cpp` so the new namespace is exercised by every actual scan run.

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan treated D-11 as N/A and stopped at "the bridge fn exists, parity is green". The Codex review correctly noted this fails ROADMAP.md Phase 2 success criterion 2 ("C++ frontend code can call into ... `classic::scanner::get_fcx_config_issues()`"). This plan now adds a real consumer migration in `classic-cli/src/scanner.cpp::scan_with_config` — after the scan completes, the C++ side calls `classic::scanner::get_fcx_config_issues()` and prints a summary line for any detected issues. The build proof is now end-to-end: every CLI scan exercises the new bridge fn.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan did not define what `get_fcx_config_issues()` returns when FCX has never run or has been reset. The empty-state behavior was implicit. This plan now defines and tests the empty-state contract:
- After `fcx_reset_global_state()`, the next `get_fcx_config_issues()` call MUST return an empty `Vec<FcxIssueDto>`.
- Before any scan has run (fresh process state), `get_fcx_config_issues()` returns whatever the lazy-init `GLOBAL_FCX_HANDLER` produces — since `FcxModeHandler::new(false)` creates an empty `detected_issues: Vec<ConfigIssue>`, the result is also an empty Vec.
- The bridge wrapper does NOT panic on empty state, does NOT throw, and does NOT block on async operations. The lock pattern matches the existing `fcx_reset_global_state` body in `scanner.rs`.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan said "FcxIssueDto mirrors fcx_handler::ConfigIssue field-for-field" but didn't enumerate the field set explicitly. This plan now lists every field, including the explicit treatment of `section: Option<String>` → `section_or_empty: String` + `has_section: bool` (Bridge String/Path Contract pattern from plan 02-01). The tests explicitly construct a ConfigIssue with `section: None` AND a ConfigIssue with `section: Some("Display")` and verify both round-trip correctly through the bridge.

Purpose: This plan finishes Phase 2. CXXS-03 is a small surface change (one new struct + one new fn). The clean-build pair at the end is the FINAL CXXS-10 verification — every prior plan's clean build was for ITS new file; this plan re-verifies the COMPLETE phase 2 surface as a unit. The D-11 consumer migration in classic-cli/src/scanner.cpp ensures the new namespace is actually exercised by production code (Codex HIGH correction).

Output: scanner.rs widened with FCX getter; classic-cli/src/scanner.cpp consumes it after every scan; FINAL phase 2 baseline committed; both clean MSVC builds green; CXXS-01..CXXS-10 ALL satisfied.
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

# Source-of-truth Rust crate (REAL ConfigIssue field set verified)
@ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs

# Bridge file this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs

# D-11 consumer migration site
@classic-cli/src/scanner.cpp

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- REAL classic-scanlog-core::fcx_handler surface (verified by direct read). -->

```rust
// classic_scanlog_core::fcx_handler

use parking_lot::Mutex;  // NOTE: parking_lot::Mutex, NOT std::sync::Mutex
use std::sync::LazyLock;

pub static GLOBAL_FCX_HANDLER: LazyLock<Mutex<FcxModeHandler>> =
    LazyLock::new(|| Mutex::new(FcxModeHandler::new(false)));

pub struct ConfigIssue {
    pub file_path: String,
    pub section: Option<String>,    // <<< the only Option field
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: String,
}

pub struct FcxModeHandler {
    pub fcx_mode: bool,
    pub main_files_check: Option<String>,
    pub game_files_check: Option<String>,
    pub detected_issues: Vec<ConfigIssue>,
    // ...
    pub checks_run: bool,
}

impl FcxModeHandler {
    pub fn new(fcx_mode: bool) -> Self;  // creates with empty detected_issues
    pub fn add_issue(&mut self, issue: ConfigIssue);
    pub fn set_detected_issues(&mut self, issues: Vec<ConfigIssue>);
    pub fn get_detected_issues(&self) -> &[ConfigIssue];
}
```

Bridge DTO (Pitfall 6 CLEAR — only String + bool fields, no Vec inside):
```rust
struct FcxIssueDto {
    file_path: String,
    section_or_empty: String,    // "" when source ConfigIssue.section is None
    has_section: bool,           // distinguishes None from Some("")
    setting: String,
    current_value: String,
    recommended_value: String,
    description: String,
    severity: String,
}
```

Bridge fn:
```rust
fn get_fcx_config_issues() -> Vec<FcxIssueDto>
```

The lock pattern uses `parking_lot::Mutex::lock()` (returns a guard directly, no Result). The existing `fcx_reset_global_state()` body in `scanner.rs` uses the SAME `GLOBAL_FCX_HANDLER.lock()` pattern — replicate it.
</interfaces>

<empty_state_contract>
<!-- Codex review MEDIUM correction: define empty/uninitialized FCX behavior. -->

**Empty-state semantics for `get_fcx_config_issues()`:**

1. **Fresh process** — On first call (before any scan), `GLOBAL_FCX_HANDLER` lazy-initializes to `FcxModeHandler::new(false)`, which constructs with `detected_issues: Vec::new()`. The bridge fn returns an empty `Vec<FcxIssueDto>` immediately.

2. **After successful reset** — After `fcx_reset_global_state()` succeeds, the handler's `detected_issues` is cleared. The next `get_fcx_config_issues()` call returns an empty `Vec<FcxIssueDto>`.

3. **After scan with no FCX issues** — After a scan that found no FCX configuration problems, `detected_issues` remains empty. Result: empty Vec.

4. **After scan with FCX issues** — After a scan that detected one or more issues, `detected_issues` contains them. The bridge maps each `ConfigIssue` to a `FcxIssueDto` (one-to-one) and returns the Vec.

5. **Lock contention** — Since the lock is `parking_lot::Mutex`, `.lock()` blocks until acquired (no Result return). The bridge fn does not panic on lock acquisition.

6. **Re-entry / idempotence** — Calling `get_fcx_config_issues()` multiple times in a row WITHOUT any intervening scan or reset returns the same Vec each time. The fn is read-only against the global state.

**No-throw guarantee:** The bridge fn is NOT declared `Result<...>` — it cannot fail. All paths return a (possibly empty) Vec.
</empty_state_contract>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scanner.rs with FcxIssueDto + get_fcx_config_issues() bridge fn + empty-state tests (CXXS-03 + Codex MEDIUM correction)</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs (READ — confirm exact ConfigIssue field names; confirm GLOBAL_FCX_HANDLER type uses parking_lot::Mutex; confirm get_detected_issues returns &[ConfigIssue])
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs (current state — has fcx_reset_global_state(); the existing body shows the GLOBAL_FCX_HANDLER lock pattern; replicate it for the getter)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 08" (the HIGH and MEDIUM concerns)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"FCX getter (CXXS-03)" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-05 (default DTO shape — flat per-issue), D-08 (keep existing fcx_reset_global_state), D-12 (Rust tests)
  </read_first>

  <behavior>
    - Test (empty-state contract): After `fcx_reset_global_state()`, `get_fcx_config_issues()` returns empty Vec.
    - Test (empty-state contract): On a fresh state (no scan run), `get_fcx_config_issues()` returns empty Vec.
    - Test: Each FcxIssueDto field is correctly mapped from the ConfigIssue source — for an issue with `section: None`, `section_or_empty == ""` AND `has_section == false`; for an issue with `section: Some("Display")`, `section_or_empty == "Display"` AND `has_section == true`.
    - Test: After `set_detected_issues` (called via the global handler) with TWO ConfigIssues, `get_fcx_config_issues()` returns a Vec with EXACTLY 2 entries in the same order.
    - Test (regression): `fcx_reset_global_state()` still works as before (D-08).
    - Test (idempotence): Calling `get_fcx_config_issues()` twice in a row returns Vecs of equal length without intervening state changes.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`. KEEP the existing `fcx_reset_global_state()` fn UNCHANGED. ADD the new wrapper fn + bridge struct + extern declaration.

  Step 1 — Add imports (extend existing):
  ```rust
  use classic_scanlog_core::fcx_handler::{ConfigIssue as CoreFcxConfigIssue, GLOBAL_FCX_HANDLER};
  ```
  (or whatever path the actual symbols live at — confirm via direct read of fcx_handler.rs)

  Step 2 — Add the wrapper fn:
  ```rust
  fn get_fcx_config_issues() -> Vec<ffi::FcxIssueDto> {
      // parking_lot::Mutex — lock() returns the guard directly (no Result)
      let handler = GLOBAL_FCX_HANDLER.lock();
      handler
          .get_detected_issues()
          .iter()
          .map(|i: &CoreFcxConfigIssue| {
              let has_section = i.section.is_some();
              ffi::FcxIssueDto {
                  file_path: i.file_path.clone(),
                  section_or_empty: i.section.clone().unwrap_or_default(),
                  has_section,
                  setting: i.setting.clone(),
                  current_value: i.current_value.clone(),
                  recommended_value: i.recommended_value.clone(),
                  description: i.description.clone(),
                  severity: i.severity.clone(),
              }
          })
          .collect()
  }
  ```

  IMPORTANT: Confirm `parking_lot::Mutex::lock()` does NOT return a Result — it returns the guard directly. Verified at `classic-scanlog-core/src/fcx_handler.rs:13` (`use parking_lot::Mutex`).

  Step 3 — Extend the existing `#[cxx::bridge]` block in scanner.rs. ADD the FcxIssueDto shared struct and the new extern declaration. KEEP the existing `fcx_reset_global_state` declaration UNCHANGED.

  ```rust
  #[cxx::bridge(namespace = "classic::scanner")]
  mod ffi {
      // EXISTING shared types (KEEP UNCHANGED)
      // …

      // NEW for CXXS-03
      // Mirrors classic_scanlog_core::fcx_handler::ConfigIssue field-for-field
      // (Codex MEDIUM correction). Option<String>.section is flattened to
      // section_or_empty + has_section per the Bridge String/Path Contract
      // from plan 02-01.
      struct FcxIssueDto {
          file_path: String,
          section_or_empty: String,
          has_section: bool,
          setting: String,
          current_value: String,
          recommended_value: String,
          description: String,
          severity: String,
      }

      extern "Rust" {
          // (existing extern declarations preserved)
          // fn fcx_reset_global_state() -> Result<()>;

          // NEW
          fn get_fcx_config_issues() -> Vec<FcxIssueDto>;
      }
  }
  ```

  Step 4 — Extend the `#[cfg(test)]` block:
  ```rust
  #[cfg(test)]
  mod tests {
      use super::*;

      // Existing tests preserved …

      #[test]
      #[serial_test::serial]
      fn test_get_fcx_config_issues_after_reset_returns_empty() {
          // Codex MEDIUM correction: empty-state contract
          let _ = fcx_reset_global_state();
          let issues = get_fcx_config_issues();
          assert!(issues.is_empty());
      }

      #[test]
      #[serial_test::serial]
      fn test_get_fcx_config_issues_idempotent() {
          let _ = fcx_reset_global_state();
          let issues1 = get_fcx_config_issues();
          let issues2 = get_fcx_config_issues();
          assert_eq!(issues1.len(), issues2.len());
      }

      #[test]
      #[serial_test::serial]
      fn test_get_fcx_config_issues_round_trips_section_none_and_some() {
          let _ = fcx_reset_global_state();
          // Inject two issues directly via the handler — one with section: None, one with section: Some
          {
              let mut handler = GLOBAL_FCX_HANDLER.lock();
              handler.set_detected_issues(vec![
                  CoreFcxConfigIssue {
                      file_path: "Fallout4.ini".to_string(),
                      section: None,
                      setting: "iNumThreads".to_string(),
                      current_value: "4".to_string(),
                      recommended_value: "8".to_string(),
                      description: "thread count too low".to_string(),
                      severity: "warning".to_string(),
                  },
                  CoreFcxConfigIssue {
                      file_path: "Fallout4Prefs.ini".to_string(),
                      section: Some("Display".to_string()),
                      setting: "iSize W".to_string(),
                      current_value: "640".to_string(),
                      recommended_value: "1920".to_string(),
                      description: "resolution too low".to_string(),
                      severity: "info".to_string(),
                  },
              ]);
          }
          let issues = get_fcx_config_issues();
          assert_eq!(issues.len(), 2);

          // First issue: section None
          assert_eq!(issues[0].file_path, "Fallout4.ini");
          assert_eq!(issues[0].section_or_empty, "");
          assert!(!issues[0].has_section);
          assert_eq!(issues[0].setting, "iNumThreads");
          assert_eq!(issues[0].current_value, "4");
          assert_eq!(issues[0].recommended_value, "8");
          assert_eq!(issues[0].description, "thread count too low");
          assert_eq!(issues[0].severity, "warning");

          // Second issue: section Some("Display")
          assert_eq!(issues[1].file_path, "Fallout4Prefs.ini");
          assert_eq!(issues[1].section_or_empty, "Display");
          assert!(issues[1].has_section);
          assert_eq!(issues[1].setting, "iSize W");

          // Cleanup
          let _ = fcx_reset_global_state();
      }

      #[test]
      #[serial_test::serial]
      fn test_get_fcx_config_issues_does_not_panic_on_repeat() {
          let _ = fcx_reset_global_state();
          let issues1 = get_fcx_config_issues();
          let issues2 = get_fcx_config_issues();
          assert_eq!(issues1.len(), issues2.len());
      }
  }
  ```

  Add `serial_test = { workspace = true }` to `classic-cpp-bridge/Cargo.toml [dev-dependencies]` if not already present (the existing `registry.rs` test module uses serial_test for the same global-state reason).

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner::tests` and confirm all pass. Run clippy.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'fn get_fcx_config_issues' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns 2+ lines (definition + extern declaration)
    - `git grep -n 'struct FcxIssueDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns the shared struct declaration
    - `git grep -nE 'file_path: String|section_or_empty: String|has_section: bool|setting: String|current_value: String|recommended_value: String|description: String|severity: String' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns at least 8 field declarations inside FcxIssueDto (Codex MEDIUM correction proof — full ConfigIssue field set mirror)
    - `git grep -n 'fn fcx_reset_global_state' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'has_section' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns the field declaration AND its usage in the mapper (Option flattening with explicit bool flag)
    - `git grep -n 'set_detected_issues' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns the test that injects fixture issues (proves empty-state and round-trip tests are present)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner::tests` exits 0 with at least 4 new passing tests (including the round-trip section None/Some test)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scanner.rs` exposes the FCX getter alongside the existing reset, FcxIssueDto mirrors fcx_handler::ConfigIssue field-for-field with Option flattening, empty-state behavior is explicitly tested, all tests pass, no regressions.
  </done>
</task>

<task type="auto">
  <name>Task 2: D-11 consumer migration in classic-cli/src/scanner.cpp scan_with_config (Codex HIGH correction)</name>

  <files>
    - classic-cli/src/scanner.cpp
  </files>

  <read_first>
    - classic-cli/src/scanner.cpp (current state — has scan_with_config which orchestrates the scan loop and prints the final summary; the new fn call goes near the end of scan_with_config, between the report-write loop and the final fmt::print summary block, so it's part of every scan run)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 08" Codex HIGH concern about D-11
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08, D-09, D-11
  </read_first>

  <action>
  ## Part A — Add `#include "classic_cxx_bridge/scanner.h"` to classic-cli/src/scanner.cpp

  At the top of `classic-cli/src/scanner.cpp`, near the existing CXX bridge includes (e.g., where `#include "classic_cxx_bridge/scanner.h"` may already exist for the orchestrator types), confirm the include is present. If not, add it.

  ## Part B — Extend scan_with_config to call get_fcx_config_issues after the scan loop

  Find the end of `scan_with_config` after the report-write loop and BEFORE the final fmt::print summary block. Add:

  ```cpp
  // D-11 / CXXS-03 consumer migration (Codex HIGH correction):
  // After the scan completes, surface any FCX configuration issues that the
  // analysis pipeline detected. This call exercises the new bridge fn from
  // every CLI scan run, satisfying ROADMAP.md Phase 2 success criterion 2.
  try {
      auto fcx_issues = classic::scanner::get_fcx_config_issues();
      if (!fcx_issues.empty()) {
          fmt::print("\nFCX Configuration Issues Detected ({}):\n", fcx_issues.size());
          for (const auto& issue : fcx_issues) {
              std::string file_path(issue.file_path.data(), issue.file_path.size());
              std::string setting(issue.setting.data(), issue.setting.size());
              std::string current(issue.current_value.data(), issue.current_value.size());
              std::string recommended(issue.recommended_value.data(), issue.recommended_value.size());
              std::string description(issue.description.data(), issue.description.size());
              std::string severity(issue.severity.data(), issue.severity.size());
              if (issue.has_section) {
                  std::string section(issue.section_or_empty.data(), issue.section_or_empty.size());
                  fmt::print("  [{}] {}/[{}] {}: {} (current: {}, recommended: {}) — {}\n",
                      severity, file_path, section, setting, description, current, recommended, "");
              } else {
                  fmt::print("  [{}] {} {}: {} (current: {}, recommended: {})\n",
                      severity, file_path, setting, description, current, recommended);
              }
          }
      }
  } catch (const rust::Error& e) {
      // Fail-soft: FCX surface is non-critical for the CLI exit code
      fmt::print(stderr, "Warning: failed to read FCX issues: {}\n", std::string(e.what()));
  }
  ```

  This call exercises `get_fcx_config_issues()` after every scan, satisfying D-11 by being part of the production CLI flow. When no FCX issues are present (the common case), the code path is silent — no output noise. When FCX issues ARE present, they're printed inline in the existing CLI output area.

  Verify the integration:
  ```bash
  grep -n 'classic::scanner::get_fcx_config_issues' classic-cli/src/scanner.cpp
  ```

  Should return at least one match.
  </action>

  <verify>
    <automated>cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'classic::scanner::get_fcx_config_issues' classic-cli/src/scanner.cpp` returns at least one match (Codex HIGH correction proof)
    - `git grep -n 'has_section' classic-cli/src/scanner.cpp` returns at least one match (the section flattening is consumed by the C++ caller)
    - The new code is INSIDE `scan_with_config`, not in a separate dormant helper
    - The call is wrapped in `try { ... } catch (const rust::Error&) { ... }` for fail-soft behavior matching the existing CLI error-handling pattern
  </acceptance_criteria>

  <done>
    classic-cli/src/scanner.cpp exercises classic::scanner::get_fcx_config_issues() in the production scan flow — Codex HIGH correction satisfied; ROADMAP.md Phase 2 success criterion 2 met for the FCX getter.
  </done>
</task>

<task type="auto">
  <name>Task 3: FINAL Phase 2 verification — D-10 clean-build pair, full Rust suite, parity gate, atomic commit</name>

  <files>
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09, D-10 (NOT mandatory for this plan since no new build.rs entries — but RUN the clean-build pair anyway as the FINAL phase verification per the plan's stated objective), D-11
    - .planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md row 2-08-01 + the "Sampling Rate" section ("Before /gsd:verify-work: Full suite must be green, including clean -Test on both frontends and check_parity_gate.py at 0 drift")
    - .planning/REQUIREMENTS.md §"CXX Bridge Surface (CXXS)" — re-read all 10 items to confirm everything is covered by the plans
  </read_first>

  <action>
  ## Part A — Run the full Rust workspace test to catch any cross-crate regressions

  ```
  cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
  ```

  Must exit 0. Any failures here indicate a Phase 2 change broke something elsewhere in the workspace; fix before proceeding.

  ## Part B — FINAL CXXS-10 clean-build pair (Phase 2 final verification)

  Even though scanner.rs is NOT a new build.rs entry (so D-10 isn't strictly mandatory for this plan), this is the LAST plan in Phase 2 — the FINAL verification of the entire phase. RUN both clean builds:

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. This is the FINAL CXXS-10 acceptance test — `classic-cli` and `classic-gui` build clean against the FULLY widened bridge surface.

  If either clean build fails, that's a Phase 2 regression — debug, fix, and re-run before commit.

  ## Part C — D-09 baseline refresh (final)

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  The gate must exit 0 with 0 drift. The committed baseline now reflects the COMPLETE Phase 2 surface — every CXXS-01..CXXS-10 entry is present.

  ## Part D — Phase 2 closeout sanity check

  Verify each requirement is satisfied by inspecting the parity baseline:

  ```bash
  # CXXS-01: classic::constants
  grep -c '"bridgeModule": "constants"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: > 0

  # CXXS-02: classic::web
  grep -c '"bridgeModule": "web"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: > 0

  # CXXS-03: get_fcx_config_issues in scanner
  grep -c 'get_fcx_config_issues' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: > 0

  # CXXS-04: scangame BA2/INI/ENB/TOML/Wrye/integrity/setup_structured/crashgen
  grep -cE 'ba2_scan_archive_summary|ini_validator_validate_inis|enb_checker_validate|crashgen_checker_check|wrye_parse_html_rows|integrity_run_all_checks|scangame_run_setup_structured|crashgen_orchestrator_check_summary' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 8

  # CXXS-05: db_pool_get_entry_typed / db_pool_get_entries_batch_typed
  grep -cE 'db_pool_get_entry_typed|db_pool_get_entries_batch_typed' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 2

  # CXXS-06: classic::version_registry namespace + version_registry_get_all_for_game
  grep -c '"bridgeModule": "version_registry"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  grep -c 'version_registry_get_all_for_game' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Both expected: > 0

  # CXXS-07: yaml_data_suspects_error_rules / yaml_data_suspects_stack_rules_metadata / yaml_data_suspects_stack_count_rules_for_id
  grep -cE 'yaml_data_suspects_error_rules|yaml_data_suspects_stack_rules_metadata|yaml_data_suspects_stack_count_rules_for_id' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 3

  # CXXS-08: classic::path namespace
  grep -c '"bridgeModule": "path"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: > 0

  # CXXS-09: classic::xse namespace
  grep -c '"bridgeModule": "xse"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: > 0

  # CXXS-10: clean builds (just verified by Part B)
  ```

  Document the actual counts in the SUMMARY.md.

  ## Part E — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
  - `classic-cli/src/scanner.cpp`
  - All 4 baseline artifacts

  Commit message: `Feat(02-08): expose FCX issue getter (CXXS-03) and finalize Phase 2 CXX bridge surface` — body mentions CXXS-03, CXXS-10, D-08, D-09, D-11, the Codex HIGH correction (D-11 consumer in scan_with_config), the Codex MEDIUM correction (empty-state contract documented and tested), and "Phase 2 complete — CXXS-01..CXXS-10 all satisfied".
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `docs/implementation/cxx_api_parity/baseline/parity_contract.json` contains entries for ALL of: `bridgeModule: "constants"`, `bridgeModule: "web"`, `bridgeModule: "path"`, `bridgeModule: "xse"`, `bridgeModule: "version_registry"`, plus widened entries in `scangame`, `config`, `database`, `scanner`
    - `git grep -n 'get_fcx_config_issues' docs/implementation/cxx_api_parity/baseline/parity_contract.json` returns at least one match
    - `git grep -n 'version_registry_get_all_for_game' docs/implementation/cxx_api_parity/baseline/parity_contract.json` returns at least one match
    - `git grep -n 'classic::scanner::get_fcx_config_issues' classic-cli/src/scanner.cpp` returns at least one match (D-11 consumer is in production code)
    - `git log -1 --stat` shows the commit touches scanner.rs AND classic-cli/src/scanner.cpp AND the parity baseline atomically
  </acceptance_criteria>

  <done>
    Plan 02-08 complete; CXXS-03 and CXXS-10 satisfied; PHASE 2 IS COMPLETE — all 10 CXXS requirements satisfied; the parity gate is at 0 drift; both clean MSVC builds are green; D-11 in-flow consumer migration in classic-cli/src/scanner.cpp exercises the new namespace from production code.
  </done>
</task>

</tasks>

<verification>
This is the FINAL plan in Phase 2. Verify the entire phase outcome:

1. `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` — exits 0 (full suite — no Phase 2 change broke anything)
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` — exits 0 (FINAL clean build — full widened bridge)
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` — exits 0 (FINAL clean build)
4. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 drift
5. Per-requirement spot checks (Part D grep counts) confirm all 10 CXXS items are represented in the baseline
6. classic-cli/src/scanner.cpp has the D-11 in-flow consumer (Codex HIGH correction)
7. scanner.rs tests cover the empty-state contract (Codex MEDIUM correction)

Validation Architecture (per 02-VALIDATION.md row 2-08-01): `cargo test -p classic-cpp-bridge scanner::tests` + clean-build pair + parity gate at 0 drift.

This plan also satisfies the VALIDATION.md "Before /gsd:verify-work" sampling requirement — full suite green + clean -Test on both frontends + parity at 0 drift.
</verification>

<success_criteria>
- src/scanner.rs exposes FcxIssueDto + get_fcx_config_issues() alongside the existing fcx_reset_global_state() (CXXS-03)
- FcxIssueDto mirrors classic_scanlog_core::fcx_handler::ConfigIssue field-for-field (Codex MEDIUM correction)
- Empty-state contract is explicitly defined and tested: post-reset, fresh-process, and post-scan-no-issues all return empty Vec (Codex MEDIUM correction)
- Section None/Some round-trip is explicitly tested
- classic-cli/src/scanner.cpp scan_with_config exercises classic::scanner::get_fcx_config_issues() in the production flow (Codex HIGH correction — D-11 satisfied for FCX getter)
- Existing fcx_reset_global_state() UNCHANGED (D-08)
- Full Rust workspace test suite green
- Both FINAL clean MSVC builds green (CXXS-10 satisfied with the FULL widened bridge)
- Parity gate at 0 drift (D-09 — final phase 2 baseline committed)
- ALL CXXS-01..CXXS-10 satisfied per the per-requirement grep checks
- Atomic commit
- PHASE 2 COMPLETE
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-08-SUMMARY.md` documenting:
- FcxIssueDto field mapping confirmation (file_path, section_or_empty, has_section, setting, current_value, recommended_value, description, severity — Codex MEDIUM correction)
- Empty-state contract test results (Codex MEDIUM correction)
- D-11 consumer migration confirmation (classic-cli/src/scanner.cpp — Codex HIGH correction)
- D-10 final clean-build outcome on both frontends
- Per-CXXS spot check counts (from Part D grep commands) — proves each requirement is covered in the final baseline
- Confirmation that Phase 2 is complete — list each CXXS-01..CXXS-10 with the plan(s) that satisfied it:
  - CXXS-01 → Plan 02-02 (constants.rs)
  - CXXS-02 → Plan 02-03 (web.rs)
  - CXXS-03 → Plan 02-08 (this plan — FCX getter)
  - CXXS-04 → Plans 02-05 + 02-06 (scangame widening)
  - CXXS-05 → Plan 02-07 (database typed API)
  - CXXS-06 → Plan 02-04 (version_registry split + get_all_for_game)
  - CXXS-07 → Plan 02-07 (config suspect rules — flattened)
  - CXXS-08 → Plan 02-01 (path.rs promotion + widening)
  - CXXS-09 → Plan 02-04 (xse.rs split)
  - CXXS-10 → Verified in this plan (final clean-build pair on the FULL widened bridge)

Also create `.planning/phases/02-cxx-bridge-surface-expansion/02-PHASE-COMPLETE.md` (or update an existing equivalent) noting the phase outcome and any deferred follow-ups (e.g., Phase 6 doc rewrite).
</output>
