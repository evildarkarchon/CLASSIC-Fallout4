# Troubleshooting Guide for CLASSIC Rust Components

This guide covers the current troubleshooting workflow for CLASSIC's maintained Rust and Python binding surfaces.

## Current state

- The active Rust workspace is `ClassicLib-rs/`.
- Maintained Python bindings are split modules such as `classic_config`, `classic_scanlog`, `classic_version_registry`, and `classic_shared`.
- Use `ClassicLib-rs/python-bindings/.venv` for Python binding validation.
- Do not expect a maintained `classic_core` facade or a `classic-rust/` workspace directory.

## Quick diagnosis

### 1. Check the Python interpreter

```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import sys; print(sys.executable)"
```

### 2. Verify required modules import

```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import classic_config, classic_scanlog, classic_version_registry; print(classic_scanlog.__version__)"
```

### 3. Rebuild the maintained Python bindings

```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
```

## Common issues

### Python module cannot be imported

Symptoms:
- `ModuleNotFoundError` for `classic_config`, `classic_scanlog`, or `classic_version_registry`

Fix:

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
```

### Old code is still being imported

Symptoms:
- A rebuild succeeds, but Python still behaves like the previous version

Fix:

```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -Clean classic_shared classic_config classic_scanlog classic_version_registry
```

### Rust tests pass but Python binding checks fail

Likely causes:
- The stub file was not updated
- The parity contract was not updated
- The runtime coverage registry is stale

Fix:

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

### Rust core changes break Node or C++ consumers

If a Rust API is binding-facing, verify the other maintained consumers too:

```powershell
# Node
# run from ClassicLib-rs/node-bindings/classic-node
bun run parity:gate:local
bun run test:bun
bun run test:node

# C++ frontends
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

## Recommended escalation order

1. Verify the correct interpreter or toolchain is being used.
2. Rebuild the affected Rust or Python binding surface.
3. Run the relevant parity/stub/test workflow.
4. Run the consumer-specific validation for Node or C++ if the API is shared.

## Minimal current validation set

### Rust core

```powershell
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
```

### Python bindings

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```
