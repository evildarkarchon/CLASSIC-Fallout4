# Binding Contract Refresh Note

Maintainer-facing note for when the generated Node declaration file, maintained Python stubs, and C++ bridge baseline should be refreshed during binding work.

Use this page with [`node-python-contract-map.md`](node-python-contract-map.md), [`binding-parity-overview.md`](binding-parity-overview.md), and [`binding-parity-policy.md`](binding-parity-policy.md).

This note describes the current repo workflow visible in source and docs today. It covers all three binding surfaces: C++ (CXX), Node (NAPI-RS), and Python (PyO3).

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this note when a change touches public binding contracts under:

- [`node-bindings/classic-node/index.d.ts`](../../node-bindings/classic-node/index.d.ts)
- `python-bindings/*-py/*.pyi`
- [`cpp-bindings/classic-cpp-bridge/src/`](../../cpp-bindings/classic-cpp-bridge/src/)

The goal is practical maintenance: decide when to refresh only one surface's contract, or multiple surfaces in the same change.

If you are translating an older `ClassicLib-rs/...` instruction, use the shared [`workspace migration matrix`](../workspace-migration-matrix.md) instead of copying legacy paths into new guidance.

---

## Current Documented Gates

The current documented gates are per surface, not one shared gate.

- **C++ (CXX)**: the parity gate is `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`. Baseline: `tools/cxx_api_parity/cxx_baseline_surface.json`. Contributor docs: [`cxx-parity-gate.md`](cxx-parity-gate.md).
- **Node**: the parity workflow is verify-first — run `bun run parity:gate`, refresh with `bun run parity:gate:update-baseline` only when the drift is intentional and source-backed, rerun `bun run parity:gate`, then finish with `bun run test:bun`, `bun run test:node`, and `bun run dts:freshness:check`.
- **Python**: the parity workflow requires parity checks, stub validation, and Python smoke tests, with `.pyi` naming/signature finalized for all APIs.

So today:

- `cxx_baseline_surface.json` freshness is an explicit C++ gate
- `index.d.ts` freshness is an explicit Node gate
- `.pyi` correctness is an explicit Python gate through `validate_stubs.py` and the Python parity workflow
- there is no separate source-backed rule that every contract refresh on one surface must also refresh the others

See [`binding-parity-policy.md`](binding-parity-policy.md) for the one-tier parity policy and gate ownership details.

---

## C++ Bridge Contract Refresh

Refresh the CXX baseline when the C++ bridge surface changes.

Typical triggers:

- changes in [`cpp-bindings/classic-cpp-bridge/src/`](../../cpp-bindings/classic-cpp-bridge/src/) wrapper modules
- changes in [`cpp-bindings/classic-cpp-bridge/build.rs`](../../cpp-bindings/classic-cpp-bridge/build.rs) (bridge source list)
- public Rust API changes in business-logic `-core` crates that the bridge exposes

The C++ refresh workflow:

1. Run the gate to detect drift: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
2. If drift is intentional, regenerate the baseline: `python tools/cxx_api_parity/generate_baseline.py --repo-root .`
3. Run the gate again to confirm zero drift
4. Commit the updated baseline in the same change

See [`cxx-parity-gate.md`](cxx-parity-gate.md) for full details.

---

## When To Refresh Node `index.d.ts`

Refresh [`node-bindings/classic-node/index.d.ts`](../../node-bindings/classic-node/index.d.ts) when the public Node export surface changes.

Treat it as a tracked generated artifact: contributors should review the committed snapshot first, and any public Node export change should refresh and commit `index.d.ts` in the same change rather than leaving freshness to CI later.

Treat it as a tracked generated artifact: contributors should review the committed snapshot first, and any public Node export change should refresh and commit `index.d.ts` in the same change rather than leaving freshness to CI later.

Typical triggers already documented in the repo include:

- changes in [`node-bindings/classic-node/src/`](../../node-bindings/classic-node/src/)
- regeneration of `index.d.ts` itself
- public Rust API changes in business-logic `-core` crates that the Node bindings expose

In practice, if a Node export name, signature, DTO shape, or async/sync contract changes, refresh and commit `index.d.ts` in the same change.

---

## When To Refresh Python `.pyi` Stubs

Refresh the affected `classic_*.pyi` files when the public Python module contract changes.

Typical documented triggers include:

- changes in `python-bindings/*-py/src/`
- changes in `python-bindings/*-py/*.pyi`
- public Rust API changes in business-logic `-core` crates that the Python bindings expose

In practice, refresh the matching `.pyi` file when a Python export name, callable signature, return type, or raised-exception contract changes.

---

## When Both Should Refresh In The Same Change

This is mostly contributor best practice inferred from the current workflow, not a separate formal gate.

Refresh all affected contract artifacts in the same change when all are true:

- the underlying Rust API change is intentionally exposed through multiple binding surfaces
- all affected bindings already cover that workflow or crate area today
- the public contract changes are user-visible on the affected surfaces, not just internal wrapper refactors

The three-surface parity policy (see [`binding-parity-policy.md`](binding-parity-policy.md)) means that new public Rust API additions should be exposed through all three bindings. In practice, if a change touches a shared business-logic `-core` crate's public surface, refresh all three binding contracts in the same change.

If only one binding surface changes, refresh only that surface's contract artifacts and validation outputs.

---

## Validation And Artifact Checks That Matter

When the C++ bridge baseline changes:

```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
```

When Node `index.d.ts` changes, the important checks are:

```powershell
# From node-bindings/classic-node
bun run parity:gate
bun run parity:gate:update-baseline   # only if the plain gate shows intentional source-backed drift
bun run parity:gate
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Relevant Node artifacts/checks:

- [`node-bindings/classic-node/parity-artifacts/tier1_gate_report.md`](../../node-bindings/classic-node/parity-artifacts/tier1_gate_report.md)
- [`node-bindings/classic-node/parity-artifacts/parity_diff_report.md`](../../node-bindings/classic-node/parity-artifacts/parity_diff_report.md)
- [`node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md`](../../node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md)

When Python `.pyi` files change, the important checks are:

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# `--inexact` stops uv from pruning maturin-built classic-*-py wheels.
uv sync --project python-bindings --inexact
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Relevant Python artifacts/checks:

- [`python-bindings/parity-artifacts/tier1_gate_report.md`](../../python-bindings/parity-artifacts/tier1_gate_report.md)
- [`python-bindings/parity-artifacts/parity_diff_report.md`](../../python-bindings/parity-artifacts/parity_diff_report.md)
- [`python-bindings/parity-artifacts/runtime_coverage_summary.md`](../../python-bindings/parity-artifacts/runtime_coverage_summary.md)
- [`python-bindings/parity-artifacts/stub_validation_report.json`](../../python-bindings/parity-artifacts/stub_validation_report.json)

If multiple surfaces refresh in one change, run all relevant workflows.

---

## Source-Backed Caveats And Non-Goals

- Node declarations are generated by NAPI-RS; Python `.pyi` files are maintained contributor-facing stubs; C++ baseline is generated by `generate_baseline.py`. They are all public contract artifacts, but they are not produced by the same mechanism.
- Current docs define separate C++, Node, and Python parity gates; they do not define a single mandatory "refresh all every time" rule.
- Node and Python do not promise exact surface parity today. Use this note to keep shared maintained workflows aligned, not to force identical exports where the repo does not already document them.
- If source, contract files, and contributor docs diverge, update the affected docs and contract artifacts in the same change.
