---
phase: 02-cxx-bridge-surface-expansion
plan: 04
type: execute
wave: 2
depends_on:
  - 02-cxx-bridge-surface-expansion/01
  - 02-cxx-bridge-surface-expansion/02
  - 02-cxx-bridge-surface-expansion/03
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
  - classic-gui/src/app/pathdialog.cpp
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-06
  - CXXS-09
  - CXXS-10
must_haves:
  truths:
    - "src/xse.rs exists, contains #[cxx::bridge(namespace = \"classic::xse\")], and exposes the full classic-xse-core surface (XseType enum, XseInfoDto, detect_xse_version, is_xse_installed, xse_get_loader_name, xse_get_dll_prefix, xse_get_info)"
    - "All xse.rs wrapper bodies use ACTUAL classic-xse-core signatures: detect_xse_version(loader_path: &Path, xse_type: XseType) -> XseResult<Version>; is_xse_installed(game_path: &Path, xse_type: XseType) -> bool; get_xse_info(game_path: &Path, xse_type: XseType) -> XseInfo (Codex review LOW correction)"
    - "XseInfoDto correctly maps PathBuf path → String and Option<semver::Version> version → String (\"\" when None)"
    - "xse_get_type_from_game_id is INFALLIBLE — XseType::from_game_id returns Self (not Option<Self>); the bridge wrapper takes a string game id and only returns empty for unknown game id strings (Codex review LOW correction)"
    - "xse_get_loader_name(F4SE) returns \"f4se_loader.exe\" (verified literal string from classic-xse-core/src/lib.rs:169) and xse_get_dll_prefix(F4SE) returns \"f4se_\" (with trailing underscore — Codex LOW correction)"
    - "src/version_registry.rs exists, contains #[cxx::bridge(namespace = \"classic::version_registry\")], and exposes the full version registry surface"
    - "ALL wrapper fn bodies in version_registry.rs are CONCRETE — there are ZERO todo!() placeholders (Codex review MEDIUM correction)"
    - "version_registry.rs version_registry_get_all_for_game iterates registry.get_all() and filters by game/is_vr (uses existing iteration helper, NOT a missing get_all_for_game core helper)"
    - "Both new files are listed in build.rs::cxx_build::bridges and lib.rs declares pub mod xse + pub mod version_registry"
    - "src/game.rs keeps shims for the moved fns (D-08 backward compat — pathdialog.cpp etc. continue to compile against game.h)"
    - "src/registry.rs is UNCHANGED (D-02 — registry namespace continues to mean classic-registry-core KV singleton)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10 — TWO new build.rs entries in one plan = ONE mandatory clean-build pair)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "classic-gui/src/app/pathdialog.cpp uses classic::xse::xse_get_loader_name(...) (or another classic::xse::* helper) in production C++ — D-11 consumer migration #3 (Codex review MEDIUM correction)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs"
      provides: "New CXX bridge module exposing classic-xse-core (CXXS-09, D-01)"
      min_lines: 180
      contains: "namespace = \"classic::xse\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs"
      provides: "New CXX bridge module exposing classic-version-registry-core full surface (CXXS-06, D-02) — ZERO todo!() placeholders"
      min_lines: 220
      contains: "namespace = \"classic::version_registry\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs"
      provides: "Compatibility shims preserved (D-08)"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array contains \"src/xse.rs\" AND \"src/version_registry.rs\""
      contains: "src/xse.rs"
    - path: "classic-gui/src/app/pathdialog.cpp"
      provides: "D-11 consumer — calls classic::xse::xse_get_loader_name(F4SE) or similar to display the expected XSE loader filename in the UI"
      contains: "classic::xse"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs"
      to: "classic-xse-core (XseType, XseInfo, detect_xse_version, is_xse_installed, get_xse_info — REAL &Path-based signatures)"
      via: "use classic_xse_core::{...}"
      pattern: "use classic_xse_core"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs"
      to: "classic-version-registry-core (get_version_registry, registry.get_all, get_by_id, match_version, get_xse_config, get_crashgen_versions)"
      via: "use classic_version_registry_core::{...}"
      pattern: "use classic_version_registry_core"
    - from: "classic-gui/src/app/pathdialog.cpp"
      to: "classic_cxx_bridge/xse.h"
      via: "C++ #include + classic::xse::xse_get_loader_name call"
      pattern: "classic::xse::"
---

<objective>
Split XSE helpers and version-registry helpers out of `src/game.rs` into TWO new bridge modules: `src/xse.rs` (D-01, CXXS-09) and `src/version_registry.rs` (D-02, CXXS-06). Per D-08, leave delegation shims in `game.rs` so existing C++ callers continue to compile. Add the new `XseType` shared enum (D-04/D-07) plus the typed XSE methods. Add the missing `version_registry_get_all_for_game(game, is_vr)` fn. Both new files land in ONE plan to share a single mandatory D-10 clean-build pair. Adds at least one D-11 consumer migration in `classic-gui/src/app/pathdialog.cpp`.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan had unresolved `todo!()` placeholders in multiple wrapper bodies in `version_registry.rs`. The Codex review correctly noted this means key signature/mapping choices were not actually locked. This plan now contains EVERY wrapper body as concrete code copied (with the namespace adjustment) from `game.rs` lines 14-161. The acceptance criteria explicitly grep for `todo!` in version_registry.rs and require ZERO matches.

**REVIEWS-MODE NOTE (Codex review LOW):** A previous version of this plan invented Option-returning paths for `XseType::from_game_id` and Option-returning `detect_xse_version`. The REAL `classic-xse-core::XseType::from_game_id(GameId) -> Self` is INFALLIBLE (lines 143-150). The REAL `detect_xse_version(loader_path: &Path, xse_type: XseType) -> XseResult<Version>` takes `&Path` and returns a semver `Version` (lines 390-426). The REAL `is_xse_installed(game_path: &Path, xse_type: XseType) -> bool` takes `&Path` (line 450). The REAL `XseInfo.path: PathBuf` and `version: Option<Version>` (lines 226-236). The REAL `dll_prefix()` includes a trailing underscore: `XseType::F4SE.dll_prefix() == "f4se_"` (line 195). This plan now uses the actual signatures and `Path::new(s)` conversions at the bridge boundary.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan treated D-11 as N/A. The roadmap explicitly expects `classic::xse` to be usable from C++. This plan adds a real D-11 consumer migration in `classic-gui/src/app/pathdialog.cpp` — the new namespace is exercised by displaying the expected XSE loader filename in the UI.

Purpose: D-01 and D-02 both move logic out of `game.rs`. Doing them in one plan minimizes the number of mandatory clean-build cycles. The shim approach prevents baseline-removal noise from `game.rs` while the additions land in the new files.

Output: Two new bridge modules with full surfaces and ZERO `todo!()` placeholders; `game.rs` shims preserved; `registry.rs` untouched (D-02); pathdialog.cpp exercises the new XSE namespace; both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source-of-truth Rust crates (REAL signatures verified)
@ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs
@ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs

# Bridge files this plan touches
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# Reference patterns
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs

# D-11 consumer migration site
@classic-gui/src/app/pathdialog.cpp

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-xse-core REAL surface (verified by direct read of lib.rs). -->
<!-- Codex LOW correction: signatures use &Path / semver::Version / total mapping. -->

```rust
pub enum XseType { F4SE, F4SEVR, SKSE, SKSE64, SKSEVR, SFSE }
impl XseType {
    pub fn as_str(self) -> &'static str;        // "F4SE" / "F4SEVR" / etc.
    pub fn from_game_id(game_id: GameId) -> Self;  // INFALLIBLE — returns Self
    pub fn loader_name(self) -> &'static str;   // "f4se_loader.exe" / "skse64_loader.exe" / etc.
    pub fn dll_prefix(self) -> &'static str;    // "f4se_" / "skse64_" / etc. (TRAILING UNDERSCORE)
}

pub struct XseInfo {
    pub xse_type: XseType,
    pub path: PathBuf,                  // NOT String
    pub version: Option<semver::Version>, // NOT Option<String>
    pub installed: bool,
}
impl XseInfo {
    pub fn new(xse_type: XseType, path: PathBuf) -> Self;
    pub fn check_installed(&self) -> bool;
    pub fn loader_path(&self) -> PathBuf;
}

pub fn detect_xse_version(loader_path: &Path, xse_type: XseType) -> XseResult<Version>;  // returns semver::Version
pub fn is_xse_installed(game_path: &Path, xse_type: XseType) -> bool;
pub fn get_xse_info(game_path: &Path, xse_type: XseType) -> XseInfo;
```

<!-- Existing game.rs XSE bridge surface (move to xse.rs, keep game.rs shims). -->

```rust
fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String;
fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool;
fn xse_type_from_str(s: &str) -> Result<XseType, String>;  // private helper
```

<!-- classic-version-registry-core surface (read directly to confirm method names). -->

Already-bridged in game.rs lines 14-161 (exact bodies are MOVED VERBATIM into version_registry.rs, with no namespace change in the function body):
```rust
fn version_registry_get_by_id(id: &str) -> VersionInfoDto;     // game.rs:14-38
fn version_registry_get_all_ids() -> Vec<String>;              // game.rs:40-43
fn version_registry_get_all_count() -> usize;                  // game.rs:45-48
fn version_registry_match_version(version_str: &str, game: &str, is_vr: bool) -> MatchResultDto;  // game.rs:50-77
fn version_registry_get_xse_config(id: &str) -> XseConfigDto;  // game.rs:79-99
fn version_registry_get_crashgen_configs(id: &str) -> Vec<CrashgenConfigDto>;  // game.rs:101-115
fn version_registry_get_crashgen_config(id: &str, crashgen_version: &str) -> CrashgenConfigDto;  // game.rs:117-140
fn parse_game_version(version_str: &str) -> GameVersionDto;    // game.rs:144-161
```

NEW for CXXS-06 (uses existing `registry.get_all()` iteration — confirmed available in classic-version-registry-core):
```rust
fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<VersionInfoDto>;
```

DTOs to MOVE from game.rs to version_registry.rs (preserved verbatim, same field names + types):
- `VersionInfoDto`, `XseConfigDto`, `CrashgenConfigDto`, `MatchResultDto`, `GameVersionDto`

NEW shared struct in xse.rs:
- `XseInfoDto { xse_type: String, path: String, version: String, installed: bool }` (flat — Pitfall 6 CLEAR)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create src/xse.rs with REAL signatures (Codex LOW correction) — XseType enum, XseInfoDto, typed methods, shimmed string helpers, tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs (READ ENTIRELY — confirm exact XseType variant names; confirm XseInfo field types (PathBuf, Option<semver::Version>); confirm detect_xse_version takes &Path and returns Version; confirm is_xse_installed takes &Path; confirm get_xse_info takes &Path; confirm XseType::from_game_id is INFALLIBLE; confirm dll_prefix has trailing underscore)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs lines 174-203 (current XSE wrapper bodies — copy and adjust for the typed enum surface)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template for module structure with #[cxx::bridge] block + #[cfg(test)] block)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 04" (Codex LOW corrections about real signatures)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-01 (xse.rs new file), D-04/D-07 (CXX shared enums), D-08 (keep shims), D-12 (Rust-side tests)
  </read_first>

  <behavior>
    - Test: `xse_get_loader_name(ffi::XseType::F4SE)` returns the literal string `"f4se_loader.exe"` (Codex correction — verified at classic-xse-core/src/lib.rs:169).
    - Test: `xse_get_loader_name(ffi::XseType::SKSE64)` returns `"skse64_loader.exe"`.
    - Test: `xse_get_dll_prefix(ffi::XseType::F4SE)` returns `"f4se_"` (with trailing underscore — verified at classic-xse-core/src/lib.rs:195).
    - Test: `xse_get_dll_prefix(ffi::XseType::SKSE64)` returns `"skse64_"`.
    - Test: `xse_get_type_from_game_id("Fallout4")` returns `"F4SE"` (XseType::from_game_id is INFALLIBLE for any GameId).
    - Test: `xse_get_type_from_game_id("Skyrim")` returns `"SKSE64"` (per classic-xse-core/src/lib.rs:147).
    - Test: `xse_get_type_from_game_id("Starfield")` returns `"SFSE"`.
    - Test: `xse_get_type_from_game_id("InvalidGame")` returns `""` (only the string-decoding step can fail; the core mapping is total).
    - Test: `is_xse_installed("nonexistent\\path", ffi::XseType::F4SE)` returns false (fail-soft).
    - Test: `xse_get_info("nonexistent\\path", ffi::XseType::F4SE)` returns XseInfoDto with `installed=false`, `version=""`, `path="nonexistent\\path"` (the input path is echoed back per XseInfo::new), `xse_type="F4SE"`.
    - Test: `detect_xse_version_string("", "F4SE")` returns "" (fail-soft preserves existing game.rs behavior).
    - Test: `is_xse_installed_check("", "F4SE")` returns false.
  </behavior>

  <action>
  Create `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs`:

  ```rust
  //! XSE bridge for CXX FFI (D-01, CXXS-09).
  //!
  //! Bridges `classic-xse-core` so C++ frontends can detect F4SE / SKSE / SFSE
  //! installations and resolve version strings without going through the
  //! string-based dispatch in `game.rs`.
  //!
  //! Per D-08, the existing string-form helpers (`detect_xse_version_string`,
  //! `is_xse_installed_check`) remain available here AND keep delegation shims
  //! in `game.rs` so existing C++ callers using `classic::game::*` continue
  //! to compile. New code should use `classic::xse::*`.

  use std::path::Path;
  use classic_constants_core::GameId;
  use classic_xse_core::{
      detect_xse_version as core_detect_xse_version,
      get_xse_info as core_get_xse_info,
      is_xse_installed as core_is_xse_installed,
      XseInfo as CoreXseInfo,
      XseType as CoreXseType,
  };

  // ─────────────────────────────────────────────────────────────────────
  // XseType bridge ↔ core mapping
  // ─────────────────────────────────────────────────────────────────────

  fn from_bridge_xse_type(t: ffi::XseType) -> CoreXseType {
      match t {
          ffi::XseType::F4SE => CoreXseType::F4SE,
          ffi::XseType::F4SEVR => CoreXseType::F4SEVR,
          ffi::XseType::SKSE => CoreXseType::SKSE,
          ffi::XseType::SKSE64 => CoreXseType::SKSE64,
          ffi::XseType::SKSEVR => CoreXseType::SKSEVR,
          ffi::XseType::SFSE => CoreXseType::SFSE,
          _ => CoreXseType::F4SE, // CXX may add sentinel variants; default to F4SE
      }
  }

  // Used by both the typed and string-form helpers.
  fn xse_type_from_str_internal(s: &str) -> Option<CoreXseType> {
      // Match the existing game.rs::xse_type_from_str logic — case-insensitive
      match s.to_uppercase().as_str() {
          "F4SE" => Some(CoreXseType::F4SE),
          "F4SEVR" => Some(CoreXseType::F4SEVR),
          "SKSE" => Some(CoreXseType::SKSE),
          "SKSE64" => Some(CoreXseType::SKSE64),
          "SKSEVR" => Some(CoreXseType::SKSEVR),
          "SFSE" => Some(CoreXseType::SFSE),
          _ => None,
      }
  }

  fn game_id_from_str(s: &str) -> Option<GameId> {
      match s {
          "Fallout4" => Some(GameId::Fallout4),
          "Fallout4VR" => Some(GameId::Fallout4VR),
          "Skyrim" => Some(GameId::Skyrim),
          "Starfield" => Some(GameId::Starfield),
          _ => None,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // Typed API (CXXS-09 widening — uses XseType shared enum)
  // ─────────────────────────────────────────────────────────────────────

  fn xse_get_loader_name(t: ffi::XseType) -> String {
      from_bridge_xse_type(t).loader_name().to_string()
  }

  fn xse_get_dll_prefix(t: ffi::XseType) -> String {
      // Codex LOW correction: returns the prefix WITH trailing underscore
      // (e.g., "f4se_") matching classic-xse-core/src/lib.rs:195.
      from_bridge_xse_type(t).dll_prefix().to_string()
  }

  fn xse_get_type_from_game_id(game_id_str: &str) -> String {
      // Codex LOW correction: from_game_id is INFALLIBLE (returns Self).
      // Only the string-decoding step can fail.
      let Some(game_id) = game_id_from_str(game_id_str) else {
          return String::new();
      };
      CoreXseType::from_game_id(game_id).as_str().to_string()
  }

  fn is_xse_installed(game_root: &str, t: ffi::XseType) -> bool {
      // Codex LOW correction: real signature takes &Path.
      if game_root.is_empty() {
          return false;
      }
      core_is_xse_installed(Path::new(game_root), from_bridge_xse_type(t))
  }

  fn detect_xse_version(exe_path: &str, t: ffi::XseType) -> String {
      // Codex LOW correction: real signature returns XseResult<semver::Version>.
      if exe_path.is_empty() {
          return String::new();
      }
      core_detect_xse_version(Path::new(exe_path), from_bridge_xse_type(t))
          .map(|v| v.to_string())
          .unwrap_or_default()
  }

  fn xse_get_info(game_path: &str, t: ffi::XseType) -> ffi::XseInfoDto {
      // Codex LOW correction: get_xse_info takes &Path; XseInfo.path is PathBuf,
      // version is Option<semver::Version>.
      let path_arg = if game_path.is_empty() {
          Path::new(".")
      } else {
          Path::new(game_path)
      };
      let info: CoreXseInfo = core_get_xse_info(path_arg, from_bridge_xse_type(t));
      ffi::XseInfoDto {
          xse_type: info.xse_type.as_str().to_string(),
          path: info.path.to_string_lossy().to_string(),
          version: info.version.map(|v| v.to_string()).unwrap_or_default(),
          installed: info.installed,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // String-form helpers (D-08 backward-compat, also called from game.rs shims)
  // ─────────────────────────────────────────────────────────────────────

  pub(crate) fn detect_xse_version_string_impl(exe_path: &str, xse_type_str: &str) -> String {
      let Some(xse_type) = xse_type_from_str_internal(xse_type_str) else {
          return String::new();
      };
      if exe_path.is_empty() {
          return String::new();
      }
      core_detect_xse_version(Path::new(exe_path), xse_type)
          .map(|v| v.to_string())
          .unwrap_or_default()
  }

  pub(crate) fn is_xse_installed_check_impl(game_root: &str, xse_type_str: &str) -> bool {
      let Some(xse_type) = xse_type_from_str_internal(xse_type_str) else {
          return false;
      };
      if game_root.is_empty() {
          return false;
      }
      core_is_xse_installed(Path::new(game_root), xse_type)
  }

  // Bridge fn aliases (the bridge block calls these names directly)
  fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String {
      detect_xse_version_string_impl(exe_path, xse_type_str)
  }
  fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool {
      is_xse_installed_check_impl(game_root, xse_type_str)
  }

  // ─────────────────────────────────────────────────────────────────────
  // CXX bridge block — D-04 shared enum + extern "Rust" fns
  // ─────────────────────────────────────────────────────────────────────

  #[cxx::bridge(namespace = "classic::xse")]
  mod ffi {
      #[repr(u8)]
      enum XseType {
          F4SE = 0,
          F4SEVR = 1,
          SKSE = 2,
          SKSE64 = 3,
          SKSEVR = 4,
          SFSE = 5,
      }

      struct XseInfoDto {
          xse_type: String,
          path: String,
          version: String,
          installed: bool,
      }

      extern "Rust" {
          // Typed API (CXXS-09 widening)
          fn xse_get_loader_name(t: XseType) -> String;
          fn xse_get_dll_prefix(t: XseType) -> String;
          fn xse_get_type_from_game_id(game_id_str: &str) -> String;
          fn is_xse_installed(game_root: &str, t: XseType) -> bool;
          fn detect_xse_version(exe_path: &str, t: XseType) -> String;
          fn xse_get_info(game_path: &str, t: XseType) -> XseInfoDto;

          // String-form D-08 backward-compat
          fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String;
          fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool;
      }
  }

  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn test_xse_get_loader_name_f4se_exact_string() {
          // Codex LOW correction: verified literal at classic-xse-core/src/lib.rs:169
          assert_eq!(xse_get_loader_name(ffi::XseType::F4SE), "f4se_loader.exe");
      }

      #[test]
      fn test_xse_get_loader_name_skse64_exact_string() {
          assert_eq!(xse_get_loader_name(ffi::XseType::SKSE64), "skse64_loader.exe");
      }

      #[test]
      fn test_xse_get_loader_name_all_variants_nonempty() {
          for t in [
              ffi::XseType::F4SE, ffi::XseType::F4SEVR,
              ffi::XseType::SKSE, ffi::XseType::SKSE64,
              ffi::XseType::SKSEVR, ffi::XseType::SFSE,
          ] {
              assert!(!xse_get_loader_name(t).is_empty());
              assert!(!xse_get_dll_prefix(t).is_empty());
          }
      }

      #[test]
      fn test_xse_get_dll_prefix_has_trailing_underscore() {
          // Codex LOW correction: dll_prefix returns "f4se_" / "skse64_" — with trailing underscore
          assert_eq!(xse_get_dll_prefix(ffi::XseType::F4SE), "f4se_");
          assert_eq!(xse_get_dll_prefix(ffi::XseType::SKSE64), "skse64_");
          assert_eq!(xse_get_dll_prefix(ffi::XseType::SFSE), "sfse_");
      }

      #[test]
      fn test_xse_get_type_from_game_id_total_mapping() {
          // Codex LOW correction: XseType::from_game_id is INFALLIBLE
          // Verified at classic-xse-core/src/lib.rs:143-150
          assert_eq!(xse_get_type_from_game_id("Fallout4"), "F4SE");
          assert_eq!(xse_get_type_from_game_id("Fallout4VR"), "F4SEVR");
          assert_eq!(xse_get_type_from_game_id("Skyrim"), "SKSE64");
          assert_eq!(xse_get_type_from_game_id("Starfield"), "SFSE");
      }

      #[test]
      fn test_xse_get_type_from_game_id_unknown_game_returns_empty() {
          // The only failure mode is the string-decoding step
          assert_eq!(xse_get_type_from_game_id("InvalidGame"), "");
      }

      #[test]
      fn test_is_xse_installed_nonexistent_returns_false() {
          assert!(!is_xse_installed("nonexistent\\path", ffi::XseType::F4SE));
      }

      #[test]
      fn test_is_xse_installed_empty_returns_false() {
          assert!(!is_xse_installed("", ffi::XseType::F4SE));
      }

      #[test]
      fn test_xse_get_info_nonexistent_returns_not_installed() {
          let info = xse_get_info("nonexistent\\path", ffi::XseType::F4SE);
          assert!(!info.installed);
          assert!(info.version.is_empty());
          assert_eq!(info.xse_type, "F4SE");
      }

      #[test]
      fn test_detect_xse_version_string_empty_returns_empty() {
          assert_eq!(detect_xse_version_string("", "F4SE"), "");
      }

      #[test]
      fn test_is_xse_installed_check_empty_returns_false() {
          assert!(!is_xse_installed_check("", "F4SE"));
      }

      #[test]
      fn test_xse_type_from_str_internal_known_and_unknown() {
          assert!(xse_type_from_str_internal("F4SE").is_some());
          assert!(xse_type_from_str_internal("f4se").is_some()); // case-insensitive
          assert!(xse_type_from_str_internal("SFSE").is_some());
          assert!(xse_type_from_str_internal("BOGUS").is_none());
      }
  }
  ```

  Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests` and confirm all 11+ tests pass.

  IMPORTANT: Add `classic-xse-core = { workspace = true }` and `classic-constants-core = { workspace = true }` to `classic-cpp-bridge/Cargo.toml` if not already present.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests</automated>
  </verify>

  <acceptance_criteria>
    - File `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` exists
    - `git grep -n 'namespace = "classic::xse"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns one match
    - `git grep -n 'enum XseType' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the bridge enum with 6 variants
    - `git grep -n 'struct XseInfoDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the shared struct
    - `git grep -n '"f4se_loader.exe"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the test assertion line (Codex LOW correction proof)
    - `git grep -n '"f4se_"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the dll_prefix test (trailing underscore proof)
    - `git grep -n 'core_is_xse_installed(Path::new' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns at least one match (proves &Path conversion at the bridge boundary)
    - `git grep -n 'todo!' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns NOTHING
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests` exits 0 with at least 11 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/xse.rs` exists with the full CXXS-09 surface using REAL classic-xse-core signatures (Codex LOW correction), has both typed and string-form helper APIs, all Rust-side tests pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create src/version_registry.rs (D-02, CXXS-06) — ZERO todo!() placeholders, all bodies CONCRETE per game.rs source</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs (confirm `registry.get_all() -> &[VersionInfo]`, `get_by_id`, `match_version`, `get_crashgen_versions`, `get_crashgen_for_version` method names)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs lines 14-161 (READ — these are the EXACT bodies that get copied verbatim into version_registry.rs; the only change is the namespace declaration in the bridge block)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template for #[cxx::bridge] block style)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 04" Codex MEDIUM concern about todo!() placeholders
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-02, D-08, D-12
  </read_first>

  <behavior>
    - Test: `version_registry_get_all_count()` returns >= 4 (the registry has at least Fallout4 OG/NG/AE/VR entries).
    - Test: `version_registry_get_by_id("DEFINITELY_NOT_REAL_VERSION_ID")` returns VersionInfoDto with `found: false`.
    - Test: `version_registry_get_all_for_game("Fallout4", false)` returns Vec with at least 1 entry, none with `is_vr: true`, all with `game == "Fallout4"`.
    - Test: `version_registry_get_all_for_game("Fallout4", true)` returns Vec where every entry has `is_vr: true`.
    - Test: `version_registry_get_all_ids()` returns a Vec containing at least 4 string IDs.
    - Test: `parse_game_version("1.10.163.0")` returns GameVersionDto with `valid: true`, major=1, minor=10, patch=163.
    - Test: `parse_game_version("garbage")` returns GameVersionDto with `valid: false`.
    - Test: `version_registry_match_version("1.10.163.0", "Fallout4", false)` returns MatchResultDto where `is_match` reflects whether the registry has a Fallout4 entry matching that version.
  </behavior>

  <action>
  Create `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs`. The implementation is a verbatim move from `game.rs` lines 14-161, with one new function added. The Codex MEDIUM correction requires ZERO `todo!()` placeholders — every wrapper body is concrete code.

  ```rust
  //! Version registry bridge for CXX FFI (D-02, CXXS-06).
  //!
  //! Bridges `classic-version-registry-core` so C++ frontends can resolve
  //! Fallout 4 OG/NG/AE/VR variants, XSE configs, crashgen configs, and version
  //! matching without going through the legacy `classic::game::version_registry_*`
  //! namespace. The legacy fns remain available as delegation shims in `game.rs`
  //! per D-08.
  //!
  //! NOTE: `src/registry.rs` is a SEPARATE bridge module for `classic-registry-core`
  //! (the typed key/value singleton) — it is NOT this file (D-02 wording).

  use classic_version_registry_core::{GameVersion, get_version_registry};

  // ─────────────────────────────────────────────────────────────────────
  // Wrapper bodies — verbatim from game.rs (Codex MEDIUM: NO todo!())
  // ─────────────────────────────────────────────────────────────────────

  fn version_registry_get_by_id(id: &str) -> ffi::VersionInfoDto {
      let registry = get_version_registry();
      match registry.get_by_id(id) {
          Some(info) => ffi::VersionInfoDto {
              id: info.id.clone(),
              version_string: info.version_string(),
              short_name: info.short_name.clone(),
              game: info.game.clone(),
              docs_name: info.docs_name.clone(),
              steam_id: info.steam_id,
              is_vr: info.is_vr,
              found: true,
          },
          None => ffi::VersionInfoDto {
              id: id.to_string(),
              version_string: String::new(),
              short_name: String::new(),
              game: String::new(),
              docs_name: String::new(),
              steam_id: 0,
              is_vr: false,
              found: false,
          },
      }
  }

  fn version_registry_get_all_ids() -> Vec<String> {
      let registry = get_version_registry();
      registry.get_all().iter().map(|v| v.id.clone()).collect()
  }

  fn version_registry_get_all_count() -> usize {
      let registry = get_version_registry();
      registry.get_all().len()
  }

  fn version_registry_match_version(
      version_str: &str,
      game: &str,
      is_vr: bool,
  ) -> ffi::MatchResultDto {
      let registry = get_version_registry();
      match GameVersion::parse(version_str) {
          Ok(detected) => {
              let result = registry.match_version(&detected, game, is_vr);
              let is_match = result.version_info.is_some();
              ffi::MatchResultDto {
                  matched_id: result
                      .version_info
                      .map(|v| v.id.clone())
                      .unwrap_or_default(),
                  confidence: format!("{:?}", result.confidence),
                  message: result.message.clone(),
                  is_match,
              }
          }
          Err(e) => ffi::MatchResultDto {
              matched_id: String::new(),
              confidence: "None".to_string(),
              message: format!("Failed to parse version: {e}"),
              is_match: false,
          },
      }
  }

  fn version_registry_get_xse_config(id: &str) -> ffi::XseConfigDto {
      let registry = get_version_registry();
      match registry.get_by_id(id).and_then(|info| info.xse.as_ref()) {
          Some(xse) => ffi::XseConfigDto {
              acronym: xse.acronym.clone(),
              full_name: xse.full_name.clone(),
              compatible_version: xse.compatible_version.clone(),
              loader: xse.loader.clone(),
              file_count: xse.file_count,
              found: true,
          },
          None => ffi::XseConfigDto {
              acronym: String::new(),
              full_name: String::new(),
              compatible_version: String::new(),
              loader: String::new(),
              file_count: 0,
              found: false,
          },
      }
  }

  fn version_registry_get_crashgen_configs(id: &str) -> Vec<ffi::CrashgenConfigDto> {
      let registry = get_version_registry();
      registry
          .get_crashgen_versions(id)
          .iter()
          .map(|c| ffi::CrashgenConfigDto {
              version: c.version.clone(),
              name: c.name.clone(),
              acronym: c.acronym.clone(),
              dll_file: c.dll_file.clone(),
              description: c.description.clone(),
              download_url: c.download_url.clone(),
          })
          .collect()
  }

  fn version_registry_get_crashgen_config(
      id: &str,
      crashgen_version: &str,
  ) -> ffi::CrashgenConfigDto {
      let registry = get_version_registry();
      match registry.get_crashgen_for_version(id, crashgen_version) {
          Some(c) => ffi::CrashgenConfigDto {
              version: c.version.clone(),
              name: c.name.clone(),
              acronym: c.acronym.clone(),
              dll_file: c.dll_file.clone(),
              description: c.description.clone(),
              download_url: c.download_url.clone(),
          },
          None => ffi::CrashgenConfigDto {
              version: String::new(),
              name: String::new(),
              acronym: String::new(),
              dll_file: String::new(),
              description: String::new(),
              download_url: String::new(),
          },
      }
  }

  fn parse_game_version(version_str: &str) -> ffi::GameVersionDto {
      match GameVersion::parse(version_str) {
          Ok(v) => ffi::GameVersionDto {
              major: v.major,
              minor: v.minor,
              patch: v.patch,
              build: v.build,
              valid: true,
          },
          Err(_) => ffi::GameVersionDto {
              major: 0,
              minor: 0,
              patch: 0,
              build: 0,
              valid: false,
          },
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // NEW for CXXS-06 — uses existing registry.get_all() iteration helper
  // (no missing core helper assumed — Codex review LOW correction)
  // ─────────────────────────────────────────────────────────────────────

  fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<ffi::VersionInfoDto> {
      let registry = get_version_registry();
      registry
          .get_all()
          .iter()
          .filter(|info| info.game == game && info.is_vr == is_vr)
          .map(|info| ffi::VersionInfoDto {
              id: info.id.clone(),
              version_string: info.version_string(),
              short_name: info.short_name.clone(),
              game: info.game.clone(),
              docs_name: info.docs_name.clone(),
              steam_id: info.steam_id,
              is_vr: info.is_vr,
              found: true,
          })
          .collect()
  }

  // ─────────────────────────────────────────────────────────────────────
  // CXX bridge block — moved DTOs + extern "Rust" declarations
  // ─────────────────────────────────────────────────────────────────────

  #[cxx::bridge(namespace = "classic::version_registry")]
  mod ffi {
      // Shared structs — copy verbatim from game.rs (same field names + types)
      struct VersionInfoDto {
          id: String,
          version_string: String,
          short_name: String,
          game: String,
          docs_name: String,
          steam_id: u32,
          is_vr: bool,
          found: bool,
      }

      struct XseConfigDto {
          acronym: String,
          full_name: String,
          compatible_version: String,
          loader: String,
          file_count: u32,
          found: bool,
      }

      struct CrashgenConfigDto {
          version: String,
          name: String,
          acronym: String,
          dll_file: String,
          description: String,
          download_url: String,
      }

      struct MatchResultDto {
          matched_id: String,
          confidence: String,
          message: String,
          is_match: bool,
      }

      struct GameVersionDto {
          major: u32,
          minor: u32,
          patch: u32,
          build: u32,
          valid: bool,
      }

      extern "Rust" {
          fn version_registry_get_by_id(id: &str) -> VersionInfoDto;
          fn version_registry_get_all_ids() -> Vec<String>;
          fn version_registry_get_all_count() -> usize;
          fn version_registry_match_version(version_str: &str, game: &str, is_vr: bool) -> MatchResultDto;
          fn version_registry_get_xse_config(id: &str) -> XseConfigDto;
          fn version_registry_get_crashgen_configs(id: &str) -> Vec<CrashgenConfigDto>;
          fn version_registry_get_crashgen_config(id: &str, crashgen_version: &str) -> CrashgenConfigDto;
          fn parse_game_version(version_str: &str) -> GameVersionDto;

          // NEW for CXXS-06
          fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<VersionInfoDto>;
      }
  }

  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn test_version_registry_get_all_count_at_least_four() {
          assert!(version_registry_get_all_count() >= 4);
      }

      #[test]
      fn test_version_registry_get_all_ids_nonempty() {
          let ids = version_registry_get_all_ids();
          assert!(!ids.is_empty());
      }

      #[test]
      fn test_version_registry_get_by_id_unknown_returns_not_found() {
          let result = version_registry_get_by_id("DEFINITELY_NOT_REAL_VERSION_ID");
          assert!(!result.found);
      }

      #[test]
      fn test_version_registry_get_all_for_game_fallout4_non_vr() {
          let entries = version_registry_get_all_for_game("Fallout4", false);
          assert!(!entries.is_empty(), "Fallout4 should have at least one non-VR variant");
          for entry in &entries {
              assert!(!entry.is_vr);
              assert_eq!(entry.game, "Fallout4");
          }
      }

      #[test]
      fn test_version_registry_get_all_for_game_fallout4_vr() {
          let entries = version_registry_get_all_for_game("Fallout4", true);
          for entry in &entries {
              assert!(entry.is_vr);
              assert_eq!(entry.game, "Fallout4");
          }
      }

      #[test]
      fn test_parse_game_version_valid() {
          let v = parse_game_version("1.10.163.0");
          assert!(v.valid);
          assert_eq!(v.major, 1);
          assert_eq!(v.minor, 10);
          assert_eq!(v.patch, 163);
      }

      #[test]
      fn test_parse_game_version_invalid() {
          assert!(!parse_game_version("garbage").valid);
      }
  }
  ```

  Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml version_registry::tests` and confirm all tests pass.

  IMPORTANT: Add `classic-version-registry-core = { workspace = true }` to `classic-cpp-bridge/Cargo.toml` if not already present.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml version_registry::tests</automated>
  </verify>

  <acceptance_criteria>
    - File `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` exists
    - `git grep -n 'namespace = "classic::version_registry"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns one match
    - `git grep -nE 'struct (VersionInfoDto|XseConfigDto|CrashgenConfigDto|MatchResultDto|GameVersionDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns at least 5 struct declarations
    - `git grep -n 'fn version_registry_get_all_for_game' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns the new CXXS-06 fn + extern declaration
    - `git grep -n 'todo!' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns NOTHING (Codex MEDIUM correction proof)
    - `git grep -n 'EXECUTOR:' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns NOTHING
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml version_registry::tests` exits 0 with at least 7 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/version_registry.rs` exists with the full CXXS-06 surface (existing fns moved + new `get_all_for_game` fn), ZERO todo!() placeholders, all DTOs moved verbatim, and all Rust-side tests pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update game.rs shims (D-08), wire both new files into build.rs + lib.rs, add D-11 consumer migration in pathdialog.cpp, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-gui/src/app/pathdialog.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (current state — KEEP all existing fn signatures + extern declarations to preserve D-08; the bodies stay UNCHANGED — both game.rs and the new modules call core directly, no cross-bridge-module calls)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (insert TWO new entries — `"src/xse.rs"` and `"src/version_registry.rs"` — near the existing `"src/game.rs"` line)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (add TWO new declarations — `pub mod xse;` and `pub mod version_registry;`)
    - classic-gui/src/app/pathdialog.cpp (find a suitable spot to add a `classic::xse::xse_get_loader_name` call — e.g., when displaying the "Looking for: f4se_loader.exe" label or in a tooltip; the goal is one production caller of the new namespace)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (keep shims), D-09, D-10
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 04" Codex MEDIUM concern about D-11
  </read_first>

  <action>
  ## Part A — game.rs shims (D-08 backward compat)

  No body changes needed in `game.rs`. Both the existing `game.rs` wrappers AND the new `version_registry.rs` / `xse.rs` wrappers call `classic_version_registry_core::*` and `classic_xse_core::*` directly. The duplication is intentional per D-08 — game.rs entries stay in the parity baseline, and new entries appear in the new bridgeModules.

  Verify by running `git diff ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` after the plan — there should be NO changes (or only formatting normalization).

  ## Part B — Add both files to build.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`. Insert `"src/xse.rs",` and `"src/version_registry.rs",` into the `cxx_build::bridges([...])` array. Place them AFTER `"src/game.rs"` so generated headers for the dependent module land in the expected order.

  ## Part C — Add both modules to lib.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`. Add under `#[cfg(windows)]` (alphabetically):

  ```rust
  #[cfg(windows)]
  pub mod version_registry;
  #[cfg(windows)]
  pub mod xse;
  ```

  ## Part D — D-11 consumer migration in pathdialog.cpp (Codex review correction)

  Edit `classic-gui/src/app/pathdialog.cpp`. Add `#include "classic_cxx_bridge/xse.h"` near the existing CXX bridge header includes.

  Find a location in the dialog where it makes sense to display the expected XSE loader filename (e.g., near the game-path validation, or in a help tooltip). Add a call like:

  ```cpp
  #include "classic_cxx_bridge/xse.h"

  // ... inside an appropriate dialog method (e.g., setupUi or validation):
  // D-11 / CXXS-09 consumer migration — display the expected loader name
  // by calling the new typed XSE API.
  auto loader_rust = classic::xse::xse_get_loader_name(classic::xse::XseType::F4SE);
  QString loader_name = QString::fromUtf8(loader_rust.data(), static_cast<int>(loader_rust.size()));
  // Then use `loader_name` in a label or tooltip — for example:
  // m_xseHelpLabel->setToolTip(QStringLiteral("Looking for: %1").arg(loader_name));
  ```

  The exact integration point depends on the dialog's existing UI structure. The minimum is: include the header, call one `classic::xse::*` fn, and use the result in the dialog's state somewhere (label, tooltip, or QString member). The build proof comes from the file compiling and linking.

  Run `git grep -n 'classic::xse' classic-gui/src/app/pathdialog.cpp` and confirm at least one match.

  ## Part E — Mandatory D-10 clean-build pair

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. Confirm both generated headers exist:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/xse.h
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/version_registry.h
  ```

  ## Part F — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part G — Atomic commit

  Stage all 9 files (2 new bridge modules + game.rs unchanged + build.rs + lib.rs + pathdialog.cpp + 4 baseline artifacts).
  Commit message: `Feat(02-04): split XSE and version registry into dedicated CXX bridge modules` — body mentions CXXS-06, CXXS-09, D-01, D-02, D-08, D-09, D-10, D-11 and the pathdialog.cpp consumer migration.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/xse.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line
    - `git grep -n '"src/version_registry.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line
    - `git grep -n 'pub mod xse' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `git grep -n 'pub mod version_registry' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `git grep -n 'fn detect_xse_version_string' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved)
    - `git grep -n 'fn version_registry_get_by_id' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved)
    - `git grep -n 'classic::xse' classic-gui/src/app/pathdialog.cpp` returns at least one line (D-11 consumer)
    - `git grep -n '#include "classic_cxx_bridge/xse.h"' classic-gui/src/app/pathdialog.cpp` returns the new include
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/xse.h` exists
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/version_registry.h` exists
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "xse"` and `bridgeModule: "version_registry"` AND no REMOVED rows from `bridgeModule: "game"` (D-08 backward compat preserved)
    - `git log -1 --stat` shows the commit touches Rust source AND pathdialog.cpp AND `docs/implementation/cxx_api_parity/baseline/*` together
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` is UNCHANGED (`git diff HEAD~1 ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` shows no changes — D-02 untouched)
  </acceptance_criteria>

  <done>
    Plan 02-04 complete — `classic::xse` and `classic::version_registry` are first-class CXX bridge modules with full surfaces, ZERO todo!() placeholders, real source signatures (Codex LOW correction), pathdialog.cpp exercises the new XSE namespace (Codex MEDIUM correction), `game.rs` shims preserve backward compatibility, both clean builds pass, and the parity gate has 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests version_registry::tests` — exits 0
2. Both clean MSVC builds exit 0
3. Parity gate at 0 drift
4. `git diff HEAD~1 ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` is empty (D-02 — registry.rs untouched)
5. game.rs still exposes detect_xse_version_string, is_xse_installed_check, version_registry_*, parse_game_version (D-08 shims)
6. ZERO todo!() in version_registry.rs (Codex MEDIUM correction)
7. xse.rs uses real classic-xse-core signatures (&Path, semver::Version, total from_game_id) (Codex LOW correction)
8. pathdialog.cpp has classic::xse::* call (Codex MEDIUM correction)

Validation Architecture (per 02-VALIDATION.md row 2-04-01): `cargo test -p classic-cpp-bridge xse::tests version_registry::tests` + clean-build pair + parity gate.
</verification>

<success_criteria>
- src/xse.rs exists with #[cxx::bridge(namespace = "classic::xse")] using REAL classic-xse-core signatures (Codex LOW correction)
- src/version_registry.rs exists with #[cxx::bridge(namespace = "classic::version_registry")] and ZERO todo!() placeholders (Codex MEDIUM correction)
- xse.rs tests assert exact strings: "f4se_loader.exe", "f4se_" (with trailing underscore)
- xse_get_type_from_game_id is total (returns "F4SE" for Fallout4, "SKSE64" for Skyrim, etc.)
- pathdialog.cpp has D-11 consumer migration (Codex MEDIUM correction)
- game.rs preserves all D-08 shim entries (no removals from the parity baseline)
- src/registry.rs is UNCHANGED (D-02 — registry namespace = classic-registry-core KV singleton)
- Both clean MSVC builds are green (D-10)
- Parity gate at 0 drift after --update-baseline (D-09)
- All changes committed atomically
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-04-SUMMARY.md` documenting:
- Confirmation that ZERO todo!() placeholders remain in version_registry.rs (Codex MEDIUM correction)
- Confirmation that xse.rs uses real signatures: &Path-taking is_xse_installed/detect_xse_version, total from_game_id, "f4se_" trailing-underscore dll_prefix (Codex LOW correction)
- Confirmation that pathdialog.cpp has classic::xse::* consumer migration (Codex MEDIUM correction)
- Number of fns moved into xse.rs (count from cxx_diff_report.md)
- Number of fns moved into version_registry.rs (count from cxx_diff_report.md)
- The single new fn added: version_registry_get_all_for_game
- Confirmation that the parity baseline shows ADDED rows in both new modules and ZERO removed rows from game.rs (D-08 verified)
- Confirmation that registry.rs is untouched (D-02 verified)
</output>
