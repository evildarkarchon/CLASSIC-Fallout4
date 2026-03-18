# Utilities Guide

This page summarizes the currently maintained Rust utility-oriented crates in CLASSIC.

## Current utility domains

The main utility-style Rust surfaces now live in dedicated crates, for example:

- `classic-constants-core`
- `classic-message-core`
- `classic-path-core`
- `classic-resource-core`
- `classic-version-core`
- `classic-version-registry-core`
- `classic-web-core`
- `classic-xse-core`

Related Python bindings live in matching `ClassicLib-rs/python-bindings/*-py` crates, and Node/C++ consumers access the same underlying Rust logic through their own layers.

## Current usage rule

- implement shared behavior in Rust core
- expose only thin adapters in bindings
- update `docs/api/` when public contracts change

## Validation shortcuts

```powershell
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

## Historical note

This file replaces an older phase-specific migration guide that referenced the temporary Python integration layer. The maintained source of truth is the current modular workspace under `ClassicLib-rs/`.
