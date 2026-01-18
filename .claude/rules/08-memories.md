# Memories (Historical Decisions and Lessons Learned)

This file contains important historical decisions, bug fixes, and lessons learned that inform future development.

## General Practices
- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings

## Rust Integration
- **Direct module imports**: Import individual Rust modules directly (e.g., `import classic_yaml`, `import classic_scanlog`)
- **Facade removed** (2025-11-01): classic-core facade eliminated - Python imports individual modules for cleaner PyO3 integration
- **ONE RUNTIME RULE**: All Rust crates use `classic_shared::get_runtime()` to share global Tokio runtime
- **PyO3 module registration**: `#[pyclass]` types ONLY export from standalone cdylib modules
- **Standalone module pattern**: Each Rust crate exporting Python classes must have `crate-type = ["cdylib", "rlib"]`
- **GIL handling for parallel work**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in worker threads (PyO3 0.27)
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context

## Architecture Decisions
- **Business logic separation** (2025-10-08): ALL new Rust code MUST separate business logic (`-core` crates) from Python bindings (`-py` crates)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
- **Slint AsyncBridge pattern** (2025-10-11): ALWAYS use `AsyncBridge::run_with_ui_update()` for async operations in Slint GUI
- **Rust documentation requirement** (2025-10-23): ALL new Rust code MUST be fully documented. Missing documentation warnings are treated as errors.

## Feature Changes
- **FCX mode read-only** (2025-10-29): FCX mode now operates in read-only mode - it detects configuration issues but never modifies files. All detected issues are reported with current vs. recommended values. Auto-fix functions (`apply_ini_fix_async`, `apply_all_ini_fixes_async`, `ConfigFileCache.set()`) have been removed. Use new detection functions (`detect_ini_issue_async`, `detect_all_ini_issues_async`, `ConfigFileCache.detect_issue()`) for read-only issue detection.

## Directory and Build System
- **Rust directory reorganization** (2025-11-01): All Rust crates moved to `rust/` directory with subdirectories: `foundation/`, `business-logic/`, `python-bindings/`, `ui-applications/`. ALL new Rust crates MUST be created in the appropriate subdirectory. Workspace manifest at `rust/Cargo.toml`. Build scripts (`rebuild_rust.ps1`, `build_all.ps1`) updated to reference new paths.

## AsyncBridge Usage
- **AsyncBridge usage patterns** (2025-11-02, enforced 2025-12-14): AsyncBridge and `create_sync_wrapper()` are ONLY for same-thread GUI contexts and testing. Production CLI code MUST use async-first pattern with single `asyncio.run()` at entry point. **ENFORCEMENT**: Non-GUI production code using AsyncBridge is an architecture violation that must be refactored.
- **AsyncBridge is thread-local**: AsyncBridge stores its event loop in a thread-local variable, so it CANNOT be used in GUI workers that cross threads (e.g., `QRunnable`, `QThread`). For cross-thread workers, use `asyncio.run()` instead to create a new event loop in the worker thread.
- **Three-tier import classification**:
  - **Tier 1 (Core)**: `AsyncBridge.py`, `_async_utils/bridge_helpers.py` - Never refactor
  - **Tier 2 (Legitimate)**: Same-thread GUI callbacks, test files, sync adapters for GUI - Keep as-is
  - **Tier 3 (Violation)**: Production CLI paths using AsyncBridge, cross-thread workers using AsyncBridge - Must be refactored
- **Dual interface pattern**: Modules shared by GUI and CLI SHALL provide async methods as primary API (for CLI) and sync wrappers clearly documented as "GUI-only" (for Qt workers).
- **Single event loop rule**: CLI applications SHALL use single `asyncio.run(main())` at entry point; no AsyncBridge or `create_sync_wrapper()` in CLI execution paths.

## Type Hints and Exceptions
- **PyO3 type stubs requirement** (2025-11-04): ALL Python binding crates (`-py` crates) MUST have corresponding `.pyi` stub files for type hints and IDE support. When creating a new Python binding crate or modifying APIs (functions, classes, signatures), the `.pyi` file MUST be created or updated. Stub files are placed in the same directory as the crate (e.g., `rust/python-bindings/classic-yaml-py/classic_yaml.pyi`).
- **Custom Rust exceptions** (2025-11-06): All Rust Python bindings now use custom exception hierarchies that map to Python `ClassicLib.integration.exceptions`. Each `-py` crate defines module-specific exceptions (e.g., `RustYamlError`, `RustYamlIOError`, `RustYamlParseError`) using PyO3's `create_exception!` macro. Error conversion functions (`to_pyerr`) map Rust error variants to appropriate Python exception types for better error handling and debugging. Implemented in: `classic-yaml-py`, `classic-scanlog-py`, `classic-file-io-py`, `classic-database-py`, `classic-config-py`.

## Bug Fixes
- **YAML helper methods fix** (2025-11-21): Fixed `get_string_value`, `get_vec_value`, and `get_hashmap_value` in `classic-yaml-core` to properly navigate YAML hash structures instead of using index notation which returns `BadValue` for missing keys. These methods now match the behavior of `get_setting` by checking if current node is a Hash, creating Yaml::String keys, and using `.get()` to safely retrieve values.
- **Parallel YAML loading order fix** (2025-11-21): Fixed critical bug in `classic-config-core/yamldata.rs` where parallel YAML file loading used `JoinSet::join_next()` which returns tasks in completion order, not spawn order. This caused file contents to be assigned to wrong variables (e.g., game YAML content assigned to main). Replaced with `tokio::join!` macro which preserves the order of results (main, game, ignore) ensuring correct file-to-variable mapping.
