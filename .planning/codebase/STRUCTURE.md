# Codebase Structure

**Analysis Date:** 2026-01-29

## Directory Layout

```
CLASSIC-Fallout4/
├── CLASSIC_Interface.py         # GUI entry point (Qt/PySide6)
├── CLASSIC_ScanLogs.py          # CLI entry point (async)
├── CLASSIC.spec                 # PyInstaller configuration
├── ClassicLib/                  # Python library (core application)
│   ├── __init__.py             # Public API, Rust component detection
│   ├── core/                   # Infrastructure (async bridge, registry, logging)
│   ├── integration/            # Rust/Python component selection (factory pattern)
│   ├── Interface/              # Qt GUI implementation
│   ├── io/                     # File I/O, database, YAML configuration
│   ├── messaging/              # Message routing, progress context
│   ├── scanning/               # Crash log and game file scanning logic
│   ├── support/                # Setup, integrity checks, backup, versioning
│   ├── TUI/                    # Text user interface (future)
│   ├── Utils/                  # General-purpose utilities
│   ├── acceleration/           # Workload distribution metrics
│   ├── API/                    # Internal API definitions
│   └── _async_utils/           # Async helper utilities
├── rust/                       # Rust workspace (performance-critical)
│   ├── Cargo.toml             # Workspace configuration
│   ├── foundation/            # Shared runtime, error types
│   │   ├── classic-shared-core/
│   │   └── classic-shared-py/
│   ├── business-logic/        # Pure Rust crates (-core suffix)
│   │   ├── classic-yaml-core/
│   │   ├── classic-scanlog-core/
│   │   ├── classic-database-core/
│   │   └── ... (15 more crates)
│   └── python-bindings/       # PyO3 adapters (-py suffix)
│       ├── classic-yaml-py/
│       ├── classic-scanlog-py/
│       └── ... (matching -py crates)
├── tests/                      # Test suite (pytest)
│   ├── fixtures/              # Shared test fixtures and factories
│   ├── rust_integration/      # Rust FFI integration tests
│   ├── unit/                  # Unit tests by component
│   ├── integration/           # Cross-component tests
│   ├── scanlog/               # Scanning logic tests
│   ├── gui/                   # GUI widget/controller tests
│   └── ... (20+ test directories)
├── docs/                       # Documentation
│   ├── architecture/          # Design documents
│   ├── development/           # Dev guides (async, PyO3, testing)
│   ├── rust/                  # Rust architecture and patterns
│   └── testing/               # Testing standards and examples
├── qml/                        # QML UI definitions (if used, currently optional)
├── tools/                      # Development tools and scripts
├── .claude/rules/              # Project guidelines (project-specific)
│   ├── 01-project-overview.md
│   ├── 02-architecture.md
│   ├── 03-testing.md
│   ├── 04-development.md
│   └── 05-memories.md
└── .planning/                  # GSD codebase mapping output
    └── codebase/              # This file and related analysis
```

## Directory Purposes

**ClassicLib/ (Python Core):**
- Purpose: Main Python library containing UI, business logic, data access, and infrastructure
- Contains: Application code (not tests)
- Key files: `__init__.py` (public API), entry point integration

**ClassicLib/core/:**
- Purpose: Infrastructure shared by all layers (logging, registry, async bridge)
- Contains: async_bridge.py (Qt sync/async bridge), registry.py (singleton pattern), logger.py, constants.py
- Key files: `async_bridge.py` (AsyncBridge class), `registry.py` (GlobalRegistry)

**ClassicLib/integration/:**
- Purpose: Rust component detection and factory pattern for component selection
- Contains: detector.py (component availability check), factory/ (submodules for specific components)
- Key files: `factory/core.py` (detection caching), individual factories (formid, database, file_io, etc.)
- Pattern: Import Rust if available, fall back to Python

**ClassicLib/Interface/:**
- Purpose: Qt GUI implementation (PySide6)
- Contains: Controllers, widgets, dialogs, thread workers, signal routing
- Subdirs:
  - `controllers/` - Feature controllers (ScanController, FolderManager, etc.)
  - `shared/` - Shared infrastructure (FeatureContext DI, SignalHub event bus)
  - `widgets/` - Custom Qt widgets
  - `dialogs/` - Dialog windows
  - `workers/` - QThread worker pool
  - `Settings/` - Settings UI components

**ClassicLib/io/:**
- Purpose: File I/O, database operations, YAML configuration
- Contains: Async file operations, database connection pooling, settings caching
- Subdirs:
  - `files/` - FileIOCore (async file read/write)
  - `database/` - AsyncDatabasePool (SQLite connection pooling)
  - `yaml/` - YamlSettingsCache (load/save YAML settings)
    - `sync/` - Synchronous wrappers for GUI
    - `async_/` - Async implementations for CLI/TUI

**ClassicLib/messaging/:**
- Purpose: Central message routing (console, GUI, file logging)
- Contains: Message types, backends (GUI, CLI, file), progress context
- Key files: `handler.py` (MessageHandler singleton), `core/router.py`, backends for different output targets

**ClassicLib/scanning/:**
- Purpose: Crash log and game file scanning logic
- Contains: Log parsing, mod detection, FormID analysis, report generation
- Subdirs:
  - `logs/` - Crash log scanning (executor, orchestrator, analyzers, report)
  - `game/` - Game file scanning (plugins, settings, XSE)
- Key classes: ScanLogsExecutor, OrchestratorCore, FormIDAnalyzer, SuspectScanner, ReportGenerator

**ClassicLib/support/:**
- Purpose: Setup, integrity checks, backup/restore, version management
- Contains: SetupCoordinator (startup sequence), GameIntegrityChecker, BackupManager
- Key files: `setup.py` (initialization coordinator), `game_path.py` (game detection), `versions/` (version matching)

**ClassicLib/TUI/:**
- Purpose: Text user interface (Ratatui-based, future implementation)
- Contains: Screen layouts, input handling
- Status: Currently minimal; full implementation in progress

**ClassicLib/Utils/:**
- Purpose: General-purpose utilities (file ops, string utils, version parsing, web)
- Contains: No complex logic; pure helper functions
- Pattern: Functions grouped by domain (file_utils.py, string_utils.py, etc.)

**rust/ (Rust Workspace):**
- Purpose: Performance-critical business logic and infrastructure
- Structure: Three-layer architecture
  - `foundation/` - Shared runtime (Tokio), error types, utilities
  - `business-logic/` - Pure Rust crates (no PyO3), each `-core` crate is a separate binary
  - `python-bindings/` - PyO3 adapter crates (each `-py` crate wraps corresponding `-core`)

**rust/business-logic/ and rust/python-bindings/:**
- Crates: 21 pairs (foundation + 20 domain-specific)
  - classic-yaml-{core,py}: YAML operations (15-30x faster than ruamel)
  - classic-scanlog-{core,py}: Log parsing and analysis
  - classic-database-{core,py}: SQLite operations
  - classic-file-io-{core,py}: File I/O with async support
  - classic-registry-{core,py}: Global registry (15-25x faster)
  - classic-settings-{core,py}: Settings cache operations
  - classic-constants-{core,py}: Compile-time constants
  - classic-message-{core,py}: Message routing
  - classic-path-{core,py}: Path validation and manipulation
  - classic-config-{core,py}: Configuration loading
  - classic-perf-{core,py}: Performance measurement
  - classic-version-{core,py}: Version parsing and matching
  - classic-xse-{core,py}: XSE plugin detection
  - classic-scangame-{core,py}: Game file scanning
  - classic-web-{core,py}: Web operations
  - classic-update-{core,py}: Update checking
  - classic-pybridge-{core,py}: Async/sync bridging
  - classic-resource-{core,py}: Resource loading
  - classic-version-registry-{core,py}: Version registry
- Pattern: -core crates have zero PyO3; -py crates are PyO3 wrappers only

**tests/ (Test Suite):**
- Purpose: Comprehensive test coverage across all layers
- Organization: Domain-driven directories mirroring ClassicLib structure
- Key directories:
  - `fixtures/` - Shared fixtures (async, crash log data, mocks, etc.)
  - `rust_integration/` - Rust FFI tests
  - `unit/` - Individual component tests
  - `integration/` - Cross-component tests
  - `scanlog/`, `gui/`, `fileio/`, etc. - Domain-specific tests
- Pattern: One test file per source file; `test_<module>_<type>.py` naming

**docs/ (Documentation):**
- Purpose: Developer guides, architecture decisions, API docs
- Key files:
  - `architecture/` - Design documents (async, hybrid architecture)
  - `development/` - Dev guides (PyO3 patterns, async development)
  - `rust/` - Rust architecture and crate descriptions
  - `testing/` - Testing standards and examples

## Key File Locations

**Entry Points:**
- `CLASSIC_Interface.py` - GUI main; calls SetupCoordinator, creates MainWindow
- `CLASSIC_ScanLogs.py` - CLI main; async-first, calls asyncio.run(run_scan())
- `ClassicLib/__init__.py` - Public API exports; Rust component detection

**Configuration:**
- `ClassicLib/core/constants.py` - Application constants (YAML keys, database paths, game IDs)
- `ClassicLib/io/yaml/` - Settings loading (async and sync)
- `rust/Cargo.toml` - Rust workspace definition
- `.claude/rules/` - Project guidelines (CLAUDE.md files)

**Core Logic:**
- `ClassicLib/scanning/logs/executor.py` - ScanLogsExecutor (main scanning entry point)
- `ClassicLib/scanning/logs/orchestrator_core.py` - Parallel orchestration
- `ClassicLib/scanning/logs/parser.py` - Crash log parsing
- `ClassicLib/scanning/logs/analyzers/` - Individual analyzers (FormID, Settings, etc.)
- `ClassicLib/support/setup.py` - SetupCoordinator (initialization sequence)

**Testing:**
- `tests/fixtures/` - All fixtures (centralized; never in individual test files)
- `tests/conftest.py` - Root pytest configuration
- `tests/rust_integration/` - Rust FFI tests
- `.pytest_cache/` - Pytest cache (gitignored)

**Infrastructure:**
- `ClassicLib/core/async_bridge.py` - Sync/async bridge for Qt
- `ClassicLib/core/registry.py` - GlobalRegistry (singleton pattern)
- `ClassicLib/messaging/handler.py` - MessageHandler (central routing)
- `ClassicLib/Interface/shared/context.py` - FeatureContext (DI container)
- `ClassicLib/Interface/shared/signal_hub.py` - SignalHub (event bus)

## Naming Conventions

**Files:**
- `snake_case.py` - Modules and packages
- `ClassName.py` - One class per file (exception: small related helpers)
- `test_<module>_<type>.py` - Tests (e.g., test_executor_unit.py, test_scanlog_integration.py)
- `conftest.py` - Pytest fixtures (centralized in tests/fixtures/, not per-directory)

**Directories:**
- `snake_case/` - Package directories
- Plural names for collections: `analyzers/`, `controllers/`, `widgets/`, `fixtures/`
- Functional grouping: `core/`, `io/`, `integration/`, `scanning/`, `support/`, `utils/`

**Python Identifiers:**
- `snake_case` - Functions and variables
- `UPPERCASE` - Module-level constants
- `PascalCase` - Classes
- `_private` - Internal/private (single underscore)
- `__very_private__` - Name mangling (double underscore, double trailing; avoid)

**Rust Identifiers:**
- `snake_case` - Functions, variables, modules, directories
- `PascalCase` - Types, traits, structs, enums
- `UPPERCASE` - Constants
- Crate names: `kebab-case` with `-core` or `-py` suffix

## Where to Add New Code

**New Feature (e.g., "Add FormID validator"):**
- Primary code: `ClassicLib/scanning/logs/analyzers/` (if related to scanning)
- Tests: `tests/scanlog/test_formid_validator_unit.py`
- Rust acceleration: `rust/business-logic/classic-scanlog-core/` + `rust/python-bindings/classic-scanlog-py/`
- Integration: `ClassicLib/integration/factory/scanlog.py` (add factory method)
- Config: `ClassicLib/core/constants.py` (if new constants needed)

**New Component/Module (e.g., "Game mod dependency analyzer"):**
- Implementation: `ClassicLib/scanning/game/mod_dependency_analyzer.py` (one file, one class)
- Tests: `tests/game/test_mod_dependency_analyzer_unit.py`
- Rust option: Separate `-core` crate if CPU-intensive
- Entry point: Add to ScanGameFilesOrchestrator or similar
- Export: Add to relevant `__init__.py` for public API

**Utilities (e.g., "Hash matching function"):**
- Shared helpers: `ClassicLib/Utils/` (by domain: hash_utils.py, string_utils.py, etc.)
- Tests: `tests/utils/test_<domain>_utils.py`
- Pattern: Pure functions, no state, import by domain

**Test Fixtures:**
- Centralized: `tests/fixtures/` (never in individual test files)
- Organization: `async_fixtures.py`, `crash_log_fixtures.py`, `mock_fixtures.py`, etc.
- Pattern: Fixture functions with @pytest.fixture decorator, autouse only in conftest.py

**GUI Component (e.g., "New dialog for advanced settings"):**
- Dialog class: `ClassicLib/Interface/dialogs/AdvancedSettingsDialog.py`
- Controller: `ClassicLib/Interface/controllers/settings_controller.py` (if new feature needs coordination)
- Tests: `tests/gui/test_advanced_settings_dialog.py`
- Integration: Register in MainWindow or relevant controller
- Signals: Use SignalHub for cross-feature communication, not direct references

## Special Directories

**ClassicLib/CLASSIC Backup/:**
- Purpose: Legacy backup code (not current application code)
- Generated: No
- Committed: Yes (for historical reference, can be deleted)

**rust/Crash Logs/:**
- Purpose: Test/sample crash logs for Rust tests
- Generated: No (committed with repo)
- Committed: Yes

**logs/, coverage_html/, htmlcov/:**
- Purpose: Runtime artifacts (test logs, coverage reports)
- Generated: Yes (during test runs)
- Committed: No (in .gitignore)

**build/, dist/, Release/, .venv/:
- Purpose: Build artifacts, distributions, virtual environments
- Generated: Yes
- Committed: No (in .gitignore)

**rust/target/:**
- Purpose: Rust compilation artifacts
- Generated: Yes
- Committed: No (in .gitignore)

**.planning/codebase/:**
- Purpose: GSD codebase mapping output (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: By `/gsd:map-codebase` command
- Committed: Yes (guides future development)

**_internal/:**
- Purpose: Pre-built Rust extension wheels for standalone distribution
- Generated: No (packaged separately for release)
- Committed: No

## Guidance for Adding New Code

**One Class Per File:** Store each class in its own file to keep modules focused. Exception: Small related helpers can coexist (e.g., exception classes + a single handler).

**Module Organization:** Group related classes by domain (all scanning logic in scanning/, all GUI controllers in Interface/controllers/), not by function (don't create a "models/" directory with random classes).

**Configuration:** Never hardcode paths or settings. Use constants from `ClassicLib/core/constants.py` or load from YAML via `yaml_settings()`.

**Async/Await:** CLI/TUI use native async (await, AsyncBridge); GUI workers use `AsyncBridge.run_async()`. CLI entry point is synchronous (parse args, setup) then calls `asyncio.run()` once.

**Error Handling:** Use MessageHandler for all output. Log errors at appropriate levels (ERROR for failures, DEBUG for detailed info). Never print() or raise exceptions silently.

**Testing:** All new code requires tests. Put fixtures in `tests/fixtures/`, tests in appropriate domain directory. Use pytest markers: @pytest.mark.unit, @pytest.mark.integration, @pytest.mark.asyncio, @pytest.mark.slow.

**Documentation:** All public classes and functions need Google-style docstrings (use `/python-docstrings` skill). Module-level docstring at top of every file. Rust: `///` doc comments on all public items.

**Type Hints:** Complete type annotations required (Python 3.12+ syntax). Use TypeVar for generic functions. Path types are always `pathlib.Path`, never `str`.

**Rust Acceleration:** Write in Rust if CPU-intensive (YAML parsing, large data processing). Create separate `-core` and `-py` crates. Provide Python fallback in `ClassicLib/integration/python/`. Add factory method in `ClassicLib/integration/factory/`.
