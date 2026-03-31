# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Multi-layer C++/Rust hybrid — C++ frontends delegate all domain logic to a Rust workspace via a CXX FFI bridge. Node and Python bindings expose the same Rust core for tooling and integration testing.

**Key Characteristics:**
- All business logic lives in Rust; C++, Python, and Node are thin wrappers
- Single shared Tokio runtime enforced by the ONE RUNTIME RULE (`classic-shared-core::get_runtime()`)
- Strict separation: `-core` crates are pure Rust (no PyO3/CXX), `-py` / node crates add binding glue
- Windows-only native surfaces (C++ bridge and frontends are `#[cfg(windows)]`); Rust core is cross-platform

## Layers

**Foundation Layer:**
- Purpose: Shared async runtime, error types, path utilities, string interning, performance timers
- Location: `ClassicLib-rs/foundation/classic-shared-core/`
- Contains: `get_runtime()`, `RuntimeConfig`, `ClassicError`/`ClassicResult`, `path_core`, `strings_core`, `performance_core`
- Depends on: Nothing (leaf dependency)
- Used by: Every other crate in the workspace

**Foundation Python Adapter:**
- Purpose: PyO3 utility layer — exception hierarchy macros, IndexMap conversions, shared Python type helpers
- Location: `ClassicLib-rs/foundation/classic-shared-py/`
- Contains: `error_convert`, `exceptions`, `indexmap_utils`, path/string/perf Python wrappers
- Depends on: `classic-shared-core`
- Used by: All `-py` binding crates

**Business Logic Layer (20 crates):**
- Purpose: Pure Rust domain logic — crash log scanning, config loading, game validation, YAML, database, file I/O, versioning, networking
- Location: `ClassicLib-rs/business-logic/`
- Contains: All `*-core` crates (see Key Abstractions section)
- Depends on: `classic-shared-core`, and each other according to the dependency chain described in `docs/api/README.md`
- Used by: C++ bridge, Node bindings, Python bindings, TUI

**C++ Bridge Layer:**
- Purpose: CXX FFI static library linking Rust business logic to C++ frontends
- Location: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`
- Contains: 16 bridge modules (`config`, `database`, `files`, `game`, `markdown`, `message`, `path`, `perf`, `registry`, `runtime`, `scangame`, `scanner`, `types`, `update`, `yaml`, opaque wrappers)
- Depends on: All business logic crates
- Used by: `classic-cli` and `classic-gui` via Corrosion + `corrosion_add_cxxbridge`

**Python Bindings Layer (19 crates):**
- Purpose: PyO3 adapters exposing Rust business logic to Python — maintained for tooling and parity testing
- Location: `ClassicLib-rs/python-bindings/`
- Contains: One `-py` crate per `-core` crate (e.g., `classic-scanlog-py`, `classic-config-py`)
- Depends on: Corresponding `-core` crates + `classic-shared-py`
- Used by: Python integration tests, parity gate tooling

**Node Bindings Layer (1 crate):**
- Purpose: NAPI-RS adapter exposing Rust business logic to Node.js and Bun — maintained for tooling and parity testing
- Location: `ClassicLib-rs/node-bindings/classic-node/`
- Contains: 20 bridge modules matching core crates, TypeScript declarations (`index.d.ts`)
- Depends on: All core business logic crates
- Used by: Bun/Node parity tests, tooling CLI (`dist/cli/main.js`)

**C++ Frontend Layer:**
- Purpose: User-facing CLI and Qt6 GUI applications; all orchestration calls delegate to the Rust bridge
- Location: `classic-cli/`, `classic-gui/`
- Contains: `main.cpp`, scanner pipeline, thread pool, Qt widgets/controllers/workers
- Depends on: `classic-cpp-bridge` (staticlib via Corrosion)
- Used by: End users

**Rust TUI Application:**
- Purpose: Terminal UI frontend written in pure Rust using Ratatui
- Location: `ClassicLib-rs/ui-applications/classic-tui/`
- Contains: `app.rs`, tabbed UI (`main_tab`, `results_tab`, `backup_tab`, `articles_tab`), state machine, Crossterm event loop
- Depends on: `classic-shared-core`, `classic-scanlog-core`, `classic-config-core`, `classic-file-io-core`, `classic-path-core`, `classic-scangame-core`, `classic-update-core`
- Used by: End users (alternative terminal frontend)

## Data Flow

**Crash Log Scan (GUI path):**

1. User triggers scan in `classic-gui/src/app/mainwindow.cpp` → `ScanController::startScan()`
2. `ScanController` creates a `ScanWorker` and offloads to `ThreadManager`
3. `ScanWorker::doScan()` calls `classic_cxx_bridge::scanner::*` CXX FFI functions
4. Bridge calls `classic_scanlog_core::OrchestratorCore` via `get_runtime().block_on()`
5. `OrchestratorCore` runs `LogParser` → `FormIDAnalyzerCore` → `SuspectScanner` → `ReportGenerator`
6. Progress callbacks (`BatchProgressEvent`) flow back through CXX FFI to `ScanProgressModel`
7. Qt signals deliver results to `ResultsController` and `MainWindow`

**Crash Log Scan (CLI path):**

1. `classic-cli/src/main.cpp` parses args with `CliArgs` and calls `run_scan()`
2. `scanner.cpp` discovers YAML data root, calls bridge to load config, creates orchestrator
3. Dispatches log paths to thread pool, collects `LogScanResult`s
4. `report_writer.cpp` writes `AUTOSCAN.md` files

**Config/YAML Loading:**

1. YAML files read from `CLASSIC Data/` directory at runtime
2. `classic-yaml-core::YamlOperations` parses and caches documents
3. `classic-settings-core` provides sync/async cache keyed by caller-chosen strings
4. `classic-config-core::YamlDataCore` builds typed config structs from merged YAML
5. `classic-version-registry-core` loads version/crashgen metadata from `CLASSIC Main.yaml`

**State Management:**
- Global singletons stored in `classic-registry-core` (DashMap-backed, `Arc<dyn Any + Send + Sync>`)
- Registry keys defined in `classic_registry_core::Keys`
- Version registry uses `OnceLock` singleton pattern (`get_version_registry()`)
- YAML document cache uses `DashMap` in `classic-yaml-core` and `classic-settings-core`

## Key Abstractions

**OrchestratorCore (`classic-scanlog-core`):**
- Purpose: Primary scan orchestration — coordinates parsing, analysis, report generation
- Examples: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
- Pattern: Takes `AnalysisConfig` + `DatabasePool`, processes one log per invocation, emits `AnalysisResult`

**YamlDataCore (`classic-config-core`):**
- Purpose: Typed access to all CLASSIC YAML configuration data (game settings, mod lists, rules)
- Examples: `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`
- Pattern: Loaded once and passed by `Arc` through analysis pipeline

**DatabasePool (`classic-database-core`):**
- Purpose: Async SQLite connection pool for FormID lookups
- Examples: `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
- Pattern: TTL-based caching, WAL mode, shared across batch scans

**CXX Bridge Modules (`classic-cpp-bridge`):**
- Purpose: Opaque type wrappers + thin sync wrappers around async Rust APIs using `block_on()`
- Examples: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` (Orchestrator), `config.rs` (FullScanConfig)
- Pattern: Opaque `struct` in CXX; C++ holds pointer; Rust calls `get_runtime().block_on(async_fn)`

**GameScanOrchestrator (`classic-scangame-core`):**
- Purpose: Game installation validation, archive/loose-file checks, setup workflow
- Examples: `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs`
- Pattern: Composed from BA2Scanner, IniValidator, XseChecker, ConfigDuplicateDetector

## Entry Points

**Qt GUI Application:**
- Location: `classic-gui/src/main.cpp`
- Triggers: Windows launch of GUI executable
- Responsibilities: Initialize Rust runtime, create QApplication, find CLASSIC Data dir, show MainWindow

**CLI Application:**
- Location: `classic-cli/src/main.cpp`
- Triggers: Command-line invocation
- Responsibilities: Parse args (CLI11), print banner, call `run_scan()`

**Rust TUI Application:**
- Location: `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`
- Triggers: Terminal invocation of `classic-tui` binary
- Responsibilities: Initialize shared runtime, set up Ratatui/Crossterm, run `App::run()`

**Python Bindings Entry:**
- Location: Each `ClassicLib-rs/python-bindings/classic-*-py/src/lib.rs` exposes a `#[pymodule]`
- Triggers: Python `import classic_*` after `maturin develop`/install

**Node Bindings Entry:**
- Location: `ClassicLib-rs/node-bindings/classic-node/src/lib.rs` (NAPI-RS `#[napi]` exports)
- Triggers: `require('@classic/node')` or `import` in Node/Bun

## Error Handling

**Strategy:** Typed errors per crate using `thiserror`, propagated as `Result<T, E>` through Rust layers; converted to CXX exceptions at the bridge boundary; PyO3 bindings convert to Python exceptions via `classic-shared-py`'s `ToPyErr`/`ResultExt` traits.

**Patterns:**
- Each `-core` crate defines its own `Error` type (e.g., `ScanLogError`, `FileIOError`, `DatabaseError`)
- Foundation provides `ClassicError` / `ClassicResult` as the common base
- CXX bridge propagates errors as `rust::Error` (CXX exception type) to C++
- Python bindings use `define_exceptions!` macro to create three-tier hierarchy (base → domain → specific)

## Cross-Cutting Concerns

**Logging:** `log` crate facade (0.4) with `env_logger` backend in Rust; `tracing`/`tracing-subscriber` used in TUI and some crates for structured spans; C++ uses `classic_cxx_bridge::message` to route messages through Rust logger

**Validation:** Input path validation in `classic-path-core::validator`; YAML schema validation at load time in `classic-config-core`; parity gate tooling in `tools/python_api_parity/` and `tools/node_api_parity/`

**Authentication:** Not applicable — application reads local files and accesses GitHub API anonymously for update checks

---

*Architecture analysis: 2026-03-30*
