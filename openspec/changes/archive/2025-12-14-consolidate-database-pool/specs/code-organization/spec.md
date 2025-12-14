# code-organization Spec Delta

## ADDED Requirements

### Requirement: Canonical Import Paths for Database Pool
ClassicLib SHALL provide database pool functionality through the `ClassicLib.Database` module with clear separation between Python fallback and Rust-accelerated implementations.

#### Scenario: Database pool imports use Database module
- **WHEN** database pool functionality is needed
- **THEN** imports MUST come from `ClassicLib.Database` or use the factory `ClassicLib.integration.factory.get_database_pool()`

#### Scenario: Pool implementation selection via factory
- **WHEN** production code needs a database pool instance
- **THEN** code SHOULD use `get_database_pool()` factory function
- **AND** the factory SHALL return `RustAsyncDatabasePool` when Rust acceleration is available
- **AND** the factory SHALL return `AsyncDatabasePool` when Rust is unavailable

#### Scenario: Singleton pool manager access
- **WHEN** code needs to manage pool lifecycle (initialization, cleanup)
- **THEN** code MUST use `DatabasePoolManager` from `ClassicLib.Database`
- **AND** there SHALL be only one `DatabasePoolManager` implementation in the codebase

#### Scenario: Backward compatibility during migration
- **WHEN** code imports from deprecated paths (`ClassicLib.ScanLog.AsyncUtil.DatabasePoolManager`, `ClassicLib.rust.database_rust.DatabasePoolManager`)
- **THEN** imports SHALL work with a `DeprecationWarning`
- **AND** warnings MUST indicate the new canonical import path

### Requirement: Database Module Structure
The `ClassicLib/Database/` package SHALL organize database pool implementations with single-responsibility modules.

#### Scenario: Module file organization
- **WHEN** the Database package is organized
- **THEN** it SHALL contain:
  - `pool_manager.py` - Single `DatabasePoolManager` singleton class
  - `async_pool.py` - Pure Python `AsyncDatabasePool` implementation
  - `rust_pool.py` - Rust-wrapped `RustAsyncDatabasePool` implementation
  - `__init__.py` - Public API re-exports

#### Scenario: No duplicate singleton managers
- **WHEN** database pool singleton management is needed
- **THEN** there SHALL be exactly one `DatabasePoolManager` class definition
- **AND** it SHALL reside in `ClassicLib/Database/pool_manager.py`

## MODIFIED Requirements

### Requirement: Single Responsibility File Organization
Each Python source file SHALL contain a single primary class or a cohesive set of closely related functions. Files exceeding 500 lines MUST be reviewed for potential extraction of distinct responsibilities. Database pool functionality SHALL be separated from file I/O utilities.

#### Scenario: Database pool separation from AsyncUtil
- **WHEN** `ClassicLib/ScanLog/AsyncUtil.py` is refactored
- **THEN** database pool classes (`DatabasePoolManager`, `AsyncDatabasePool`) SHALL be extracted to `ClassicLib/Database/`
- **AND** `AsyncUtil.py` SHALL retain only file I/O operations (`read_file_async`, `write_file_async`, `load_crash_logs_async`, `batch_file_operations`)
- **AND** `AsyncUtil.py` line count SHALL be reduced to under 200 lines

### Requirement: Rust Wrapper Module Organization
Rust wrapper modules in `ClassicLib/rust/` SHALL separate Rust bindings from Python fallback implementations. Database pool Rust wrappers MUST be consolidated into `ClassicLib/Database/` to eliminate duplication.

#### Scenario: Database Rust wrapper consolidation
- **WHEN** `ClassicLib/rust/database_rust.py` contains duplicate classes
- **THEN** `RustAsyncDatabasePool` SHALL be moved to `ClassicLib/Database/rust_pool.py`
- **AND** `DatabasePoolManager` SHALL be removed (use `ClassicLib/Database/pool_manager.py`)
- **AND** `database_rust.py` SHALL be reduced to a deprecation shim or removed entirely
