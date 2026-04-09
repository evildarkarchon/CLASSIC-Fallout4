# Phase 4: Node Tier Collapse - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Collapse the Node parity gate's Tier-1/Tier-2 split into a single enforced contract. Promote all currently-deferred Node parity entries from the Tier-2 backlog to enforced Tier-1 rows in `docs/implementation/node_api_parity/baseline/parity_contract.json`. Expand `tools/node_api_parity/generate_baseline.py::RUST_TARGET_CRATES` from the current 10 entries to 18 (matching Phase 3's set, excluding `classic-crashgen-settings-core` which has no Node binding crate). Delete the `RUST_FULL_INVENTORY_CRATES` filter so every tracked crate produces full public-symbol output. Add a bidirectional `validate_contract_surface()` helper in `check_parity_gate.py` that asserts both `rustSymbol ∈ rust_surface` AND `nodeExport ∈ node_surface (index.d.ts)` — fires unconditionally on every gate invocation. Regenerate and commit `index.d.ts` per wave atomically with the Rust source change. Add `extractPeVersion(path)` and `isValidPePath(path)` NAPI functions delegating to `classic_version_core::pe_version::extract_pe_version` and `is_valid_executable_path` (HARM-01, HARM-02). Remove `tierDefinitions.tier2`, `gap_type=rust_unmapped` / `gap_type=node_unmapped` branches, and empty `deferred_runtime_backlog.json::entries` in a single M7-style atomic cleanup commit (matching Phase 3 Plan 09b precedent). Phase 6 still owns governance file deletion and `--deferred-registry` argument tolerance.

**In scope:**
- `tools/node_api_parity/generate_baseline.py` — expand `RUST_TARGET_CRATES` from 10 to 18, delete `RUST_FULL_INVENTORY_CRATES` and `include_rust_symbol()`, add `RUST_OWNER_BY_CRATE` rows for new crates, expand `SQUAD_BY_OWNER` to cover new owners
- `tools/node_api_parity/check_parity_gate.py` — add `validate_contract_surface()` bidirectional guard run unconditionally on every invocation
- `ClassicLib-rs/node-bindings/classic-node/src/<module>.rs` (existing 20 modules) — add `#[napi]` exports for promoted entries; the wrapper types already exist (this phase exposes them, does not add new bindings)
- `ClassicLib-rs/node-bindings/classic-node/src/version.rs` — append `extract_pe_version` and `is_valid_pe_path` NAPI exports (HARM-01/02)
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` — regenerate per wave commit via `napi build --release`; bundled atomically with Rust source change
- `docs/implementation/node_api_parity/baseline/parity_contract.json` — add ~109 promoted contract rows + 2-3 PE-version rows; delete `tierDefinitions.tier2`
- `docs/implementation/node_api_parity/baseline/{rust_api_surface.json, node_api_surface.json, parity_diff_report.{json,md}, runtime_coverage_summary.{json,md}, tier1_gate_report.md}` — refresh per wave plan
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` — add a row per promoted contract entry pointing to its bun:test nodeid; selectors use `_stable_id_hash` full 64-char SHA-256
- `ClassicLib-rs/node-bindings/classic-node/__test__/<module>.spec.ts` (existing 20 spec files) — append new `describe` blocks for promoted entries
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` — add one representative cross-runtime smoke test per promoted module
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json::entries` — empty (preserve file shape for Phase 6 to delete)

**Out of scope:**
- Phase 3 Python Tier Collapse (already shipped 2026-04-08)
- Deletion of `docs/implementation/node_api_parity/governance/` files — Phase 6 owns this (DOC-02, DOC-03, DOC-04)
- Making the `--deferred-registry` argument optional / missing-tolerant in `check_parity_gate.py` or `generate_baseline.py` — Phase 6 owns this (DOC-01)
- Rewriting `docs/api/binding-parity-overview.md` — Phase 6 owns this (DOC-05)
- Per-binding error-contract documentation (`docs/api/error-contract.md`) — Phase 6 owns this (HARM-05)
- Standardizing error conventions across bindings — explicit anti-feature (PROJECT.md Out of Scope; Pitfall 7); Phase 4 preserves the existing `to_napi_err` message-only convention
- Adding new Cargo workspace dependencies — `pelite` stays confined to `classic-version-core` per HARM-01 requirement text (no direct `pelite` dep added to `classic-node`)
- CI wiring for the parity gate — Phase 5 (CI-02 verifies the Phase 4 gate stays green in CI)
- Any C++ bridge surface change (Phase 2 is complete; Phase 4 is Node-only)
- `classic-shared-core` exposure as a standalone Node binding — HARM-03/04 was Python-only and already shipped in Phase 3; Phase 4 has no equivalent Node binding crate to enroll
- Adding `.code` field to existing or promoted error types — Phase 4 preserves message-only `to_napi_err`; HARM-05 (Phase 6) documents this convention as-is

</domain>

<decisions>
## Implementation Decisions

### PE-version API Shape (HARM-01, HARM-02)

- **D-PE-01:** `extractPeVersion(path: string)` returns a typed object `{ major: number, minor: number, patch: number, build: number }` (all `u16` → JS `number`). HARM-02 requirement text's preferred shape; idiomatic for TS/NAPI; future-proof if Rust adds a 5th component. Mirrors neither Python (`tuple[int, int, int, int]`) nor C++ (`String`) — Node is intentionally the named-field outlier per the milestone's "document, don't standardize" Pitfall 7 stance.

- **D-PE-02:** Failure throws a `napi::Error` with the existing `to_napi_err()` pattern (`napi::Error::from_reason(format!("{err}"))`). No `.code` field — preserves consistency with all other `version.rs` exports (`parse_version`, `compare_versions`, etc.) and with the D-ERR-01 milestone-wide Node convention. Caller distinguishes failure modes by message inspection only.

- **D-PE-03:** `isValidPePath(path: string) -> boolean` exported as a sibling NAPI function delegating to `classic_version_core::pe_version::is_valid_executable_path`. Required by HARM-01 explicitly. Synchronous, never throws — returns `false` for any unreadable, non-existent, or wrong-extension path.

- **D-PE-04:** Both functions live in existing `ClassicLib-rs/node-bindings/classic-node/src/version.rs` (appended at the bottom). No new `mod pe_version;` entry in `lib.rs`. Tests append to existing `__test__/version.spec.ts` as new `describe("extractPeVersion", ...)` and `describe("isValidPePath", ...)` blocks. Reduces file count and keeps the binding-to-core mapping 1:1 (`version.rs` already wraps `classic-version-core`'s parse, compare, and extract patterns).

### Plan Decomposition

- **D-PLAN-01:** Phase 4 targets **5-7 plans** total — right-sized for Node's ~101-109 deferred rows (vs Phase 3's 303). Provisional skeleton:
  1. **Plan 1** — Tooling expansion: `RUST_TARGET_CRATES` 10→18, delete `RUST_FULL_INVENTORY_CRATES`, add bidirectional `validate_contract_surface()` guard (D-TOOL-03), end-to-end `bun run build` env smoke test (D-DTS-02), per-owner gap-count A10 sizing report
  2. **Plan 2** — scanlog promotion (single plan covering all 67 deferred scanlog entries; D-PLAN-02)
  3. **Plan 3** — config promotion (~23-26 entries)
  4. **Plan 4** — version_registry promotion + HARM-01/02 PE-version (D-PLAN-03)
  5. **Plan 5** — aux promotion (~7-12 entries from `file_io`, `path`, `settings`, `message`, `perf`, `registry`, `shared` crates)
  6. **Plan 6** — Tier-2 cleanup atomic cascade (D-PLAN-04) + final mypy-equivalent verification + parity gate green proof
  Plan count may grow to 7 if Plan 1's A10 sizing report surfaces residual rows from newly-tracked crates that warrant a dedicated wave (mirrors Phase 3 Plan 09a precedent). The planner decides during research; final count stays in 5-7 range.

- **D-PLAN-02:** Scanlog's 67 deferred rows land in **a single plan** — well within plan capacity (Phase 3 Wave 1 was 74 in one plan). No artificial sub-module slicing. Bisect granularity comes from atomic commits *within* the plan (one commit per sub-module or one commit per ~10 rows), not from inter-plan boundaries.

- **D-PLAN-03:** HARM-01/02 (PE-version) **bundles with the version_registry promotion plan** (Plan 4). Both touch version-related Node bindings; one plan validates both pieces under the same pre-commit gates and reuses test fixtures (e.g., `kernel32.dll` real PE file for runtime smoke verification). PE-version contract rows (2-3) land in the same `parity_contract.json` refresh as version_registry's 4 promoted rows.

- **D-PLAN-04:** Tier-2 cleanup is a **single M7-style atomic cascade** in the final plan: one commit deletes `gap_type=rust_unmapped` and `gap_type=node_unmapped` branches in `generate_baseline.py` (lines ~463-489), removes `tierDefinitions.tier2` from `parity_contract.json`, empties `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json::entries` to `[]` (preserves file shape for Phase 6 to delete the file itself), refreshes all baseline artifacts, and confirms `bun run parity:gate:local` exits zero. Mirrors Phase 3 Plan 09b precedent. Bisect-clean: every commit either fully passes or fully fails the gate.

- **D-PLAN-05:** Plan 1 delivers an **A10-style sizing report** (per-owner deferred-row count after the `RUST_TARGET_CRATES` expansion) so Plans 2-5 know their actual task budget before they start. Phase 3 Plan 09a's 593-row residual surprise was caused by deferring this sizing pass. Phase 4 front-loads it explicitly.

### Tooling Expansion + camelCase Guard

- **D-TOOL-01:** `RUST_TARGET_CRATES` expands from **10 to 18 entries** matching Phase 3's expanded set, explicitly excluding `classic-crashgen-settings-core` (no Node binding crate exists for it; symbols surface through `classic-config`/`classic-scanlog`/`classic-scangame` Node modules indirectly). Plan 1 verifies each candidate has a corresponding `classic-node/src/<crate>.rs` file before adding.

- **D-TOOL-02:** `RUST_FULL_INVENTORY_CRATES` set is **deleted entirely**, along with `include_rust_symbol()` (which becomes a tautology returning `True` for every symbol). Every tracked crate produces full public-symbol output. Aligns with the "one tier for everything" milestone philosophy. The `tier='tier2'` label assignments at lines 190/210/230/250 stay temporarily (Phase 3 left similar vestigial labels) — the labels become descriptive metadata once `tierDefinitions.tier2` is deleted in the final cleanup plan; Phase 6 sweeps them in DOC-02.

- **D-TOOL-03:** `check_parity_gate.py` gains a **bidirectional `validate_contract_surface()` helper** that walks the contract once and asserts both:
  - `rustSymbol ∈ parsed Rust surface (rust_api_surface.json)` — catches missing `pub use` re-exports at `-core/lib.rs`
  - `nodeExport ∈ parsed Node surface (node_api_surface.json from index.d.ts)` — catches snake_case typos in `nodeExport` and stale entries after Rust function renames

  Single function, single walk, two-direction error messages. Lands in Plan 1 before any promotions. Modeled on Phase 3 D-05 `validate_contract_rust_symbols()` but extended for Node's bidirectional case (Python only had to validate one side because `.pyi` stubs are hand-edited and surface drift is caught by `mypy --strict` separately).

- **D-TOOL-04:** The `validate_contract_surface()` guard runs **unconditionally** on every `check_parity_gate.py` invocation including CI — no `--strict` flag, no opt-out. Mirrors Phase 3 D-05 unconditional invariant pattern. The guard's diagnostic output names the missing side explicitly (e.g., "row `node-config-foo` rustSymbol `FooConfig` not in rust surface — missing `pub use` at `classic-config-core/src/lib.rs`?" or "row `node-config-foo` nodeExport `getFooConfig` not in node surface — Rust function still uses snake_case `get_foo_config`?").

### `index.d.ts` Regeneration + Smoke Test Discipline

- **D-DTS-01:** `index.d.ts` regeneration is **atomic with Rust source change**. Each wave plan commit must include all of: `src/<module>.rs` edits + regenerated `index.d.ts` (via `napi build --release`) + contract row(s) + runtime coverage registry row(s) + smoke test(s) + baseline artifacts refresh. One commit per logical promotion unit (sub-module or ~10 rows). Bisect-clean: every commit either passes or fails `bun run dts:freshness:check` as a unit. No interim commits with stale `index.d.ts`.

- **D-DTS-02:** **Plan 1 runs `bun run build` end-to-end** as a smoke test of the executor environment before any promotion plan depends on the build chain. This verifies:
  - `napi build --release --platform --manifest-path ./Cargo.toml` succeeds in the executor's PowerShell environment
  - `tsc -p tsconfig.json` produces `dist/` output
  - Generated `index.d.ts` matches the committed shape (no drift)
  - `bun run dts:freshness:check` exits zero against the fresh build

  Catches Phase 3-style PowerShell wrapper failures (`rebuild_rust.ps1 -Target python` `NativeCommandError` interaction documented in `project_milestone_state.md`) **before** any promotion plan depends on the build chain. If Plan 1 surfaces an executor environment issue, that becomes a Plan 1 fix — not a downstream blocker.

- **D-TEST-01:** Smoke tests for promoted entries **append to existing `__test__/<module>.spec.ts` files** as new `describe` blocks. No new sibling test files. Follows the per-module convention already established (config.spec.ts, scanlog.spec.ts, version.spec.ts, etc. — all 20 modules have an existing spec file). Discoverable, follows precedent, tests live next to the existing tests for the same module.

- **D-TEST-02:** Coverage strategy: **bun:test for every promoted entry** (full per-row coverage matching Phase 3's per-class depth), plus **one representative entry per promoted module** also added to `__test__/runtime.node.test.mjs` (node:test) to prove cross-runtime parity. Existing `runtime.node.test.mjs` is the venue for the cross-runtime verification. The bun:test + node:test pair matches `package.json::test:bun && test:node` enforcement.

### Error Shape, Cross-AI Review, Execution, Hash Algorithm

- **D-ERR-01:** Phase 4 preserves the existing `to_napi_err()` message-only pattern (`napi::Error::from_reason(format!("{err}"))`) for **all promoted error types**. No `.code` field on promoted errors. Consistent with version.rs and every other current binding. Phase 6 HARM-05 documents the Node convention as-is: "Node errors carry messages only, no structured codes." This is the documented contract that ships from Phase 4. PE-version errors (D-PE-02) follow the same rule.

- **D-REVIEW-01:** Cross-AI review (`/gsd:review --phase 4 --claude --codex`) is **pre-scheduled** for two specific plans before `/gsd:execute-phase`:
  1. **Plan 1** (tooling expansion + camelCase guard + contractIdsHash schema) — high algorithmic encoding; Phase 3 lost 4 CRITICAL findings here when the internal plan checker passed
  2. **Final cleanup plan** (M7 atomic cascade across multiple shared files) — high regression risk; one wrong key deletion regresses the gate

  Other plans use the per-plan feedback rule from `feedback_review_before_execute_encoded_logic.md`. Reviews use **both** `--claude` AND `--codex` per memory rule (different investigation styles produce different findings).

- **D-EXEC-01:** Phase 4 plans execute **sequentially on main** — no worktrees. Per memory rule `feedback_sequential_when_files_overlap`: every plan touches `parity_contract.json` and `index.d.ts`, so parallel worktrees would conflict on merge-back (the regenerated baseline JSON files are particularly conflict-prone). `napi build --release` native dependencies (cargo, npm, MSVC toolchain) are simpler to satisfy in the main repo. Sequential mode means dropping `<parallel_execution>` blocks and `--no-verify` flags from agent prompts; commits run pre-commit hooks normally.

- **D-HASH-01:** All `runtime_coverage_registry.json` selectors use **full 64-char SHA-256 via `tools/binding_parity_runtime_coverage.py::_stable_id_hash`** — mandatory import, no truncation, no inline reimplementation. Phase 3 R8 bug must not recur (hardcoded `sha256[:16]` would produce `registry_mismatch_total > 0` and silently fail the gate). Plan 1's `validate_contract_surface()` helper or any new selector-writing helper imports `_stable_id_hash` directly from `tools/binding_parity_runtime_coverage.py`. The Node `runtime_coverage_registry.json` already uses the full SHA-256 form (verified at `__test__/fixtures/runtime_coverage_registry.json:15`), so this decision codifies the existing convention to prevent drift during promotion.

### Claude's Discretion

- **Owner module reassignment** for newly-tracked crates. Phase 3 added `RUST_OWNER_BY_CRATE` rows for 7 new owners (file_io, path, settings, message, perf, registry, shared). Node's existing tooling already maps these as `aux`. Plan 1 may either preserve the `aux` collapse (smaller table) or split them into 7 distinct owner modules (better gap reporting per crate). The planner decides based on gap-report readability. Either choice is acceptable.

- **Atomic commit granularity within a wave plan.** D-DTS-01 requires `index.d.ts` regen to be atomic with Rust source change, but the planner decides whether each commit covers one sub-module's promotions, ~10 rows of promotions, or all promotions for a single owner module in one commit. The minimum bar is "every commit individually passes `bun run parity:gate:local`."

- **Per-class smoke test grouping.** D-TEST-01 says append to existing `__test__/<module>.spec.ts` as new `describe` blocks, but the planner decides whether each promoted class gets its own `describe` block (more bisect granularity) or related classes are grouped (fewer test boundaries). Match the existing per-spec-file conventions in each target file.

- **`runtime.node.test.mjs` representative selection.** D-TEST-02 says one representative entry per promoted module gets a node:test smoke test. The planner picks which entry — the criterion is "exercises a real method or non-trivial constructor path, not a no-op import."

- **A10 sizing report format.** Plan 1's per-owner gap-count report can be a markdown table, a JSON file, or both. The planner decides; the constraint is "downstream plans (2-5) can read it without ambiguity to size their task budgets."

- **`generate_baseline.py` SQUAD_BY_OWNER expansion mechanics.** Phase 3 added a dict-based SQUAD_BY_OWNER that scaled to N owners. Node's current tooling has the same dict shape. Plan 1 decides whether to add new squads for the new owners, collapse them all into the existing two squads, or eliminate the squad concept entirely (it's not load-bearing for the gate's exit code).

- **Whether the final cleanup plan also touches `tools/node_api_parity/generate_wave_manifest.py` and `generate_deferred_backlog.py`.** Phase 3 left these files in place because Phase 6 owns wave manifest deletion. The planner decides whether Phase 4's cleanup commit also strips dead code from these scripts or leaves them entirely for Phase 6.

### Folded Todos

None — `node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" todo match-phase 4` returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements

- `.planning/REQUIREMENTS.md` §"Node Tier Collapse (NODE)" — NODE-01..NODE-06 are this phase's core requirement set
- `.planning/REQUIREMENTS.md` §"Cross-Binding Harmonization (HARM)" — HARM-01 and HARM-02 are this phase's PE-version extraction requirements (HARM-03/04 belong to Phase 3 and are already shipped; HARM-05 belongs to Phase 6)
- `.planning/ROADMAP.md` §"Phase 4: Node Tier Collapse" — phase goal + 5 success criteria
- `.planning/PROJECT.md` §"Active" — confirms Node Tier-1/Tier-2 collapse is a v9.1.0-bindings target and that PE-version extraction belongs to Phase 4
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` — Phase 1 decisions; relevant because the "no Tier-2 concept from birth" philosophy Phase 1 established is what Phase 4 enforces retroactively on the Node gate
- `.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md` §D-09 — per-plan baseline refresh cadence pattern Phase 4 inherits via Phase 3 D-03
- `.planning/phases/03-python-tier-collapse/03-CONTEXT.md` — direct sibling phase; Phase 3 decisions D-01..D-10, A1-A10 amendments, and the 10-plan structure provide the precedent template Phase 4 adapts to Node's smaller surface

### Source-of-truth Rust crates the promoted entries live in

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/` — 67 entries span sub-modules: `parser`, `formid`, `formid_analyzer`, `record_scanner`, `plugin_analyzer`, `patterns`, `mod_detector`, `suspect_scanner`, `settings_validator`, `fcx_handler`, `gpu_detector`, `orchestrator`, `report`, `papyrus`, `version`, `crashgen_registry`, `segment_key`, `error`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` + sub-modules — 23-26 entries
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs` + sub-modules — 4 entries
- `ClassicLib-rs/business-logic/classic-version-core/src/pe_version.rs` — `extract_pe_version`, `is_valid_executable_path`, `PeVersionError`, `PeVersionResult` (HARM-01/02 source-of-truth API)
- All 18 business-logic `-core` crates that have a corresponding Node binding — Plan 1 must add each crate's `lib.rs` path to `generate_baseline.py::RUST_TARGET_CRATES`. Excludes `classic-crashgen-settings-core` (no `classic-node/src/crashgen_settings.rs` module exists)

### Node binding crate files the promotions write to

- `ClassicLib-rs/node-bindings/classic-node/src/lib.rs` — module declaration list (no changes expected; all 20 modules are already declared)
- `ClassicLib-rs/node-bindings/classic-node/src/version.rs` — Plan 4 appends `extract_pe_version` and `is_valid_pe_path` NAPI functions (HARM-01/02)
- `ClassicLib-rs/node-bindings/classic-node/src/{scanlog,config,version_registry,fileio,path,settings,message,resource,shared,update,xse,scangame,database,yaml,web,constants,crashgen_rules}.rs` — Plan 2-5 add `#[napi]` exports for promoted entries; the wrapper types and functions already exist (this phase exposes them via `#[napi]`, does not add new wrappers)
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` — auto-regenerated per wave commit via `napi build --release`; committed atomically with the Rust source change (D-DTS-01)
- `ClassicLib-rs/node-bindings/classic-node/__test__/<module>.spec.ts` (20 spec files) — append new `describe` blocks per promoted entry (D-TEST-01)
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` — append one representative cross-runtime smoke test per promoted module (D-TEST-02)
- `ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts` — module-level import gate; updated automatically via `parity:gate:local` baseline refresh

### Parity tooling the phase modifies

- `tools/node_api_parity/generate_baseline.py` — Plan 1 expands `RUST_TARGET_CRATES` (line 24) from 10 to 18 entries, deletes `RUST_FULL_INVENTORY_CRATES` (line 50-54) and `include_rust_symbol()` (line 64-70), expands `RUST_OWNER_BY_CRATE` and `SQUAD_BY_OWNER` for new owners; final cleanup plan deletes `gap_type=rust_unmapped` and `gap_type=node_unmapped` branches at lines 463-489
- `tools/node_api_parity/check_parity_gate.py` — Plan 1 adds the `validate_contract_surface()` bidirectional guard (D-TOOL-03); the `--deferred-registry` default at line 140 stays untouched (Phase 6 owns DOC-01)
- `tools/node_api_parity/check_dts_freshness.py` — read-only reference; ensures `index.d.ts` doesn't drift from a fresh `napi build`. Used by `bun run dts:freshness:check`
- `tools/node_api_parity/generate_deferred_backlog.py` — read-only reference for current deferred backlog generation; Phase 6 may delete or rewrite
- `tools/node_api_parity/generate_wave_manifest.py` — read-only reference for current wave manifest generation; Phase 6 may delete or rewrite
- `tools/binding_parity_runtime_coverage.py` — provides `_stable_id_hash` (line 57) — mandatory import for any selector writing (D-HASH-01); also provides `build_coverage_summary()` and `render_coverage_summary_markdown()` used by `generate_baseline.py`

### Parity artifacts the phase refreshes

- `docs/implementation/node_api_parity/baseline/parity_contract.json` — the gate-truth source; rewritten via `generate_baseline.py --write-baseline` per plan; final cleanup plan deletes `tierDefinitions.tier2`
- `docs/implementation/node_api_parity/baseline/parity_contract.md` — human-readable contract mirror
- `docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md}` — per-plan refresh via `check_parity_gate.py --update-baseline`
- `docs/implementation/node_api_parity/baseline/rust_api_surface.json` — per-plan refresh
- `docs/implementation/node_api_parity/baseline/node_api_surface.json` — per-plan refresh
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` — per-plan refresh; the `deferred` count is the load-bearing PYT-06-equivalent metric (NODE-06 success criterion: drops to 0)
- `docs/implementation/node_api_parity/baseline/tier1_gate_report.md` — per-plan refresh via `check_parity_gate.py`
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` — per-plan updates, one row added per promoted contract row; selectors use full 64-char SHA-256 via `_stable_id_hash` (D-HASH-01)
- `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/` — ephemeral build outputs; per-plan refresh as a side effect of `bun run parity:gate:local`

### Tier-2 governance files (read-only source for promotion until final cleanup plan)

- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md` — authoritative list of deferred entries per owner module; Plan N reads but does not modify; Phase 6 owns deletion (DOC-03)
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` — machine-readable deferred entries (1327 lines, 101 entries currently); Plan N reads for promotion targets; final cleanup plan empties `entries` to `[]` but does NOT delete the file (Phase 6 owns deletion)
- `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` — Plan N reads for historical context; NOT deleted (Phase 6 owns deletion)
- `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md` — Plan N reads as context only; not modified
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md` — Plan N reads as context only; not modified

### Build, test, and verification commands

- `bun run build` — Plan 1's environment smoke test (D-DTS-02); regenerates `index.d.ts` in subsequent waves
- `bun run parity:gate:local` — per-plan gate verification; equivalent to `dts:freshness:local && parity:gate:update-baseline`
- `bun run parity:gate` — gate-only without `index.d.ts` freshness; used by CI
- `bun run dts:freshness:check` — `index.d.ts` freshness gate (read-only)
- `bun run test:bun` — Bun test runner (`bun test`) for `__test__/*.spec.ts` files
- `bun run test:node` — node:test runner for `__test__/runtime.node.test.mjs`
- `pwsh -ExecutionPolicy Bypass -File ../../../tools/enter_vs_dev_shell.ps1 -WorkingDirectory . -Command "bun run parity:gate:local"` — alternate vsdev-shell entry point if msvc linker shadowing is needed

### Architectural rules

- `AGENTS.md` §"Always-On Repository Rules" — single Tokio runtime; never write to `nul`/`NUL`; Node bindings should stay in sync with Rust core logic
- `CLAUDE.md` §"Build Commands" §"Node bindings (from ClassicLib-rs/node-bindings/classic-node)" — exact `bun install && bun run build` and `bun run parity:gate:local` invocations
- `CLAUDE.md` §"Key Gotchas" — Node-specific gotchas (msvc linker shadowing, vcpkg requirement)
- `docs/api/node-python-contract-map.md` — current Node and Python public contract file locations
- `docs/api/binding-contract-refresh-note.md` — when Node `index.d.ts` and Python `.pyi` contract artifacts should refresh separately vs together
- `docs/api/binding-parity-overview.md` — current C++/Node/Python exposure comparison; Phase 4 makes the Node column harmony-achieved (Phase 6 DOC-05 rewrites the doc)

### Phase 3 sibling artifacts (template precedent)

- `.planning/phases/03-python-tier-collapse/03-CONTEXT.md` §D-04..D-10 — narrow `pub use` policy, atomic commits, runtime coverage registry, classic_shared wiring chain (the structural patterns Phase 4 adapts)
- `.planning/phases/03-python-tier-collapse/03-CONTEXT.md` §A1..A10 — research amendments showing how Phase 3 corrected its own decisions mid-execution; Phase 4 should expect similar A-style amendments after research lands
- `.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-PLAN.md` — the residual-promotion plan that handled 593 unexpected rows; Phase 4 hopes to avoid this via D-PLAN-05 front-loaded sizing
- `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md` — the M7 atomic cascade plan that drove `deferred_total` to 0; Phase 4's final cleanup plan mirrors this structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`tools/node_api_parity/generate_baseline.py::parse_rust_surface()`** (lines 169-262) — the regex-based `lib.rs` parser. Functionally equivalent to Python's tooling: iterates `RUST_TARGET_CRATES`, reads each `lib.rs`, applies regex patterns for `pub mod`, `pub fn`, `pub struct`, `pub enum`, `pub type`, `pub trait`, `pub const`, `pub static`, and `pub use`. No sub-module recursion. Plan 1 does not change the regex — it changes `RUST_TARGET_CRATES` to include 18 crates instead of 10 and deletes the inventory filter.
- **`tools/node_api_parity/generate_baseline.py::expand_pub_use_statement()`** (lines 122-166) — already handles grouped `pub use foo::{a, b, c}` and `pub use foo as bar` shapes. Same as Python's tooling. Confirms that the narrow `pub use` style from Phase 3 D-04 will be parsed correctly.
- **`tools/node_api_parity/generate_baseline.py::parse_node_surface()`** (lines 284-360) — reads `index.d.ts` line-by-line and extracts function/class/interface/type/const/enum signatures via regex. This is the canonical source for what Node's surface looks like; the camelCase `nodeExport` field on contract rows must match what this function emits. Plan 1's `validate_contract_surface()` guard reads from this function's JSON output.
- **`tools/node_api_parity/check_parity_gate.py::main()`** (lines 116-280) — the current `tier1_mappings` loop that Plan 1 extends with the `validate_contract_surface()` guard. The script already iterates `tier1Mappings` only — the "Tier-2 skip" mechanic doesn't actually exist in `check_parity_gate.py` itself (same finding as Phase 3 A9). The Tier-2 logic lives in `generate_baseline.py` lines 463-489 (`gap_type=rust_unmapped` / `gap_type=node_unmapped` branches) and `parity_contract.json::tierDefinitions`.
- **`ClassicLib-rs/node-bindings/classic-node/src/version.rs`** (99 lines) — the existing Node binding for `classic-version-core`. Already wraps `parse_version`, `try_parse_version`, `compare_versions`, `is_known_fallout4_version`, `extract_version_from_filename`, `extract_version_from_log`, `extract_all_versions`, `format_version`. The reference pattern for the new `extractPeVersion` + `isValidPePath` functions: each function uses the `to_napi_err` helper at line 12-14, takes simple String parameters, and delegates entirely to the `-core` crate.
- **`ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts`** — the existing per-module test file using `bun:test` describe/test/expect shape. The reference pattern for the new `extractPeVersion` + `isValidPePath` describes that Plan 4 appends.
- **`ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts`** — the module-level import gate that lists every expected export. Functions as a compile-time inventory check: if a `nodeExport` row lands in the contract but isn't in `index.d.ts`, this test fails on import.
- **`ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs`** — the cross-runtime parity test using node:test. Reference for D-TEST-02's "one representative entry per promoted module" cross-runtime smoke tests.
- **`ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json`** — already uses full 64-char SHA-256 `contractIdsHash` (verified at line 15). Confirms the `_stable_id_hash` algorithm is the existing convention; D-HASH-01 codifies this so no Plan reverts to truncated form.
- **`tools/binding_parity_runtime_coverage.py::_stable_id_hash`** (line 57) — full SHA-256 hash function for selector validation. Mandatory import per D-HASH-01.

### Established Patterns

- **`#[napi]` attribute on free functions and methods.** Every Node binding function uses `#[napi]` (no `#[napi(constructor)]` for free functions). Class methods use `#[napi]` inside `#[napi]` impl blocks. The `napi_derive::*` macros auto-convert snake_case Rust names to camelCase JS names — no explicit naming overrides needed unless a Rust function name collides with a JS reserved word.
- **`to_napi_err()` helper per binding module.** Each `src/<module>.rs` defines a local `fn to_napi_err(err: impl std::fmt::Display) -> napi::Error { napi::Error::from_reason(format!("{err}")) }`. Phase 4 D-ERR-01 preserves this pattern for promoted errors.
- **Direct delegation to `-core` crates from `#[napi]` functions.** No business logic in `classic-node/src/`; every NAPI function calls a `classic_<crate>_core::*` function directly. This means promoting an entry is purely an exposure change — the wrapper logic already exists.
- **Per-module spec file in `__test__/<module>.spec.ts` using `bun:test`.** All 20 modules already have spec files. New tests append to existing files as new `describe` blocks.
- **`parity:gate:local` runs both `dts:freshness:local` and `parity:gate:update-baseline`** — the canonical local gate verification command. Per `package.json` line 27.
- **Per-plan `--update-baseline` refresh committed with code (Phase 2 D-09 / Phase 3 D-03).** Phase 4 D-DTS-01 inherits this cadence for both `parity_contract.json` and `index.d.ts`.
- **Sequential execution within waves when plans share files (memory rule `feedback_sequential_when_files_overlap`).** Phase 4 D-EXEC-01 codifies this for the entire phase since every plan touches `parity_contract.json` and `index.d.ts`.
- **Cross-AI review for plans encoding logic (memory rule `feedback_review_before_execute_encoded_logic`).** Phase 4 D-REVIEW-01 pre-schedules this for Plans 1 and final cleanup; other plans use the per-plan rule.
- **Full 64-char SHA-256 selectors via `_stable_id_hash`.** Already the existing convention in `runtime_coverage_registry.json`; D-HASH-01 codifies it to prevent Phase 3 R8 recurrence.

### Integration Points

- **Phase 3 Python Tier Collapse is complete and shipped.** No cross-phase coordination needed. Phase 4 inherits the structural patterns (D-04..D-10 from Phase 3 CONTEXT) but operates entirely in Node territory.
- **Phase 5 (CI Enforcement) consumes Phase 4's gate.** Final cleanup plan's commit must land green in CI (`bun run parity:gate` exits zero), and Phase 5 verifies the Node parity gate job keeps passing. Phase 4 must NOT touch CI workflow files — Phase 5 owns those.
- **Phase 6 (Documentation Reset) consumes Phase 4's gate-green state.** Phase 6's DOC-02/DOC-03 deletes the governance files; DOC-01 makes `--deferred-registry` optional. Phase 4 keeps the existing default and keeps the files in place, only emptying `deferred_runtime_backlog.json::entries` to `[]`.
- **`tools/binding_parity_runtime_coverage.py` is shared between Python and Node tooling.** Phase 4 must not modify it (Phase 3 left it stable); it provides `_stable_id_hash` and `build_coverage_summary()` used by both bindings. Any required modification is a separate quick task.
- **`napi build --release` requires the MSVC toolchain and is sensitive to PowerShell wrapper interactions.** Phase 3 documented `rebuild_rust.ps1 -Target python` aborting via `NativeCommandError` in the executor environment. Plan 1's `bun run build` smoke test (D-DTS-02) catches the equivalent issue for Node before any promotion plan depends on the build chain.
- **`__test__/parity_tier1.spec.ts` import gate** — the existing test imports every expected `nodeExport` from `../index.js`. As Plan 1 expands the contract surface, this test file's import block grows automatically via baseline regeneration. A snake_case `nodeExport` typo would surface as a runtime ImportError here.
- **Phase 4 and Phase 6 both touch `deferred_runtime_backlog.json`** — Phase 4 empties `entries` to `[]` (preserves file shape); Phase 6 deletes the file. The intermediate state (file exists with empty entries) is the structural prerequisite that lets the Phase 4 cleanup commit pass `bun run parity:gate:local` while the Phase 6 deletion ships separately.

</code_context>

<specifics>
## Specific Ideas

- **Plan 1 tooling expansion is the keystone.** Same as Phase 3: everything downstream breaks if `RUST_TARGET_CRATES` is wrong. Plan 1 must verify each of the 18 entries by running `parse_rust_surface()` against them and confirming non-empty symbol lists. A crate with zero parsed symbols signals a path typo or an empty `lib.rs` — fix in Plan 1, not a downstream plan.
- **Plan 1's `bun run build` end-to-end smoke test (D-DTS-02) is non-negotiable.** Without it, downstream plans risk the same `NativeCommandError` PowerShell wrapper failure that Phase 3 documented. Catching it in Plan 1 turns a phase blocker into a Plan 1 fix.
- **The bidirectional `validate_contract_surface()` guard (D-TOOL-03) lands in Plan 1, not later.** Same logic as Phase 3 D-05: the guard must already exist before any promotion lands so no row can be authored that the gate would later reject.
- **Every wave plan commit must include regenerated `index.d.ts`.** This is the single biggest behavioral difference from Phase 3. Phase 3 plans never touched `.pyi` regeneration because `.pyi` is hand-edited. Phase 4 plans cannot skip this step.
- **Final cleanup plan's atomic cascade is bisect-critical.** Splitting Tier-2 deletion across multiple commits creates intermediate states where `parity_contract.json::tierDefinitions.tier2` is gone but `gap_type=rust_unmapped` branches still emit "tier2" rows — gate fails. Single commit only.
- **`deferred_runtime_backlog.json::entries` empty, file shape preserved.** Phase 6 deletes the file. Phase 4 empties the array. This split mirrors Phase 3 exactly: Phase 3 emptied the Python equivalent and Phase 6 hasn't deleted it yet (per `project_milestone_state.md`).
- **`_stable_id_hash` import is mandatory in any selector-writing helper.** D-HASH-01 codifies this to prevent the Phase 3 R8 sha256[:16] truncation bug from recurring. Any agent writing `runtime_coverage_registry.json` rows must `from binding_parity_runtime_coverage import _stable_id_hash` rather than reimplementing.
- **Cross-AI review pre-scheduled for Plans 1 and final cleanup.** D-REVIEW-01 makes this mandatory. The user has explicit memory of Phase 3's 4 CRITICAL findings caught only by Codex+Claude review; Phase 4 front-loads the protection.
- **Sequential execution on main, no worktrees.** D-EXEC-01 makes this mandatory. Memory rule `feedback_sequential_when_files_overlap` applies fully — every plan touches the contract and `index.d.ts`.
- **No new Cargo dependencies.** `pelite` stays in `classic-version-core`; `classic-node` doesn't grow a direct `pelite` dep. HARM-01 requirement text is explicit on this.
- **Node error shape is "message-only, no .code" — even for promoted errors.** D-ERR-01 preserves the existing convention for HARM-05 to document. Adding `.code` would diverge from every shipped Node binding error.
- **The 101 vs 109 deferred-count discrepancy is a research question.** `deferred_runtime_backlog.json::entries.length = 101`; `runtime_coverage_summary.md::deferred = 109`. Same shape as Phase 3 A4 amendment. Research must resolve which is authoritative for the NODE-06 success criterion before plans are written.
- **Never run any tooling against `nul` / `NUL` for discard output.** User's global Windows rule: `nul`-destined files become undeletable on system drives. Use `/dev/null` in Git Bash or explicit file paths.

</specifics>

<deferred>
## Deferred Ideas

- **Tier-2 governance file deletion** — `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`, `deferred_runtime_backlog.json`, `tier2_wave_manifest.json`, `gate_contract_baseline.md`, `per_wave_acceptance_template.md`. Phase 6 DOC-03 / DOC-04 owns the deletion. Phase 4 reads but does not delete.
- **`--deferred-registry` argument optional/missing-tolerant behavior in `check_parity_gate.py` and `generate_baseline.py`** — Phase 6 DOC-01 owns this. Phase 4 keeps the existing default.
- **Rewriting `docs/api/binding-parity-overview.md` for the harmony-achieved reference** — Phase 6 DOC-05.
- **Per-binding error-contract documentation (`docs/api/error-contract.md`)** — Phase 6 HARM-05. Phase 4 does not document; Phase 4 ships the convention that HARM-05 will document.
- **Standardizing error conventions across bindings (Python typed exceptions vs Node messages vs C++ rust::Error)** — Explicit anti-feature (PROJECT.md Out of Scope, Pitfall 7).
- **Adding `.code` field to Node error types** — Considered and rejected (D-ERR-01). HARM-05 documents the message-only convention as-is.
- **Adding new Cargo workspace dependencies** — STACK research (Phase 3 era) rejected this; Phase 4 inherits the rule. `pelite` stays confined to `classic-version-core`.
- **`classic-shared-core` Node exposure as a standalone Node binding crate** — HARM-03/04 was Python-only and already shipped in Phase 3. Adding `classic-shared-node` would be scope creep; the milestone goal is parity *of existing surfaces*, not new binding surfaces.
- **Node `classic_shared` runtime stats / health helpers** — Same reason: HARM-03/04 closed for Python only. Could be a future milestone item if Node consumers need observability, but not Phase 4.
- **Auto-generating Node binding code from a schema** — Out of scope; NAPI's `#[napi]` macros are the existing code-gen path. No new generator.
- **Cross-binding parity manifest unification** — Out of scope for v9.1.0-bindings; each binding keeps its own `parity_contract.json`. Phase 6 documents the policy.
- **Splitting scanlog promotions across multiple plans** — Considered and rejected (D-PLAN-02). 67 rows fits in one plan.
- **Worktree-based parallel execution** — Considered and rejected (D-EXEC-01). Memory rule `feedback_sequential_when_files_overlap` applies.
- **Per-plan cross-AI review for every plan** — Considered and rejected (D-REVIEW-01). Pre-scheduling Plans 1 and final cleanup is the targeted protection; other plans use the per-plan feedback rule.
- **Adding `.code` field only to PE-version errors** — Considered and rejected (D-PE-02 follows D-ERR-01). Splitting the convention within the Node binding is worse than uniform message-only.
- **Stringified PE version return** — Considered and rejected (D-PE-01). Object form is HARM-02's preferred shape and idiomatic for TS/NAPI.
- **CI workflow file edits for Node parity gate** — Phase 5 owns `ci-node-bindings.yml` modifications. Phase 4 keeps CI unchanged; Plan 6 just confirms `bun run parity:gate:local` exits zero locally.
- **Promoting more entries than the deferred backlog contains** — Plan 1's A10 sizing report may surface previously-untracked rows from newly-tracked crates; those become legitimate Phase 4 scope (as Phase 3 Plan 09a did with its 593-row residual). But "go beyond the deferred backlog because we can" is not in scope.

### Reviewed Todos (not folded)

None — `node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" todo match-phase 4` returned 0 matches.

</deferred>

---

*Phase: 04-node-tier-collapse*
*Context gathered: 2026-04-09*
