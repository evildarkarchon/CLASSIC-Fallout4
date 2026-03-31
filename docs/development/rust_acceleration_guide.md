# Rust Acceleration & Troubleshooting Guide

This guide describes the current Rust-backed Python binding workflow for CLASSIC.

## Current state

- Rust business logic lives in `ClassicLib-rs/business-logic/*-core`.
- Python bindings live in `ClassicLib-rs/python-bindings/*-py` plus `ClassicLib-rs/foundation/classic-shared-py`.
- Active imports are split modules such as `classic_config`, `classic_scanlog`, `classic_version_registry`, and `classic_shared`.
- The current maintained workflow does not use a monolithic `classic_core` module.

## Quick verification

Create and use the bindings-local virtual environment:

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
```

Verify imports:

```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import classic_config, classic_scanlog, classic_version_registry; print(classic_scanlog.__version__)"
```

Run the maintained Python binding smoke tests:

```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Common issues

### `ModuleNotFoundError`

Cause:
- The bindings were not built and installed into `ClassicLib-rs/python-bindings/.venv`.
- The wrong Python interpreter is being used.

Fix:

```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import classic_config"
```

### Changes are not reflected after rebuild

Cause:
- A stale wheel or extension module is still installed in the bindings venv.

Fix:

```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -Clean classic_shared classic_config classic_scanlog classic_version_registry
```

### Export missing from Python

Cause:
- The binding crate did not register the symbol in `#[pymodule]`.
- The symbol was added in Rust but the stub/parity artifacts were not refreshed.

Fix:

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
```

### Wrong environment selected

Check which interpreter you are using:

```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import sys; print(sys.executable)"
```

That path should resolve inside `ClassicLib-rs/python-bindings/.venv`.

## Recommended validation set

When Python binding APIs change, run:

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```
