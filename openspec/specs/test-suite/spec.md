# Test Suite Specification

## Purpose

Define the testing infrastructure, standards, and patterns for the CLASSIC project. The test suite provides comprehensive coverage for a hybrid Python-Rust application analyzing crash logs from Bethesda games, supporting parallel execution, singleton isolation, Rust/Python parity validation, and stress testing for production readiness.

**Key Metrics:**
- 217 test modules across 30 directories
- ~15,000+ lines of test code
- 28+ custom pytest markers
- Centralized fixture architecture in `tests/fixtures/`
## Requirements
### Requirement: Domain-Driven Directory Structure

Tests SHALL be organized in domain-driven directories under `tests/` that reflect the application's architecture and concern areas.

#### Scenario: Root-level test categories exist
- **WHEN** examining the test directory structure
- **THEN** domain-specific directories exist for:
  - `async_tests/` - Async patterns, AsyncBridge, database pools
  - `async_resources/` - Resource lifecycle and cleanup
  - `core/` - Core business logic (MessageHandler, FormID, path validation)
  - `scanning/` - Log scanning and mod detection
  - `game/` - Platform-specific game path detection
  - `settings/` - YAML settings and configuration
  - `performance/` - Benchmarks and regression tests
  - `stress/` - Memory, concurrency, and scalability tests
  - `rust_integration/` - Rust FFI parity and memory safety
  - `gui/` - PySide6/Qt GUI components
  - `integration/` - Cross-component workflows

#### Scenario: Centralized fixtures directory exists
- **WHEN** examining `tests/fixtures/`
- **THEN** domain-specific fixture modules exist for:
  - `async_fixtures.py` - Event loop and async resource management
  - `data_fixtures.py` - Test files, crash logs, game structures
  - `mock_fixtures.py` - YAML, network, registry mocks
  - `registry_fixtures.py` - Singleton management
  - `qt_fixtures.py` - Qt/PySide6 GUI fixtures
  - `database_pool_fixtures.py` - Database connection management

### Requirement: Test File Naming Convention

Test files SHALL follow a consistent naming pattern that identifies the component and test type.

#### Scenario: Standard test file naming
- **WHEN** creating a new test file
- **THEN** the file MUST be named `test_<component>_<type>.py` where:
  - `<component>` identifies the module or feature being tested
  - `<type>` optionally indicates the test type (unit, integration, parity)
- **AND** examples include:
  - `test_message_handler.py` - Core component tests
  - `test_async_bridge_adapters_unit.py` - Unit tests for specific aspect
  - `test_formid_parity.py` - Rust/Python parity tests

#### Scenario: Test class naming
- **WHEN** creating a test class
- **THEN** the class MUST be named `Test<Component><Aspect>`
- **AND** examples include: `TestMessageHandler`, `TestAsyncBridgeAdapter`, `TestMemoryTracker`

#### Scenario: Test method naming
- **WHEN** creating a test method
- **THEN** the method MUST be named `test_<functionality>_<scenario>[_<aspect>]`
- **AND** examples include: `test_async_bridge_basic`, `test_thread_safe_concurrent_access`

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

### Requirement: Stress Testing Markers

Stress tests SHALL have specific markers for test categorization and selective execution.

#### Scenario: Stress test categories
- **WHEN** writing a stress test
- **THEN** the `@pytest.mark.stress` marker MUST be applied
- **AND** one of the following category markers:
  - `@pytest.mark.memory` - Memory usage and leak detection
  - `@pytest.mark.concurrency` - Thread safety and race conditions
  - `@pytest.mark.error_recovery` - Error handling validation
  - `@pytest.mark.data_volume` - Large dataset scalability

### Requirement: Automatic Marker Application

The test framework SHALL automatically apply markers based on test path patterns.

#### Scenario: Path-based auto-marking
- **WHEN** pytest collects tests
- **THEN** auto-marking rules apply:
  - Tests with "async" in path receive `@pytest.mark.asyncio`
  - Tests with "gui/qt/pyside/widget/dialog" receive `@pytest.mark.gui`
  - Tests with "performance/benchmark/perf" receive `@pytest.mark.performance`
  - Tests with "stress" receive `@pytest.mark.stress` plus category markers

### Requirement: Centralized Fixture Management

Common fixtures SHALL be centralized in `tests/fixtures/` for consistency and reusability.

#### Scenario: Fixture module organization
- **WHEN** creating fixtures for a domain
- **THEN** fixtures MUST be placed in the appropriate module:
  - `async_fixtures.py` for event loop management
  - `data_fixtures.py` for test data creation
  - `mock_fixtures.py` for external dependency mocking
  - `registry_fixtures.py` for singleton management
  - `qt_fixtures.py` for GUI test support

#### Scenario: Fixture scope selection
- **WHEN** defining a fixture scope
- **THEN** the appropriate scope MUST be selected:
  - `scope="session"` for expensive, read-only shared resources
  - `scope="function"` for test isolation (default)
- **AND** session-scoped fixtures MUST be treated as read-only

### Requirement: Singleton Isolation

Tests SHALL properly isolate singleton state to prevent test pollution.

#### Scenario: MessageHandler cleanup
- **WHEN** a test uses MessageHandler
- **THEN** `init_message_handler_fixture` or `ensure_message_handler_cleanup` MUST be used
- **AND** the singleton state MUST be restored after the test

#### Scenario: GlobalRegistry isolation
- **WHEN** a test modifies GlobalRegistry
- **THEN** `setup_global_registry` or `mock_global_registry` fixture MUST be used
- **AND** registry state MUST be properly reset after the test

#### Scenario: Thread-safe singleton management
- **WHEN** tests run in parallel with pytest-xdist
- **THEN** thread-local state tracking MUST be used for singleton isolation
- **AND** stack-based restoration MUST ensure proper cleanup order

### Requirement: Read-Only Cached Test Files

Session-scoped test files SHALL be treated as read-only to prevent cross-test contamination.

#### Scenario: Cached test files usage
- **WHEN** using `cached_test_files` fixture
- **THEN** tests MUST NOT modify the returned files
- **AND** tests needing modifications MUST use `tmp_path` fixture instead

#### Scenario: Test file creation
- **WHEN** a test needs to create files
- **THEN** the `tmp_path` fixture MUST be used for function-scoped isolation
- **AND** the `tmp_path_factory` MAY be used for custom scope

### Requirement: Async Test Patterns

Async tests SHALL follow established patterns for proper event loop handling.

#### Scenario: Basic async test
- **WHEN** writing an async test
- **THEN** use `async def test_*()` with `@pytest.mark.asyncio` marker
- **AND** never call `asyncio.run()` inside the test function

#### Scenario: Async resource cleanup
- **WHEN** async tests create resources
- **THEN** `async_cleanup` fixture SHOULD be used for tracking
- **AND** resources MUST be added via `async_cleanup.append(resource)`
- **AND** cleanup runs automatically in fixture teardown

#### Scenario: Event loop policy
- **WHEN** tests require specific event loop configuration
- **THEN** platform-specific policies MUST be applied:
  - Windows: `asyncio.WindowsProactorEventLoopPolicy()`
  - Other: `asyncio.DefaultEventLoopPolicy()`

### Requirement: Rust Parity Validation

Tests SHALL validate that Rust implementations produce identical results to Python implementations.

#### Scenario: Parity test structure
- **WHEN** testing Rust/Python parity
- **THEN** tests MUST be placed in `tests/rust_integration/`
- **AND** both implementations MUST be called with identical inputs
- **AND** outputs MUST be compared for exact or semantic equality

#### Scenario: Rust extension handling
- **WHEN** Rust extensions may not be available
- **THEN** `pytest.importorskip("classic_*")` MUST be used to skip gracefully
- **AND** fallback behavior MUST be tested separately

### Requirement: Memory Safety Testing

FFI boundary operations SHALL be tested for memory safety under stress.

#### Scenario: FFI boundary stress test
- **WHEN** testing FFI operations
- **THEN** memory safety tests MUST validate:
  - No memory leaks during repeated operations
  - Proper reference counting across boundary
  - Thread safety for concurrent FFI calls

#### Scenario: Rust acceleration disable
- **WHEN** testing Python-only code paths
- **THEN** `disable_rust_acceleration` autouse fixture MUST be available
- **AND** monkeypatching disables Rust module availability

### Requirement: Stress Test Categories

Stress tests SHALL cover memory, concurrency, performance, and error recovery.

#### Scenario: Memory stress tests
- **WHEN** testing memory behavior
- **THEN** tests MUST validate:
  - Memory growth < 10% during sustained operations
  - No memory leaks detected by `MemoryTracker`
  - Large dataset handling (100k+ items)

#### Scenario: Concurrency stress tests
- **WHEN** testing thread safety
- **THEN** tests MUST validate:
  - No race conditions in 1000+ iteration tests
  - Proper behavior under high contention (20-30 threads)
  - Atomic operations remain consistent

#### Scenario: Error recovery stress tests
- **WHEN** testing error handling
- **THEN** tests MUST validate:
  - Recovery rate > 90% from cascading failures
  - Malformed data handled gracefully
  - System returns to stable state after errors

### Requirement: Stress Test Reporting

Stress tests SHALL generate comprehensive reports for production readiness assessment.

#### Scenario: Report generation
- **WHEN** running stress test suite
- **THEN** `StressTestReporter` SHALL generate reports
- **AND** reports MAY be in JSON, HTML, or Markdown format
- **AND** reports MUST include production readiness criteria

### Requirement: Performance Baseline Management

Performance tests SHALL maintain and validate against established baselines.

#### Scenario: Baseline establishment
- **WHEN** establishing performance baselines
- **THEN** baselines MUST be stored in versioned format
- **AND** baselines MUST include execution time, throughput, memory usage

#### Scenario: Regression detection
- **WHEN** performance tests run
- **THEN** results MUST be compared against baselines
- **AND** significant regressions MUST fail the test
- **AND** response time variance > 50% triggers failure

### Requirement: CI Performance Considerations

Performance tests SHALL handle CI environment limitations.

#### Scenario: Timing test skip in CI
- **WHEN** running timing-sensitive tests in CI
- **THEN** tests with `@pytest.mark.timing` MAY be skipped
- **AND** skip detection uses `CI` environment variable

### Requirement: Qt Test Infrastructure

GUI tests SHALL use proper Qt fixture infrastructure.

#### Scenario: Qt application setup
- **WHEN** testing Qt/PySide6 components
- **THEN** `qt_application` fixture MUST provide QApplication instance
- **AND** `qt_parent_widget` MAY provide parent widget for component tests
- **AND** `mock_qt_dialogs` MAY mock dialog interactions

#### Scenario: Offscreen rendering
- **WHEN** running GUI tests in CI
- **THEN** `QT_QPA_PLATFORM=offscreen` environment MUST be set
- **AND** tests MUST NOT require visible display

### Requirement: Test Coverage Targets

Test coverage SHALL meet minimum thresholds.

#### Scenario: Coverage requirements
- **WHEN** measuring test coverage
- **THEN** the following minimums MUST be met:
  - Overall project: 90%+ line coverage
  - New code: 95%+ required
  - Critical modules: 95%+ required
  - GUI components: 70%+ (due to GUI testing limitations)

### Requirement: Test Documentation

Tests SHALL be documented following project standards.

#### Scenario: Test function documentation
- **WHEN** writing a test function
- **THEN** complex tests SHOULD have docstrings describing what is being tested
- **AND** test method names MUST be descriptive of the scenario

### Requirement: Parallel Test Execution

Tests SHALL support parallel execution via pytest-xdist.

#### Scenario: Parallel-safe tests
- **WHEN** tests run with `-n auto`
- **THEN** tests MUST NOT share mutable global state
- **AND** file operations MUST use unique paths per worker
- **AND** singleton fixtures MUST use thread-local isolation

### Requirement: Test Timeouts

Tests SHALL have timeout protection to prevent CI hangs.

#### Scenario: Timeout configuration
- **WHEN** tests run in CI
- **THEN** global timeout of 300 seconds (5 minutes) applies per test
- **AND** unit tests have 300s timeout
- **AND** integration tests have 600s timeout
- **AND** tests MAY define custom timeouts with `@pytest.mark.timeout()`

### Requirement: Test Execution Commands

Standard test execution commands SHALL be documented.

#### Scenario: Common test commands
- **WHEN** running tests
- **THEN** standard commands SHALL work:
  - `uv run pytest -n auto` - All tests, parallel
  - `uv run pytest -m "unit and not slow"` - Quick unit tests
  - `uv run pytest tests/rust_integration/ -v` - Rust tests
  - `uv run pytest tests/stress/ -v` - Stress tests

### Requirement: Test Data Isolation

Tests SHALL NOT modify production data files.

#### Scenario: YAML file protection
- **WHEN** tests need YAML configuration
- **THEN** tests MUST use `YAML.TEST` namespace or mocks
- **AND** production YAML files MUST NOT be modified

#### Scenario: File system isolation
- **WHEN** tests create files
- **THEN** tests MUST use `tmp_path` or similar temp directories
- **AND** tests MUST NOT write to project directories

### Requirement: API Currency

Tests SHALL use current APIs, not deprecated ones.

#### Scenario: Deprecated API usage
- **WHEN** APIs are deprecated
- **THEN** tests MUST be updated to use current APIs
- **AND** backward compatibility SHALL NOT be added to fix tests
- **AND** tests ARE exempt from API stability requirements

### Requirement: Async Mocking

Async operations SHALL be mocked properly to avoid warnings.

#### Scenario: Async mock creation
- **WHEN** mocking async functions
- **THEN** `AsyncMock` MUST be used instead of `Mock`
- **AND** awaitable returns MUST be properly configured
- **AND** no "unawaited coroutine" warnings SHALL occur

### Requirement: Test File Size Limits

Test files SHALL be kept under 500 lines to ensure maintainability, fast failure isolation, and efficient parallel execution.

#### Scenario: Maximum file size enforcement
- **WHEN** creating or modifying a test file
- **THEN** the file SHOULD NOT exceed 500 lines of code
- **AND** files approaching 400 lines SHOULD be considered for splitting

#### Scenario: Splitting strategy for large files
- **WHEN** a test file exceeds 500 lines
- **THEN** the file MUST be split into focused modules
- **AND** each new file SHOULD contain tests for a single logical concern
- **AND** file names MUST clearly indicate the test scope

#### Scenario: Class-per-file guideline
- **WHEN** organizing test classes
- **THEN** each test file SHOULD contain 1-3 related test classes
- **AND** classes exceeding 200 lines SHOULD be considered for extraction
- **AND** shared fixtures MUST be extracted to `tests/fixtures/`

#### Scenario: Naming convention for split files
- **WHEN** splitting a large test file
- **THEN** new files MUST follow the pattern `test_<component>_<aspect>.py`
- **AND** examples include:
  - `test_update_version_parsing.py` - Version parsing tests
  - `test_update_github_api.py` - GitHub API tests
  - `test_stress_formid_volume.py` - FormID volume stress tests

