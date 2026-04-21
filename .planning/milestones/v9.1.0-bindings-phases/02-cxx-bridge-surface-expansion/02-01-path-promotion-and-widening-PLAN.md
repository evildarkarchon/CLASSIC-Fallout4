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
  - classic-gui/src/app/mainwindow.cpp
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
    - "src/path.rs exposes the full classic-path-core surface (validation, restricted-path, IniCheckResult mirroring DocumentsChecker, backup, parse_xse_log, find_game_path) per CXXS-08"
    - "src/path.rs IniCheckResultDto mirrors classic_path_core::checker::IniCheckResult field-for-field (ini_name, exists, is_valid, message, issue_or_empty) — NOT the previous fictional 6-flag DTO"
    - "Bridge IniCheckResult entry points wrap DocumentsChecker::validate_ini_file and DocumentsChecker::run_all_checks — there is NO check_ini_files free fn"
    - "classic-gui/src/app/pathdialog.cpp uses classic::path::check_restricted_path() (D-11 consumer migration #1)"
    - "classic-gui/src/app/mainwindow.cpp line ~1443 ManualPathDialog::validateAndAccept-style block uses classic::path::check_restricted_path() (D-11 consumer migration #2 — flagged by code review)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10 mandatory clean-build pair after build.rs change)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "All path bridge fns have a #[cfg(test)] mod tests block (D-12)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/path.rs\""
      contains: "src/path.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs"
      provides: "Full classic-path-core bridge surface (validation, restricted, IniCheckResult mirroring DocumentsChecker, backup, find_game_path)"
      min_lines: 200
      contains: "namespace = \"classic::path\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs"
      provides: "Compatibility shims for check_restricted_path / validate_path / find_game_path that delegate to classic_path_core (D-08)"
    - path: "classic-gui/src/app/pathdialog.cpp"
      provides: "Includes classic_cxx_bridge/path.h and calls classic::path::check_restricted_path (D-11 migration #1)"
      contains: "classic::path::check_restricted_path"
    - path: "classic-gui/src/app/mainwindow.cpp"
      provides: "Migrated line ~1443 from classic::game::check_restricted_path to classic::path::check_restricted_path (D-11 migration #2)"
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
    - from: "classic-gui/src/app/mainwindow.cpp"
      to: "classic_cxx_bridge/path.h"
      via: "C++ #include + classic::path::check_restricted_path call (replacing classic::game::check_restricted_path on line ~1443)"
      pattern: "classic::path::check_restricted_path"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs"
      to: "classic-path-core (validator, checker::DocumentsChecker / checker::IniCheckResult, backup::BackupManager, game_path::parse_xse_log)"
      via: "use classic_path_core::{...} imports"
      pattern: "use classic_path_core"
---

<objective>
Promote `src/path.rs` from a source-only file into the `build.rs::cxx_build::bridges([...])` list AND widen it to cover the full `classic-path-core` validation/backup/checker surface required by CXXS-08. This is the first plan in Phase 2 because every other path migration depends on `classic::path::*` headers existing in `include/classic_cxx_bridge/`. Also migrate BOTH confirmed D-11 consumers (`classic-gui/src/app/pathdialog.cpp` AND `classic-gui/src/app/mainwindow.cpp` line ~1443) so the new namespace has at least two production callers.

**REVIEWS-MODE NOTE (Codex review HIGH):** A previous version of this plan referenced a fictional `IniCheckResultDto { has_ini, has_custom_ini, has_prefs_ini, ini_path, custom_ini_path, prefs_ini_path }` and a non-existent `check_ini_files(docs_path, game_name) -> IniCheckResult` free fn. The REAL `classic-path-core::checker::IniCheckResult` has fields `{ ini_name: String, exists: bool, is_valid: bool, message: String, issue: Option<String> }`. The REAL entry point is `DocumentsChecker::new(game_name).validate_ini_file(docs_path: &Path, ini_name: &str) -> DocsPathResult<IniCheckResult>` plus `DocumentsChecker::run_all_checks(docs_path: &Path) -> DocsPathResult<Vec<String>>`. This plan now mirrors that real surface exactly.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan only migrated `pathdialog.cpp` but missed `mainwindow.cpp` line ~1443, which still calls `classic::game::check_restricted_path` for custom scan paths. This plan adds the `mainwindow.cpp` migration explicitly.

Purpose: D-03 requires `path.rs` go into `build.rs` early so subsequent plans can reference `classic::path::*` types without race conditions, and CXXS-08 requires the full `classic-path-core` surface. The Codex review and the research §"D-11 Consumer Migration Enumeration" identified BOTH `pathdialog.cpp` AND `mainwindow.cpp` as required migration sites.

Output: Widened `src/path.rs` with all CXXS-08 helpers; `pathdialog.cpp` AND `mainwindow.cpp` migrated to `classic::path::check_restricted_path`; `game.rs` keeps shims so existing callers continue to compile (D-08); refreshed parity baseline committed in the same commit.
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
@.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md

# Source of truth — what's currently in the bridge (read these to see existing patterns)
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# Source of truth — classic-path-core surface to mirror (REWORKED — read checker.rs THOROUGHLY)
@ClassicLib-rs/business-logic/classic-path-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-path-core/src/checker.rs
@ClassicLib-rs/business-logic/classic-path-core/src/validator.rs
@ClassicLib-rs/business-logic/classic-path-core/src/backup.rs
@ClassicLib-rs/business-logic/classic-path-core/src/game_path.rs

# Source of truth — D-11 consumer migration sites
@classic-gui/src/app/pathdialog.cpp
@classic-gui/src/app/mainwindow.cpp

# Reference pattern — small single-purpose bridge module
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs

# Parity gate tools (D-09 refresh runs through these)
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Key types from classic-path-core that path.rs must mirror. -->
<!-- Verified by direct read of source files (Codex HIGH severity review correction). -->

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

From classic-path-core::checker (REAL — corrected from fictional version):
```rust
pub struct IniCheckResult {
    pub ini_name: String,         // name of the INI file checked
    pub exists: bool,             // whether the INI file exists
    pub is_valid: bool,           // whether the INI file is valid and parseable
    pub message: String,          // human-readable message
    pub issue: Option<String>,    // "missing" / "corrupted" / "missing_archive_section" / etc.
}

impl IniCheckResult {
    pub fn has_issue(&self) -> bool;  // returns issue.is_some()
}

pub struct DocumentsChecker {
    // game_name field is private; constructed via new()
}

impl DocumentsChecker {
    pub fn new(game_name: impl Into<String>) -> Self;
    pub fn check_onedrive_in_path(&self, docs_path: &Path) -> Option<String>;
    pub fn validate_ini_file(&self, docs_path: &Path, ini_name: &str) -> DocsPathResult<IniCheckResult>;
    pub fn run_all_checks(&self, docs_path: &Path) -> DocsPathResult<Vec<String>>;
    pub fn game_name(&self) -> &str;
}

// NOTE: There is NO `check_ini_files` free function. The only entry points
// are DocumentsChecker::validate_ini_file and DocumentsChecker::run_all_checks.
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

Existing game.rs path helpers (gain shims that delegate to path.rs / classic_path_core):
```rust
fn find_game_path(game_exe: &str, xse_loader: &str, game_name: &str, is_vr: bool, cached_path: &str, xse_log_path: &str) -> String;
fn validate_path(path: &str) -> bool;
fn check_restricted_path(path: &str) -> bool;
```

The CXX shared struct `IniCheckResultDto` has all flat String/bool fields with `Option<String>` flattened to `issue_or_empty: String` (Pitfall 6 CLEAR — only String/bool fields).
</interfaces>

<bridge_string_path_contract>
<!-- Codex review MEDIUM severity: spell out the C++→Rust string/path conversion contract. -->
<!-- The bridge surface is string-heavy because CXX cannot share `&Path` directly. -->

**C++→Rust string conversion:**
- C++ callers convert `QString` via `qstr.toUtf8().constData()` or use the project helper `classic::toRustString(qstr)` (defined in `classic-gui/src/core/rust_qt_bridge.h`) which returns `rust::String`.
- C++ callers convert `std::filesystem::path` via `path.u8string()` to get a UTF-8 std::string, then construct `rust::Str` from that.
- C++ callers using `std::string` pass `::rust::Str(s.data(), s.size())`.

**Empty-path policy (fail-soft):**
- All bridge fns that take a path argument MUST treat empty `&str` as "no path provided" and return their fail-soft default (`false` for predicates, empty `Vec` for list helpers, error variant for `Result` returns).
- Empty path inputs MUST NOT panic, MUST NOT throw, MUST NOT call into core functions that would panic on missing paths.
- Internal Rust wrappers convert `&str` to `&Path` via `Path::new(s)` ONLY after the empty check.

**Windows path normalization:**
- The bridge does NOT normalize paths (e.g., does NOT canonicalize separators or resolve symlinks). Normalization stays in `classic-path-core` validators where it already lives.
- Backslash vs forward-slash handling: pass strings through verbatim; `Path::new` handles both on Windows.
- Long-path prefix `\\?\`: pass through verbatim — `classic-path-core::validator::is_valid_path` already handles this.

**`Option<String>` field flattening:**
- All bridge DTOs flatten `Option<String>` to `String` with `""` as the None sentinel.
- The associated bool field (e.g., `has_issue: bool` for `IniCheckResultDto`) lets C++ distinguish None from `Some("")` if needed.
- For `IniCheckResult::issue: Option<String>`, the bridge field is `issue_or_empty: String` and an additional `has_issue: bool` is included (mirrors `IniCheckResult::has_issue()`).

**Result<T, String> conversion:**
- `Result<T, String>` from core helpers maps to CXX `Result<T>` (which throws on the C++ side).
- C++ callers wrap calls in `try { ... } catch (const rust::Error& e) { ... }` (already established pattern in `pathdialog.cpp`).

**`&[String]` slice parameters:**
- `&[String]` works directly on the CXX side as `rust::Slice<rust::String>` — see existing `db_pool_get_entries_batch` and `validate_required_files` patterns.
</bridge_string_path_contract>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Promote path.rs into build.rs and widen with REAL CXXS-08 surface (corrected per Codex review)</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current 14-file list — add `"src/path.rs"` AFTER `"src/game.rs"` to keep ordering predictable)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (current 3-fn surface; EXTEND, do not replace existing fns)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (current path helpers)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template for #[cfg(test)] mod tests pattern)
    - ClassicLib-rs/business-logic/classic-path-core/src/checker.rs (READ ENTIRELY — DocumentsChecker::new, validate_ini_file, run_all_checks, IniCheckResult struct)
    - ClassicLib-rs/business-logic/classic-path-core/src/validator.rs
    - ClassicLib-rs/business-logic/classic-path-core/src/backup.rs
    - ClassicLib-rs/business-logic/classic-path-core/src/game_path.rs
    - ClassicLib-rs/business-logic/classic-path-core/src/lib.rs (re-exports — confirm `pub use checker::{DocumentsChecker, IniCheckResult}` and `pub use validator::*` reach the crate root)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 01" (the HIGH-severity correction this task implements)
  </read_first>

  <behavior>
    - Test: Adding "src/path.rs" to build.rs::cxx_build::bridges results in include/classic_cxx_bridge/path.h being generated on a clean build (proven by D-10 clean build pair).
    - Test: validate_path on `env!("CARGO_MANIFEST_DIR")` returns true (it's a valid existing directory).
    - Test: is_restricted_path("C:\\Windows") returns true on Windows; is_restricted_path on CARGO_MANIFEST_DIR returns false.
    - Test: docs_checker_validate_ini_file(temp_dir, "Fallout4", "Fallout4.ini") on a missing file returns IniCheckResultDto with `exists: false`, `is_valid: false`, `has_issue: true`, `issue_or_empty: "missing"`, and a non-empty `message`.
    - Test: docs_checker_run_all_checks(temp_dir, "Fallout4") on an empty docs dir returns Vec<String> with at least 2 entries (one per missing INI), each non-empty.
    - Test: backup_list_existing("nonexistent\\path", "Fallout4") returns empty Vec<String> (fail-soft on missing source).
    - Test: parse_xse_log("nonexistent.log") returns Err with non-empty message.
    - Test: find_game_path with empty inputs returns "" (existing helper preserved with same fail-soft behavior).
    - Test: detect_fallout4_game_path / resolve_fallout4_exe_name / detect_fallout4_docs_path existing tests still pass (regression guard for the 3 fns already in path.rs).
    - Test: All bridge fns that take path strings handle empty inputs without panicking (per Bridge String/Path Contract above).
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

  No change to `lib.rs` is needed — `pub mod path;` is already declared (verify by reading current `lib.rs`).

  ## Part B — Widen src/path.rs with the REAL CXXS-08 surface (corrected per Codex review)

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`. KEEP the existing 3 fns (`detect_fallout4_game_path`, `resolve_fallout4_exe_name`, `detect_fallout4_docs_path`) and the existing `#[cfg(test)] mod tests` for those.

  ADD these new wrapper fns (above the bridge block) that call into `classic-path-core`:

  ```rust
  use std::path::Path;
  use classic_path_core::{
      backup::BackupManager,
      checker::{DocumentsChecker, IniCheckResult as CoreIniCheckResult},
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

  // ─────────────────────────────────────────────────────────────────────
  // Validation helpers — fail-soft Result<(), String>
  // (Bridge String/Path Contract: empty strings fall through to the
  //  underlying validator, which returns Err with a clear message.)
  // ─────────────────────────────────────────────────────────────────────

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

  // ─────────────────────────────────────────────────────────────────────
  // Predicate helpers — fail-soft bool
  // ─────────────────────────────────────────────────────────────────────

  fn is_valid_path(path: &str) -> bool { core_is_valid_path(path) }
  fn is_restricted_path(path: &str) -> bool { core_is_restricted_path(path) }

  // Compatibility for the bool helper that game.rs currently exposes
  fn validate_path(path: &str) -> bool { core_is_valid_path(path) }
  fn check_restricted_path(path: &str) -> bool { core_is_restricted_path(path) }

  // ─────────────────────────────────────────────────────────────────────
  // INI checker — REAL surface (corrected per Codex HIGH review)
  // Mirrors DocumentsChecker::validate_ini_file and run_all_checks.
  // ─────────────────────────────────────────────────────────────────────

  fn docs_checker_validate_ini_file(
      docs_path: &str,
      game_name: &str,
      ini_name: &str,
  ) -> ffi::IniCheckResultDto {
      // Bridge String/Path Contract: empty docs_path returns a fail-soft "missing" result.
      if docs_path.is_empty() {
          return ffi::IniCheckResultDto {
              ini_name: ini_name.to_string(),
              exists: false,
              is_valid: false,
              message: String::new(),
              issue_or_empty: "missing".to_string(),
              has_issue: true,
          };
      }
      let checker = DocumentsChecker::new(game_name);
      match checker.validate_ini_file(Path::new(docs_path), ini_name) {
          Ok(result) => map_ini_check_result(result),
          Err(_e) => ffi::IniCheckResultDto {
              ini_name: ini_name.to_string(),
              exists: false,
              is_valid: false,
              message: String::new(),
              issue_or_empty: "io_error".to_string(),
              has_issue: true,
          },
      }
  }

  fn docs_checker_run_all_checks(docs_path: &str, game_name: &str) -> Vec<String> {
      if docs_path.is_empty() {
          return Vec::new();
      }
      let checker = DocumentsChecker::new(game_name);
      checker.run_all_checks(Path::new(docs_path)).unwrap_or_default()
  }

  fn map_ini_check_result(r: CoreIniCheckResult) -> ffi::IniCheckResultDto {
      let has_issue = r.issue.is_some();
      ffi::IniCheckResultDto {
          ini_name: r.ini_name,
          exists: r.exists,
          is_valid: r.is_valid,
          message: r.message,
          issue_or_empty: r.issue.unwrap_or_default(),
          has_issue,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // Backup helpers
  // ─────────────────────────────────────────────────────────────────────

  fn backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String, String> {
      BackupManager::create_timestamped(source_path, game_name).map_err(|e| e.to_string())
  }
  fn backup_list_existing(source_path: &str, game_name: &str) -> Vec<String> {
      BackupManager::list_existing(source_path, game_name)
  }

  // ─────────────────────────────────────────────────────────────────────
  // XSE log + game-path discovery
  // ─────────────────────────────────────────────────────────────────────

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
      // Flat shared struct — IniCheckResult REAL mirror
      // Field names match classic_path_core::checker::IniCheckResult exactly,
      // except `issue: Option<String>` is flattened to `issue_or_empty: String`
      // + `has_issue: bool` per the Bridge String/Path Contract above.
      struct IniCheckResultDto {
          ini_name: String,
          exists: bool,
          is_valid: bool,
          message: String,
          issue_or_empty: String,
          has_issue: bool,
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

          // NEW — backward-compatible bool aliases (D-11 / pathdialog.cpp + mainwindow.cpp use these names)
          fn validate_path(path: &str) -> bool;
          fn check_restricted_path(path: &str) -> bool;

          // NEW — REAL INI checker surface (DocumentsChecker mirrors)
          fn docs_checker_validate_ini_file(
              docs_path: &str,
              game_name: &str,
              ini_name: &str,
          ) -> IniCheckResultDto;
          fn docs_checker_run_all_checks(docs_path: &str, game_name: &str) -> Vec<String>;

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
      use tempfile::TempDir;
      use std::fs;

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
      fn test_path_validate_exists_empty_returns_err() {
          assert!(path_validate_exists("").is_err());
      }

      #[test]
      fn test_docs_checker_validate_ini_file_missing_real_shape() {
          let temp_dir = TempDir::new().unwrap();
          let docs_path = temp_dir.path().to_string_lossy().to_string();
          let result = docs_checker_validate_ini_file(&docs_path, "Fallout4", "Fallout4.ini");
          assert!(!result.exists);
          assert!(!result.is_valid);
          assert!(result.has_issue);
          assert_eq!(result.issue_or_empty, "missing");
          assert_eq!(result.ini_name, "Fallout4.ini");
          assert!(!result.message.is_empty());
      }

      #[test]
      fn test_docs_checker_validate_ini_file_empty_path_fail_soft() {
          let result = docs_checker_validate_ini_file("", "Fallout4", "Fallout4.ini");
          assert!(!result.exists);
          assert!(result.has_issue);
      }

      #[test]
      fn test_docs_checker_validate_ini_file_existing_valid() {
          let temp_dir = TempDir::new().unwrap();
          fs::write(
              temp_dir.path().join("Fallout4.ini"),
              "[General]\nkey=value\n",
          )
          .unwrap();
          let docs_path = temp_dir.path().to_string_lossy().to_string();
          let result = docs_checker_validate_ini_file(&docs_path, "Fallout4", "Fallout4.ini");
          assert!(result.exists);
          assert!(result.is_valid);
          assert!(!result.has_issue);
      }

      #[test]
      fn test_docs_checker_run_all_checks_empty_path_returns_empty() {
          assert!(docs_checker_run_all_checks("", "Fallout4").is_empty());
      }

      #[test]
      fn test_docs_checker_run_all_checks_returns_messages_for_missing_inis() {
          let temp_dir = TempDir::new().unwrap();
          let docs_path = temp_dir.path().to_string_lossy().to_string();
          let messages = docs_checker_run_all_checks(&docs_path, "Fallout4");
          // Three checks (Main, Custom, Prefs) all missing → at least 3 messages
          assert!(messages.len() >= 3);
          for msg in &messages {
              assert!(!msg.is_empty());
          }
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

  Add `tempfile = { workspace = true }` to `classic-cpp-bridge/Cargo.toml [dev-dependencies]` if not already present (the existing test pattern in checker.rs uses tempfile).

  Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests` and confirm all pass.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/path.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the `cxx_build::bridges` array
    - `git grep -n 'fn path_validate_exists' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns the wrapper function definition AND the bridge `extern "Rust"` declaration
    - `git grep -n 'struct IniCheckResultDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns the shared struct declaration
    - `git grep -nE 'ini_name: String|exists: bool|is_valid: bool|issue_or_empty: String|has_issue: bool' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns at least 5 matches inside IniCheckResultDto
    - `git grep -n 'fn docs_checker_validate_ini_file' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns 2 matches (definition + extern)
    - `git grep -n 'fn docs_checker_run_all_checks' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns 2 matches
    - `git grep -n 'check_ini_files' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns NOTHING (the fictional fn name is gone)
    - `git grep -n 'has_ini\|has_custom_ini\|has_prefs_ini\|prefs_ini_path' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns NOTHING (the fictional 6-flag DTO is gone)
    - `git grep -n 'DocumentsChecker' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` returns at least one match (the import)
    - `git grep -n 'fn check_restricted_path' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved — not removed)
    - `git grep -n 'fn validate_path' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml path::tests` exits 0 and reports at least 12 passing tests (3 existing + 9 new)
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 trait-bound errors)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/path.rs` is in `build.rs`, exposes the REAL CXXS-08 surface (corrected from the fictional check_ini_files version), has a passing #[cfg(test)] block covering every new fn including the IniCheckResult shape, and `game.rs` shims are preserved per D-08.
  </done>
</task>

<task type="auto">
  <name>Task 2: D-11 consumer migrations (BOTH pathdialog.cpp AND mainwindow.cpp) + D-10 clean-build pair + D-09 baseline refresh + commit</name>

  <files>
    - classic-gui/src/app/pathdialog.cpp
    - classic-gui/src/app/mainwindow.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - classic-gui/src/app/pathdialog.cpp (find every `classic::game::check_restricted_path` and `classic::game::validate_path` call site; also the #include for `classic_cxx_bridge/game.h`)
    - classic-gui/src/app/mainwindow.cpp around lines 1430-1455 (the `if (classic::game::check_restricted_path(...))` block that the Codex review identified — REQUIRED migration site #2)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 01" MEDIUM concern about mainwindow.cpp migration
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"D-11 Consumer Migration Enumeration"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (keep shims), D-09 (per-plan baseline refresh), D-10 (clean-build pair), D-11 (consumer migration)
    - tools/cxx_api_parity/check_parity_gate.py (read the `--update-baseline` flag handling)
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json (current contents — to confirm format before refresh)
  </read_first>

  <action>
  ## Part A — Add `classic::path::check_restricted_path` calls in pathdialog.cpp AND mainwindow.cpp (D-11)

  ### A.1 — pathdialog.cpp (D-11 consumer migration #1)

  Edit `classic-gui/src/app/pathdialog.cpp`.

  1. Add `#include "classic_cxx_bridge/path.h"` next to the existing `#include "classic_cxx_bridge/game.h"` (do NOT remove the game.h include — game.rs shims still exist per D-08).
  2. Find the call to `classic::game::check_restricted_path(...)` inside `ManualPathDialog::validateAndAccept()` (or wherever it currently lives). Replace it with `classic::path::check_restricted_path(...)`. Same args, same return type — `path.rs` exposes the identical fn signature.
  3. If the same file calls `classic::game::validate_path`, also migrate that to `classic::path::validate_path`.
  4. Do NOT remove or rename any other `classic::game::*` calls — those are PE-version, XSE, version registry concerns and are migrated by other plans.

  ### A.2 — mainwindow.cpp (D-11 consumer migration #2 — Codex review correction)

  Edit `classic-gui/src/app/mainwindow.cpp`. Around line 1443 (in the custom-scan-path validation block), find:

  ```cpp
  if (classic::game::check_restricted_path(std::string(path.toUtf8().constData()))) {
  ```

  Replace with:

  ```cpp
  if (classic::path::check_restricted_path(std::string(path.toUtf8().constData()))) {
  ```

  Add `#include "classic_cxx_bridge/path.h"` near the existing CXX bridge includes (the file already includes other `classic_cxx_bridge/*.h` headers — match the existing pattern).

  Do NOT remove the existing `classic_cxx_bridge/game.h` include (D-08 — game.rs shims remain).
  Do NOT modify any other `classic::game::*` or `classic::path::*` calls in mainwindow.cpp — only the line ~1443 restricted-path check.

  Run `git grep -n 'classic::path::check_restricted_path' classic-gui/src/app/` and confirm at least TWO matches (one in pathdialog.cpp, one in mainwindow.cpp).

  Run `git grep -n 'classic::game::check_restricted_path' classic-gui/src/app/mainwindow.cpp` and confirm ZERO matches (the migration is complete in mainwindow.cpp; pathdialog.cpp may or may not still have the game:: form depending on whether it had multiple call sites).

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

  Expected output: exit 0 and a report line saying "drift: 0".

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
  - `classic-gui/src/app/mainwindow.cpp`
  - `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md`
  - `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`

  Use `node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" commit "Feat(02-01): promote path.rs to build.rs and widen for CXXS-08" --files <list>` (per CLAUDE.md commit conventions). The commit message body should mention CXXS-08, CXXS-10, D-03, D-08, D-09, D-10, D-11 and explicitly note both consumer migrations (pathdialog.cpp and mainwindow.cpp).
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'classic::path::check_restricted_path' classic-gui/src/app/pathdialog.cpp` returns at least one line
    - `git grep -n '#include "classic_cxx_bridge/path.h"' classic-gui/src/app/pathdialog.cpp` returns the new include
    - `git grep -n 'classic::path::check_restricted_path' classic-gui/src/app/mainwindow.cpp` returns at least one line (line ~1443 area)
    - `git grep -n 'classic::game::check_restricted_path' classic-gui/src/app/mainwindow.cpp` returns ZERO matches (migration complete)
    - `git grep -n '#include "classic_cxx_bridge/path.h"' classic-gui/src/app/mainwindow.cpp` returns the new include
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/path.h` exists after the clean build (proves Pitfall 5 cleared)
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0
    - The parity gate report file (`docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`) shows 0 drift for `path` bridgeModule entries
    - `git log -1 --stat` shows the commit touches Rust source AND BOTH C++ migration files AND `docs/implementation/cxx_api_parity/baseline/*.json`/`*.md` (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-01 complete — `path.rs` is gate-locked into the bridge contract, `pathdialog.cpp` AND `mainwindow.cpp` are the first TWO D-11 production callers, both clean MSVC builds are green, parity gate is at 0 drift, and the entire change is one atomic commit.
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
6. `git grep -n 'classic::path::check_restricted_path' classic-gui/` returns BOTH migrated call sites (pathdialog.cpp + mainwindow.cpp)

Validation Architecture sources (per 02-VALIDATION.md row 2-01-01):
- `cargo test -p classic-cpp-bridge path::tests` (Rust unit tests)
- `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` (D-10)
- `check_parity_gate.py` (D-09)
</verification>

<success_criteria>
- src/path.rs is listed in build.rs::cxx_build::bridges and produces include/classic_cxx_bridge/path.h on a clean build
- src/path.rs exposes the REAL CXXS-08 surface (DocumentsChecker-based, not the fictional check_ini_files version)
- IniCheckResultDto mirrors classic_path_core::checker::IniCheckResult exactly (ini_name/exists/is_valid/message/issue_or_empty/has_issue)
- src/path.rs has #[cfg(test)] coverage on every new fn including the new IniCheckResult tests
- BOTH classic-gui/src/app/pathdialog.cpp AND classic-gui/src/app/mainwindow.cpp use classic::path::check_restricted_path (D-11 — both consumer migrations confirmed by review)
- game.rs shims preserved (D-08 backward compat — game.rs check_restricted_path / validate_path still exist as shims)
- Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test are green (D-10)
- check_parity_gate.py exits 0 with 0 drift after --update-baseline (D-09)
- The four parity baseline artifacts AND the Rust source AND BOTH C++ migration files are committed in ONE atomic commit
- Bridge String/Path Contract section in plan documents UTF-8/empty-path/normalization/Option-flattening rules
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-01-SUMMARY.md` documenting:
- New path.rs entries enumerated (count from cxx_diff_report.md "added" rows)
- Confirmation that IniCheckResultDto matches the REAL classic_path_core::checker::IniCheckResult shape (Codex HIGH correction)
- Confirmation that BOTH pathdialog.cpp AND mainwindow.cpp migrations are in place (Codex MEDIUM correction)
- D-10 clean-build outcome (both green; any Pitfall 5 surprises observed)
- pathdialog.cpp migration outcome (exact line numbers + before/after snippets)
- mainwindow.cpp migration outcome (exact line numbers + before/after snippets — should be around line 1443)
- Baseline drift after --update-baseline (must be 0)
- Decisions made for the discretion items (game.rs shims kept vs moved; field-naming choices)
</output>
