# Architecture

**Analysis Date:** 2026-04-04

## Pattern Overview

**Overall:** Layered Rust core with thin multi-language adapter surfaces

**Key Characteristics:**
- All business logic lives in pure Rust `*-core` crates under `ClassicLib-rs/business-logic/`
- A single shared Tokio runtime (the ONE RUNTIME RULE) is process-wide and owned by `classic-shared-core`
- C++, Python, and Node.js surfaces are thin adapters that delegate entirely to `-core` crates
- Native C++ frontends (GUI and CLI) access Rust through CXX FFI via `classic-cpp-bridge`
- No business logic is re-implemented in binding layers; all meaningful behavior lives in Rust

## Layers

**Foundation:**
- Purpose: Process-wide shared runtime, error types, path helpers, performance primitives, string utilities
- Location: `ClassicLib-rs/foundation/`
- Contains: `classic-shared-core` (Rust runtime via `LazyLock<Runtime>`, errors, path/string helpers), `classic-shared-py` (PyO3 utility adapters)
- Depends on: nothing within this codebase
- Used by: every `-core` crate and every binding crate

**Business Logic (-core crates):**
- Purpose: All domain logic — crash log parsing, config loading, file I/O, game scan, version detection, database, update, messaging
- Location: `ClassicLib-rs/business-logic/`
- Contains: 17 pure Rust crates (see Crate Inventory below); no PyO3 dependencies. **v9.1.0 Phase 1 merge:** ``yaml-core`` was absorbed into `classic-settings-core` (19 -> 18). **v9.1.0 Phase 2 merge:** the former `classic-crashgen-settings-core` crate was absorbed into `classic-config-core` (rule model now at `classic_config_core::crashgen_rules::*`), 18 -> 17.
- Depends on: `foundation/classic-shared-core`
- Used by: `classic-cpp-bridge`, all `-py` binding crates, `classic-node`, `classic-tui`

**C++ Bridge:**
- Purpose: Expose Rust APIs to C++ via CXX FFI as a static library
- Location: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`
- Contains: 14 bridge modules mirroring the `-core` domains (`scanner`, `game`, `files`, `config`, `database`, `scangame`, `settings` (renamed from `yaml` in v9.1.0 Phase 1 and expanded with the D-09 settings-core cache ops and validators), `registry`, `runtime`, `message`, `perf`, `path`, `update`, `markdown`); CXX-generated headers in `include/classic_cxx_bridge/`
- Depends on: all business-logic `-core` crates
- Used by: `classic-cli/`, `classic-gui/`
- Note: Windows-only (`#[cfg(windows)]` on all modules)

**Python Bindings (-py crates):**
- Purpose: Expose all `-core` APIs to Python via PyO3
- Location: `ClassicLib-rs/python-bindings/`
- Contains: 17 crates mirroring each business-logic crate (e.g., `classic-scanlog-py`, `classic-config-py`). The former `classic-yaml-py` was deleted in v9.1.0 Phase 1 and folded into `classic-settings-py`. The former `classic-crashgen-settings-py` equivalent never existed as a distinct Python crate (its surface was always embedded in `classic-config-py`, `classic-scanlog-py`, and `classic-scangame-py`); after Phase 2's core-crate merge those wrappers now consume the rule model from `classic_config_core::crashgen_rules::*`.
- Depends on: corresponding `-core` crates + `foundation/classic-shared-py`
- Used by: Python consumers; parity checked against Node bindings

**Node.js Bindings:**
- Purpose: Expose all `-core` APIs to JavaScript/TypeScript via NAPI-RS
- Location: `ClassicLib-rs/node-bindings/classic-node/`
- Contains: Single crate with 20 modules, organized in 5 implementation waves
- Depends on: all business-logic `-core` crates
- Used by: Node/Bun consumers; CLI wrapper at `ClassicLib-rs/node-bindings/classic-node/cli/`

**C++ CLI Frontend:**
- Purpose: Command-line crash log scanner
- Location: `classic-cli/`
- Contains: `main.cpp`, `scanner.cpp`, `cli_args.cpp`, `progress.cpp`, `report_writer.cpp`, `thread_pool.cpp`
- Depends on: `classic-cpp-bridge` (via CXX headers in `classic_cxx_bridge/`)
- Used by: end users via command line

**C++ Qt GUI Frontend:**
- Purpose: Desktop GUI application
- Location: `classic-gui/`
- Contains: `app/` (dialogs, main window), `controllers/` (scan, results, backup, game files), `workers/` (QObject thread workers), `core/` (bridge, signal hub, thread manager), `widgets/` (custom Qt widgets)
- Depends on: `classic-cpp-bridge` (via CXX headers)
- Used by: end users via Qt desktop GUI

**Rust TUI:**
- Purpose: Terminal UI application (Ratatui-based)
- Location: `ClassicLib-rs/ui-applications/classic-tui/`
- Contains: `app.rs`, `state.rs`, `tabs/` (main, results, backup, articles), `widgets/`, `ui.rs`, `theme.rs`
- Depends on: `-core` crates directly (no bridge needed)
- Used by: terminal users

## Data Flow

**Crash Log Scan (primary feature):**

1. C++ GUI or CLI collects log file paths and scan settings
2. `ScanController` (GUI) or `run_scan()` (CLI) calls into `classic-cpp-bridge`'s `scanner` module
3. Bridge's `Orchestrator` wraps `classic_scanlog_core::OrchestratorCore`; async execution uses `get_runtime().block_on()`
4. `OrchestratorCore` loads `AnalysisConfig` from YAML via `classic_config_core::YamlDataCore`
5. Analysis pipeline: `LogParser` → `FormIDAnalyzerCore` → `SuspectScanner` → `ModDetector` → `PluginAnalyzer` → `ReportGenerator`
6. Optional `DatabasePool` (`classic-database-core`) performs async SQLite FormID lookups via sqlx
7. Progress events (`BatchProgressEvent`) flow back to C++ via `ScanBatchProgressCallback` virtual interface
8. GUI `ScanWorker` emits Qt signals → `scancontroller` → `MainWindow` / `BatchProgressModel`
9. Final `AnalysisResult` report lines written to disk

**Game Setup Validation:**

1. GUI or CLI requests a game setup check
2. Bridge `scangame` module calls `classic_scangame_core::OrchestratorCore`
3. Orchestrator runs concurrent sub-checks via `tokio::JoinSet`: BA2 archives, ENB, INI config, loose files, XSE, Wrye Bash
4. Results collected into `IssueMap` (BTreeMap<String, BTreeSet<String>>) and returned

**Configuration Loading:**

1. Any consumer calls `classic_config_core::YamlDataCore::load()`
2. `YamlDataCore` reads from `CLASSIC Data/databases/CLASSIC Main.yaml` and game-specific YAML
3. `classic-settings-core` handles parsing and caching (mtime-aware `quick_cache` file cache, absorbed from the former ``yaml-core`` in v9.1.0 Phase 1)
4. `classic-version-registry-core` provides game version metadata as single source of truth
5. Config is passed down into scan and analysis functions as `AnalysisConfig` or `ClassicConfig`

**State Management:**
- `classic-registry-core` provides a process-wide typed singleton `DashMap` (keyed `&'static str`) for cross-crate state sharing (game selection, path, GUI mode flag, XSE status)
- All async state uses the single Tokio runtime from `classic-shared-core::get_runtime()`
- Settings are cached by caller-chosen string keys in `classic-settings-core`

## Key Abstractions

**OrchestratorCore (crash log):**
- Purpose: Coordinates the full crash log analysis pipeline
- Examples: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
- Pattern: Takes `AnalysisConfig` + optional `DatabasePool`, produces `AnalysisResult`; progress emitted via `ScanProgressPhase` enum

**OrchestratorCore (game scan):**
- Purpose: Coordinates concurrent game-installation integrity checks
- Examples: `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs`
- Pattern: Spawns `tokio::JoinSet` sub-tasks; individual task failure does not abort entire scan

**YamlDataCore:**
- Purpose: Loaded, merged YAML configuration for one game variant
- Examples: `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`
- Pattern: Consumed as `Arc<YamlDataCore>` throughout analysis crates; structured ordered sequences (`IndexMap`) for `Mods_FREQ` and `Mods_SOLU`

**VersionRegistry:**
- Purpose: Single source of truth for Fallout 4 game version metadata (OG/NG/AE/VR)
- Examples: `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs`
- Pattern: Thread-safe `OnceLock` singleton; all version queries go through `get_version_registry()`

**GlobalRegistry:**
- Purpose: Process-wide typed singleton store for cross-crate runtime state
- Examples: `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs`
- Pattern: `DashMap<&'static str, Arc<dyn Any + Send + Sync>>`; predefined key constants in `Keys` struct

**DatabasePool:**
- Purpose: Async SQLite connection pool for FormID lookups
- Examples: `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
- Pattern: sqlx pool in WAL mode; TTL-based LRU query cache; batch query optimization

**CXX FFI Bridge Modules:**
- Purpose: Wrap Rust async APIs as synchronous C++ functions using `block_on()`
- Examples: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `game.rs`, `files.rs`
- Pattern: Opaque Rust types + shared DTOs; all async calls use `classic_shared_core::get_runtime().block_on()`

## Entry Points

**C++ GUI:**
- Location: `classic-gui/src/main.cpp`
- Triggers: Qt application startup
- Responsibilities: Initialize Rust runtime via `classic::runtime::init_runtime()`, load version from `CLASSIC Main.yaml`, set registry game/mode, create `MainWindow`

**C++ CLI:**
- Location: `classic-cli/src/main.cpp`
- Triggers: Command-line invocation
- Responsibilities: Parse CLI args, call `run_scan(args)` which drives the CXX bridge scan pipeline

**Rust TUI:**
- Location: `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`
- Triggers: Binary execution
- Responsibilities: Initialize logging, touch shared runtime, start Ratatui terminal loop via `App::new().run()`

**Node.js CLI:**
- Location: `ClassicLib-rs/node-bindings/classic-node/cli/main.ts`
- Triggers: `bun`/`node` invocation
- Responsibilities: Parse args, call NAPI-RS scan functions, write results

## Error Handling

**Strategy:** Typed errors per crate using `thiserror`; propagation via `Result<T, E>`; `anyhow` used for cross-boundary aggregation where needed

**Patterns:**
- Each `-core` crate defines its own `Error` enum (e.g., `ScanLogError`, `FileIOError`, `VersionRegistryError`, `DatabaseError`) using `thiserror`
- CXX bridge converts Rust errors to CXX exceptions caught by C++ `catch (const rust::Error& e)`
- PyO3 bindings convert Rust errors to Python exceptions via `classic-shared-py`'s error-conversion helpers
- NAPI-RS bindings convert via `to_napi_err()` helpers in each binding module

## Cross-Cutting Concerns

**Logging:** `tracing` crate with `tracing-subscriber`; `classic-message-core` provides structured `Message` DTOs routed by `MessageTarget` (GUI / CLI / log-only); C++ bridge exposes `classic::message::init_logging()` and startup log helpers

**Validation:** Input validation lives in respective `-core` crates (e.g., `classic-path-core::validator`, `classic-settings-core::validators`); game version validation through `VersionRegistry::match_version()`

**Authentication:** Not applicable — no user authentication; Windows registry access for game path detection in `classic-path-core`

**Performance Monitoring:** `classic-perf-core` provides process-wide `DashMap`-backed timing buckets; scoped RAII timer via `start_timer()`; summary statistics (count, total, avg, min, max)

**Parity Enforcement:** Python and Node binding surfaces are tracked against Rust core via automated parity reports in `ClassicLib-rs/python-bindings/parity-artifacts/` and `ClassicLib-rs/node-bindings/classic-node/__test__/`

---

*Architecture analysis: 2026-04-04*
