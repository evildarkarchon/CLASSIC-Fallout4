# Rust Workspace Architecture

This guide describes the current CLASSIC Rust workspace structure.

## Workspace layout

The active Rust workspace lives under `ClassicLib-rs/`.

```text
ClassicLib-rs/
|- foundation/          shared runtime, error, and support crates
|- business-logic/      pure Rust product logic (`*-core`)
|- python-bindings/     PyO3 binding crates (`*-py`)
|- node-bindings/       Node/NAPI bindings
|- cpp-bindings/        C++ bridge crates
|- ui-applications/     Rust-hosted UI/TUI applications
```

## Layering rules

### Foundation layer

- Lives under `ClassicLib-rs/foundation/`
- Holds shared runtime and support crates such as `classic-shared-core`
- Owns the shared Tokio runtime facilities

### Business-logic layer

- Lives under `ClassicLib-rs/business-logic/`
- Uses crate names like `classic-config-core`, `classic-scanlog-core`, `classic-version-registry-core`
- Contains product logic, validation rules, parsing, matching, persistence rules, and shared behavior
- Should not depend on PyO3, Node, or C++ bridge code

### Binding layers

- Python bindings live under `ClassicLib-rs/python-bindings/*-py`
- Node bindings live under `ClassicLib-rs/node-bindings/`
- C++ bindings live under `ClassicLib-rs/cpp-bindings/`
- These layers should stay thin and delegate real logic to Rust core crates

## Naming conventions

- Rust core crates: `classic-{name}-core`
- Python binding crates: `classic-{name}-py`
- Python import names: `classic_{name}`

Examples:

- `ClassicLib-rs/business-logic/classic-config-core`
- `ClassicLib-rs/python-bindings/classic-config-py`
- `ClassicLib-rs/business-logic/classic-scanlog-core`
- `ClassicLib-rs/python-bindings/classic-scanlog-py`

## Dependency direction

Dependencies should flow downward only:

```text
Consumers (CLI / GUI / TUI / bindings)
        -> business-logic core crates
        -> foundation crates
```

Bindings should not become alternate homes for business logic.

## Important current-state notes

- There is no maintained `classic_core` facade crate in the current workspace.
- There is no `classic-rust/` workspace directory; the active workspace root is `ClassicLib-rs/`.
- C++ frontends live outside the workspace in `classic-cli/` and `classic-gui/`, but consume Rust through the C++ bridge.

## Validation by surface

### Rust core changes

```powershell
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
```

### Python binding changes

```powershell
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe maturin pytest
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
```

### Node binding changes

Run from `ClassicLib-rs/node-bindings/classic-node`:

```powershell
bun run build:debug
bun run parity:gate:local
bun run test:bun
bun run test:node
```
