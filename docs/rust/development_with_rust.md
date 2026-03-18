# Development Guide for CLASSIC Rust Components

This guide summarizes the current Rust development workflow for CLASSIC.

## Workspace overview

The active Rust workspace is `ClassicLib-rs/`.

Key areas:

- `ClassicLib-rs/foundation/` - shared runtime and support crates
- `ClassicLib-rs/business-logic/` - product logic in `*-core` crates
- `ClassicLib-rs/python-bindings/` - PyO3 binding crates
- `ClassicLib-rs/node-bindings/` - Node bindings
- `ClassicLib-rs/cpp-bindings/` - C++ bridge crates
- `ClassicLib-rs/ui-applications/` - Rust-hosted UI/TUI applications

The Windows-native frontends live at the repo root in `classic-cli/` and `classic-gui/`.

## Core rules

- Put business logic in Rust core crates, not in bindings.
- Keep Python, Node, and C++ layers thin.
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
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
```

Use crate-scoped tests while iterating, for example:

```powershell
cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml
```

## Python binding workflow

Use a bindings-local virtual environment:

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe maturin pytest
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

For binding-surface changes, also run:

```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
```

## Node binding workflow

From `ClassicLib-rs/node-bindings/classic-node`:

```powershell
bun run build:debug
bun run parity:gate:local
bun run test:bun
bun run test:node
```

## C++ consumer workflow

Use the repo PowerShell scripts rather than ad-hoc CMake commands:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

## When APIs change

- Rust core API changes may require updates in Python, Node, and C++ binding layers.
- Check parity artifacts for binding surfaces.
- Refresh docs under `docs/api/` if behavior or public contracts changed.

## Practical recommendation

If you are unsure which validation set applies, use the CLASSIC project guide skill or start from:

- Rust core: `cargo fmt`, `cargo clippy`, `cargo test`
- Python bindings: parity gate, stub validation, rebuild, smoke tests
- Node bindings: parity gate plus Bun/Node runtime tests
- C++ frontends: `build_cli.ps1 -Test` and `build_gui.ps1 -Test`
