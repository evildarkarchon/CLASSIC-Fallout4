# Spec Delta: test-suite

## MODIFIED Requirements

### Requirement: Centralized Fixture Management

Common fixtures SHALL be centralized in `tests/fixtures/` for consistency and reusability, with clear separation by domain.

#### Scenario: Fixture module organization
- **WHEN** creating fixtures for a domain
- **THEN** fixtures MUST be placed in the appropriate module:
  - `async_fixtures.py` for event loop management
  - `crash_log_fixtures.py` for crash log content and files
  - `data_fixtures.py` for general test data creation
  - `database_fixtures.py` for database pool and connection fixtures
  - `mock_fixtures.py` for external dependency mocking
  - `qt_fixtures.py` for GUI test support
  - `registry_fixtures.py` for singleton management
  - `rust_fixtures.py` for Rust-specific test infrastructure
  - `stress_fixtures.py` for stress testing helpers and utilities
  - `yamldata_fixtures.py` for yamldata and scanloginfo mocks

#### Scenario: YamlData fixture variants
- **WHEN** testing components that use yamldata
- **THEN** the appropriate variant from `yamldata_fixtures.py` MUST be used:
  - `mock_yamldata` - Rust-compatible, full attributes (default)
  - `mock_yamldata_simple` - Minimal for unit tests not calling Rust
  - `mock_yamldata_with_data` - Populated mod detection data
- **AND** `mock_yamldata` MUST have all attributes as proper Python types (not Mock objects)
- **AND** Rust integration tests MUST use `mock_yamldata` for PyO3 compatibility

#### Scenario: Crash log fixture variants
- **WHEN** testing crash log parsing
- **THEN** the appropriate fixture from `crash_log_fixtures.py` MUST be used:
  - `sample_crash_log_content` - Standard crash log string
  - `sample_crash_log_minimal` - Minimal valid crash log
  - `sample_crash_log_malformed` - Invalid crash log for error tests
  - `crash_log_file` - Single crash log file (uses tmp_path)
  - `crash_log_directory` - Multiple crash log files
  - `crash_log_large` - Large crash log for stress testing

#### Scenario: Fixture scope selection
- **WHEN** defining a fixture scope
- **THEN** the appropriate scope MUST be selected:
  - `scope="session"` for expensive, read-only shared resources
  - `scope="function"` for test isolation (default)
- **AND** session-scoped fixtures MUST be treated as read-only

### Requirement: No Fixture Duplication

Fixtures SHALL be defined in exactly one location to ensure consistency and reduce maintenance burden.

#### Scenario: Single definition rule
- **WHEN** a fixture is needed across multiple test domains
- **THEN** the fixture MUST be defined in `tests/fixtures/`
- **AND** domain conftest.py files MUST import from `tests/fixtures/`
- **AND** no domain conftest.py SHALL redefine centralized fixtures

#### Scenario: Fixture shadowing prohibited
- **WHEN** a fixture name exists in `tests/fixtures/`
- **THEN** domain conftest.py files MUST NOT define a fixture with the same name
- **AND** any existing duplicates MUST be removed or renamed

#### Scenario: Domain-specific fixture location
- **WHEN** a fixture is only used within a single test domain
- **THEN** the fixture MAY be defined in the domain's conftest.py
- **AND** the fixture MUST NOT duplicate any centralized fixture

### Requirement: Conftest File Size Limits

Domain conftest.py files SHALL be kept under 200 lines to maintain readability and encourage fixture centralization.

#### Scenario: Maximum conftest size
- **WHEN** creating or modifying a domain conftest.py
- **THEN** the file MUST NOT exceed 200 lines of code
- **AND** files approaching 150 lines SHOULD extract fixtures to `tests/fixtures/`

#### Scenario: Root conftest structure
- **WHEN** examining `tests/conftest.py`
- **THEN** the file MUST primarily consist of imports from `tests/fixtures/`
- **AND** configuration hooks (pytest_configure, pytest_collection_modifyitems) MAY be included
- **AND** the file SHOULD NOT exceed 150 lines

### Requirement: Rust Compatibility for Fixtures

Fixtures used in Rust integration tests SHALL provide proper Python types compatible with PyO3 type conversion.

#### Scenario: Rust-compatible mock attributes
- **WHEN** creating fixtures for Rust integration tests
- **THEN** all attributes MUST be proper Python types (str, list, dict, etc.)
- **AND** Mock objects MUST NOT be used for attributes that cross FFI boundary
- **AND** the fixture docstring MUST indicate Rust compatibility

#### Scenario: Rust environment fixtures
- **WHEN** testing Rust components that need YAML configuration
- **THEN** `rust_yaml_files` fixture MUST create minimal valid YAML files
- **AND** `mock_rust_yaml_environment` MUST patch ResourceLoader and GlobalRegistry
- **AND** fixtures MUST be placed in `tests/fixtures/rust_fixtures.py`

## ADDED Requirements

### Requirement: Fixture Documentation

Centralized fixtures SHALL be documented in `tests/fixtures/README.md`.

#### Scenario: README content
- **WHEN** examining `tests/fixtures/README.md`
- **THEN** the file MUST include:
  - Purpose of each fixture module
  - Rust compatibility guidelines
  - Usage examples for common scenarios
  - Fixture hierarchy and scope information

#### Scenario: Fixture docstrings
- **WHEN** defining a fixture
- **THEN** the fixture MUST have a docstring explaining:
  - Purpose of the fixture
  - Return type
  - Use cases (e.g., "Use for Rust integration tests")
  - Any Rust compatibility notes

### Requirement: Stress Fixture Separation

Stress testing helper classes and fixtures SHALL be centralized in `tests/fixtures/stress_fixtures.py`.

#### Scenario: Stress helper classes
- **WHEN** examining `tests/fixtures/stress_fixtures.py`
- **THEN** the file MUST contain helper classes:
  - `MemoryTracker` - Memory usage monitoring
  - `ConcurrencyTestHelper` - Thread safety testing
  - `StressDataGenerator` - Large dataset generation
  - `PerformanceProfiler` - Performance monitoring

#### Scenario: Stress fixture availability
- **WHEN** writing stress tests
- **THEN** the following fixtures MUST be available:
  - `memory_tracker` - Session-scoped memory tracking
  - `fresh_memory_tracker` - Function-scoped memory tracking
  - `concurrency_helper` - Thread contention testing
  - `stress_data_generator` - Large data generation
  - `performance_profiler` - Performance monitoring

## REMOVED Requirements

None - this change only modifies and adds requirements.
