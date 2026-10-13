# CLASSIC Rust Usage Guide

This guide describes the current maintained Rust surfaces in CLASSIC.

## Current model

- Core product logic lives in `business-logic/*-core`.
- Shared runtime/support crates live in `foundation/`.
- The Python and Node bindings retired with ADR-0010.
- C++ consumers use `cpp-bindings/classic-cpp-bridge`.

There is no maintained monolithic `classic_core` facade and no active `classic-rust/` workspace directory.

## Common usage paths

### Rust-only development

```powershell
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```

### C++ frontends

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

## Practical guidance

- Put behavior in Rust core crates first.
- Treat bindings and bridges as thin wrappers.
- If a public API changes, update the relevant docs in `docs/api/` and run the matching parity/test workflow.
