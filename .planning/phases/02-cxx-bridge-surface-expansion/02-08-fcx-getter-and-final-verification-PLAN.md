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
    - "FcxIssueDto is a flat shared struct with all 7 fields from classic_scanlog_core::fcx_handler::ConfigIssue, with Option<String> section flattened to section_or_empty: String (Pitfall 6 CLEAR per RESEARCH.md)"
    - "Existing fcx_reset_global_state() UNCHANGED (D-08)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (FINAL CXXS-10 proof — clean build pair as the phase-final verification)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "ALL CXXS-01..CXXS-10 are satisfied — phase complete"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs"
      provides: "Widened scanner bridge with FcxIssueDto + get_fcx_config_issues() (CXXS-03)"
      contains: "FcxIssueDto"
    - path: "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
      provides: "FINAL Phase 2 baseline with all CXXS-01..CXXS-10 surface entries committed"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs"
      to: "classic-scanlog-core::fcx_handler::ConfigIssue (via GLOBAL_FCX_HANDLER.lock().get_detected_issues())"
      via: "use classic_scanlog_core::fcx_handler::*"
      pattern: "GLOBAL_FCX_HANDLER"
---

<objective>
Add the FCX issue getter (CXXS-03) to `src/scanner.rs` alongside the existing `fcx_reset_global_state()`. Per RESEARCH.md §"FCX getter (CXXS-03)", `ConfigIssue` from `classic_scanlog_core::fcx_handler` has 7 fields with one `Option<String>` (`section`) — bridge as `FcxIssueDto` with `section_or_empty: String` (`""` when None). Per D-08, the existing `fcx_reset_global_state()` stays unchanged. This is the LAST plan in Phase 2 — it ALSO performs the FINAL phase verification: clean builds on both frontends to satisfy CXXS-10 with the fully-widened bridge surface from Plans 01-07.

Purpose: This plan finishes Phase 2. CXXS-03 is a small surface change (one new struct + one new fn). The clean-build pair at the end is the FINAL CXXS-10 verification — every prior plan's clean build was for ITS new file; this plan re-verifies the COMPLETE phase 2 surface as a unit. Per the deferred-discretion items in CONTEXT.md, this plan also confirms (one final time) that the database typed result API (Plan 02-07) and config suspect-rules (Plan 02-07) compile and link cleanly with the rest of the bridge.

Output: scanner.rs widened with FCX getter; FINAL phase 2 baseline committed; both clean MSVC builds green; CXXS-01..CXXS-10 ALL satisfied.
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

# Source-of-truth Rust crate
@ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs

# Bridge file this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Per RESEARCH.md §"FCX getter (CXXS-03)". -->

```rust
// classic_scanlog_core::fcx_handler
pub struct ConfigIssue {
    pub file_path: String,
    pub section: Option<String>,
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: String,
}

pub static GLOBAL_FCX_HANDLER: /* Mutex<FcxModeHandler> */;

impl FcxModeHandler {
    pub fn get_detected_issues(&self) -> &[ConfigIssue];
    pub fn reset_global_state() -> Result<(), FcxResetError>; // already bridged
}
```

Bridge DTO (Pitfall 6 CLEAR per RESEARCH.md DTO table — all String fields, no Vec):
```rust
struct FcxIssueDto {
    file_path: String,
    section_or_empty: String,  // "" when source ConfigIssue.section is None
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

The exact Mutex/lock pattern depends on `GLOBAL_FCX_HANDLER`'s type — per the existing `fcx_reset_global_state()` body in scanner.rs, the lock pattern is already established. Read scanner.rs and replicate it for the new getter.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen scanner.rs with FcxIssueDto + get_fcx_config_issues() bridge fn + tests (CXXS-03)</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs (READ — confirm exact ConfigIssue field names; confirm GLOBAL_FCX_HANDLER type and how to access get_detected_issues; confirm whether the lock is sync (`std::sync::Mutex`) or async (`tokio::sync::Mutex`); confirm whether get_detected_issues returns &[ConfigIssue] or Vec<ConfigIssue>)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs (current state — has fcx_reset_global_state(); the existing body shows the GLOBAL_FCX_HANDLER lock pattern; replicate it for the getter)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"FCX getter (CXXS-03)" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-05 (default DTO shape — flat per-issue), D-08 (keep existing fcx_reset_global_state), D-12 (Rust tests)
  </read_first>

  <behavior>
    - Test: `get_fcx_config_issues()` after a clean (or freshly reset) global FCX state returns empty Vec.
    - Test: After `fcx_reset_global_state()`, `get_fcx_config_issues()` returns empty Vec (the reset clears the issues list).
    - Test: Each FcxIssueDto field is correctly mapped from the ConfigIssue source — for an issue with `section: None`, `section_or_empty == ""`; for an issue with `section: Some("Display")`, `section_or_empty == "Display"`.
    - Test (regression): `fcx_reset_global_state()` still works as before (D-08).
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
      // Replicate the lock pattern from the existing fcx_reset_global_state() body.
      // If GLOBAL_FCX_HANDLER is a sync std::sync::Mutex:
      let handler = match GLOBAL_FCX_HANDLER.lock() {
          Ok(h) => h,
          Err(poisoned) => poisoned.into_inner(), // recover from poison — same pattern as reset
      };

      handler
          .get_detected_issues()
          .iter()
          .map(|i: &CoreFcxConfigIssue| ffi::FcxIssueDto {
              file_path: i.file_path.clone(),
              section_or_empty: i.section.clone().unwrap_or_default(),
              setting: i.setting.clone(),
              current_value: i.current_value.clone(),
              recommended_value: i.recommended_value.clone(),
              description: i.description.clone(),
              severity: i.severity.clone(),
          })
          .collect()
  }
  ```

  IMPORTANT: If `GLOBAL_FCX_HANDLER` uses a different lock type (e.g., `parking_lot::Mutex`, `tokio::sync::Mutex`, `RwLock`), adapt the lock acquisition. The existing `fcx_reset_global_state()` body in `scanner.rs` is the CANONICAL pattern — replicate exactly. If `get_detected_issues()` returns `Vec<ConfigIssue>` (owned), adjust the iteration accordingly.

  IMPORTANT: If `GLOBAL_FCX_HANDLER` requires a tokio runtime to lock (async Mutex), wrap in `classic_shared_core::get_runtime().block_on(async { ... })` per the one-runtime rule.

  Step 3 — Extend the existing `#[cxx::bridge]` block in scanner.rs. ADD the FcxIssueDto shared struct and the new extern declaration. KEEP the existing `fcx_reset_global_state` declaration UNCHANGED.

  ```rust
  #[cxx::bridge(namespace = "classic::scanner")]
  mod ffi {
      // EXISTING shared types (KEEP UNCHANGED)
      // …

      // NEW for CXXS-03
      struct FcxIssueDto {
          file_path: String,
          section_or_empty: String,
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
  #[test]
  fn test_get_fcx_config_issues_after_reset_returns_empty() {
      // First reset to a known clean state
      let _ = fcx_reset_global_state();
      let issues = get_fcx_config_issues();
      assert!(issues.is_empty());
  }

  #[test]
  fn test_fcx_issue_dto_field_mapping() {
      // This is a unit test on the Option flattening logic — construct a CoreFcxConfigIssue
      // directly and assert that the mapper correctly produces "" when section is None.
      let none_section = CoreFcxConfigIssue {
          file_path: "Fallout4.ini".to_string(),
          section: None,
          setting: "iNumThreads".to_string(),
          current_value: "4".to_string(),
          recommended_value: "8".to_string(),
          description: "test".to_string(),
          severity: "warning".to_string(),
      };
      // (Inline the DTO construction the same way the wrapper does)
      let dto = ffi::FcxIssueDto {
          file_path: none_section.file_path.clone(),
          section_or_empty: none_section.section.clone().unwrap_or_default(),
          setting: none_section.setting.clone(),
          current_value: none_section.current_value.clone(),
          recommended_value: none_section.recommended_value.clone(),
          description: none_section.description.clone(),
          severity: none_section.severity.clone(),
      };
      assert_eq!(dto.section_or_empty, "");
      assert_eq!(dto.file_path, "Fallout4.ini");
  }

  // serial_test required because GLOBAL_FCX_HANDLER is shared mutable state across tests
  #[test]
  #[serial_test::serial]
  fn test_get_fcx_config_issues_does_not_panic_on_repeat() {
      let _ = fcx_reset_global_state();
      let issues1 = get_fcx_config_issues();
      let issues2 = get_fcx_config_issues();
      assert_eq!(issues1.len(), issues2.len());
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
    - `git grep -n 'fn fcx_reset_global_state' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` STILL returns the existing fn (D-08 preserved)
    - `git grep -n 'section_or_empty' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns the field declaration AND its usage in the mapper (Option flattening)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner::tests` exits 0 with at least 3 new passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/scanner.rs` exposes the FCX getter alongside the existing reset, all tests pass, no regressions.
  </done>
</task>

<task type="auto">
  <name>Task 2: FINAL Phase 2 verification — D-10 clean-build pair, full Rust suite, parity gate, atomic commit</name>

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

  Both must exit 0. This is the FINAL CXXS-10 acceptance test — `classic-cli` and `classic-gui` build clean against the FULLY widened bridge surface (path + constants + web + xse + version_registry + scangame + config suspect rules + database typed + scanner FCX getter, all together).

  If either clean build fails, that's a Phase 2 regression — debug, fix, and re-run before commit.

  ## Part C — D-09 baseline refresh (final)

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  The gate must exit 0 with 0 drift. The committed baseline now reflects the COMPLETE Phase 2 surface — every CXXS-01..CXXS-10 entry is present.

  ## Part D — Phase 2 closeout sanity check

  Verify each requirement is satisfied by inspecting the parity baseline:

  ```
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
  grep -c 'scangame_run_ba2_check\|scangame_run_ini_check\|scangame_run_enb_check\|scangame_run_toml_check\|scangame_run_wrye_check\|scangame_run_integrity_check\|scangame_run_setup_structured\|scangame_run_crashgen_check' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 8

  # CXXS-05: db_pool_get_entry_typed / db_pool_get_entries_batch_typed
  grep -c 'db_pool_get_entry_typed\|db_pool_get_entries_batch_typed' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 2

  # CXXS-06: classic::version_registry namespace + version_registry_get_all_for_game
  grep -c '"bridgeModule": "version_registry"' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  grep -c 'version_registry_get_all_for_game' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Both expected: > 0

  # CXXS-07: yaml_data_suspects_error_rules / yaml_data_suspects_stack_rules
  grep -c 'yaml_data_suspects_error_rules\|yaml_data_suspects_stack_rules' docs/implementation/cxx_api_parity/baseline/parity_contract.json
  # Expected: at least 2

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
  - All 4 baseline artifacts

  Commit message: `Feat(02-08): expose FCX issue getter (CXXS-03) and finalize Phase 2 CXX bridge surface` — body mentions CXXS-03, CXXS-10, D-08, D-09, "Phase 2 complete — CXXS-01..CXXS-10 all satisfied".
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
    - `git log -1 --stat` shows the commit touches scanner.rs AND the parity baseline atomically
  </acceptance_criteria>

  <done>
    Plan 02-08 complete; CXXS-03 and CXXS-10 satisfied; PHASE 2 IS COMPLETE — all 10 CXXS requirements satisfied; the parity gate is at 0 drift; both clean MSVC builds are green.
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

Validation Architecture (per 02-VALIDATION.md row 2-08-01): `cargo test -p classic-cpp-bridge scanner::tests` + clean-build pair + parity gate at 0 drift.

This plan also satisfies the VALIDATION.md "Before /gsd:verify-work" sampling requirement — full suite green + clean -Test on both frontends + parity at 0 drift.
</verification>

<success_criteria>
- src/scanner.rs exposes FcxIssueDto + get_fcx_config_issues() alongside the existing fcx_reset_global_state() (CXXS-03)
- Pitfall 6 verified: FcxIssueDto is all-String fields (no Vec), the Option<String>.section flattened to section_or_empty: String
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
- FcxIssueDto field mapping decisions (Option<String> flattening confirmed)
- D-10 final clean-build outcome on both frontends
- Per-CXXS spot check counts (from Part D grep commands) — proves each requirement is covered in the final baseline
- Confirmation that Phase 2 is complete — list each CXXS-01..CXXS-10 with the plan(s) that satisfied it:
  - CXXS-01 → Plan 02-02 (constants.rs)
  - CXXS-02 → Plan 02-03 (web.rs)
  - CXXS-03 → Plan 02-08 (this plan — FCX getter)
  - CXXS-04 → Plans 02-05 + 02-06 (scangame widening)
  - CXXS-05 → Plan 02-07 (database typed API)
  - CXXS-06 → Plan 02-04 (version_registry split + get_all_for_game)
  - CXXS-07 → Plan 02-07 (config suspect rules)
  - CXXS-08 → Plan 02-01 (path.rs promotion + widening)
  - CXXS-09 → Plan 02-04 (xse.rs split)
  - CXXS-10 → Verified in this plan (final clean-build pair on the FULL widened bridge)

Also create `.planning/phases/02-cxx-bridge-surface-expansion/02-PHASE-COMPLETE.md` (or update an existing equivalent) noting the phase outcome and any deferred follow-ups (e.g., Phase 6 doc rewrite).
</output>