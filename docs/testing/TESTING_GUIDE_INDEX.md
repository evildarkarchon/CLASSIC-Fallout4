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
- [`ci-python-bindings.yml`](../../.github/workflows/ci-python-bindings.yml)
  - Python binding parity gate, stub validation, and smoke tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml)
  - benchmark regression checks

Use local command sets that mirror these workflows before opening PRs.

---

## 3) Binding-specific testing flows

### Node bindings (`ClassicLib-rs/node-bindings/classic-node`)

```powershell
bun install
bun run build
bun run cli -- --version
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python bindings (`ClassicLib-rs/python-bindings`)

```powershell
uv venv
uv pip install maturin pytest
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry classic_pybridge
uv run python -m pytest ClassicLib-rs/python-bindings/tests -q
```

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
- [ ] Ran Python parity/stub/runtime checks if Python-exposed APIs changed
- [ ] Updated docs when architecture/build/test behavior changed

Canonical policy reference: [`AGENTS.md`](../../AGENTS.md).

