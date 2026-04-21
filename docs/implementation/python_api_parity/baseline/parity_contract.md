# Python API Parity Contract

This contract defines the Tier-1 parity gate between:

- Rust core symbols in `business-logic/*-core`
- Python binding exports declared in `.pyi` files under `python-bindings/*-py`

## Tier model

- `tier1`: release-gated Python APIs required by maintained integration workflows.
- `tier2`: deferred APIs tracked for later promotion.

## Current Tier-1 scope

- `classic_scanlog`
- `classic_config`
- `classic_version_registry`

Tier-1 rows are codified in `parity_contract.json` and enforced by:

`python tools/python_api_parity/check_parity_gate.py --repo-root .`

Each contract row maps one Rust symbol to one Python callable export target.
For Python, Tier-1 now uses `pythonExportPath` as the primary contract key:

- top-level function/class: `classic_config.clear_yaml_cache`
- class or static method: `classic_config.YamlData.from_yaml_content`
- instance method: `classic_version_registry.VersionRegistry.match_version`

Legacy `pythonExport` rows remain accepted during migration, but new Tier-1
entries should use `pythonExportPath`.

## Gate behavior

The gate fails when any Tier-1 row is:

- `missing_rust`
- `missing_python`
- `signature_mismatch`

Method arity is evaluated at the Python call site:

- instance and class methods ignore the leading `self` or `cls`
- static methods count all declared parameters

Properties are intentionally excluded from contract rows. Property coverage is
handled through runtime smoke tests and stub validation instead of parity rows.

Diagnostic artifacts are emitted under:

`python-bindings/parity-artifacts/`
