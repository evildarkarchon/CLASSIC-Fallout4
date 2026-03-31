# Rust Parser Module Overview

This page describes the current maintained parser surface for scanlog work.

## Current location

- Core parser logic lives in `ClassicLib-rs/business-logic/classic-scanlog-core`.
- Python-facing parser APIs live in `ClassicLib-rs/python-bindings/classic-scanlog-py` as part of the `classic_scanlog` module.
- Node-facing parser APIs are surfaced through `ClassicLib-rs/node-bindings/classic-node`.

## Current rule

Parser behavior belongs in the Rust core crate. Binding crates should expose wrappers, not alternate parser implementations.

## Validation

```powershell
cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Historical note

Earlier migration documents referenced parser APIs through a `classic_core.scanlog` facade. That is not the maintained surface today.
