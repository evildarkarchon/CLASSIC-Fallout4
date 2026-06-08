# CLASSIC Quick Start (Contributor)

This quick start reflects the active CLASSIC architecture: **C++ frontends + Rust core**.

## 1) Prerequisites (Windows-focused)

- Visual Studio with C++ Desktop workload (MSVC; optional LLVM/clang-cl component for clang-cl builds)
- `VCPKG_ROOT` configured (example: `C:\vcpkg`)
- CMake 3.25+
- Ninja
- Rust toolchain (`cargo`)
- PowerShell 7 (`pwsh`)
- Qt 6 (for GUI builds)
- Bun (only if you are modifying Node bindings)

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## 2) Clone and bootstrap

```powershell
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
```

If you plan to run CLI integration tests using fixture submodules:

```powershell
git submodule update --init --recursive
```

---

## 3) Build active applications

### Build CLI

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Compiler clang-cl
```

### Build GUI

```powershell
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Compiler clang-cl
```

Use these scripts instead of ad-hoc CMake commands so VS environment detection and preset wiring remain consistent.

---

## 4) Run tests

### C++ tests (preferred path)

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -Compiler clang-cl
```

CLI integration tests (requires built CLI binary):

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
```

### Rust tests and quality checks

```powershell
cargo test --workspace
cargo test --workspace -- --nocapture

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

---

## 5) Rust workspace development

```powershell
cargo build --workspace
cargo build --workspace --release
```

Core domain work belongs under [`business-logic/`](../../business-logic).

If you are translating older instructions that still mention `ClassicLib-rs/...`, use the shared [`workspace migration matrix`](../workspace-migration-matrix.md) instead of guessing the repo-root replacement.

---

## 6) Node bindings workflow (only when touching Node surface)

From [`node-bindings/classic-node/`](../../node-bindings/classic-node):

```powershell
bun install
bun run build
bun run cli -- --version
bun run parity:gate
# only if the plain gate reports intentional source-backed drift
bun run parity:gate:update-baseline
bun run parity:gate
bun run test:bun
bun run test:node
```

---

## 7) CI mapping

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml): C++ CLI/GUI build + test for MSVC and clang-cl
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml): Rust format/lint/build/test
- [`ci-typescript.yml`](../../.github/workflows/ci-typescript.yml): Node parity/runtime tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml): benchmark regression checks

---

## 8) Scope boundary: maintained vs deprecated Python

- Maintained Python scope: bindings under [`python-bindings/`](../../python-bindings)
- Deprecated runtime scope: Python entrypoints/orchestration under [`deprecated/`](../../deprecated)

Do not treat legacy Python runtime paths as the default contributor flow unless the task is explicitly migration/legacy support.

