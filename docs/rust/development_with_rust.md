# Development Guide for CLASSIC Rust Components

This guide summarizes the current Rust development workflow for CLASSIC.

## Workspace overview

The active Cargo workspace is rooted at the repository root.

Key areas:

- `foundation/` - shared runtime and support crates
- `business-logic/` - product logic in `*-core` crates
- `cpp-bindings/` - C++ bridge crates
- `ui-applications/` - Rust-hosted UI/TUI applications

The Windows-native frontends live at the repo root in `classic-cli/` and `classic-gui/`.

## Core rules

- Put business logic in Rust core crates, not in bindings.
- Keep the C++ bridge layer thin (the Python and Node bindings retired with ADR-0010).
- Preserve the shared Tokio runtime design.
- Update `docs/api/` when public Rust or binding-facing APIs change.

## Rust setup

```powershell
rustup toolchain install stable
rustup component add rustfmt clippy
```

## Rust-only workflow

From the repo root:

```powershell
cargo fmt --all
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```

Use crate-scoped tests while iterating, for example:

```powershell
cargo test -p classic-scanlog-core
```

## C++ consumer workflow

Use the repo PowerShell scripts rather than ad-hoc CMake commands:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

## When APIs change

- Rust core API changes may require updates in the C++ bridge layer.
- Check parity artifacts for binding surfaces.
- Refresh docs under `docs/api/` if behavior or public contracts changed.

## Practical recommendation

If you are unsure which validation set applies, use the CLASSIC project guide skill or start from:

- Rust core: `cargo fmt`, `cargo clippy`, `cargo test`
- C++ frontends: `build_cli.ps1 -Test` and `build_gui.ps1 -Test`
