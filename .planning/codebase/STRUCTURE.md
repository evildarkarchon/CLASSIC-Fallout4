# Codebase Structure

**Analysis Date:** 2026-04-04

## Directory Layout

```
CLASSIC-Fallout4/                        # Repo root
├── classic-cli/                         # C++20 CLI frontend
│   ├── src/                             # CLI source files
│   ├── tests/                           # CLI integration tests
│   ├── build_cli.ps1                    # Canonical build/test script
│   ├── CMakeLists.txt
│   └── vcpkg.json
├── classic-gui/                         # Qt 6 C++20 GUI frontend
│   ├── src/
│   │   ├── app/                         # Main window + dialogs
│   │   ├── controllers/                 # Business-action controllers
│   │   ├── core/                        # Bridge helpers, signal hub, thread manager
│   │   ├── workers/                     # QObject thread workers
│   │   └── widgets/                     # Custom Qt widgets
│   ├── tests/                           # GUI tests
│   ├── build_gui.ps1                    # Canonical build/test script
│   ├── cmake/
│   ├── resources/
│   └── vcpkg.json
├── ClassicLib-rs/                       # Rust workspace (all Rust code lives here)
│   ├── Cargo.toml                       # Workspace manifest
│   ├── foundation/                      # Shared runtime & utilities
│   │   ├── classic-shared-core/         # ONE RUNTIME, errors, paths, strings
│   │   └── classic-shared-py/          # PyO3 utility adapters
│   ├── business-logic/                  # Pure Rust domain crates
│   │   ├── classic-yaml-core/
│   │   ├── classic-settings-core/
│   │   ├── classic-config-core/
│   │   ├── classic-constants-core/
│   │   ├── classic-version-core/
│   │   ├── classic-version-registry-core/
│   │   ├── classic-registry-core/
│   │   ├── classic-message-core/
│   │   ├── classic-perf-core/
│   │   ├── classic-path-core/
│   │   ├── classic-xse-core/
│   │   ├── classic-web-core/
│   │   ├── classic-update-core/
│   │   ├── classic-file-io-core/
│   │   ├── classic-resource-core/
│   │   ├── classic-database-core/
│   │   ├── classic-crashgen-settings-core/
│   │   ├── classic-scangame-core/
│   │   └── classic-scanlog-core/        # Primary analysis engine
│   ├── cpp-bindings/
│   │   └── classic-cpp-bridge/          # CXX FFI static library
│   │       ├── src/                     # Bridge modules (one per domain)
│   │       ├── include/classic_cxx_bridge/  # CXX-generated + handwritten headers
│   │       └── build.rs
│   ├── node-bindings/
│   │   └── classic-node/                # NAPI-RS bindings (single crate)
│   │       ├── src/                     # One .rs module per domain
│   │       ├── __test__/                # TypeScript/Bun tests
│   │       ├── cli/                     # Node CLI wrapper (TypeScript)
│   │       └── package.json
│   ├── python-bindings/                 # PyO3 binding crates
│   │   ├── classic-*-py/                # One crate per business-logic crate
│   │   ├── parity-artifacts/            # Parity diff reports and API surfaces
│   │   └── tests/                       # Python parity and smoke tests
│   ├── ui-applications/
│   │   └── classic-tui/                 # Ratatui TUI (pure Rust)
│   │       └── src/
│   │           ├── tabs/                # Tab views (main, results, backup, articles)
│   │           └── widgets/
│   └── benches/                         # Criterion benchmarks
│       └── common/                      # Shared benchmark fixtures
├── CLASSIC Data/                        # Runtime data directory
│   └── databases/
│       ├── CLASSIC Main.yaml            # Single source of truth for app version + config
│       └── CLASSIC Fallout4.yaml        # Game-specific rules and mod data
├── sample_logs/                         # Git submodule with test fixture crash logs
│   └── FO4/
├── tests/                               # Top-level integration tests (PowerShell)
│   └── powershell/
├── tools/                               # Developer tooling
│   ├── python_api_parity/               # Python parity check tooling
│   ├── node_api_parity/                 # Node parity check tooling
│   ├── use_msvc_from_git_bash.sh        # MSVC linker shim for Git Bash
│   └── sign-binaries.ps1
├── docs/                                # Contributor documentation
│   ├── api/                             # Per-crate API docs (canonical contract)
│   └── architecture/                    # Architecture overview docs
├── .planning/                           # GSD planning artifacts
│   └── codebase/                        # Codebase map documents
├── scripts/                             # bench/profile helpers
├── performance_baselines/               # Criterion baseline results
├── openspec/                            # OpenSpec change specs
├── conductor/                           # Workflow orchestration
├── rebuild_rust.ps1                     # Cross-platform Rust rebuild helper
├── rebuild_node.ps1                     # Node binding rebuild helper
├── set_version.ps1                      # Version bump tooling
└── ClassicLib-rs/Cargo.toml             # Workspace root
```

## Directory Purposes

**`ClassicLib-rs/foundation/`:**
- Purpose: Process-wide shared runtime, errors, path/string helpers, PyO3 utilities
- Contains: `classic-shared-core` (ONE RUNTIME RULE via `LazyLock<Runtime>`), `classic-shared-py`
- Key files: `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` (runtime bootstrap + `get_runtime()`)

**`ClassicLib-rs/business-logic/`:**
- Purpose: All domain logic; never import PyO3 here
- Contains: 19 pure Rust `-core` crates; each has its own `src/` and `tests/` subdirectories
- Key files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` (primary analysis engine), `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs` (config loading)

**`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`:**
- Purpose: CXX FFI surface consumed by `classic-cli` and `classic-gui`
- Contains: 14 domain-aligned `.rs` modules in `src/`; CXX-generated C++ headers in `include/classic_cxx_bridge/`
- Key files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`, `src/scanner.rs`, `src/runtime.rs`

**`ClassicLib-rs/node-bindings/classic-node/`:**
- Purpose: NAPI-RS Node.js/Bun bindings as a single compiled `.node` native module
- Contains: `src/` (20 Rust modules), `__test__/` (per-module `.spec.ts` files + parity specs), `cli/` (TypeScript CLI wrapper)
- Key files: `ClassicLib-rs/node-bindings/classic-node/src/lib.rs`, `package.json`, `tsconfig.json`

**`ClassicLib-rs/python-bindings/`:**
- Purpose: PyO3 Python bindings mirroring business-logic crates 1:1
- Contains: One `-py` crate per `-core` crate; `parity-artifacts/` for automated diff reports; `tests/` for parity smoke tests
- Key files: `ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs`, `parity-artifacts/parity_diff_report.md`

**`ClassicLib-rs/ui-applications/classic-tui/`:**
- Purpose: Ratatui terminal UI; uses `-core` crates directly without bridge indirection
- Contains: `src/` with `app.rs`, `state.rs`, `tabs/`, `widgets/`, `ui.rs`, `theme.rs`

**`classic-cli/src/`:**
- Purpose: C++ CLI scanner entry point and pipeline
- Key files: `classic-cli/src/main.cpp`, `scanner.cpp` (drives bridge scan), `cli_args.cpp`, `progress.cpp`, `report_writer.cpp`, `thread_pool.cpp`

**`classic-gui/src/`:**
- Purpose: Qt 6 desktop GUI organized by MVC-ish role
- Contains: `app/` (dialogs + MainWindow), `controllers/` (feature controllers owning business action flow), `workers/` (QObject thread workers for async bridge calls), `core/` (bridge helpers, signal bus), `widgets/` (custom Qt widgets)
- Key files: `classic-gui/src/main.cpp`, `app/mainwindow.cpp`, `controllers/scancontroller.cpp`, `workers/scanworker.cpp`

**`CLASSIC Data/databases/`:**
- Purpose: Runtime YAML data consumed by the application; NOT committed to Rust source
- Key files: `CLASSIC Data/databases/CLASSIC Main.yaml` (single source of truth for version + core config), `CLASSIC Data/databases/CLASSIC Fallout4.yaml` (game rules)

**`sample_logs/FO4/`:**
- Purpose: Git submodule providing real crash log test fixtures for integration and parity tests
- Generated: No (curated fixtures)
- Committed: As a submodule reference

**`docs/api/`:**
- Purpose: Contributor-facing API documentation; one `.md` per crate or workflow boundary
- Key files: `docs/api/README.md` (loading order index), `docs/api/classic-scanlog-core.md`, `docs/api/binding-parity-overview.md`

## Naming Conventions

**Files:**
- Rust source: `snake_case.rs` matching the module name
- C++ source: `lowercase_with_underscores.cpp` / `.h`
- Qt worker suffix: `*worker.cpp` / `*worker.h`
- Qt controller suffix: `*controller.cpp` / `*controller.h`
- PowerShell scripts: `PascalCase_snake_mix.ps1` or `verb_noun.ps1`

**Directories:**
- Rust crates: `classic-{domain}-{layer}` (e.g., `classic-scanlog-core`, `classic-scanlog-py`)
- The `-core` suffix means pure Rust business logic; the `-py` suffix means PyO3 adapter

**Rust modules:**
- One `.rs` file per module, matching the `mod foo;` declaration
- `lib.rs` always present as the crate root

**C++ namespaces:**
- `classic::runtime`, `classic::scanner`, `classic::message`, `classic::registry`, etc. (mirrors bridge module names)

## Key File Locations

**Entry Points:**
- `classic-gui/src/main.cpp`: Qt GUI application startup
- `classic-cli/src/main.cpp`: CLI application startup
- `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`: TUI application startup
- `ClassicLib-rs/node-bindings/classic-node/cli/main.ts`: Node CLI entry

**Configuration:**
- `ClassicLib-rs/Cargo.toml`: Workspace definition and shared dependency versions
- `CLASSIC Data/databases/CLASSIC Main.yaml`: Runtime app config and version (NOT in Rust workspace)
- `ClassicLib-rs/.cargo/`: Cargo configuration (linker settings for MSVC)

**Core Logic:**
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`: Crash log analysis pipeline
- `ClassicLib-rs/business-logic/classic-scangame-core/src/orchestrator.rs`: Game scan pipeline
- `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs`: Config loading types
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`: Shared Tokio runtime
- `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs`: Global state store
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs`: Game version metadata

**Bridge:**
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`: Scan bridge (primary feature)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/runtime.rs`: Runtime init/shutdown bridge
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h`: C++ callback interface

**Testing:**
- `ClassicLib-rs/node-bindings/classic-node/__test__/`: Node per-module specs + parity tests
- `ClassicLib-rs/python-bindings/tests/`: Python parity smoke tests
- `ClassicLib-rs/python-bindings/parity-artifacts/`: Automated parity diff reports
- `sample_logs/FO4/`: Crash log fixtures (submodule)
- `tests/powershell/`: Integration tests for C++ frontends

**API Contracts:**
- `docs/api/README.md`: Navigation index; read before changing any public Rust API
- `docs/api/classic-scanlog-core.md`: Scanlog contract
- `docs/api/binding-parity-overview.md`: What is exposed across C++/Node/Python

## Where to Add New Code

**New business-logic feature (Rust):**
- Implementation: Create a new crate under `ClassicLib-rs/business-logic/classic-{domain}-core/`
- Tests: Add `tests/` subdirectory within the crate
- Register: Add to `ClassicLib-rs/Cargo.toml` workspace `members`
- API doc: Add a corresponding page under `docs/api/`

**New bridge module (C++):**
- Implementation: Add a new `.rs` file under `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`
- Register: Add `pub mod {name};` to `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`
- If headers are needed: Add to `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/`

**New Python binding:**
- Implementation: Create `ClassicLib-rs/python-bindings/classic-{domain}-py/` crate
- Register: Add to `ClassicLib-rs/Cargo.toml` workspace `members`
- Update parity: Run `python tools/python_api_parity/check_parity_gate.py --repo-root .`

**New Node.js binding module:**
- Implementation: Add a new `.rs` file under `ClassicLib-rs/node-bindings/classic-node/src/`
- Register: Add `mod {name};` in `ClassicLib-rs/node-bindings/classic-node/src/lib.rs`
- Tests: Add `ClassicLib-rs/node-bindings/classic-node/__test__/{name}.spec.ts`

**New C++ GUI feature:**
- Controller: `classic-gui/src/controllers/{name}controller.{cpp,h}`
- Worker (if async): `classic-gui/src/workers/{name}worker.{cpp,h}`
- Dialog/widget: `classic-gui/src/app/{name}dialog.{cpp,h}` or `classic-gui/src/widgets/{name}.{cpp,h}`

**Utilities:**
- Shared Rust helpers: Add to the appropriate `-core` crate's `src/` (prefer extending existing modules over new crates)
- Build scripts: `tools/` for developer utilities; `scripts/` for bench/profile scripts

## Special Directories

**`ClassicLib-rs/benches/`:**
- Purpose: Criterion benchmark entry points and shared fixture helpers
- Generated: No
- Committed: Yes

**`ClassicLib-rs/python-bindings/parity-artifacts/`:**
- Purpose: Generated parity diff reports comparing Python and Node API surfaces against Rust core
- Generated: Yes (via `python tools/python_api_parity/check_parity_gate.py`)
- Committed: Yes (treated as checked-in contract artifacts)

**`sample_logs/`:**
- Purpose: Git submodule with real Fallout 4 crash log test fixtures
- Generated: No (curated)
- Committed: As submodule pointer only

**`openspec/`:**
- Purpose: OpenSpec change-management spec files for structured feature proposals
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning documents, roadmap, phase plans, codebase maps
- Generated: Partially (codebase map files generated by `/gsd:map-codebase`)
- Committed: Yes

---

*Structure analysis: 2026-04-04*
