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
Each Python source file SHALL contain a single primary class or a cohesive set of closely related functions. Files exceeding 500 lines SHOULD be reviewed for potential extraction of distinct responsibilities.

#### Scenario: Large file triggers review
- **WHEN** a Python file exceeds 500 lines
- **THEN** the file SHOULD be evaluated for responsibility separation
- **AND** distinct responsibilities SHALL be extracted to separate modules

#### Scenario: Multi-class file extraction
- **WHEN** a file contains multiple unrelated classes
- **THEN** each class SHALL be extracted to its own file
- **AND** a package `__init__.py` SHALL re-export all classes for backward compatibility

### Requirement: Rust Wrapper Module Organization
Rust wrapper modules in `ClassicLib/rust/` SHALL separate Rust bindings from Python fallback implementations.

#### Scenario: Fallback code separation
- **WHEN** a Rust wrapper module contains Python fallback code
- **THEN** fallback implementations SHALL be placed in `ClassicLib/rust/fallback/` subdirectory
- **AND** the main wrapper file SHALL remain a thin adapter to Rust bindings

#### Scenario: Multi-class Rust wrapper extraction
- **WHEN** a Rust wrapper file contains multiple classes (e.g., `report_rust.py`)
- **THEN** each class SHALL be extracted to a subdirectory matching the original filename
- **AND** the subdirectory SHALL contain one file per class plus `__init__.py` for re-exports

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

