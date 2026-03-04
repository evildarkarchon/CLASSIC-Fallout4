# CLASSIC Testing Guide Index

This index points contributors to the active testing workflows for the current **C++ + Rust** architecture.

## 1) Primary testing entry points (active)

### C++ frontend tests (via script wrappers + CTest)

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

CLI integration test wrapper:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
```

> Policy: run C++ tests via wrapper scripts/CTest path, not by invoking test binaries directly.

### Rust workspace tests and quality gates

```powershell
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture

cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

---

## 2) CI workflow mapping

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml)
  - C++ CLI/GUI build + test jobs on Windows
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml)
  - Rust format/lint/build/test jobs
- [`ci-typescript.yml`](../../.github/workflows/ci-typescript.yml)
  - Node binding parity gate and Bun/Node runtime tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml)
  - benchmark regression checks

Use local command sets that mirror these workflows before opening PRs.

---

## 3) Binding-specific testing flows

### Node bindings (`ClassicLib-rs/node-bindings/classic-node`)

```powershell
bun install
bun run build
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python bindings (`ClassicLib-rs/python-bindings`)

Treat as maintained **integration** surfaces. Validate against the relevant Rust crates and binding-specific checks when working in that area.

---

## 4) Scope boundaries (important)

- Active app/runtime paths:
  - [`classic-cli/`](../../classic-cli)
  - [`classic-gui/`](../../classic-gui)
  - [`ClassicLib-rs/`](../../ClassicLib-rs)
- Maintained integration bindings:
  - [`ClassicLib-rs/node-bindings/`](../../ClassicLib-rs/node-bindings)
  - [`ClassicLib-rs/python-bindings/`](../../ClassicLib-rs/python-bindings)
- Deprecated runtime entrypoints/orchestration:
  - [`deprecated/`](../../deprecated)

Do not assume Python runtime/orchestration tests under `deprecated/` are part of the default contributor test flow unless the task explicitly targets migration/legacy support.

---

## 5) Related testing docs

- [`docs/testing/rust_testing_guide.md`](rust_testing_guide.md)
- [`docs/testing/TEST_STRUCTURE.md`](TEST_STRUCTURE.md)
- [`docs/testing/test_pollution_guide.md`](test_pollution_guide.md)
- [`docs/testing/testing_async_bridge.md`](testing_async_bridge.md) *(legacy Python-runtime context)*
- [`docs/testing/testing_global_registry.md`](testing_global_registry.md) *(legacy Python-runtime context)*
- [`docs/testing/testing_yaml_cache.md`](testing_yaml_cache.md) *(legacy Python-runtime context)*

---

## 6) Quick pre-PR checklist

- [ ] Ran relevant C++ wrapper script tests (`classic-cli` / `classic-gui`)
- [ ] Ran Rust format/lint/tests for touched crates
- [ ] Ran Node parity/runtime checks if Node-exposed APIs changed
- [ ] Updated docs when architecture/build/test behavior changed

Canonical policy reference: [`AGENTS.md`](../../AGENTS.md).

