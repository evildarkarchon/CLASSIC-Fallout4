# CLASSIC Rust Modules - Detailed Documentation

This page summarizes the current maintained Rust module families in CLASSIC.

## Foundation crates

- `foundation/classic-shared-core` - shared runtime, shared helpers, cross-cutting support
- `foundation/classic-operation-context` - workspace-internal async operation context (no binding surface)
- `foundation/classic-vocabulary` - workspace-internal Vocabulary naming contract for domain enums (no binding surface)

The former `foundation/classic-shared-py` helper library was folded into the
one Python adapter crate (`python-bindings/classic-python-bindings`, module
`src/support/`) in issue #259.

## Business-logic crates

Representative maintained crates include:

- `classic-config-core`
- `classic-database-core`
- `classic-file-io-core`
- `classic-message-core`
- `classic-path-core`
- `classic-resource-core`
- `classic-scangame-core`
- `classic-scanlog-core`
- `classic-update-core`
- `classic-version-registry-core`
- `classic-web-core`
- `classic-xse-core`

## Binding crates

### Python

One PyO3 adapter crate, `python-bindings/classic-python-bindings`, builds a
single native extension and wheel (issue #259). It serves the 18 `classic_*`
direct-import facades (`classic_config`, `classic_scanlog`,
`classic_version_registry`, and the other domain facades under
`python-bindings/classic-python-bindings/python/`). Facade adapter code lives in
`src/classic_<name>/`. The former per-module `classic-*-py` crates no longer
exist. See [`docs/api/python-bindings-adapter.md`](../api/python-bindings-adapter.md).

### Node

- `node-bindings/classic-node`

### C++

- `cpp-bindings/classic-cpp-bridge`

## Important note

Older documentation may reference a monolithic `classic_core` facade. The maintained repo now uses split core crates and split binding modules instead.

## Where to look next

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
- `docs/development/pyo3_integration_patterns.md`
- `docs/api/`
