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
    - "src/version_registry.rs exists, contains #[cxx::bridge(namespace = \"classic::version_registry\")], and exposes the full version registry surface including the new version_registry_get_all_for_game fn (CXXS-06 widening)"
    - "Both new files are listed in build.rs::cxx_build::bridges and lib.rs declares pub mod xse + pub mod version_registry"
    - "src/game.rs keeps shims for the moved fns (D-08 backward compat — pathdialog.cpp etc. continue to compile against game.h)"
    - "src/registry.rs is UNCHANGED (D-02 — registry namespace continues to mean classic-registry-core KV singleton)"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10 — TWO new build.rs entries in one plan = ONE mandatory clean-build pair)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs"
      provides: "New CXX bridge module exposing classic-xse-core (CXXS-09, D-01)"
      min_lines: 150
      contains: "namespace = \"classic::xse\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs"
      provides: "New CXX bridge module exposing classic-version-registry-core full surface (CXXS-06, D-02)"
      min_lines: 200
      contains: "namespace = \"classic::version_registry\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs"
      provides: "Compatibility shims preserved — XSE, version registry, parse_game_version helpers still compile from classic::game namespace (D-08)"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array contains \"src/xse.rs\" AND \"src/version_registry.rs\""
      contains: "src/xse.rs"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs"
      to: "classic-xse-core (XseType, XseInfo, detect_xse_version, is_xse_installed, get_xse_info)"
      via: "use classic_xse_core::{...}"
      pattern: "use classic_xse_core"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs"
      to: "classic-version-registry-core (VersionRegistry::get_all_for_game and existing get_by_id / match_version / get_xse_config / get_crashgen_configs)"
      via: "use classic_version_registry_core::{...}"
      pattern: "use classic_version_registry_core"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs"
      to: "src/xse.rs and src/version_registry.rs (delegation shims)"
      via: "crate::xse::* / crate::version_registry::* function calls"
      pattern: "crate::(xse|version_registry)::"
---

<objective>
Split XSE helpers and version-registry helpers out of `src/game.rs` into TWO new bridge modules: `src/xse.rs` (D-01, CXXS-09) and `src/version_registry.rs` (D-02, CXXS-06). Per D-08, leave delegation shims in `game.rs` so existing C++ callers (like `pathdialog.cpp` for `classic::game::*`) continue to compile. Add the new `XseType` shared enum (D-04/D-07) plus the typed XSE methods. Add the missing `version_registry_get_all_for_game(game, is_vr)` fn (the only true CXXS-06 gap; the rest of the surface already exists in `game.rs`). Both new files land in ONE plan to share a single mandatory D-10 clean-build pair.

Purpose: D-01 and D-02 both move logic out of `game.rs`. Doing them in one plan minimizes the number of mandatory clean-build cycles (one cycle covers two new bridge files). Per RESEARCH.md §"game.rs Split Compatibility", the shim approach prevents baseline-removal noise from `game.rs` while the additions land in the new files. CXXS-06 widens the version-registry surface; CXXS-09 widens the XSE surface.

Output: Two new bridge modules with full surfaces; `game.rs` shims preserved; `registry.rs` untouched (D-02); both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source-of-truth Rust crates
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

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-xse-core surface (per RESEARCH.md §"classic-xse-core"). -->

```rust
pub enum XseType { F4SE, F4SEVR, SKSE, SKSE64, SKSEVR, SFSE }
impl XseType {
    pub fn loader_name(&self) -> &'static str;
    pub fn dll_prefix(&self) -> &'static str;
    pub fn from_game_id(game_id: GameId) -> Option<XseType>;
    pub fn as_str(&self) -> &'static str;
}

pub struct XseInfo {
    pub xse_type: XseType,
    pub path: String,
    pub version: Option<String>,
    pub installed: bool,
}

pub fn detect_xse_version(exe_path: &str, xse_type: XseType) -> Option<String>;
pub fn is_xse_installed(game_root: &str, xse_type: XseType) -> bool;
pub fn get_xse_info(game_path: &str, xse_type: XseType) -> XseInfo;
```

<!-- Existing game.rs XSE surface (move to xse.rs, keep game.rs shims). -->

```rust
fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String;
fn is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool;
fn xse_type_from_str(s: &str) -> Result<XseType, String>;  // private helper
```

<!-- classic-version-registry-core surface (per RESEARCH.md §"classic-version-registry-core"). -->

Already-bridged in game.rs (move verbatim to version_registry.rs):
```rust
fn version_registry_get_by_id(id: &str) -> VersionInfoDto;
fn version_registry_get_all_ids() -> Vec<String>;
fn version_registry_get_all_count() -> usize;
fn version_registry_match_version(version_str: &str, game: &str, is_vr: bool) -> MatchResultDto;
fn version_registry_get_xse_config(id: &str) -> XseConfigDto;
fn version_registry_get_crashgen_configs(id: &str) -> Vec<CrashgenConfigDto>;
fn version_registry_get_crashgen_config(id: &str, crashgen_version: &str) -> CrashgenConfigDto;
fn parse_game_version(version_str: &str) -> GameVersionDto;
```

NEW for CXXS-06 (only true gap per RESEARCH.md):
```rust
fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<VersionInfoDto>;
```

DTOs to MOVE from game.rs to version_registry.rs (preserved verbatim):
- `VersionInfoDto { id, version_string, short_name, game, docs_name, steam_id: u32, is_vr, found }`
- `XseConfigDto { acronym, full_name, compatible_version, loader, file_count: u32, found }`
- `CrashgenConfigDto { version, name, acronym, dll_file, description, download_url }`
- `MatchResultDto { matched_id, confidence, message, is_match }`
- `GameVersionDto { major, minor, patch, build: u32 each, valid }`

NEW shared struct in xse.rs:
- `XseInfoDto { xse_type: String, path: String, version: String, installed: bool }` (flat — Pitfall 6 CLEAR)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create src/xse.rs (D-01, CXXS-09) — XseType enum, XseInfoDto, typed methods, shimmed string helpers, tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs (READ ENTIRELY — confirm exact XseType variant names; confirm XseInfo field names; confirm detect_xse_version / is_xse_installed / get_xse_info signatures)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (current XSE bridge fns — `detect_xse_version_string`, `is_xse_installed_check`, `xse_type_from_str` — copy their bodies into xse.rs as the implementation source for the shim'd string-form fns)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template for module structure with #[cxx::bridge] block + #[cfg(test)] block)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-xse-core" §"D-11 Consumer Migration Enumeration" (xse.rs has no required D-11 migration site — XSE detection is currently handled via game.rs string helpers and there are no qualifying narrowed call sites in classic-cli/classic-gui per the research enumeration)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-01 (xse.rs new file), D-04/D-07 (CXX shared enums), D-08 (keep shims), D-12 (Rust-side tests)
  </read_first>

  <behavior>
    - Test: `xse_get_loader_name(ffi::XseType::F4SE)` returns "f4se_loader.exe" (confirm exact value via direct read of XseType::loader_name()).
    - Test: `xse_get_loader_name(ffi::XseType::SKSE64)` returns "skse64_loader.exe" or whatever core defines.
    - Test: `xse_get_dll_prefix(ffi::XseType::F4SE)` returns "f4se" (or whatever core defines).
    - Test: `xse_get_type_from_game_id("Fallout4")` returns "F4SE" (string form of the resolved XseType).
    - Test: `xse_get_type_from_game_id("InvalidGame")` returns "" (fail-soft).
    - Test: `is_xse_installed(nonexistent path, ffi::XseType::F4SE)` returns false (fail-soft).
    - Test: `xse_get_info(nonexistent path, ffi::XseType::F4SE)` returns XseInfoDto with installed=false, version="".
    - Test: `detect_xse_version_string("", "F4SE")` returns "" (fail-soft preserves existing game.rs behavior).
    - Test: `is_xse_installed_check("", "F4SE")` returns false (fail-soft preserves existing game.rs behavior).
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
          _ => CoreXseType::F4SE,
      }
  }

  fn xse_type_from_str(s: &str) -> Result<CoreXseType, String> {
      match s {
          "F4SE" => Ok(CoreXseType::F4SE),
          "F4SEVR" => Ok(CoreXseType::F4SEVR),
          "SKSE" => Ok(CoreXseType::SKSE),
          "SKSE64" => Ok(CoreXseType::SKSE64),
          "SKSEVR" => Ok(CoreXseType::SKSEVR),
          "SFSE" => Ok(CoreXseType::SFSE),
          other => Err(format!("unknown XSE type: {}", other)),
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
      from_bridge_xse_type(t).dll_prefix().to_string()
  }

  fn xse_get_type_from_game_id(game_id_str: &str) -> String {
      let Some(game_id) = game_id_from_str(game_id_str) else {
          return String::new();
      };
      CoreXseType::from_game_id(game_id)
          .map(|t| t.as_str().to_string())
          .unwrap_or_default()
  }

  fn is_xse_installed(game_root: &str, t: ffi::XseType) -> bool {
      core_is_xse_installed(game_root, from_bridge_xse_type(t))
  }

  fn detect_xse_version(exe_path: &str, t: ffi::XseType) -> String {
      core_detect_xse_version(exe_path, from_bridge_xse_type(t)).unwrap_or_default()
  }

  fn xse_get_info(game_path: &str, t: ffi::XseType) -> ffi::XseInfoDto {
      let info: CoreXseInfo = core_get_xse_info(game_path, from_bridge_xse_type(t));
      ffi::XseInfoDto {
          xse_type: info.xse_type.as_str().to_string(),
          path: info.path,
          version: info.version.unwrap_or_default(),
          installed: info.installed,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // String-form helpers (D-08 backward-compat, also called from game.rs shims)
  // ─────────────────────────────────────────────────────────────────────

  pub(crate) fn detect_xse_version_string_impl(exe_path: &str, xse_type_str: &str) -> String {
      let Ok(xse_type) = xse_type_from_str(xse_type_str) else { return String::new() };
      core_detect_xse_version(exe_path, xse_type).unwrap_or_default()
  }

  pub(crate) fn is_xse_installed_check_impl(game_root: &str, xse_type_str: &str) -> bool {
      let Ok(xse_type) = xse_type_from_str(xse_type_str) else { return false };
      core_is_xse_installed(game_root, xse_type)
  }

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
      fn test_xse_get_loader_name_f4se() {
          let name = xse_get_loader_name(ffi::XseType::F4SE);
          assert!(!name.is_empty());
          assert!(name.contains("f4se"));
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
      fn test_xse_get_type_from_game_id_fallout4() {
          let result = xse_get_type_from_game_id("Fallout4");
          assert!(!result.is_empty());
      }

      #[test]
      fn test_xse_get_type_from_game_id_unknown_returns_empty() {
          assert_eq!(xse_get_type_from_game_id("InvalidGame"), "");
      }

      #[test]
      fn test_is_xse_installed_nonexistent_returns_false() {
          assert!(!is_xse_installed("nonexistent\\path", ffi::XseType::F4SE));
      }

      #[test]
      fn test_xse_get_info_nonexistent_returns_not_installed() {
          let info = xse_get_info("nonexistent\\path", ffi::XseType::F4SE);
          assert!(!info.installed);
          assert!(info.version.is_empty());
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
      fn test_xse_type_from_str_known_and_unknown() {
          assert!(xse_type_from_str("F4SE").is_ok());
          assert!(xse_type_from_str("SFSE").is_ok());
          assert!(xse_type_from_str("BOGUS").is_err());
      }
  }
  ```

  Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests` and confirm all 9+ tests pass.

  IMPORTANT: Add `classic-xse-core = { workspace = true }` to `classic-cpp-bridge/Cargo.toml` if not already present.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests</automated>
  </verify>

  <acceptance_criteria>
    - File `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` exists
    - `git grep -n 'namespace = "classic::xse"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns one match
    - `git grep -n 'enum XseType' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the bridge enum with 6 variants
    - `git grep -n 'struct XseInfoDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns the shared struct
    - `git grep -nE 'fn (xse_get_loader_name|xse_get_dll_prefix|xse_get_type_from_game_id|is_xse_installed|detect_xse_version|xse_get_info|detect_xse_version_string|is_xse_installed_check)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` returns at least 8 wrapper definitions PLUS extern declarations
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests` exits 0 with at least 9 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/xse.rs` exists with the full CXXS-09 surface, has both typed and string-form helper APIs, and all Rust-side tests pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create src/version_registry.rs (D-02, CXXS-06) + add CXXS-06 missing fn + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs (confirm VersionRegistry::get_all_for_game(game, is_vr_filter) signature; confirm VersionInfo field names that the existing DTO mirrors)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (READ the version_registry_* fns, the parse_game_version fn, AND the VersionInfoDto / XseConfigDto / CrashgenConfigDto / MatchResultDto / GameVersionDto shared struct definitions — these all MOVE verbatim into version_registry.rs)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template for #[cxx::bridge] block style)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-version-registry-core" §"D-11 Consumer Migration Enumeration"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-02 (version_registry.rs new file; src/registry.rs UNCHANGED), D-08 (keep shims in game.rs), D-12 (Rust tests)
  </read_first>

  <behavior>
    - Test: `version_registry_get_all_count()` returns >= 4 (the registry has at least Fallout4 OG/NG/AE/VR entries).
    - Test: `version_registry_get_by_id("FO4_OG")` (or whatever the canonical Original ID is) returns VersionInfoDto with `found: true` and a non-empty `version_string`.
    - Test: `version_registry_get_by_id("DEFINITELY_NOT_REAL")` returns VersionInfoDto with `found: false`.
    - Test: `version_registry_get_all_for_game("Fallout4", false)` returns Vec with at least 1 entry, none with `is_vr: true`.
    - Test: `version_registry_get_all_for_game("Fallout4", true)` returns Vec where every entry has `is_vr: true` (likely 1 entry — the VR variant).
    - Test: `version_registry_get_all_ids()` returns a Vec containing at least 4 string IDs.
    - Test: `parse_game_version("1.10.163.0")` returns GameVersionDto with `valid: true`, major=1, minor=10, patch=163, build=0.
    - Test: `parse_game_version("garbage")` returns GameVersionDto with `valid: false`.
    - Test: `version_registry_get_xse_config("FO4_OG")` returns XseConfigDto with `found: true`, non-empty `acronym`.
    - Test: `version_registry_get_crashgen_configs("FO4_OG")` returns at least one CrashgenConfigDto.
    - Test: `version_registry_match_version("1.10.163.0", "Fallout4", false)` returns MatchResultDto with `is_match: true`.
  </behavior>

  <action>
  Create `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs`. The implementation is largely a verbatim move from `game.rs`, with one new function added. COPY the wrapper fn bodies, the shared struct definitions, and the DTO mappings from `game.rs::version_registry_*` and `game.rs::parse_game_version` into the new file. Adjust the `#[cxx::bridge]` namespace.

  Module skeleton:

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

  use classic_version_registry_core::{
      get_version_registry,
      VersionInfo as CoreVersionInfo,
      // ... other re-exports as needed
  };

  // ─────────────────────────────────────────────────────────────────────
  // DTO mappings (moved verbatim from game.rs — keep field names identical
  // so the parity gate sees this as a MOVE not a CHANGE)
  // ─────────────────────────────────────────────────────────────────────

  fn map_version_info(info: Option<&CoreVersionInfo>) -> ffi::VersionInfoDto {
      match info {
          Some(i) => ffi::VersionInfoDto {
              id: i.id.clone(),
              version_string: i.version_string.clone(),
              short_name: i.short_name.clone(),
              game: i.game.clone(),
              docs_name: i.docs_name.clone(),
              steam_id: i.steam_id,
              is_vr: i.is_vr,
              found: true,
          },
          None => ffi::VersionInfoDto {
              id: String::new(),
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

  // (Move from game.rs — keep the same wrapper logic for XseConfigDto, CrashgenConfigDto,
  //  MatchResultDto, GameVersionDto. The executor reads game.rs and copies them verbatim.)

  // ─────────────────────────────────────────────────────────────────────
  // Existing fns moved from game.rs
  // ─────────────────────────────────────────────────────────────────────

  fn version_registry_get_by_id(id: &str) -> ffi::VersionInfoDto {
      let registry = get_version_registry();
      map_version_info(registry.get_by_id(id))
  }

  fn version_registry_get_all_ids() -> Vec<String> {
      get_version_registry().get_all_ids().into_iter().collect()
  }

  fn version_registry_get_all_count() -> usize {
      get_version_registry().get_all_ids().len()
  }

  fn version_registry_match_version(version_str: &str, game: &str, is_vr: bool) -> ffi::MatchResultDto {
      // Copy body from game.rs::version_registry_match_version
      // (executor reads game.rs and pastes the exact body, replacing only the namespace import)
      todo!("EXECUTOR: copy body verbatim from game.rs::version_registry_match_version")
  }

  fn version_registry_get_xse_config(id: &str) -> ffi::XseConfigDto {
      todo!("EXECUTOR: copy body verbatim from game.rs::version_registry_get_xse_config")
  }

  fn version_registry_get_crashgen_configs(id: &str) -> Vec<ffi::CrashgenConfigDto> {
      todo!("EXECUTOR: copy body verbatim from game.rs::version_registry_get_crashgen_configs")
  }

  fn version_registry_get_crashgen_config(id: &str, crashgen_version: &str) -> ffi::CrashgenConfigDto {
      todo!("EXECUTOR: copy body verbatim from game.rs::version_registry_get_crashgen_config")
  }

  fn parse_game_version(version_str: &str) -> ffi::GameVersionDto {
      todo!("EXECUTOR: copy body verbatim from game.rs::parse_game_version")
  }

  // ─────────────────────────────────────────────────────────────────────
  // NEW for CXXS-06 — fills the only true gap per RESEARCH.md
  // ─────────────────────────────────────────────────────────────────────

  fn version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<ffi::VersionInfoDto> {
      let registry = get_version_registry();
      // Filter all entries by game name and is_vr flag.
      // Use registry.get_all_for_game(game, Some(is_vr)) if it exists, otherwise
      // iterate get_all_ids and filter manually.
      registry
          .get_all_ids()
          .iter()
          .filter_map(|id| registry.get_by_id(id))
          .filter(|info| info.game == game && info.is_vr == is_vr)
          .map(|info| map_version_info(Some(info)))
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
          // VR variant should exist
          for entry in &entries {
              assert!(entry.is_vr);
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

  IMPORTANT: The `todo!()` markers above are PLACEHOLDERS — the executor MUST read `game.rs` and copy the exact bodies verbatim into the new file. Do not commit `todo!()` calls. The DTO mappings (`map_version_info` etc.) and the wrapper logic for `version_registry_match_version`, `version_registry_get_xse_config`, `version_registry_get_crashgen_configs`, `version_registry_get_crashgen_config`, `parse_game_version` already exist in `game.rs` — copy them.

  After copy, run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml version_registry::tests` and confirm all tests pass.

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
    - `git grep -n 'todo!' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` returns NOTHING (no leftover placeholders)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml version_registry::tests` exits 0 with at least 7 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/version_registry.rs` exists with the full CXXS-06 surface (existing fns moved + new `get_all_for_game` fn), all DTOs moved verbatim, and all Rust-side tests pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update game.rs shims (D-08), wire both new files into build.rs + lib.rs, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (current state — KEEP all existing fn signatures + extern declarations to preserve D-08; only the BODIES change to delegate to crate::xse and crate::version_registry where applicable)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (insert TWO new entries — `"src/xse.rs"` and `"src/version_registry.rs"` — near the existing `"src/game.rs"` line)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (add TWO new declarations — `pub mod xse;` and `pub mod version_registry;`)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (keep shims), D-09, D-10
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"Pattern: Split Migration (game.rs shim)" §"Baseline Refresh Cadence (D-09)" §"game.rs Split Compatibility"
  </read_first>

  <action>
  ## Part A — Update game.rs to delegate to crate::xse and crate::version_registry

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs`. DO NOT change any function signatures, struct definitions, or `extern "Rust"` declarations inside the existing `#[cxx::bridge(namespace = "classic::game")]` block. ONLY rewrite the bodies of these fns to call into the new modules:

  - `detect_xse_version_string(exe_path, xse_type_str)` → call `crate::xse::detect_xse_version_string_impl(exe_path, xse_type_str)`
  - `is_xse_installed_check(game_root, xse_type_str)` → call `crate::xse::is_xse_installed_check_impl(game_root, xse_type_str)`
  - `version_registry_get_by_id(id)` → call `crate::version_registry::ffi::*` is NOT possible across bridge modules, so instead delegate at the implementation level: import `classic_version_registry_core::get_version_registry` directly and reuse the same DTO mapping logic. Simplest: keep the existing body unchanged in game.rs (don't try to call across bridge modules — just keep two implementations sharing the same core crate). The D-09 baseline will reflect that the SAME entries exist in both `game` and `version_registry` bridgeModules — that's expected and correct (D-08 dual exposure).
  - Same applies to `version_registry_*` and `parse_game_version` — leave the bodies as-is (they call core directly), and the new `version_registry.rs` file calls the core via its own copies. No cross-bridge-module calls.

  Result: `game.rs` source is essentially UNCHANGED except for two single-line body rewrites in `detect_xse_version_string` and `is_xse_installed_check` (these can be private helpers shared via `pub(crate)` in xse.rs).

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

  ## Part D — Mandatory D-10 clean-build pair (TWO new files = ONE clean cycle)

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. Confirm both generated headers exist:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/xse.h
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/version_registry.h
  ```

  ## Part E — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part F — Atomic commit

  Stage all 9 files (2 new bridge modules + 1 modified game.rs + build.rs + lib.rs + 4 baseline artifacts).
  Commit message: `Feat(02-04): split XSE and version registry into dedicated CXX bridge modules` — body mentions CXXS-06, CXXS-09, D-01, D-02, D-08, D-09, D-10.
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
    - `git grep -n 'fn version_registry_get_by_id' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` STILL returns a definition (D-08 shim preserved — still bridged in classic::game namespace)
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/xse.h` exists
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/version_registry.h` exists
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "xse"` and `bridgeModule: "version_registry"` AND no REMOVED rows from `bridgeModule: "game"` (D-08 backward compat preserved)
    - `git log -1 --stat` shows the commit touches Rust source AND `docs/implementation/cxx_api_parity/baseline/*` together
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` is UNCHANGED (`git diff HEAD~1 ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` shows no changes — D-02 untouched)
  </acceptance_criteria>

  <done>
    Plan 02-04 complete — `classic::xse` and `classic::version_registry` are first-class CXX bridge modules with full surfaces, `game.rs` shims preserve backward compatibility, both clean builds pass, and the parity gate has 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml xse::tests version_registry::tests` — exits 0
2. Both clean MSVC builds exit 0
3. Parity gate at 0 drift
4. `git diff HEAD~1 ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` is empty (D-02 — registry.rs untouched)
5. game.rs still exposes detect_xse_version_string, is_xse_installed_check, version_registry_*, parse_game_version (D-08 shims)

Validation Architecture (per 02-VALIDATION.md row 2-04-01): `cargo test -p classic-cpp-bridge xse::tests version_registry::tests` + clean-build pair + parity gate.

D-11 consumer migration: Per RESEARCH.md §"D-11 Consumer Migration Enumeration", neither classic-cli nor classic-gui currently has a hand-rolled XSE or version-registry call site that would qualify as a narrowed-bridge migration target. The existing C++ callers of `classic::game::version_registry_*` and `classic::game::detect_xse_version_string` continue to work via the D-08 shims in game.rs. CXXS-09 and CXXS-06 are satisfied by the new bridge surfaces being available; consumers can migrate at their own pace in subsequent work.
</verification>

<success_criteria>
- src/xse.rs exists with #[cxx::bridge(namespace = "classic::xse")] exposing the full CXXS-09 surface
- src/version_registry.rs exists with #[cxx::bridge(namespace = "classic::version_registry")] exposing the full CXXS-06 surface (including the new version_registry_get_all_for_game fn)
- game.rs preserves all D-08 shim entries (no removals from the parity baseline)
- src/registry.rs is UNCHANGED (D-02 — registry namespace = classic-registry-core KV singleton, NOT version registry)
- Both clean MSVC builds are green (D-10 — TWO new build.rs entries share ONE clean cycle)
- Parity gate at 0 drift after --update-baseline (D-09)
- All changes committed atomically
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-04-SUMMARY.md` documenting:
- Number of fns moved into xse.rs (count from cxx_diff_report.md)
- Number of fns moved into version_registry.rs (count from cxx_diff_report.md)
- The single new fn added: version_registry_get_all_for_game
- Confirmation that the parity baseline shows ADDED rows in both new modules and ZERO removed rows from game.rs (D-08 verified)
- Confirmation that registry.rs is untouched (D-02 verified)
- D-10 clean-build outcome
</output>