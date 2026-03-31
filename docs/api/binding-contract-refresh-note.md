# Binding Contract Refresh Note

Maintainer-facing note for when the generated Node declaration file and maintained Python stubs should be refreshed during binding work.

Use this page with [`node-python-contract-map.md`](node-python-contract-map.md) and [`binding-parity-overview.md`](binding-parity-overview.md).

This note describes the current repo workflow visible in source and docs today. It does **not** create a new parity policy, and it does **not** mean Node and Python must expose identical APIs.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this note when a change touches public binding contracts under:

- [`ClassicLib-rs/node-bindings/classic-node/index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts)
- `ClassicLib-rs/python-bindings/*-py/*.pyi`

The goal is practical maintenance: decide when to refresh only the Node contract, only the Python stubs, or both in the same change.

---

## Current Documented Gates

The current documented gates are per surface, not one shared Node-plus-Python gate.

- Node: the parity workflow requires regenerated, fresh [`ClassicLib-rs/node-bindings/classic-node/index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts), plus `bun run parity:gate:local`, `bun run test:bun`, `bun run test:node`, and `bun run dts:freshness:check` for accepted wave work and release gating. See [`docs/implementation/node_api_parity/governance/gate_contract_baseline.md`](../implementation/node_api_parity/governance/gate_contract_baseline.md) and [`docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`](../implementation/node_api_parity/governance/tier2_backlog_and_governance.md).
- Python: the parity workflow requires parity checks, stub validation, and Python smoke tests, with `.pyi` naming/signature finalized for promoted APIs. See [`docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`](../implementation/python_api_parity/governance/tier2_backlog_and_governance.md).

So today:

- `index.d.ts` freshness is an explicit Node gate
- `.pyi` correctness is an explicit Python gate through `validate_stubs.py` and the Python parity workflow
- there is no separate source-backed rule that every Node contract refresh must also refresh Python, or vice versa

---

## When To Refresh Node `index.d.ts`

Refresh [`ClassicLib-rs/node-bindings/classic-node/index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts) when the public Node export surface changes.

Typical triggers already documented in the repo include:

- changes in [`ClassicLib-rs/node-bindings/classic-node/src/`](../../ClassicLib-rs/node-bindings/classic-node/src/)
- regeneration of `index.d.ts` itself
- public Rust API changes in the currently tracked parity-owner crates:
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`

In practice, if a Node export name, signature, DTO shape, async/sync contract, or promoted Tier-1 parity row changes, refresh and commit `index.d.ts` in the same change.

---

## When To Refresh Python `.pyi` Stubs

Refresh the affected `classic_*.pyi` files when the public Python module contract changes.

Typical documented triggers include:

- changes in `ClassicLib-rs/python-bindings/*-py/src/`
- changes in `ClassicLib-rs/python-bindings/*-py/*.pyi`
- public Rust API changes in the same currently tracked parity-owner crates:
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
  - `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`

In practice, refresh the matching `.pyi` file when a Python export name, callable signature, return type, raised-contract expectation, or promoted Tier-1 Python parity row changes.

---

## When Both Should Refresh In The Same Change

This is mostly contributor best practice inferred from the current workflow, not a separate formal gate.

Refresh both Node `index.d.ts` and the affected Python `.pyi` stubs in the same change when all are true:

- the underlying Rust API change is intentionally exposed through both maintained binding surfaces
- both bindings already cover that workflow or crate area today, or the change is promoting matching maintained coverage on both sides
- the public contract changes are user-visible on both sides, not just internal wrapper refactors

The strongest current examples are shared API changes in the parity-owner crate areas named by both workflows today:

- `classic-scanlog-core`
- `classic-config-core`
- `classic-version-registry-core`

Why this is the practical expectation:

- both workflows use the same trigger-crate set for parity maintenance
- [`binding-parity-overview.md`](binding-parity-overview.md) documents many of those crates as exposed through both Node and Python already
- [`node-python-contract-map.md`](node-python-contract-map.md) treats `index.d.ts` and `classic_*.pyi` files as the fastest public contract views contributors should check first

If only one binding surface changes, refresh only that surface's contract artifacts and validation outputs.

---

## Validation And Artifact Checks That Matter

When Node `index.d.ts` changes, the important checks are:

```powershell
# From ClassicLib-rs/node-bindings/classic-node
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Relevant Node artifacts/checks:

- [`ClassicLib-rs/node-bindings/classic-node/parity-artifacts/tier1_gate_report.md`](../../ClassicLib-rs/node-bindings/classic-node/parity-artifacts/tier1_gate_report.md)
- [`ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md`](../../ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md)
- [`ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md`](../../ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md)

When Python `.pyi` files change, the important checks are:

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

Relevant Python artifacts/checks:

- [`ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md`](../../ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md)
- [`ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md`](../../ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md)
- [`ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md`](../../ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md)
- [`ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json`](../../ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json)

If both surfaces refresh in one change, run both workflows.

---

## Source-Backed Caveats And Non-Goals

- Node declarations are generated by NAPI-RS; Python `.pyi` files are maintained contributor-facing stubs. They are both public contract artifacts, but they are not produced by the same mechanism.
- Current docs define separate Node and Python parity gates; they do not define a single mandatory "refresh both every time" rule.
- Python remains a maintained compatibility/integration surface, not the default location for new product behavior. A Node-only or Rust-only change does not automatically require Python stub churn.
- Node and Python do not promise exact surface parity today. Use this note to keep shared maintained workflows aligned, not to force identical exports where the repo does not already document them.
- If source, contract files, and contributor docs diverge, update the affected docs and contract artifacts in the same change.
