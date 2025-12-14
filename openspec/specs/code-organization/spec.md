# code-organization Specification

## Purpose
TBD - created by archiving change remove-deprecated-imports. Update Purpose after archive.
## Requirements
### Requirement: Canonical Import Paths for File I/O
ClassicLib SHALL provide file I/O functionality through the `ClassicLib.FileIO` module.

#### Scenario: File I/O imports use FileIO module
- **WHEN** file I/O functionality is needed
- **THEN** imports MUST come from `ClassicLib.FileIO` or `ClassicLib.FileIO.Async`

### Requirement: Canonical Import Paths for YAML Settings
ClassicLib SHALL provide YAML settings functionality exclusively through the `ClassicLib.YamlSettings` module. No backward compatibility aliases SHALL be maintained.

#### Scenario: YAML settings imports use YamlSettings module
- **WHEN** YAML settings functionality is needed
- **THEN** imports MUST come from `ClassicLib.YamlSettings` or `ClassicLib.YamlSettings.async_`

#### Scenario: Backward compatibility module removed
- **WHEN** code attempts to import from `ClassicLib.YamlSettingsCache`
- **THEN** an ImportError SHALL be raised

#### Scenario: Test mock paths use canonical module
- **WHEN** tests need to mock YAML settings functionality
- **THEN** patches MUST use `ClassicLib.YamlSettings` as the module path, not legacy aliases

### Requirement: Canonical Import Paths for Async Utilities
ClassicLib SHALL provide async utility functionality through the `ClassicLib.Utils.Async` module.

#### Scenario: Async utilities imports use Utils.Async module
- **WHEN** async utility functionality is needed
- **THEN** imports MUST come from `ClassicLib.Utils.Async`

### Requirement: Canonical MessageTarget Enum Values
The MessageTarget enum SHALL use canonical values: `ALL`, `GUI`, `CONSOLE`, `LOG_ONLY`.

#### Scenario: MessageTarget uses canonical enum values
- **WHEN** message targeting is needed
- **THEN** code MUST use canonical values: `ALL`, `GUI`, `CONSOLE`, `LOG_ONLY`

### Requirement: Direct Rust Module Imports
Rust modules SHALL be imported directly by their specific module names.

#### Scenario: Direct Rust module imports
- **WHEN** Rust module functionality is needed
- **THEN** code MUST import specific modules directly (e.g., `import classic_scanlog`, `import classic_yaml`)

### Requirement: No Legacy Import Aliases for Core Modules
Core functionality modules that have been migrated to new canonical paths SHALL NOT maintain backward compatibility import aliases beyond their migration period. This includes:
- YAML settings: `ClassicLib.YamlSettings` (no `ClassicLib.YamlSettingsCache`)
- File I/O: `ClassicLib.FileIO` (no legacy aliases)
- Async utilities: `ClassicLib.Utils.Async` (no legacy aliases)
- Utils: `ClassicLib.Utils` (no `ClassicLib.Util`)

#### Scenario: Removed import alias raises ImportError
- **WHEN** code imports from a removed legacy alias path
- **THEN** Python SHALL raise `ImportError` or `ModuleNotFoundError`

#### Scenario: Migration documentation provided
- **WHEN** a legacy import alias is removed
- **THEN** the change proposal MUST include a migration guide with old-to-new import mappings

### Requirement: Canonical Import Paths for Utils
ClassicLib SHALL provide utility functionality exclusively through the `ClassicLib.Utils` module and its submodules. No backward compatibility aliases SHALL be maintained.

#### Scenario: Utils imports use canonical submodule paths
- **WHEN** utility functionality is needed
- **THEN** imports MUST come from `ClassicLib.Utils` or specific submodules:
  - `ClassicLib.Utils.string_utils` for string manipulation (normalize_list, append_or_extend)
  - `ClassicLib.Utils.path_utils` for path operations (validate_path, remove_readonly)
  - `ClassicLib.Utils.file_utils` for file operations (calculate_file_hash, calculate_similarity, open_file_with_encoding)
  - `ClassicLib.Utils.version_utils` for version handling (get_game_version, crashgen_version_gen)
  - `ClassicLib.Utils.logging_utils` for logging setup (configure_logging)
  - `ClassicLib.Utils.web_utils` for network operations (pastebin_fetch, async_pastebin_fetch)

#### Scenario: Backward compatibility module removed
- **WHEN** code attempts to import from `ClassicLib.Util`
- **THEN** an ImportError SHALL be raised

#### Scenario: Test mock paths use canonical module
- **WHEN** tests need to mock utility functionality
- **THEN** patches MUST use `ClassicLib.Utils` submodule paths, not the legacy `ClassicLib.Util` alias

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

### Requirement: Strategy Pattern for Multi-Strategy Components
Components with multiple behavioral strategies (e.g., path resolution, acceleration detection) SHALL use the Strategy pattern for organization.

#### Scenario: ResourceLoader path strategies
- **WHEN** ResourceLoader resolves resource paths
- **THEN** each path resolution strategy SHALL be a separate class implementing a common protocol
- **AND** strategies SHALL be located in `ResourceLoader/strategies/` subdirectory

#### Scenario: Strategy selection
- **WHEN** a component needs to select a strategy
- **THEN** strategy selection logic SHALL be separate from strategy implementation
- **AND** the main component SHALL act as a facade coordinating strategies

### Requirement: Utility Function Extraction
Standalone utility functions that do not depend on class state SHALL be extractable to dedicated utility modules.

#### Scenario: AsyncBridge helper functions
- **WHEN** AsyncBridge contains standalone helper functions (e.g., `run_async`, `smart_await`)
- **THEN** these functions MAY be extracted to `Utils/Async/` submodules
- **AND** the AsyncBridge module SHALL re-export them for backward compatibility

#### Scenario: Helper function import paths
- **WHEN** utility functions are extracted from a class module
- **THEN** both the original import path and the new canonical path SHALL work
- **AND** the original path SHALL be maintained via re-exports in `__init__.py`

### Requirement: GUI Widget Component Extraction
Large GUI widget files SHALL be split into focused component widgets.

#### Scenario: ResultsViewer widget extraction
- **WHEN** `Interface/ResultsViewerWidgets.py` contains multiple distinct widgets
- **THEN** each widget SHALL be extracted to `Interface/ResultsViewer/<widget>.py`
- **AND** `Interface/ResultsViewer/__init__.py` SHALL re-export all widgets

#### Scenario: Widget dependency management
- **WHEN** extracted widgets have shared dependencies
- **THEN** shared code SHALL be placed in a common module within the widget directory
- **AND** circular imports SHALL be avoided using TYPE_CHECKING imports

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

### Requirement: Type Ignore Comments Must Use Specific Error Codes
All `# type: ignore` comments in production code SHALL include specific mypy/pyright error codes. Bare `# type: ignore` comments without error codes are prohibited.

#### Scenario: Type ignore with specific error code
- **WHEN** a type ignore comment is necessary
- **THEN** the comment MUST include at least one specific error code
- **AND** the format SHALL be `# type: ignore[error-code]` or `# type: ignore[code1, code2]`

#### Scenario: Bare type ignore rejected
- **WHEN** code contains a bare `# type: ignore` without error codes
- **THEN** static analysis SHALL report an error
- **AND** CI pipeline SHALL fail until specific error codes are added

#### Scenario: Multiple error codes documented
- **WHEN** a line triggers multiple type errors that must be ignored
- **THEN** all error codes SHALL be listed: `# type: ignore[arg-type, return-value]`

### Requirement: Type Ignore Comments Require Justification for Non-Trivial Cases
Type ignore comments for complex cases (attr-defined, union-attr, no-any-return) SHALL include a brief comment explaining why the ignore is necessary.

#### Scenario: Complex type ignore with explanation
- **WHEN** a type ignore uses error codes `[attr-defined]`, `[union-attr]`, or `[no-any-return]`
- **THEN** the comment SHOULD include a brief explanation
- **AND** the format MAY be `# type: ignore[attr-defined]  # Qt signal type`

#### Scenario: Simple type ignore without explanation
- **WHEN** a type ignore uses straightforward error codes like `[assignment]` for conditional imports
- **THEN** no additional explanation is required

### Requirement: Broad Exception Handlers Limited to Specific Contexts
The use of `except Exception` (or bare `except:`) SHALL be limited to specific contexts: GUI thread workers, top-level entry points, and cleanup operations. All other exception handlers MUST use specific exception types.

#### Scenario: GUI worker uses broad exception handler
- **WHEN** a Qt worker thread handles exceptions
- **THEN** `except Exception` MAY be used
- **AND** the handler MUST include `# noqa: BLE001` comment
- **AND** the handler SHOULD log the exception before handling

#### Scenario: Top-level entry point uses broad exception handler
- **WHEN** `CLASSIC_Interface.py` or `CLASSIC_ScanLogs.py` main function handles exceptions
- **THEN** `except Exception` MAY be used for graceful shutdown
- **AND** the exception MUST be logged with full traceback

#### Scenario: Business logic uses specific exception types
- **WHEN** exception handling is needed in business logic (ScanLog, FileIO, Database)
- **THEN** specific exception types MUST be used (e.g., `FileNotFoundError`, `ValueError`, `RustYamlError`)
- **AND** `except Exception` SHALL NOT be used

#### Scenario: Rust fallback with specific exception hierarchy
- **WHEN** code catches Rust extension exceptions
- **THEN** specific Rust exception types SHOULD be caught first (e.g., `RustYamlError`, `RustScanlogError`)
- **AND** only after specific Rust exceptions MAY a broader handler be used with documentation

### Requirement: Pass Statements Must Have Explicit Purpose
All `pass` statements in production code SHALL either be replaced with proper implementations or include a comment explaining their purpose.

#### Scenario: Abstract method placeholder
- **WHEN** a method is intended to be abstract but not using ABC
- **THEN** `raise NotImplementedError("Subclass must implement")` SHALL be used instead of `pass`

#### Scenario: Intentional no-operation
- **WHEN** a `pass` statement represents an intentional no-op (e.g., empty except handler that swallows errors)
- **THEN** a comment MUST explain why no action is needed
- **AND** the format SHALL be `pass  # Intentionally empty: <reason>`

#### Scenario: Incomplete implementation
- **WHEN** a `pass` statement represents incomplete code
- **THEN** it SHALL be replaced with a proper implementation
- **OR** include a TODO comment with issue reference: `pass  # TODO(#123): Implement X`

### Requirement: Dynamic Code Patterns Must Be Documented
Use of dynamic code execution patterns (`globals()`, `eval()`, `exec()`) in production code SHALL be documented and justified.

#### Scenario: Globals usage for feature detection
- **WHEN** `globals()` is used to check for available functions (e.g., Rust module detection)
- **THEN** the usage MUST include a comment explaining the pattern
- **AND** alternative approaches (e.g., `hasattr()`, try/except import) SHOULD be considered

#### Scenario: Eval/exec prohibited
- **WHEN** production code needs dynamic execution
- **THEN** `eval()` and `exec()` SHALL NOT be used
- **AND** alternatives like `getattr()`, dispatch tables, or plugin systems SHALL be used instead

