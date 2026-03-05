# Python API Parity Contract

This contract defines the Tier-1 parity gate between:

- Rust core symbols in `ClassicLib-rs/business-logic/*-core`
- Python binding exports declared in `.pyi` files under `ClassicLib-rs/python-bindings/*-py`

## Tier model

- `tier1`: release-gated Python APIs required by maintained integration workflows.
- `tier2`: deferred APIs tracked for later promotion.

## Current Tier-1 scope

- `classic_scanlog`
- `classic_config`
- `classic_version_registry`

Tier-1 rows are codified in `parity_contract.json` and enforced by:

`python tools/python_api_parity/check_parity_gate.py --repo-root .`

## Gate behavior

The gate fails when any Tier-1 row is:

- `missing_rust`
- `missing_python`
- `signature_mismatch`

Diagnostic artifacts are emitted under:

`ClassicLib-rs/python-bindings/parity-artifacts/`
