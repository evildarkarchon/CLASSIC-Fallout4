# CLASSIC Rust Modules - Detailed Documentation

This page summarizes the current maintained Rust module families in CLASSIC.

## Foundation crates

- `foundation/classic-shared-core` - shared runtime, shared helpers, cross-cutting support
- `foundation/classic-operation-context` - workspace-internal async operation context (no binding surface)
- `foundation/classic-vocabulary` - workspace-internal Vocabulary naming contract for domain enums (no binding surface)

The former `foundation/classic-shared-py` helper library and the Python adapter
crate it was folded into retired with the Python bindings (ADR-0010).

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

The Python and Node binding crates retired with ADR-0010.

### C++

- `cpp-bindings/classic-cpp-bridge`

## Important note

Older documentation may reference a monolithic `classic_core` facade. The maintained repo now uses split core crates and split binding modules instead.

## Where to look next

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
- `docs/api/`
