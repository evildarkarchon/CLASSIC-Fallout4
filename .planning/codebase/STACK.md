# Technology Stack

**Analysis Date:** 2026-04-04

## Languages

**Primary:**
- Rust (edition 2024, MSRV 1.85.0) - All business logic, bindings, and TUI (`ClassicLib-rs/`)
- C++20 - CLI and Qt GUI frontends (`classic-cli/`, `classic-gui/`)

**Secondary:**
- TypeScript 5.8 - Node.js binding CLI wrapper (`ClassicLib-rs/node-bindings/classic-node/cli/`)
- Python 3.12 - Python binding adapters and parity/tooling scripts (`ClassicLib-rs/python-bindings/`, `tools/`)

## Runtime

**Environment:**
- Windows-only native targets (MSVC x64); Rust workspace is cross-platform at source level but CI is Windows-only
- Single shared Tokio async runtime — one runtime rule enforced project-wide (`classic-shared-core`)

**Package Managers:**
- Cargo (Rust workspace) — lockfile present at `ClassicLib-rs/Cargo.lock`
- Bun (Node bindings) — lockfile present at `ClassicLib-rs/node-bindings/classic-node/bun.lockb`
- uv (Python bindings) — venv at `ClassicLib-rs/python-bindings/.venv`
- vcpkg (C++ dependencies) — managed per-component via `classic-cli/vcpkg.json` and `classic-gui/vcpkg.json`

## Frameworks

**Core Async:**
- tokio 1.49.0 — shared runtime, async I/O, task scheduling (`workspace dependency`)

**GUI:**
- Qt 6 (qtbase with network, testlib, widgets, thread) — C++ desktop GUI (`classic-gui/`)
- Slint 1.15.0 — optional Rust GUI bridge (feature-gated `gui-bridge` in `classic-shared-core`)
- Ratatui 0.30 + crossterm 0.28 — terminal UI (`ClassicLib-rs/ui-applications/classic-tui/`)

**Binding Frameworks:**
- PyO3 0.27.2 (abi3-py312) — Python extension modules (`ClassicLib-rs/python-bindings/`)
- NAPI-RS 3 (napi9) — Node.js/Bun native addon (`ClassicLib-rs/node-bindings/classic-node/`)
- CXX 1.0 — C++ FFI bridge (`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`)

**Build Integration:**
- Corrosion v0.6.1 — Cargo-into-CMake integration for C++ frontends (fetched at CMake configure time)
- Maturin — Python wheel builder for PyO3 crates

**C++ Libraries (via vcpkg):**
- CLI11 — CLI argument parsing (`classic-cli/`)
- {fmt} — string formatting (`classic-cli/`)
- Catch2 3 — C++ unit testing (`classic-cli/`)
- Qt 6 (qtbase + qttranslations) — GUI framework (`classic-gui/`)

**Testing:**
- Rust built-in `cargo test` + `criterion 0.5/0.6/0.8` (benchmarks)
- pytest — Python binding smoke tests
- Bun test + Node `--test` — Node binding runtime tests
- Catch2 3 — C++ CLI unit tests
- mockito 1.5 — HTTP mocking in Rust update tests (`classic-update-core`)

## Key Dependencies

**Critical:**
- `rusqlite 0.38.0` (bundled) + `sqlx 0.8` (runtime-tokio, sqlite) — local SQLite FormID databases
- `ba2 3.0.1` — Bethesda Archive 2 file format support (game mod file scanning)
- `regex 1.12.2` + `aho-corasick 1.1.4` + `memchr 2.7.6` — crash log pattern matching
- `yaml-rust2 0.11.0` — YAML config parsing (no serde_yaml; custom parser)
- `reqwest 0.13.1` — async HTTP client for GitHub release checks
- `pelite 0.10` — PE file parsing for game/XSE version extraction from Windows binaries
- `semver 1.0` — version comparison for GitHub releases and crashgen rules
- `encoding_rs 0.8` + `chardetng 0.1` — multi-encoding log file support

**Performance:**
- `rayon 1.10` — parallel crash log scanning
- `dashmap 6.1` — concurrent hash maps
- `parking_lot 0.12.5` — fast mutexes/RwLocks
- `lasso 0.7` (multi-threaded) — fast string interning
- `quick_cache 0.6` — lock-free concurrent cache
- `xxhash-rust 0.8` (xxh3) — fast non-cryptographic hashing
- `rustc-hash 2.1` — fast hasher for short strings
- `mimalloc 0.1.43` — optional alternative allocator (feature flag in `classic-scanlog-core`)
- `memmap2 0.9.9` — memory-mapped file I/O

**Serialization:**
- `serde 1.0` + `serde_json 1.0` — structured data serialization
- `indexmap 2.7` — ordered map (required for YAML key-order parity with Python)

**Data & Parsing:**
- `ddsfile 0.5` — DDS texture file validation
- `scraper 0.20` — HTML parsing
- `pulldown-cmark 0.13` — Markdown to HTML rendering (GUI help content)
- `configparser 3.1` — INI file parsing
- `strsim 0.11` — string similarity (fuzzy matching)
- `walkdir 2.5` — recursive directory traversal

## Configuration

**Environment:**
- `VCPKG_ROOT` env var required for C++ builds
- `GITHUB_TOKEN` optional env var (loaded via `dotenvy` from `.env`) to raise GitHub API rate limit for update checks
- No `.env` file committed — must be created locally for token auth

**Build:**
- `ClassicLib-rs/Cargo.toml` — Rust workspace root
- `ClassicLib-rs/.cargo/config.toml` — cargo aliases (flame, profile-build)
- `classic-cli/CMakeLists.txt` + `classic-cli/CMakePresets.json` — CLI build
- `classic-gui/CMakeLists.txt` + `classic-gui/CMakePresets.json` — GUI build
- `ClassicLib-rs/node-bindings/classic-node/tsconfig.json` — TypeScript (CommonJS, ES2022 target, outDir `dist/`)
- `pyrightconfig.json` — Python type checking config at repo root

**Release Profiles:**
- `release`: opt-level=3, lto=thin, codegen-units=1, strip=true
- `release-with-debug`: inherits release, debug=true (for profiling)

## Platform Requirements

**Development:**
- Windows (MSVC toolchain) — required for C++ and CXX bridge targets
- Visual Studio linker must shadow Git's `usr/bin/link.exe` (use `tools/use_msvc_from_git_bash.sh`)
- vcpkg installed with `VCPKG_ROOT` set

**Production:**
- Windows x86_64 MSVC target for all native binaries
- Python 3.12+ for Python binding consumers
- Node 22+ / Bun (latest) for Node binding consumers

---

*Stack analysis: 2026-04-04*
