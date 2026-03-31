# CLASSIC Rust Modules - Detailed Documentation

This page summarizes the current maintained Rust module families in CLASSIC.

## Foundation crates

- `ClassicLib-rs/foundation/classic-shared-core` - shared runtime, shared helpers, cross-cutting support
- `ClassicLib-rs/foundation/classic-shared-py` - Python-facing shared support module

## Business-logic crates

Representative maintained crates include:

- `classic-config-core`
- `classic-constants-core`
- `classic-database-core`
- `classic-file-io-core`
- `classic-message-core`
- `classic-path-core`
- `classic-resource-core`
- `classic-scangame-core`
- `classic-scanlog-core`
- `classic-settings-core`
- `classic-update-core`
- `classic-version-core`
- `classic-version-registry-core`
- `classic-web-core`
- `classic-xse-core`
- `classic-yaml-core`

## Binding crates

### Python

Maintained Python modules are split across binding crates such as:

- `classic-config-py` -> `classic_config`
- `classic-scanlog-py` -> `classic_scanlog`
- `classic-version-registry-py` -> `classic_version_registry`
- additional `*-py` crates for other domains under `ClassicLib-rs/python-bindings/`

### Node

- `ClassicLib-rs/node-bindings/classic-node`

### C++

- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge`

## Important note

Older documentation may reference a monolithic `classic_core` facade. The maintained repo now uses split core crates and split binding modules instead.

## Where to look next

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
- `docs/development/pyo3_integration_patterns.md`
- `docs/api/`
