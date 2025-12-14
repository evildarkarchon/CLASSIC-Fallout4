# test-suite Spec Delta

## ADDED Requirements

### Requirement: ScanLog Package Test Coverage

The ScanLog package SHALL have comprehensive test coverage for its core parsing, orchestration, and execution components.

#### Scenario: Parser module has unit tests
- **WHEN** examining `tests/scanlog/parser/`
- **THEN** unit tests MUST exist for:
  - `parse_crash_header()` function
  - `extract_segments()` function
  - `extract_module_names()` function
  - `find_segments()` Rust-accelerated function
- **AND** tests MUST cover both success and error paths

#### Scenario: Parser module has Rust parity tests
- **WHEN** Rust acceleration is available
- **THEN** parity tests MUST validate Python/Rust output equivalence
- **AND** tests MUST be placed in `tests/scanlog/parser/test_parser_parity.py`
- **AND** tests MUST be marked with `@pytest.mark.rust`

#### Scenario: OrchestratorCore has async tests
- **WHEN** examining `tests/scanlog/orchestrator/`
- **THEN** tests MUST exist for:
  - Async context manager behavior (`__aenter__`, `__aexit__`)
  - Module initialization (`_initialize_modules_async`)
  - Error handling for missing dependencies
- **AND** tests MUST be marked with `@pytest.mark.asyncio`

#### Scenario: ScanLogsExecutor has unit tests
- **WHEN** examining `tests/scanlog/executor/`
- **THEN** unit tests MUST exist for:
  - Configuration loading
  - Settings extraction
  - Resource warm-up
  - Statistics tracking
- **AND** tests MUST be marked with `@pytest.mark.unit`

#### Scenario: ScanLog coverage minimum threshold
- **WHEN** measuring ScanLog package coverage
- **THEN** coverage MUST be at least 70%
- **AND** critical modules (Parser, OrchestratorCore, Executor) MUST have 80%+ coverage

### Requirement: ScanLog Test Fixtures

The test suite SHALL provide centralized fixtures for ScanLog testing in `tests/fixtures/scanlog_fixtures.py`.

#### Scenario: Crash log fixtures exist
- **WHEN** testing ScanLog components
- **THEN** fixtures MUST be available for:
  - `sample_crash_log` - Realistic crash log content
  - `malformed_crash_log` - Error handling test data
  - `mock_yamldata` - ClassicScanLogsInfo mock
  - `mock_database_pool` - FormID database mock

#### Scenario: Fixtures are reusable
- **WHEN** creating ScanLog fixtures
- **THEN** fixtures MUST be placed in `tests/fixtures/scanlog_fixtures.py`
- **AND** fixtures MUST be importable via `from tests.fixtures.scanlog_fixtures import *`

## MODIFIED Requirements

### Requirement: Required Marker System

All tests MUST be annotated with appropriate pytest markers to enable selective test execution and CI categorization.

#### Scenario: Test type markers are applied
- **WHEN** writing a test
- **THEN** one of the following type markers MUST be applied:
  - `@pytest.mark.unit` - Fast, isolated tests (< 100ms)
  - `@pytest.mark.integration` - Tests with external dependencies
  - `@pytest.mark.e2e` - End-to-end workflow tests

#### Scenario: Component markers are applied
- **WHEN** a test targets a specific component type
- **THEN** the appropriate component marker MUST be applied:
  - `@pytest.mark.asyncio` - Async tests using pytest-asyncio
  - `@pytest.mark.gui` - GUI-dependent tests (Qt/PySide6)
  - `@pytest.mark.rust` - Tests validating Rust integration
  - `@pytest.mark.database` - Tests interacting with databases

#### Scenario: Performance markers are applied
- **WHEN** a test measures performance or timing
- **THEN** the `@pytest.mark.performance` marker MUST be applied
- **AND** `@pytest.mark.slow` if execution time exceeds 1 second
- **AND** `@pytest.mark.timing` if test is time-sensitive

#### Scenario: Marker compliance enforcement
- **WHEN** a test file is created or modified
- **THEN** at least one type marker (`unit`, `integration`, or `e2e`) MUST be present
- **AND** CI MAY warn or fail for files without required markers
- **AND** the test collection SHALL report unmarked test files

### Requirement: Test Coverage Targets

Test coverage SHALL meet minimum thresholds.

#### Scenario: Coverage requirements
- **WHEN** measuring test coverage
- **THEN** the following minimums MUST be met:
  - Overall project: 90%+ line coverage
  - New code: 95%+ required
  - Critical modules: 95%+ required
  - GUI components: 70%+ (due to GUI testing limitations)
  - **ScanLog package: 70%+ required**
  - **ScanLog critical modules (Parser, OrchestratorCore, Executor): 80%+ required**
