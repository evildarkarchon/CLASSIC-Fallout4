---
phase: quick-260407-rvj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs
  - ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
  - ClassicLib-rs/ui-applications/classic-tui/src/app.rs
  - ClassicLib-rs/ui-applications/classic-tui/Cargo.toml
  - ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
  - ClassicLib-rs/node-bindings/classic-node/src/path.rs
  - ClassicLib-rs/node-bindings/classic-node/index.d.ts
  - docs/api/classic-path-core.md
  - docs/api/classic-cpp-bridge-game-entrypoints.md
autonomous: true
requirements:
  - DOCSPATH-STEAMID-OPT-IN-01
must_haves:
  truths:
    - "DocsPathFinder::new() constructs a finder with steam_app_id = None and performs NO Proton lookup on Linux unless the caller opts in via with_steam_app_id."
    - "A generic consumer of the DocsPathFinder Python or Node API on Linux that passes only `relative_path` no longer implicitly probes Fallout 4's compatdata/377160 Proton prefix; it goes straight to ~/.local/share/<relative_path>."
    - "A consumer that DOES want FO4 Proton behavior opts in by calling with_steam_app_id(377160) (Rust) / set_steam_app_id(377160) (binding) and then sees the existing Proton-first-then-local-share ordering."
    - "The CXX bridge detect_fallout4_docs_path chains .with_steam_app_id(Fallout4Version::Original.steam_app_id()) so the Qt GUI's Fallout 4 docs detection behavior on Linux is byte-identical to before this change."
    - "The TUI resolve_xse_folder_for_scan chains .with_steam_app_id(Fallout4Version::Original.steam_app_id()) so its Linux Proton fallback is byte-identical to before this change."
    - "The literal 377160 no longer appears in classic-path-core/src/docs_path.rs; the canonical source is Fallout4Version::steam_app_id() in classic-constants-core."
    - "All 4 pre-existing tests in linux_proton_docs_path.rs still pass after being updated to chain .with_steam_app_id(377160)."
    - "A new test proton_path_ignored_when_steam_app_id_unset asserts that when BOTH a valid Proton FO4 docs dir AND a valid local-share docs dir exist, a DocsPathFinder with no Steam ID set returns the local-share path."
    - "The Python parity gate (tools/python_api_parity/check_parity_gate.py) passes."
    - "The Node parity gate (bun run parity:gate:local) passes."
    - "cargo test --workspace, cargo clippy -D warnings, and cargo fmt --check all pass on the Rust workspace."
  artifacts:
    - path: "ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs"
      provides: "DocsPathFinder with Option<u32> steam_app_id field, consuming with_steam_app_id builder, and steam-id-gated Proton lookup in find_docs_path_linux / find_docs_path_linux_with."
      contains: "with_steam_app_id"
    - path: "ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs"
      provides: "5 integration tests (4 updated + 1 new) proving the opt-in Linux Proton selection contract."
      contains: "proton_path_ignored_when_steam_app_id_unset"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs"
      provides: "detect_fallout4_docs_path chains .with_steam_app_id using Fallout4Version::Original.steam_app_id() from classic-constants-core."
      contains: "with_steam_app_id"
    - path: "ClassicLib-rs/ui-applications/classic-tui/src/app.rs"
      provides: "resolve_xse_folder_for_scan chains .with_steam_app_id using Fallout4Version::Original.steam_app_id()."
      contains: "with_steam_app_id"
    - path: "ClassicLib-rs/ui-applications/classic-tui/Cargo.toml"
      provides: "classic-constants-core added as a path dependency so app.rs can import Fallout4Version."
      contains: "classic-constants-core"
    - path: "ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs"
      provides: "DocsPathFinder PyO3 wrapper with new set_steam_app_id(app_id: u32) &mut self method, implemented via self.inner.clone().with_steam_app_id(app_id)."
      contains: "set_steam_app_id"
    - path: "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi"
      provides: "Type stub for DocsPathFinder.set_steam_app_id(app_id: int) -> None."
      contains: "set_steam_app_id"
    - path: "ClassicLib-rs/node-bindings/classic-node/src/path.rs"
      provides: "DocsPathFinder NAPI wrapper with new set_steam_app_id(app_id: u32) &mut self method."
      contains: "set_steam_app_id"
    - path: "ClassicLib-rs/node-bindings/classic-node/index.d.ts"
      provides: "REGENERATED (NOT hand-edited) TypeScript contract containing DocsPathFinder.setSteamAppId."
      contains: "setSteamAppId"
    - path: "docs/api/classic-path-core.md"
      provides: "DocsPathFinder docs updated to document the new with_steam_app_id opt-in and the changed Linux Proton behavior."
      contains: "with_steam_app_id"
    - path: "docs/api/classic-cpp-bridge-game-entrypoints.md"
      provides: "Bridge docs updated to note detect_fallout4_docs_path chains .with_steam_app_id for Fallout 4."
      contains: "with_steam_app_id"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs::detect_fallout4_docs_path"
      to: "classic_path_core::DocsPathFinder::with_steam_app_id"
      via: "chained builder call using classic_constants_core::Fallout4Version::Original.steam_app_id()"
      pattern: "with_steam_app_id\\("
    - from: "ClassicLib-rs/ui-applications/classic-tui/src/app.rs::resolve_xse_folder_for_scan"
      to: "classic_path_core::DocsPathFinder::with_steam_app_id"
      via: "chained builder call using classic_constants_core::Fallout4Version::Original.steam_app_id()"
      pattern: "with_steam_app_id\\("
    - from: "ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs::DocsPathFinder::set_steam_app_id"
      to: "classic_path_core::DocsPathFinder::with_steam_app_id"
      via: "self.inner.clone().with_steam_app_id(app_id) mutation of inner field"
      pattern: "self\\.inner\\.clone\\(\\)\\.with_steam_app_id"
    - from: "ClassicLib-rs/node-bindings/classic-node/src/path.rs::DocsPathFinder::set_steam_app_id"
      to: "classic_path_core::DocsPathFinder::with_steam_app_id"
      via: "self.inner.clone().with_steam_app_id(app_id) mutation of inner field"
      pattern: "self\\.inner\\.clone\\(\\)\\.with_steam_app_id"
---

<objective>
Make `classic_path_core::DocsPathFinder`'s Fallout-4-specific Steam App ID (377160)
opt-in instead of hard-coded, so that a non-FO4 consumer of the generic
`DocsPathFinder` API (for example a Skyrim user of the Python or Node binding on
Linux/Proton) no longer implicitly probes Fallout 4's `compatdata/377160` prefix
when searching for its own documents folder.

Purpose:
- Remove the `const FALLOUT_4_STEAM_APP_ID: u32 = 377160` from `docs_path.rs` and
  replace it with a `steam_app_id: Option<u32>` builder field (default `None`).
- Gate the Linux Proton lookup in both `find_docs_path_linux` and
  `find_docs_path_linux_with` on that field: if it's `None`, skip the Proton lookup
  entirely and go straight to `~/.local/share/<relative_path>`.
- Give internal Rust FO4 callers (CXX bridge `detect_fallout4_docs_path` and TUI
  `resolve_xse_folder_for_scan`) a one-line chained opt-in using
  `classic_constants_core::Fallout4Version::Original.steam_app_id()`, so the
  canonical 377160 literal lives in exactly one place in the whole codebase.
- Give binding consumers (Python + Node) a `set_steam_app_id` mutable setter on
  their `DocsPathFinder` wrappers so they can opt in too.

Output:
- An edited core crate + tests + 3 Rust consumer crates + 2 binding crates +
  2 docs files. Single atomic commit prefixed `Fix:`.
- Fully-green cargo workspace (tests + clippy -D warnings + fmt --check).
- Fully-green Python parity gate.
- Fully-green Node parity gate (`bun run build` regenerates `index.d.ts`, then
  `bun run parity:gate:local` validates against it).
- Docs pages under `docs/api/` updated per the AGENTS.md docs-sync rule.
- C++ frontends (`classic-cli`, `classic-gui`) NOT touched — they consume the
  bridge's `detect_fallout4_docs_path`, which after this fix already chains the
  right Steam ID internally.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@AGENTS.md
@docs/api/README.md

# Files the executor MUST read in full before editing
@ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs
@ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs
@ClassicLib-rs/business-logic/classic-path-core/Cargo.toml
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml
@ClassicLib-rs/ui-applications/classic-tui/src/app.rs
@ClassicLib-rs/ui-applications/classic-tui/Cargo.toml
@ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs
@ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
@ClassicLib-rs/node-bindings/classic-node/src/path.rs
@docs/api/classic-path-core.md
@docs/api/classic-cpp-bridge-game-entrypoints.md
@docs/api/game-setup-workflow.md

# Ground-truth reference (read targeted range only, do NOT modify)
@ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs
@ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs

<rules_in_force>
From CLAUDE.md (project):
- GSD Workflow Enforcement: this edit is happening under `/gsd:quick`, the required
  entry point for small fixes. Do NOT make freeform edits outside this plan.
- Commit Conventions: prefix the single commit with `Fix:` (capitalize the first
  word after the prefix).
- Never write to `nul` on Windows — creates an undeletable file on a system drive.
- Subdirectory rules apply: `classic-path-core` sits in the Rust workspace under
  `ClassicLib-rs/business-logic/`, which follows the workspace-level lint rules
  (`deprecated = "deny"`, `unsafe_code = "deny"`, `unused = "deny"`, `missing_docs = "warn"`).

From AGENTS.md (project, always-on rules):
- Rule #2 / #3: business logic lives in Rust; keep non-interface layers thin.
  The core behavior change lives in `classic-path-core`; the binding crates are
  intentionally thin wrappers that just clone-mutate `inner`.
- Rule #7 (docs-sync rule): "Consult `docs/api/README.md` before changing public
  Rust, bridge, GUI-consumer, or binding-facing APIs; if an API-breaking or
  contract-shaping change occurs, update the affected pages under `docs/api/` in
  the same change." This change touches `DocsPathFinder` public API shape, so
  `docs/api/classic-path-core.md` and `docs/api/classic-cpp-bridge-game-entrypoints.md`
  MUST be updated in the same commit. `docs/api/game-setup-workflow.md` is checked
  but only updated if it references DocsPathFinder construction (see Task 4 for
  the check).
- Rule #8: never run C++ tests by invoking raw `ctest` — use the PowerShell
  wrappers. No C++ tests are in scope here, so this rule does not directly apply,
  but no raw ctest in the verify blocks either.

From global user CLAUDE.md:
- Prefer PowerShell over Bash for command execution. ALL cargo / bun / python
  verification commands in the verify blocks MUST be run through the PowerShell
  tool. Do not use the Bash tool unless absolutely necessary.
- No emojis anywhere (code, plan, commit message, tests, docs).
- "Verify APIs before testing or wrapping" — the executor should confirm the exact
  signatures in `docs_path.rs`, `app.rs`, `classic-path-py/src/lib.rs`, and
  `classic-node/src/path.rs` BEFORE editing. Planner has already verified
  that DocsPathFinder derives `Clone` (docs_path.rs line 58) so the binding-side
  `self.inner.clone().with_steam_app_id(...)` pattern is sound.

Explicit FORBIDDEN actions (planner-specified constraints):
- Do NOT hand-edit `ClassicLib-rs/node-bindings/classic-node/index.d.ts`. It is
  the generated Node contract artifact. Regenerate it by running `bun run build`
  from `ClassicLib-rs/node-bindings/classic-node`.
- Do NOT add entries to any parity-gate ignore list / tolerance list to make a
  gate pass. If a gate fails, fix the root cause (missing method, missing stub,
  wrong camelCase) — do not suppress the failure.
- Do NOT use `--no-verify` on the commit.
- Do NOT touch `classic-cli/` or `classic-gui/` (the native C++ frontends). They
  consume `detect_fallout4_docs_path` through the bridge; the bridge change in
  Task 2 is the ONLY thing they need.
- Do NOT modify `classic-path-core/src/platform/linux.rs`. The
  `parse_steam_library_vdf` and `construct_proton_docs_path` helpers already
  accept arbitrary Steam IDs as parameters — no change needed there.
- Do NOT add `classic-constants-core` as a dependency on `classic-path-core`
  itself. That would create a crate-graph cycle (constants-core is a lower layer).
  The caller crates (`classic-cpp-bridge`, `classic-tui`) add the constants dep
  instead — bridge already has it, TUI needs it added in Task 2.

Environment quirk (from project memory_project_build_paths_and_quirks):
- If running from Git Bash, source `tools/use_msvc_from_git_bash.sh` BEFORE any
  cargo or `bun run build` invocation so Git's `usr/bin/link.exe` doesn't
  shadow the MSVC linker. Running through PowerShell (the preferred tool here)
  already has the VS environment, so this is a fallback note only.
- Python bindings venv lives at `ClassicLib-rs/python-bindings/.venv`, NOT at
  the repo root. The parity gate script at
  `tools/python_api_parity/check_parity_gate.py` is driven by the repo-root
  Python interpreter and does NOT require the binding venv to be active — it
  parses source artifacts, not runtime imports.
</rules_in_force>

<interfaces>
<!-- Confirmed from source reads. Executor uses these directly — no further exploration. -->

classic-path-core docs_path.rs current state (lines 41-197):

  const FALLOUT_4_STEAM_APP_ID: u32 = 377160;          // line 41 — DELETE

  #[derive(Debug, Clone)]                              // line 58 — KEEP; Clone is the
  pub struct DocsPathFinder {                          //  basis for the binding
      relative_path: String,                           //  clone-mutate pattern.
  }                                                    //  ADD: steam_app_id: Option<u32>

  pub fn new(relative_path: impl Into<String>) -> Self // line 86 — steam_app_id: None
  pub fn find_docs_path(&self, cached_path: Option<&str>) -> DocsPathResult<PathBuf>  // line 125 — unchanged
  fn find_docs_path_linux(&self) -> DocsPathResult<PathBuf>  // lines 190-197 — gate on self.steam_app_id
  pub fn find_docs_path_linux_with(&self, home: &Path, steam_library: DocsPathResult<PathBuf>) -> DocsPathResult<PathBuf>
                                                                // lines 203-226 — gate on self.steam_app_id

Current Linux body to rewrite (lines 191-197):
  fn find_docs_path_linux(&self) -> DocsPathResult<PathBuf> {
      use crate::platform::linux::{get_home_directory, parse_steam_library_vdf};
      let home = get_home_directory()?;
      self.find_docs_path_linux_with(&home, parse_steam_library_vdf(FALLOUT_4_STEAM_APP_ID))
  }

After the change, find_docs_path_linux should:
  - Call get_home_directory() always.
  - If self.steam_app_id is Some(id), call parse_steam_library_vdf(id) and pass it
    through to find_docs_path_linux_with.
  - If self.steam_app_id is None, pass Err(DocsPathError::NotFound) (or any Err
    variant) as the steam_library argument so find_docs_path_linux_with skips the
    Proton branch entirely and goes straight to local-share.

Current find_docs_path_linux_with body (lines 203-226):
  pub fn find_docs_path_linux_with(
      &self,
      home: &Path,
      steam_library: DocsPathResult<PathBuf>,
  ) -> DocsPathResult<PathBuf> {
      use crate::platform::linux::construct_proton_docs_path;

      if let Ok(steam_library) = steam_library {
          let proton_docs_path = construct_proton_docs_path(
              &steam_library,
              FALLOUT_4_STEAM_APP_ID,       // <-- LITERAL TO REMOVE
              &self.relative_path,
          );

          if self.validate_docs_path(&proton_docs_path).is_ok() {
              return Ok(proton_docs_path);
          }
      }

      let local_share_path = home.join(".local/share").join(&self.relative_path);
      self.validate_docs_path(&local_share_path)?;
      Ok(local_share_path)
  }

After the change, find_docs_path_linux_with must:
  - Check `self.steam_app_id` first. If None, skip the entire Proton branch
    unconditionally — even if `steam_library` arg is Ok(_). (Belt-and-suspenders:
    guards both the public call path and the test-injected call path.)
  - If Some(id), use that id in construct_proton_docs_path INSTEAD of the deleted
    constant.

classic-constants-core Fallout4Version steam_app_id (lines 278-282, already verified):

  #[must_use]
  pub const fn steam_app_id(&self) -> u32 {
      if self.is_vr() { 611660 } else { 377160 }
  }

  // Call as: classic_constants_core::Fallout4Version::Original.steam_app_id()
  // which returns 377160 as a const fn.

classic-cpp-bridge path.rs detect_fallout4_docs_path (lines 85-101):

  fn detect_fallout4_docs_path(cached_path: &str, selected_game_version: &str) -> String {
      let relative = resolve_fallout4_version_info(selected_game_version)
          .map(|info| format!(r"My Games\{}", info.docs_name))
          .unwrap_or_else(|| r"My Games\Fallout4".to_string());
      let finder = DocsPathFinder::new(relative);          // <-- CHAIN .with_steam_app_id HERE

      let cached = if cached_path.is_empty() { None } else { Some(cached_path) };

      finder
          .find_docs_path(cached)
          .map(|p| p.to_string_lossy().to_string())
          .unwrap_or_default()
  }

classic-cpp-bridge Cargo.toml (verified):
  - classic-constants-core = { path = "../../business-logic/classic-constants-core" }
    is ALREADY present at line 52. No Cargo.toml edit needed for the bridge crate.
  - Current path.rs imports (lines 29-42) do NOT yet pull in Fallout4Version;
    the executor must add `use classic_constants_core::Fallout4Version;` to the
    `use` block at the top of src/path.rs.

classic-tui app.rs resolve_xse_folder_for_scan (lines 1451-1468):

  fn resolve_xse_folder_for_scan(config: &ClassicConfig) -> Option<PathBuf> {
      if let Some(xse_from_local) = xse_folder_from_local_yaml() {
          return Some(xse_from_local);
      }
      if let Some(docs_root) = &config.paths.docs_root
          && !docs_root.as_os_str().is_empty()
      {
          return Some(docs_root.join("F4SE"));
      }
      let relative_docs = resolve_selected_docs_relative_path(config);
      let finder = DocsPathFinder::new(&relative_docs);      // <-- CHAIN .with_steam_app_id HERE
      finder
          .find_docs_path(None)
          .ok()
          .map(|path| path.join("F4SE"))
  }

classic-tui Cargo.toml (verified):
  - classic-constants-core is NOT currently a dependency. Must be ADDED in Task 2.
  - Current deps list (lines 18-24) does NOT include classic-constants-core.
  - Current `use classic_path_core::` import on line 10 of app.rs covers
    DocsPathFinder + validate_custom_scan_path; add a new
    `use classic_constants_core::Fallout4Version;` near the existing
    `use classic_path_core::...` line.

classic-path-py DocsPathFinder (lines 778-927):
  - Currently uses `&self` methods only. Add a new `#[pymethods]`-scope method
    `set_steam_app_id(&mut self, app_id: u32)` that performs
    `self.inner = self.inner.clone().with_steam_app_id(app_id);`
  - Because `DocsPathFinder` derives Clone (verified at docs_path.rs:58), the
    clone-mutate pattern is sound and cheap (String + Option<u32>).
  - PyO3 0.27 accepts `&mut self` on pymethods; no #[pyo3] attribute override
    needed since the Rust name `set_steam_app_id` already matches the Python
    snake_case convention.

classic-path-py classic_path.pyi:
  - The DocsPathFinder class stub is at lines 241-294. Add a new method stub
    `def set_steam_app_id(self, app_id: int) -> None: ...` with a docstring
    explaining the opt-in semantics.

classic-node DocsPathFinder (lines 291-352):
  - Currently uses `&self` methods only. Add a new `#[napi]`-scope method
    `pub fn set_steam_app_id(&mut self, app_id: u32)` that performs
    `self.inner = self.inner.clone().with_steam_app_id(app_id);`
  - NAPI-RS auto-converts `set_steam_app_id` to `setSteamAppId` in the generated
    `index.d.ts`. Do NOT add an explicit `#[napi(js_name = ...)]` override.

classic-node index.d.ts:
  - Generated by `napi build`. Regenerated via `bun run build` from
    `ClassicLib-rs/node-bindings/classic-node`. NEVER hand-edited.
  - After `bun run build`, the file must contain a line like
    `setSteamAppId(appId: number): void`  inside the `DocsPathFinder` class.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Core opt-in refactor in classic-path-core + test updates + new test</name>
  <files>
    ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs,
    ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs
  </files>
  <action>
Edit ONLY the two files above.

Step 1 — Refactor `docs_path.rs`:

  a) Delete line 41 entirely (`const FALLOUT_4_STEAM_APP_ID: u32 = 377160;`).

  b) Add a new field to the `DocsPathFinder` struct (line 58-62). After the
     refactor it must read:

        #[derive(Debug, Clone)]
        pub struct DocsPathFinder {
            /// Relative path within documents folder (e.g., "My Games\\Fallout4")
            relative_path: String,
            /// Optional Steam application ID. When Some(_), the Linux
            /// documents-path lookup will try the Steam/Proton prefix for that
            /// app ID before falling back to ~/.local/share. When None
            /// (the default from `new`), the Proton lookup is skipped entirely
            /// and the finder goes straight to ~/.local/share. Callers that
            /// want Fallout 4 Proton behavior opt in via `with_steam_app_id`.
            steam_app_id: Option<u32>,
        }

  c) Update `new` (line 86-90) so the new field defaults to None:

        pub fn new(relative_path: impl Into<String>) -> Self {
            Self {
                relative_path: relative_path.into(),
                steam_app_id: None,
            }
        }

  d) Add a new public consuming builder method RIGHT AFTER `new` (before
     `find_docs_path`). Required shape, including a full doc comment because
     the crate has `missing_docs = "warn"`:

        /// Opt in to a Steam-application-ID-aware Linux Proton documents
        /// path lookup.
        ///
        /// When this is set, `find_docs_path` on Linux will first try the
        /// Steam/Proton compatdata prefix for the given app ID before
        /// falling back to `~/.local/share/<relative_path>`. When it is NOT
        /// set (the `new` default), the Proton lookup is skipped entirely
        /// and `find_docs_path` on Linux goes straight to
        /// `~/.local/share/<relative_path>`.
        ///
        /// This is an opt-in because `DocsPathFinder` is a game-agnostic
        /// helper — historically it hard-coded Fallout 4's Steam App ID
        /// (377160) for its Linux Proton lookup, which meant a consumer of
        /// the generic API for another game implicitly probed Fallout 4's
        /// compatdata prefix.
        ///
        /// # Arguments
        ///
        /// * `app_id` - The Steam application ID for the game whose Proton
        ///   documents prefix should be searched (for Fallout 4 this is
        ///   `377160`; use
        ///   `classic_constants_core::Fallout4Version::Original.steam_app_id()`
        ///   in callers that already depend on `classic-constants-core` to
        ///   avoid duplicating the literal).
        ///
        /// # Returns
        ///
        /// The finder with the new Steam app ID installed (consuming
        /// builder).
        ///
        /// # Examples
        ///
        /// ```rust
        /// use classic_path_core::DocsPathFinder;
        ///
        /// // Generic usage (no Proton lookup on Linux):
        /// let finder = DocsPathFinder::new("My Games/Skyrim");
        ///
        /// // Fallout-4-specific usage (Linux Proton lookup enabled):
        /// let fo4_finder = DocsPathFinder::new("My Games/Fallout4")
        ///     .with_steam_app_id(377160);
        /// ```
        #[must_use]
        pub fn with_steam_app_id(mut self, app_id: u32) -> Self {
            self.steam_app_id = Some(app_id);
            self
        }

  e) Rewrite `find_docs_path_linux` (currently lines 190-197) to gate on
     `self.steam_app_id`:

        #[cfg(not(target_os = "windows"))]
        fn find_docs_path_linux(&self) -> DocsPathResult<PathBuf> {
            use crate::platform::linux::{get_home_directory, parse_steam_library_vdf};

            let home = get_home_directory()?;

            let steam_library = match self.steam_app_id {
                Some(app_id) => parse_steam_library_vdf(app_id),
                None => Err(DocsPathError::NotFound),
            };

            self.find_docs_path_linux_with(&home, steam_library)
        }

  f) Rewrite `find_docs_path_linux_with` (currently lines 203-226) so that:
     - If `self.steam_app_id` is None, the Proton branch is skipped regardless
       of the `steam_library` argument (belt-and-suspenders so test-injected
       Ok(_) values also get ignored when no app_id is set).
     - When `self.steam_app_id` is Some(id), use `id` in
       `construct_proton_docs_path` instead of the deleted constant.

     Exact target body:

        #[doc(hidden)]
        pub fn find_docs_path_linux_with(
            &self,
            home: &Path,
            steam_library: DocsPathResult<PathBuf>,
        ) -> DocsPathResult<PathBuf> {
            use crate::platform::linux::construct_proton_docs_path;

            if let Some(app_id) = self.steam_app_id
                && let Ok(steam_library) = steam_library
            {
                let proton_docs_path = construct_proton_docs_path(
                    &steam_library,
                    app_id,
                    &self.relative_path,
                );

                if self.validate_docs_path(&proton_docs_path).is_ok() {
                    return Ok(proton_docs_path);
                }
            }

            let local_share_path = home.join(".local/share").join(&self.relative_path);
            self.validate_docs_path(&local_share_path)?;

            Ok(local_share_path)
        }

     Note: `let ... && let ...` chains are stable on Rust edition 2024 / MSRV
     1.85 (workspace edition per `classic-path-core/Cargo.toml` line 4). If
     the build fails on the let-chain for any reason, fall back to nested
     `if let Some(app_id) = self.steam_app_id { if let Ok(steam_library) = ... { ... } }`.

  g) Update the module-level doc comment section "Detection Strategies"
     (lines 7-12) to reflect the new Linux behavior. After the change the
     relevant bullet should read:

        //! 1. **Cached Path**: Use previously saved path from settings if valid
        //! 2. **Windows Registry**: Query "Personal" folder from Windows registry
        //! 3. **Linux**: Uses home directory + ".local/share"; if the caller has
        //!    opted in via `with_steam_app_id`, a Steam/Proton compatdata path
        //!    is tried first before that fallback.
        //! 4. **Manual Selection**: Prompt user to manually select the path (handled by caller)

     Also update the "Platform Support" bullet for Linux (line 17) to:

        //! - **Linux**: Uses home directory + ".local/share"; Proton
        //!   compatdata lookup is opt-in via `DocsPathFinder::with_steam_app_id`

  h) Update the doc comments on `find_docs_path` (lines 92-98) and
     `find_docs_path_linux` (lines 178-189) so the behavior description is
     accurate. Specifically the `find_docs_path_linux` doc should say "Uses
     the home directory and, when the caller has opted in via
     `with_steam_app_id`, prefers a valid Steam/Proton documents path for
     that app ID before falling back to the legacy `.local/share` location"
     — the existing reference to "Fallout 4" must go away.

  i) Confirm the `tests` module at the bottom of the file still compiles —
     no existing test in `docs_path.rs`'s inline `#[cfg(test)] mod tests`
     references `FALLOUT_4_STEAM_APP_ID` directly (checked during planning).

Step 2 — Update the integration test file
  `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs`:

  Chain `.with_steam_app_id(377160)` on the DocsPathFinder construction in the
  following FOUR existing tests so they continue to prove Proton selection:

    - `proton_docs_path_wins_over_valid_local_share` (line 23)
    - `steam_lookup_failure_proton_falls_back_to_local_share` (line 41)
    - `invalid_proton_docs_path_falls_back_to_local_share` (line 56)
    - `legacy_local_share_regression_still_works_without_proton` (line 73)

  Specifically, each one currently has:

      let finder = DocsPathFinder::new(relative_path);

  Replace that line with:

      let finder = DocsPathFinder::new(relative_path).with_steam_app_id(377160);

  The helper `proton_docs_root` at line 16 hard-codes `377160` in the test
  path literal — LEAVE IT ALONE. It is test-fixture infrastructure, not
  production code, and explicitly matching on the literal is what makes the
  test assertion meaningful. (The planner-scope rule permits literal 377160
  in test files.)

Step 3 — ADD a new integration test AT THE END of
  `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs`:

    #[test]
    fn proton_path_ignored_when_steam_app_id_unset() {
        // When the caller does NOT opt in via with_steam_app_id, the Proton
        // compatdata lookup must be skipped entirely, even if a valid Proton
        // FO4 docs dir is present on disk. The finder must return the
        // local-share path instead.
        let temp_dir = TempDir::new().unwrap();
        let home = temp_dir.path();
        let relative_path = "My Games/Fallout4";
        let steam_library = home.join("steam-library");
        let proton_path = proton_docs_root(&steam_library, relative_path);
        let local_share_path = local_share(home, relative_path);

        // Create BOTH paths on disk. Before the fix, the Proton path would
        // win. After the fix, with no Steam app ID opt-in, the local-share
        // path must win.
        create_directory(&proton_path);
        create_directory(&local_share_path);

        // NO .with_steam_app_id call — default-constructed finder.
        let finder = DocsPathFinder::new(relative_path);
        let result = finder.find_docs_path_linux_with(home, Ok(steam_library));

        assert_eq!(result.unwrap(), local_share_path);
    }

Step 4 — DO NOT modify any other file in this task. In particular, do NOT
touch `classic-path-core/src/platform/linux.rs` or `classic-path-core/src/lib.rs`.
  </action>
  <verify>
    <automated>
Run from repo root using the PowerShell tool (pwsh), NOT bash:

  pwsh -Command "cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml"

Expected: all tests in `classic-path-core` pass, including:
  - the 4 updated `linux_proton_docs_path` tests
  - the NEW `proton_path_ignored_when_steam_app_id_unset` test
  - all existing inline `#[cfg(test)] mod tests` in `docs_path.rs`, `validator.rs`,
    `platform/linux.rs`, etc.

Then the narrow "literal-is-gone" check (grep):

  pwsh -Command "Select-String -Path ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs -Pattern '377160'"

Expected: NO matches. The literal 377160 must not appear anywhere in
`docs_path.rs` after this task — not in code, not in comments, not in doc
examples. (The doc example in `with_steam_app_id` uses `.with_steam_app_id(377160)`
as an inline example; that IS a literal. If the executor chooses to include that
example literal, the grep will match it once. Preferred resolution: write the
example as `.with_steam_app_id(classic_constants_core::Fallout4Version::Original.steam_app_id())`
is NOT acceptable either because classic-path-core can't depend on
classic-constants-core. So the compromise is: the example IS allowed to have
one `377160` literal because it's documentation of the literal's meaning,
AND the test file is allowed to keep its `proton_docs_root` literal. If
the Select-String above returns exactly 1 hit (the doc example line), accept.
If it returns more than 1, the executor must investigate and strip the extra.)

Then the "new method exists" check:

  pwsh -Command "Select-String -Path ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs -Pattern 'pub fn with_steam_app_id'"

Expected: exactly 1 match.

Then the "new test exists" check:

  pwsh -Command "Select-String -Path ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs -Pattern 'proton_path_ignored_when_steam_app_id_unset'"

Expected: exactly 1 match (the `#[test]` function itself).

Then the "4 existing tests updated" check:

  pwsh -Command "Select-String -Path ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs -Pattern 'with_steam_app_id\(377160\)'"

Expected: AT LEAST 4 matches (one per updated test).
    </automated>
  </verify>
  <done>
- `docs_path.rs` no longer contains `const FALLOUT_4_STEAM_APP_ID`.
- `DocsPathFinder` has a `steam_app_id: Option<u32>` field defaulting to `None`.
- `DocsPathFinder::with_steam_app_id(u32) -> Self` exists, is `#[must_use]`, and
  has a full doc comment passing `missing_docs = "warn"`.
- `find_docs_path_linux_with` skips the Proton branch entirely when
  `self.steam_app_id` is `None`.
- All 4 pre-existing integration tests in `tests/linux_proton_docs_path.rs`
  now chain `.with_steam_app_id(377160)` and pass.
- New test `proton_path_ignored_when_steam_app_id_unset` exists at the bottom
  of `tests/linux_proton_docs_path.rs`, constructs BOTH a valid Proton FO4 docs
  dir AND a valid local-share dir, calls `find_docs_path_linux_with` on a
  finder with NO Steam app ID set, and asserts the local-share path wins.
- `cargo test -p classic-path-core` passes fully.
- Grep confirms the new method, the new test, and the 4 chained
  `.with_steam_app_id(377160)` calls all exist.
- No files outside the two declared ones were modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Internal Rust callers opt in + binding wrappers get set_steam_app_id</name>
  <files>
    ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs,
    ClassicLib-rs/ui-applications/classic-tui/src/app.rs,
    ClassicLib-rs/ui-applications/classic-tui/Cargo.toml,
    ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs,
    ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi,
    ClassicLib-rs/node-bindings/classic-node/src/path.rs
  </files>
  <action>
Edit ONLY the six files above. Do not touch `index.d.ts` by hand (Task 3
regenerates it).

Step 1 — `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`:

  a) Add a new line to the `use` block at the top of the file (after line 42,
     where `std::path::Path` is imported):

        use classic_constants_core::Fallout4Version;

     `classic-constants-core` is already in the bridge crate's Cargo.toml
     (line 52, verified during planning), so no Cargo.toml edit is needed
     on the bridge side.

  b) In `detect_fallout4_docs_path` (lines 85-101), change the `DocsPathFinder`
     construction at line 89 from:

        let finder = DocsPathFinder::new(relative);

     to:

        // Opt in to Fallout 4's Steam/Proton documents lookup on Linux.
        // The canonical 377160 literal lives in classic_constants_core.
        let finder = DocsPathFinder::new(relative)
            .with_steam_app_id(Fallout4Version::Original.steam_app_id());

     Note: `Fallout4Version::Original.steam_app_id()` returns `377160` as a
     const fn (verified from classic-constants-core lines 278-282). Using
     `Original` (not `NextGen`, not `Vr`) is intentional — the planner verified
     that `Original.steam_app_id()` and `NextGen.steam_app_id()` both return
     `377160`; only `Vr` returns `611660`. Since this function is the
     non-VR Fallout 4 docs-path helper, `Original` is the correct choice.
     (VR users are handled by version-info resolution elsewhere in the bridge.)

Step 2 — `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml`:

  Add `classic-constants-core` as a path dependency. In the `[dependencies]`
  section (currently lines 14-35), add this line right after the existing
  `classic-path-core` line at line 22:

        classic-constants-core = { path = "../../business-logic/classic-constants-core" }

Step 3 — `ClassicLib-rs/ui-applications/classic-tui/src/app.rs`:

  a) Add a new `use` line near the existing `use classic_path_core::...` at
     line 10. Insert immediately AFTER line 10 (or near the other classic_*
     use statements — executor may pick the most-neighbor position that
     clang-format... no, rustfmt... won't relocate):

        use classic_constants_core::Fallout4Version;

  b) In `resolve_xse_folder_for_scan` (lines 1451-1468), change the
     DocsPathFinder construction at line 1463 from:

        let finder = DocsPathFinder::new(&relative_docs);

     to:

        // Opt in to Fallout 4's Steam/Proton documents lookup on Linux.
        // The canonical 377160 literal lives in classic_constants_core.
        let finder = DocsPathFinder::new(&relative_docs)
            .with_steam_app_id(Fallout4Version::Original.steam_app_id());

Step 4 — `ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs`:

  Inside the `#[pymethods] impl DocsPathFinder { ... }` block (starts at
  line 783), add a new method RIGHT AFTER the `new` constructor (line 811)
  and BEFORE `find_docs_path` (line 848). Exact shape:

        /// Opt in to a Steam-application-ID-aware Linux Proton documents
        /// path lookup.
        ///
        /// When set, `find_docs_path` on Linux will first try the
        /// Steam/Proton compatdata prefix for the given app ID before
        /// falling back to `~/.local/share/<relative_path>`. When NOT
        /// set (the default from the constructor), the Proton lookup is
        /// skipped entirely and `find_docs_path` on Linux goes straight
        /// to `~/.local/share/<relative_path>`.
        ///
        /// This is an opt-in because DocsPathFinder is a game-agnostic
        /// helper. For example, a Fallout 4 caller should pass
        /// `377160`, while a Skyrim caller should pass that game's
        /// Steam app ID (or not call this method at all if Proton
        /// fallback is unwanted).
        ///
        /// # Arguments
        ///
        /// * `app_id` - The Steam application ID for the game whose
        ///   Proton documents prefix should be searched.
        ///
        /// # Python Examples
        ///
        /// ```python
        /// from classic_path import DocsPathFinder
        ///
        /// finder = DocsPathFinder("My Games\\Fallout4")
        /// finder.set_steam_app_id(377160)  # Fallout 4 Steam App ID
        /// docs_path = finder.find_docs_path(cached_path=None)
        /// ```
        fn set_steam_app_id(&mut self, app_id: u32) {
            self.inner = self.inner.clone().with_steam_app_id(app_id);
        }

  Note: The PyO3 0.27 `#[pymethods]` block already allows `&mut self`
  receivers. No `#[pyo3(name = "...")]` attribute is needed because the
  Rust snake_case name matches Python's convention.

Step 5 — `ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi`:

  In the `class DocsPathFinder:` block (starts line 241), add a new method
  stub RIGHT AFTER `__init__` (which currently ends at line 250) and BEFORE
  `find_docs_path` (line 252). Exact shape:

        def set_steam_app_id(self, app_id: int) -> None:
            """Opt in to a Steam-application-ID-aware Linux Proton documents path lookup.

            When set, ``find_docs_path`` on Linux will first try the Steam/Proton
            compatdata prefix for the given app ID before falling back to
            ``~/.local/share/<relative_path>``. When NOT set (the default from
            the constructor), the Proton lookup is skipped entirely and
            ``find_docs_path`` on Linux goes straight to
            ``~/.local/share/<relative_path>``.

            This is an opt-in because DocsPathFinder is a game-agnostic helper.
            For example, a Fallout 4 caller should pass ``377160``, while a
            Skyrim caller should pass that game's Steam app ID (or not call
            this method at all if Proton fallback is unwanted).

            Args:
                app_id: The Steam application ID for the game whose Proton
                    documents prefix should be searched.

            """

Step 6 — `ClassicLib-rs/node-bindings/classic-node/src/path.rs`:

  Inside the `#[napi] impl DocsPathFinder { ... }` block (starts line 297),
  add a new method RIGHT AFTER the `new` constructor (line 306) and BEFORE
  `find_docs_path` (line 316). Exact shape:

        /// Opt in to a Steam-application-ID-aware Linux Proton documents
        /// path lookup.
        ///
        /// When set, `findDocsPath` on Linux will first try the
        /// Steam/Proton compatdata prefix for the given app ID before
        /// falling back to `~/.local/share/<relativePath>`. When NOT
        /// set (the default from the constructor), the Proton lookup is
        /// skipped entirely and `findDocsPath` on Linux goes straight to
        /// `~/.local/share/<relativePath>`.
        ///
        /// This is an opt-in because DocsPathFinder is a game-agnostic
        /// helper. For example, a Fallout 4 caller should pass
        /// `377160`, while a Skyrim caller should pass that game's
        /// Steam app ID (or not call this method at all if Proton
        /// fallback is unwanted).
        ///
        /// @param appId - The Steam application ID for the game whose
        ///                Proton documents prefix should be searched.
        #[napi]
        pub fn set_steam_app_id(&mut self, app_id: u32) {
            self.inner = self.inner.clone().with_steam_app_id(app_id);
        }

  Note: NAPI-RS 3 auto-converts `set_steam_app_id` to the JavaScript name
  `setSteamAppId` in the generated `index.d.ts`. Do NOT add `#[napi(js_name = ...)]`.

Step 7 — Do NOT touch any other file in this task. In particular:
  - DO NOT edit `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (Task 3
    regenerates it).
  - DO NOT edit `classic-cli/` or `classic-gui/` (the C++ frontends) — they
    already consume `detect_fallout4_docs_path` through the bridge, and the
    bridge change in Step 1 is all they need.
  - DO NOT edit `classic-path-core/src/platform/linux.rs`.
  - DO NOT edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`
    (the dep is already there).
  - DO NOT add or remove any other dependency from `classic-tui/Cargo.toml`
    beyond the one `classic-constants-core` line.
  </action>
  <verify>
    <automated>
Run these pwsh commands from repo root.

  pwsh -Command "Select-String -Path ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs -Pattern 'with_steam_app_id'"

Expected: exactly 1 match (the chained call in detect_fallout4_docs_path).

  pwsh -Command "Select-String -Path ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs -Pattern 'use classic_constants_core::Fallout4Version'"

Expected: exactly 1 match.

  pwsh -Command "Select-String -Path ClassicLib-rs/ui-applications/classic-tui/src/app.rs -Pattern 'with_steam_app_id'"

Expected: exactly 1 match (the chained call in resolve_xse_folder_for_scan).

  pwsh -Command "Select-String -Path ClassicLib-rs/ui-applications/classic-tui/src/app.rs -Pattern 'use classic_constants_core::Fallout4Version'"

Expected: exactly 1 match.

  pwsh -Command "Select-String -Path ClassicLib-rs/ui-applications/classic-tui/Cargo.toml -Pattern 'classic-constants-core'"

Expected: exactly 1 match (the new dep line).

  pwsh -Command "Select-String -Path ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs -Pattern 'fn set_steam_app_id'"

Expected: exactly 1 match.

  pwsh -Command "Select-String -Path ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi -Pattern 'def set_steam_app_id'"

Expected: exactly 1 match.

  pwsh -Command "Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/path.rs -Pattern 'pub fn set_steam_app_id'"

Expected: exactly 1 match.

Now build the full Rust workspace and assert it compiles cleanly:

  pwsh -Command "cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml"

Expected: clean build, no warnings from the workspace lints (deprecated = deny,
unsafe_code = deny in classic-path-core, unused = deny, etc.). The bridge crate
allows dead_code because CXX exports aren't seen by cargo check — that's OK.

Then run the workspace tests:

  pwsh -Command "cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml"

Expected: all workspace tests pass. This includes all 5 `linux_proton_docs_path`
integration tests (from Task 1) AND every other existing workspace test. A
regression in any other crate means the executor broke something — investigate
before proceeding.
    </automated>
  </verify>
  <done>
- `classic-cpp-bridge/src/path.rs` imports `classic_constants_core::Fallout4Version`
  and `detect_fallout4_docs_path` chains
  `.with_steam_app_id(Fallout4Version::Original.steam_app_id())`.
- `classic-tui/src/app.rs` imports `classic_constants_core::Fallout4Version` and
  `resolve_xse_folder_for_scan` chains
  `.with_steam_app_id(Fallout4Version::Original.steam_app_id())`.
- `classic-tui/Cargo.toml` has `classic-constants-core` as a new path dependency.
- `classic-path-py/src/lib.rs` `DocsPathFinder` exposes a new
  `set_steam_app_id(&mut self, app_id: u32)` method whose body is
  `self.inner = self.inner.clone().with_steam_app_id(app_id);`, with a full
  Python-facing doc comment.
- `classic-path-py/classic_path.pyi` `DocsPathFinder` class has a matching
  `def set_steam_app_id(self, app_id: int) -> None: ...` stub.
- `classic-node/src/path.rs` `DocsPathFinder` exposes a new
  `pub fn set_steam_app_id(&mut self, app_id: u32)` method under `#[napi]`, same
  body pattern.
- `cargo build --workspace` and `cargo test --workspace` both pass with no
  new warnings or failures.
- No files outside the six declared ones were modified.
  </done>
</task>

<task type="auto">
  <name>Task 3: Regenerate Node contract + run parity gates + full-workspace clippy/fmt</name>
  <files>
    ClassicLib-rs/node-bindings/classic-node/index.d.ts
  </files>
  <action>
This task produces exactly one CODE artifact (the regenerated `index.d.ts`) and
otherwise runs verification gates. Do NOT hand-edit `index.d.ts`.

Step 1 — Regenerate `index.d.ts`:

  From the directory `ClassicLib-rs/node-bindings/classic-node`, run:

    pwsh -Command "cd ClassicLib-rs/node-bindings/classic-node; bun run build"

  Expected: the build succeeds. It will recompile the Rust NAPI crate and
  regenerate `index.d.ts`. After the build, the file must contain a line
  under the `DocsPathFinder` class declaration that looks like:

    setSteamAppId(appId: number): void

  If `bun run build` fails with an MSVC linker error and the executor is
  running from Git Bash, source `tools/use_msvc_from_git_bash.sh` first,
  then retry. If running from PowerShell (preferred), the VS environment
  should already be in scope.

Step 2 — Verify the regenerated TypeScript contract:

  pwsh -Command "cd ClassicLib-rs/node-bindings/classic-node; Select-String -Path index.d.ts -Pattern 'setSteamAppId'"

  Expected: exactly 1 match. If 0, the NAPI macro did not pick up the new
  method — re-check Task 2 Step 6 and rebuild. If more than 1, something
  is off; investigate.

Step 3 — Run the Node parity gate (the whole point of the contract):

  pwsh -Command "cd ClassicLib-rs/node-bindings/classic-node; bun run parity:gate:local"

  Expected: GREEN. The gate compares the TypeScript contract in `index.d.ts`
  against the documented parity baseline. Adding a new method to a tracked
  class should either (a) pass automatically because the gate tracks
  exposed-but-unused growth as neutral, or (b) require a tiny gate refresh
  command. The executor MUST NOT add the new method to any ignore list.
  If the gate explicitly fails because the new method needs baseline
  acknowledgement, run the project's documented refresh command (typically
  something like `bun run parity:baseline:refresh` or the scripted equivalent
  — check `package.json` scripts for the exact name), then rerun
  `bun run parity:gate:local` and confirm it passes. Capture BOTH the
  refresh command output AND the final gate-green output.

Step 4 — Run the Python parity gate (from repo root):

  pwsh -Command "python tools/python_api_parity/check_parity_gate.py --repo-root ."

  Expected: GREEN. This script parses the Rust source of the binding crates
  and the `.pyi` stubs and compares them. Adding `set_steam_app_id` to both
  the Rust PyO3 impl (Task 2 Step 4) AND the `.pyi` stub (Task 2 Step 5)
  should keep the gate green. If the gate complains about a missing stub,
  it means the .pyi edit in Task 2 did not land correctly — fix it
  (re-edit the .pyi file) and rerun the gate. Do NOT add the new method
  to any parity ignore list.

Step 5 — Run the full-workspace lint gates:

  pwsh -Command "cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings"

  Expected: zero warnings, zero errors. `-D warnings` promotes every clippy
  warning to an error. The worktree memory explicitly notes: NEVER bypass
  clippy. If clippy flags something in the new code (e.g. a doc-test that
  won't compile, a must_use mismatch, a needless-clone warning on the
  binding-side `self.inner.clone().with_steam_app_id(app_id)` pattern),
  fix the root cause — do NOT add `#[allow(...)]` attributes unless they
  are absolutely necessary and the executor has a compelling
  per-call-site reason.

  (If clippy complains about `needless_clone` on the binding sites, note
  that the clone IS necessary because `with_steam_app_id` is a consuming
  builder and `&mut self` doesn't let us `mem::take` safely without
  introducing a fallible placeholder. In that case, an
  `#[allow(clippy::needless_clone)]` per-function would be acceptable,
  but prefer `std::mem::replace` with a default if clippy is persistent.
  The planner expects clippy to accept the clone silently because the
  inner type is Clone-derived and the clone is documented-intent.)

Step 6 — Run fmt --check:

  pwsh -Command "cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check"

  Expected: GREEN (no diff). If fmt fails, run `cargo fmt --all` without
  --check to apply the formatting, then rerun --check.

Step 7 — Final full workspace test sanity pass:

  pwsh -Command "cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml"

  Expected: all tests still pass, identical to the Task 2 verify step.
  This is the final post-regen confirmation that no Rust change broke
  anything.

Do NOT touch any file other than letting `bun run build` regenerate
`index.d.ts` in Step 1. If any other file in the workspace gets modified by
`bun run build` or `cargo fmt`, inspect why — it should only be `index.d.ts`
and possibly binding compiled artifacts under `target/` / `dist/` (which are
gitignored).
  </action>
  <verify>
    <automated>
The verify block is embedded in the action steps (this task IS verification
after the Rust change lands). The acceptance gates are:

  Step 1: `bun run build` exits 0 in ClassicLib-rs/node-bindings/classic-node.
  Step 2: `index.d.ts` contains `setSteamAppId`.
  Step 3: `bun run parity:gate:local` exits 0.
  Step 4: `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0.
  Step 5: `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0.
  Step 6: `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` exits 0.
  Step 7: `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` exits 0.

ALL seven must pass. Capture the stdout+stderr of each into the SUMMARY so
the user has a complete audit trail.
    </automated>
  </verify>
  <done>
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` has been regenerated by
  `bun run build` (NOT hand-edited) and contains a `setSteamAppId(appId: number): void`
  method inside the `DocsPathFinder` class.
- `bun run parity:gate:local` reports GREEN.
- `python tools/python_api_parity/check_parity_gate.py --repo-root .` reports GREEN.
- `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` reports GREEN.
- `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` reports GREEN.
- `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` reports GREEN.
- No ignore-list / tolerance-list entries were added to any parity-gate config.
- Captured stdout/stderr of each of the 7 commands above are in the SUMMARY.
  </done>
</task>

<task type="auto">
  <name>Task 4: Docs sync + single Fix commit</name>
  <files>
    docs/api/classic-path-core.md,
    docs/api/classic-cpp-bridge-game-entrypoints.md,
    docs/api/game-setup-workflow.md
  </files>
  <action>
Step 1 — `docs/api/classic-path-core.md`:

  Update the `DocsPathFinder` section (roughly lines 124-145 in the current
  file) to document the new opt-in. Specifically:

  a) Add `with_steam_app_id(app_id: u32) -> Self (consuming builder)` to the
     "Important methods:" bulleted list after `relative_path() -> &str`.

  b) Rewrite the "Behavior visible in source:" bullets for the Linux case.
     The current non-Windows bullet (line 143) reads:
       "- on non-Windows builds it next tries a Fallout 4 Proton documents
          path resolved from Steam library metadata, then falls back to
          `home/.local/share/<relative_path>` if Proton metadata lookup fails
          or the Proton path is invalid"

     Replace with:
       "- on non-Windows builds it uses `home/.local/share/<relative_path>`
          by default; if the caller opted in via
          `DocsPathFinder::with_steam_app_id(app_id)`, the finder first tries
          a Steam/Proton documents path built from the Steam library metadata
          for that app ID and falls back to the legacy `.local/share` location
          if the Proton lookup fails or the Proton path is invalid. Callers
          that do not opt in get NO Proton lookup at all, so a generic
          non-Fallout-4 consumer no longer implicitly probes Fallout 4's
          `compatdata/377160` prefix."

  c) Update the "Documents-path flow" section around lines 263-270 to
     reflect the new opt-in ordering. Replace the current Linux bullet
     ("`home/.local/share/<relative_path>` on non-Windows builds" or the
     equivalent text) with a bullet that mentions both the default
     local-share path and the opt-in Proton lookup via `with_steam_app_id`.

  d) In the "Contributor Notes And Known Limits" section (line 442+), find
     the existing bullet that says:
       "- `DocsPathFinder` does not currently build a Proton documents path
          automatically even though Linux Steam helpers exist in the crate"
     and UPDATE it to reflect the new reality:
       "- `DocsPathFinder`'s Linux Proton lookup is opt-in via
          `with_steam_app_id(app_id)`; the default is `home/.local/share/...`
          only. Game-specific callers like the CXX bridge's
          `detect_fallout4_docs_path` and the TUI's
          `resolve_xse_folder_for_scan` opt in with
          `Fallout4Version::Original.steam_app_id()` (377160)."

  e) At the bottom of the file in the "If you extend this crate, update this
     document when you change:" bullet list (around line 453-461), add a new
     bullet:
       "- the opt-in rules for the Linux Proton documents lookup"

Step 2 — `docs/api/classic-cpp-bridge-game-entrypoints.md`:

  Update the `detect_fallout4_docs_path` entry (lines 102-115 in the current
  file). After the existing "Current bridge choices:" bullet list, add one
  more bullet to that list:

       "- chains `DocsPathFinder::with_steam_app_id(Fallout4Version::Original.steam_app_id())`
          so Linux Proton documents-path detection for Fallout 4 still works.
          This is the canonical call site for the 377160 literal — the
          bridge imports `classic_constants_core::Fallout4Version` rather than
          hard-coding the Steam ID."

Step 3 — `docs/api/game-setup-workflow.md`:

  Read the "Detect Or Validate The Documents Folder" section (lines 123-139)
  and the "Source-Backed Limits And Caveats" section (lines 376-389). Two
  edits are required:

  a) In the "Documents-path flow" section (currently lines 128-133), update
     the Linux bullets. The current bullets 3 and 4 read:

       "3. on non-Windows builds, a valid Fallout 4 Proton documents path
           resolved from Steam metadata
        4. `home/.local/share/<relative_path>` on non-Windows builds when
           Steam lookup fails or the Proton documents path is invalid"

     Replace with:

       "3. on non-Windows builds, if the caller opted in via
           `DocsPathFinder::with_steam_app_id(app_id)`, a valid Steam/Proton
           documents path resolved from Steam metadata for that app ID
        4. `home/.local/share/<relative_path>` on non-Windows builds when no
           opt-in was made or when the Proton lookup fails or the Proton
           documents path is invalid"

  b) In the "Source-Backed Limits And Caveats" section, find the existing
     bullet:
       "- `classic-path-core::DocsPathFinder` does not currently auto-build
          a Proton-specific documents path from Steam metadata"
     and UPDATE it to:
       "- `classic-path-core::DocsPathFinder`'s Linux Proton documents path
          lookup is opt-in via `with_steam_app_id(app_id)`; the default finder
          skips it and goes straight to `~/.local/share/<relative_path>`"

  If after reading the file these sections do NOT reference the exact
  behavior as the planner described (i.e. the file has already been updated
  or the structure differs from what the planner saw at 2026-04-07), the
  executor must apply the spirit of the update: document the opt-in, and
  remove any stale claims that DocsPathFinder never builds a Proton path
  or always builds one for FO4. If zero relevant text is found, SKIP this
  file and note "docs/api/game-setup-workflow.md did not reference the
  changed behavior, no update needed" in the SUMMARY.

Step 4 — Final assembly and single commit:

  a) Re-run the static checks from Tasks 1-3 one more time as a safety net:

       pwsh -Command "cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check"
       pwsh -Command "cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings"
       pwsh -Command "cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml"

  b) Verify the full set of files-to-commit matches the plan's
     `files_modified` list EXACTLY:

       pwsh -Command "git status --porcelain"

     Expected modified files (11 total):
       - ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs
       - ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs
       - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs
       - ClassicLib-rs/ui-applications/classic-tui/src/app.rs
       - ClassicLib-rs/ui-applications/classic-tui/Cargo.toml
       - ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs
       - ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
       - ClassicLib-rs/node-bindings/classic-node/src/path.rs
       - ClassicLib-rs/node-bindings/classic-node/index.d.ts
       - docs/api/classic-path-core.md
       - docs/api/classic-cpp-bridge-game-entrypoints.md

     If `docs/api/game-setup-workflow.md` was updated in Step 3, it is the
     12th file. If it was NOT updated (no relevant text found), it is NOT
     staged. Either outcome is fine.

     `ClassicLib-rs/Cargo.lock` MAY also appear modified if adding
     classic-constants-core to classic-tui's Cargo.toml pulls in new
     transitive lockfile lines. That is expected and should be committed.

     If ANY other file shows as modified (especially in `classic-cli/`,
     `classic-gui/`, `classic-path-core/src/lib.rs`,
     `classic-path-core/src/platform/linux.rs`, the shared
     `AGENTS.md`, `CLAUDE.md`, or `README.md`), STOP. Investigate why it
     changed and either revert or explain before committing.

  c) Create a single commit. Per CLAUDE.md commit conventions, the message
     MUST start with `Fix:` (capitalized first word after the prefix).
     Suggested commit message:

       Fix: make DocsPathFinder Steam App ID opt-in for Linux Proton lookup

       DocsPathFinder was hard-coding Fallout 4's Steam App ID (377160) into
       its Linux Proton compatdata lookup, which meant a non-FO4 consumer of
       the generic API (Python/Node on Linux/Proton) implicitly probed
       Fallout 4's compatdata prefix while searching for its own game's
       documents folder.

       Make the Steam App ID an opt-in builder field: new DocsPathFinder
       instances default to steam_app_id = None and skip the Proton lookup
       entirely; callers that want FO4 Proton behavior opt in via
       with_steam_app_id(Fallout4Version::Original.steam_app_id()). The CXX
       bridge and TUI opt in directly. Python and Node bindings get a
       set_steam_app_id(app_id) method so generic binding consumers can opt
       in too. The literal 377160 is now sourced from classic_constants_core
       in every opt-in call site, removing the duplicate constant from
       classic-path-core.

       Docs updated per the AGENTS.md docs-sync rule.

     Do NOT use `--no-verify`. Do NOT use `--amend` on any prior commit —
     this is a brand-new single commit. Do NOT add a `Co-Authored-By`
     line unless the user explicitly asked for one (they did not).

  d) After the commit, verify it landed cleanly:

       pwsh -Command "git log -1 --stat"

     Expected: one commit with the `Fix:` prefix, touching the files
     listed above and no others.

Step 5 — Do NOT touch any other file. In particular do NOT update
`.planning/STATE.md` — the `/gsd:quick` orchestrator owns STATE updates, not
the executor.
  </action>
  <verify>
    <automated>
  pwsh -Command "Select-String -Path docs/api/classic-path-core.md -Pattern 'with_steam_app_id'"

Expected: at least 2 matches (API listing + behavior description).

  pwsh -Command "Select-String -Path docs/api/classic-cpp-bridge-game-entrypoints.md -Pattern 'with_steam_app_id'"

Expected: at least 1 match (the new bullet under detect_fallout4_docs_path).

  pwsh -Command "git log -1 --format='%s'"

Expected: starts with `Fix:` and mentions DocsPathFinder / opt-in.

  pwsh -Command "git log -1 --stat"

Expected: touches exactly the files from the `files_modified` frontmatter
list (optionally plus Cargo.lock and optionally plus game-setup-workflow.md
if Step 3 applied). MUST NOT touch classic-cli/, classic-gui/, README.md,
AGENTS.md, CLAUDE.md, or any core crate beyond classic-path-core.
    </automated>
  </verify>
  <done>
- `docs/api/classic-path-core.md` documents `with_steam_app_id` in the
  DocsPathFinder API list AND in the Linux behavior description AND in the
  Contributor Notes AND in the "update this document when you change" list.
- `docs/api/classic-cpp-bridge-game-entrypoints.md` documents that
  `detect_fallout4_docs_path` chains `.with_steam_app_id(Fallout4Version::Original.steam_app_id())`.
- `docs/api/game-setup-workflow.md` either (a) documents the new opt-in in
  both the Documents-path flow and the Source-Backed Limits sections, OR
  (b) was skipped because it did not reference the changed behavior (noted
  explicitly in the SUMMARY).
- A single `Fix:` commit exists containing exactly the files from the plan's
  `files_modified` list (optionally plus `Cargo.lock` and/or
  `game-setup-workflow.md` per above). No C++ frontends touched. No
  `--no-verify`. No `Co-Authored-By` line.
- Final `cargo fmt --check`, `cargo clippy -D warnings`, and
  `cargo test --workspace` all still green.
  </done>
</task>

</tasks>

<verification>
- Single atomic commit with `Fix:` prefix.
- The 7 gates from Task 3 (bun build, node parity, python parity, clippy,
  fmt, test, grep checks) all GREEN.
- The 3 docs files either updated or (for game-setup-workflow.md) explicitly
  noted as not-needing-update.
- `git show HEAD --stat` confirms no file outside the `files_modified` list
  (+ optionally Cargo.lock, + optionally game-setup-workflow.md) was touched.
- No C++ frontend files, no `classic-path-core/src/platform/linux.rs`, no
  shared root docs (README.md, AGENTS.md, CLAUDE.md), no `.planning/STATE.md`
  modified.
- `classic_path_core::DocsPathFinder` source file no longer contains the
  `const FALLOUT_4_STEAM_APP_ID` definition.
- `Fallout4Version::Original.steam_app_id()` is the canonical 377160 source
  for every non-test opt-in call site.
</verification>

<success_criteria>
- A generic DocsPathFinder consumer on Linux no longer implicitly probes
  Fallout 4's compatdata/377160 Proton prefix. Without calling
  `with_steam_app_id` / `set_steam_app_id`, the finder goes straight to
  `~/.local/share/<relative_path>` — proven by the new integration test
  `proton_path_ignored_when_steam_app_id_unset`, which places BOTH a valid
  Proton FO4 docs dir AND a valid local-share dir on disk and asserts
  local-share wins.
- Fallout 4 Proton behavior is unchanged for the in-repo FO4 callers: the
  CXX bridge's `detect_fallout4_docs_path` and the TUI's
  `resolve_xse_folder_for_scan` both explicitly opt in via
  `Fallout4Version::Original.steam_app_id()`, and the 4 pre-existing
  integration tests (updated to chain `.with_steam_app_id(377160)`) still
  pass unchanged.
- Python and Node binding consumers can opt in via
  `DocsPathFinder.set_steam_app_id(app_id)` (Python snake_case) /
  `docsPathFinder.setSteamAppId(appId)` (JavaScript camelCase, auto-generated
  by NAPI).
- The literal 377160 exists exactly once (or twice counting the inline doc
  example) in `classic-path-core/src/docs_path.rs` — no longer as a
  `const FALLOUT_4_STEAM_APP_ID`. The canonical source is
  `classic_constants_core::Fallout4Version::steam_app_id()`. All in-repo
  opt-in call sites pull from there.
- Workspace gates green:
  - `cargo test --workspace`
  - `cargo clippy --workspace --all-targets --all-features -- -D warnings`
  - `cargo fmt --all -- --check`
- Parity gates green:
  - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
  - `bun run parity:gate:local` from `ClassicLib-rs/node-bindings/classic-node`
- Docs under `docs/api/` updated per the AGENTS.md docs-sync rule.
- Single atomic `Fix:` commit, no `--no-verify`, no `Co-Authored-By`.
- C++ frontends (`classic-cli/`, `classic-gui/`) NOT modified, because the
  bridge change in Task 2 already chains the right Steam ID for them.
- No parity gate ignore-list entries were added.
- No emojis anywhere.
</success_criteria>

<output>
After completion, create:
`.planning/quick/260407-rvj-docspathfinder-steam-id-opt-in-for-linux/260407-rvj-01-SUMMARY.md`

Summary MUST include:
- A tight description of the diff in `docs_path.rs` (struct field add, `new`
  update, new `with_steam_app_id` method, rewritten
  `find_docs_path_linux` / `find_docs_path_linux_with`, deleted const).
- The full body of the new `proton_path_ignored_when_steam_app_id_unset` test.
- The full chained call lines inserted in the CXX bridge and TUI.
- The full signatures of the new Python and Node `set_steam_app_id` methods.
- The exact line added to `classic-tui/Cargo.toml` and confirmation that the
  bridge's Cargo.toml needed NO change.
- Confirmation (grep output) that `index.d.ts` contains `setSteamAppId` and
  that it was regenerated, NOT hand-edited.
- Full stdout/stderr of each of the 7 gate commands from Task 3 (exit codes
  visible).
- The exact sections updated in `docs/api/classic-path-core.md` and
  `docs/api/classic-cpp-bridge-game-entrypoints.md`, and either the
  `docs/api/game-setup-workflow.md` updates or the explicit "no update
  needed" note.
- The commit hash, commit message, and `git show --stat HEAD` output.
- An explicit "no files in classic-cli/ or classic-gui/ or
  classic-path-core/src/platform/linux.rs were touched" assertion backed
  by the git-show-stat output.
- An explicit "no parity-gate ignore-list entries were added" assertion.
- Any deviations from the plan (e.g. if `game-setup-workflow.md` was
  skipped, if clippy needed an `#[allow(...)]`, if the let-chain fallback
  was used, if the Node parity gate needed a baseline refresh command).
</output>
