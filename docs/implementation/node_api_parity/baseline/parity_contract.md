# Node Bindings Parity Contract

## Scope

This contract defines how API parity is measured between:

- Rust public APIs from Tier-1 target crates:
  - `classic-scanlog-core`
  - `classic-config-core`
  - `classic-version-registry-core`
- Node surface exported by `node-bindings/classic-node/index.d.ts`

This contract establishes the live one-tier baseline: Tier-1 is the full enforced Node parity contract.

## Tier Definition

- **Tier 1 (live one-tier contract)**
  - High-level APIs required by app workflows and cross-language integration.
  - A Tier-1 contract row must map at least one Rust symbol to one Node export.
  - Missing Rust/Node side is a parity gap.
  - Signature compatibility is checked on the Node side by expected arity where defined.
  - The committed baseline currently contains **705** Tier-1 rows, and the checked-in diff report records a **705/705** matched result with zero gaps.
  - `tierDefinitions.tier2` is intentionally absent from `parity_contract.json`; this human-readable contract should not describe active Tier 2 scope.

## Acceptance Criteria

Contract/inventory is accepted when all of the following exist:

1. **Machine-readable manifests generated**
   - `rust_api_surface.json`
   - `node_api_surface.json`
2. **Machine-readable diff generated**
   - `parity_diff_report.json` with gap entries annotated by:
     - `tier`
     - `owner_module`
     - `squad`
3. **Human-readable summaries generated**
   - `parity_diff_report.md`
   - `handoff_map.md`
4. **Tier-1 contract rows are evaluated**
    - Each row is marked as one of:
      - `matched`
      - `missing_rust`
      - `missing_node`
      - `signature_mismatch`
5. **Live one-tier baseline remains synchronized across committed artifacts**
   - `parity_contract.json` remains the machine-readable source of truth.
   - `parity_diff_report.md` continues to report the live **705** Tier-1 rows and **0** gaps.
   - `.planning/phases/02-crashgen-config-merge/deferred-items.md` continues to describe the historical floor mismatch as resolved against the live **705-row one-tier** baseline.
   - `tools/node_api_parity/tests/test_check_parity_gate.py` continues to enforce `assert len(tier1) >= 705` and the absence of `tierDefinitions.tier2`.

## Owner Modules

- `scanlog`
- `config`
- `version_registry`
- `aux` (other classic-node exports outside the Tier-1 module scope)

## Squad Ownership Model

- **Squad A (scanlog/config):** owner modules `scanlog`, `config`
- **Squad B (version-registry/aux):** owner modules `version_registry`, `aux`

## Contract Source Of Truth

The machine-readable contract and Tier-1 mappings are stored in:

- `parity_contract.json`

The extractor/diff tooling consumes that file directly. The human-readable narrative in this file is a companion explanation of the same one-tier contract, not an independent policy surface.

Cross-check the live contract state with:

- `parity_diff_report.md` for the committed human-readable 705-row evaluation summary.
- `.planning/phases/02-crashgen-config-merge/deferred-items.md` for the resolved historical note about the retired 711-row story.
- `tools/node_api_parity/tests/test_check_parity_gate.py` for the executable tripwire that protects the live one-tier baseline.
