---
phase: 02-cxx-bridge-surface-expansion
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-02
  - CXXS-10
must_haves:
  truths:
    - "src/web.rs exists and contains a #[cxx::bridge(namespace = \"classic::web\")] block"
    - "ModSite is exposed as a CXX shared enum (D-04 / D-07) with the exact 3 variants from classic-web-core"
    - "URL helpers (is_valid_url, validate_url, extract_domain, get_user_agent, get_user_agent_with_suffix, join_url, build_url_with_query) are bridged"
    - "ModSite methods (base_url, name, game_url) are bridged using string-based dispatch (no cross-module GameId reference per RESEARCH.md Open Question 4)"
    - "src/web.rs is in build.rs::cxx_build::bridges and lib.rs declares pub mod web"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs"
      provides: "New CXX bridge module exposing classic-web-core URL/user-agent/mod-site helpers (CXXS-02)"
      min_lines: 100
      contains: "namespace = \"classic::web\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/web.rs\""
      contains: "src/web.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs"
      provides: "pub mod web declaration under #[cfg(windows)]"
      contains: "pub mod web"
    - path: "docs/implementation/cxx_api_parity/baseline/parity_contract.json"
      provides: "Refreshed CXX baseline including new web entries (D-09)"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      to: "src/web.rs"
      via: "cxx_build::bridges array entry"
      pattern: "src/web\\.rs"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs"
      to: "classic-web-core (validate_url, is_valid_url, extract_domain, get_user_agent, build_url_with_query, ModSite)"
      via: "use classic_web_core::{...}"
      pattern: "use classic_web_core"
---

<objective>
Create a brand-new CXX bridge module `src/web.rs` exposing `classic-web-core` (CXXS-02). Per D-04, declares `ModSite` as a CXX shared enum and bridges all URL helpers, user-agent helpers, and ModSite methods. Per RESEARCH.md "Open Question 4", uses string-based dispatch for `mod_site_game_url(site_name, game_id_str)` to avoid cross-module shared-enum referencing problems with `classic::constants::GameId`. Adds the file to `build.rs` and runs the mandatory D-10 clean-build pair.

Purpose: First-time exposure of `classic-web-core` to C++ frontends. Independent of `constants.rs` (no shared types cross the module boundary because we use string dispatch), so this plan can run in parallel with Plan 02-02 in Wave 1.

Output: New `src/web.rs` with bridged URL/user-agent/mod-site helpers; `build.rs` and `lib.rs` updated; both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source of truth — what classic-web-core exposes
@ClassicLib-rs/business-logic/classic-web-core/src/lib.rs

# Reference patterns
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# Files this plan modifies
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# Parity gate
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-web-core public surface (per RESEARCH.md §"classic-web-core"). -->

```rust
pub fn validate_url(url_str: &str) -> Result<(), String>;
pub fn is_valid_url(url_str: &str) -> bool;
pub fn extract_domain(url_str: &str) -> Result<String, String>;
pub fn get_user_agent() -> String;
pub fn get_user_agent_with_suffix(suffix: &str) -> String;
pub fn join_url(base: &str, path: &str) -> Result<String, String>;
pub fn build_url_with_query(base: &str, params: &[(&str, &str)]) -> Result<String, String>;

pub enum ModSite { NexusMods, BethesdaNet, ModDB }
impl ModSite {
    pub fn base_url(&self) -> &'static str;
    pub fn name(&self) -> &'static str;
    pub fn game_url(&self, game_id: GameId) -> String;  // takes classic_constants_core::GameId
}
```

CXX bridging strategy (per D-04, D-07, RESEARCH.md):
- Declare `ModSite` as a CXX shared enum INSIDE `#[cxx::bridge(namespace = "classic::web")]`
- For ModSite methods, expose free fns that take a string discriminant (NOT the bridge enum, NOT GameId from constants) — `mod_site_base_url(site_name: &str) -> String`, etc.
- This avoids cross-module shared-enum referencing problems entirely (Open Question 4 resolution)
- For `build_url_with_query`, the `&[(&str, &str)]` slice-of-tuples is NOT CXX-bridgeable. Take two parallel `&[String]` vectors (keys + values). Pattern documented in RESEARCH.md §"Architecture Patterns".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create src/web.rs with shared ModSite enum + URL helpers + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-web-core/src/lib.rs (READ ENTIRELY — confirm exact ModSite variant names; confirm validate_url / is_valid_url / extract_domain / get_user_agent / get_user_agent_with_suffix / join_url / build_url_with_query signatures; confirm ModSite::base_url / name / game_url method names)
    - ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs (only read GameId — needed if game_url() requires constructing one from a string)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template for single-purpose bridge module with #[cfg(test)] mod tests)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template — extern "Rust" Result<T> declarations and slice parameters)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-web-core" §"Pattern: build_url_with_query key/value parallel vectors" §"Open Question 4"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-07 (CXX shared enums for ModSite + constants), D-12 (Rust-side tests)
  </read_first>

  <behavior>
    - Test: `is_valid_url("https://nexusmods.com")` returns true.
    - Test: `is_valid_url("not-a-url")` returns false.
    - Test: `validate_url_string("https://nexusmods.com")` returns Ok(()).
    - Test: `validate_url_string("garbage")` returns Err with non-empty message.
    - Test: `extract_domain_string("https://nexusmods.com/games/fallout4")` returns Ok("nexusmods.com").
    - Test: `web_get_user_agent()` returns a non-empty string starting with the project's user-agent prefix (whatever core defines).
    - Test: `web_get_user_agent_with_suffix("test-suffix")` returns a string CONTAINING "test-suffix".
    - Test: `web_join_url("https://example.com", "path")` returns Ok("https://example.com/path") (or whatever core's join_url defines for the trailing-slash policy).
    - Test: `web_build_url_with_query("https://example.com", &["a".into(), "b".into()], &["1".into(), "2".into()])` returns Ok with a query string containing both `a=1` and `b=2`.
    - Test: `web_build_url_with_query("https://example.com", &["only_one".into()], &[])` returns Err (parallel-vec length mismatch).
    - Test: `mod_site_name("NexusMods")` returns the exact name() string from `ModSite::NexusMods.name()`.
    - Test: `mod_site_base_url("NexusMods")` returns a string starting with "https://".
    - Test: `mod_site_game_url("NexusMods", "Fallout4")` returns a non-empty URL (exact form depends on core).
    - Test: `mod_site_name("InvalidSite")` returns "" (fail-soft on unknown discriminant).
  </behavior>

  <action>
  Create the file `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs`.

  Step 1 — Read `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` end-to-end. Note the EXACT ModSite variant names (research says NexusMods, BethesdaNet, ModDB but verify by direct read).

  Step 2 — Write the file:

  ```rust
  //! Web bridge for CXX FFI.
  //!
  //! Bridges `classic-web-core` URL helpers, user-agent helpers, and the
  //! `ModSite` enum so C++ frontends can build canonical mod-site URLs and
  //! validate user-supplied URLs without hardcoding strings.
  //!
  //! Per D-04 and D-07, `ModSite` is a CXX shared enum. Per RESEARCH.md
  //! "Open Question 4", `mod_site_game_url` takes a string game-id discriminant
  //! to avoid referencing `classic::constants::GameId` from a separate bridge
  //! module.

  use classic_constants_core::GameId;
  use classic_web_core::{
      build_url_with_query as core_build_url_with_query,
      extract_domain as core_extract_domain,
      get_user_agent as core_get_user_agent,
      get_user_agent_with_suffix as core_get_user_agent_with_suffix,
      is_valid_url as core_is_valid_url,
      join_url as core_join_url,
      validate_url as core_validate_url,
      ModSite,
  };

  // ─────────────────────────────────────────────────────────────────────
  // URL helpers
  // ─────────────────────────────────────────────────────────────────────

  fn is_valid_url(url_str: &str) -> bool {
      core_is_valid_url(url_str)
  }

  fn validate_url_string(url_str: &str) -> Result<(), String> {
      core_validate_url(url_str).map_err(|e| e.to_string())
  }

  fn extract_domain_string(url_str: &str) -> Result<String, String> {
      core_extract_domain(url_str).map_err(|e| e.to_string())
  }

  fn web_join_url(base: &str, path: &str) -> Result<String, String> {
      core_join_url(base, path).map_err(|e| e.to_string())
  }

  fn web_build_url_with_query(
      base: &str,
      keys: &[String],
      values: &[String],
  ) -> Result<String, String> {
      if keys.len() != values.len() {
          return Err(format!(
              "build_url_with_query: keys.len() ({}) != values.len() ({})",
              keys.len(),
              values.len()
          ));
      }
      let params: Vec<(&str, &str)> = keys
          .iter()
          .zip(values.iter())
          .map(|(k, v)| (k.as_str(), v.as_str()))
          .collect();
      core_build_url_with_query(base, &params).map_err(|e| e.to_string())
  }

  // ─────────────────────────────────────────────────────────────────────
  // User-agent helpers
  // ─────────────────────────────────────────────────────────────────────

  fn web_get_user_agent() -> String {
      core_get_user_agent()
  }

  fn web_get_user_agent_with_suffix(suffix: &str) -> String {
      core_get_user_agent_with_suffix(suffix)
  }

  // ─────────────────────────────────────────────────────────────────────
  // ModSite helpers — string-based dispatch (Open Question 4 resolution)
  // ─────────────────────────────────────────────────────────────────────

  fn mod_site_from_str(name: &str) -> Option<ModSite> {
      match name {
          "NexusMods" => Some(ModSite::NexusMods),
          "BethesdaNet" => Some(ModSite::BethesdaNet),
          "ModDB" => Some(ModSite::ModDB),
          _ => None,
      }
  }

  fn game_id_from_str(name: &str) -> Option<GameId> {
      match name {
          "Fallout4" => Some(GameId::Fallout4),
          "Fallout4VR" => Some(GameId::Fallout4VR),
          "Skyrim" => Some(GameId::Skyrim),
          "Starfield" => Some(GameId::Starfield),
          _ => None,
      }
  }

  fn mod_site_base_url(site_name: &str) -> String {
      mod_site_from_str(site_name)
          .map(|s| s.base_url().to_string())
          .unwrap_or_default()
  }

  fn mod_site_name(site_name: &str) -> String {
      mod_site_from_str(site_name)
          .map(|s| s.name().to_string())
          .unwrap_or_default()
  }

  fn mod_site_game_url(site_name: &str, game_id_str: &str) -> String {
      let Some(site) = mod_site_from_str(site_name) else {
          return String::new();
      };
      let Some(game_id) = game_id_from_str(game_id_str) else {
          return String::new();
      };
      site.game_url(game_id)
  }

  // ─────────────────────────────────────────────────────────────────────
  // CXX bridge block — D-04 shared enum + extern "Rust" helper fns
  // ─────────────────────────────────────────────────────────────────────

  #[cxx::bridge(namespace = "classic::web")]
  mod ffi {
      #[repr(u8)]
      enum ModSite {
          NexusMods = 0,
          BethesdaNet = 1,
          ModDB = 2,
      }

      extern "Rust" {
          // URL validation
          fn is_valid_url(url_str: &str) -> bool;
          fn validate_url_string(url_str: &str) -> Result<()>;
          fn extract_domain_string(url_str: &str) -> Result<String>;
          fn web_join_url(base: &str, path: &str) -> Result<String>;
          fn web_build_url_with_query(
              base: &str,
              keys: &[String],
              values: &[String],
          ) -> Result<String>;

          // User-agent
          fn web_get_user_agent() -> String;
          fn web_get_user_agent_with_suffix(suffix: &str) -> String;

          // ModSite methods (string dispatch)
          fn mod_site_base_url(site_name: &str) -> String;
          fn mod_site_name(site_name: &str) -> String;
          fn mod_site_game_url(site_name: &str, game_id_str: &str) -> String;
      }
  }

  #[cfg(test)]
  mod tests {
      use super::*;

      #[test]
      fn test_is_valid_url_true_for_https() {
          assert!(is_valid_url("https://nexusmods.com"));
      }
      #[test]
      fn test_is_valid_url_false_for_garbage() {
          assert!(!is_valid_url("not-a-url"));
      }
      #[test]
      fn test_validate_url_string_ok() {
          assert!(validate_url_string("https://nexusmods.com").is_ok());
      }
      #[test]
      fn test_validate_url_string_err() {
          assert!(validate_url_string("garbage").is_err());
      }
      #[test]
      fn test_extract_domain_string() {
          let result = extract_domain_string("https://nexusmods.com/games/fallout4");
          assert!(result.is_ok());
          assert!(result.unwrap().contains("nexusmods.com"));
      }
      #[test]
      fn test_get_user_agent_nonempty() {
          assert!(!web_get_user_agent().is_empty());
      }
      #[test]
      fn test_get_user_agent_with_suffix_contains_suffix() {
          let ua = web_get_user_agent_with_suffix("test-suffix-xyz");
          assert!(ua.contains("test-suffix-xyz"));
      }
      #[test]
      fn test_build_url_with_query_two_pairs() {
          let result = web_build_url_with_query(
              "https://example.com",
              &["a".to_string(), "b".to_string()],
              &["1".to_string(), "2".to_string()],
          );
          assert!(result.is_ok());
          let url = result.unwrap();
          assert!(url.contains("a=1"));
          assert!(url.contains("b=2"));
      }
      #[test]
      fn test_build_url_with_query_length_mismatch_returns_err() {
          let result = web_build_url_with_query(
              "https://example.com",
              &["only_one".to_string()],
              &[],
          );
          assert!(result.is_err());
      }
      #[test]
      fn test_mod_site_base_url_known() {
          let url = mod_site_base_url("NexusMods");
          assert!(url.starts_with("https://"));
      }
      #[test]
      fn test_mod_site_base_url_unknown_returns_empty() {
          assert_eq!(mod_site_base_url("InvalidSite"), "");
      }
      #[test]
      fn test_mod_site_name_known() {
          assert_eq!(mod_site_name("NexusMods"), ModSite::NexusMods.name());
      }
      #[test]
      fn test_mod_site_game_url_nonempty_for_valid_pair() {
          let url = mod_site_game_url("NexusMods", "Fallout4");
          assert!(!url.is_empty());
      }
      #[test]
      fn test_mod_site_game_url_empty_for_invalid_site() {
          assert_eq!(mod_site_game_url("InvalidSite", "Fallout4"), "");
      }
      #[test]
      fn test_mod_site_game_url_empty_for_invalid_game() {
          assert_eq!(mod_site_game_url("NexusMods", "InvalidGame"), "");
      }
  }
  ```

  Step 3 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` and confirm all 14 tests pass.

  IMPORTANT: If `classic-web-core` or `classic-constants-core` is not in `classic-cpp-bridge/Cargo.toml`, add it as a workspace dependency: `classic-web-core = { workspace = true }`. Verify the workspace `Cargo.toml` lists it; add if missing.

  IMPORTANT: If the actual ModSite variant names differ from `NexusMods/BethesdaNet/ModDB`, update both the `mod_site_from_str` match arms AND the bridge enum block.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests</automated>
  </verify>

  <acceptance_criteria>
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` exists
    - `git grep -n 'namespace = "classic::web"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns one match
    - `git grep -n 'enum ModSite' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns the bridge enum declaration
    - `git grep -nE 'fn (is_valid_url|validate_url_string|extract_domain_string|web_get_user_agent|web_join_url|web_build_url_with_query|mod_site_base_url|mod_site_name|mod_site_game_url)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns at least 9 wrapper definitions plus 9 extern declarations
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` exits 0 with at least 14 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/web.rs` exists with all CXXS-02 helpers, ModSite as a CXX shared enum, and every bridge fn has a passing Rust-side test.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire web.rs into build.rs + lib.rs, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current bridges array — add `"src/web.rs"` after constants.rs OR near the start; web.rs uses string discriminants so cross-module ordering doesn't matter, but listing it consistently with constants.rs keeps the layout predictable)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (add `pub mod web;` under `#[cfg(windows)]` alphabetically — likely between `pub mod update;` and `pub mod yaml;`)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09, D-10
    - .planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md row 2-03-01
  </read_first>

  <action>
  ## Part A — Add to build.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`. Insert `"src/web.rs",` into the `cxx_build::bridges([...])` array. A safe location is near the end (right before `"src/markdown.rs"`) or anywhere after the foundation modules — since `web.rs` doesn't reference shared types from other bridge modules, ordering is not critical.

  ## Part B — Add to lib.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`. Insert under `#[cfg(windows)]`:

  ```rust
  #[cfg(windows)]
  pub mod web;
  ```

  Place it alphabetically (between `pub mod update;` and `pub mod yaml;`).

  ## Part C — Mandatory D-10 clean-build pair

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0.

  Confirm the generated header appears:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/web.h
  ```

  ## Part D — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part E — Atomic commit

  Stage all 7 files (the new `web.rs`, `build.rs`, `lib.rs`, plus the 4 baseline artifacts). Commit message: `Feat(02-03): expose classic-web-core via classic::web CXX bridge` — body mentions CXXS-02, D-04, D-07, D-09, D-10.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/web.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the bridges array
    - `git grep -n 'pub mod web' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/web.h` exists
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "web"` for the ModSite shared enum and all 10 bridge fns
    - `git log -1 --stat` shows the commit touches Rust source AND `docs/implementation/cxx_api_parity/baseline/*` (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-03 complete — `classic::web` is a first-class CXX bridge module locked in the parity contract, both clean builds pass, CXXS-02 satisfied.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` — exits 0
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` — exits 0
4. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 drift
5. Generated header `include/classic_cxx_bridge/web.h` exists

Validation Architecture (per 02-VALIDATION.md row 2-03-01): `cargo test -p classic-cpp-bridge web::tests` + clean-build pair + parity gate.
</verification>

<success_criteria>
- src/web.rs exists with #[cxx::bridge(namespace = "classic::web")] and exposes ModSite as CXX shared enum + 10 bridge fns
- All helper bridge fns are tested and pass (14+ tests)
- Both clean MSVC builds are green (D-10)
- Parity gate at 0 drift after --update-baseline (D-09)
- All changes committed atomically
- D-11 N/A: first-time exposure of classic-web-core, no narrowed call sites to migrate
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-03-SUMMARY.md` documenting:
- Exact ModSite variant names found in classic-web-core
- Entries added to the parity contract (count of fns, count of enum variants)
- D-10 clean-build outcome
- Note on D-11 N/A status (first-time exposure)
</output>