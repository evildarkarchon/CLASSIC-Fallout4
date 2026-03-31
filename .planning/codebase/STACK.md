# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Rust (edition 2024, rust-version 1.85.0) - All business logic; `ClassicLib-rs/` workspace
- C++20 - CLI frontend (`classic-cli/`) and Qt GUI frontend (`classic-gui/`)

**Secondary:**
- TypeScript (ES2022/CommonJS, strict mode) - Node binding CLI wrapper; `ClassicLib-rs/node-bindings/classic-node/cli/`
- Python 3.12 - Binding parity tooling, pytest test suite, and CI scripts; `ClassicLib-rs/python-bindings/` and `tools/`

## Runtime

**Rust async runtime:**
- Tokio 1.49.0 — single shared runtime enforced across all Rust crates ("ONE RUNTIME RULE")
- Shared runtime provided by `ClassicLib-rs/foundation/classic-shared-core`

**Node runtime:**
- Node.js ≥18 (targeting `@types/node` ^22) and Bun (primary test/build runner) — `ClassicLib-rs/node-bindings/classic-node/`

**Python runtime:**
- Python 3.12 (PyO3 abi3-py312 ABI) — `ClassicLib-rs/python-bindings/`

## Package Manager

**Rust:**
- Cargo with workspace resolver v2
- Lockfile: `ClassicLib-rs/Cargo.lock` (present)

**C++ dependencies:**
- vcpkg (baseline `39a6cc0e44641977a7ccdfdb01a14eaf832aa330`)
- Manifests: `classic-cli/vcpkg.json`, `classic-gui/vcpkg.json`

**Node:**
- Bun (primary), npm-compatible
- Lockfile: `ClassicLib-rs/node-bindings/classic-node/bun.lock` (present)

**Python:**
- uv (venv and package install in CI); maturin for wheel builds
- Legacy `poetry.lock` at repo root (retained for some tooling)
- CI requirements: `ClassicLib-rs/python-bindings/requirements-ci.txt` (maturin + pytest)

## Frameworks

**GUI (C++):**
- Qt 6 (Widgets, Network, testlib, thread) — `classic-gui/`; deployed as `Qt6/` subdirectory alongside `Qt6Core.dll`, etc.

**GUI (Rust TUI — in-progress):**
- Ratatui 0.30.0 + crossterm 0.28 — `ClassicLib-rs/ui-applications/classic-tui/`
- Optional native file dialog: rfd 0.15 (non-Linux only)
- Clipboard: arboard 3

**GUI bridge (optional Rust feature):**
- Slint 1.15.0 — used as optional `gui-bridge` feature in `classic-shared-core` for Slint event-loop dispatch

**CLI argument parsing (C++):**
- CLI11 (vcpkg) — `classic-cli/`

**Testing (C++ CLI):**
- Catch2 v3 (vcpkg) — `classic-cli/tests/`

**Testing (C++ GUI):**
- Qt Test (QtTest/QTest) — `classic-gui/tests/`

**Testing (Rust):**
- Rust built-in test framework + criterion 0.8.1 for benchmarks
- serial_test 3.2 for test serialization
- tempfile 3.24.0 for temp file fixtures

**Testing (Python):**
- pytest (via uv)

**Testing (Node/Bun):**
- Bun built-in test runner (`bun test`)
- Node built-in test runner (`node --test`) for cross-runtime checks

## Key Dependencies

**FFI bridges:**
- `cxx` 1.0 / `cxx-build` 1.0 — Rust↔C++ bridge in `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`; exposes types, runtime, config, scanner, database, files, scangame, game, update, message, perf, markdown, path bridges
- Corrosion v0.6.1 — CMake integration that compiles Rust as part of the C++ build (`FetchContent`)
- `napi` 3 / `napi-derive` 3 / `napi-build` 2 — NAPI-RS Node.js bindings in `classic-node`
- `pyo3` 0.27.2 (abi3-py312) / `pyo3-async-runtimes` 0.27.0 — Python bindings in `ClassicLib-rs/python-bindings/`

**Async / concurrency:**
- tokio 1.49.0 (`full` features)
- futures 0.3
- rayon 1.10 — parallel iterators
- crossbeam 0.8 — lock-free data structures
- dashmap 6.1 — concurrent hashmap
- parking_lot 0.12.5 — faster mutexes

**Database:**
- `sqlx` 0.8 (runtime-tokio, sqlite) — async connection pooling for FormID SQLite databases
- `rusqlite` 0.38.0 (bundled, backup) — synchronous SQLite access

**File I/O & parsing:**
- `ba2` 3.0.1 — Bethesda BA2 archive reading (Fallout 4 GNRL/DX10 formats)
- `walkdir` 2.5 — directory traversal
- `memmap2` 0.9.9 — memory-mapped file I/O
- `encoding_rs` 0.8 — text encoding conversion
- `chardetng` 0.1 — character encoding detection
- `ddsfile` 0.5 — DDS texture file parsing
- `pelite` 0.10 — PE executable file parsing (Windows version resource extraction)
- `configparser` 3.1 — INI file parsing (game `.ini` files)

**YAML:**
- `yaml-rust2` 0.11.0 — YAML parsing and serialization

**String / text processing:**
- `regex` 1.12.2
- `aho-corasick` 1.1.4
- `memchr` 2.7.6
- `strsim` 0.11 — string similarity
- `lasso` 0.7 (multi-threaded) — string interning
- `smartstring` 1.0 — small-string optimization
- `string_cache` 0.9.0
- `pulldown-cmark` 0.13 — Markdown → HTML rendering

**Serialization:**
- `serde` 1.0 + `serde_json` 1.0

**Version management:**
- `semver` 1.0 — semantic version comparison (update/release checks)
- `winreg` 0.52 (Windows-only, path-core) — Windows Registry access for game path detection

**Hashing / caching:**
- `xxhash-rust` 0.8 (xxh3) — fast non-cryptographic hashing
- `sha2` 0.10 — SHA-256 file integrity hashing
- `lru` 0.16.3, `quick_cache` 0.6, `rustc-hash` 2.1

**HTTP / networking:**
- `reqwest` 0.13.1 (`json` feature) — async HTTP for GitHub release checks
- `url` 2.5 — URL parsing and validation
- `scraper` 0.20 — HTML parsing (mod site URL helpers)

**Logging / tracing:**
- `log` 0.4.29 + `env_logger` 0.11 — structured log facade
- `tracing` 0.1.44 + `tracing-subscriber` 0.3.22 + `tracing-appender` 0.2 — async-aware tracing

**Misc:**
- `mimalloc` 0.1.43 — alternative allocator (optional)
- `indexmap` 2.7 — insertion-order-preserving map (YAML key order parity)
- `phf` 0.13.1 — compile-time perfect hash maps (constants-core)
- `dotenvy` 0.15 — `.env` file loading (update-core)
- `once_cell` 1.20 — lazy statics
- `dirs` 6.0.0 + `directories` 6.0.0 — cross-platform config/data paths
- `mockito` 1.5 — HTTP mocking in update-core tests
- `color-eyre` 0.6 — rich error reporting in TUI
- `open` 5 — open URLs/files in system browser/viewer (TUI)
- `fmt` (vcpkg) — C++ string formatting (CLI/GUI)

## Configuration

**Environment:**
- `VCPKG_ROOT` must be set for all C++ builds
- `GITHUB_TOKEN` (optional) — raises GitHub API rate limit from 60→5,000 req/hr; loaded via `dotenvy` from `.env`
- Python venv: `ClassicLib-rs/python-bindings/.venv` (created with `uv venv`)
- Git Bash users: source `tools/use_msvc_from_git_bash.sh` before Rust/MSVC commands

**Application config files (runtime, not build):**
- `CLASSIC Settings.yaml` — user settings (game path, scan options, FormID DB paths, update source)
- `CLASSIC Ignore.yaml` — patterns to ignore during scanning
- `CLASSIC Data/CLASSIC Fallout4 Local.yaml` — game-local data

**Build:**
- Rust: `ClassicLib-rs/Cargo.toml` (workspace root), per-crate `Cargo.toml`
- C++ CLI: `classic-cli/CMakeLists.txt`, `classic-cli/CMakePresets.json`
- C++ GUI: `classic-gui/CMakeLists.txt`, `classic-gui/CMakePresets.json`
- Node: `ClassicLib-rs/node-bindings/classic-node/package.json`, `tsconfig.json`
- Python: `rebuild_rust.ps1 -Target python` (maturin wheels)

## Platform Requirements

**Development:**
- Windows (primary target); MSVC toolchain required for C++ components
- Rust stable toolchain ≥ 1.85.0
- Bun for Node binding development
- Python 3.12 + uv for Python binding development
- `VCPKG_ROOT` for C++ builds
- PowerShell for all build scripts (`*.ps1`)

**Production:**
- Windows x64 (C++ targets are Windows/MSVC only)
- Rust business logic is cross-platform where OS APIs not required (Linux supported for Steam/Proton path detection in path-core)
- Distributed as a standalone executable bundle with Qt6 DLLs and CLASSIC Data assets

---

*Stack analysis: 2026-03-30*
