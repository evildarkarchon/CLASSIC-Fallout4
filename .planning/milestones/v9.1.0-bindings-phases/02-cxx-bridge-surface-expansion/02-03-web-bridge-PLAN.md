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
  - classic-gui/src/workers/updateworker.cpp
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
    - "ModSite is exposed as a CXX shared enum (D-04 / D-07) with the exact 3 variants from classic-web-core (NexusMods, BethesdaNet, ModDB)"
    - "ModSite-taking helper fns use the SHARED ENUM directly — NOT raw strings (Codex review MEDIUM correction)"
    - "URL helpers (is_valid_url, validate_url, extract_domain, get_user_agent, get_user_agent_with_suffix, join_url, build_url_with_query) are bridged"
    - "validate_url returns the normalized URL string on success (preserving canonicalization), not just bool — Codex review MEDIUM correction"
    - "src/web.rs is in build.rs::cxx_build::bridges and lib.rs declares pub mod web"
    - "Both build_cli.ps1 -Clean -Test and build_gui.ps1 -Clean -Test exit 0 (D-10)"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift after --update-baseline"
    - "classic-gui/src/workers/updateworker.cpp uses classic::web::get_user_agent or another classic::web::* helper in production C++ — D-11 consumer migration (Codex review MEDIUM correction)"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs"
      provides: "New CXX bridge module exposing classic-web-core URL/user-agent/mod-site helpers (CXXS-02)"
      min_lines: 130
      contains: "namespace = \"classic::web\""
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs"
      provides: "Bridges array now includes \"src/web.rs\""
      contains: "src/web.rs"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs"
      provides: "pub mod web declaration under #[cfg(windows)]"
      contains: "pub mod web"
    - path: "classic-gui/src/workers/updateworker.cpp"
      provides: "D-11 consumer — calls classic::web::get_user_agent (or another classic::web::* fn) in the existing GitHub check flow"
      contains: "classic::web"
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
    - from: "classic-gui/src/workers/updateworker.cpp"
      to: "classic_cxx_bridge/web.h"
      via: "C++ #include + classic::web::get_user_agent call"
      pattern: "classic::web::"
---

<objective>
Create a brand-new CXX bridge module `src/web.rs` exposing `classic-web-core` (CXXS-02). Per D-04, declares `ModSite` as a CXX shared enum AND uses it directly (not via string dispatch) for ModSite-taking helpers. Bridges all URL helpers, user-agent helpers, and ModSite methods. Adds the file to `build.rs` and runs the mandatory D-10 clean-build pair. Adds at least one D-11 consumer migration in `classic-gui/src/workers/updateworker.cpp`.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan used string-based dispatch for `mod_site_*(site_name: &str, ...)` helpers, giving up the type safety that the bridge ModSite shared enum was supposed to provide. The Codex review correctly noted this creates invalid-input states that don't exist in Rust. This plan now uses the shared `ModSite` enum directly. For `mod_site_game_url`, the GameId is also passed as a CXX shared enum (declared as a SECOND shared enum in `web.rs` to avoid cross-module references — same variant set as `classic::constants::GameId`, but a separate type per the per-bridge-module shared-enum scoping rule).

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan defined `validate_url_string(url) -> Result<()>`, collapsing `classic-web-core::validate_url`'s parsed `Url` return value to a bool/error. The Codex review correctly noted this loses canonicalization. This plan now defines `validate_url_string(url) -> Result<String>` returning the normalized URL string on success.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan treated D-11 as N/A. This plan adds a real consumer migration in `updateworker.cpp` where the existing `github_check_for_updates` call is paired with `classic::web::get_user_agent()` (used in a logging or pre-call diagnostic line, since the actual user-agent string used by the GitHub HTTP client lives inside the Rust core).

Purpose: First-time exposure of `classic-web-core` to C++ frontends. Independent of `constants.rs` (no shared types cross the module boundary), so this plan can run in parallel with Plan 02-02 in Wave 1.

Output: New `src/web.rs` with bridged URL/user-agent/mod-site helpers using typed enums; `build.rs` and `lib.rs` updated; updateworker.cpp exercises the new namespace; both clean MSVC builds green; refreshed parity baseline committed atomically.
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

# Source of truth — what classic-web-core exposes
@ClassicLib-rs/business-logic/classic-web-core/src/lib.rs

# Source of truth — GameId for the second shared enum
@ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs

# Reference patterns
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs

# Files this plan modifies
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs

# D-11 consumer migration site
@classic-gui/src/workers/updateworker.cpp

# Parity gate
@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- classic-web-core public surface (per RESEARCH.md §"classic-web-core" + direct read). -->

```rust
pub fn validate_url(url_str: &str) -> Result<Url, WebError>;  // returns parsed Url on success
pub fn is_valid_url(url_str: &str) -> bool;
pub fn extract_domain(url_str: &str) -> Result<String, WebError>;
pub fn get_user_agent() -> String;
pub fn get_user_agent_with_suffix(suffix: &str) -> String;
pub fn join_url(base: &str, path: &str) -> Result<String, WebError>;
pub fn build_url_with_query(base: &str, params: &[(&str, &str)]) -> Result<String, WebError>;

pub enum ModSite { NexusMods, BethesdaNet, ModDB }
impl ModSite {
    pub fn base_url(&self) -> &'static str;
    pub fn name(&self) -> &'static str;
    pub fn game_url(&self, game_id: GameId) -> String;
}
```

CXX bridging strategy (Codex review MEDIUM corrections):
- Declare `ModSite` as a CXX shared enum INSIDE `#[cxx::bridge(namespace = "classic::web")]`
- Declare `WebGameId` as a SECOND CXX shared enum in the SAME bridge block (mirrors `classic::constants::GameId` but is a separate type — CXX shared enums don't cross bridge module boundaries cleanly)
- For ModSite methods, the bridge fns take the **shared enum directly** — `mod_site_base_url(site: ModSite) -> String`, NOT `mod_site_base_url(site_name: &str)`
- For `mod_site_game_url`, take both shared enums: `mod_site_game_url(site: ModSite, game: WebGameId) -> String`
- For `validate_url_string`, return `Result<String>` (the normalized URL on success) — preserves canonicalization per Codex MEDIUM correction
- For `build_url_with_query`, the `&[(&str, &str)]` slice-of-tuples is NOT CXX-bridgeable. Take two parallel `&[String]` vectors (keys + values).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create src/web.rs with shared ModSite + WebGameId enums (NOT string dispatch) + URL helpers + Result<String> validate + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-web-core/src/lib.rs (READ ENTIRELY — confirm exact ModSite variant names; confirm validate_url ACTUAL return type is Result<Url, _> not Result<(), _>; confirm is_valid_url / extract_domain / get_user_agent / get_user_agent_with_suffix / join_url / build_url_with_query signatures; confirm ModSite::base_url / name / game_url method names)
    - ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs (only read GameId enum — needed because `ModSite::game_url()` takes a `GameId`)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (template for single-purpose bridge module with #[cfg(test)] mod tests)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs (template — extern "Rust" Result<T> declarations and slice parameters)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 03" (the MEDIUM concerns about string dispatch and validate_url collapsing)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-web-core" §"Pattern: build_url_with_query key/value parallel vectors"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-04, D-07 (CXX shared enums for ModSite + GameId), D-12 (Rust-side tests)
  </read_first>

  <behavior>
    - Test: `is_valid_url("https://nexusmods.com")` returns true.
    - Test: `is_valid_url("not-a-url")` returns false.
    - Test: `validate_url_string("https://nexusmods.com")` returns Ok with a normalized URL string (e.g., "https://nexusmods.com/").
    - Test: `validate_url_string("garbage")` returns Err with non-empty message.
    - Test: `extract_domain_string("https://nexusmods.com/games/fallout4")` returns Ok("nexusmods.com").
    - Test: `web_get_user_agent()` returns a non-empty string.
    - Test: `web_get_user_agent_with_suffix("test-suffix")` returns a string CONTAINING "test-suffix".
    - Test: `web_join_url("https://example.com", "path")` returns Ok with a URL containing "/path".
    - Test: `web_build_url_with_query("https://example.com", &["a","b"], &["1","2"])` returns Ok with a query string containing both `a=1` and `b=2`.
    - Test: `web_build_url_with_query("https://example.com", &["only_one"], &[])` returns Err (parallel-vec length mismatch).
    - Test: `mod_site_name(ffi::ModSite::NexusMods)` returns the exact string from `ModSite::NexusMods.name()`.
    - Test: `mod_site_base_url(ffi::ModSite::NexusMods)` returns a string starting with "https://".
    - Test: `mod_site_game_url(ffi::ModSite::NexusMods, ffi::WebGameId::Fallout4)` returns a non-empty URL.
    - Test: All ModSite variants × all WebGameId variants — enumerate the matrix and verify no panics, all returns are non-empty strings.
  </behavior>

  <action>
  Create the file `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs`.

  Step 1 — Read `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` end-to-end. CONFIRM:
  - ModSite variant names: `NexusMods`, `BethesdaNet`, `ModDB`
  - `validate_url` ACTUAL return type — likely `Result<Url, WebError>` (NOT `Result<()>`); the bridge wrapper preserves the canonicalized URL string

  Step 2 — Write the file:

  ```rust
  //! Web bridge for CXX FFI.
  //!
  //! Bridges `classic-web-core` URL helpers, user-agent helpers, and the
  //! `ModSite` enum so C++ frontends can build canonical mod-site URLs and
  //! validate user-supplied URLs without hardcoding strings.
  //!
  //! Per D-04 and D-07, `ModSite` and `WebGameId` are CXX shared enums declared
  //! INSIDE this bridge block. The Codex review (MEDIUM) corrected an earlier
  //! string-dispatch design — bridge fns now take the typed enums directly.
  //!
  //! Note on cross-module shared enums: CXX shared enums don't share across
  //! `#[cxx::bridge]` modules. `WebGameId` here mirrors the variant set of
  //! `classic::constants::GameId` but is a separate CXX type. C++ callers
  //! that have a `classic::constants::GameId` value translate via the value
  //! (both enums use the same `#[repr(u8)]` discriminants).

  use classic_constants_core::GameId as CoreGameId;
  use classic_web_core::{
      build_url_with_query as core_build_url_with_query,
      extract_domain as core_extract_domain,
      get_user_agent as core_get_user_agent,
      get_user_agent_with_suffix as core_get_user_agent_with_suffix,
      is_valid_url as core_is_valid_url,
      join_url as core_join_url,
      validate_url as core_validate_url,
      ModSite as CoreModSite,
  };

  // ─────────────────────────────────────────────────────────────────────
  // Enum mappers (Codex MEDIUM correction: typed enums, not string dispatch)
  // ─────────────────────────────────────────────────────────────────────

  fn from_bridge_mod_site(site: ffi::ModSite) -> CoreModSite {
      match site {
          ffi::ModSite::NexusMods => CoreModSite::NexusMods,
          ffi::ModSite::BethesdaNet => CoreModSite::BethesdaNet,
          ffi::ModSite::ModDB => CoreModSite::ModDB,
          _ => CoreModSite::NexusMods,
      }
  }

  fn from_bridge_web_game_id(g: ffi::WebGameId) -> CoreGameId {
      match g {
          ffi::WebGameId::Fallout4 => CoreGameId::Fallout4,
          ffi::WebGameId::Fallout4VR => CoreGameId::Fallout4VR,
          ffi::WebGameId::Skyrim => CoreGameId::Skyrim,
          ffi::WebGameId::Starfield => CoreGameId::Starfield,
          _ => CoreGameId::Fallout4,
      }
  }

  // ─────────────────────────────────────────────────────────────────────
  // URL helpers
  // ─────────────────────────────────────────────────────────────────────

  fn is_valid_url(url_str: &str) -> bool {
      core_is_valid_url(url_str)
  }

  // Codex MEDIUM correction: return the canonicalized URL string on success
  // (preserves Url::parse normalization), not Result<()>.
  fn validate_url_string(url_str: &str) -> Result<String, String> {
      core_validate_url(url_str)
          .map(|url| url.to_string())  // Url -> normalized String
          .map_err(|e| e.to_string())
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
  // ModSite helpers — TYPED ENUM dispatch (Codex MEDIUM correction)
  // ─────────────────────────────────────────────────────────────────────

  fn mod_site_base_url(site: ffi::ModSite) -> String {
      from_bridge_mod_site(site).base_url().to_string()
  }

  fn mod_site_name(site: ffi::ModSite) -> String {
      from_bridge_mod_site(site).name().to_string()
  }

  fn mod_site_game_url(site: ffi::ModSite, game: ffi::WebGameId) -> String {
      from_bridge_mod_site(site).game_url(from_bridge_web_game_id(game))
  }

  // ─────────────────────────────────────────────────────────────────────
  // CXX bridge block — D-04 shared enums + extern "Rust" helper fns
  // ─────────────────────────────────────────────────────────────────────

  #[cxx::bridge(namespace = "classic::web")]
  mod ffi {
      #[repr(u8)]
      enum ModSite {
          NexusMods = 0,
          BethesdaNet = 1,
          ModDB = 2,
      }

      // Mirrors classic::constants::GameId variant set; declared separately
      // because CXX shared enums don't cross bridge module boundaries.
      // Discriminant values match classic::constants::GameId so C++ callers
      // can `static_cast` between the two if needed.
      #[repr(u8)]
      enum WebGameId {
          Fallout4 = 0,
          Fallout4VR = 1,
          Skyrim = 2,
          Starfield = 3,
      }

      extern "Rust" {
          // URL validation
          fn is_valid_url(url_str: &str) -> bool;
          // Returns the canonicalized URL string on success (preserves Url::parse normalization)
          fn validate_url_string(url_str: &str) -> Result<String>;
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

          // ModSite methods (TYPED enum dispatch — Codex MEDIUM correction)
          fn mod_site_base_url(site: ModSite) -> String;
          fn mod_site_name(site: ModSite) -> String;
          fn mod_site_game_url(site: ModSite, game: WebGameId) -> String;
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
      fn test_validate_url_string_returns_canonicalized() {
          let result = validate_url_string("https://nexusmods.com");
          assert!(result.is_ok());
          let normalized = result.unwrap();
          assert!(normalized.starts_with("https://nexusmods.com"));
      }
      #[test]
      fn test_validate_url_string_err_for_garbage() {
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
      fn test_mod_site_base_url_typed_enum() {
          // Codex MEDIUM correction: typed enum dispatch, not string
          let url = mod_site_base_url(ffi::ModSite::NexusMods);
          assert!(url.starts_with("https://"));
          assert_eq!(url, CoreModSite::NexusMods.base_url());
      }
      #[test]
      fn test_mod_site_name_typed_enum_all_variants() {
          let pairs = [
              (ffi::ModSite::NexusMods, CoreModSite::NexusMods),
              (ffi::ModSite::BethesdaNet, CoreModSite::BethesdaNet),
              (ffi::ModSite::ModDB, CoreModSite::ModDB),
          ];
          for (bridge, core) in pairs {
              assert_eq!(mod_site_name(bridge), core.name());
          }
      }
      #[test]
      fn test_mod_site_game_url_typed_enums_all_combinations() {
          // Cross-product: 3 ModSites × 4 GameIds = 12 calls, all non-empty, no panics
          for site in [
              ffi::ModSite::NexusMods,
              ffi::ModSite::BethesdaNet,
              ffi::ModSite::ModDB,
          ] {
              for game in [
                  ffi::WebGameId::Fallout4,
                  ffi::WebGameId::Fallout4VR,
                  ffi::WebGameId::Skyrim,
                  ffi::WebGameId::Starfield,
              ] {
                  let url = mod_site_game_url(site, game);
                  assert!(!url.is_empty(), "mod_site_game_url returned empty for site/game combination");
              }
          }
      }
  }
  ```

  Step 3 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` and confirm all 12+ tests pass.

  IMPORTANT: If `classic-web-core` or `classic-constants-core` is not in `classic-cpp-bridge/Cargo.toml`, add as workspace dependencies.

  IMPORTANT: If the actual ModSite variant names differ from `NexusMods/BethesdaNet/ModDB`, update both the bridge enum block AND the `from_bridge_mod_site` match arms. The Codex review confirmed the variant set; verify by direct read.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests</automated>
  </verify>

  <acceptance_criteria>
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` exists
    - `git grep -n 'namespace = "classic::web"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns one match
    - `git grep -n 'enum ModSite' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns the bridge enum declaration
    - `git grep -n 'enum WebGameId' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns the second bridge enum declaration
    - `git grep -n 'fn mod_site_base_url(site: ModSite)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns the typed-enum signature (NOT a `&str` parameter — Codex MEDIUM correction)
    - `git grep -n 'fn mod_site_game_url(site: ModSite, game: WebGameId)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns the dual-typed-enum signature
    - `git grep -n 'fn validate_url_string' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` shows it returns `Result<String>` not `Result<()>` (Codex MEDIUM correction — preserves canonicalization)
    - `git grep -n 'mod_site_from_str\|game_id_from_str' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` returns NOTHING (the string-dispatch helpers are gone)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` exits 0 with at least 12 passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/web.rs` exists with all CXXS-02 helpers, ModSite + WebGameId as CXX shared enums dispatched directly (no string fallback), validate_url_string returns the canonicalized URL, every bridge fn has a passing Rust-side test.
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire web.rs into build.rs + lib.rs, add D-11 consumer migration in updateworker.cpp, run D-10 clean-build pair, refresh D-09 baseline, commit</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-gui/src/workers/updateworker.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs (current bridges array)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs (add `pub mod web;` under `#[cfg(windows)]` alphabetically)
    - classic-gui/src/workers/updateworker.cpp (the existing checkForUpdates flow that calls classic::update::github_check_for_updates — D-11 target)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09, D-10, D-11
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 03" MEDIUM concern about D-11
    - .planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md row 2-03-01
  </read_first>

  <action>
  ## Part A — Add to build.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`. Insert `"src/web.rs",` into the `cxx_build::bridges([...])` array. A safe location is near the end (right before `"src/markdown.rs"`) or anywhere after the foundation modules.

  ## Part B — Add to lib.rs

  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`. Insert under `#[cfg(windows)]`:

  ```rust
  #[cfg(windows)]
  pub mod web;
  ```

  Place it alphabetically (between `pub mod update;` and `pub mod yaml;`).

  ## Part C — D-11 consumer migration in updateworker.cpp (Codex review correction)

  Edit `classic-gui/src/workers/updateworker.cpp`. Add `#include "classic_cxx_bridge/web.h"` next to the existing `#include "classic_cxx_bridge/update.h"`.

  In the existing `checkForUpdates` method body, BEFORE the `classic::update::github_check_for_updates` call, add a one-line use of `classic::web::get_user_agent()` so the bridge fn is exercised by production code. The simplest pattern:

  ```cpp
  #include "classic_cxx_bridge/web.h"

  void UpdateWorker::checkForUpdates(const QString& currentVersion)
  {
      try {
          // D-11 / CXXS-02 consumer migration: classic::web::get_user_agent
          // is called here so the new bridge namespace is exercised in
          // production C++. The user-agent string returned is the same one
          // the underlying GitHub HTTP client uses internally; logging it
          // here gives users visibility into the request signature without
          // duplicating the HTTP layer in C++.
          auto user_agent = classic::web::web_get_user_agent();
          qDebug() << "Update check user-agent:"
                   << QString::fromUtf8(user_agent.data(), static_cast<int>(user_agent.size()));

          auto result = classic::update::github_check_for_updates(
              "evildarkarchon",
              "CLASSIC-Fallout4",
              classic::toRustString(currentVersion));
          // ... rest unchanged
      }
      // ... catch blocks unchanged
  }
  ```

  Add `#include <QDebug>` if not already present.

  Run `git grep -n 'classic::web' classic-gui/src/workers/updateworker.cpp` and confirm at least one match.

  ## Part D — Mandatory D-10 clean-build pair

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test
  ```

  Both must exit 0.

  Confirm the generated header appears:
  ```
  ls ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/web.h
  ```

  ## Part E — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part F — Atomic commit

  Stage all 8 files (the new `web.rs`, `build.rs`, `lib.rs`, `updateworker.cpp`, plus the 4 baseline artifacts). Commit message: `Feat(02-03): expose classic-web-core via classic::web CXX bridge` — body mentions CXXS-02, D-04, D-07, D-09, D-10, D-11 and notes the updateworker.cpp consumer migration.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n '"src/web.rs"' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` returns exactly one line inside the bridges array
    - `git grep -n 'pub mod web' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` returns the new declaration
    - `git grep -n 'classic::web' classic-gui/src/workers/updateworker.cpp` returns at least one line (D-11 consumer)
    - `git grep -n '#include "classic_cxx_bridge/web.h"' classic-gui/src/workers/updateworker.cpp` returns the new include
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` exits 0
    - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/web.h` exists
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "web"` for the ModSite + WebGameId shared enums and all 10 bridge fns
    - `git log -1 --stat` shows the commit touches Rust source AND updateworker.cpp AND `docs/implementation/cxx_api_parity/baseline/*` (D-09 atomicity)
  </acceptance_criteria>

  <done>
    Plan 02-03 complete — `classic::web` is a first-class CXX bridge module with typed-enum dispatch (no string fallback), validate_url_string returns canonicalized URLs, updateworker.cpp exercises the new namespace, both clean builds pass, CXXS-02 satisfied.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml web::tests` — exits 0
2. `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` — exits 0
3. `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test` — exits 0
4. `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 drift
5. Generated header `include/classic_cxx_bridge/web.h` exists
6. updateworker.cpp has the D-11 consumer migration

Validation Architecture (per 02-VALIDATION.md row 2-03-01): `cargo test -p classic-cpp-bridge web::tests` + clean-build pair + parity gate + D-11 consumer.
</verification>

<success_criteria>
- src/web.rs exists with #[cxx::bridge(namespace = "classic::web")] exposing ModSite AND WebGameId as CXX shared enums + 10 bridge fns using TYPED dispatch (Codex MEDIUM correction)
- validate_url_string returns Result<String> with the canonicalized URL on success (Codex MEDIUM correction — preserves Url::parse normalization)
- All helper bridge fns are tested and pass (12+ tests)
- updateworker.cpp has at least one classic::web::* call site (D-11 consumer migration — Codex MEDIUM correction)
- Both clean MSVC builds are green (D-10)
- Parity gate at 0 drift after --update-baseline (D-09)
- All changes committed atomically
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-03-SUMMARY.md` documenting:
- Confirmation that ModSite + WebGameId use typed enum dispatch (Codex MEDIUM correction — no string fallback)
- Confirmation that validate_url_string returns Result<String> (Codex MEDIUM correction — canonicalization preserved)
- Confirmation that updateworker.cpp has D-11 consumer migration (Codex MEDIUM correction)
- Exact ModSite variant names found in classic-web-core
- Entries added to the parity contract (count of fns, count of enum variants — including the second WebGameId enum)
- D-10 clean-build outcome
</output>
