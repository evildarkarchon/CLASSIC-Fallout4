# Python Bindings Tier-2 Backlog And Governance

## Baseline

Source artifacts:

- `docs/implementation/python_api_parity/baseline/parity_diff_report.md`
- `docs/implementation/python_api_parity/baseline/parity_diff_report.json`

Tier-1 parity is release-gated. Tier-2 remains intentionally deferred.

## Promotion criteria (Tier-2 -> Tier-1)

An API can be promoted when all are true:

1. It is required by an active maintained integration workflow.
2. The Rust symbol shape is stable for at least one release cycle.
3. Python export naming/signature is finalized in `.pyi`.
4. `parity_contract.json` includes owner, Rust symbol mapping, `pythonExportPath`,
   and expected callable signature metadata.
5. Local parity, stub validation, and runtime smoke tests pass.

## Required local checks

```powershell
uv venv
uv pip install maturin pytest
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
uv run python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Trigger points

Run parity maintenance when any of these change:

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/python-bindings/*-py/src/`
- `ClassicLib-rs/python-bindings/*-py/*.pyi`

## Contract rules

- Tier-1 contract rows cover classes, top-level functions, and callable methods.
- Method rows must use `pythonExportPath` such as
  `classic_scanlog.AnalysisConfig.from_yamldata`.
- Properties are not added as parity rows; verify them with smoke tests and stub checks.
- Mixed contracts are supported temporarily, but new rows should not rely on legacy
  `pythonExport` unless a migration step still requires it.

## Release gate

Do not cut a release unless:

- Tier-1 Python parity gate passes.
- Stub validation gate passes.
- Python binding smoke/parity tests pass.
