# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
@docs/api/README.md
@docs/workspace-migration-matrix.md

## Python Binding Testing Quickstart

The binding-local virtualenv at `python-bindings/.venv/` is a full uv-managed project (`python-bindings/pyproject.toml`, `python-bindings/uv.lock`). It does not carry the maturin-built `-py` extension modules by default. Run tests in this order:

```powershell
# 1. Pin pyo3's interpreter for any cargo invocation (shell-scoped).
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"

# 2. Create/refresh the tooling venv from the locked manifest.
#    `--inexact` is load-bearing — it stops uv from pruning the
#    maturin-built `classic-*-py` wheels (they are not declared in
#    pyproject.toml). Add `--group drift-guards` if you also need
#    ruamel.yaml for `tools/schema_version_gate.py`.
uv sync --project python-bindings --inexact

# 3. Build and install every `-py` crate into the venv via maturin.
./rebuild_rust.ps1 -Target python

# 4. Run pytest through the project's venv. `--project` pins the
#    environment without changing CWD, so pytest sees repo-root paths.
#    Use `python -m pytest`, NOT the `pytest.exe` entrypoint — the
#    config crate anchors settings lookup to `sys.argv[0]`'s parent,
#    which goes wrong if sys.argv[0] is `.venv\Scripts\pytest.exe`.
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Skipping step 3 produces `ModuleNotFoundError` at pytest collection time (the test files `import classic_shared`, `import classic_version_registry`, etc., and those wheels have not been installed). Skipping step 1 makes cargo's pyo3-build-config chase `VIRTUAL_ENV` and fail if that path is stale. Skipping `--inexact` in step 2 wipes every `classic-*-py` wheel from the venv on each re-sync.

For deeper context (why `.cargo/config.toml` intentionally omits a global PyO3 pin, which `-py` crates this rebuilds, or how the parity gates fit on top), see rule 9 and the PyO3 Quick Note in `AGENTS.md`, plus `docs/implementation/python_api_parity/`.