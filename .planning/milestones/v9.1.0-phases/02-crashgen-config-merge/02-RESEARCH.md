# Phase 2: Crashgen -> Config Merge - Research

**Researched:** 2026-04-11
**Domain:** Rust workspace crate consolidation (absorb `classic-crashgen-settings-core` into `classic-config-core`)
**Confidence:** HIGH (pure repo archaeology; every finding grep-verified against working-tree source)

## RESEARCH COMPLETE

## Summary

Phase 2 is a strict structural refactor: move a single 573-line pure-data-model file (`classic-crashgen-settings-core/src/lib.rs`) into `classic-config-core` as a new sibling module `crashgen_rules.rs`, re-export its public surface flat from the config-core crate root, swap import paths across 3 Rust core consumers and 4 binding crates, delete the source crate, and verify three parity gates report zero drift. Everything downstream — Cargo.toml touches, consumer grep counts, doc cross-refs — is small and finite. Phase 2 is genuinely smaller than Phase 1 was, and the CONTEXT.md guidance to not reproduce Phase 1's structure is correct.

Two findings worth elevating that CONTEXT.md does not explicitly name:

1. **`thiserror` is declared in crashgen-settings-core's `Cargo.toml` but is NOT used in `lib.rs`** (0 `thiserror` matches in the entire file — confirmed by grep). The crate is a pure enum/struct rule model with a single `fn evaluate_rules`. When the file moves into config-core (which already carries `thiserror`), no new transitive dep arrives and no `#[derive(Error)]` plumbing needs to carry forward.
2. **`tools/node_api_parity/generate_baseline.py` hardcodes the crate path** at lines 43 and 72 (`RUST_TARGET_CRATES["classic-crashgen-settings-core"] = ".../src/lib.rs"` and `RUST_OWNER_BY_CRATE["classic-crashgen-settings-core"] = "crashgen_settings"`). The Node parity test `tools/node_api_parity/tests/test_generate_baseline_targets.py` also asserts these entries exist. Both will break the instant the directory disappears. The Python parity gate is unaffected because its generator *excludes* crashgen-settings-core with an intentional comment (and a test that asserts exclusion), so the Python side stays green without edits.

**Primary recommendation:** Plan this phase as **two plans**, not three. Plan 02-01 is the Rust core merge (git mv + content edits + consumer migration + crate deletion + stray .bak cleanup), Plan 02-02 is the docs + parity gate alignment + verification. The binding import-path updates stay inside Plan 02-01 because each one is a 1-line edit — splitting them into a separate plan would add scaffolding for no benefit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add crashgen-settings-core's code as a new sibling module: `crashgen_rules.rs` (from `classic-crashgen-settings-core/src/lib.rs` — contains `RuleSeverity`, `ConfigLayout`, `TargetValueType`, `ExpectedValue`, `Predicate`, `PreflightActionKind`, `RuleReportBucket`, `PreflightAction`, `PreflightRule`, `RuleTarget`, `RuleMessages`, `CheckRule`, `CrashgenSettingsRules`, `EvaluationContext`, `OutcomeKind`, `EvaluationOutcome`, `EvaluationResult`, and the `evaluate_rules` function). Existing modules (`config.rs`, `yamldata.rs`, `lib.rs`) stay untouched structurally.
- **D-02:** Single flat file — do NOT split into `crashgen/` subfolder or `crashgen_types.rs + crashgen_eval.rs` pair. Keeps the `git mv` rename clean and preserves full blame history on a single file.
- **D-03:** Flat re-exports at the crate root via `pub use crashgen_rules::*;`. Consumers migrate by swapping `classic_crashgen_settings_core::X` -> `classic_config_core::X`.
- **D-04:** `classic-scanlog-core` already depends on `classic-config-core`; its swap is pure content edit, no Cargo.toml dep delta.
- **D-05:** `classic-scangame-core` does NOT currently depend on `classic-config-core`. It gains `classic-config-core = { path = "../classic-config-core" }` as a new direct dependency. This pulls yaml-rust2, indexmap, tokio-full, dirs, anyhow, serde as new transitive deps.
- **D-06:** `classic-config-core` — remove the crashgen-settings-core dep; update the 1 import in `yamldata.rs`.
- **D-07:** `classic-scanlog-core` — drop the crashgen-settings-core dep (config-core already present); update `orchestrator.rs` (11 refs), `settings_validator.rs` (2 refs), `crashgen_registry.rs` (1 ref).
- **D-08:** `classic-scangame-core` — add config-core dep per D-05, remove crashgen-settings-core dep, update `orchestrator.rs` (1 ref), `crashgen_orchestrator.rs` (1 ref), `toml.rs` (4 refs).
- **D-09:** Keep all binding-crate filenames as-is. `classic-node/src/crashgen_rules.rs`, `classic-config-py/src/lib.rs`, `classic-scangame-py/src/crashgen_rules.rs`, `classic-scanlog-py/src/crashgen_rules.rs` and `classic-scanlog-py/src/settings_validator.rs` each keep their existing filename. Only the `use classic_crashgen_settings_core::X;` lines change.
- **D-10:** Each binding crate's `Cargo.toml` drops `classic-crashgen-settings-core`; adds `classic-config-core` if not already present.
- **D-11:** Delete `ClassicLib-rs/business-logic/classic-crashgen-settings-core/` directory entirely via `git rm -r`. Remove from workspace members.
- **D-12:** Verify-only parity gate strategy. Run CXX, Python, Node gates after the merge; all three should exit 0 with zero drift. If drift appears, investigate as a real bug, not a reason to regenerate baselines. Phase 4 does final cross-merge validation.
- **D-13:** `git mv ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs ClassicLib-rs/business-logic/classic-config-core/src/crashgen_rules.rs` for blame preservation. Content edits in a separate commit.
- **D-14:** Merge `docs/api/classic-crashgen-settings-core.md` content into `docs/api/classic-config-core.md` as a new "Crashgen rule model" section. Delete the source doc. Update `docs/api/README.md` index.
- **D-15:** Update references in active docs only: `CLAUDE.md`, `docs/api/*.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/codebase/*.md`, `AGENTS.md`. Skip archived milestone plans.
- **D-16:** Preserve zero coverage for the absorbed crashgen module. No new tests. Strict structural refactor.
- **D-17:** Delete `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` as a separate commit.
- **D-18:** Remove `"business-logic/classic-crashgen-settings-core"` from the `members = [...]` list in `ClassicLib-rs/Cargo.toml` in the same commit as directory deletion.

### Claude's Discretion

- Exact ordering of operations within each commit
- Internal import organization inside the moved `crashgen_rules.rs`
- How to handle incidental `cargo fmt` churn on neighboring lines
- Workspace `Cargo.lock` updates (mechanical, automatic)
- `#[allow(...)]` lint attributes carrying forward with the moved code
- Whether to verify with `cargo build --workspace` after each subplan or only at the end

### Deferred Ideas (OUT OF SCOPE)

- Splitting the rule model from the evaluator (subfolder or two-file split)
- Adding tests for crashgen rule model
- Relocating crashgen rule types to a foundation-layer crate
- Renaming binding-crate `crashgen_rules.rs` files
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CGEN-01 | classic-crashgen-settings-core source modules relocated into classic-config-core with same public API surface preserved | Full public API inventory below (section 1) enumerates every `pub` item; flat re-export pattern matches Phase 1 precedent |
| CGEN-02 | All workspace crates importing from classic-crashgen-settings-core import from classic-config-core instead | Consumer reference audit below (section 2) lists all 35 import sites across 9 files in 7 crates with exact line numbers |
| CGEN-03 | classic-crashgen-settings-core crate removed from Cargo.toml workspace members and directory deleted | Workspace member location (line 9) and 8 consumer Cargo.toml dep locations documented below (section 2) |
</phase_requirements>

## Project Constraints (from CLAUDE.md / AGENTS.md)

- **Build from Git Bash:** Source `tools/use_msvc_from_git_bash.sh` before any Rust build so Git's `usr/bin/link.exe` doesn't shadow MSVC's linker. Phase 2 is workspace-Rust only, no C++ compile, but `cargo build --workspace` still links Rust executables (classic-tui etc.) so MSVC must be active.
- **PowerShell preferred over Bash** for running commands (user's global CLAUDE.md rule). This matters for the planner's task actions — prefer `pwsh -c "cargo ..."` framing. Note: GSD commit/git tooling through `gsd-tools.cjs` runs under Node and is shell-agnostic.
- **Never write to `nul`** on Windows (creates undeletable file on system drive). Any `> /dev/null` redirects must stay Unix-style (Git Bash), never `> nul`.
- **Commit prefix convention:** `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:` (from CLAUDE.md). Phase 1 used `Refactor:` for the merge commits — Phase 2 should match.
- **Never invoke raw `ctest` or test binaries directly** — but Phase 2 does not run C++ tests.
- **Keep docs synchronized** with API changes (AGENTS.md rule 7). Consult `docs/api/README.md` before changing public Rust APIs — Phase 2 is internally a pure move but removes one doc page (D-14), so `docs/api/README.md` must be updated in the same change.
- **CLAUDE.md technology-stack block explicitly says "18 pure Rust crates" and "v9.1.0 Phase 1 merge: `yaml-core` was absorbed into `classic-settings-core`, reducing the business-logic crate count from 19 to 18."** Phase 2 needs to update this line to "17 pure Rust crates" (or the correct final count — Phase 4 GATE-06 is the canonical update pass, but Phase 2 should still update CLAUDE.md because its guidance rule D-15 names CLAUDE.md as an active doc requiring updates).

## 1. Full Public API Surface of `classic-crashgen-settings-core`

Source: `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` (573 lines, single file, no submodules).

**Every public item** (every `pub` at crate root) that MUST be accessible from `classic_config_core::X` after the merge:

### Enums (10)
| Item | Notes |
|------|-------|
| `RuleSeverity` | `Info \| Warning \| Error`; has `fn parse(&str) -> Option<Self>` |
| `ConfigLayout` | `Og \| Vr \| Unknown`; has `fn parse` |
| `TargetValueType` | `Bool \| Int \| String`; has `fn parse` |
| `ExpectedValue` | `Bool(bool) \| Int(i64) \| String(String)`; note: `fn as_string` is private — do NOT accidentally promote |
| `Predicate` | `Always \| PluginAny(Vec<String>) \| ConfigLayoutIs(ConfigLayout) \| CrashgenVersionLt((u32,u32,u32)) \| All(Vec<Predicate>) \| Any(Vec<Predicate>) \| Not(Box<Predicate>)`; `#[derive(Default)]` with `Always` as default |
| `PreflightActionKind` | `NoticeAndSkipRemaining \| Notice \| Issue`; has `fn parse` |
| `RuleReportBucket` | `Settings \| ErrorInformation`; `#[derive(Default)]` with `Settings` as default; has `fn parse` |
| `OutcomeKind` | `Notice \| Issue \| Success` |

### Structs (7)
| Item | All fields `pub` |
|------|-------------------|
| `PreflightAction` | `kind, bucket, severity, message, fix` |
| `PreflightRule` | `id, when, action` |
| `RuleTarget` | `section, key, value_type` |
| `RuleMessages` | `fail, fix, pass` |
| `CheckRule` | `id, target, when, expect, messages, severity` |
| `CrashgenSettingsRules` | `version, preflight, checks`; `#[derive(Default)]` |
| `EvaluationContext` | `crashgen_name, display_section, installed_plugins, settings, config_layout, crashgen_version` |
| `EvaluationOutcome` | `id, kind, bucket, severity, message, fix, section, setting, expected, actual` |
| `EvaluationResult` | `outcomes, skip_remaining`; `#[derive(Default)]` |

### Free Functions (1)
| Item | Signature |
|------|-----------|
| `evaluate_rules` | `pub fn evaluate_rules(rules: &CrashgenSettingsRules, context: &EvaluationContext) -> EvaluationResult` |

### Private helpers (do NOT re-export — keep private inside `crashgen_rules.rs`)
- `fn evaluate_predicate`
- `fn parse_bool`
- `fn value_matches`
- `fn apply_template`
- `impl ExpectedValue { fn as_string }`
- `#[cfg(test)] mod tests` with `rule_report_bucket_parses_known_values_and_defaults_to_settings`, `base_context`, `evaluate_preflight_skip_remaining`, `evaluate_check_fail_and_pass`. **These unit tests live inline in the source file and will carry forward automatically via `git mv`. They are not a separate `tests/` directory — D-16's "preserve zero coverage" is already respected because the inline tests are preserved, not added.**

**Total items to re-export via `pub use crashgen_rules::*;`:** 8 enums + 9 structs + 1 function = **18 public symbols**. The glob re-export handles all of them in one line.

**Cargo.toml dep reality check:** `classic-crashgen-settings-core/Cargo.toml` declares `thiserror = { workspace = true }` but the source file uses zero `thiserror` — verified by `rg thiserror lib.rs` returning 0 matches. No `#[derive(Error)]`, no `#[error(...)]`. This means:
- No dep needs to carry forward into config-core (config-core already has `thiserror`).
- The leftover `thiserror` dep declaration is dead weight that vanishes with the crate.
- `[lints.rust]` settings in the source Cargo.toml (`deprecated = "deny"`, `rust_2024_compatibility = "deny"`, `unsafe_code = "deny"`, `missing_docs = "warn"`, `unused = "deny"`) are already matched or stricter in config-core's `[lints.rust]` block — no lint regressions expected.

## 2. Consumer Reference Audit (grep-verified)

### Rust core consumers (3 crates, 18 import sites)

**`classic-config-core` — 1 site (D-06)**
- `src/yamldata.rs:9` — `use classic_crashgen_settings_core::{...}` (block import)
- `Cargo.toml:22` — `classic-crashgen-settings-core = { path = "../classic-crashgen-settings-core" }`

**`classic-scanlog-core` — 14 sites across 3 files (D-07)**
- `src/orchestrator.rs` — 11 references: lines 1195, 1198 (`RuleReportBucket`), 1883, 1888, 1890 (`ConfigLayout` in function signature and body), 2534 (block `use` inside a test), 2606 (`ConfigLayout::Unknown`), 2628 (block `use` inside test), 2847, 2856 (test assertions on `ConfigLayout::Og`), 2867 (`ConfigLayout::Unknown`)
- `src/settings_validator.rs` — 2 references: line 16 (top-of-file block `use`), line 630 (block `use` inside `#[cfg(test)] mod tests`)
- `src/crashgen_registry.rs` — 1 reference: line 14 (`use classic_crashgen_settings_core::CrashgenSettingsRules`)
- `Cargo.toml:25` — drop `classic-crashgen-settings-core` dep; `classic-config-core` already present at line 24
- **Count confirms CONTEXT.md claim of 14.**

**`classic-scangame-core` — 6 sites across 3 files (D-08)**
- `src/orchestrator.rs:22` — `use classic_crashgen_settings_core::CrashgenSettingsRules`
- `src/crashgen_orchestrator.rs:26` — `use classic_crashgen_settings_core::CrashgenSettingsRules`
- `src/toml.rs` — 4 references: line 25 (block `use`), line 151 (fully-qualified type in signature `Option<classic_crashgen_settings_core::CrashgenSettingsRules>`), line 181 (same), line 716 (block `use` inside `#[cfg(test)] mod tests`)
- `Cargo.toml:17` — replace `classic-crashgen-settings-core` dep with `classic-config-core = { path = "../classic-config-core" }`. **scangame-core has NO classic-config-core line currently** (verified: `rg classic-config-core classic-scangame-core/Cargo.toml` → 0 matches). This is the only dep-graph-affecting change in Phase 2.
- **Count confirms CONTEXT.md claim of 6.**

### Binding crate consumers (4 crates, 17 import sites)

**`classic-node` (Node binding) — 1 file**
- `src/crashgen_rules.rs:1` — `use classic_crashgen_settings_core::{...}` (block import)
- `Cargo.toml:48` — drop `classic-crashgen-settings-core`; `classic-config-core` already present at line 47. **No dep add needed** (verified).

**`classic-config-py` (Python binding) — 1 file**
- `src/lib.rs:86` — block `use classic_crashgen_settings_core::{...}`
- `src/lib.rs:114,115,116` — `classic_crashgen_settings_core::ConfigLayout::Og|Vr|Unknown` (fully-qualified literal branches)
- `src/lib.rs:150,153,154` — `classic_crashgen_settings_core::PreflightActionKind::NoticeAndSkipRemaining|Notice|Issue`
- **7 total references in one file** (confirmed by `rg -c`)
- `Cargo.toml:18` — drop `classic-crashgen-settings-core`; `classic-config-core` already present at line 16.

**`classic-scanlog-py` (Python binding) — 2 files**
- `src/crashgen_rules.rs:1` — block `use`; line 96 is a doc comment mentioning the crate name in backticks (harmless, but D-15 cross-ref cleanup should update it to the new path)
- `src/settings_validator.rs:78,79` — fully-qualified `classic_crashgen_settings_core::ConfigLayout::parse` and `classic_crashgen_settings_core::ConfigLayout::Unknown`
- `Cargo.toml:24` — drop `classic-crashgen-settings-core`; `classic-config-core` already present at line 23.

**`classic-scangame-py` (Python binding) — 1 file**
- `src/crashgen_rules.rs:1` — block `use`; line 96 is a doc comment mentioning the crate name (same as scanlog-py)
- `Cargo.toml:20` — drop `classic-crashgen-settings-core`. **Classic-config-core is NOT currently in scangame-py's Cargo.toml** (verified by re-reading — only `classic-scangame-core`, `classic-shared-core`, `classic-shared-py`, `classic-file-io-core`, `anyhow` are listed). scangame-py **needs a new `classic-config-core` dep** per D-10. This is a second dep-graph-affecting change CONTEXT.md implies under D-10's "if not already present" clause — the planner should be explicit about it.

### Workspace root
- `ClassicLib-rs/Cargo.toml:9` — `"business-logic/classic-crashgen-settings-core",` workspace members entry (D-18)

### Parity gate tooling files — CRITICAL, not flagged in CONTEXT.md

- **`tools/node_api_parity/generate_baseline.py:43`** — `"classic-crashgen-settings-core": "ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs",` in `RUST_TARGET_CRATES` dict. After the merge, this path is dangling.
- **`tools/node_api_parity/generate_baseline.py:72`** — `"classic-crashgen-settings-core": "crashgen_settings",` in `RUST_OWNER_BY_CRATE` dict.
- **`tools/node_api_parity/generate_baseline.py:37-39`** — inline comment describing the "Phase 4 Plan 1 A1" decision to track this crate.
- **`tools/node_api_parity/generate_baseline.py` owner label `crashgen_settings` in `SQUAD_BY_OWNER`** — the label still needs a squad entry or a KeyError blows up on handoff rendering. Options: (a) remove all three entries and remove the squad assignment, (b) remap the entry to point at `classic-config-core/src/crashgen_rules.rs` with owner `config`. Option (b) is semantically wrong because the Node parity generator tracks *crates as ownership units*, not *modules*. Option (a) is the correct fix: after the merge, the former crashgen surface is subsumed by the config owner, and the generator's existing `classic-config-core: "config"` entry already tracks it. **Verify-only D-12 will fail here unless this file is updated, because the generator's first action is to stat each `RUST_TARGET_CRATES` path and a missing file will cause an exception before the contract comparison even runs.**
- **`tools/node_api_parity/tests/test_generate_baseline_targets.py`** — four assertions that will fail after the merge:
  - Line 39: `assert "classic-crashgen-settings-core" in gb.RUST_TARGET_CRATES`
  - Line 76: `assert "classic-crashgen-settings-core" in gb.RUST_OWNER_BY_CRATE`
  - Plus the two docstring assertions referencing Amendment A1.
  - These tests must be **inverted** (or deleted) so they now assert *absence* post-merge, mirroring the Phase 1 pattern where yaml-core's generator entries were removed.
- **`tools/python_api_parity/generate_baseline.py:46-48`** — exclusion comment. Python generator already excludes crashgen-settings-core (it flows through `classic-config-py`/`classic-scanlog-py`/`classic-scangame-py` wrappers). **No edit needed here**, but the exclusion comment can optionally be reworded as historical context.
- **`tools/python_api_parity/tests/test_generate_baseline_targets.py:33-35`** — `test_classic_crashgen_settings_core_is_excluded` asserts the crate is NOT in `RUST_TARGET_CRATES`. This assertion stays valid after the merge (crate doesn't exist → still not in the dict). **No edit needed**, though the planner may want to simplify the test comment.
- **`.planning/milestones/v9.1.0-bindings-phases/04-node-tier-collapse/_build_plan05_rows.py:206,267`** — archived plan script referencing the old crate name. CONTEXT.md D-15 says skip archived milestone plans; leave this alone.
- **`tools/parity_contract_merge_owner.py`** — the reusable owner-group merge helper used in Phase 1. The `classic-yaml-core` string in it at line 31 is inside a docstring example (`--rust-crate-old classic-yaml-core`). This helper is Phase 2's natural tool for updating the Node parity_contract.json owner-grouping if any re-homing is needed, but since Phase 2 has no *exposed* API renames, the helper likely goes unused this phase. Worth noting for the planner as an available tool.

### Active doc surface (D-15 cross-ref cleanup)

Files found by grep (glob `**/*.md`) that reference `classic-crashgen-settings-core` or `classic_crashgen_settings_core` and are in active (non-archived) doc paths:

| File | Action |
|------|--------|
| `CLAUDE.md` | Update "18 pure Rust crates" → "17"; update/remove the Phase 1 v9.1.0 note line, or append Phase 2 equivalent |
| `AGENTS.md` | No crashgen mentions found via grep (not in the 33-file list); no edit needed |
| `docs/api/classic-crashgen-settings-core.md` | **Delete** (D-14); content merges into classic-config-core.md |
| `docs/api/classic-config-core.md` | Add "Crashgen rule model" section with the 18-item API surface |
| `docs/api/README.md` | Remove the crashgen entry from the numbered index; update the config-core entry description |
| `docs/api/binding-parity-overview.md` | Update references to the former crate; note Phase 2 consolidation |
| `docs/api/classic-scanlog-core.md` | Update any import-path references in examples |
| `docs/api/classic-scangame-core.md` | Update any import-path references in examples |
| `docs/RUST_DOCUMENTATION_INDEX.md` | Remove or redirect the crashgen entry |
| `.planning/REQUIREMENTS.md` | CGEN-01/02/03 checkboxes flip to `[x]` at plan execution (done by verifier, not planner) |
| `.planning/ROADMAP.md` | Phase 2 status line updates (orchestrator concern, not plan content) |
| `.planning/PROJECT.md` | If it carries a crate count or tech-stack block matching CLAUDE.md, update it |
| `.planning/codebase/STRUCTURE.md` | Update business-logic crate list |

Files to leave alone (archived milestone snapshots, per D-15):
- `.planning/milestones/v9.1.0-bindings-phases/**`
- `.planning/milestones/v9.1.0-bugfixes-phases/**`
- `.planning/phases/02-crashgen-config-merge/02-DISCUSSION-LOG.md` (it's input context, not touched)

## 3. Dep-Graph Delta for `classic-scangame-core`

**Current state (verified by reading `classic-scangame-core/Cargo.toml`):**

scangame-core depends on: shared-core, file-io-core, **crashgen-settings-core**, path-core, version-registry-core, tokio, futures, walkdir, ddsfile, sha2, strsim, configparser, toml, encoding_rs, chardetng, scraper, regex, memchr, aho-corasick, rayon, crossbeam, num_cpus, dashmap, parking_lot, lru, rustc-hash, xxhash-rust, string_cache, smartstring, anyhow, thiserror, log, serde, serde_json, ba2 (windows-only).

**Post-Phase-2 state:**
- Remove line 17: `classic-crashgen-settings-core = { path = "../classic-crashgen-settings-core" }`
- Add: `classic-config-core = { path = "../classic-config-core" }`

**New transitive deps pulled in via config-core** (that scangame-core did not already have):
| Dep | Scangame-core already has it? | Source |
|-----|-------------------------------|--------|
| `classic-settings-core` | NO — new transitive | config-core line 21 |
| `classic-registry-core` | NO — new transitive | config-core line 18 |
| `classic-version-registry-core` | YES (already direct at scangame line 19) | — |
| `classic-shared-core` | YES (direct) | — |
| `tokio` full features | YES (direct) | — |
| `yaml-rust2` | NO — new transitive | config-core line 29 |
| `hashlink` | NO — new transitive | config-core line 30 |
| `indexmap` | NO — new transitive | config-core line 33 |
| `serde`, `serde_json` | YES (direct) | — |
| `dirs` | NO — new transitive | config-core line 38 |
| `thiserror`, `anyhow`, `log` | YES (direct) | — |

So the dep graph genuinely grows. Nothing catastrophic — these are all already in the workspace Cargo.lock because other crates consume them — but `cargo tree -p classic-scangame-core` output will lengthen, and `cargo build -p classic-scangame-core` cold-build times will rise because config-core itself must now build first in scangame-core's build plan. This is mentioned in CONTEXT.md's "specifics" block as worth explicit verification.

**Exact Cargo.toml diff for `classic-scangame-core/Cargo.toml`:**
```diff
 classic-file-io-core = { path = "../classic-file-io-core" }
-classic-crashgen-settings-core = { path = "../classic-crashgen-settings-core" }
+classic-config-core = { path = "../classic-config-core" }
 classic-path-core = { path = "../classic-path-core" }
```

**Exact Cargo.toml diff for `classic-scangame-py/Cargo.toml`** (needs identical treatment — not called out in CONTEXT.md but required by D-10):
```diff
 classic-scangame-core = { path = "../../business-logic/classic-scangame-core" }
-classic-crashgen-settings-core = { path = "../../business-logic/classic-crashgen-settings-core" }
+classic-config-core = { path = "../../business-logic/classic-config-core" }
```

All other Cargo.toml edits are pure deletions (no adds) because the consuming crate already lists classic-config-core.

## 4. Phase 1 Patterns to Reuse

Read `.planning/phases/01-yaml-settings-merge/01-01-PLAN.md` (plan frontmatter already enumerates files_modified, must_haves, artifacts, key_links — copy the shape). Read `01-VERIFICATION.md` (which this research already inlines) for the exact truths-table shape the verifier expects.

**Patterns to carry forward:**

1. **Plan frontmatter shape** — YAML block with `files_modified`, `must_haves.truths`, `artifacts`, `key_links`, `requirements`. Phase 1's Plan 01 had ~35 files listed; Phase 2 will have fewer (~15-18). The `key_links` section is high-value — it lists explicit `from: file, to: target, via: use statement, pattern: rg regex` entries so the verifier can grep each link.
2. **Commit ordering** — Phase 1 used: `git mv` (rename-only commit, buildable) → content edits (imports fixed, dep Cargo.toml edits, workspace member removed) → binding migrations → docs → parity gates. Phase 2 collapses this because there's no bridge renaming, no binding crate deletion, no test migration. Compressed sequence:
   - **Commit 1 (rename-only):** `git mv .../classic-crashgen-settings-core/src/lib.rs .../classic-config-core/src/crashgen_rules.rs`. Workspace does NOT compile yet (the inline module has no `mod crashgen_rules;` declaration, and the old crate still exists in workspace members referencing a deleted `src/lib.rs`). **Acceptance: `git status` shows a single rename; nothing else.** Phase 1's commit `3276fd20` did the equivalent.
   - **Commit 2 (content edits):** Add `mod crashgen_rules;` + `pub use crashgen_rules::*;` to `config-core/src/lib.rs`. Update `yamldata.rs` import. Remove crashgen-settings-core dep from config-core's Cargo.toml. Remove the now-orphaned `Cargo.toml` file from the deleted crate directory via `git rm -r` (delete the entire directory). Remove the workspace members entry. **Acceptance: `cargo build --workspace` green; `cargo test --workspace` green.**
   - **Commit 3 (consumer migration — scanlog-core):** Swap `classic_crashgen_settings_core::X` → `classic_config_core::X` in 14 sites. Drop Cargo.toml dep. **Acceptance: `cargo build -p classic-scanlog-core` green.**
   - **Commit 4 (consumer migration — scangame-core):** Same swap in 6 sites. **Add `classic-config-core` dep** (dep-graph delta). Drop `classic-crashgen-settings-core` dep. **Acceptance: `cargo build -p classic-scangame-core` green; `cargo tree -p classic-scangame-core | grep classic-config-core` confirms the new transitive.**
   - **Commit 5 (binding migrations):** Four binding crates in one commit — import swaps + Cargo.toml edits (dropping the dep in 4 files, adding classic-config-core to 1 file: scangame-py). All 1-line edits. **Acceptance: full `cargo build --workspace` + `cargo test --workspace` green.**
   - **Commit 6 (stray file cleanup — D-17):** `git rm ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` as a **separate commit**, explicitly called out by D-17. Label it `Chore: remove stale yamldata.rs.bak backup`.
   - **Commit 7 (docs consolidation — D-14, D-15):** Merge `classic-crashgen-settings-core.md` into `classic-config-core.md`. Delete the source doc. Update `README.md` index. Update CLAUDE.md crate count. Update `.planning/codebase/STRUCTURE.md`. Update `binding-parity-overview.md`. Update `RUST_DOCUMENTATION_INDEX.md`.
   - **Commit 8 (parity tooling update):** Edit `tools/node_api_parity/generate_baseline.py` — remove the 3 entries (target, owner, squad). Edit `tools/node_api_parity/tests/test_generate_baseline_targets.py` — invert or delete the 2 assertions. **Acceptance: `python -m pytest tools/node_api_parity/tests/ -q` green.**
   - **Commit 9 (parity verification — D-12):** Run all three gates. Expect 0 drift. Capture outputs into the plan SUMMARY.
3. **Commits 3, 4, 5 could merge into one commit** ("consumer migration across Rust core + bindings") if the planner prefers fewer commits, but Phase 1 precedent is to keep them separate for bisect granularity. Recommend keeping at least the rust-core vs. binding split for readability.
4. **`git mv` semantics on Windows** — Git on Windows preserves blame across renames only when `git mv` is followed by a commit with *just* the rename, no content edits. Phase 1 commit `3276fd20` (rename) preceded commit `ec596e0e` (content). Phase 2 must follow the same discipline or blame gets muddled.
5. **Artifact generation ordering** — Phase 1 ran parity gates LAST, after all consumer migrations and doc updates. Phase 2 matches this.

**Phase 1 pitfalls surfaced in `01-VERIFICATION.md` "Observations":**
- Stale `docs/implementation/*/rust_api_surface.json` snapshots were left behind even though `parity_contract.json` was clean. Root cause: those snapshots are WRITE-ONLY artifacts of the parity generator, not gate inputs, and the Phase 1 baseline regeneration commit did not include them. **Phase 2 lesson:** since Phase 2 is verify-only (D-12), the planner does NOT need to commit a regenerated `rust_api_surface.json`. If the gates run and those snapshots update as a side effect, they can be committed or left uncommitted — but the committed baseline `parity_contract.json` files are the only authoritative input. Recommend: add a verification step that explicitly greps `parity_contract.json` for `classic-crashgen-settings-core` post-merge and asserts zero matches. The baselines themselves do not need touching.
- Two pre-existing pytest failures in `test_parity_gate_tooling.py::test_update_baseline_flag_refreshes_stale_baseline` (unsupported `--deferred-registry` flag). These were noted as pre-existing and NOT a Phase 1 gap. **Update:** these were later fixed in quick task `260410-wsw` (commit `f0b6aa17`), so Phase 2 starts with a clean pytest baseline. Verify this assumption holds before running gates.

## 5. Parity Gate Commands and Expected Outputs (D-12 verify-only)

All commands assume working directory is repo root (`J:/CLASSIC-Fallout4`).

### CXX parity gate
```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
```
Expected exit code: `0`. Expected signal: summary line `CXX parity gate: OK` or equivalent. The CXX baseline lives at `tools/cxx_api_parity/baseline/parity_contract.json`. Crashgen-settings-core has **no direct CXX bridge module** (confirmed earlier in this file: "no `crashgen.rs` in `classic-cpp-bridge`"), so the CXX baseline should have zero references to it already. Post-merge, CXX gate should still report zero drift without any baseline edit.

**Pre-run sanity grep:**
```powershell
rg "classic-crashgen-settings-core|classic_crashgen_settings_core" tools/cxx_api_parity/baseline/
```
Expect 0 matches both pre-merge and post-merge.

### Python parity gate
```powershell
./rebuild_rust.ps1 -Target python
python tools/python_api_parity/check_parity_gate.py --repo-root .
```
Expected exit code: `0`. Expected signal: `deferred_total == 0`. **Rebuild is required** because the Python gate compares the installed PyO3 wheel's runtime surface against the committed `parity_contract.json`; if the wheel is stale (still imports `classic_crashgen_settings_core`), the gate will drift. The `rebuild_rust.ps1` script lives at repo root.

### Node parity gate
```powershell
cd ClassicLib-rs/node-bindings/classic-node
bun install   # only if bun.lockb or node_modules are stale
bun run parity:gate:local
```
Expected exit code: `0`. The gate script is defined in `ClassicLib-rs/node-bindings/classic-node/package.json`. The Node gate will **break immediately post-merge** unless `tools/node_api_parity/generate_baseline.py` is updated (Commit 8 above) — the generator will crash when it tries to stat the deleted crate's lib.rs, before the contract diff even runs. The planner MUST sequence Commit 8 before running the Node gate.

**Cross-verification greps** (after the merge is merged but before gates run):
```powershell
rg "classic-crashgen-settings-core|classic_crashgen_settings_core" ClassicLib-rs/**/Cargo.toml   # expect 0 (Rust)
rg "classic-crashgen-settings-core|classic_crashgen_settings_core" docs/implementation/*/baseline/parity_contract.json   # expect 0
rg "use classic_crashgen_settings_core" ClassicLib-rs/                                            # expect 0 (no live imports)
```

## 6. Build / Test Commands (CLAUDE.md verified)

```bash
# From repo root
source tools/use_msvc_from_git_bash.sh   # if running from Git Bash

# Primary build + test
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml

# Per-crate incremental (useful per commit during development)
cargo build -p classic-config-core --manifest-path ClassicLib-rs/Cargo.toml
cargo build -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml
cargo build -p classic-scangame-core --manifest-path ClassicLib-rs/Cargo.toml

# Format + lint gates (CLAUDE.md "pre-commit minimum")
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings

# Format fix
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml
```

**PowerShell equivalents** (user preference):
```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

**No C++ build required for Phase 2** (no CXX bridge surface change). The C++ `build_cli.ps1` / `build_gui.ps1` scripts do not need to run, saving ~10 minutes per verification cycle. Phase 4 will do the final cross-cutting C++ verification.

**No Node/Python binding rebuild required for verification per se** (the Rust-side `cargo build --workspace` covers the rlib compile of all binding crates). However, the Python parity gate DOES require `rebuild_rust.ps1 -Target python` because it inspects the installed wheel's runtime surface, and the Node parity gate requires no extra rebuild because `bun run parity:gate:local` handles it internally.

## 7. Environment Availability

Phase 2 depends only on tools that are required by all Phase 1 work and are known-available on the dev machine. Quick checklist:

| Dependency | Required By | Available | Version check |
|------------|-------------|-----------|----------------|
| Rust 1.85+ | `cargo build --workspace` | Assumed YES | `cargo --version` |
| Git | `git mv`, `git rm -r`, commits | Assumed YES | — |
| Python 3.12 | `python tools/*/check_parity_gate.py` | Assumed YES (Python parity gates ran in phase 1) | — |
| Bun | `bun run parity:gate:local` | Assumed YES (phase 1 ran Node gates) | — |
| MSVC linker (via `use_msvc_from_git_bash.sh`) | `cargo build --workspace` final link | Assumed YES | — |
| uv (Python project manager) | `uv run pytest` if tests needed | Assumed YES | — |

**Nothing missing.** Phase 2 is a pure internal refactor; no new tooling is needed beyond what Phase 1 already exercised.

## Runtime State Inventory

Phase 2 is a **Rust-only structural refactor**. Per the rename/refactor protocol:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified. The crashgen rule model is pure code (enums, structs, `fn evaluate_rules`). No database keys, no on-disk YAML, no collection names, no user IDs reference `classic_crashgen_settings_core` — it's a module name, not data. | None |
| Live service config | None — verified. No external service (n8n, Datadog, Tailscale, Cloudflare) knows about Rust crate names. | None |
| OS-registered state | None — verified. No Windows scheduled task, pm2 process, systemd unit, or launchd plist references the crate name. | None |
| Secrets/env vars | None — verified. No env var or secret key embeds `crashgen_settings_core` or `classic-crashgen-settings-core`. Phase 1 precedent: yaml-core merge had zero env var impact. | None |
| Build artifacts / installed packages | **Cargo.lock** will auto-update when `classic-crashgen-settings-core` is removed and scangame-core gains `classic-config-core`. Mechanical, handled by `cargo build`. **Python wheel** (`classic_config`, `classic_scanlog`, `classic_scangame`) must be rebuilt via `./rebuild_rust.ps1 -Target python` before running the Python parity gate, because the old wheel has the old symbol table. **Node `.node` native addon** — `bun run parity:gate:local` rebuilds it automatically. **Target directory** — `cargo clean` is NOT required; incremental rebuild handles the removal correctly. | `rebuild_rust.ps1 -Target python` before Python parity gate |

The canonical rename-phase question — *"After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?"* — answer: **only the installed Python wheel**, which `rebuild_rust.ps1` refreshes mechanically. Everything else updates at the next `cargo build`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `cargo test` (built-in Rust test harness), `pytest` for parity tooling tests, `bun test` for Node parity |
| Config file | `ClassicLib-rs/Cargo.toml` (workspace), `tools/python_api_parity/pyproject.toml` if present, `ClassicLib-rs/node-bindings/classic-node/package.json` |
| Quick run command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | The quick run IS the full suite for Phase 2. Plus three parity gates. |
| Phase gate | All parity gates green + workspace tests green |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CGEN-01 | All 18 public symbols from old crate accessible via `classic_config_core::X` | compile-only | `cargo build -p classic-config-core` | YES |
| CGEN-01 | Inline unit tests from crashgen lib.rs (4 tests) still pass from new location | unit | `cargo test -p classic-config-core --lib crashgen_rules::tests` | Will exist after `git mv` |
| CGEN-02 | Workspace has zero `classic_crashgen_settings_core::` imports | grep | `rg "use classic_crashgen_settings_core" ClassicLib-rs/` returns 0 | — |
| CGEN-02 | Workspace has zero `classic-crashgen-settings-core` Cargo.toml deps | grep | `rg "classic-crashgen-settings-core" ClassicLib-rs/**/Cargo.toml` returns 0 | — |
| CGEN-02 | Every former consumer still compiles | compile | `cargo build --workspace` exits 0 | — |
| CGEN-02 | Every former consumer's tests still pass | unit+integration | `cargo test --workspace` exits 0 | — |
| CGEN-03 | Crate directory does not exist | filesystem | `test ! -d ClassicLib-rs/business-logic/classic-crashgen-settings-core` | — |
| CGEN-03 | Workspace members list has no crashgen entry | grep | `rg "classic-crashgen-settings-core" ClassicLib-rs/Cargo.toml` returns 0 | — |
| CGEN-03 | CXX parity gate green (no drift) | integration | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 | — |
| CGEN-03 | Python parity gate green with `deferred_total == 0` | integration | `./rebuild_rust.ps1 -Target python && python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0 | — |
| CGEN-03 | Node parity gate green | integration | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` exits 0 | — |
| CGEN-03 (ancillary) | Node parity generator tooling tests pass after D-12 tooling edit | unit | `python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q` exits 0 | — |

### Sampling Rate
- **Per task commit:** `cargo build --workspace` (fast — ~30s incremental) is the per-commit gate. The rename-only commit (Commit 1) is the explicit exception: it will NOT compile in isolation and the planner must document this.
- **Per wave merge:** `cargo test --workspace` + `cargo clippy --workspace -- -D warnings`.
- **Phase gate:** All three parity gates + full workspace test suite before `/gsd:verify-work`.

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements:
- Rust test harness already in place (cargo test).
- Parity gate scripts already in place (three gate entry points).
- The 4 inline unit tests inside the moved `crashgen_rules.rs` carry forward automatically with `git mv`.
- No new test files to add. **D-16 forbids adding new tests for the absorbed module.**

## 8. Recommended Plan Shape

**Recommendation: TWO plans**, executed sequentially (single wave; second plan depends on first).

### Plan 02-01: Rust core merge + consumer migration + crate deletion

Covers Commits 1-6 from section 4 above.

- **Scope:** `git mv` source file; add module declaration and re-export to config-core lib.rs; update 1 config-core import; swap 14 scanlog-core imports and drop dep; swap 6 scangame-core imports and add config-core dep (the only dep-graph delta); swap binding imports across 4 binding crates (17 sites) with 1 binding-crate dep add (scangame-py); delete crate directory; remove workspace member; delete `yamldata.rs.bak` as its own commit.
- **Requirements covered:** CGEN-01, CGEN-02, CGEN-03.
- **Must-have truths:**
  - `cargo build --workspace` green
  - `cargo test --workspace` green
  - 0 matches for `classic-crashgen-settings-core` in any Cargo.toml
  - 0 matches for `use classic_crashgen_settings_core` in any .rs file outside doc-comment migration markers
  - Directory `ClassicLib-rs/business-logic/classic-crashgen-settings-core/` absent
  - File `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs.bak` absent
- **Commit count:** 5-6 commits (can merge consumer-migration commits if desired; rename-commit and content-commit must stay separate for blame preservation).
- **Autonomous:** yes.

### Plan 02-02: Docs consolidation + parity tooling update + parity gate verification

Covers Commits 7-9 from section 4.

- **Scope:** Merge crashgen API doc into config-core doc and delete source; update docs/api/README.md index; update active doc cross-refs (CLAUDE.md crate count line, `.planning/codebase/STRUCTURE.md`, `docs/api/binding-parity-overview.md`, `docs/RUST_DOCUMENTATION_INDEX.md`, relevant `docs/api/classic-scanlog-core.md` and `classic-scangame-core.md` mentions); update `tools/node_api_parity/generate_baseline.py` (remove 3 entries); invert/delete 4 Node parity test assertions; run all three parity gates; capture output evidence into SUMMARY.
- **Requirements covered:** CGEN-02 (finalized via gate verification), ancillary GATE-01..04 preview (full gate pass gets finalized in Phase 4).
- **Must-have truths:**
  - `docs/api/classic-crashgen-settings-core.md` absent
  - `docs/api/classic-config-core.md` contains a "Crashgen rule model" section
  - `docs/api/README.md` no longer lists the deleted doc in its index
  - `python -m pytest tools/node_api_parity/tests/ -q` exits 0
  - CXX parity gate exits 0 with 0 drift
  - Python parity gate exits 0 with `deferred_total == 0`
  - Node parity gate exits 0 with 0 drift
- **Depends on:** Plan 02-01 (must be committed and merged before parity gates can pass)
- **Autonomous:** yes, though the parity gate invocation requires the dev machine's Python/bun environment to be active.

### Why not 3 plans like Phase 1?

Phase 1 used 3 plans because it had three distinct concerns: (1) Rust core merge, (2) binding consolidation including a bridge rename + a binding crate deletion + Node test merge + Python module merge, (3) test migration + docs + parity baseline regeneration. Phase 2 has NO binding crate deletion, NO bridge surface change, NO new tests, NO baseline regeneration, NO Node spec-file merge. Binding changes collapse into 17 trivial import-line swaps that belong in the same plan as the Rust core merge. Splitting them would add plan scaffolding for no information gain.

### Wave structure

Single wave. Plan 02-02 begins only after Plan 02-01 is fully committed and merged. No parallelism between the two plans — Plan 02-02 inherently depends on the merged filesystem state from Plan 02-01.

### Estimated commit count

- Plan 02-01: 5-6 commits
- Plan 02-02: 3 commits (docs, parity tooling, verification-only commit capturing gate outputs)
- **Total phase: ~8-9 commits** (Phase 1 had ~10 commits across 3 plans, which supports "fewer, smaller" CONTEXT.md guidance).

## 9. Common Pitfalls

### Pitfall 1: Committing content edits with the `git mv` rename
**What goes wrong:** Git's rename detection kicks in only if the commit looks like a pure rename (no significant content diff). Mixing the rename with content edits (adding `pub use`, updating imports) can cause `git blame` to attribute all lines to the new commit rather than preserving the original author/date.
**Why it happens:** Git renames are heuristic, not explicit.
**How to avoid:** Phase 1 D-15 pattern — split rename and content into two commits. Verify with `git log --follow --oneline ClassicLib-rs/business-logic/classic-config-core/src/crashgen_rules.rs` showing pre-Phase-2 history.
**Warning sign:** `git log --follow` on the renamed file shows only Phase 2 commits.

### Pitfall 2: Forgetting scangame-py also needs the new config-core dep
**What goes wrong:** CONTEXT.md D-10 says "if not already present" for the config-core dep add in binding crates. Three of four bindings (classic-node, classic-config-py, classic-scanlog-py) already have config-core. **scangame-py does not** — confirmed by grep of its Cargo.toml. If the planner treats D-10 as "only drop the dep", scangame-py will fail to compile.
**How to avoid:** Plan must explicitly enumerate the scangame-py Cargo.toml diff (see section 3) — not leave it to "if not already present" implicit logic.
**Warning sign:** `cargo build -p classic-scangame-py` errors with `unresolved import classic_config_core`.

### Pitfall 3: Node parity generator crash before gate runs
**What goes wrong:** `tools/node_api_parity/generate_baseline.py` hardcodes the old crate path at line 43. The moment `classic-crashgen-settings-core/src/lib.rs` is deleted, any re-run of the Node gate will crash trying to open that path — not drift-report, crash. D-12 verify-only assumes the gate can *run*.
**How to avoid:** Update the generator's `RUST_TARGET_CRATES`, `RUST_OWNER_BY_CRATE`, and `SQUAD_BY_OWNER` entries in Plan 02-02 Commit 8 *before* invoking `bun run parity:gate:local`. Also update the test file `tools/node_api_parity/tests/test_generate_baseline_targets.py`.
**Warning sign:** `FileNotFoundError: [Errno 2] No such file or directory: '.../classic-crashgen-settings-core/src/lib.rs'` during gate run.

### Pitfall 4: Assuming verify-only means "no tooling edits"
**What goes wrong:** D-12 says "verify-only, expect zero drift" and PHASE 4 does final baseline regeneration. A reader could infer that nothing under `tools/` needs touching. But D-12 is about *baseline files* (the `parity_contract.json` snapshots), not *generator scripts*. The generator scripts are code that needs to compile and run; they are not baselines.
**How to avoid:** Separate "baselines" from "tooling code" in the planner's mental model. Baselines = verify-only (no edits). Tooling code = must be kept working (edits permitted and required).
**Warning sign:** Plan has no commit touching `tools/node_api_parity/` even though the crate is being deleted.

### Pitfall 5: Cargo.lock churn as a review distraction
**What goes wrong:** Removing the old crate and adding `classic-config-core` to scangame-core/scangame-py will re-sort the lockfile's `[[package]]` blocks. This generates a large diff (~40 lines) that looks scary but is purely mechanical.
**How to avoid:** Commit `Cargo.lock` changes alongside the Cargo.toml edits, not in a separate commit. Make the commit message explicit: `Refactor: remove classic-crashgen-settings-core dep (Cargo.lock regenerated)`.
**Warning sign:** Review confusion over lockfile diff size.

### Pitfall 6: `cargo fmt` churn on neighboring lines
**What goes wrong:** Editing a `use classic_crashgen_settings_core::{...}` block can trigger rustfmt to reflow the block or its neighbors. Phase 1 ran into this.
**How to avoid:** Run `cargo fmt --all` at the end of each content-edit commit so the next commit doesn't surprise-format anything.
**Warning sign:** Diff shows unrelated indentation changes in files you didn't intend to touch.

## 10. State of the Art

Nothing changes. The rule model is stable data. No external libraries, no framework upgrades, no API contract migrations. Phase 2 is repo-internal reorganization only.

## Open Questions

1. **Should `.planning/codebase/STRUCTURE.md` be updated in Phase 2 or deferred to Phase 4 GATE-06?**
   - What we know: D-15 names it as an active doc. CLAUDE.md also names 18 crates in the tech stack. CONTEXT.md D-15 includes `.planning/codebase/*.md` in the update list.
   - What's unclear: Whether Phase 4 GATE-06 regenerates this file from a canonical source or just edits it by hand. If the former, Phase 2 edits will be clobbered.
   - Recommendation: Update it in Phase 2 Plan 02-02 anyway — it's a trivial line edit and matches D-15 literally. Phase 4 can adjust if needed.

2. **Should the inline unit tests inside `crashgen_rules.rs` (4 tests after `git mv`) be counted toward D-16's "zero coverage" rule?**
   - What we know: D-16 says "preserve zero coverage for the absorbed crashgen module". The source file DOES contain a `#[cfg(test)] mod tests` block with 4 tests (`rule_report_bucket_parses_known_values_and_defaults_to_settings`, `evaluate_preflight_skip_remaining`, `evaluate_check_fail_and_pass`, plus `base_context` helper).
   - What's unclear: "Zero coverage" — does this mean the crate has no external integration tests (true: no `tests/` dir, no `benches/` dir) or does it mean zero tests anywhere (false: inline tests exist)?
   - Recommendation: Interpret D-16 as "don't *add* new tests". The existing 4 inline tests carry forward via `git mv` automatically and run from their new crate location as `cargo test -p classic-config-core --lib crashgen_rules::tests`. No action needed unless user says otherwise.

3. **Should Phase 2 update CLAUDE.md's "18 pure Rust crates" line, or defer to Phase 4?**
   - What we know: CLAUDE.md says "v9.1.0 Phase 1 merge: ``yaml-core`` was absorbed into `classic-settings-core`, reducing the business-logic crate count from 19 to 18." D-15 names CLAUDE.md as an active doc requiring updates.
   - What's unclear: Whether updating the count incrementally (19→18→17→16) reads cleanly in the doc, or whether Phase 4 should do a single sweep.
   - Recommendation: Phase 2 updates the count line to reflect 17 crates (or whatever the exact Phase 2 post-state is) and appends a one-line Phase 2 note, matching Phase 1's pattern. Phase 4 does a final cleanup pass to add Phase 3.

## Sources

### Primary (HIGH confidence — direct file reads)
- `.planning/phases/02-crashgen-config-merge/02-CONTEXT.md` — all 18 user decisions
- `.planning/REQUIREMENTS.md` — CGEN-01/02/03 definitions
- `.planning/ROADMAP.md` — Phase 2 goal and success criteria
- `.planning/STATE.md` — project state
- `.planning/phases/01-yaml-settings-merge/01-01-PLAN.md` — Phase 1 plan frontmatter shape (template for Phase 2 plans)
- `.planning/phases/01-yaml-settings-merge/01-VERIFICATION.md` — Phase 1 verification shape + stale-snapshot pitfall
- `.planning/phases/01-yaml-settings-merge/01-RESEARCH.md` — Phase 1 research format
- `ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs` — full 573-line source
- `ClassicLib-rs/business-logic/classic-crashgen-settings-core/Cargo.toml` — source crate deps
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` — current 27-line crate root
- `ClassicLib-rs/business-logic/classic-config-core/Cargo.toml` — target crate deps
- `ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml` — verified NO config-core dep
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` — verified config-core already present
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` — verified config-core already present
- `ClassicLib-rs/python-bindings/classic-config-py/Cargo.toml` — verified config-core already present
- `ClassicLib-rs/python-bindings/classic-scanlog-py/Cargo.toml` — verified config-core already present
- `ClassicLib-rs/python-bindings/classic-scangame-py/Cargo.toml` — verified NO config-core dep (second dep-graph delta)
- `ClassicLib-rs/Cargo.toml` — workspace members list (line 9)
- `tools/node_api_parity/generate_baseline.py` — hardcoded crate target (lines 43, 72)
- `tools/node_api_parity/tests/test_generate_baseline_targets.py` — assertions that need inversion (lines 33-77)
- `tools/python_api_parity/generate_baseline.py` — exclusion comment (lines 46-48)
- `CLAUDE.md`, `AGENTS.md`, `docs/api/README.md` — project instructions and active doc surface
- Grep evidence: 35 import sites across 9 files, all line numbers verified against working-tree source

### Secondary (MEDIUM confidence — grep-inferred, not verified line-by-line)
- Count of 33 `**/*.md` files mentioning `classic_crashgen_settings_core` — filenames listed via grep, individual content not re-read for each file. Most matches are in archived milestone plans (skip per D-15) or CONTEXT.md self-reference.

### Tertiary (LOW confidence)
None. All findings in this research are directly verifiable from the repo working tree. No WebSearch was used (intentional — this is repo archaeology, not library documentation).

## Metadata

**Confidence breakdown:**
- Public API surface: HIGH — read every line of the 573-line source file
- Consumer reference counts: HIGH — every reference grep-verified with line numbers
- Dep-graph delta: HIGH — Cargo.toml files read directly for config-core, scangame-core, scanlog-core, node, config-py, scanlog-py, scangame-py
- Phase 1 precedent: HIGH — PLAN 01-01 frontmatter + VERIFICATION read directly
- Parity tooling gotcha: HIGH — `generate_baseline.py` line numbers verified by grep output
- Pitfalls: MEDIUM — derived from Phase 1 VERIFICATION observations plus Rust/Git general knowledge
- Plan shape recommendation: MEDIUM — derived from Phase 1 shape and Phase 2 scope comparison; the planner may legitimately choose to split differently

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days — repo is stable, no imminent upstream changes expected)
