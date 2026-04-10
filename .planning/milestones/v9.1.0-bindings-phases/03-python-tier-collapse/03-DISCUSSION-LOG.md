# Phase 3: Python Tier Collapse - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `03-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 03-python-tier-collapse
**Areas discussed:** Plan decomposition strategy, pub use re-export scope, Runtime smoke test depth, classic_shared scope & wiring verification

---

## Plan Decomposition Strategy

| Option | Description | Selected |
|---|---|---|
| B: Split-scanlog hybrid | 8-10 plans: tooling → 3 scanlog waves (~76 entries each by dependency layer) → config → version_registry → classic_shared+aux → skip-logic removal & verification. Bisectable, each plan <90min, matches Phase 2 cadence. | ✓ |
| A: Per-owner-module (6 plans) | 1 tooling + 4 content (scanlog as mega-plan, config, version_registry, aux) + 1 verification. Simpler structure but scanlog mega-plan risks long execution times and painful rollbacks. | |
| C: Per-binding-crate atoms (19+ plans) | One plan per -py crate pair. Maximum bisect granularity but high plan-overhead for crates with 1-3 entries. Doesn't match how deferred entries cluster by owner. | |

**User's choice:** B: Split-scanlog hybrid
**Notes:** User accepted the recommended option directly. Hybrid shape explicitly fends off the scanlog mega-plan risk while preserving Phase 2's per-plan baseline refresh cadence.

---

### Follow-up: Scanlog splitting method

| Option | Description | Selected |
|---|---|---|
| By dependency layer | Wave 1: parsing primitives (parser, formid, formid_analyzer, record_scanner, plugin_analyzer, patterns). Wave 2: detection & analysis (mod_detector, suspect_scanner, settings_validator, fcx_handler, gpu_detector). Wave 3: orchestration & output (orchestrator, report, papyrus, version, crashgen_rules). Failures point to the broken tier. | ✓ |
| By governance file order | Mechanically split the deferred_runtime_backlog.json entries in list order into 3 equal chunks. Ignores semantic boundaries. | |
| By file size/LOC balance | Group modules until each chunk has ~76 entries. Balanced cost but may split related modules. | |

**User's choice:** By dependency layer
**Notes:** Layered split supports meaningful bisects when promotion breaks a downstream consumer.

---

### Follow-up: Parity contract refresh cadence

| Option | Description | Selected |
|---|---|---|
| Per plan | Each promotion plan runs check_parity_gate.py --update-baseline in its own commit alongside the code change. Matches Phase 2's D-09 pattern. Repo stays gate-green after every commit; bisects remain meaningful. | ✓ |
| Batched at phase end | All plans commit code only; final verification plan regenerates the contract once. Fewer baseline churn commits but no bisect signal between plans — breakage hides until the end. | |

**User's choice:** Per plan
**Notes:** Phase 2 established the cadence as D-09; Phase 3 inherits it as D-03.

---

## pub use Re-export Scope

| Option | Description | Selected |
|---|---|---|
| Narrow — 1:1 with contract rows | Only promoted symbols get pub use added to the -py crate's lib.rs. Crate root surface exactly matches parity_contract.json. Matches existing scanlog-py pattern. Drift impossible by construction. | ✓ |
| Broad — wildcard re-export sub-modules | Use pub use sub_module::* for each sub-module. Future-proof but fragile to the regex parser; breaks the "contract is the surface" model. | |
| Per-need — failure-driven additions | Add pub use only when the gate reports missing_rust during a promotion plan. Mechanical but wastes verification cycles. | |

**User's choice:** Narrow — 1:1 with contract rows
**Notes:** Narrow pattern locks contract fidelity and matches the existing classic-scanlog-py/src/lib.rs reference (lines 115-141).

---

### Follow-up: Pitfall 2 guard mechanism

| Option | Description | Selected |
|---|---|---|
| Add assertion | Extend check_parity_gate.py so every contract row's rustSymbol must appear in the parsed Rust surface from lib.rs. Cheap mechanical check. Prevents 'contract row added but pub use forgotten' from recurring. | ✓ |
| Rely on existing missing_rust reporting | Gate already reports missing_rust entries in parity_diff_report.md. No new script logic required but Pitfall 2 stays a manual discipline problem. | |
| Pre-commit hook instead | Add a git pre-commit hook. Local-only — doesn't help CI. | |

**User's choice:** Add assertion
**Notes:** Gate-side assertion becomes D-05; keeps enforcement centralized and visible in CI.

---

### Follow-up: pub use / contract row commit ordering

| Option | Description | Selected |
|---|---|---|
| Same commit, pub use first | Within each promotion plan, add pub use re-exports first, then contract rows, then baseline refresh — all in one atomic commit. Every commit gate-green. | ✓ |
| Separate commit for pub use | One commit per plan for pub use, then another for contract rows. Finer history but doubles bisect surface. | |

**User's choice:** Same commit, pub use first
**Notes:** Atomic commit rule becomes D-06; mirrors Phase 2's "code + baseline in one commit" pattern.

---

## Runtime Smoke Test Depth

| Option | Description | Selected |
|---|---|---|
| Per-class | Every promoted #[pyclass] gets a constructor + one method call. Free functions grouped. ~70-90 pytest functions total. Strong Pitfall 4 protection without test explosion. | ✓ |
| Shallow per-module | One smoke test per Python module (~19 tests). Minimum PYT-05 compliance but weak Pitfall 4 protection — 94% of promoted entries untested at runtime. | |
| Exhaustive per-symbol | One test per contract row (289 tests). Complete Pitfall 4 protection but high maintenance cost. | |

**User's choice:** Per-class
**Notes:** Per-class depth is the Pitfall 4 sweet spot — every compiled #[pyclass] is exercised at runtime without exploding to 289 tests.

---

### Follow-up: Runtime coverage registry coverage

| Option | Description | Selected |
|---|---|---|
| Yes, every promoted row | For each promoted contract row, add a runtime coverage registry entry pointing to the smoke test. Activates the gate's tier1_missing_runtime_total check as a secondary Pitfall 4 guard. | ✓ |
| Per-class only, not per-row | Add registry entries matching the per-class smoke tests. Simpler but misses free-function drift detection. | |
| Skip registry updates in Phase 3 | Leave runtime coverage registry untouched. Defers the tier1_missing_runtime_total gate path. Risks a hollow pass. | |

**User's choice:** Yes, every promoted row
**Notes:** One-to-one registry coverage becomes D-08 and makes the secondary Pitfall 4 guard mechanical rather than discretionary.

---

## classic_shared Scope & Wiring Verification

| Option | Description | Selected |
|---|---|---|
| Full module surface — 6 rows | RuntimeStats, get_runtime_stats, is_runtime_healthy, PyStringProcessor, PyPathHandler, PyRustPerformanceMonitor. Matches D-04 narrow re-export policy (crate root = contract). Exceeds success criteria minimum. | ✓ |
| Minimum 3 rows | Only RuntimeStats, get_runtime_stats, is_runtime_healthy per success criteria literal wording. Leaves other module-level exports parity-ungated. | |
| All public 6+ with methods | 6 root symbols plus method rows. Duplicates smoke test coverage from D-07. | |

**User's choice:** Full module surface — 6 rows
**Notes:** 6 rows become D-09; matches the narrow D-04 "crate root equals contract" policy.

---

### Follow-up: classic_shared wiring verification chain

| Option | Description | Selected |
|---|---|---|
| Full chain — gate + wheel + import + mypy | (1) Parity gate includes classic_shared and passes. (2) rebuild_rust.ps1 -Target python classic_shared produces a wheel. (3) pytest smoke test imports classic_shared and calls get_runtime_stats(). (4) mypy --strict passes on classic_shared.pyi. All four required. | ✓ |
| Gate + wheel build | Parity gate + wheel compile only. Skips runtime import proof. | |
| Gate only | Parity gate enrollment only. Maximum risk of 'looks wired but doesn't build/import' regression. | |

**User's choice:** Full chain — gate + wheel + import + mypy
**Notes:** 4-step chain becomes D-10 — every step must pass before Plan 7 can close.

---

## Claude's Discretion

- Sub-module grouping boundaries within each scanlog wave (76-76-76 target).
- `.pyi` stub update mechanics — hand-edited diffs vs wholesale rewrite (diffs preferred).
- Plan 1 Pitfall 2 guard shape — standalone helper vs inlined in `main()` vs emitted through `generate_baseline.py`.
- `validate_stubs.py` + `mypy --strict` cadence within each plan — one run at close is the minimum.
- Per-class test fixture storage — shared `tests/fixtures/` vs inline.
- Plan 8 Tier-2 skip logic removal — pure deletion vs annotated removal.
- Runtime coverage registry `nodeids` granularity convention — module-level vs class-level; Plan 7 locks a convention after Plan 2 experiments.

## Deferred Ideas

- Tier-2 governance file deletion — Phase 6 DOC-02/DOC-04.
- `--deferred-registry` argument missing-tolerance — Phase 6 DOC-01.
- `docs/api/binding-parity-overview.md` rewrite — Phase 6 DOC-05.
- `docs/api/error-contract.md` per-binding documentation — Phase 6 HARM-05.
- Standardizing error conventions across bindings — explicit anti-feature.
- Auto-generating `.pyi` stubs — explicit anti-feature.
- Unified cross-binding parity manifest — out of scope for v9.1.0-bindings.
- Structured error codes for the C++ bridge — out of scope.
- FcxResetError promoted alongside other 288 entries via normal D-04/D-05 path.
- New Cargo workspace dependencies — STACK rejected.
- `classic_shared` wheel publishing/distribution — out of scope.
- Expanding `classic_shared` contract beyond 6 module-level rows — possible future follow-up.
- Phase 3 / Phase 4 commit-level coordination mechanism — resolved by rebase when needed.
- CI workflow file edits — Phase 5 owns.
