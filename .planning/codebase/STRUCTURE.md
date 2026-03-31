# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
CLASSIC-Fallout4/                      # Repo root / Windows working directory
├── classic-cli/                       # C++20 CLI frontend
│   ├── CMakeLists.txt                 # CMake project (links Rust via Corrosion)
│   ├── build_cli.ps1                  # Canonical build script (always use this, not ctest directly)
│   ├── test_cli.ps1                   # CLI integration test runner
│   ├── src/                           # C++ source files
│   └── tests/                         # Catch2 unit tests
│
├── classic-gui/                       # Qt 6 C++20 GUI frontend
│   ├── CMakeLists.txt
│   ├── build_gui.ps1                  # Canonical build script
│   ├── cmake/                         # Qt-specific CMake modules
│   ├── resources/                     # Qt resources (.qrc, icons)
│   ├── src/                           # C++ source tree
│   │   ├── main.cpp                   # Application entry point
│   │   ├── app/                       # Top-level windows and dialogs
│   │   ├── controllers/               # Business logic controllers (scan, backup, results, game files)
│   │   ├── core/                      # Qt bridge utilities, signal hub, thread manager
│   │   ├── widgets/                   # Custom Qt widgets (progress bar, markdown viewer, report list)
│   │   └── workers/                   # QObject workers run on background threads
│   └── tests/                         # Catch2 + Qt test suite
│
├── ClassicLib-rs/                     # Rust workspace root
│   ├── Cargo.toml                     # Workspace manifest (all members listed here)
│   ├── foundation/                    # Lowest-level shared crates
│   │   ├── classic-shared-core/       # ONE RUNTIME RULE, errors, path/string/perf utils
│   │   └── classic-shared-py/         # PyO3 utilities shared by all -py crates
│   ├── business-logic/                # Pure Rust domain crates (no PyO3/CXX)
│   │   ├── classic-config-core/       # YAML config loading and typed config structs
│   │   ├── classic-constants-core/    # Game/version/YAML identifier enums
│   │   ├── classic-crashgen-settings-core/ # Crashgen rule model and evaluator
│   │   ├── classic-database-core/     # SQLite async pool for FormID lookups
│   │   ├── classic-file-io-core/      # File I/O, hashing, log collection, DDS parsing
│   │   ├── classic-message-core/      # Message DTOs, routing enums, log formatting
│   │   ├── classic-path-core/         # Game/docs path detection, validation, backups
│   │   ├── classic-perf-core/         # Global timing sample collection and scoped timers
│   │   ├── classic-registry-core/     # Process-wide typed singleton registry
│   │   ├── classic-resource-core/     # Resource classification and enumeration helpers
│   │   ├── classic-scangame-core/     # Game installation validation, archive/file checks
│   │   ├── classic-scanlog-core/      # Crash log analysis (primary feature)
│   │   ├── classic-settings-core/     # YAML settings cache (sync/async)
│   │   ├── classic-update-core/       # GitHub release/update-check client
│   │   ├── classic-version-core/      # Version parsing, text extraction, PE-version helpers
│   │   ├── classic-version-registry-core/ # Game version detection and OG/NG/AE/VR selection
│   │   ├── classic-web-core/          # URL and mod-site helper layer
│   │   ├── classic-xse-core/          # XSE loader/version detection
│   │   └── classic-yaml-core/         # YAML parsing, caching, merge helpers
│   ├── cpp-bindings/
│   │   └── classic-cpp-bridge/        # CXX staticlib — 16 bridge modules
│   │       ├── include/classic_cxx_bridge/  # Hand-written C++ headers
│   │       └── src/                   # One .rs file per bridge module
│   ├── python-bindings/               # PyO3 (-py) crates, one per -core crate
│   │   ├── classic-*-py/              # Individual binding crates
│   │   ├── tests/                     # Cross-crate parity smoke tests (pytest)
│   │   └── parity-artifacts/          # Generated parity diff/coverage reports
│   ├── node-bindings/
│   │   └── classic-node/              # Single NAPI-RS crate (Bun/Node)
│   │       ├── src/                   # One .rs module per feature area
│   │       ├── __test__/              # Bun/Node runtime tests
│   │       └── parity-artifacts/      # Generated parity reports
│   ├── ui-applications/
│   │   └── classic-tui/               # Ratatui terminal UI (Rust binary crate)
│   │       └── src/
│   │           ├── main.rs            # TUI entry point
│   │           ├── app.rs             # App state machine
│   │           ├── tabs/              # Tab views (main, results, backup, articles)
│   │           └── widgets/           # Custom Ratatui widgets
│   └── benches/                       # Workspace-level benchmarks
│
├── CLASSIC Data/                      # Runtime data directory (YAML configs, SQLite DBs)
│   ├── CLASSIC Main.yaml              # Master YAML: version registry, crashgen settings
│   ├── CLASSIC Fallout4.yaml          # Game-specific YAML: mod lists, suspect rules
│   ├── databases/                     # SQLite FormID database files (.db)
│   └── games/                         # Per-game YAML fragments
│
├── docs/                              # Contributor documentation
│   ├── api/                           # Crate-level API contracts (primary reference)
│   └── architecture/                  # Architecture overviews
│
├── tools/                             # Developer tooling (Python scripts)
│   ├── python_api_parity/             # Python parity gate check scripts
│   └── node_api_parity/               # Node parity gate check scripts
│
├── sample_logs/                       # Test fixture crash logs (git submodule: FO4/)
├── scripts/                           # Benchmark and profiling helpers
├── tests/                             # PowerShell-level build/integration tests
├── .github/workflows/                 # CI pipelines (ci-cpp, ci-rust, ci-typescript, ci-python-bindings, benchmarks)
├── rebuild_rust.ps1                   # Rebuild Python or Node bindings selectively
├── rebuild_node.ps1                   # Rebuild Node bindings
├── set_version.ps1                    # Version bump helper
└── CLASSIC Settings.yaml              # User settings file (runtime, not tracked)
```

## Directory Purposes

**`classic-cli/src/`:**
- Purpose: CLI application C++ source
- Contains: `main.cpp`, `cli_args.{cpp,h}`, `scanner.{cpp,h}`, `progress.{cpp,h}`, `report_writer.{cpp,h}`, `thread_pool.{cpp,h}`
- Key files: `classic-cli/src/main.cpp`, `classic-cli/src/scanner.cpp`

**`classic-gui/src/app/`:**
- Purpose: Top-level Qt windows and dialogs
- Contains: `MainWindow`, `AboutDialog`, `ErrorDialog`, `PapyrusDialog`, `PathDialog`, `SettingsDialog`
- Key files: `classic-gui/src/app/mainwindow.{cpp,h}`

**`classic-gui/src/controllers/`:**
- Purpose: Qt controllers encapsulating scan, backup, results, and game-files workflows
- Contains: `ScanController`, `BackupController`, `ResultsController`, `GameFilesController`

**`classic-gui/src/workers/`:**
- Purpose: QObject workers run on background threads via `ThreadManager`
- Contains: `ScanWorker`, `GameFilesWorker`, `PapyrusWorker`, `UpdateWorker`, `ScanProgressModel`

**`ClassicLib-rs/foundation/classic-shared-core/src/`:**
- Purpose: Foundation utilities used by every crate
- Key files: `lib.rs` (runtime), `errors.rs`, `path_core.rs`, `strings_core.rs`, `performance_core.rs`

**`ClassicLib-rs/business-logic/classic-scanlog-core/src/`:**
- Purpose: Primary feature — crash log parsing and analysis
- Key files: `orchestrator.rs`, `parser.rs`, `report.rs`, `mod_detector.rs`, `formid_analyzer.rs`

**`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`:**
- Purpose: CXX bridge modules — one `.rs` file per feature area
- Key files: `scanner.rs` (main scan pipeline), `game.rs`, `config.rs`, `files.rs`

**`ClassicLib-rs/python-bindings/tests/`:**
- Purpose: Pytest cross-crate parity smoke tests
- Key files: `test_tier1_parity_smoke.py`, `fixtures/tier1_parity_fixtures.py`

**`CLASSIC Data/`:**
- Purpose: Runtime YAML and SQLite data consumed at application startup
- Contains: `CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`, FormID `.db` files
- Generated: No — these are maintained data files
- Committed: Yes (core YAML files)

## Key File Locations

**Entry Points:**
- `classic-gui/src/main.cpp`: Qt GUI application start
- `classic-cli/src/main.cpp`: CLI application start
- `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`: TUI binary entry point

**Build Configuration:**
- `classic-cli/build_cli.ps1`: C++ CLI build script (always use, not raw cmake/ctest)
- `classic-gui/build_gui.ps1`: C++ GUI build script
- `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`: CMake projects (use Corrosion for Rust)
- `ClassicLib-rs/Cargo.toml`: Rust workspace manifest

**Core Logic:**
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`: Scan orchestration
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`: Typed YAML config
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`: CXX scan bridge
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`: ONE RUNTIME RULE and `get_runtime()`

**API Contracts:**
- `docs/api/README.md`: Index to all crate API docs (read before changing public APIs)
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts`: Node TypeScript declarations
- `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json`: Python parity report

**Testing:**
- `classic-cli/tests/`: Catch2 C++ unit tests
- `classic-gui/tests/`: Catch2 + Qt test suite
- `ClassicLib-rs/python-bindings/tests/`: pytest parity tests
- `ClassicLib-rs/node-bindings/classic-node/__test__/`: Bun/Node runtime tests
- Per-crate `tests/` dirs inside each `*-core` crate (e.g., `classic-yaml-core/tests/`)

## Naming Conventions

**Files (Rust):**
- `snake_case.rs` for all Rust source files
- `lib.rs` is the crate root for every crate
- `main.rs` for binary crates (TUI)
- Test files in `tests/` subdirectory are named `test_*.rs`

**Files (C++):**
- `lowercase.{cpp,h}` for plain modules: `scanner.cpp`, `cli_args.h`
- `lowercase{noun}.{cpp,h}` for Qt classes: `scanworker.cpp`, `mainwindow.h`

**Directories (Rust crates):**
- `classic-{domain}-core` for pure Rust business logic
- `classic-{domain}-py` for PyO3 Python bindings
- `classic-{domain}` for Node bindings (single crate covers all domains)

**Crate names (Rust):**
- `classic_{domain}_core` (underscore in crate name, hyphen in directory)
- Consistent with workspace manifest

## Where to Add New Code

**New Rust business logic feature:**
- Primary code: `ClassicLib-rs/business-logic/classic-{domain}-core/src/`
- Tests: `ClassicLib-rs/business-logic/classic-{domain}-core/tests/` or inline `#[cfg(test)]`
- Add to workspace: `ClassicLib-rs/Cargo.toml` members list
- Document API: `docs/api/classic-{domain}-core.md`

**New C++ bridge entry point:**
- Bridge module: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/{module}.rs`
- Register in: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`
- Add to CMake: `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` `corrosion_add_cxxbridge(FILES ...)` list

**New Python binding:**
- Crate: `ClassicLib-rs/python-bindings/classic-{domain}-py/src/lib.rs`
- Add to workspace: `ClassicLib-rs/Cargo.toml`
- Rebuild: `./rebuild_rust.ps1 -Target python -Crates classic_{domain}`

**New Node binding module:**
- Module file: `ClassicLib-rs/node-bindings/classic-node/src/{module}.rs`
- Register in `lib.rs`, update `index.d.ts` TypeScript declarations
- Rebuild: `./rebuild_node.ps1` or `bun run build` from node-bindings dir

**New Qt GUI feature:**
- View/dialog: `classic-gui/src/app/`
- Controller: `classic-gui/src/controllers/`
- Background worker: `classic-gui/src/workers/`
- Custom widget: `classic-gui/src/widgets/`

**New CLI feature:**
- Source: `classic-cli/src/`
- Tests: `classic-cli/tests/`

**New TUI tab or widget:**
- Tab: `ClassicLib-rs/ui-applications/classic-tui/src/tabs/`
- Widget: `ClassicLib-rs/ui-applications/classic-tui/src/widgets/`

**Utilities (shared Rust helpers):**
- If usable by all crates: add to `ClassicLib-rs/foundation/classic-shared-core/src/`
- If domain-specific: add to the relevant `-core` crate

## Special Directories

**`CLASSIC Data/`:**
- Purpose: Runtime YAML configuration and SQLite FormID databases read at startup
- Generated: No (maintained; SQLite files are partially generated)
- Committed: Core YAML files yes; `.db-shm`/`.db-wal` WAL files no

**`CLASSIC Backup/`:**
- Purpose: Backup copies of game/cleaned files created by the backup feature
- Generated: Yes (at runtime by BackupManager)
- Committed: No

**`sample_logs/FO4/`:**
- Purpose: Test fixture crash log files for integration tests
- Generated: No (git submodule)
- Committed: Yes (via submodule)

**`ClassicLib-rs/target/`:**
- Purpose: Rust build artifacts
- Generated: Yes
- Committed: No

**`classic-cli/build/`, `classic-gui/build/`:**
- Purpose: CMake build trees (includes Corrosion-embedded Rust builds and vcpkg)
- Generated: Yes
- Committed: No

**`ClassicLib-rs/python-bindings/.venv/`:**
- Purpose: Python virtual environment for binding tests
- Generated: Yes
- Committed: No

**`ClassicLib-rs/python-bindings/parity-artifacts/`:**
- Purpose: Generated parity diff/coverage JSON reports from parity gate tooling
- Generated: Yes (by `tools/python_api_parity/check_parity_gate.py`)
- Committed: Yes (baseline snapshots)

**`ClassicLib-rs/node-bindings/classic-node/parity-artifacts/`:**
- Purpose: Generated Node/TypeScript parity reports
- Generated: Yes
- Committed: Yes (baseline snapshots)

---

*Structure analysis: 2026-03-30*
