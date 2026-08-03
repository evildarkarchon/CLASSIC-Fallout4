# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

Read on demand, not up front:

- `docs/api/README.md` — index of contributor-facing API guides. Read it before changing any public Rust, bridge, GUI-consumer, or binding-facing API (AGENTS.md rule 8).
- `docs/workspace-migration-matrix.md` — legacy `ClassicLib-rs/` to repo-root path and command translation. Read it only when you hit that retired path root in older docs, specs, or tool config.

## Python Binding Testing Quickstart

The binding-local virtualenv at `python-bindings/.venv/` is a uv-managed project that does **not** carry the maturin-built `-py` extension modules by default. Run tests in this order:

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

Each skipped step has a distinct failure mode: skipping step 1 makes cargo's pyo3-build-config chase a stale `VIRTUAL_ENV`; skipping `--inexact` in step 2 wipes every `classic-*-py` wheel from the venv on each re-sync; skipping step 3 produces `ModuleNotFoundError` at pytest collection time.

For deeper context (why `.cargo/config.toml` intentionally omits a global PyO3 pin, which `-py` crates this rebuilds, or how the parity gates fit on top), see the Python binding test rule and the PyO3 Quick Note in `AGENTS.md`, plus `docs/implementation/python_api_parity/`.
