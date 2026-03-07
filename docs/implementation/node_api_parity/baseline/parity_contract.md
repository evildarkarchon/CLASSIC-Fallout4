# Node Bindings Parity Contract

## Scope

This contract defines how API parity is measured between:

- Rust public APIs from Tier-1 target crates:
  - `classic-scanlog-core`
  - `classic-config-core`
  - `classic-version-registry-core`
- Node surface exported by `ClassicLib-rs/node-bindings/classic-node/index.d.ts`

This contract establishes a hybrid-tiered baseline: Tier-1 is enforced now, Tier-2 is intentionally triaged.

## Tier Definitions

- **Tier 1 (must-have now)**
  - High-level APIs required by app workflows and cross-language integration.
  - A Tier-1 contract row must map at least one Rust symbol to one Node export.
  - Missing Rust/Node side is a parity gap.
  - Signature compatibility is checked on the Node side by expected arity where defined.

- **Tier 2 (defer-capable)**
  - Lower-level internals and advanced APIs not required for immediate workflow parity.
  - Still inventoried and reported as gaps/backlog, but not Tier-1 blockers.

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

The extractor/diff tooling consumes that file directly.
