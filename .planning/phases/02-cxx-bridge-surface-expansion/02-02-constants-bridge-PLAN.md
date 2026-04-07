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
    - "GameId, Fallout4Version, and YamlFile are exposed as CXX shared enums (D-04) with the exact variant set from classic-constants-core"
    - "must_not_be_none, settings_ignore_none_contains, is_null_version, game_id_as_str helper fns are bridged"
    - "src/constants.rs is in build.rs::cxx_build::bridges and lib.rs declares pub mod constants"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs"
      provides: "New CXX bridge module exposing classic-constants-core surface (CXXS-01, D-04)"
      min_lines: 80
      contains: "namespace = \"classic::constants\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/constants.rs\""
      contains: "src/constants.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs"
      provides: "pub mod constants declaration under #[cfg(windows)]"
      contains: "pub mod constants"
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
---

<objective>
Create a brand-new CXX bridge module `src/constants.rs` exposing `classic-constants-core` for the first time (CXXS-01). Per D-04, the module declares `GameId`, `Fallout4Version`, and `YamlFile` as CXX shared enums inside `#[cxx::bridge(namespace = "classic::constants")]`, plus helper functions for the constants and predicates that don't fit the enum shape (`SETTINGS_IGNORE_NONE`, `must_not_be_none`, `NULL_VERSION` predicate, `as_str` getters). Adds the file to `build.rs` and runs the mandatory D-10 clean-build pair.

Purpose: This is one of the three first-time exposures in Phase 2 (CXXS-01/02/03 are first-time, the rest are widenings). `classic-constants-core` enums are referenced by `classic-web-core::ModSite::game_url(GameId)` — but per RESEARCH.md "Open Question 4", we use string-based dispatch in `web.rs` to avoid cross-module CXX shared-enum referencing problems, so `constants.rs` and `web.rs` are independent and can run in parallel (Wave 1).

Output: New `src/constants.rs` with bridged enums and helpers; `build.rs` and `lib.rs` updated; both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source of truth — what classic-constants-core exposes
@ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs

# Reference patterns — how an existing single-purpose bridge module looks
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# build.rs and lib.rs — files this plan modifies
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# Parity gate
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-constants-core public surface (read directly from lib.rs before implementing). -->

GameId enum (4 variants per RESEARCH.md):
```rust
pub enum GameId { Fallout4, Fallout4VR, Skyrim, Starfield }
impl GameId { pub fn as_str(&self) -> &'static str; }
```

Fallout4Version enum (4 variants):
```rust
pub enum Fallout4Version { Original, NextGen, AnniversaryEdition, Vr }
impl Fallout4Version {
    pub fn registry_id(&self) -> &'static str;
    pub fn is_vr(&self) -> bool;
    pub fn is_standard(&self) -> bool;
    pub fn exe_name(&self) -> &'static str;
    pub fn docs_folder_name(&self) -> &'static str;
    pub fn steam_app_id(&self) -> u32;
}
```

YamlFile — variant set MUST be confirmed by direct read of lib.rs before implementing (RESEARCH.md "Open Question 1"). Likely candidates: Settings, Main, Game, Ignore. The executor reads lib.rs and uses the EXACT variant names.

Constants and helpers:
```rust
pub const NULL_VERSION: semver::Version = Version::new(0, 0, 0); // not directly bridgeable — use predicate
pub const SETTINGS_IGNORE_NONE: &[&str] = &[/* 5 string literals */];
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
  <name>Task 1: Create src/constants.rs with shared enums + helper bridge fns + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs (READ ENTIRELY — confirm exact GameId / Fallout4Version / YamlFile variant names; confirm NULL_VERSION construction; confirm SETTINGS_IGNORE_NONE contents; confirm must_not_be_none signature)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template — single-purpose bridge module with #[cfg(test)] mod tests using serial_test where global state is touched)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template — extern "Rust" function declarations and existing #[cxx::bridge] block style)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-constants-core" §"Pattern: New Bridge File"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04 (CXX shared enums for constants), D-12 (Rust-side tests default)
  </read_first>

  <behavior>
    - Test: `game_id_as_str(ffi::GameId::Fallout4)` returns "Fallout4" (exact case from `GameId::as_str()`).
    - Test: `game_id_as_str(ffi::GameId::Fallout4VR)` returns "Fallout4VR" (or whatever as_str() produces).
    - Test: `fallout4_version_registry_id(ffi::Fallout4Version::Original)` returns the exact registry_id() result (e.g. "FO4_OG" or whatever the core defines).
    - Test: `fallout4_version_is_vr(ffi::Fallout4Version::Vr)` returns true; `fallout4_version_is_vr(ffi::Fallout4Version::Original)` returns false.
    - Test: `fallout4_version_steam_app_id(ffi::Fallout4Version::Original)` returns a non-zero u32.
    - Test: `must_not_be_none_key("Root_Folder_Game")` returns true (assuming this is in SETTINGS_IGNORE_NONE — confirm via lib.rs before writing).
    - Test: `must_not_be_none_key("Root_Folder_Game_NOT_REAL")` returns false.
    - Test: `settings_ignore_none_contains` matches `must_not_be_none_key` for the same key (sanity equivalence).
    - Test: `is_null_version(0, 0, 0)` returns true; `is_null_version(1, 0, 0)` returns false.
  </behavior>

  <action>
  Create the file `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs`.

  Step 1 — Read `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` end-to-end. Note the EXACT variant names of `GameId`, `Fallout4Version`, and `YamlFile`. The research notes that `YamlFile` variant names are an Open Question — resolve it by direct read here (no guessing).

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
          _ => CoreGameId::Fallout4, // unreachable in safe usage; CXX may add sentinel variants
      }
  }

  fn game_id_as_str(id: ffi::GameId) -> String {
      from_bridge_game_id(id).as_str().to_string()
  }

  // ─────────────────────────────────────────────────────────────────────
  // Fallout4Version helpers
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
  // YamlFile helpers
  // ─────────────────────────────────────────────────────────────────────
  // NOTE: variants populated from direct read of classic-constants-core lib.rs
  // (Settings / Main / Game / Ignore — confirm and update if reality differs).

  fn from_bridge_yaml_file(f: ffi::YamlFile) -> CoreYamlFile {
      match f {
          ffi::YamlFile::Settings => CoreYamlFile::Settings,
          ffi::YamlFile::Main => CoreYamlFile::Main,
          ffi::YamlFile::Game => CoreYamlFile::Game,
          ffi::YamlFile::Ignore => CoreYamlFile::Ignore,
          _ => CoreYamlFile::Settings,
      }
  }
  fn yaml_file_as_str(f: ffi::YamlFile) -> String {
      // Expose via the core's preferred string form — adjust if core has a different method name
      format!("{:?}", from_bridge_yaml_file(f))
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

      #[repr(u8)]
      enum YamlFile {
          Settings = 0,
          Main = 1,
          Game = 2,
          Ignore = 3,
      }

      extern "Rust" {
          fn game_id_as_str(id: GameId) -> String;

          fn fallout4_version_registry_id(v: Fallout4Version) -> String;
          fn fallout4_version_is_vr(v: Fallout4Version) -> bool;
          fn fallout4_version_is_standard(v: Fallout4Version) -> bool;
          fn fallout4_version_exe_name(v: Fallout4Version) -> String;
          fn fallout4_version_docs_folder_name(v: Fallout4Version) -> String;
          fn fallout4_version_steam_app_id(v: Fallout4Version) -> u32;

          fn yaml_file_as_str(f: YamlFile) -> String;

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
          assert_eq!(game_id_as_str(ffi::GameId::Fallout4), CoreGameId::Fallout4.as_str());
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
      fn test_must_not_be_none_key_matches_settings_ignore_none() {
          // Pick a key from SETTINGS_IGNORE_NONE — confirm via lib.rs read
          // (executor: substitute the actual first key from the slice)
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

      #[test]
      fn test_yaml_file_as_str_returns_nonempty() {
          for f in [ffi::YamlFile::Settings, ffi::YamlFile::Main, ffi::YamlFile::Game, ffi::YamlFile::Ignore] {
              assert!(!yaml_file_as_str(f).is_empty());
          }
      }
  }
  ```

  Step 3 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests` and confirm all 8 tests pass.

  IMPORTANT: If any of the variant names (`GameId`, `Fallout4Version`, `YamlFile`) differ from what's hardcoded above, update both the bridge enum block AND the `from_bridge_*` helper match arms to use the EXACT names from `classic-constants-core/src/lib.rs`. The CXX gate will reject any drift.

  If `classic-constants-core` has a `Cargo.toml` dependency missing in `classic-cpp-bridge/Cargo.toml`, add it: `classic-constants-core = { workspace = true }` (verify the workspace already declares it; if not, add to workspace `Cargo.toml` first).
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests</automated>
  </verify>

  <acceptance_criteria>
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` exists
    - `git grep -n 'namespace = "classic::constants"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns one match
    - `git grep -n 'enum GameId' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns the bridge enum declaration
    - `git grep -n 'enum Fallout4Version' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns the bridge enum declaration
    - `git grep -n 'enum YamlFile' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns the bridge enum declaration
    - `git grep -n 'fn must_not_be_none_key' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 2 matches (definition + extern declaration)
    - `git grep -n 'fn is_null_version' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` returns at least 2 matches
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml constants::tests` exits 0 with at least 8 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/constants.rs` exists with all CXXS-01 enums + helpers, every bridge fn has a passing Rust-side test, and the file compiles cleanly with no clippy warnings.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire constants.rs into build.rs + lib.rs, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current bridges array — INSERT `"src/constants.rs"` BEFORE `"src/web.rs"` if web.rs is also being added in the same wave; otherwise insert near the start so generated headers appear before consumers reference them; per RESEARCH.md "Pitfall 5", listing constants.rs early avoids forward-declaration issues)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (current pub mod declarations — add `pub mod constants;` under `#[cfg(windows)]` in the alphabetical block)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09 (per-plan baseline refresh), D-10 (mandatory clean-build pair on new build.rs entries)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"Clean-Build Cadence (D-10)" §"Baseline Refresh Cadence (D-09)"
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

  ## Part C — Mandatory D-10 clean-build pair

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0. If MSVC reports `C2027 use of undefined type` referencing the new shared enums in a generated header, the include order in `build.rs` is wrong — move `"src/constants.rs"` even earlier (right after `"src/types.rs"`) and re-run.

  Confirm the generated header appears:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/constants.h
  ```

  ## Part D — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  The second run must exit 0 with 0 drift.

  ## Part E — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`
  - `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json`
  - `docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md`
  - `docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md`

  Commit message: `Feat(02-02): expose classic-constants-core via classic::constants CXX bridge` — body mentions CXXS-01, D-04, D-09, D-10.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/constants.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the bridges array
    - `git grep -n 'pub mod constants' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/constants.h` exists after the clean build
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0
    - The parity gate report includes new entries under `bridgeModule: "constants"` covering all 11 bridge fns + 3 shared enums
    - `git log -1 --stat` shows the commit touches Rust source AND `docs/implementation/cxx_api_parity/baseline/*` together (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-02 complete — `classic::constants` is a first-class CXX bridge module locked in the parity contract, both clean builds pass, and CXXS-01 is satisfied.
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

Validation Architecture (per 02-VALIDATION.md row 2-02-01): `cargo test -p classic-cpp-bridge constants::tests` + clean-build pair + parity gate.
</verification>

<success_criteria>
- src/constants.rs exists with #[cxx::bridge(namespace = "classic::constants")] and exposes GameId, Fallout4Version, YamlFile as CXX shared enums
- All helper bridge fns are tested and pass
- Both clean MSVC builds are green (D-10)
- Parity gate is at 0 drift after --update-baseline (D-09)
- All changes committed atomically
- Note: NO D-11 consumer migration in this plan — `classic-constants-core` was previously bridge-invisible, so there are no narrowed C++ call sites to migrate. Future plans (or separate consumer-side work in Phase 5/6) will exercise the new namespace from frontend code.
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-02-SUMMARY.md` documenting:
- Exact YamlFile variant names found in classic-constants-core/lib.rs (resolves RESEARCH.md Open Question 1)
- Entries added to the parity contract (count by kind: function, enum)
- D-10 clean-build outcome
- Note that this plan adds a first-time bridge namespace; D-11 consumer migration is N/A for first-time exposures
</output>