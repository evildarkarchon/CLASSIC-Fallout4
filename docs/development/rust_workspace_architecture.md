# Rust Workspace Architecture

This guide describes the current CLASSIC Rust workspace structure.

## Workspace layout

The active Cargo workspace is rooted at the repository root.

```text
<repo root>/
|- Cargo.toml           workspace manifest
|- foundation/          shared runtime, error, and support crates
|- business-logic/      pure Rust product logic (`*-core`)
|- cpp-bindings/        C++ bridge crates
|- ui-applications/     Rust-hosted UI/TUI applications
```

## Layering rules

### Foundation layer

- Lives under `foundation/`
- Holds shared runtime and support crates such as `classic-shared-core`
- Owns the shared Tokio runtime facilities

### Business-logic layer

- Lives under `business-logic/`
- Uses crate names like `classic-config-core`, `classic-scanlog-core`, `classic-version-registry-core`
- Contains product logic, validation rules, parsing, matching, persistence rules, and shared behavior
- Should not depend on binding-framework or C++ bridge code

### Binding layers

- C++ bindings live under `cpp-bindings/` (the Python and Node bindings retired with ADR-0010)
- These layers should stay thin and delegate real logic to Rust core crates

## Naming conventions

- Rust core crates: `classic-{name}-core`

Examples:

- `business-logic/classic-config-core`
- `business-logic/classic-scanlog-core`

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
- There is no nested Rust workspace directory; the active workspace root is the repository root.
- C++ frontends live outside the workspace in `classic-cli/` and `classic-gui/`, but consume Rust through the C++ bridge.

## Validation by surface

### Rust core changes

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```
