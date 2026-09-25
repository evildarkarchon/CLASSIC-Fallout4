# Python API Parity Contract

This contract defines the Tier-1 parity gate between:

- Rust core symbols in the declared crate, including foundation owners
- Python binding exports declared in maintained `classic_*.pyi` files

## Tier model

- `tier1`: release-gated Python APIs required by maintained integration workflows.
- `tier2`: deferred APIs tracked for later promotion.

## Current Tier-1 scope

All 18 direct-import `classic_*` modules are covered. Existing row IDs remain
stable as Rust owners move and Python facades later share a native adapter.

Tier-1 rows are codified in `parity_contract.json` and enforced by:

`python tools/python_api_parity/check_parity_gate.py --repo-root .`

Most contract rows map a Rust symbol to a Python export target. Explicit
`unmapped` rows retain a Python name without claiming a Rust counterpart, and
historical `@rust` rows also inventory Rust-only source.
The source check resolves the exact (`rustCrate`, `rustSymbol`) pair; a namesake
in another crate does not satisfy it. The report records the physical
`rust_crate` separately from the stable `owner_module` grouping. Source-backed
PyO3 evidence also checks uniquely mapped exports where the wrapper names its
core owner directly, including method bodies with a single source-backed owner,
following external Rust re-exports to their defining crate. A method row that
names an owner type still checks that type in its declared crate; a direct
method-call source also checks the crate even when the row names that type
instead of the method. For checked-in facade packages, a declared export's
unresolved native import is a parity failure.
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
- `owner_mismatch`

Method arity is evaluated at the Python call site:

- instance and class methods ignore the leading `self` or `cls`
- static methods count all declared parameters

Properties are intentionally excluded from contract rows. Property coverage is
handled through runtime smoke tests and stub validation instead of parity rows.

Diagnostic artifacts are emitted under:

`python-bindings/parity-artifacts/`
