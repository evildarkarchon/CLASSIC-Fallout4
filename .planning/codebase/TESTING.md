# Testing Patterns

**Analysis Date:** 2026-01-29

## Test Framework

**Runner:**
- pytest 9.0.2+
- Config file: `pyproject.toml` (`[tool.pytest.ini_options]`)
- Async support: `pytest-asyncio` with `asyncio_mode = "auto"`

**Assertion Library:**
- pytest built-in assertions (no external library)
- `pytest.raises()` for exception testing
- `assert` statements with clear messages

**Test Markers (pyproject.toml):**
- `@pytest.mark.unit` - Fast unit tests with mocked dependencies (< 100ms)
- `@pytest.mark.integration` - Tests with real I/O and multiple components
- `@pytest.mark.e2e` - Full workflow tests from entry point to output
- `@pytest.mark.asyncio` - Tests using async/await patterns
- `@pytest.mark.slow` - Tests taking > 1 second
- `@pytest.mark.gui` - GUI component tests requiring Qt/PySide6
- `@pytest.mark.tui` - Textual TUI interface tests
- `@pytest.mark.performance` - Performance benchmarks and regression tests
- `@pytest.mark.rust` - Tests requiring Rust integration
- `@pytest.mark.snapshot` - Visual snapshot regression tests
- `@pytest.mark.stress` - Comprehensive stress tests (also marks subtypes: memory, concurrency, error_recovery, data_volume)
- `@pytest.mark.network` - Tests requiring network connectivity
- `@pytest.mark.database` - Tests interacting with databases

**Run Commands:**
```bash
# All tests with coverage
uv run pytest

# Quick unit tests only
uv run pytest -m "unit and not slow"

# Integration tests
uv run pytest -m "integration"

# Skip slow/performance tests (CI environments)
uv run pytest -m "not slow and not performance"

# Single test file
uv run pytest tests/path/to/test_file.py -v

# Single test function
uv run pytest tests/path/to/test_file.py::test_function -v

# With coverage report
uv run pytest --cov --cov-report=lcov:lcov.info --cov-report=term
```

**Timeout:**
- Global timeout: 300 seconds (5 minutes) per test
- Override per test: `@pytest.mark.timeout(seconds)`
- CI environment: Skips performance/benchmark tests automatically

## Test File Organization

**Location:**
- Domain-driven directory structure in `tests/` mirroring `ClassicLib/` structure
- Examples:
  - `tests/async_tests/` - Async utilities and patterns
  - `tests/async_resources/` - Resource management for async code
  - `tests/core/` - Core functionality
  - `tests/database/` - Database operations
  - `tests/integration/` - Multi-component integration
  - `tests/fixtures/` - All test fixtures (centralized)
  - `tests/tui/` - TUI-specific tests
  - `tests/gui/` - GUI component tests
  - `tests/benchmarks/` - Performance benchmarks

**Naming:**
- `test_<component>_<type>.py` pattern
- Types: `unit`, `integration`, `e2e`, `performance`, `stress`
- Examples:
  - `test_async_bridge_wrapper_unit.py`
  - `test_async_bridge_failure_modes_integration.py`
  - `test_async_orchestrator_e2e.py`
  - `test_rust_ffi_performance.py`

**Test Classes:**
- Group related tests in classes: `class TestAsyncBridgeWrapper:`
- One test class per logical component
- Inherit from `object` (or nothing) - don't inherit from unittest.TestCase

## Test Structure

**Suite Organization:**
```python
"""Module-level docstring describing test purpose."""

from __future__ import annotations

import asyncio
import pytest

# Global marker
pytestmark = [pytest.mark.unit]

class TestComponentName:
    """Test class for component functionality."""

    def test_function_basic(self, fixture_name):
        """Test description (first line is summary).

        Extended description if needed explaining setup or context.

        Args:
            fixture_name: Description of fixture used
        """
        # Arrange
        expected = "value"

        # Act
        result = function_under_test()

        # Assert
        assert result == expected
```

**Patterns:**
- Arrange-Act-Assert (AAA) pattern for unit tests
- Setup fixtures for test initialization
- Teardown/cleanup via fixture generators (`yield`)
- One assertion focus per test (when possible)
- Test names describe what is being tested: `test_function_wrapper_basic`, `test_nested_async_calls`

## Fixtures

**Location:**
- ALL fixtures in `tests/fixtures/` directory (REQUIRED)
- Never add fixtures to individual test files
- Central fixture modules by domain:
  - `async_fixtures.py` - Async resource tracking, event loops
  - `crash_log_fixtures.py` - Crash log content and parsing
  - `database_pool_fixtures.py` - Database pool management
  - `game_fixtures.py` - Game detection and configuration
  - `io_fixtures.py` - File I/O operations
  - `mock_fixtures.py` - Common mocks and patches
  - `registry_fixtures.py` - GlobalRegistry configuration
  - `rust_fixtures.py` - Rust FFI mocking and availability checks
  - `scanlog_fixtures.py` - Parser and orchestrator fixtures
  - `yaml_fixtures.py` - YAML settings and configuration
  - `yamldata_fixtures.py` - YamlData objects
  - And more by domain...

**Fixture Patterns:**
```python
@pytest.fixture
def simple_fixture():
    """Simple fixture returning a value."""
    return "value"

@pytest.fixture
async def async_fixture():
    """Async fixture for async tests."""
    resource = await setup()
    yield resource
    await cleanup(resource)

@pytest.fixture
def fixture_with_request(request):
    """Fixture with access to test metadata."""
    # request.node.name - test function name
    # request.param - parametrized value
    return setup(request)

@pytest.fixture(scope="session")
def session_fixture():
    """Session-scoped fixture (shared across all tests)."""
    return expensive_setup()

@pytest.fixture(scope="function", autouse=True)
def auto_cleanup():
    """Auto-used cleanup fixture - runs for every test."""
    yield
    cleanup()
```

**Conftest Pattern:**
- Global `tests/conftest.py` imports all fixture modules
- Directory-specific `conftest.py` allowed ONLY for `autouse=True` fixtures
- Example: `tests/stress/conftest.py` wraps centralized cleanup
- No test discovery in conftest files

**Fixture Imports:**
```python
# tests/conftest.py - Global fixture setup
from tests.fixtures.async_fixtures import *  # noqa: F403
from tests.fixtures.crash_log_fixtures import *  # noqa: F403
from tests.fixtures.database_pool_fixtures import *  # noqa: F403
# ... etc for each fixture module
```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
```python
# Simple mock
from unittest.mock import Mock, MagicMock
mock_obj = Mock()
mock_obj.method.return_value = "result"

# Async mock
from unittest.mock import AsyncMock
mock_async = AsyncMock()
mock_async.return_value = "result"
await mock_async()

# Patch decorator
@patch('module.path.to.function')
def test_with_patch(mock_function):
    mock_function.return_value = "mocked"

# Patch context manager
with patch('module.path.to.function') as mock_func:
    mock_func.return_value = "mocked"
    result = function_under_test()
    assert result == "mocked"

# Side effects
mock_func.side_effect = lambda x: x * 2

# Call assertions
mock_func.assert_called_once()
mock_func.assert_called_with(arg1, arg2)
mock_func.assert_called_once_with(expected_arg)
```

**AsyncBridge Mocking (CRITICAL):**
- For sync functions using AsyncBridge: Mock `bridge.run_async()`, NOT the async function
- Pattern: `bridge.run_async.return_value = "result"`
- Do NOT use AsyncMock for methods called through AsyncBridge
- Prevents RuntimeWarning about unawaited coroutines
- Exception: Mock the async function only if testing pure async code

**Example AsyncBridge Test:**
```python
def test_function_with_async_bridge(async_bridge):
    """Test sync wrapper using AsyncBridge."""
    async def async_operation(x):
        return x * 2

    def sync_wrapper(x):
        return async_bridge.run_async(async_operation(x))

    # Mock the bridge's run_async method
    async_bridge.run_async = Mock(return_value=10)

    # Call the function
    result = sync_wrapper(5)

    # Verify
    assert result == 10
    async_bridge.run_async.assert_called_once()
```

**What to Mock:**
- External dependencies: file I/O, network, databases
- Expensive operations: YAML file loads, Rust FFI calls
- Non-deterministic behavior: timestamps, randomness, system info
- AsyncBridge in sync wrapper tests (NOT the async function)
- Global singletons (GlobalRegistry, MessageHandler) between tests

**What NOT to Mock:**
- Code under test
- Simple utility functions
- Built-in functions (unless testing error handling)
- Async functions in pure async tests (use real coroutines)
- Internal async calls within async functions

## Fixtures and Factories

**Test Data Fixtures:**
```python
# Location: tests/fixtures/crash_log_fixtures.py
@pytest.fixture
def sample_crash_log() -> str:
    """Return a valid crash log sample."""
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512
"""

# Usage in tests
def test_parse_crash_log(sample_crash_log):
    result = parse_log(sample_crash_log)
    assert "EXCEPTION_ACCESS_VIOLATION" in str(result)
```

**Mock Factories:**
```python
# Location: tests/fixtures/mock_fixtures.py
@pytest.fixture
def mock_yaml_settings_patch():
    """Mock YAML settings with side effects."""
    with patch("ClassicLib.io.yaml.yaml_settings") as mock:
        def side_effect(_type, store, key, value=None):
            if key == "setting_name":
                return "setting_value"
            return None
        mock.side_effect = side_effect
        yield mock
```

## Coverage

**Requirements:** 80% minimum (enforced)

**Configuration:** `pyproject.toml` `[tool.coverage.run]`
- Source: Everything except venv, build, test, release directories
- Branch coverage: Enabled
- Omit patterns: `*/tests/*`, `*/_internal/*`, `install_requirements.py`, etc.

**View Coverage:**
```bash
# Generate coverage report
uv run pytest --cov --cov-report=html

# View in browser
open htmlcov/index.html
```

**Excluded from Coverage:**
- Protocol stubs and type checking blocks
- `if __name__ == "__main__":` blocks
- `raise NotImplementedError` (abstract methods)
- `if sys.platform` / `if platform.system()` (platform-specific)

## Test Types and Patterns

**Unit Tests:**
- Scope: Single function/class with all dependencies mocked
- Location: `test_*_unit.py`
- Marker: `@pytest.mark.unit`
- Speed: < 100ms per test
- Database: Mocked
- File I/O: Mocked
- Network: Mocked
- Async: Real async/await if testing async, use AsyncBridge.run_async() for sync wrappers

**Integration Tests:**
- Scope: Multiple components working together
- Location: `test_*_integration.py`
- Marker: `@pytest.mark.integration`
- Real I/O allowed but controlled (temp files)
- Real async patterns
- May use real databases with transactions/rollback

**E2E Tests:**
- Scope: Full workflow from entry point to output
- Location: `test_*_e2e.py`
- Marker: `@pytest.mark.e2e`
- Real file I/O and temporary data
- Test complete user workflows
- Example: `test_async_orchestrator_e2e.py` tests full log scanning

**Async Testing:**
```python
# Pure async test (use real await)
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with real coroutines."""
    result = await async_function()
    assert result == expected

# Sync wrapper with AsyncBridge
def test_sync_wrapper(async_bridge):
    """Test sync function that uses AsyncBridge."""
    async_bridge.run_async = Mock(return_value="result")
    result = sync_wrapper()
    assert result == "result"
```

**Performance Tests:**
```python
@pytest.mark.performance
@pytest.mark.benchmark
def test_parsing_performance(benchmark):
    """Measure parsing performance."""
    result = benchmark(parse_function, large_input)
    assert result is not None
```

**Stress Tests:**
```python
@pytest.mark.stress
@pytest.mark.concurrency
async def test_concurrent_operations():
    """Test system under concurrent load."""
    tasks = [operation() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 100
```

**Snapshot Tests (TUI):**
```python
@pytest.mark.snapshot
def test_tui_appearance(snap_compare):
    """Test TUI visual output consistency."""
    assert snap_compare(
        "path/to/app.py",
        terminal_size=(120, 40),
        press=["1"],  # Simulate key press
    )
```

**GUI Tests:**
```python
@pytest.mark.gui
def test_widget_rendering(qtbot):
    """Test Qt widget behavior."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    assert widget.isVisible() is True
```

## Common Patterns

**Async Resource Tracking:**
```python
# Location: tests/fixtures/async_fixtures.py
class AsyncResourceTracker:
    """Track async resources to detect leaks."""

    def register(self, resource, name="Unknown"):
        """Register a resource for tracking."""

    def check_leaks(self) -> list[str]:
        """Check for leaked resources."""

# Usage
def test_no_resource_leaks(async_cleanup_tracker):
    """Verify no resources are leaked."""
    tracker = async_cleanup_tracker
    # ... test code ...
    leaked = tracker.check_leaks()
    assert len(leaked) == 0
```

**Async Context Managers:**
```python
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager pattern."""
    async with AsyncComponent() as component:
        assert component.initialized
    assert component.cleaned_up
```

**Error Testing:**
```python
def test_handles_io_error():
    """Test error handling for I/O failures."""
    with patch("builtins.open", side_effect=OSError("File not found")):
        with pytest.raises(OSError):
            read_file("nonexistent.txt")

def test_handles_value_error():
    """Test error handling for invalid values."""
    with pytest.raises(ValueError, match="Invalid format"):
        parse_invalid_data()
```

**Parametrization:**
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
    ("edge_case", None),
])
def test_validate_input(input, expected):
    """Test validation with multiple inputs."""
    result = validate(input)
    assert result == expected
```

**Fixture Dependencies:**
```python
@pytest.fixture
def setup_database(temp_db):
    """Fixture that depends on another fixture."""
    db = temp_db
    db.initialize()
    return db

def test_with_dependency(setup_database):
    """Test using dependent fixture."""
    result = setup_database.query()
    assert result is not None
```

## CI/CD Integration

**Automated Test Skipping:**
- CI environment detection: `CI=true` environment variable
- Auto-skips: Performance, stress, benchmark, timing tests
- Command-line options:
  - `--skip-slow` - Skip tests marked slow
  - `--skip-network` - Skip network tests
  - `--skip-performance` - Skip performance tests
  - `--skip-stress` - Skip all stress subtypes

**Test Output:**
- Coverage report: LCOV format (`lcov.info`)
- Terminal coverage summary included in test output
- HTML report generated: `htmlcov/`

---

*Testing analysis: 2026-01-29*
