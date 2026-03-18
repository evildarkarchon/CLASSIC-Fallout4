# ScanGame Rust Guide

This guide describes the current maintained ScanGame Rust surfaces.

## Current layout

- Core logic: `ClassicLib-rs/business-logic/classic-scangame-core`
- Python binding: `ClassicLib-rs/python-bindings/classic-scangame-py`
- Node exposure: `ClassicLib-rs/node-bindings/classic-node`
- C++ consumers reach shared logic through `ClassicLib-rs/cpp-bindings/classic-cpp-bridge` where applicable

## Current rule

ScanGame behavior should be implemented once in `classic-scangame-core`, with bindings and frontends acting as wrappers over that logic.

## Typical validation

```powershell
cargo test -p classic-scangame-core --manifest-path ClassicLib-rs/Cargo.toml
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
```

If the Node surface changed, also run from `ClassicLib-rs/node-bindings/classic-node`:

```powershell
bun run parity:gate:local
bun run test:bun
bun run test:node
```

## Historical note

Older documentation referenced `ClassicLib.integration.scangame_factory` and transparent Python fallback/orchestration layers. Those are not the primary maintained product path today.
