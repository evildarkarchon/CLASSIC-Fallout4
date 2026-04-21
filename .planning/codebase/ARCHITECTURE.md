# Architecture

**Analysis Date:** 2026-04-14

## Pattern Overview

**Overall:** Native frontend + thin bridge + repo-root Rust workspace.

**Key Characteristics:**
- Keep shared product behavior in Rust crates under `business-logic/` and `foundation/`.
- Keep native entrypoints in `classic-cli/` and `classic-gui/` thin and integration-focused.
- Cross-language boundaries go through dedicated adapter crates in `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, and `python-bindings/`.

## Layers

**Runtime Assets & Config Layer:**
- Purpose: Provide the YAML, databases, graphics, help content, and portable runtime files consumed by every frontend.
- Location: `CLASSIC Data/`, root-level `CLASSIC Settings.yaml`, root-level `CLASSIC Ignore.yaml`.
- Contains: `CLASSIC Data/databases/`, `CLASSIC Data/graphics/`, `CLASSIC Data/Help/`, `CLASSIC Data/games/`.
- Depends on: File-system access from `classic-cli/src/scanner.cpp`, `classic-gui/src/main.cpp`, `classic-gui/src/app/mainwindow.cpp`, and Rust loaders exposed through `business-logic/classic-settings-core/src/lib.rs` and `business-logic/classic-config-core/src/lib.rs`.
- Used by: `classic-cli/src/main.cpp`, `classic-gui/src/main.cpp`, `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, and maintained bindings.

**Native Frontend Layer:**
- Purpose: Own user interaction, process startup, threading, widget composition, and report presentation.
- Location: `classic-cli/src/` and `classic-gui/src/`.
- Contains: CLI argument parsing and progress rendering in `classic-cli/src/cli_args.cpp`, `classic-cli/src/progress.cpp`, `classic-cli/src/scanner.cpp`; Qt windows/controllers/workers/widgets in `classic-gui/src/app/`, `classic-gui/src/controllers/`, `classic-gui/src/workers/`, `classic-gui/src/widgets/`.
- Depends on: Generated CXX headers such as `classic_cxx_bridge/scanner.h`, `classic_cxx_bridge/settings.h`, `classic_cxx_bridge/runtime.h`, and local conversion helpers in `classic-gui/src/core/rust_qt_bridge.h`.
- Used by: End users through `classic-cli/src/main.cpp` and `classic-gui/src/main.cpp`.

**C++/Rust Bridge Layer:**
- Purpose: Translate between C++ types and Rust APIs while keeping Rust business logic callable from native frontends.
- Location: `cpp-bindings/classic-cpp-bridge/`.
- Contains: Bridge modules such as `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `src/settings.rs`, `src/files.rs`, `src/path.rs`, `src/version_registry.rs`, and generated headers/glue declared by `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`.
- Depends on: `foundation/classic-shared-core/` and the `business-logic/*-core` crates listed in `cpp-bindings/classic-cpp-bridge/Cargo.toml`.
- Used by: `classic-cli/` and `classic-gui/`.

**Rust Foundation Layer:**
- Purpose: Own process-wide runtime, shared errors, game identifiers, path helpers, performance helpers, and low-level common utilities.
- Location: `foundation/classic-shared-core/` and `foundation/classic-shared-py/`.
- Contains: Shared Tokio runtime and runtime configuration in `foundation/classic-shared-core/src/lib.rs`, plus shared types and helpers.
- Depends on: Workspace dependencies from `Cargo.toml`.
- Used by: Every Rust crate that needs the single runtime or shared foundational types.

**Rust Business-Logic Layer:**
- Purpose: Own the actual scanning, config, file, database, version, path, web, update, and setup workflows.
- Location: `business-logic/`.
- Contains: Domain crates such as `business-logic/classic-config-core/`, `classic-scanlog-core/`, `classic-file-io-core/`, `classic-database-core/`, `classic-scangame-core/`, `classic-version-registry-core/`, `classic-path-core/`, and `classic-update-core/`.
- Depends on: `foundation/classic-shared-core/` plus other focused `*-core` crates, as shown in `business-logic/classic-config-core/Cargo.toml` and `business-logic/classic-scanlog-core/Cargo.toml`.
- Used by: `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/*-py/`, and `ui-applications/classic-tui/`.

**Maintained Binding Layer:**
- Purpose: Expose Rust core behavior to Node/Bun and Python without reimplementing business rules.
- Location: `node-bindings/classic-node/` and `python-bindings/`.
- Contains: NAPI modules in `node-bindings/classic-node/src/` and per-domain PyO3 crates such as `python-bindings/classic-config-py/` and `python-bindings/classic-scanlog-py/`.
- Depends on: Same `*-core` crates consumed by the bridge, plus binding-specific packaging files like `node-bindings/classic-node/index.js` and `index.d.ts`.
- Used by: External integration consumers and parity/test tooling.

**Rust UI Layer:**
- Purpose: Provide a Rust-native terminal interface over the same shared core crates.
- Location: `ui-applications/classic-tui/`.
- Contains: TUI entrypoint in `ui-applications/classic-tui/src/main.rs`, app state in `src/app/`, `src/state/`, `src/tabs/`, and rendering helpers in `src/ui/` and `src/widgets/`.
- Depends on: `classic-shared-core`, `classic-scanlog-core`, `classic-config-core`, `classic-file-io-core`, `classic-path-core`, `classic-scangame-core`, `classic-update-core`, and `classic-version-registry-core` per `ui-applications/classic-tui/Cargo.toml`.
- Used by: The `classic-tui` binary defined in `ui-applications/classic-tui/Cargo.toml`.

## Data Flow

**CLI scan flow:**

1. `classic-cli/src/main.cpp` parses arguments and hands control to `run_scan()` in `classic-cli/src/scanner.cpp`.
2. `classic-cli/src/scanner.cpp` locates `CLASSIC Data/`, reads YAML through `classic::settings::*`, resolves logs with `classic::files::*`, and builds a scan config with `classic::scanner::build_full_scan_config()`.
3. `cpp-bindings/classic-cpp-bridge/src/scanner.rs` constructs `Orchestrator` and forwards work into `business-logic/classic-scanlog-core/src/orchestrator.rs` plus supporting config/file/database crates.
4. Results return through CXX into `classic-cli/src/scanner.cpp`, which writes `-AUTOSCAN.md` reports via `classic-cli/src/report_writer.cpp`.

**GUI scan flow:**

1. `classic-gui/src/main.cpp` initializes logging and the shared runtime, creates `MainWindow`, and registers GUI mode in `classic::registry::*`.
2. `classic-gui/src/app/mainwindow.cpp` delegates feature actions to controllers such as `classic-gui/src/controllers/scancontroller.cpp`.
3. `classic-gui/src/controllers/scancontroller.cpp` resolves inputs, creates `ScanWorker`, and starts a dedicated `QThread` through `classic-gui/src/core/threadmanager.cpp`.
4. `classic-gui/src/workers/scanworker.cpp` calls bridge APIs like `classic::scanner::orchestrator_process_logs_batch_with_progress()` and emits Qt signals back to the controller/UI.
5. The bridge streams progress events from `cpp-bindings/classic-cpp-bridge/src/scanner.rs` through `ScanBatchProgressCallback`, and the GUI updates progress models and result widgets.

**Binding flow:**

1. Public exports live in `node-bindings/classic-node/src/lib.rs` or the per-domain `python-bindings/*-py/src/lib.rs` files.
2. Binding modules convert language-native values into Rust values.
3. Binding modules delegate directly into `business-logic/*-core` crates and `foundation/classic-shared-core/src/lib.rs`.

**State Management:**
- Process-wide async state is centralized in the shared runtime returned by `foundation/classic-shared-core/src/lib.rs`.
- Process-wide mutable flags and mode data use the typed registry exposed from `business-logic/classic-registry-core/` and consumed in `classic-gui/src/main.cpp`.
- GUI feature state stays in Qt objects such as `MainWindow`, `ScanController`, `SignalHub`, `ThreadManager`, and worker instances under `classic-gui/src/`.
- Scan configuration state is rebuilt from YAML via `business-logic/classic-settings-core/` and `business-logic/classic-config-core/` rather than duplicated in C++.

## Key Abstractions

**Shared Tokio runtime:**
- Purpose: Ensure all async Rust work shares one runtime.
- Examples: `foundation/classic-shared-core/src/lib.rs`, `classic-gui/src/main.cpp`, `cpp-bindings/classic-cpp-bridge/src/lib.rs`.
- Pattern: Initialize once, then call `get_runtime()` or bridge wrappers that already use it.

**Scan orchestrator:**
- Purpose: Coordinate crash-log parsing, analysis, DB lookups, and report generation.
- Examples: `business-logic/classic-scanlog-core/src/lib.rs`, `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `classic-cli/src/scanner.cpp`, `classic-gui/src/workers/scanworker.cpp`.
- Pattern: Build config first, create orchestrator second, process one or many logs last.

**YAML operations + config model:**
- Purpose: Load settings and build typed config/data models from runtime YAML files.
- Examples: `business-logic/classic-settings-core/src/lib.rs`, `business-logic/classic-config-core/src/lib.rs`, `classic-gui/src/main.cpp`, `classic-gui/src/app/mainwindow.cpp`.
- Pattern: C++ calls bridge wrappers for file-backed YAML reads; Rust crates own parsing and validation.

**Qt controller/worker split:**
- Purpose: Keep long-running work off the GUI thread and isolate feature orchestration.
- Examples: `classic-gui/src/controllers/scancontroller.cpp`, `classic-gui/src/workers/scanworker.cpp`, `classic-gui/src/core/threadmanager.cpp`, `classic-gui/src/core/signalhub.cpp`.
- Pattern: Controller resolves inputs, worker runs Rust-backed tasks, signals return to widgets.

**Thin binding adapters:**
- Purpose: Preserve parity across C++, Node, and Python surfaces while keeping logic in Rust core crates.
- Examples: `cpp-bindings/classic-cpp-bridge/src/`, `node-bindings/classic-node/src/`, `python-bindings/classic-config-py/src/lib.rs`.
- Pattern: Translate types at the boundary, then delegate into `*-core` crates.

## Entry Points

**CLI executable:**
- Location: `classic-cli/src/main.cpp`
- Triggers: Running the `classic-cli` executable built by `classic-cli/CMakeLists.txt`.
- Responsibilities: Setup console behavior, parse args, print version/banner text, and start the scan pipeline.

**GUI executable:**
- Location: `classic-gui/src/main.cpp`
- Triggers: Running `CLASSIC.exe` built from `classic-gui/src/CMakeLists.txt`.
- Responsibilities: Start Qt, initialize Rust runtime/logging, locate runtime assets, load app version from YAML, register GUI mode, and show `MainWindow`.

**Rust TUI binary:**
- Location: `ui-applications/classic-tui/src/main.rs`
- Triggers: Running the `classic-tui` binary declared in `ui-applications/classic-tui/Cargo.toml`.
- Responsibilities: Initialize tracing, start terminal mode, construct `App`, and drive the ratatui event loop.

**Node addon surface:**
- Location: `node-bindings/classic-node/src/lib.rs`
- Triggers: Loading `node-bindings/classic-node/index.js` / compiled addon from Node or Bun.
- Responsibilities: Publish NAPI exports and route JS calls into Rust core crates.

**Python binding surfaces:**
- Location: `python-bindings/*-py/src/lib.rs`
- Triggers: Importing built PyO3 modules.
- Responsibilities: Publish per-domain Python wrappers over the same Rust business-logic crates.

## Error Handling

**Strategy:** Rust crates return typed errors or bridge-safe error DTOs; frontends convert them into process exit codes, dialogs, signals, or failed scan results.

**Patterns:**
- Catch `rust::Error` at the C++ boundary in `classic-cli/src/scanner.cpp`, `classic-gui/src/main.cpp`, and `classic-gui/src/controllers/scancontroller.cpp`.
- Convert recoverable scan failures into per-log result objects in `classic-gui/src/workers/scanworker.cpp` and `classic-cli/src/scanner.cpp` instead of aborting the whole batch.
- Keep Rust-side error definitions inside domain crates such as `business-logic/classic-scanlog-core/src/error.rs` and shared types under `foundation/classic-shared-core/src/errors.rs`.

## Cross-Cutting Concerns

**Logging:** Use shared Rust logging through `business-logic/classic-message-core/` and bridge calls such as `classic::message::init_logging()` in `classic-gui/src/main.cpp`; use `qDebug`/`qWarning` for Qt-local diagnostics in files like `classic-gui/src/workers/scanworker.cpp` and `classic-gui/src/core/threadmanager.cpp`.

**Validation:** Put config and input validation in Rust core and bridge APIs such as `classic::files::resolve_targeted_inputs()` and YAML/config loaders from `business-logic/classic-settings-core/` and `business-logic/classic-config-core/`.

**Authentication:** Not applicable in the local desktop/runtime architecture; no application auth layer is detected in `classic-cli/`, `classic-gui/`, or `business-logic/`.

---

*Architecture analysis: 2026-04-14*
