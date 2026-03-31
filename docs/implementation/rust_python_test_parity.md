# Rust-Python Test Parity

This document describes the current parity model for CLASSIC's maintained Python bindings.

## Current parity model

CLASSIC no longer tracks Python parity against a monolithic `classic-rust/` test tree.
The maintained parity workflow is contract-based and lives around the modular bindings in
`ClassicLib-rs/python-bindings/`.

## Source of truth

- Tier-1 contract: `docs/implementation/python_api_parity/baseline/parity_contract.json`
- Runtime coverage registry: `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json`
- Generated parity artifacts: `ClassicLib-rs/python-bindings/parity-artifacts/`
- Smoke/parity tests: `ClassicLib-rs/python-bindings/tests/`

## Maintained Python test entry points

- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py`
- `ClassicLib-rs/python-bindings/tests/test_python_parity_tooling.py`
- `ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py`

These tests validate the active Python binding surfaces such as:

- `classic_config`
- `classic_scanlog`
- `classic_version_registry`

Additional binding crates are validated through stubs, parity metadata, and targeted rebuild/install workflows.

## Required workflow when Python binding APIs change

1. Update the Rust binding crate and its `.pyi` stub.
2. If the public surface changed, update `docs/implementation/python_api_parity/baseline/parity_contract.json` as needed.
3. Update `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` for newly runtime-verified or deferred surfaces.
4. Refresh parity artifacts and run the smoke tests.

## Local commands

Use the Python bindings virtual environment at `ClassicLib-rs/python-bindings/.venv`.

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Relationship to Rust tests

- Core behavior should be tested first in Rust crates under `ClassicLib-rs/business-logic/`.
- Python tests should verify that the PyO3 binding surface is callable, correctly typed, and aligned with the parity contract.
- Binding tests should not reimplement large amounts of core-business-logic coverage that already belongs in Rust.

## Practical rule

If a change affects a maintained Python binding surface, the expected evidence is:

- Rust tests pass for the affected core crate(s)
- Python parity gate passes
- Stub validation passes
- Python smoke tests pass in `ClassicLib-rs/python-bindings/.venv`
