# Architecture

**Analysis Date:** 2026-01-29

## Pattern Overview

**Overall:** Hybrid layered architecture with synchronous GUI (PySide6/Qt), asynchronous CLI/TUI, and performance-critical Rust business logic.

**Key Characteristics:**
- **Separation of concerns**: UI layer (GUI/CLI/TUI) → Business logic (scanning, analysis) → Data access (files, databases)
- **Async-first for CLI/TUI**: Native asyncio throughout, `asyncio.run()` at entry point only
- **GUI-sync with AsyncBridge**: Qt requires synchronous execution; AsyncBridge bridges async code for worker threads
- **Rust acceleration**: Pure Rust business logic (`-core` crates) with PyO3 bindings (`-py` crates)
- **Automatic fallback**: All Rust components have Python equivalents; detection/factory pattern selects best available

## Layers

**Presentation Layer (GUI):**
- Purpose: Qt-based desktop interface with tabs (Main, File Backup, Articles, Results)
- Location: `ClassicLib/Interface/`
- Contains: Controllers, widgets, dialogs, thread workers, signal routing
- Depends on: Business logic, messaging, settings
- Used by: MainWindow, QApplication

**Presentation Layer (CLI/TUI):**
- Purpose: Command-line and text user interface for server/headless operation
- Location: CLASSIC_ScanLogs.py (CLI entry point), `ClassicLib/TUI/` (TUI implementation)
- Contains: Argument parsing, async execution, native async operations
- Depends on: Business logic, messaging
- Used by: Direct invocation from terminal

**Business Logic Layer:**
- Purpose: Core scanning, analysis, and orchestration logic
- Location: `ClassicLib/scanning/`, `ClassicLib/support/`, `ClassicLib/integration/`
- Contains: ScanLogsExecutor, OrchestratorCore, FormIDAnalyzer, SettingsScanner, etc.
- Depends on: Data access, configuration, messaging
- Used by: CLI, GUI workers, tests

**Data Access Layer:**
- Purpose: File I/O, database operations, YAML configuration
- Location: `ClassicLib/io/` (files, database, yaml)
- Contains: AsyncDatabasePool, FileIOCore, YamlSettingsCache, async file operations
- Depends on: Rust acceleration modules (optional)
- Used by: Business logic, application startup

**Core Infrastructure:**
- Purpose: Shared utilities, messaging, registry, async bridging
- Location: `ClassicLib/core/`, `ClassicLib/messaging/`
- Contains: AsyncBridge, GlobalRegistry, MessageHandler, constants, performance monitoring
- Depends on: Nothing (foundation)
- Used by: All layers

**Rust Acceleration Layer:**
- Purpose: 10-150x performance improvements for CPU-intensive operations
- Location: `rust/foundation/` (shared), `rust/business-logic/` (pure Rust), `rust/python-bindings/` (PyO3 adapters)
- Contains: YAML parsing, database operations, form ID analysis, registry, message routing
- Depends on: Nothing (standard Rust libraries)
- Used by: Factory pattern; automatic selection if available, Python fallback if not

## Data Flow

**Crash Log Scanning (CLI/TUI):**

1. User runs CLASSIC_ScanLogs.py with optional arguments
2. SetupCoordinator.initialize_application() executes startup checks (paths, integrity, etc.)
3. parse_arguments() extracts CLI flags
4. create_config_from_args_async() builds ScanConfig with settings
5. asyncio.run(run_scan(args)) enters async context
6. ScanLogsExecutor(config) loads crash log file list
7. OrchestratorCore (via factory selection) scans logs in parallel
8. Individual analyzers (FormIDAnalyzer, SettingsScanner, etc.) process each log
9. ReportGenerator composes findings into markdown
10. Reports written to file, database updated
11. Summary displayed, database connections closed, exit

**GUI Scanning (Qt Event Loop):**

1. MainWindow.__init__() creates controllers via composition pattern
2. ScanController registers callback with user interaction
3. User clicks "Scan Crash Logs" button
4. ScanController dispatches to ThreadManager (QThread pool)
5. Worker thread uses AsyncBridge.run_async() to run async business logic
6. ScanLogsExecutor.execute_scan() runs in event loop (not blocking UI)
7. Progress signals emitted via SignalHub → Qt slots → UI updates
8. ResultsViewerController displays report
9. On close, ThreadManager stops all threads, database pools cleaned up

**Settings/Configuration:**

1. At startup, SetupCoordinator calls yaml_settings_async() to batch-load config
2. YAML cache (Python or Rust) checked first, fallback to file read
3. Settings available globally via classic_settings() (sync wrapper)
4. Changes persisted via yaml_settings() immediately
5. All paths are pathlib.Path, never strings

**State Management:**

- **GlobalRegistry** (`classic_registry` or Python fallback): Singleton access to application state (paths, version, game info)
- **MessageHandler**: Central routing for all output (console, GUI progress, logs)
- **YamlSettingsCache**: Lazy-loaded settings with batch read optimization
- **AsyncBridge**: Singleton instance per thread; manages event loop lifecycle for GUI workers

## Key Abstractions

**ScanLogsExecutor:**
- Purpose: Entry point for crash log scanning, abstracts CLI/GUI differences
- Examples: `ClassicLib/scanning/logs/executor.py`
- Pattern: Initialization with config; single method `execute_scan()` returns ScanResult

**OrchestratorCore:**
- Purpose: Parallel orchestration of crash log scanning with resource coordination
- Examples: `ClassicLib/scanning/logs/orchestrator_core.py`
- Pattern: Manages worker pool, batching, error handling; coordinate with individual analyzers

**Factory Pattern (Integration):**
- Purpose: Select Rust accelerated components when available, fall back to Python
- Examples: `ClassicLib/integration/factory/`, `get_formid_analyzer()`, `get_suspect_scanner()`
- Pattern: detect_rust_components() checks availability → factory returns best option

**Controller Pattern (GUI):**
- Purpose: Separate UI construction from logic; enable composition over inheritance
- Examples: ScanController, BackupManager, FolderManager, ResultsViewerController
- Pattern: Each controller owns one feature; receives FeatureContext for shared dependencies

**FeatureContext (Dependency Injection):**
- Purpose: Single container for GUI dependencies, passed to all controllers
- Examples: `ClassicLib/Interface/shared/context.py`
- Pattern: Eliminates circular imports, explicit dependencies, testable composition

**SignalHub (Qt Event Bus):**
- Purpose: Decouples controllers via Qt signals; enables cross-feature communication
- Examples: `ClassicLib/Interface/shared/signal_hub.py`
- Pattern: Controllers emit signals → other controllers connect slots; no direct references

**AsyncBridge (Sync/Async Bridge):**
- Purpose: Bridge async code into synchronous Qt contexts without blocking
- Examples: `ClassicLib/core/async_bridge.py`, used in GUI worker threads
- Pattern: Singleton per thread; creates hidden event loop for async operations in sync context

## Entry Points

**CLASSIC_Interface.py (GUI):**
- Location: `CLASSIC_Interface.py` root
- Triggers: User double-clicks executable or runs `uv run python CLASSIC_Interface.py`
- Responsibilities:
  1. Create QApplication
  2. SetupCoordinator.initialize_application(is_gui=True) - startup checks
  3. Instantiate MainWindow with all controllers
  4. Show window and run Qt event loop
  5. Cleanup on close (threads, database pools)

**CLASSIC_ScanLogs.py (CLI):**
- Location: `CLASSIC_ScanLogs.py` root
- Triggers: User runs `uv run python CLASSIC_ScanLogs.py [args]` or in CI/batch
- Responsibilities:
  1. Configure Windows console UTF-8 (if Windows)
  2. Parse command-line arguments
  3. SetupCoordinator.initialize_application(is_gui=False) - startup checks
  4. Call asyncio.run(run_scan(args)) - run async scan in event loop
  5. Cleanup and exit

**TUI (Future):**
- Location: `ClassicLib/TUI/` (Ratatui-based)
- Pattern: Similar to CLI but interactive; uses native async throughout

## Error Handling

**Strategy:** Try Rust first, fall back to Python; never fail silently.

**Patterns:**

**Factory Fallback:**
```python
# In ClassicLib/integration/factory/
try:
    return classic_scanlog.FormIDAnalyzer(...)  # Rust attempt
except ImportError:
    return FormIDAnalyzer(...)  # Python fallback
```

**Database/File I/O:**
- AsyncDatabasePool handles connection errors gracefully
- FileIOCore includes retry logic for transient filesystem errors
- cleanup_database_pools() on exit ensures WAL files checkpointed

**Message Handler:**
- Tries to route to GUI (if available) → CLI → file log
- Never raises exceptions; always outputs somewhere
- msg_error(), msg_warning() distinguish severity

**Scanning Exceptions:**
- Individual analyzer failures logged but don't stop scan
- Report records which mods/plugins failed analysis
- ScanResult includes failure counts and details

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Configuration: `ClassicLib/core/logger.py` sets up root logger
- Output: File (logs/) + console + GUI progress context
- Levels: DEBUG (enabled by config), INFO, WARNING, ERROR
- No print() allowed; use msg_info(), msg_debug(), etc.

**Validation:**
- Paths: pathlib.Path + optional Rust validator
- YAML: Type-safe with T TypeVar; batch loading for startup efficiency
- Settings: Lazy load on first access; cache subsequent accesses
- Config: ScanConfig validates bounds on __post_init__ (0-32 concurrent workers)

**Authentication:**
- Game path detection: Scans registry/filesystem for Bethesda games
- XSE/ENB integrity: Hash verification against known good versions
- No user auth; file-based (game install must be readable)

**Concurrency:**
- AsyncBridge: Single event loop per thread, reused for efficiency
- OrchestratorCore: Tokio runtime (Rust) or asyncio (Python) manages workers
- Database pool: Connection pooling prevents SQLite lock contention
- Settings cache: Lock-free caching (Rust version) or RWLock (Python)

**Performance Monitoring:**
- TimedBlock context manager for function timing
- timed_operation() decorator for method timing
- classic_perf (Rust) provides sub-microsecond precision
- Metrics logged at INFO level if enabled
