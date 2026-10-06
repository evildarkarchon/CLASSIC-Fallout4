# PyO3 Integration Patterns

This guide covers the current PyO3 patterns used by CLASSIC's maintained Python bindings.

## Current model

- Python bindings live in one adapter crate, `python-bindings/classic-python-bindings` (see `docs/api/python-bindings-adapter.md`): one native extension, `_classic_native._native`, and one wheel.
- Shared business logic lives in pure Rust crates under `business-logic/*-core` and `foundation/*`.
- The active Python surface is split into 18 direct-import facade packages such as `classic_config`, `classic_scanlog`, `classic_version_registry`, and `classic_shared`; each re-exports its native submodule's canonical objects.
- There is no maintained monolithic `classic_core` facade in the current repo layout.

## Required facade pattern

Each Python facade of the adapter crate should:

1. keep its PyO3 code in its own module, `src/classic_<name>/`, and register
   its classes, functions, exceptions, and `__version__` in that module's
   `register_facade` function (listed in `FACADES` in `src/lib.rs`);
2. keep business logic in the corresponding `*-core` crate;
3. select any core scope handle (registry, YAML cache, file hash, Version
   Registry) for its own facade at entry or object construction, never the
   process default, when the state is observable from Python;
4. keep `python/classic_<name>/__init__.py` importing each public name from
   `_classic_native._native.classic_<name>` with a literal `__all__`, in step
   with `python/classic_<name>/__init__.pyi`.

Example:

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct ExampleValue {
    #[pyo3(get)]
    pub name: String,
}

/// Registers the `classic_example` facade exports on its native submodule.
pub(crate) fn register_facade(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ExampleValue>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

## Architecture rules

- `*-core` crates should not depend on `pyo3`.
- Facade modules of the adapter crate should stay thin and do type conversion plus module registration only.
- If C++, Node, and Python all need the same behavior, implement it once in Rust core and adapt it at the binding layer.
- Keep the shared Tokio runtime in Rust core facilities; do not create a separate runtime in bindings.

## Build and install workflow

Use the Python bindings virtual environment at `python-bindings/.venv`.

### Recommended full rebuild

From the repo root:

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# --inexact is load-bearing: it keeps uv from pruning the maturin-built classic-python-bindings wheel.
uv sync --project python-bindings --inexact
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
```

### Manual wheel build

All 18 modules ship in one wheel; prefer `rebuild_rust.ps1 -Target python`,
which also removes obsolete per-module wheels and verifies the install. To
build by hand from `python-bindings/classic-python-bindings`:

```powershell
uv run --no-project --python ..\.venv\Scripts\python.exe maturin build --release --out dist
python ..\..\tools\python_wheel\one_wheel.py remove-obsolete   # run with the target venv's python
uv pip install --python ..\.venv\Scripts\python.exe .\dist\classic_python_bindings-<version>-*.whl --reinstall
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
