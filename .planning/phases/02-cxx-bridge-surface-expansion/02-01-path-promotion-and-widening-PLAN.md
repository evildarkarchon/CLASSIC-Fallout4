---
phase: 02-cxx-bridge-surface-expansion
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
  - classic-gui/src/app/pathdialog.cpp
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-08
  - CXXS-10
must_haves:
  truths:
    - "src/path.rs is listed in build.rs::cxx_build::bridges([...]) so its #[cxx::bridge(namespace = \"classic::path\")] block produces generated headers in include/classic_cxx_bridge/path.h"
    - "src/path.rs exposes the full classic-path-core surface (validation, restricted-path, IniCheckResult, backup, parse_xse_log, find_game_path) per CXXS-08"
    - "classic-gui/src/app/pathdialog.cpp uses classic::path::check_restricted_path() (D-11 consumer migration; old classic::game::check_restricted_path call replaced or paired with the new include)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10 mandatory clean-build pair after build.rs change)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "All path bridge fns have a #[cfg(test)] mod tests block (D-12)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/path.rs\""
      contains: "src/path.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs"
      provides: "Full classic-path-core bridge surface (validation, restricted, IniCheckResult, backup, find_game_path)"
      min_lines: 200
      contains: "namespace = \"classic::path\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs"
      provides: "Compatibility shims for check_restricted_path / validate_path / find_game_path that delegate to classic_path_core (D-08)"
    - path: "classic-gui/src/app/pathdialog.cpp"
      provides: "Includes classic_cxx_bridge/path.h and calls classic::path::check_restricted_path (D-11 migration)"
      contains: "classic::path::check_restricted_path"
    - path: "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
      provides: "Refreshed CXX baseline including all new path.rs entries (D-09)"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      to: "src/path.rs"
      via: "cxx_build::bridges array entry"
      pattern: "src/path\\.rs"
    - from: "classic-gui/src/app/pathdialog.cpp"
      to: "classic_cxx_bridge/path.h"
      via: "C++ #include + classic::path::check_restricted_path call"
      pattern: "classic::path::check_restricted_path"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs"
      to: "classic-path-core (validator, checker::IniCheckResult, backup::BackupManager, game_path::parse_xse_log)"
      via: "use classic_path_core::{...} imports"
      pattern: "use classic_path_core"
---

<objective>
Promote `src/path.rs` from a source-only file into the `build.rs::cxx_build::bridges([...])` list AND widen it to cover the full `classic-path-core` validation/backup/checker surface required by CXXS-08. This is the first plan in Phase 2 because every other path migration depends on `classic::path::*` headers existing in `include/classic_cxx_bridge/`. Also migrate the one already-confirmed D-11 consumer (`classic-gui/src/app/pathdialog.cpp`) so the new namespace has at least one production caller.

Purpose: D-03 requires `path.rs` go into `build.rs` early so subsequent plans can reference `classic::path::*` types without race conditions, and CXXS-08 requires the full `classic-path-core` surface. The research §"D-11 Consumer Migration Enumeration" identified `pathdialog.cpp` as the confirmed migration site.

Output: Widened `src/path.rs` with all CXXS-08 helpers; `pathdialog.cpp` migrated to `classic::path::check_restricted_path`; `game.rs` keeps shims so existing callers continue to compile (D-08); refreshed parity baseline committed in the same commit.
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
@.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md

# Source of truth — what's currently in the bridge (read these to see existing patterns)
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# Source of truth — classic-path-core surface to mirror
@ClassicLib-rs/business-logic/classic-path-core/src/lib.rs

# Source of truth — D-11 consumer migration site
@classic-gui/src/app/pathdialog.cpp

# Reference pattern — small single-purpose bridge module
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs

# Parity gate tools (D-09 refresh runs through these)
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Key types from classic-path-core that path.rs must mirror. -->
<!-- Executor uses these directly — no exploration needed. -->

From classic-path-core::validator (existing public fns):
```rust
pub fn validate_path_exists(path: &str) -> Result<(), String>;
pub fn validate_is_directory(path: &str) -> Result<(), String>;
pub fn validate_is_file(path: &str) -> Result<(), String>;
pub fn validate_required_files(dir: &str, required: &[String]) -> Result<(), String>;
pub fn validate_custom_scan_path(path: &str) -> Result<(), String>;
pub fn is_restricted_path(path: &str) -> bool;
pub fn is_valid_path(path: &str) -> bool;
```

From classic-path-core::checker::IniCheckResult:
```rust
pub struct IniCheckResult {
    pub has_ini: bool,
    pub has_custom_ini: bool,
    pub has_prefs_ini: bool,
    pub ini_path: String,
    pub custom_ini_path: String,
    pub prefs_ini_path: String,
}
pub fn check_ini_files(docs_path: &str, game_name: &str) -> IniCheckResult;
```

From classic-path-core::backup::BackupManager:
```rust
impl BackupManager {
    pub fn create_timestamped(source_path: &str, game_name: &str) -> Result<String, String>;
    pub fn list_existing(source_path: &str, game_name: &str) -> Vec<String>;
}
```

From classic-path-core::game_path:
```rust
pub fn parse_xse_log(log_path: &str) -> Result<String, String>;
pub fn find_game_path(game_exe: &str, xse_loader: Option<&str>, game_name: &str, is_vr: bool, cached_path: Option<&str>, xse_log_path: Option<&str>) -> Option<PathBuf>;
```

Existing path.rs (already in repo, NOT yet in build.rs):
```rust
#[cxx::bridge(namespace = "classic::path")]
mod ffi {
    extern "Rust" {
        fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String;
        fn resolve_fallout4_exe_name(selected_game_version: &str) -> String;
        fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String;
    }
}
```

Existing game.rs path helpers (to gain shims that delegate to path.rs / classic_path_core):
```rust
fn find_game_path(game_exe: &str, xse_loader: &str, game_name: &str, is_vr: bool, cached_path: &str, xse_log_path: &str) -> String;
fn validate_path(path: &str) -> bool;
fn check_restricted_path(path: &str) -> bool;
```

The CXX shared struct `IniCheckResultDto` has all flat String/bool fields (Pitfall 6 CLEAR per RESEARCH.md §"Pitfall 6 DTO Validation").
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Promote path.rs into build.rs and widen with CXXS-08 surface</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current 14-file list — add `"src/path.rs"` AFTER `"src/game.rs"` to keep ordering predictable)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (current 3-fn surface; EXTEND, do not replace existing fns)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (current path helpers; ADD shims that delegate to classic_path_core or to crate::path::*; existing C++ callers must keep working per D-08)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template for a single-purpose bridge module with #[cfg(test)] mod tests)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs (template for nested-but-flat shared struct using YamlDataModSolutionCriteria — IniCheckResultDto follows the same pattern)
    - ClassicLib-rs/business-logic/classic-path-core/src/lib.rs (re-exports for validator, checker, backup, game_path; confirm exact pub item names)
    - ClassicLib-rs/business-logic/classic-path-core/src/validator.rs (exact signatures of validate_path_exists / validate_is_directory / validate_is_file / validate_required_files / validate_custom_scan_path / is_restricted_path / is_valid_path)
    - ClassicLib-rs/business-logic/classic-path-core/src/checker.rs (IniCheckResult struct definition + check_ini_files signature)
    - ClassicLib-rs/business-logic/classic-path-core/src/backup.rs (BackupManager::create_timestamped + list_existing exact signatures)
    - ClassicLib-rs/business-logic/classic-path-core/src/game_path.rs (parse_xse_log + find_game_path exact signatures)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-path-core (CXXS-08)" and §"D-11 Consumer Migration Enumeration"
  </read_first>

  <behavior>
    - Test: Adding "src/path.rs" to build.rs::cxx_build::bridges([...]) results in include/classic_cxx_bridge/path.h being generated on a clean build (proven by D-10 clean build pair).
    - Test: validate_path on `env!("CARGO_MANIFEST_DIR")` returns true (it's a valid existing directory).
    - Test: is_restricted_path("C:\\Windows") returns true on Windows; is_restricted_path on CARGO_MANIFEST_DIR returns false.
    - Test: docs_checker_check_ini_files(nonexistent docs, "Fallout4") returns IniCheckResultDto with has_ini=false, has_custom_ini=false, has_prefs_ini=false, ini_path="", custom_ini_path="", prefs_ini_path="".
    - Test: backup_list_existing("nonexistent\\path", "Fallout4") returns empty Vec<String> (fail-soft on missing source).
    - Test: parse_xse_log("nonexistent.log") returns Err with non-empty message.
    - Test: find_game_path with empty inputs returns "" (existing helper preserved with same fail-soft behavior).
    - Test: detect_fallout4_game_path / resolve_fallout4_exe_name / detect_fallout4_docs_path existing tests still pass (regression guard for the 3 fns already in path.rs).
  </behavior>

  <action>
  ## Part A — Add path.rs to build.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`. Insert `"src/path.rs",` into the `cxx_build::bridges([...])` array AFTER `"src/game.rs",`. New list (keep all existing entries):

  ```rust
  cxx_build::bridges([
      "src/types.rs",
      "src/runtime.rs",
      "src/registry.rs",
      "src/yaml.rs",
      "src/config.rs",
      "src/scanner.rs",
      "src/database.rs",
      "src/files.rs",
      "src/scangame.rs",
      "src/game.rs",
      "src/path.rs",
      "src/update.rs",
      "src/message.rs",
      "src/perf.rs",
      "src/markdown.rs",
  ])
  ```

  No change to `lib.rs` is needed — `pub mod path;` is already declared (verified by reading current `lib.rs`).

  ## Part B — Widen src/path.rs with the CXXS-08 surface

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`. KEEP the existing 3 fns (`detect_fallout4_game_path`, `resolve_fallout4_exe_name`, `detect_fallout4_docs_path`) and the existing `#[cfg(test)] mod tests` for those.

  ADD these new wrapper fns (above the bridge block) that call into `classic-path-core`:

  ```rust
  use classic_path_core::{
      backup::BackupManager,
      checker::{check_ini_files as core_check_ini_files, IniCheckResult as CoreIniCheckResult},
      game_path::{find_game_path as core_find_game_path, parse_xse_log as core_parse_xse_log},
      validator::{
          is_restricted_path as core_is_restricted_path,
          is_valid_path as core_is_valid_path,
          validate_custom_scan_path as core_validate_custom_scan_path,
          validate_is_directory as core_validate_is_directory,
          validate_is_file as core_validate_is_file,
          validate_path_exists as core_validate_path_exists,
          validate_required_files as core_validate_required_files,
      },
  };

  // Validation helpers — fail-soft Result<(), String>
  fn path_validate_exists(path: &str) -> Result<(), String> {
      core_validate_path_exists(path).map_err(|e| e.to_string())
  }
  fn path_validate_is_directory(path: &str) -> Result<(), String> {
      core_validate_is_directory(path).map_err(|e| e.to_string())
  }
  fn path_validate_is_file(path: &str) -> Result<(), String> {
      core_validate_is_file(path).map_err(|e| e.to_string())
  }
  fn path_validate_required_files(dir: &str, required: &[String]) -> Result<(), String> {
      core_validate_required_files(dir, required).map_err(|e| e.to_string())
  }
  fn path_validate_custom_scan(path: &str) -> Result<(), String> {
      core_validate_custom_scan_path(path).map_err(|e| e.to_string())
  }

  // Predicate helpers — fail-soft bool
  fn is_valid_path(path: &str) -> bool { core_is_valid_path(path) }
  fn is_restricted_path(path: &str) -> bool { core_is_restricted_path(path) }

  // Compatibility for the bool helper that game.rs currently exposes
  fn validate_path(path: &str) -> bool { core_is_valid_path(path) }
  fn check_restricted_path(path: &str) -> bool { core_is_restricted_path(path) }

  // INI check — wraps IniCheckResult into a flat shared struct
  fn docs_checker_check_ini_files(docs_path: &str, game_name: &str) -> ffi::IniCheckResultDto {
      let r: CoreIniCheckResult = core_check_ini_files(docs_path, game_name);
      ffi::IniCheckResultDto {
          has_ini: r.has_ini,
          has_custom_ini: r.has_custom_ini,
          has_prefs_ini: r.has_prefs_ini,
          ini_path: r.ini_path,
          custom_ini_path: r.custom_ini_path,
          prefs_ini_path: r.prefs_ini_path,
      }
  }

  // Backup helpers
  fn backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String, String> {
      BackupManager::create_timestamped(source_path, game_name).map_err(|e| e.to_string())
  }
  fn backup_list_existing(source_path: &str, game_name: &str) -> Vec<String> {
      BackupManager::list_existing(source_path, game_name)
  }

  // XSE log + game-path discovery (moved out of game.rs scope)
  fn parse_xse_log(log_path: &str) -> Result<String, String> {
      core_parse_xse_log(log_path).map_err(|e| e.to_string())
  }
  fn find_game_path(
      game_exe: &str,
      xse_loader: &str,
      game_name: &str,
      is_vr: bool,
      cached_path: &str,
      xse_log_path: &str,
  ) -> String {
      let xse_loader_opt = if xse_loader.is_empty() { None } else { Some(xse_loader) };
      let cached_opt = if cached_path.is_empty() { None } else { Some(cached_path) };
      let xse_log_opt = if xse_log_path.is_empty() { None } else { Some(xse_log_path) };
      core_find_game_path(game_exe, xse_loader_opt, game_name, is_vr, cached_opt, xse_log_opt)
          .map(|p| p.to_string_lossy().to_string())
          .unwrap_or_default()
  }
  ```

  EXTEND the existing `#[cxx::bridge(namespace = "classic::path")]` block to declare:

  ```rust
  #[cxx::bridge(namespace = "classic::path")]
  mod ffi {
      // Flat shared struct — IniCheckResult mirror (Pitfall 6 CLEAR — all String/bool)
      struct IniCheckResultDto {
          has_ini: bool,
          has_custom_ini: bool,
          has_prefs_ini: bool,
          ini_path: String,
          custom_ini_path: String,
          prefs_ini_path: String,
      }

      extern "Rust" {
          // EXISTING (preserved)
          fn detect_fallout4_game_path(cached_path: &str, selected_game_version: &str) -> String;
          fn resolve_fallout4_exe_name(selected_game_version: &str) -> String;
          fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String;

          // NEW — validation Result helpers
          fn path_validate_exists(path: &str) -> Result<()>;
          fn path_validate_is_directory(path: &str) -> Result<()>;
          fn path_validate_is_file(path: &str) -> Result<()>;
          fn path_validate_required_files(dir: &str, required: &[String]) -> Result<()>;
          fn path_validate_custom_scan(path: &str) -> Result<()>;

          // NEW — predicate helpers
          fn is_valid_path(path: &str) -> bool;
          fn is_restricted_path(path: &str) -> bool;

          // NEW — backward-compatible bool aliases (D-11 / pathdialog.cpp uses these names)
          fn validate_path(path: &str) -> bool;
          fn check_restricted_path(path: &str) -> bool;

          // NEW — INI checker
          fn docs_checker_check_ini_files(docs_path: &str, game_name: &str) -> IniCheckResultDto;

          // NEW — backup
          fn backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String>;
          fn backup_list_existing(source_path: &str, game_name: &str) -> Vec<String>;

          // NEW — XSE log + find_game_path moved out of game.rs scope
          fn parse_xse_log(log_path: &str) -> Result<String>;
          fn find_game_path(
              game_exe: &str,
              xse_loader: &str,
              game_name: &str,
              is_vr: bool,
              cached_path: &str,
              xse_log_path: &str,
          ) -> String;
      }
  }
  ```

  ## Part C — Update game.rs shims

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs`. KEEP the existing fn signatures and bridge declarations unchanged (D-08 backward compat). For each of `find_game_path`, `validate_path`, `check_restricted_path`: rewrite the BODY to delegate to `classic_path_core::*` (so they share the exact same implementation as `path.rs`). Do NOT remove these functions from game.rs and do NOT remove their entries from the `#[cxx::bridge(namespace = "classic::game")]` block. The baseline diff for this plan should show ADDITIONS in `path.rs` ONLY — no removals from `game.rs` (D-09 + D-08).

  ## Part D — Add #[cfg(test)] mod tests for the new path.rs surface

  Append to the existing `#[cfg(test)] mod tests` in `path.rs`:

  ```rust
      #[test]
      fn test_is_valid_path_on_manifest_dir() {
          let p = env!("CARGO_MANIFEST_DIR");
          assert!(is_valid_path(p));
          assert!(validate_path(p)); // alias
      }

      #[test]
      fn test_is_restricted_path_false_on_manifest_dir() {
          let p = env!("CARGO_MANIFEST_DIR");
          assert!(!is_restricted_path(p));
          assert!(!check_restricted_path(p)); // alias
      }

      #[test]
      fn test_docs_checker_check_ini_files_missing_returns_all_false() {
          let result = docs_checker_check_ini_files("nonexistent\\path", "Fallout4");
          assert!(!result.has_ini);
          assert!(!result.has_custom_ini);
          assert!(!result.has_prefs_ini);
      }

      #[test]
      fn test_backup_list_existing_missing_source_returns_empty() {
          let result = backup_list_existing("nonexistent\\path", "Fallout4");
          assert!(result.is_empty());
      }

      #[test]
      fn test_parse_xse_log_nonexistent_returns_err() {
          let result = parse_xse_log("nonexistent.log");
          assert!(result.is_err());
      }

      #[test]
      fn test_find_game_path_empty_inputs_returns_empty_string() {
          let result = find_game_path("", "", "", false, "", "");
          assert!(result.is_empty());
      }
  ```

  Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests` and confirm all pass.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/path.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the `cxx_build::bridges` array
    - `git grep -n 'fn path_validate_exists' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns the wrapper function definition AND the bridge `extern "Rust"` declaration
    - `git grep -n 'struct IniCheckResultDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns the shared struct declaration with `has_ini: bool`, `ini_path: String`, etc.
    - `git grep -n 'fn check_restricted_path' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved — not removed)
    - `git grep -n 'fn validate_path' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests` exits 0 and reports at least 9 passing tests (3 existing + 6 new)
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 trait-bound errors)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/path.rs` is in `build.rs`, exposes the full CXXS-08 surface, has a passing #[cfg(test)] block covering every new fn, and `game.rs` shims are preserved per D-08.
  </done>
</task>

<task type="auto">
  <name>Task 2: D-11 consumer migration in pathdialog.cpp + D-10 clean-build pair + D-09 baseline refresh + commit</name>

  <files>
    - classic-gui/src/app/pathdialog.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/app/pathdialog.cpp (find every `classic::game::check_restricted_path` and `classic::game::validate_path` call site; also the #include for `classic_cxx_bridge/game.h`)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"D-11 Consumer Migration Enumeration" §"classic-gui/src/app/pathdialog.cpp" (the migration recipe)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (keep shims), D-09 (per-plan baseline refresh), D-10 (clean-build pair), D-11 (consumer migration)
    - tools/cxx_api_parity/check_parity_gate.py (read the `--update-baseline` flag handling so the executor knows which artifacts get rewritten)
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json (current contents — just to confirm format before refresh)
  </read_first>

  <action>
  ## Part A — Add `classic::path::check_restricted_path` call in pathdialog.cpp (D-11)

  Edit `classic-gui/src/app/pathdialog.cpp`.

  1. Add `#include "classic_cxx_bridge/path.h"` next to the existing `#include "classic_cxx_bridge/game.h"` (do NOT remove the game.h include — game.rs shims still exist per D-08).
  2. Find the call to `classic::game::check_restricted_path(...)` inside `ManualPathDialog::validateAndAccept()` (or wherever it currently lives). Replace it with `classic::path::check_restricted_path(...)`. Same args, same return type — `path.rs` exposes the identical fn signature.
  3. If the same file calls `classic::game::validate_path`, also migrate that to `classic::path::validate_path`.
  4. Do NOT remove or rename any other `classic::game::*` calls — those are PE-version, XSE, version registry concerns and are migrated by other plans.

  Run `git grep -n 'classic::path::check_restricted_path' classic-gui/src/app/pathdialog.cpp` and confirm at least one match.

  ## Part B — Mandatory D-10 clean-build pair (path.rs is a NEW build.rs entry)

  From the repo root, run BOTH (do NOT skip — Pitfall 5 / D-10 says incremental builds can hide header generation order errors):

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. If either fails with `C2027 use of undefined type` or `C2079 uses undefined struct` referencing a CXX-generated header, that is a Pitfall 5 occurrence — fix the include order or struct declaration before re-running. Do NOT use raw `ctest` (AGENTS.md prohibition).

  Confirm `include/classic_cxx_bridge/path.h` exists after the clean build:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/path.h
  ```

  ## Part C — D-09 baseline refresh

  Run the parity gate update flag:
  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  ```

  Then verify the gate is green:
  ```
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  Expected output: exit 0 and a report line saying "drift: 0" (or equivalent — the Phase 1 implementation chose the exact wording; it should match what plans 01-01..01-03 produced).

  Confirm the four committed artifacts changed (or were created):
  ```
  git status docs/implementation/cxx_api_parity/baseline/
  ```

  Expected: changes to `parity_contract.json`, `cxx_diff_report.json`, `cxx_diff_report.md`, `cxx_gate_report.md`.

  ## Part D — Stage everything and commit in one atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs`
  - `classic-gui/src/app/pathdialog.cpp`
  - `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md`
  - `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`

  Use `node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "Feat(02-01): promote path.rs to build.rs and widen for CXXS-08" --files <list>` (per CLAUDE.md commit conventions). The commit message body should mention CXXS-08, CXXS-10, D-03, D-09, D-10, D-11.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'classic::path::check_restricted_path' classic-gui/src/app/pathdialog.cpp` returns at least one line
    - `git grep -n '#include "classic_cxx_bridge/path.h"' classic-gui/src/app/pathdialog.cpp` returns the new include
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/path.h` exists after the clean build (proves Pitfall 5 cleared)
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0
    - The parity gate report file (`docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`) shows 0 drift for `path` bridgeModule entries
    - `git log -1 --stat` shows the commit touches both Rust source AND `docs/implementation/cxx_api_parity/baseline/*.json`/`*.md` (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-01 complete — `path.rs` is gate-locked into the bridge contract, `pathdialog.cpp` is the first D-11 production caller, both clean MSVC builds are green, parity gate is at 0 drift, and the entire change is one atomic commit.
  </done>
</task>

</tasks>

<verification>
After both tasks complete, verify Plan 02-01 is fully done:

1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` — exits 0
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` — exits 0
4. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 drift
5. `git log -1` shows one commit containing all source + baseline changes
6. `git grep -n 'classic::path::check_restricted_path' classic-gui/` returns the migrated call site

Validation Architecture sources (per 02-VALIDATION.md row 2-01-01):
- `cargo test -p classic-cpp-bridge path::tests` (Rust unit tests)
- `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` (D-10)
- `check_parity_gate.py` (D-09)
</verification>

<success_criteria>
- src/path.rs is listed in build.rs::cxx_build::bridges and produces include/classic_cxx_bridge/path.h on a clean build
- src/path.rs exposes the full CXXS-08 surface (validation, restricted-path, IniCheckResult, backup, find_game_path, parse_xse_log) with #[cfg(test)] coverage on every new fn
- classic-gui/src/app/pathdialog.cpp uses classic::path::check_restricted_path (D-11 consumer migration confirmed)
- game.rs shims preserved (D-08 backward compat — game.rs check_restricted_path / validate_path still exist as shims)
- Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test are green (D-10)
- check_parity_gate.py exits 0 with 0 drift after --update-baseline (D-09)
- The four parity baseline artifacts AND the Rust source AND the C++ migration are committed in ONE atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-01-SUMMARY.md` documenting:
- New path.rs entries enumerated (count from cxx_diff_report.md "added" rows)
- D-10 clean-build outcome (both green; any Pitfall 5 surprises observed)
- pathdialog.cpp migration outcome (exact line numbers + before/after snippets)
- Baseline drift after --update-baseline (must be 0)
- Decisions made for the discretion items (game.rs shims kept vs moved; field-naming choices on IniCheckResultDto)
</output>