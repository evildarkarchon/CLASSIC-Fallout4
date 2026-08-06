# CLASSIC Rust Usage Guide

This guide describes the current maintained Rust surfaces in CLASSIC.

## Current model

- Core product logic lives in `business-logic/*-core`.
- Shared runtime/support crates live in `foundation/`.
- Python bindings live in `python-bindings/*-py`.
- Node bindings live in `node-bindings/classic-node`.
- C++ consumers use `cpp-bindings/classic-cpp-bridge`.

There is no maintained monolithic `classic_core` facade and no active `classic-rust/` workspace directory.

## Common usage paths

### Rust-only development

```powershell
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```

### Python bindings

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# --inexact is load-bearing: it keeps uv from pruning maturin-built classic-*-py wheels.
uv sync --project python-bindings --inexact
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q
```

### Node bindings

From `node-bindings/classic-node`:

```powershell
bun run build:debug
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### C++ frontends

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

## How to verify the maintained Python modules

```powershell
uv run --python python-bindings/.venv/Scripts/python.exe python -c "import classic_config, classic_scanlog, classic_version_registry; print(classic_scanlog.__version__)"
```

## Practical guidance

- Put behavior in Rust core crates first.
- Treat bindings and bridges as thin wrappers.
- If a public API changes, update the relevant docs in `docs/api/` and run the matching parity/test workflow.
