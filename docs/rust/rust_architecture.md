# CLASSIC Rust Architecture Documentation

This document describes the current architecture used by the maintained Rust surfaces in CLASSIC.

## Architecture summary

CLASSIC uses Rust as the home for shared product logic, with thin consumer layers on top.

```text
classic-cli/ and classic-gui/
          -> cpp-bindings/classic-cpp-bridge
          -> business-logic/*-core
          -> foundation/*

python-bindings/*-py
          -> business-logic/*-core
          -> foundation/*

node-bindings/classic-node
          -> business-logic/*-core
          -> foundation/*
```

## Rules

- Keep business logic in `ClassicLib-rs/business-logic/*-core`.
- Keep Python, Node, and C++ layers thin.
- Preserve the shared Tokio runtime provided by Rust core facilities.
- Avoid duplicating the same logic across bindings.

## Key current-state notes

- The active Rust workspace root is `ClassicLib-rs/`.
- There is no maintained `classic_core` facade.
- There is no active `classic-rust/` workspace directory.
- Public API changes may require matching updates in Python, Node, C++, and `docs/api/`.

## Related docs

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
- `docs/development/pyo3_integration_patterns.md`
