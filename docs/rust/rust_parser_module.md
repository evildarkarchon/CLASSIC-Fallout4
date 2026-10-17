# Rust Parser Module Overview

This page describes the current maintained parser surface for scanlog work.

## Current location

- Core parser logic lives in `business-logic/classic-scanlog-core`.
- C++-facing parser APIs are surfaced through `cpp-bindings/classic-cpp-bridge` (the Python and Node bindings retired with ADR-0010).

## Current rule

Parser behavior belongs in the Rust core crate. Binding crates should expose wrappers, not alternate parser implementations.

## Validation

```powershell
cargo test -p classic-scanlog-core
```

## Historical note

Earlier migration documents referenced parser APIs through a `classic_core.scanlog` facade. That is not the maintained surface today.
