# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Rust 2024 edition / Rust 1.85.0 - core business logic, shared utilities, bindings, and the TUI live under the repo-root workspace shell in `Cargo.toml`, `business-logic/*`, `foundation/*`, `cpp-bindings/classic-cpp-bridge/`, `python-bindings/*`, `node-bindings/classic-node/`, and `ui-applications/classic-tui/`.
- C++20 - native CLI and Qt desktop frontends live under `classic-cli/CMakeLists.txt`, `classic-cli/src/`, `classic-gui/CMakeLists.txt`, and `classic-gui/src/`.

**Secondary:**
- Python 3.12 ABI target - PyO3 bindings and repo tooling use Python via `Cargo.toml`, `python-bindings/*`, `python-bindings/requirements-ci.txt`, `.github/workflows/ci-python-bindings.yml`, and parity tooling in `tools/python_api_parity/`.
- TypeScript / JavaScript - Node/Bun bindings and generated CLI surface live under `node-bindings/classic-node/package.json`, `node-bindings/classic-node/tsconfig.json`, `node-bindings/classic-node/src/`, and `node-bindings/classic-node/index.d.ts`.
- PowerShell - all native build orchestration and several repo utilities use PowerShell scripts in `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1`, `rebuild_rust.ps1`, `tools/enter_vs_dev_shell.ps1`, and `.github/scripts/setup-vcpkg.ps1`.
- YAML / JSON / TOML / CMake - configuration surfaces are defined in `Cargo.toml`, `classic-cli/CMakePresets.json`, `classic-gui/CMakePresets.json`, `classic-cli/vcpkg.json`, `classic-gui/vcpkg.json`, and `.github/workflows/*.yml`.

## Runtime

**Environment:**
- Windows-first native desktop/runtime stack with MSVC + Ninja + CMake 3.25+ in `README.md`, `classic-cli/build_cli.ps1`, and `classic-gui/build_gui.ps1`.
- Rust uses a single Tokio async runtime policy across crates via the repo-root workspace and binding/front-end consumers such as `ui-applications/classic-tui/src/app.rs`.
- Python bindings target CPython 3.12 through `pyo3 = { features = ["abi3-py312"] }` in `Cargo.toml`; CI also standardizes on Python 3.12 in `.github/workflows/ci-rust.yml` and `.github/workflows/ci-python-bindings.yml`.
- Node runtime coverage is validated against Node 22 in `.github/workflows/ci-typescript.yml`; Bun is used as the package/script runner for `node-bindings/classic-node/package.json`.

**Package Manager:**
- Cargo / rustup - Rust workspace manager for `Cargo.toml`.
  - Lockfile: present at `Cargo.lock`
- vcpkg - C++ dependency manager configured by `classic-cli/vcpkg.json`, `classic-gui/vcpkg.json`, `.github/scripts/setup-vcpkg.ps1`, `classic-cli/CMakePresets.json`, and `classic-gui/CMakePresets.json`.
  - Lockfile: not applicable; baseline pins are embedded in `classic-cli/vcpkg.json` and `classic-gui/vcpkg.json`
- Bun - Node binding package manager and task runner in `node-bindings/classic-node/package.json`.
  - Lockfile: missing under `node-bindings/classic-node/`
- uv - Python CI environment/bootstrap tool in `.github/workflows/ci-python-bindings.yml`.
  - Lockfile: not detected for the bindings-specific CI environment
- Poetry - a root `poetry.lock` is present at `poetry.lock`, but no matching `pyproject.toml` was detected in the repository root.

## Frameworks

**Core:**
- Tokio 1.49.0 - shared async runtime for Rust crates from `Cargo.toml`.
- PyO3 0.27.2 + `pyo3-async-runtimes` 0.27.0 - Python extension modules and async bridges from `Cargo.toml` and crates such as `python-bindings/classic-update-py/Cargo.toml`.
- NAPI-RS 3.x - Node native addon layer in `node-bindings/classic-node/Cargo.toml` and `node-bindings/classic-node/package.json`.
- CXX + Corrosion - Rust/C++ bridge stack in `cpp-bindings/classic-cpp-bridge/Cargo.toml`, `classic-cli/CMakeLists.txt`, and `classic-gui/CMakeLists.txt`.
- Qt 6 - desktop GUI framework via `classic-gui/CMakeLists.txt` and `classic-gui/vcpkg.json`.
- CLI11 + fmt - native CLI parsing/output stack via `classic-cli/CMakeLists.txt` and `classic-cli/vcpkg.json`.

**Testing:**
- Rust built-in test harness + cargo test - workspace tests driven by `.github/workflows/ci-rust.yml`.
- Catch2 3 - C++ CLI tests in `classic-cli/CMakeLists.txt` and `classic-cli/vcpkg.json`.
- Qt TestLib - GUI tests via `classic-gui/vcpkg.json` and `classic-gui/tests/CMakeLists.txt`.
- pytest - Python binding smoke tests via `python-bindings/requirements-ci.txt` and `.github/workflows/ci-python-bindings.yml`.
- Bun test / Node `--test` - runtime checks for the Node addon in `node-bindings/classic-node/package.json` and `.github/workflows/ci-typescript.yml`.

**Build/Dev:**
- CMake presets + Ninja - native configure/build entrypoints in `classic-cli/CMakePresets.json` and `classic-gui/CMakePresets.json`.
- Corrosion v0.6.1 - Cargo-into-CMake integration fetched in `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`.
- maturin - Python wheel build/install path used through `rebuild_rust.ps1` and `.github/workflows/ci-python-bindings.yml`.
- TypeScript compiler - Node CLI build path in `node-bindings/classic-node/package.json`.

## Key Dependencies

**Critical:**
- `tokio` 1.49.0 - single async runtime used by Rust core, bindings, and update checks in `Cargo.toml`.
- `reqwest` 0.13.1 - async HTTP client for update/release checks in `Cargo.toml` and `business-logic/classic-update-core/src/github.rs`.
- `sqlx` 0.8 + `rusqlite` 0.38.0 - SQLite-backed FormID/data access in `Cargo.toml` and `business-logic/classic-database-core/src/pool_sqlx.rs`.
- `serde` / `serde_json` - serialization across Rust core and bindings in `Cargo.toml`, `node-bindings/classic-node/Cargo.toml`, and `business-logic/classic-update-core/src/github.rs`.
- `yaml-rust2` 0.11.0 - YAML parsing for config/version-registry/data files in `Cargo.toml` and crates such as `business-logic/classic-version-registry-core/src/registry.rs`.

**Infrastructure:**
- `qtbase` + `qttranslations` - GUI runtime/deployment dependencies in `classic-gui/vcpkg.json`.
- `cxx` / `cxx-build` - generated bridge code for C++ consumers in `cpp-bindings/classic-cpp-bridge/Cargo.toml`.
- `napi`, `napi-derive`, `napi-build` - Node/Bun binary addon support in `node-bindings/classic-node/Cargo.toml`.
- `pyo3`, `pyo3-async-runtimes` - Python ABI surface in `Cargo.toml` and `python-bindings/classic-update-py/Cargo.toml`.
- `scraper` 0.20 - HTML parsing support included in the Rust workspace dependency set in `Cargo.toml`.
- `dashmap`, `lru`, `quick_cache`, `rayon`, `crossbeam` - concurrency and caching primitives concentrated in `Cargo.toml` and `business-logic/classic-database-core/src/pool_sqlx.rs`.

## Configuration

**Environment:**
- C++ builds require `VCPKG_ROOT`, enforced by `classic-cli/build_cli.ps1`, referenced by `classic-cli/CMakePresets.json`, and mirrored in `classic-gui/CMakePresets.json`.
- Update checks can use `GITHUB_TOKEN`, loaded through `dotenvy` in `business-logic/classic-update-core/src/github.rs`; a repo-root `.env` and `.env.example` are present but were not read.
- Diagnostic toggles include `CLASSIC_SCAN_DIAGNOSTICS` and `CLASSIC_DB_COUNTER_INTERVAL` in `business-logic/classic-scanlog-core/src/orchestrator.rs` and `cpp-bindings/classic-cpp-bridge/src/scanner.rs`.
- GUI CI uses `QT_QPA_PLATFORM=offscreen` in `.github/workflows/ci-cpp.yml`.

**Build:**
- Rust workspace manifest/lints/profiles: `Cargo.toml`
- Native CMake entrypoints: `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`
- Native preset files: `classic-cli/CMakePresets.json`, `classic-gui/CMakePresets.json`
- Native dependency manifests: `classic-cli/vcpkg.json`, `classic-gui/vcpkg.json`
- Node binding scripts/config: `node-bindings/classic-node/package.json`, `node-bindings/classic-node/tsconfig.json`
- CI pipelines: `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, `.github/workflows/benchmarks.yml`

## Platform Requirements

**Development:**
- Windows development is the primary supported path, with MSVC, CMake, Ninja, Rust, and vcpkg called out in `README.md`, `classic-cli/build_cli.ps1`, and `classic-gui/build_gui.ps1`.
- Qt 6 is expected from vcpkg by default for the GUI in `classic-gui/build_gui.ps1` and `classic-gui/CMakePresets.json`.
- Node bindings assume Bun plus a Rust toolchain in `node-bindings/classic-node/package.json` and `.github/workflows/ci-typescript.yml`.
- Python binding builds assume a local virtual environment at `python-bindings/.venv` and `uv`-managed installs in `.github/workflows/ci-python-bindings.yml` and `rebuild_rust.ps1`.

**Production:**
- Desktop Windows deliverables are packaged as ZIP archives via CPack in `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`.
- Release bundles include runtime data from `CLASSIC Data/` during native installs/packages as wired in `classic-cli/CMakeLists.txt`; GUI deployment runs `windeployqt` from `classic-gui/src/CMakeLists.txt` during install packaging.
- Node output targets `x86_64-pc-windows-msvc` in `node-bindings/classic-node/package.json`.

---

*Stack analysis: 2026-04-14*
