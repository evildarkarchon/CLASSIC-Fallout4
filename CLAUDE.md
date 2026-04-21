# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
@docs/api/README.md
@docs/workspace-migration-matrix.md

## Python Binding Testing Quickstart

The binding-local virtualenv at `python-bindings/.venv/` does not carry the maturin-built `-py` extension modules by default. Run tests in this order:

```powershell
# 1. Pin pyo3's interpreter for any cargo invocation (shell-scoped).
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"

# 2. Build and install every `-py` crate into the venv via maturin.
./rebuild_rust.ps1 -Target python

# 3. Run pytest through uv, pinning the interpreter so a stale
#    global VIRTUAL_ENV cannot redirect pytest to a different Python.
uv run --python python-bindings/.venv/Scripts/python.exe `
    python -m pytest python-bindings/tests -q
```

Skipping step 2 produces `ModuleNotFoundError` at pytest collection time (the test files `import classic_shared`, `import classic_version_registry`, etc., and those wheels have not been installed). Skipping step 1 makes cargo's pyo3-build-config chase `VIRTUAL_ENV` and fail if that path is stale.

For deeper context (why `.cargo/config.toml` intentionally omits a global PyO3 pin, which `-py` crates this rebuilds, or how the parity gates fit on top), see rule 9 and the PyO3 Quick Note in `AGENTS.md`, plus `docs/implementation/python_api_parity/`.