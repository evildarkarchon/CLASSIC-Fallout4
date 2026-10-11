# ScanGame Rust Guide

This guide describes the current maintained ScanGame Rust surfaces.

## Current layout

- Core logic: `business-logic/classic-scangame-core`
- C++ consumers reach shared logic through `cpp-bindings/classic-cpp-bridge` where applicable

## Current rule

ScanGame behavior should be implemented once in `classic-scangame-core`, with bindings and frontends acting as wrappers over that logic.

## Typical validation

```powershell
cargo test -p classic-scangame-core
```

The Python and Node bindings that also wrapped this crate retired with ADR-0010.

## Historical note

Older documentation referenced `ClassicLib.integration.scangame_factory` and transparent Python fallback/orchestration layers. Those are not the primary maintained product path today.
