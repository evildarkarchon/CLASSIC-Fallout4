## ADDED Requirements

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
