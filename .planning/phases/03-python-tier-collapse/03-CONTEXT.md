# Phase 3: Python Tier Collapse - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Collapse the Python parity gate's Tier-1/Tier-2 split into a single enforced contract. Promote all 289 currently-deferred Python parity entries (228 scanlog + 34 version_registry + 26 config + 1 aux) from the Tier-2 backlog to enforced Tier-1 rows in `docs/implementation/python_api_parity/baseline/parity_contract.json`. Expand `tools/python_api_parity/generate_baseline.py::RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` from the current 3 entries to all 19 business-logic crate / Python binding pairs. Add the required `pub use` re-exports to each `-py` crate's `lib.rs` so the regex parser can see promoted symbols (Pitfall 2). Wire `classic_shared` as a gate-enrolled Python binding with at least 6 contract rows and full wiring verification (HARM-03, HARM-04). Remove the Tier-2 skip logic from `check_parity_gate.py`. Keep runtime coverage registry entries in lockstep with promoted contract rows (Pitfall 4).

**In scope:**
- `tools/python_api_parity/generate_baseline.py` — expand `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` to 19 entries each
- `tools/python_api_parity/check_parity_gate.py` — remove Tier-2 skip logic; add mechanical Pitfall 2 guard assertion
- `ClassicLib-rs/python-bindings/classic-*-py/src/lib.rs` (all 19 crates) — add `pub use` re-exports for every promoted contract symbol (narrow, 1:1 with contract rows)
- `ClassicLib-rs/python-bindings/classic-*-py/classic_*.pyi` (all 19 stubs) — update to cover promoted entries; mypy --strict clean
- `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` — already exists; update if needed
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — add contract rows for 289 promoted entries + 6 classic_shared rows
- `docs/implementation/python_api_parity/baseline/rust_api_surface.json`, `python_api_surface.json`, `parity_diff_report.{json,md}`, `runtime_coverage_summary.{json,md}`, `tier1_gate_report.md` — refresh per plan
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — add a row per promoted contract entry pointing to its smoke test nodeid
- `ClassicLib-rs/python-bindings/tests/` — add per-class pytest smoke tests for every promoted `#[pyclass]`; grouped free-function tests
- `rebuild_rust.ps1` verification only — confirm `-Target python classic_shared` builds a working wheel (already auto-discovered from `ClassicLib-rs/foundation/`)
- `ClassicLib-rs/validate_stubs.py` — run per promotion plan to catch stub/wrapper divergence

**Out of scope:**
- Phase 4 Node Tier Collapse (independent; parallel-safe)
- Deletion of `docs/implementation/python_api_parity/governance/` files — Phase 6 owns this (DOC-02, DOC-04)
- Making the `--deferred-registry` argument optional / missing-tolerant — Phase 6 owns this (DOC-01)
- Rewriting `docs/api/binding-parity-overview.md` — Phase 6 owns this (DOC-05)
- Per-binding error-contract documentation — Phase 6 owns this (HARM-05)
- Standardizing error conventions across bindings — explicit anti-feature (PROJECT.md Out of Scope; Pitfall 7)
- Auto-generating `.pyi` stubs via stubgen / pyo3-stub-gen — explicit anti-feature (FEATURES research)
- Adding new Cargo workspace dependencies — STACK research confirmed none are needed
- CI wiring for the parity gate — Phase 5 (CI-01 validates the Phase 3 gate stays green in CI)
- Any C++ bridge surface change (Phase 2 is complete; Phase 3 is Python-only)
- `classic-shared-py` crate source changes beyond adding `.pyi` coverage if gaps surface — the `#[pymodule]` surface is already implemented

</domain>

<decisions>
## Implementation Decisions

### Plan Decomposition Strategy

- **D-01:** Phase 3 uses a **split-scanlog hybrid** shape with 8-10 plans. Sequence:
  1. Plan 1 — Tooling expansion: `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` grow from 3 to 19 entries; add the mechanical Pitfall 2 guard assertion in `check_parity_gate.py` (see D-05); baseline regenerated against the widened target set but Tier-2 skip logic still in place so existing governance still passes.
  2. Plan 2 — scanlog Wave 1 (parsing primitives): `parser`, `formid`, `formid_analyzer`, `record_scanner`, `plugin_analyzer`, `patterns` — roughly 76 of 228 scanlog entries.
  3. Plan 3 — scanlog Wave 2 (detection & analysis): `mod_detector`, `suspect_scanner`, `settings_validator`, `fcx_handler`, `gpu_detector` — roughly 76 of 228 scanlog entries.
  4. Plan 4 — scanlog Wave 3 (orchestration & output): `orchestrator`, `report`, `papyrus`, `version`, `crashgen_rules`, `core_mod_convert` — remaining ~76 of 228 scanlog entries.
  5. Plan 5 — config module promotion: 26 entries across `classic-config-py`.
  6. Plan 6 — version_registry module promotion: 34 entries across `classic-version-registry-py`.
  7. Plan 7 — `classic_shared` wiring: add 6 contract rows for the full module surface, add registry rows, run full wiring verification chain (D-10).
  8. Plan 8 — Tier-2 skip logic removal, final mypy --strict sweep across all 19 stubs, final parity gate + pytest verification. This plan lands the change that flips `check_parity_gate.py` from two-tier to single-tier.

  The 8-plan skeleton may grow to 9-10 if scanlog waves have to split further during research (e.g., if Wave 2 exceeds reasonable plan size). The planner decides. Aux entries (1 entry at phase start per ROADMAP) fold into Plan 7 alongside `classic_shared`.

- **D-02:** scanlog's 228 entries are split **by dependency layer**, not by file size or governance-file order. Layer order is parsing primitives → detection & analysis → orchestration & output. Rationale: a failing promotion in Wave 2 (detection) points to that semantic tier rather than "whichever chunk the modulo landed in." Bisects yield actionable information.

- **D-03:** Every promotion plan refreshes the committed parity baseline (`parity_contract.json`, `rust_api_surface.json`, `python_api_surface.json`, `parity_diff_report.{json,md}`, `runtime_coverage_summary.{json,md}`, `tier1_gate_report.md`) **in the same commit as the code change**, mirroring Phase 2's D-09 cadence. The repository is gate-green after every Phase 3 commit. Bisects across Phase 3 commits remain meaningful.

### `pub use` Re-export Policy

- **D-04:** Each `-py` crate's `lib.rs` gets **narrow `pub use` additions — exactly 1:1 with promoted contract rows.** No wildcard `pub use sub_module::*` and no speculative re-exports. Rationale: `generate_baseline.py::parse_rust_surface()` reads only `lib.rs`; the crate-root surface must equal the parity contract for the gate to be lossless. This also matches the existing `classic-scanlog-py/src/lib.rs` re-export pattern (explicit per-symbol list at lines 115-141). If a sub-module symbol is needed by two contract rows (e.g., a method and its class), both names land in one `pub use` line grouped with `{}`.

- **D-05:** `tools/python_api_parity/check_parity_gate.py` gains a **mechanical Pitfall 2 guard assertion** during Plan 1 tooling work. For every row in `parity_contract.json`, the gate asserts the `rustSymbol` appears in the parsed Rust surface (`rust_api_surface.json`). A missing symbol exits non-zero with a clear diagnostic pointing at the `pub use` gap in the corresponding `lib.rs`, rather than the current `missing_rust` noise that requires manual investigation. The assertion runs unconditionally — not under a flag — so it applies to every gate invocation including CI.

- **D-06:** Within each promotion plan, commits are **atomic**: `pub use` additions land first (in the `-py` crate `lib.rs`), then contract rows and `.pyi` updates, then the baseline refresh, then runtime coverage registry rows and smoke tests. Everything committed together. No plan commits partial state that leaves the gate red mid-plan. This is an absolute rule for bisect integrity — the same rule Phase 2 followed with its per-plan `--update-baseline` cadence.

### Runtime Smoke Test Depth and Coverage Registry

- **D-07:** Runtime smoke test depth is **per-class with grouped free functions.** Every promoted `#[pyclass]` gets at least one pytest test that constructs an instance and calls one real method. Related free functions (e.g., `detect_mods_single` / `detect_mods_double` / `detect_mods_important` / `detect_mods_batch`) are grouped into one test each that exercises the real call path with a minimal valid input. This produces roughly 70-90 new pytest functions across the phase. It is strong Pitfall 4 protection (every compiled `#[pyclass]` type is touched at runtime) without exploding to 289 individual tests.

- **D-08:** Every promoted contract row gets a matching **runtime coverage registry entry** in `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json`. The registry entry's `nodeids` point to the per-class smoke test from D-07. This activates the gate's `tier1_missing_runtime_total` check as the secondary Pitfall 4 guard and makes the relationship between contract rows and test coverage mechanical. A promotion plan is not done until its registry rows match its contract rows one-for-one.

### `classic_shared` Wiring (HARM-03, HARM-04)

- **D-09:** The `classic_shared` parity contract captures the **full `#[pymodule] fn classic_shared` root surface** — 6 contract rows. The 6 are the exact symbols registered in `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs::classic_shared`: `RuntimeStats`, `get_runtime_stats`, `is_runtime_healthy`, `PyStringProcessor`, `PyPathHandler`, `PyRustPerformanceMonitor`. This exceeds the success criteria minimum of 3 rows and matches the D-04 narrow re-export policy (crate root equals contract). The `aux` owner-module entry (1 entry at phase start) folds into this row set if it resolves to a `classic_shared` surface symbol.

- **D-10:** `classic_shared` wiring is proven by a **4-step verification chain**, all of which must pass before Plan 7 can close:
  1. The Python parity gate (`python tools/python_api_parity/check_parity_gate.py --repo-root .`) exits zero with `classic_shared` enrolled as a 6-row Tier-1 contract.
  2. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared` produces a `classic_shared*.whl` and installs it into `ClassicLib-rs/python-bindings/.venv`.
  3. A pytest smoke test imports `classic_shared` and successfully calls `classic_shared.get_runtime_stats()` returning a non-None `RuntimeStats` with `worker_threads > 0`.
  4. `mypy --strict` against `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` runs clean with no errors.

  Any single failure in 1-4 blocks Plan 7 completion. Discovered gaps (e.g., the stub is missing an entry, or `Get-PythonRustModules` does not pick up the foundation directory) are fixed inside Plan 7, not deferred.

### Claude's Discretion

- The exact sub-module grouping boundaries within each scanlog wave. D-02 fixes the three layers (parsing primitives / detection & analysis / orchestration & output), but which specific sub-modules land in which wave is the planner's call during research. Research must verify the 76-76-76 split is achievable and adjust chunk counts if the underlying entries cluster unevenly.
- The exact `.pyi` stub update mechanics — which parts of each stub are rewritten vs patched. Preference is hand-edited diffs against the existing stubs, not wholesale regeneration. `validate_stubs.py` is the authoritative check.
- Whether Plan 1's Pitfall 2 guard assertion is a standalone `validate_contract_rust_symbols()` helper function, inlined into `main()` of `check_parity_gate.py`, or emitted through `generate_baseline.py`'s existing `parse_rust_surface()`. All three shapes are acceptable as long as the assertion fires on every gate run.
- How aggressively each promotion plan uses `validate_stubs.py` + `mypy --strict` — the minimum is one run per plan at plan close, but per-commit-within-plan runs are acceptable if the planner finds that the feedback loop is too slow otherwise. PYT-04 is only satisfied when every promoted entry's stub passes mypy --strict.
- Whether test fixtures for per-class smoke tests (e.g., minimal crash logs, minimal YAML inputs) get added to a shared `tests/fixtures/` directory or live inline in the test function. Existing `python-bindings/tests/` structure is the reference.
- Whether Plan 8's Tier-2 skip logic removal is a pure deletion or a clearly-commented annotation (e.g., `# Single-tier contract per v9.1.0-bindings Phase 3`). Both acceptable.
- Whether the runtime coverage registry's `nodeids` field is populated with module-level paths (`tests/test_scanlog_promoted.py::test_formid_analyzer_smoke`) or class-level paths. Plan 7 locks a convention after Plan 2 experiments with the first few promotions.

### Folded Todos

None — `gsd-tools todo match-phase 3` returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements

- `.planning/REQUIREMENTS.md` §"Python Tier Collapse (PYT)" — PYT-01..PYT-06 are this phase's core requirement set
- `.planning/REQUIREMENTS.md` §"Cross-Binding Harmonization (HARM)" — HARM-03 and HARM-04 are this phase's `classic_shared` wiring requirements (HARM-01/02 belong to Phase 4)
- `.planning/ROADMAP.md` §"Phase 3: Python Tier Collapse" — phase goal + 5 success criteria
- `.planning/PROJECT.md` §"Active" — confirms Python Tier-1/Tier-2 collapse is a v9.1.0-bindings target and that classic_shared belongs to Phase 3
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` — Phase 1 decisions; relevant because D-04 (no Tier-2 concept in the CXX gate from birth) establishes the milestone-wide "one tier" philosophy Phase 3 enforces retroactively on the Python gate
- `.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md` §D-09 — per-plan baseline refresh cadence pattern Phase 3 inherits as D-03

### Research (this milestone)

- `.planning/research/ARCHITECTURE.md` §"3. Python Tier Collapse" — the 19-crate expansion blueprint that drives Plan 1's tooling work
- `.planning/research/ARCHITECTURE.md` §"6. Python `classic_shared` Module" — the wiring requirements for HARM-03/HARM-04 (note: the section's claim that `classic-shared-py` is not in the workspace is STALE — it is already in `ClassicLib-rs/Cargo.toml`; see code_context below)
- `.planning/research/FEATURES.md` §"Python Tier-1/Tier-2 collapse" — sizing ("LARGE"), surface counts, constraint that `.pyi` files stay maintained and are NOT auto-generated
- `.planning/research/FEATURES.md` §"Python `classic_shared` runtime helpers as a public module" — classic_shared gate enrollment requirements
- `.planning/research/FEATURES.md` §"Anti-features" §"Automated `.pyi` generation" — the anti-feature that forbids stubgen / pyo3-stub-gen
- `.planning/research/PITFALLS.md` §"Pitfall 1: Deferred Runtime Backlog Survives Tier Collapse" — explains why Phase 3 must not delete governance files; Phase 6 owns that step
- `.planning/research/PITFALLS.md` §"Pitfall 2: Regex-Based Rust Surface Parser Misses Promoted Entries" — the architectural constraint driving D-04 (narrow pub use) and D-05 (mechanical guard assertion)
- `.planning/research/PITFALLS.md` §"Pitfall 4: Python Test-Only Stub Hides Real Implementation Gap" — the runtime-vs-stub divergence problem driving D-07 (per-class smoke tests) and D-08 (registry entries for every promoted row)
- `.planning/research/PITFALLS.md` §"Pitfall 7: Cross-Binding Error-Contract Standardization" — the rule keeping Phase 3 away from error-shape normalization (HARM-05 is Phase 6)
- `.planning/research/STACK.md` §"Python tier collapse" — confirms no new Cargo dependencies are needed

### Source-of-truth Rust crates the promoted entries live in

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/` — 228 entries span sub-modules: `parser`, `formid`, `formid_analyzer`, `record_scanner`, `plugin_analyzer`, `patterns`, `mod_detector`, `suspect_scanner`, `settings_validator`, `fcx_handler`, `gpu_detector`, `orchestrator`, `report`, `papyrus`, `version`, `crashgen_rules`, `core_mod_convert`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` + sub-modules — 26 entries
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs` + sub-modules — 34 entries
- All 19 business-logic `-core` crates — Plan 1 must add each crate's `lib.rs` path to `generate_baseline.py::RUST_TARGET_CRATES`

### Python binding crate files the promotions write to

- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs` — narrow `pub use` additions for Waves 1/2/3; current re-exports live at lines 115-141 as the reference pattern
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/` sub-module files (`parser.rs`, `formid.rs`, `formid_analyzer.rs`, `record_scanner.rs`, `plugin_analyzer.rs`, `patterns.rs`, `mod_detector.rs`, `suspect_scanner.rs`, `settings_validator.rs`, `fcx_handler.rs`, `gpu_detector.rs`, `orchestrator.rs`, `report.rs`, `papyrus.rs`, `version.rs`, `crashgen_rules.rs`, `core_mod_convert.rs`) — reference-only, for verifying a promoted symbol actually exists before adding the `pub use`
- `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` — stub file that must cover every promoted scanlog entry
- `ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs` + `classic_config.pyi` — Plan 5 targets
- `ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs` + `classic_version_registry.pyi` — Plan 6 targets
- `ClassicLib-rs/python-bindings/classic-*-py/*.pyi` for all 16 other bindings — Plan 1 expands `PYTHON_TARGET_MODULES` to reference these; later plans add rows per crate as promotions surface specific needs
- `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` — read-only reference for classic_shared's 6 module-level exports (Plan 7)
- `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` — already exists; Plan 7 validates completeness against the 6-row contract

### Parity tooling the phase modifies

- `tools/python_api_parity/generate_baseline.py` — Plan 1 expands `RUST_TARGET_CRATES` (line 24) from 3 to 19 entries and `PYTHON_TARGET_MODULES` (line 36) from 3 to 19 entries, plus adds corresponding `RUST_OWNER_BY_CRATE` and `PYTHON_OWNER_BY_MODULE` entries; each wave plan extends `SQUAD_BY_OWNER` or adjusts owner labels as needed
- `tools/python_api_parity/check_parity_gate.py` — Plan 1 adds the Pitfall 2 guard assertion (D-05); Plan 8 removes the Tier-2 skip logic; the `--deferred-registry` default stays untouched (Phase 6 owns DOC-01)
- `tools/binding_parity_runtime_coverage.py` — helper imported by both scripts; reference only, no modifications expected unless the registry schema has to flex for the per-class-plus-grouped-free-fn coverage model
- `ClassicLib-rs/validate_stubs.py` — stub validator invoked per plan; run against the updated `parity_contract.json` and each crate's `.pyi`

### Parity artifacts the phase refreshes

- `docs/implementation/python_api_parity/baseline/parity_contract.json` — the gate-truth source; rewritten via `generate_baseline.py --write-baseline` per plan
- `docs/implementation/python_api_parity/baseline/parity_contract.md` — human-readable contract mirror
- `docs/implementation/python_api_parity/baseline/parity_diff_report.{json,md}` — per-plan refresh via `check_parity_gate.py --update-baseline`
- `docs/implementation/python_api_parity/baseline/rust_api_surface.json` — per-plan refresh
- `docs/implementation/python_api_parity/baseline/python_api_surface.json` — per-plan refresh
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.{json,md}` — per-plan refresh
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — per-plan updates, one row added per promoted contract row (D-08)

### Tier-2 governance files (read-only source for promotion)

- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` — authoritative list of deferred entries per owner module; Plan N reads but does not modify
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` — machine-readable deferred entries; Plan N reads for promotion targets; NOT deleted (Phase 6 owns DOC-02)
- `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` — Plan N reads for historical context; NOT deleted (Phase 6 owns DOC-02)

### Build, test, and verification commands

- `rebuild_rust.ps1` — Plan 7 verification step 2 runs `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared`; the `Get-PythonRustModules` function already searches `ClassicLib-rs/foundation/` so classic-shared-py should be auto-discovered
- `ClassicLib-rs/python-bindings/.venv` — Plan N wheel installs land here; `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` is the smoke test runner
- `uv run mypy --strict` against each updated `.pyi` file — PYT-04 compliance gate

### Architectural rules

- `AGENTS.md` §"Always-On Repository Rules" — single Tokio runtime; never write to `nul` (and by user's global rule, never write to `nul` or `NUL` on Windows); Python bindings should stay in sync with Rust core logic
- `AGENTS.md` §"Quick Notes" — Python bindings remain for other potential projects and are kept in sync with Rust core logic
- `CLAUDE.md` §"Build Commands" §"Python bindings" — exact `rebuild_rust.ps1 -Target python` invocation for Plan 7 verification; `check_parity_gate.py` invocation for every plan
- `CLAUDE.md` §"Key Gotchas" — Python venv for bindings lives at `ClassicLib-rs/python-bindings/.venv`, not repo root

### Related quick-task precedent

- `.planning/phases/quick/260406-syy-resolve-the-newly-uncovered-python-parit/` — recent quick task that handled a newly-uncovered Python parity entry (FcxResetError) by registering it as Tier-2. Phase 3 inherits the outcome: when Phase 3 promotes all Tier-2 entries, FcxResetError is among them. The quick task is context only, not a scope item.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs` lines 115-141** — the exact reference pattern for narrow `pub use` re-exports. Phase 3 plans should match this shape: explicit name lists grouped by source sub-module, one `pub use` line per sub-module, comma-separated braces for multi-name imports. No wildcards.
- **`tools/python_api_parity/generate_baseline.py::parse_rust_surface()`** (lines ~160-200) — the regex-based `lib.rs` parser that Plan 1 expands. The function iterates `RUST_TARGET_CRATES`, reads each `lib.rs`, and applies regex patterns for `pub mod`, `pub fn`, `pub struct`, `pub enum`, `pub type`, `pub trait`, `pub const`, `pub static`, and `pub use`. No sub-module recursion. Plan 1 does not change the regex — it changes `RUST_TARGET_CRATES` to include 19 crates instead of 3.
- **`tools/python_api_parity/generate_baseline.py::expand_pub_use_statement()`** (lines ~113-158) — already handles grouped `pub use foo::{a, b, c}` and `pub use foo as bar` shapes. Confirms that the narrow `pub use` style from D-04 will be parsed correctly; no new parser capability is needed.
- **`tools/python_api_parity/check_parity_gate.py::main()`** (lines ~116-272) — the current `tier1_mappings` loop that Plan 1 extends with the Pitfall 2 guard assertion (D-05) and Plan 8 simplifies to remove Tier-2 skip logic. The existing `sync_baseline_artifacts()` helper is reusable for per-plan refreshes.
- **`ClassicLib-rs/validate_stubs.py`** — the authoritative `.pyi` validator invoked per promotion plan. Walks the parity contract and confirms every stub row matches a Rust symbol and vice versa.
- **`ClassicLib-rs/python-bindings/tests/`** — existing pytest layout for per-module smoke tests. The per-class D-07 test additions follow the existing file-per-target convention.
- **`classic-shared-py` (`ClassicLib-rs/foundation/classic-shared-py/`)** — ALREADY registered at `ClassicLib-rs/Cargo.toml` line 5 as a workspace member; already has `crate-type = ["cdylib", "rlib"]` + the `pyo3` dep at `foundation/classic-shared-py/Cargo.toml`; already has `classic_shared.pyi` in place; `#[pymodule] fn classic_shared` already exports the 6 symbols at `foundation/classic-shared-py/src/lib.rs::classic_shared`. The heavy-lifting work for HARM-03/HARM-04 is already done; Phase 3 just needs to verify the wiring, add the 6 contract rows, and prove the wheel builds and imports.
- **`rebuild_rust.ps1::Get-PythonRustModules`** (lines ~215-272) — already searches both `ClassicLib-rs/foundation/` and `ClassicLib-rs/python-bindings/`, so `classic-shared-py` should auto-discover without script changes. Plan 7 verifies this assumption; if it fails, the fix is inside Plan 7 (not deferred).

### Established Patterns

- **Narrow explicit `pub use` at `lib.rs`.** Existing scanlog-py demonstrates the style. Plan 2-6 additions match line-for-line shape.
- **`#[pyclass]` backed by sub-module wrapper types; `#[pymodule]` initialization in `lib.rs`.** The classic_scanlog / classic_config / classic_version_registry bindings share this shape. Every promoted entry has a physically existing wrapper type — Phase 3 does not create new PyO3 bindings, only exposes them.
- **Per-plan `--update-baseline` refresh committed with code (Phase 2 D-09).** Phase 3 D-03 inherits this cadence.
- **`validate_stubs.py` + `mypy --strict` + `pytest` as the three-way gate per plan.** Matches the maintained stub workflow from PROJECT.md.
- **Runtime coverage registry rows point to pytest nodeids.** Existing `runtime_coverage_registry.json` rows follow this shape; Phase 3 adds 289 new rows following the same convention.
- **No new Cargo dependencies.** STACK research confirmed Phase 3 is Python tooling + wrapper plumbing only.
- **Shared exception macro from `classic_shared`.** `define_exceptions!` and `register_exceptions!` macros live in `classic-shared-py` and are consumed by `classic-scanlog-py` (lines 87-92). Promoted entries re-use the existing exception hierarchy; Phase 3 does not add new exception classes.

### Integration Points

- **Phase 4 (Node Tier Collapse) runs in parallel.** Both phases are independent per ROADMAP. No cross-phase coordination is required. The runtime coverage registry lives in a different directory (`ClassicLib-rs/node-bindings/classic-node/runtime-coverage/` vs `ClassicLib-rs/python-bindings/tests/fixtures/`), so no file-level contention.
- **Phase 5 (CI Enforcement) consumes Phase 3's gate.** Plan 8's Tier-2 skip logic removal must land green in CI, and Phase 5 verifies the Python parity gate job keeps passing. Phase 3 must NOT touch CI workflow files — Phase 5 owns those.
- **Phase 6 (Documentation Reset) consumes Phase 3's gate-green state.** Phase 6's DOC-02 / DOC-04 only runs if Phase 3 ends with zero deferred entries. Phase 6's DOC-01 adds the deferred-registry tolerance that Phase 3 intentionally defers.
- **`rebuild_rust.ps1 -Target python` auto-discovery path.** Plan 7 verification step 2 relies on `Get-PythonRustModules` finding `classic-shared-py` under `foundation/`. If discovery fails, Plan 7 fixes `rebuild_rust.ps1` inside its own scope.
- **`ClassicLib-rs/python-bindings/.venv`** — the Python bindings virtualenv. Plan 1 assumes it already exists; if missing, the plan creates it via `uv venv ClassicLib-rs/python-bindings/.venv`. Existing STATE.md quick task precedent suggests the venv is in place.

</code_context>

<specifics>
## Specific Ideas

- **Plan 1 tooling expansion is the keystone.** Everything downstream breaks if `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` are wrong. Plan 1 must verify each of the 19 new crate entries by running `parse_rust_surface()` against them and confirming the parser emits non-empty symbol lists. A crate with zero parsed symbols signals a path typo or an empty `lib.rs` — fix in Plan 1, not a downstream plan.
- **Pitfall 2 guard assertion must fire in Plan 1 itself.** Before any promotion lands, the guard assertion must already exist. Plan 1's completion criterion: gate still exits zero on the current 70 Tier-1 rows with the guard assertion active. That establishes the guard as the enforcement mechanism for Plans 2-7.
- **Keep Tier-2 skip logic in place until Plan 8.** The existing skip logic means Plans 2-7 can land deferred entries piecewise without the gate failing on rows that haven't been promoted yet. Plan 8 removes the skip logic only after all 289 entries are promoted, which is structurally the final flip from two-tier to single-tier.
- **Every promotion plan must run the full verification chain at plan close.** The chain is: (1) `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits zero, (2) `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` exits zero, (3) `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python <affected-modules>` builds the affected wheels cleanly, (4) `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` passes including the new per-class smoke tests, (5) `uv run mypy --strict` runs clean on the updated stubs. All five steps are non-negotiable.
- **`.pyi` hand-edit discipline.** Stubs remain maintained contracts, not generated artifacts. Promotion plans read the existing stub, diff in the promoted symbols by hand, preserve docstrings and annotations, then run `validate_stubs.py` + `mypy --strict`. Auto-generation via stubgen or pyo3-stub-gen is forbidden (FEATURES anti-feature).
- **Runtime coverage registry rows must be one-per-contract-row (D-08).** No "one test covers ten rows via import alone" shortcuts. Each row gets its own registry entry that names the pytest nodeid that exercises it. This is what makes the gate's `tier1_missing_runtime_total` path mechanically effective.
- **Phase 3 stops at "gate green, skip logic removed" — it does not delete governance files.** Phase 6 owns the deletion. If Phase 3 accidentally breaks the existing governance read path by touching `deferred_runtime_backlog.json`, that is a bug to fix inside Phase 3, not a milestone-scope change.
- **Phase 3 does not touch CI workflow files.** CI enforcement is Phase 5. The current Python parity gate CI job continues to run unmodified during Phase 3 execution. Each Phase 3 plan must produce a commit that, if pushed, keeps the existing CI green.
- **Phase 3 and Phase 4 can interleave commits on the main branch.** The directories the two phases edit do not overlap (Python tooling + Python bindings + Python parity artifacts vs Node tooling + Node bindings + Node parity artifacts). Coordination is only needed if both phases decide to edit `tools/binding_parity_runtime_coverage.py` in the same window.
- **Never run the parity tooling against `nul` / `NUL` for discard output.** User's global Windows rule: `nul`-destined files become undeletable on system drives. Use `/dev/null` in Git Bash or explicit file paths.

</specifics>

<deferred>
## Deferred Ideas

- **Tier-2 governance file deletion** — `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`, `deferred_runtime_backlog.json`, `tier2_wave_manifest.json`. Phase 6 DOC-02 / DOC-04 owns the deletion. Phase 3 must read but never write these files.
- **`--deferred-registry` argument optional/missing-tolerant behavior in `check_parity_gate.py`** — Phase 6 DOC-01 owns this. Phase 3 keeps the existing default and keeps the files in place.
- **Rewriting `docs/api/binding-parity-overview.md` for the harmony-achieved reference** — Phase 6 DOC-05.
- **Per-binding error-contract documentation (`docs/api/error-contract.md`)** — Phase 6 HARM-05. Phase 3 does not normalize or document error shapes.
- **Standardizing error conventions across bindings** — Explicit anti-feature (PROJECT.md Out of Scope, Pitfall 7). Phase 3 preserves existing per-binding exception classes.
- **Auto-generating `.pyi` stubs via stubgen / pyo3-stub-gen** — Explicit anti-feature (FEATURES research §Anti-features).
- **Unified cross-binding parity manifest** — Out of scope for v9.1.0-bindings per FEATURES research; each binding keeps its own `parity_contract.json`.
- **Structured error codes for the C++ bridge** — Out of scope (FEATURES research §LATER). Not a Phase 3 concern.
- **Promoting `FcxResetError` as a first-class Python parity entry beyond the current runtime-verified Tier-2 treatment** — Phase 3 promotes it alongside the other 288 entries via the normal D-04/D-05 path; the Phase 2 quick-task 260406-syy registration is context only. Its wrapper lives in `classic-scanlog-py::fcx_handler`; narrow `pub use` in Plan 2 (scanlog Wave 1) or Plan 3 (scanlog Wave 2, depending on which sub-module-layer grouping research assigns fcx_handler to) picks it up.
- **Adding new Cargo workspace dependencies** — STACK research rejected this; Phase 3 is Python tooling + wrapper re-exports only.
- **Python `classic_shared` wheel publishing or distribution changes** — Out of scope; Plan 7 only verifies the local wheel builds, installs, and imports. Publishing is not a v9.1.0-bindings milestone concern.
- **Expanding the `classic_shared` contract beyond the 6 module-level exports** — Deferred as a possible follow-up if future phases decide the `PyStringProcessor.normalize`-style method rows are needed. D-09 deliberately stops at module-root rows per the D-04 narrow policy.
- **Parallel execution of Phase 3 plans against Phase 4 plans at the commit level** — Parallel at plan level is allowed, parallel at commit level is fine as long as only one phase touches `tools/binding_parity_runtime_coverage.py` at a time. No explicit coordination mechanism is introduced; conflicts are resolved by the second committer rebasing.
- **CI workflow file edits** — Phase 5 owns `ci-python-bindings.yml` modifications. Phase 3 keeps CI unchanged.

### Reviewed Todos (not folded)

None — `gsd-tools todo match-phase 3` returned 0 matches.

</deferred>

---

*Phase: 03-python-tier-collapse*
*Context gathered: 2026-04-07*
