# Codebase Structure

**Analysis Date:** 2026-04-11

## Directory Layout

```text
[project-root]/
├── classic-cli/                 # Native C++ CLI frontend
├── classic-gui/                 # Native Qt 6 desktop frontend
├── ClassicLib-rs/               # Rust workspace: foundation, business logic, bindings, TUI
├── CLASSIC Data/                # Runtime YAML, databases, graphics, help, game metadata
├── docs/                        # Contributor docs, API docs, architecture docs, parity docs
├── tests/                       # Repo-level PowerShell/script tests
├── tools/                       # Parity, signing, shell, and support tooling
├── sample_logs/                 # Crash-log fixtures submodule content
├── .planning/                   # Planning artifacts consumed by GSD workflows
├── rebuild_rust.ps1             # Canonical Rust rebuild entrypoint
├── rebuild_node.ps1             # Node binding rebuild entrypoint
└── README.md                    # Top-level repository guide
```

## Directory Purposes

**`classic-cli/`:**
- Purpose: House the C++ command-line application.
- Contains: Build wrapper `classic-cli/build_cli.ps1`, CMake files, source in `classic-cli/src/`, tests in `classic-cli/tests/`, and runtime test fixtures in `classic-cli/test_data/`.
- Key files: `classic-cli/CMakeLists.txt`, `classic-cli/src/main.cpp`, `classic-cli/src/scanner.cpp`, `classic-cli/tests/test_cli_args.cpp`.

**`classic-gui/`:**
- Purpose: House the Qt desktop application and its test/build scaffolding.
- Contains: Build wrapper `classic-gui/build_gui.ps1`, CMake files, source in `classic-gui/src/`, tests in `classic-gui/tests/`, Qt/CMake helpers in `classic-gui/cmake/`, and resources in `classic-gui/resources/`.
- Key files: `classic-gui/CMakeLists.txt`, `classic-gui/src/CMakeLists.txt`, `classic-gui/src/main.cpp`, `classic-gui/src/app/mainwindow.cpp`, `classic-gui/tests/CMakeLists.txt`.

**`ClassicLib-rs/`:**
- Purpose: House the Rust workspace that owns shared runtime facilities, business rules, bindings, and the TUI.
- Contains: Workspace manifest in `ClassicLib-rs/Cargo.toml`, foundation crates in `ClassicLib-rs/foundation/`, domain crates in `ClassicLib-rs/business-logic/`, C++ bridge in `ClassicLib-rs/cpp-bindings/`, Node bindings in `ClassicLib-rs/node-bindings/`, Python bindings in `ClassicLib-rs/python-bindings/`, and Rust UI binaries in `ClassicLib-rs/ui-applications/`.
- Key files: `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs`, `ClassicLib-rs/validate_stubs.py`.

**`ClassicLib-rs/foundation/`:**
- Purpose: Hold shared foundational crates.
- Contains: `ClassicLib-rs/foundation/classic-shared-core/` and `ClassicLib-rs/foundation/classic-shared-py/`.
- Key files: `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`, `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs`.

**`ClassicLib-rs/business-logic/`:**
- Purpose: Hold focused Rust domain crates.
- Contains: One crate per domain, including `classic-config-core/`, `classic-database-core/`, `classic-file-io-core/`, `classic-message-core/`, `classic-path-core/`, `classic-perf-core/`, `classic-registry-core/`, `classic-resource-core/`, `classic-scangame-core/`, `classic-scanlog-core/`, `classic-settings-core/`, `classic-update-core/`, `classic-version-core/`, `classic-version-registry-core/`, `classic-web-core/`, and `classic-xse-core/`.
- Key files: `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`, `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`, `ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs`.

**`ClassicLib-rs/cpp-bindings/`:**
- Purpose: Hold the CXX-based bridge consumed by native C++ frontends.
- Contains: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` with bridge modules under `src/`, generated/build support in `build.rs`, exported headers in `include/`, and parity artifacts in `parity-artifacts/`.
- Key files: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`.

**`ClassicLib-rs/node-bindings/`:**
- Purpose: Hold the maintained Node/Bun integration surface.
- Contains: `ClassicLib-rs/node-bindings/classic-node/` with Rust NAPI modules in `src/`, JS packaging files, tests in `__test__/`, and generated contract files like `index.d.ts`.
- Key files: `ClassicLib-rs/node-bindings/classic-node/src/lib.rs`, `ClassicLib-rs/node-bindings/classic-node/index.js`, `ClassicLib-rs/node-bindings/classic-node/package.json`.

**`ClassicLib-rs/python-bindings/`:**
- Purpose: Hold maintained PyO3 bindings and binding-specific tests.
- Contains: Per-domain `classic-*-py/` crates, shared fixtures/tests in `ClassicLib-rs/python-bindings/tests/`, parity artifacts, and binding-local virtualenv state in `ClassicLib-rs/python-bindings/.venv/`.
- Key files: `ClassicLib-rs/python-bindings/tests/conftest.py`, `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py`, `ClassicLib-rs/python-bindings/requirements-ci.txt`.

**`ClassicLib-rs/ui-applications/`:**
- Purpose: Hold Rust-native application crates.
- Contains: `ClassicLib-rs/ui-applications/classic-tui/` with `src/main.rs`, `src/lib.rs`, and TUI tests.
- Key files: `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml`, `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`.

**`CLASSIC Data/`:**
- Purpose: Hold runtime-owned assets loaded by the frontends and Rust core.
- Contains: `CLASSIC Data/databases/`, `CLASSIC Data/games/`, `CLASSIC Data/graphics/`, `CLASSIC Data/Help/` and local YAML like `CLASSIC Data/CLASSIC Fallout4 Local.yaml`.
- Key files: `CLASSIC Data/databases/`, `CLASSIC Data/games/`, `CLASSIC Data/graphics/CLASSIC.ico`.

**`docs/`:**
- Purpose: Hold contributor-facing documentation and contract docs.
- Contains: API docs in `docs/api/`, architecture docs in `docs/architecture/`, testing docs in `docs/testing/`, and parity/implementation docs in `docs/implementation/`.
- Key files: `docs/api/README.md`, `docs/architecture/ARCHITECTURE_OVERVIEW.md`, `docs/README.md`.

**`tests/`:**
- Purpose: Hold repo-level script tests rather than app-local unit tests.
- Contains: PowerShell tests in `tests/powershell/` and planning-related test assets in `tests/planning/`.
- Key files: `tests/powershell/cpp_build_scripts.test.ps1`, `tests/powershell/rebuild_rust.general_target.test.ps1`.

**`tools/`:**
- Purpose: Hold reusable support tooling.
- Contains: Parity checkers under `tools/cxx_api_parity/`, `tools/node_api_parity/`, `tools/python_api_parity/`, shell helpers like `tools/use_msvc_from_git_bash.sh`, and signing/dev-shell scripts.
- Key files: `tools/enter_vs_dev_shell.ps1`, `tools/parity_contract_merge_owner.py`, `tools/cxx_api_parity/`, `tools/node_api_parity/`, `tools/python_api_parity/`.

## Key File Locations

**Entry Points:**
- `classic-cli/src/main.cpp`: CLI process entrypoint.
- `classic-gui/src/main.cpp`: Qt GUI process entrypoint.
- `ClassicLib-rs/ui-applications/classic-tui/src/main.rs`: Rust TUI entrypoint.
- `ClassicLib-rs/node-bindings/classic-node/src/lib.rs`: NAPI export root.
- `ClassicLib-rs/python-bindings/*-py/src/lib.rs`: PyO3 export roots.

**Configuration:**
- `ClassicLib-rs/Cargo.toml`: Rust workspace layout and shared dependencies.
- `classic-cli/CMakeLists.txt`: CLI build, bridge import, and test target registration.
- `classic-gui/CMakeLists.txt`: GUI build, bridge import, packaging, and Qt deployment.
- `classic-gui/src/CMakeLists.txt`: GUI source ownership and link graph.
- `classic-gui/tests/CMakeLists.txt`: Qt test target registration.
- `rebuild_rust.ps1`: Canonical Rust rebuild dispatcher.

**Core Logic:**
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`: Shared runtime and foundational exports.
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`: Config/YAML model entrypoint.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`: Scanlog domain entrypoint.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`: Native bridge orchestrator surface.
- `classic-gui/src/controllers/scancontroller.cpp`: GUI scan orchestration.
- `classic-cli/src/scanner.cpp`: CLI scan orchestration.

**Testing:**
- `classic-cli/tests/`: CLI unit tests.
- `classic-gui/tests/`: GUI Qt tests.
- `ClassicLib-rs/python-bindings/tests/`: Python binding smoke/parity tests.
- `tests/powershell/`: Repo-level build and script tests.
- `sample_logs/FO4/`: Crash-log fixture corpus for integration-style workflows.

## Ownership Boundaries

**Rust core owns behavior:**
- Put shared product logic in `ClassicLib-rs/business-logic/*-core/` or `ClassicLib-rs/foundation/classic-shared-core/`.
- Keep parsing, validation, orchestration, persistence rules, version logic, and scan rules out of `classic-cli/` and `classic-gui/` when the behavior should be shared.

**C++ frontends own presentation and process integration:**
- Put CLI-only UX in `classic-cli/src/`.
- Put Qt windows, controllers, workers, and widgets in `classic-gui/src/app/`, `src/controllers/`, `src/workers/`, `src/widgets/`, and `src/core/`.
- Keep these files focused on UI flow, threading, dialogs, signal wiring, and type conversion.

**Bridge crates own translation, not policy:**
- Put C++ FFI shims in `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`.
- Put JS adapter code in `ClassicLib-rs/node-bindings/classic-node/src/`.
- Put Python adapter code in `ClassicLib-rs/python-bindings/*-py/src/`.
- Do not move shared business rules into these surfaces.

**Runtime assets live outside code crates:**
- Keep packaged YAML, DBs, graphics, and help content under `CLASSIC Data/`.
- Frontends discover these assets at runtime; they are not owned by `classic-cli/src/` or `classic-gui/src/`.

**Docs and planning stay separate from implementation:**
- API contract docs live in `docs/api/`.
- Architecture docs live in `docs/architecture/`.
- Planning artifacts live in `.planning/`.

## Naming Conventions

**Files:**
- Rust crate directories use kebab-case with domain suffixes: `ClassicLib-rs/business-logic/classic-scanlog-core/`, `ClassicLib-rs/python-bindings/classic-config-py/`.
- Rust module files use snake_case: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs`, `ClassicLib-rs/node-bindings/classic-node/src/logging_contract.rs`.
- C++ source files use lowercase snake_case: `classic-gui/src/controllers/scancontroller.cpp`, `classic-cli/src/report_writer.cpp`.

**Directories:**
- Repo-level product surfaces use descriptive names: `classic-cli/`, `classic-gui/`, `ClassicLib-rs/`, `CLASSIC Data/`.
- GUI subdirectories are role-based: `classic-gui/src/app/`, `src/controllers/`, `src/core/`, `src/workers/`, `src/widgets/`.
- Rust workspace directories are layer-based: `ClassicLib-rs/foundation/`, `ClassicLib-rs/business-logic/`, `ClassicLib-rs/cpp-bindings/`, `ClassicLib-rs/node-bindings/`, `ClassicLib-rs/python-bindings/`, `ClassicLib-rs/ui-applications/`.

## Where to Add New Code

**New Feature:**
- Primary shared logic: `ClassicLib-rs/business-logic/<new-or-existing-domain>-core/src/`.
- C++ bridge exposure for native apps: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/<domain>.rs` and corresponding bridge declarations consumed by `classic-cli/CMakeLists.txt` or `classic-gui/CMakeLists.txt`.
- Native GUI orchestration: `classic-gui/src/controllers/` plus `classic-gui/src/workers/` when the task is asynchronous.
- Tests: Rust crate-local tests in the touched crate, CLI tests under `classic-cli/tests/`, GUI tests under `classic-gui/tests/`, binding tests under `ClassicLib-rs/python-bindings/tests/` or `ClassicLib-rs/node-bindings/classic-node/__test__/`.

**New Component/Module:**
- Qt visual components: `classic-gui/src/widgets/`.
- Qt dialogs/windows: `classic-gui/src/app/`.
- Qt feature coordination: `classic-gui/src/controllers/`.
- Rust domain modules: `ClassicLib-rs/business-logic/<crate>/src/`.

**Utilities:**
- Shared Rust helpers: `ClassicLib-rs/foundation/classic-shared-core/src/`.
- Repo scripts/tooling: `tools/` or root scripts such as `rebuild_rust.ps1` only when the utility is repo-wide and not product runtime logic.

## Special Directories

**`ClassicLib-rs/target/`:**
- Purpose: Cargo build output.
- Generated: Yes.
- Committed: No.

**`classic-cli/build/` and `classic-gui/build/`:**
- Purpose: CMake/Ninja build output.
- Generated: Yes.
- Committed: No.

**`ClassicLib-rs/node-bindings/classic-node/dist/`:**
- Purpose: Node binding build artifacts.
- Generated: Yes.
- Committed: Mixed; treat emitted artifacts as build output unless the touched workflow explicitly requires refreshed contract files like `index.d.ts`.

**`ClassicLib-rs/python-bindings/.venv/`:**
- Purpose: Binding-local virtual environment for Python validation.
- Generated: Yes.
- Committed: No.

**`sample_logs/`:**
- Purpose: Fixture corpus for crash-log scenarios.
- Generated: No.
- Committed: Yes, as submodule-backed fixture content.

**`.planning/`:**
- Purpose: Planning, milestone, and execution context for GSD workflows.
- Generated: No.
- Committed: Yes.

---

*Structure analysis: 2026-04-11*
