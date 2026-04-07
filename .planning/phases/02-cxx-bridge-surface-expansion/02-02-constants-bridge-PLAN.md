---
phase: 02-cxx-bridge-surface-expansion
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
  - classic-gui/src/app/mainwindow.cpp
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-01
  - CXXS-10
must_haves:
  truths:
    - "src/constants.rs exists and contains a #[cxx::bridge(namespace = \"classic::constants\")] block"
    - "GameId, Fallout4Version, and YamlFile are exposed as CXX shared enums (D-04) with the COMPLETE variant set from classic-constants-core (verified by direct read)"
    - "YamlFile bridge enum has all 7 variants: Main, Settings, Ignore, Game, GameLocal, Test, Cache (Codex review correction)"
    - "Fallout4Version bridge enum maps Vr to as_str()=\"VR\" (Codex review LOW correction — there is a tested case asserting this exact mapping)"
    - "must_not_be_none, settings_ignore_none_contains, is_null_version, game_id_as_str, yaml_file_as_str, fallout4_version_as_str helper fns are bridged"
    - "src/constants.rs is in build.rs::cxx_build::bridges and lib.rs declares pub mod constants"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "classic-gui/src/app/mainwindow.cpp uses classic::constants::game_id_as_str (or fallout4_version_*) in at least one place where a hardcoded game/version string is currently used (D-11 consumer migration — Codex review MEDIUM correction)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs"
      provides: "New CXX bridge module exposing classic-constants-core surface (CXXS-01, D-04)"
      min_lines: 100
      contains: "namespace = \"classic::constants\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/constants.rs\""
      contains: "src/constants.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs"
      provides: "pub mod constants declaration under #[cfg(windows)]"
      contains: "pub mod constants"
    - path: "classic-gui/src/app/mainwindow.cpp"
      provides: "D-11 consumer — at least one call site uses classic::constants::* to replace a hardcoded game/version string (e.g., the QStringLiteral(\"Fallout4\") usage in saveLocalYamlPaths or startScan, replaced or paired with classic::constants::game_id_as_str(classic::constants::GameId::Fallout4))"
      contains: "classic::constants"
    - path: "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
      provides: "Refreshed CXX baseline including new constants entries (D-09)"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      to: "src/constants.rs"
      via: "cxx_build::bridges array entry"
      pattern: "src/constants\\.rs"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs"
      to: "src/constants.rs"
      via: "pub mod constants;"
      pattern: "pub mod constants"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs"
      to: "classic-constants-core (GameId, Fallout4Version, YamlFile, must_not_be_none, SETTINGS_IGNORE_NONE)"
      via: "use classic_constants_core::{...}"
      pattern: "use classic_constants_core"
    - from: "classic-gui/src/app/mainwindow.cpp"
      to: "classic_cxx_bridge/constants.h"
      via: "C++ #include + classic::constants::game_id_as_str / fallout4_version_* call"
      pattern: "classic::constants::"
---

<objective>
Create a brand-new CXX bridge module `src/constants.rs` exposing `classic-constants-core` for the first time (CXXS-01). Per D-04, the module declares `GameId`, `Fallout4Version`, and `YamlFile` as CXX shared enums inside `#[cxx::bridge(namespace = "classic::constants")]`, plus helper functions for the constants and predicates that don't fit the enum shape (`SETTINGS_IGNORE_NONE`, `must_not_be_none`, `NULL_VERSION` predicate, `as_str` getters). Adds the file to `build.rs` and runs the mandatory D-10 clean-build pair. Adds at least one D-11 consumer migration in `classic-gui/src/app/mainwindow.cpp` so the new namespace is exercised by production C++ code.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** The previous version of this plan only enumerated 4 YamlFile variants (Settings, Main, Game, Ignore). The REAL `classic-constants-core::YamlFile` has 7 variants — verified by direct read of `lib.rs` lines 592-700: `Main`, `Settings`, `Ignore`, `Game`, `GameLocal`, `Test`, `Cache`. This plan now enumerates all 7.

**REVIEWS-MODE NOTE (Codex review LOW):** `Fallout4Version::Vr.as_str()` returns the literal string `"VR"` (uppercase, not `"Vr"`). Verified at `classic-constants-core/src/lib.rs` line 1086. This plan now includes an explicit test case for the `Vr → "VR"` mapping.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** The previous version of this plan treated D-11 as N/A. The Codex review correctly noted that the roadmap explicitly calls out `classic::constants` as a new namespace C++ should be able to call (Phase 2 success criterion 2). This plan now adds a real consumer migration in `mainwindow.cpp` where hardcoded `QStringLiteral("Fallout4")` strings are replaced or paired with `classic::constants::game_id_as_str(classic::constants::GameId::Fallout4)` calls.

Purpose: This is one of the three first-time exposures in Phase 2 (CXXS-01/02/03 are first-time, the rest are widenings). `classic-constants-core` enums are referenced by `classic-web-core::ModSite::game_url(GameId)` — but per RESEARCH.md "Open Question 4", we use string-based dispatch in `web.rs` to avoid cross-module CXX shared-enum referencing problems, so `constants.rs` and `web.rs` are independent and can run in parallel (Wave 1).

Output: New `src/constants.rs` with bridged enums and helpers; `build.rs` and `lib.rs` updated; `mainwindow.cpp` exercises one new bridge fn; both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source of truth — what classic-constants-core ACTUALLY exposes (verified by direct read)
@ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs

# Reference patterns — how an existing single-purpose bridge module looks
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# build.rs and lib.rs — files this plan modifies
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# D-11 consumer migration site
@classic-gui/src/app/mainwindow.cpp

# Parity gate
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-constants-core public surface (VERIFIED by direct read of lib.rs). -->
<!-- Codex review MEDIUM correction: enum audit complete. -->

GameId enum (4 variants):
```rust
pub enum GameId { Fallout4, Fallout4VR, Skyrim, Starfield }
impl GameId {
    pub const fn as_str(&self) -> &'static str;
    // returns: "Fallout4", "Fallout4VR", "Skyrim", "Starfield"
}
```

Fallout4Version enum (4 variants — note Vr.as_str() returns "VR"):
```rust
pub enum Fallout4Version { Original, NextGen, AnniversaryEdition, Vr }
impl Fallout4Version {
    pub const fn as_str(&self) -> &'static str;
    // returns: "Original", "NextGen", "AnniversaryEdition", "VR" <-- NOT "Vr"
    pub fn registry_id(&self) -> &'static str;
    pub fn is_vr(&self) -> bool;
    pub fn is_standard(&self) -> bool;
    pub fn exe_name(&self) -> &'static str;
    pub fn docs_folder_name(&self) -> &'static str;
    pub fn steam_app_id(&self) -> u32;
}
```

YamlFile enum — VERIFIED 7 variants per lib.rs line 592-700:
```rust
pub enum YamlFile {
    Main,
    Settings,
    Ignore,
    Game,
    GameLocal,
    Test,
    Cache,
}
impl YamlFile {
    pub const fn as_str(&self) -> &'static str;
    // returns: "Main", "Settings", "Ignore", "Game", "GameLocal", "Test", "Cache"
    pub fn description(&self) -> &'static str;
    pub fn all() -> [YamlFile; 7];  // confirmed via lib.rs test_yaml_file_as_str
}
```

Constants and helpers:
```rust
pub const NULL_VERSION: semver::Version = Version::new(0, 0, 0); // not directly bridgeable — expose as predicate
pub const SETTINGS_IGNORE_NONE: &[&str] = &[/* string literals */]; // exact list confirmed via direct read
pub fn must_not_be_none(key: &str) -> bool;
```

CXX bridging strategy (per D-04 + RESEARCH.md):
- Declare each enum INSIDE the `#[cxx::bridge(namespace = "classic::constants")]` block with `#[repr(u8)]`
- For methods that take `&self`, expose a free fn that takes the bridge enum by value: `fn game_id_as_str(id: GameId) -> String`
- For NULL_VERSION (semver type — not bridgeable), expose a predicate: `fn is_null_version(major: u32, minor: u32, patch: u32) -> bool`
- For SETTINGS_IGNORE_NONE (slice — not bridgeable), expose a predicate: `fn settings_ignore_none_contains(key: &str) -> bool`
- For must_not_be_none: pass-through `fn must_not_be_none_key(key: &str) -> bool`
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create src/constants.rs with COMPLETE shared enums (7 YamlFile variants) + helper bridge fns + tests including the Vr→"VR" assertion</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs (READ ENTIRELY — confirm exact GameId / Fallout4Version / YamlFile variant names; confirm NULL_VERSION construction; confirm SETTINGS_IGNORE_NONE contents; confirm must_not_be_none signature; specifically read lines 592-700 for YamlFile variants and lines 1083-1086 for the Vr→"VR" assertion)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template — single-purpose bridge module with #[cfg(test)] mod tests using serial_test where global state is touched)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template — extern "Rust" function declarations and existing #[cxx::bridge] block style)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 02" (the MEDIUM concerns about enum audit completeness and VR mapping)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-constants-core" §"Pattern: New Bridge File"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04 (CXX shared enums for constants), D-12 (Rust-side tests default)
  </read_first>

  <behavior>
    - Test: `game_id_as_str(ffi::GameId::Fallout4)` returns "Fallout4".
    - Test: `game_id_as_str(ffi::GameId::Fallout4VR)` returns "Fallout4VR".
    - Test: `game_id_as_str` for all 4 variants matches `CoreGameId::as_str()` exactly.
    - Test: `fallout4_version_as_str(ffi::Fallout4Version::Vr)` returns the literal `"VR"` (Codex LOW review correction — not `"Vr"`).
    - Test: `fallout4_version_as_str(ffi::Fallout4Version::Original)` returns `"Original"`.
    - Test: `fallout4_version_registry_id(ffi::Fallout4Version::Original)` returns the exact registry_id() result.
    - Test: `fallout4_version_is_vr(ffi::Fallout4Version::Vr)` returns true; all other variants return false.
    - Test: `fallout4_version_steam_app_id(ffi::Fallout4Version::Original)` returns a non-zero u32.
    - Test: `yaml_file_as_str` round-trip for ALL 7 variants (Main, Settings, Ignore, Game, GameLocal, Test, Cache) matches `CoreYamlFile::as_str()`.
    - Test: `must_not_be_none_key` returns true for every entry in `SETTINGS_IGNORE_NONE` and false for an obviously fake key.
    - Test: `settings_ignore_none_contains` matches `must_not_be_none_key` for the same key.
    - Test: `is_null_version(0, 0, 0)` returns true; `is_null_version(1, 0, 0)` returns false.
  </behavior>

  <action>
  Create the file `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs`.

  Step 1 — Read `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` end-to-end. CONFIRM by direct read:
  - `GameId` variants: `Fallout4`, `Fallout4VR`, `Skyrim`, `Starfield`
  - `Fallout4Version` variants: `Original`, `NextGen`, `AnniversaryEdition`, `Vr`
  - `Fallout4Version::Vr.as_str() == "VR"` (NOT "Vr")
  - `YamlFile` variants — ALL 7: `Main`, `Settings`, `Ignore`, `Game`, `GameLocal`, `Test`, `Cache`
  - The exact contents of `SETTINGS_IGNORE_NONE` (read the slice literal — it's around line 857)

  Step 2 — Write the file with this structure (substitute the EXACT variant names from step 1):

  ```rust
  //! Constants bridge for CXX FFI.
  //!
  //! Bridges `classic-constants-core` enums and helpers so C++ frontends can
  //! reference the canonical game / YAML file / Fallout 4 version identifiers
  //! without hardcoding strings. Per D-04, enums cross the boundary as CXX
  //! shared enums.

  use classic_constants_core::{
      Fallout4Version as CoreFallout4Version,
      GameId as CoreGameId,
      YamlFile as CoreYamlFile,
      must_not_be_none as core_must_not_be_none,
      SETTINGS_IGNORE_NONE,
  };

  // ─────────────────────────────────────────────────────────────────────
  // GameId helpers
  // ─────────────────────────────────────────────────────────────────────

  fn from_bridge_game_id(id: ffi::GameId) -> CoreGameId {
      match id {
          ffi::GameId::Fallout4 => CoreGameId::Fallout4,
          ffi::GameId::Fallout4VR => CoreGameId::Fallout4VR,
          ffi::GameId::Skyrim => CoreGameId::Skyrim,
          ffi::GameId::Starfield => CoreGameId::Starfield,
          _ => CoreGameId::Fallout4, // unreachable in safe usage
      }
  }

  fn game_id_as_str(id: ffi::GameId) -> String {
      from_bridge_game_id(id).as_str().to_string()
  }

  // ─────────────────────────────────────────────────────────────────────
  // Fallout4Version helpers
  // NOTE: Vr.as_str() returns "VR" (uppercase) — Codex review LOW correction
  // ─────────────────────────────────────────────────────────────────────

  fn from_bridge_f4_version(v: ffi::Fallout4Version) -> CoreFallout4Version {
      match v {
          ffi::Fallout4Version::Original => CoreFallout4Version::Original,
          ffi::Fallout4Version::NextGen => CoreFallout4Version::NextGen,
          ffi::Fallout4Version::AnniversaryEdition => CoreFallout4Version::AnniversaryEdition,
          ffi::Fallout4Version::Vr => CoreFallout4Version::Vr,
          _ => CoreFallout4Version::Original,
      }
  }

  fn fallout4_version_as_str(v: ffi::Fallout4Version) -> String {
      from_bridge_f4_version(v).as_str().to_string()
  }
  fn fallout4_version_registry_id(v: ffi::Fallout4Version) -> String {
      from_bridge_f4_version(v).registry_id().to_string()
  }
  fn fallout4_version_is_vr(v: ffi::Fallout4Version) -> bool {
      from_bridge_f4_version(v).is_vr()
  }
  fn fallout4_version_is_standard(v: ffi::Fallout4Version) -> bool {
      from_bridge_f4_version(v).is_standard()
  }
  fn fallout4_version_exe_name(v: ffi::Fallout4Version) -> String {
      from_bridge_f4_version(v).exe_name().to_string()
  }
  fn fallout4_version_docs_folder_name(v: ffi::Fallout4Version) -> String {
      from_bridge_f4_version(v).docs_folder_name().to_string()
  }
  fn fallout4_version_steam_app_id(v: ffi::Fallout4Version) -> u32 {
      from_bridge_f4_version(v).steam_app_id()
  }

  // ─────────────────────────────────────────────────────────────────────
  // YamlFile helpers — ALL 7 variants (Codex review MEDIUM correction)
  // ─────────────────────────────────────────────────────────────────────

  fn from_bridge_yaml_file(f: ffi::YamlFile) -> CoreYamlFile {
      match f {
          ffi::YamlFile::Main => CoreYamlFile::Main,
          ffi::YamlFile::Settings => CoreYamlFile::Settings,
          ffi::YamlFile::Ignore => CoreYamlFile::Ignore,
          ffi::YamlFile::Game => CoreYamlFile::Game,
          ffi::YamlFile::GameLocal => CoreYamlFile::GameLocal,
          ffi::YamlFile::Test => CoreYamlFile::Test,
          ffi::YamlFile::Cache => CoreYamlFile::Cache,
          _ => CoreYamlFile::Settings,
      }
  }
  fn yaml_file_as_str(f: ffi::YamlFile) -> String {
      from_bridge_yaml_file(f).as_str().to_string()
  }
  fn yaml_file_description(f: ffi::YamlFile) -> String {
      from_bridge_yaml_file(f).description().to_string()
  }

  // ─────────────────────────────────────────────────────────────────────
  // SETTINGS_IGNORE_NONE / must_not_be_none predicates
  // (slices and consts are not directly bridgeable; expose as predicates)
  // ─────────────────────────────────────────────────────────────────────

  fn must_not_be_none_key(key: &str) -> bool {
      core_must_not_be_none(key)
  }

  fn settings_ignore_none_contains(key: &str) -> bool {
      SETTINGS_IGNORE_NONE.iter().any(|k| *k == key)
  }

  // ─────────────────────────────────────────────────────────────────────
  // NULL_VERSION predicate (semver types are not bridgeable as values)
  // ─────────────────────────────────────────────────────────────────────

  fn is_null_version(major: u32, minor: u32, patch: u32) -> bool {
      major == 0 && minor == 0 && patch == 0
  }

  // ─────────────────────────────────────────────────────────────────────
  // CXX bridge block — D-04 shared enums + extern "Rust" helper fns
  // ─────────────────────────────────────────────────────────────────────

  #[cxx::bridge(namespace = "classic::constants")]
  mod ffi {
      #[repr(u8)]
      enum GameId {
          Fallout4 = 0,
          Fallout4VR = 1,
          Skyrim = 2,
          Starfield = 3,
      }

      #[repr(u8)]
      enum Fallout4Version {
          Original = 0,
          NextGen = 1,
          AnniversaryEdition = 2,
          Vr = 3,
      }

      // ALL 7 YamlFile variants — Codex review MEDIUM correction
      #[repr(u8)]
      enum YamlFile {
          Main = 0,
          Settings = 1,
          Ignore = 2,
          Game = 3,
          GameLocal = 4,
          Test = 5,
          Cache = 6,
      }

      extern "Rust" {
          fn game_id_as_str(id: GameId) -> String;

          fn fallout4_version_as_str(v: Fallout4Version) -> String;
          fn fallout4_version_registry_id(v: Fallout4Version) -> String;
          fn fallout4_version_is_vr(v: Fallout4Version) -> bool;
          fn fallout4_version_is_standard(v: Fallout4Version) -> bool;
          fn fallout4_version_exe_name(v: Fallout4Version) -> String;
          fn fallout4_version_docs_folder_name(v: Fallout4Version) -> String;
          fn fallout4_version_steam_app_id(v: Fallout4Version) -> u32;

          fn yaml_file_as_str(f: YamlFile) -> String;
          fn yaml_file_description(f: YamlFile) -> String;

          fn must_not_be_none_key(key: &str) -> bool;
          fn settings_ignore_none_contains(key: &str) -> bool;
          fn is_null_version(major: u32, minor: u32, patch: u32) -> bool;
      }
  }

  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn test_game_id_as_str_fallout4() {
          assert_eq!(game_id_as_str(ffi::GameId::Fallout4), "Fallout4");
      }

      #[test]
      fn test_game_id_as_str_all_variants_match_core() {
          let pairs = [
              (ffi::GameId::Fallout4, CoreGameId::Fallout4),
              (ffi::GameId::Fallout4VR, CoreGameId::Fallout4VR),
              (ffi::GameId::Skyrim, CoreGameId::Skyrim),
              (ffi::GameId::Starfield, CoreGameId::Starfield),
          ];
          for (bridge, core) in pairs {
              assert_eq!(game_id_as_str(bridge), core.as_str());
          }
      }

      #[test]
      fn test_fallout4_version_as_str_vr_is_uppercase_VR() {
          // Codex review LOW correction: Vr.as_str() returns literal "VR"
          assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::Vr), "VR");
          // sanity: also matches the core
          assert_eq!(
              fallout4_version_as_str(ffi::Fallout4Version::Vr),
              CoreFallout4Version::Vr.as_str()
          );
      }

      #[test]
      fn test_fallout4_version_as_str_all_variants() {
          assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::Original), "Original");
          assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::NextGen), "NextGen");
          assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::AnniversaryEdition),
                     CoreFallout4Version::AnniversaryEdition.as_str());
          assert_eq!(fallout4_version_as_str(ffi::Fallout4Version::Vr), "VR");
      }

      #[test]
      fn test_fallout4_version_is_vr_only_true_for_vr() {
          assert!(fallout4_version_is_vr(ffi::Fallout4Version::Vr));
          assert!(!fallout4_version_is_vr(ffi::Fallout4Version::Original));
          assert!(!fallout4_version_is_vr(ffi::Fallout4Version::NextGen));
          assert!(!fallout4_version_is_vr(ffi::Fallout4Version::AnniversaryEdition));
      }

      #[test]
      fn test_fallout4_version_steam_app_id_nonzero_for_original() {
          assert!(fallout4_version_steam_app_id(ffi::Fallout4Version::Original) > 0);
      }

      #[test]
      fn test_yaml_file_as_str_all_seven_variants() {
          // Codex review MEDIUM correction: ALL 7 variants
          let pairs = [
              (ffi::YamlFile::Main, "Main"),
              (ffi::YamlFile::Settings, "Settings"),
              (ffi::YamlFile::Ignore, "Ignore"),
              (ffi::YamlFile::Game, "Game"),
              (ffi::YamlFile::GameLocal, "GameLocal"),
              (ffi::YamlFile::Test, "Test"),
              (ffi::YamlFile::Cache, "Cache"),
          ];
          for (bridge, expected) in pairs {
              assert_eq!(yaml_file_as_str(bridge), expected);
          }
      }

      #[test]
      fn test_yaml_file_description_returns_nonempty_for_all_seven() {
          for f in [
              ffi::YamlFile::Main,
              ffi::YamlFile::Settings,
              ffi::YamlFile::Ignore,
              ffi::YamlFile::Game,
              ffi::YamlFile::GameLocal,
              ffi::YamlFile::Test,
              ffi::YamlFile::Cache,
          ] {
              assert!(!yaml_file_description(f).is_empty());
          }
      }

      #[test]
      fn test_must_not_be_none_key_matches_settings_ignore_none() {
          for key in SETTINGS_IGNORE_NONE {
              assert!(must_not_be_none_key(key), "must_not_be_none should be true for key {}", key);
              assert!(settings_ignore_none_contains(key));
          }
      }

      #[test]
      fn test_must_not_be_none_key_false_for_unknown() {
          assert!(!must_not_be_none_key("definitely_not_a_real_key_xyz_789"));
          assert!(!settings_ignore_none_contains("definitely_not_a_real_key_xyz_789"));
      }

      #[test]
      fn test_is_null_version_predicate() {
          assert!(is_null_version(0, 0, 0));
          assert!(!is_null_version(1, 0, 0));
          assert!(!is_null_version(0, 1, 0));
          assert!(!is_null_version(0, 0, 1));
      }
  }
  ```

  Step 3 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests` and confirm all 11+ tests pass.

  IMPORTANT: If `classic-constants-core` is not in `classic-cpp-bridge/Cargo.toml`, add it: `classic-constants-core = { workspace = true }`.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests</automated>
  </verify>

  <acceptance_criteria>
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` exists
    - `git grep -n 'namespace = "classic::constants"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns one match
    - `git grep -n 'enum GameId' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns the bridge enum declaration with 4 variants
    - `git grep -nE 'Main|Settings|Ignore|Game|GameLocal|Test|Cache' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 7 distinct variant names inside the YamlFile bridge enum block (Codex review correction)
    - `git grep -n 'GameLocal' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 2 lines (bridge variant + match arm)
    - `git grep -n 'fn fallout4_version_as_str' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns 2+ matches (definition + extern)
    - `git grep -n '"VR"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least one match in the test block (the explicit Vr → "VR" assertion)
    - `git grep -n 'fn must_not_be_none_key' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 2 matches
    - `git grep -n 'fn is_null_version' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 2 matches
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests` exits 0 with at least 11 passing tests (including the test_yaml_file_as_str_all_seven_variants and test_fallout4_version_as_str_vr_is_uppercase_VR tests)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/constants.rs` exists with all CXXS-01 enums + helpers, the YamlFile enum has all 7 variants, the Vr → "VR" mapping is explicitly tested, every bridge fn has a passing Rust-side test, and the file compiles cleanly with no clippy warnings.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire constants.rs into build.rs + lib.rs, add D-11 consumer migration in mainwindow.cpp, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-gui/src/app/mainwindow.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current bridges array — INSERT `"src/constants.rs"` early in the array, immediately after `"src/types.rs"`, so generated headers for the shared enums appear before any potential consumers reference them)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (current pub mod declarations — add `pub mod constants;` under `#[cfg(windows)]` in alphabetical order)
    - classic-gui/src/app/mainwindow.cpp (around lines 1148, 1187, 1566, 1584 — find where `QStringLiteral("Fallout4")` is hardcoded; one of these is the D-11 consumer migration target. The simplest target: introduce a small helper function or static-storage variable initialized via `classic::constants::game_id_as_str(classic::constants::GameId::Fallout4)` and use it in at least one of those call sites — the goal is a real production caller of the new bridge fn, not a comprehensive sweep)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09 (per-plan baseline refresh), D-10 (mandatory clean-build pair on new build.rs entries), D-11 (consumer migration mandatory)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 02" MEDIUM concern about D-11
    - .planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md row 2-02-01
  </read_first>

  <action>
  ## Part A — Add to build.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`. Insert `"src/constants.rs",` near the START of the `cxx_build::bridges([...])` array (immediately after `"src/types.rs",`). Listing constants.rs before any consumer prevents Pitfall 5 forward-declaration ordering issues for the shared enums.

  Final state for the relevant lines:
  ```rust
  cxx_build::bridges([
      "src/types.rs",
      "src/constants.rs",   // <- NEW
      "src/runtime.rs",
      "src/registry.rs",
      ...
  ```

  ## Part B — Add to lib.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`. Insert under `#[cfg(windows)]` (alphabetically — after `pub mod config;`):

  ```rust
  #[cfg(windows)]
  pub mod constants;
  ```

  ## Part C — D-11 consumer migration in mainwindow.cpp (Codex review correction)

  Edit `classic-gui/src/app/mainwindow.cpp`. Add `#include "classic_cxx_bridge/constants.h"` near the existing CXX bridge header includes.

  Then add a small helper at the top of the file (or in an anonymous namespace), and use it in at least one place where `QStringLiteral("Fallout4")` is currently hardcoded:

  ```cpp
  #include "classic_cxx_bridge/constants.h"

  namespace {
      // D-11 / CXXS-01 consumer migration: use the bridged GameId helper
      // instead of hardcoding the literal "Fallout4" string. This proves
      // classic::constants is callable from production C++ code.
      QString fallout4GameIdLabel() {
          // game_id_as_str returns a rust::String — convert via classic::toQString
          auto rust_str = classic::constants::game_id_as_str(classic::constants::GameId::Fallout4);
          return QString::fromUtf8(rust_str.data(), static_cast<int>(rust_str.size()));
      }
  }
  ```

  Then find ONE existing site where `QStringLiteral("Fallout4")` is used (e.g., line ~1148, 1187, 1566, or 1584 — the `saveLocalYamlPaths` or `m_scanController->startScan` calls) and change it to call `fallout4GameIdLabel()` instead. Pick a SINGLE site — the goal is to prove the bridge fn is exercised, not to do a sweeping refactor. Other QStringLiteral("Fallout4") usages can stay.

  IMPORTANT: Do NOT introduce a Qt translation marker or change the visible UI text. The bridged value is the same string ("Fallout4") that was previously hardcoded.

  Run `git grep -n 'classic::constants' classic-gui/src/app/mainwindow.cpp` and confirm at least one line.

  ## Part D — Mandatory D-10 clean-build pair

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. If MSVC reports `C2027 use of undefined type` referencing the new shared enums in a generated header, the include order in `build.rs` is wrong — move `"src/constants.rs"` even earlier and re-run.

  Confirm the generated header appears:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/constants.h
  ```

  ## Part E — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  The second run must exit 0 with 0 drift.

  ## Part F — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`
  - `classic-gui/src/app/mainwindow.cpp`
  - `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md`
  - `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`

  Commit message: `Feat(02-02): expose classic-constants-core via classic::constants CXX bridge` — body mentions CXXS-01, D-04, D-09, D-10, D-11 and explicitly notes the mainwindow.cpp consumer migration.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/constants.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the bridges array
    - `git grep -n 'pub mod constants' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `git grep -n 'classic::constants::game_id_as_str\|classic::constants::GameId' classic-gui/src/app/mainwindow.cpp` returns at least one line (D-11 consumer)
    - `git grep -n '#include "classic_cxx_bridge/constants.h"' classic-gui/src/app/mainwindow.cpp` returns the new include
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/constants.h` exists after the clean build
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0
    - The parity gate report includes new entries under `bridgeModule: "constants"` covering all bridge fns + 3 shared enums (with YamlFile having 7 variants)
    - `git log -1 --stat` shows the commit touches Rust source AND mainwindow.cpp AND `docs/implementation/cxx_api_parity/baseline/*` together (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-02 complete — `classic::constants` is a first-class CXX bridge module with all 7 YamlFile variants and the Vr → "VR" mapping locked, mainwindow.cpp has at least one production caller for the new namespace, both clean builds pass, and CXXS-01 is satisfied.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` — exits 0
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` — exits 0
4. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 drift
5. `git grep -n 'classic::constants' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/constants.h` returns multiple matches (CXX-generated namespace declarations)
6. The committed `cxx_diff_report.md` shows ADDED rows for `constants` bridgeModule
7. `git grep -n 'classic::constants' classic-gui/src/app/mainwindow.cpp` returns the D-11 consumer call

Validation Architecture (per 02-VALIDATION.md row 2-02-01): `cargo test -p classic-cpp-bridge constants::tests` + clean-build pair + parity gate + D-11 consumer caller verified.
</verification>

<success_criteria>
- src/constants.rs exists with #[cxx::bridge(namespace = "classic::constants")] and exposes GameId, Fallout4Version, YamlFile (ALL 7 variants) as CXX shared enums
- Vr → "VR" mapping explicitly tested
- All helper bridge fns are tested and pass (11+ tests)
- mainwindow.cpp has a D-11 consumer migration calling at least one classic::constants::* fn (Codex review correction)
- Both clean MSVC builds are green (D-10)
- Parity gate is at 0 drift after --update-baseline (D-09)
- All changes committed atomically
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-02-SUMMARY.md` documenting:
- Confirmation that ALL 7 YamlFile variants are bridged (Codex MEDIUM correction)
- Confirmation that Vr → "VR" mapping is tested (Codex LOW correction)
- Confirmation that mainwindow.cpp has a D-11 consumer migration (Codex MEDIUM correction)
- Entries added to the parity contract (count by kind: function, enum)
- D-10 clean-build outcome
- The exact mainwindow.cpp line that was migrated (before/after snippet)
</output>
