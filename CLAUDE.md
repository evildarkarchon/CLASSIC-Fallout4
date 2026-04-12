# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
@docs/api/README.md

## Build Commands

### Rust (from repo root)

```
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

### C++ (always use PowerShell wrappers, never raw ctest)

```
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 [-Clean] [-Test] [-Install] [-Package] [-Debug]
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 [-Clean] [-Test] [-Install] [-Package] [-Debug]
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "test name"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
```

### Node bindings (from ClassicLib-rs/node-bindings/classic-node)

```
bun install && bun run build
bun run parity:gate:local
bun run test:bun && bun run test:node
```

### Python bindings

```
./rebuild_rust.ps1 -Target python [-Crates <names>]
python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run pytest ClassicLib-rs/python-bindings/tests -q
```

### Formatting (pre-commit minimum)

```
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml
uv run ruff format .
```

## Commit Conventions

Prefix commits: `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`. Capitalize the first word after the prefix.

## Key Gotchas

- `VCPKG_ROOT` env var must be set for C++ builds.
- From Git Bash, source `tools/use_msvc_from_git_bash.sh` before Rust or MSVC C++ commands so Git's `link.exe` doesn't shadow the VS linker.
- Python venv for bindings lives at `ClassicLib-rs/python-bindings/.venv`, not repo root.
- `sample_logs/FO4/` is a git submodule with test fixtures.
- Trailing whitespace is intentionally NOT trimmed in markdown files.
- Never output to `nul` on Windows — it creates an undeletable file on system drives.

## Subdirectory CLAUDE.md

For module-specific instructions (e.g., `ClassicLib-rs/CLAUDE.md`, `classic-cli/CLAUDE.md`), add a CLAUDE.md in that directory. It loads automatically when Claude works there.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**CLASSIC Crate Consolidation Milestone**

The active milestone reduces workspace granularity by merging or redistributing redundant crates while keeping the Rust core, C++ bridge, Node bindings, and Python bindings in parity. Phase 3 specifically redistributes the retired constants surface across `classic-version-registry-core`, `classic-settings-core`, and `classic-shared-core` with zero behavioral drift.

**Core Value:** The Rust workspace keeps minimal, well-bounded crates with no redundant boundaries, while all three binding surfaces stay in full parity with zero drift.

### Constraints

- **Platform**: Native C++ targets are Windows-only (MSVC x64); Rust workspace is cross-platform at source level
- **Runtime**: Single shared Tokio runtime — no new runtimes
- **Bindings**: All binding changes must pass existing parity gates (`check_parity_gate.py` for Python, `parity:gate:local` for Node)
- **Testing**: Use PowerShell build wrappers for C++ tests, never raw ctest
- **Backwards compat**: Python FormID legacy map format gets deprecation warning first, not immediate removal
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Rust (edition 2024, MSRV 1.85.0) - All business logic, bindings, and TUI (`ClassicLib-rs/`)
- C++20 - CLI and Qt GUI frontends (`classic-cli/`, `classic-gui/`)
- TypeScript 5.8 - Node.js binding CLI wrapper (`ClassicLib-rs/node-bindings/classic-node/cli/`)
- Python 3.12 - Python binding adapters and parity/tooling scripts (`ClassicLib-rs/python-bindings/`, `tools/`)
## Runtime
- Windows-only native targets (MSVC x64); Rust workspace is cross-platform at source level but CI is Windows-only
- Single shared Tokio async runtime — one runtime rule enforced project-wide (`classic-shared-core`)
- Cargo (Rust workspace) — lockfile present at `ClassicLib-rs/Cargo.lock`
- Bun (Node bindings) — lockfile present at `ClassicLib-rs/node-bindings/classic-node/bun.lockb`
- uv (Python bindings) — venv at `ClassicLib-rs/python-bindings/.venv`
- vcpkg (C++ dependencies) — managed per-component via `classic-cli/vcpkg.json` and `classic-gui/vcpkg.json`
## Frameworks
- tokio 1.49.0 — shared runtime, async I/O, task scheduling (`workspace dependency`)
- Qt 6 (qtbase with network, testlib, widgets, thread) — C++ desktop GUI (`classic-gui/`)
- Slint 1.15.0 — optional Rust GUI bridge (feature-gated `gui-bridge` in `classic-shared-core`)
- Ratatui 0.30 + crossterm 0.28 — terminal UI (`ClassicLib-rs/ui-applications/classic-tui/`)
- PyO3 0.27.2 (abi3-py312) — Python extension modules (`ClassicLib-rs/python-bindings/`)
- NAPI-RS 3 (napi9) — Node.js/Bun native addon (`ClassicLib-rs/node-bindings/classic-node/`)
- CXX 1.0 — C++ FFI bridge (`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`)
- Corrosion v0.6.1 — Cargo-into-CMake integration for C++ frontends (fetched at CMake configure time)
- Maturin — Python wheel builder for PyO3 crates
- CLI11 — CLI argument parsing (`classic-cli/`)
- {fmt} — string formatting (`classic-cli/`)
- Catch2 3 — C++ unit testing (`classic-cli/`)
- Qt 6 (qtbase + qttranslations) — GUI framework (`classic-gui/`)
- Rust built-in `cargo test` + `criterion 0.5/0.6/0.8` (benchmarks)
- pytest — Python binding smoke tests
- Bun test + Node `--test` — Node binding runtime tests
- Catch2 3 — C++ CLI unit tests
- mockito 1.5 — HTTP mocking in Rust update tests (`classic-update-core`)
## Key Dependencies
- `rusqlite 0.38.0` (bundled) + `sqlx 0.8` (runtime-tokio, sqlite) — local SQLite FormID databases
- `ba2 3.0.1` — Bethesda Archive 2 file format support (game mod file scanning)
- `regex 1.12.2` + `aho-corasick 1.1.4` + `memchr 2.7.6` — crash log pattern matching
- `yaml-rust2 0.11.0` — YAML config parsing (no serde_yaml; custom parser)
- `reqwest 0.13.1` — async HTTP client for GitHub release checks
- `pelite 0.10` — PE file parsing for game/XSE version extraction from Windows binaries
- `semver 1.0` — version comparison for GitHub releases and crashgen rules
- `encoding_rs 0.8` + `chardetng 0.1` — multi-encoding log file support
- `rayon 1.10` — parallel crash log scanning
- `dashmap 6.1` — concurrent hash maps
- `parking_lot 0.12.5` — fast mutexes/RwLocks
- `lasso 0.7` (multi-threaded) — fast string interning
- `quick_cache 0.6` — lock-free concurrent cache
- `xxhash-rust 0.8` (xxh3) — fast non-cryptographic hashing
- `rustc-hash 2.1` — fast hasher for short strings
- `mimalloc 0.1.43` — optional alternative allocator (feature flag in `classic-scanlog-core`)
- `memmap2 0.9.9` — memory-mapped file I/O
- `serde 1.0` + `serde_json 1.0` — structured data serialization
- `indexmap 2.7` — ordered map (required for YAML key-order parity with Python)
- `ddsfile 0.5` — DDS texture file validation
- `scraper 0.20` — HTML parsing
- `pulldown-cmark 0.13` — Markdown to HTML rendering (GUI help content)
- `configparser 3.1` — INI file parsing
- `strsim 0.11` — string similarity (fuzzy matching)
- `walkdir 2.5` — recursive directory traversal
## Configuration
- `VCPKG_ROOT` env var required for C++ builds
- `GITHUB_TOKEN` optional env var (loaded via `dotenvy` from `.env`) to raise GitHub API rate limit for update checks
- No `.env` file committed — must be created locally for token auth
- `ClassicLib-rs/Cargo.toml` — Rust workspace root
- `ClassicLib-rs/.cargo/config.toml` — cargo aliases (flame, profile-build)
- `classic-cli/CMakeLists.txt` + `classic-cli/CMakePresets.json` — CLI build
- `classic-gui/CMakeLists.txt` + `classic-gui/CMakePresets.json` — GUI build
- `ClassicLib-rs/node-bindings/classic-node/tsconfig.json` — TypeScript (CommonJS, ES2022 target, outDir `dist/`)
- `pyrightconfig.json` — Python type checking config at repo root
- `release`: opt-level=3, lto=thin, codegen-units=1, strip=true
- `release-with-debug`: inherits release, debug=true (for profiling)
## Platform Requirements
- Windows (MSVC toolchain) — required for C++ and CXX bridge targets
- Visual Studio linker must shadow Git's `usr/bin/link.exe` (use `tools/use_msvc_from_git_bash.sh`)
- vcpkg installed with `VCPKG_ROOT` set
- Windows x86_64 MSVC target for all native binaries
- Python 3.12+ for Python binding consumers
- Node 22+ / Bun (latest) for Node binding consumers
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Rust: `snake_case.rs` (e.g., `core.rs`, `pool_sqlx.rs`, `game_files.rs`)
- Crates: kebab-case with game-prefix (e.g., `classic-config-core`, `classic-file-io-py`)
- C++ source: `snake_case.cpp` / `snake_case.h` (e.g., `cli_args.cpp`, `thread_pool.h`)
- TypeScript: `camelCase.ts` for CLI (`run-scan.ts`), `kebab.spec.ts` for tests
- Python: `snake_case.py` (e.g., `tier1_parity_fixtures.py`)
- Rust: `snake_case` for all functions and methods (e.g., `load_yaml_file`, `resolve_settings_search_paths`)
- NAPI (Node bindings): Rust functions are `snake_case` internally; NAPI auto-converts them to `camelCase` for JS consumers
- PyO3 (Python bindings): `snake_case` for Python-facing methods, using `#[pyo3(name = "...")]` to override when needed
- C++: `snake_case` for free functions and methods (e.g., `parse_args`, `auto_concurrency_for_cpu_count`)
- TypeScript: `camelCase` (e.g., `parseArgs`, `printHelp`, `requireValue`)
- Rust: `snake_case` always
- C++: `snake_case` (e.g., `cpu_count`, `recommended`, `args`)
- TypeScript: `camelCase` (e.g., `gameVersion`, `fcxMode`, `showFidValues`)
- Python: `snake_case`
- Rust: `PascalCase` (e.g., `FileIOCore`, `YamlDataCore`, `SuspectScanner`, `BackupType`)
- NAPI wrapper types: `Js` prefix (e.g., `JsModConflictEntry`, `JsSuspectErrorRule`, `JsDatabasePool`)
- C++: `PascalCase` structs (e.g., `CliArgs`, `ArgvBuilder`, `ProgressDisplay`)
- TypeScript interfaces/types: `PascalCase` (e.g., `CliOptions`, `SupportedGame`)
- Rust: `SCREAMING_SNAKE_CASE` (e.g., `DEFAULT_CONFIG_FILENAME`, `NULL_VERSION`)
- TypeScript: `SCREAMING_SNAKE_CASE` (e.g., `BATCH_CACHE_TTL`, `THIS_SUITE`)
- Python module names: `classic_config`, `classic_scanlog`, `classic_version_registry` (underscore, not hyphen)
## Code Style
- Tool: `rustfmt` via `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml`
- No standalone `rustfmt.toml` detected; default rustfmt settings apply
- Workspace lints enforced in `ClassicLib-rs/Cargo.toml`:
- Tool: clang-format, config at `classic-cli/.clang-format` and `classic-gui/.clang-format`
- `ColumnLimit: 120`, `IndentWidth: 4`, `UseTab: Never`
- Braces: K&R / Attach style (same line for everything)
- Pointer alignment: `Left` (`int* p`)
- Standard: C++20, MSVC-targeted
- Compiler: TypeScript 5.8+, `strict: true` in `tsconfig.json`
- No eslint or prettier config detected; strict TypeScript is the primary linting tool
- Target: `ES2022`, `module: CommonJS`
- Formatter: `ruff format` (from `CLAUDE.md` commands)
- No `ruff.toml` or `pyproject.toml` detected at repo root; ruff uses defaults
- Type hints: `from __future__ import annotations` used in test files; type annotations on all public functions
## Import Organization
## Error Handling
- Use `thiserror` for typed, domain-specific errors
- Define a dedicated `error.rs` in each crate exposing a typed enum
- Provide a `Result<T>` type alias in each crate: `pub type Result<T> = std::result::Result<T, CrateError>`
- Use `anyhow::Result` and `.context()` in higher-level integration code and config loading
- `#[from]` attribute on error variants for `std::io::Error` and `tokio::task::JoinError` conversions
- Never use bare `unwrap()` in production code; use `.expect("descriptive message")` only in tests
#[derive(Debug, Error)]
- Convert Rust errors to NAPI errors via helper functions (e.g., `config_error_to_napi_err`)
- NAPI errors include a `code` field matching the variant name (e.g., `"InvalidArg"`, `"ParseError"`)
- Tests verify both `error.message` and `error.code`
- Expose typed Python exception classes (e.g., `classic_config.RustConfigParseError`, `classic_config.RustConfigIOError`)
- Tests use `pytest.raises(ExceptionClass)` with message inspection
- CLI11 parse errors call `std::exit(app.exit(e))` directly
- Result propagation via return values; no exceptions in bridge-facing code
## Logging
- Internal business-logic crates use `log::debug!` extensively for tracing data extraction
- `log::warn!` used for missing or unexpected YAML keys
- `tracing` crate is a workspace dependency but primary usage in business logic is `log` macros
- Production code does not use `println!`/`eprintln!` directly; CLI output goes through the report system
## Comments
- Module-level: `//!` doc comments at the top of every `lib.rs` and key modules
- Required sections for modules: description, architecture note, and `# Examples` with runnable code
- Public items: `///` doc comments with `# Arguments`, `# Returns`, `# Examples` as needed
- Private items: `//` comments where behavior is non-obvious
- `///` doc-style comments for public functions in headers (Doxygen-adjacent)
- `//` for inline implementation notes
- TSDoc `@param`, `@throws` comments on NAPI-exposed Rust functions (in `.rs` source, not `.ts`)
- Minimal comments in TypeScript CLI source; self-documenting code preferred
## Function Design
- Rust: prefer `&str` over `String` for input, `impl Into<String>` for builders
- Use `Option<&Path>` for optional path parameters
- Async functions use `async fn` throughout; no manual `Future` boxing in business logic
- Return `Result<T>` or `Option<T>` consistently; never panic on expected failure conditions
- Builder pattern used in `Message`: `Message::new(...).with_title(...).with_details(...)`
## Module Design
- `lib.rs` re-exports all public API items explicitly
- `pub use` is used to flatten module hierarchies at the crate boundary
- Internal helpers stay private (`fn` without `pub`)
- Single `index.js` / `index.d.ts` as the binding surface; all exports flow through it
- Test files import exclusively from `"../index.js"`, never from individual binding modules
- Each crate produces a top-level `classic_*` Python module
- A `pyi` stub file lives alongside each binding crate (e.g., `classic-config-py/classic_config.pyi`)
## NAPI-RS Specific Conventions (Node Bindings)
- All NAPI structs are annotated `#[napi]` or `#[napi(object)]`
- Constructors use `#[napi(constructor)]`, factory methods use `#[napi(factory)]`
- Private state in NAPI structs uses an `inner:` field holding the core Rust type
- The `Js` prefix is used for NAPI-facing types that wrap core types (e.g., `JsFileIO`, `JsDatabasePool`)
- App directory must be initialized via `Once` guard to resolve paths correctly in Node/Bun context
## PyO3 Specific Conventions (Python Bindings)
- `#[getter]` attribute exposes Python properties with `snake_case` names
- `#[pyo3(name = "method_name")]` overrides Rust name when Python convention differs
- `#[allow(non_snake_case)]` used selectively where YAML keys require uppercase names
- Python binding crates are excluded from the standard Rust test run (require Python DLL at runtime)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- All business logic lives in pure Rust `*-core` crates under `ClassicLib-rs/business-logic/`
- A single shared Tokio runtime (the ONE RUNTIME RULE) is process-wide and owned by `classic-shared-core`
- C++, Python, and Node.js surfaces are thin adapters that delegate entirely to `-core` crates
- Native C++ frontends (GUI and CLI) access Rust through CXX FFI via `classic-cpp-bridge`
- No business logic is re-implemented in binding layers; all meaningful behavior lives in Rust
## Layers
- Purpose: Process-wide shared runtime, error types, path helpers, performance primitives, string utilities
- Location: `ClassicLib-rs/foundation/`
- Contains: `classic-shared-core` (Rust runtime via `LazyLock<Runtime>`, errors, path/string helpers), `classic-shared-py` (PyO3 utility adapters)
- Depends on: nothing within this codebase
- Used by: every `-core` crate and every binding crate
- Purpose: All domain logic — crash log parsing, config loading, file I/O, game scan, version detection, database, update, messaging
- Location: `ClassicLib-rs/business-logic/`
- Contains: 16 pure Rust crates after the v9.1.0 consolidation work. ``yaml-core`` was absorbed into `classic-settings-core` in Phase 1, `classic-crashgen-settings-core` was absorbed into `classic-config-core` in Phase 2, and Phase 3 redistributed the retired constants crate across version-registry, settings, and shared.
- Depends on: `foundation/classic-shared-core`
- Used by: `classic-cpp-bridge`, all `-py` binding crates, `classic-node`, `classic-tui`
- Purpose: Expose Rust APIs to C++ via CXX FFI as a static library
- Location: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`
- Contains: 14 bridge modules mirroring the `-core` domains (`scanner`, `game`, `files`, `config`, `database`, `scangame`, `settings` (renamed from `yaml` in v9.1.0 Phase 1 and expanded with the D-09 settings-core cache ops and validators), `registry`, `runtime`, `message`, `perf`, `path`, `update`, `markdown`); CXX-generated headers in `include/classic_cxx_bridge/`
- Depends on: all business-logic `-core` crates
- Used by: `classic-cli/`, `classic-gui/`
- Note: Windows-only (`#[cfg(windows)]` on all modules)
- Purpose: Expose all `-core` APIs to Python via PyO3
- Location: `ClassicLib-rs/python-bindings/`
- Contains: 17 crates mirroring the active Rust API owners (including `classic-shared-py`). The former `classic-yaml-py` was deleted in v9.1.0 Phase 1, and Phase 3 retired `classic-constants-py` by redistributing its wrappers into `classic-version-registry-py`, `classic-settings-py`, and `classic-shared-py`.
- Depends on: corresponding `-core` crates + `foundation/classic-shared-py`
- Used by: Python consumers; parity checked against Node bindings
- Purpose: Expose all `-core` APIs to JavaScript/TypeScript via NAPI-RS
- Location: `ClassicLib-rs/node-bindings/classic-node/`
- Contains: Single crate with 20 modules, organized in 5 implementation waves
- Depends on: all business-logic `-core` crates
- Used by: Node/Bun consumers; CLI wrapper at `ClassicLib-rs/node-bindings/classic-node/cli/`
- Purpose: Command-line crash log scanner
- Location: `classic-cli/`
- Contains: `main.cpp`, `scanner.cpp`, `cli_args.cpp`, `progress.cpp`, `report_writer.cpp`, `thread_pool.cpp`
- Depends on: `classic-cpp-bridge` (via CXX headers in `classic_cxx_bridge/`)
- Used by: end users via command line
- Purpose: Desktop GUI application
- Location: `classic-gui/`
- Contains: `app/` (dialogs, main window), `controllers/` (scan, results, backup, game files), `workers/` (QObject thread workers), `core/` (bridge, signal hub, thread manager), `widgets/` (custom Qt widgets)
- Depends on: `classic-cpp-bridge` (via CXX headers)
- Used by: end users via Qt desktop GUI
- Purpose: Terminal UI application (Ratatui-based)
- Location: `ClassicLib-rs/ui-applications/classic-tui/`
- Contains: `app.rs`, `state.rs`, `tabs/` (main, results, backup, articles), `widgets/`, `ui.rs`, `theme.rs`
- Depends on: `-core` crates directly (no bridge needed)
- Used by: terminal users
## Data Flow
- `classic-registry-core` provides a process-wide typed singleton `DashMap` (keyed `&'static str`) for cross-crate state sharing (game selection, path, GUI mode flag, XSE status)
- All async state uses the single Tokio runtime from `classic-shared-core::get_runtime()`
- Settings are cached by caller-chosen string keys in `classic-settings-core`
## Key Abstractions
- Purpose: Coordinates the full crash log analysis pipeline
- Examples: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
- Pattern: Takes `AnalysisConfig` + optional `DatabasePool`, produces `AnalysisResult`; progress emitted via `ScanProgressPhase` enum
- Purpose: Coordinates concurrent game-installation integrity checks
- Examples: `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs`
- Pattern: Spawns `tokio::JoinSet` sub-tasks; individual task failure does not abort entire scan
- Purpose: Loaded, merged YAML configuration for one game variant
- Examples: `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`
- Pattern: Consumed as `Arc<YamlDataCore>` throughout analysis crates; structured ordered sequences (`IndexMap`) for `Mods_FREQ` and `Mods_SOLU`
- Purpose: Single source of truth for Fallout 4 game version metadata (OG/NG/AE/VR)
- Examples: `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs`
- Pattern: Thread-safe `OnceLock` singleton; all version queries go through `get_version_registry()`
- Purpose: Process-wide typed singleton store for cross-crate runtime state
- Examples: `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs`
- Pattern: `DashMap<&'static str, Arc<dyn Any + Send + Sync>>`; predefined key constants in `Keys` struct
- Purpose: Async SQLite connection pool for FormID lookups
- Examples: `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
- Pattern: sqlx pool in WAL mode; TTL-based LRU query cache; batch query optimization
- Purpose: Wrap Rust async APIs as synchronous C++ functions using `block_on()`
- Examples: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `game.rs`, `files.rs`
- Pattern: Opaque Rust types + shared DTOs; all async calls use `classic_shared_core::get_runtime().block_on()`
## Entry Points
- Location: `classic-gui/src/main.cpp`
- Triggers: Qt application startup
- Responsibilities: Initialize Rust runtime via `classic::runtime::init_runtime()`, load version from `CLASSIC Main.yaml`, set registry game/mode, create `MainWindow`
- Location: `classic-cli/src/main.cpp`
- Triggers: Command-line invocation
- Responsibilities: Parse CLI args, call `run_scan(args)` which drives the CXX bridge scan pipeline
- Location: `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`
- Triggers: Binary execution
- Responsibilities: Initialize logging, touch shared runtime, start Ratatui terminal loop via `App::new().run()`
- Location: `ClassicLib-rs/node-bindings/classic-node/cli/main.ts`
- Triggers: `bun`/`node` invocation
- Responsibilities: Parse args, call NAPI-RS scan functions, write results
## Error Handling
- Each `-core` crate defines its own `Error` enum (e.g., `ScanLogError`, `FileIOError`, `VersionRegistryError`, `DatabaseError`) using `thiserror`
- CXX bridge converts Rust errors to CXX exceptions caught by C++ `catch (const rust::Error& e)`
- PyO3 bindings convert Rust errors to Python exceptions via `classic-shared-py`'s error-conversion helpers
- NAPI-RS bindings convert via `to_napi_err()` helpers in each binding module
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
