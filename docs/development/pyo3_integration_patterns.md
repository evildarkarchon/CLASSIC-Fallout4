# PyO3 Integration Patterns

This guide covers the current PyO3 patterns used by CLASSIC's maintained Python bindings.

## Current model

- Python bindings live in `python-bindings/*-py` and `foundation/classic-shared-py`.
- Shared business logic lives in pure Rust crates under `business-logic/*-core` and `foundation/*`.
- The active Python surface is split into importable modules such as `classic_config`, `classic_scanlog`, `classic_version_registry`, and `classic_shared`.
- There is no maintained monolithic `classic_core` facade in the current repo layout.

## Required crate pattern

Each Python binding crate should:

1. expose a Python module name in `[lib]`, for example:

```toml
[lib]
name = "classic_config"
crate-type = ["cdylib", "rlib"]
```

2. keep PyO3 code in the `*-py` crate only.
3. keep business logic in the corresponding `*-core` crate.
4. register Python classes and functions in that crate's `#[pymodule]` entrypoint.

Example:

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct ExampleValue {
    #[pyo3(get)]
    pub name: String,
}

#[pymodule]
fn classic_example(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ExampleValue>()?;
    Ok(())
}
```

## Architecture rules

- `*-core` crates should not depend on `pyo3`.
- `*-py` crates should stay thin and do type conversion plus module registration only.
- If C++, Node, and Python all need the same behavior, implement it once in Rust core and adapt it at the binding layer.
- Keep the shared Tokio runtime in Rust core facilities; do not create a separate runtime in bindings.

## Build and install workflow

Use the Python bindings virtual environment at `python-bindings/.venv`.

### Recommended full rebuild

From the repo root:

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# --inexact is load-bearing: it keeps uv from pruning maturin-built classic-*-py wheels.
uv sync --project python-bindings --inexact
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
```

### Single-crate wheel build

From a specific `*-py` crate directory:

```powershell
uv run --python ..\.venv\Scripts\python.exe maturin build --release --out dist
uv pip install --python ..\.venv\Scripts\python.exe .\dist\<wheel-name>.whl --reinstall
```

## Validation

For binding-surface changes, run:

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q
```

## Troubleshooting

### `ModuleNotFoundError`

- Make sure you are using `python-bindings/.venv`.
- Rebuild and reinstall the required wheel with `rebuild_rust.ps1`.
- Verify imports directly, for example:

```powershell
uv run --python python-bindings/.venv/Scripts/python.exe python -c "import classic_config, classic_scanlog, classic_version_registry; print(classic_config.__version__)"
```

### Stale extension module

If an old wheel is still being imported, rebuild with a clean reinstall:

```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -Clean classic_shared classic_config classic_scanlog classic_version_registry
```

### `#[pyclass]` or function not visible in Python

- Confirm the symbol is added in the crate's `#[pymodule]` function.
- Confirm the crate builds as `cdylib`.
- Confirm the `.pyi` stub matches the exported surface.
- Re-run stub validation and the parity gate.
