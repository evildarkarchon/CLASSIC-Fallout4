# Test Suite Design

Technical architecture and patterns for the CLASSIC test infrastructure.

## Directory Architecture

```
tests/
├── conftest.py                 # Root pytest configuration (marker registration, auto-marking)
├── pytest.ini                  # Pytest settings (asyncio_mode=auto, timeout=300)
│
├── fixtures/                   # Centralized fixture modules
│   ├── __init__.py            # Re-exports for backward compatibility
│   ├── async_fixtures.py      # Event loop, async cleanup
│   ├── data_fixtures.py       # Test files, crash logs, game structures
│   ├── database_pool_fixtures.py
│   ├── mock_fixtures.py       # YAML, network, registry mocks
│   ├── qt_fixtures.py         # Qt/PySide6 fixtures
│   ├── registry_fixtures.py   # Singleton management (~737 lines)
│   ├── fcx_fixtures.py        # FCX mode fixtures
│   └── version_cache_fixtures.py
│
├── async_tests/               # AsyncBridge, database pools, orchestrator
├── async_resources/           # Resource lifecycle, cleanup validation
├── core/                      # MessageHandler, FormID, path validation
├── scanning/                  # Log scanning, mod detection
├── game/                      # Platform-specific game detection
├── settings/                  # YAML settings, cache, batch operations
├── performance/               # Benchmarks, regression tests
├── stress/                    # Memory, concurrency, scalability
│   ├── stress_test_fixtures.py   # MemoryTracker, ConcurrencyHelper
│   ├── stress_report_generator.py
│   └── README.md              # Comprehensive documentation
├── rust_integration/          # FFI parity, memory safety (~50 files)
├── gui/                       # PySide6/Qt components
├── integration/               # Cross-component workflows
├── documents/                 # INI validation, path detection
├── edge_cases/               # Boundary conditions
└── test_data/                # Sample data files
```

## Pytest Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto              # Auto-detect async tests
timeout = 300                    # 5-minute global timeout
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### conftest.py Structure
```python
# pytest_configure: Registers 28+ markers
# pytest_collection_modifyitems: Auto-marks tests by path
# pytest_addoption: --run-slow, --run-network flags
# pytest_runtest_setup: CI environment skipping
```

## Fixture Patterns

### Pattern 1: Singleton Management (registry_fixtures.py)

```python
# Thread-local state for parallel execution
_handler_states = threading.local()

@pytest.fixture
def init_message_handler_fixture():
    """Initialize MessageHandler with proper cleanup tracking."""
    if not hasattr(_handler_states, 'handler_stack'):
        _handler_states.handler_stack = []

    # Save current state
    _handler_states.handler_stack.append(current_state)

    yield

    # Restore state from stack
    if _handler_states.handler_stack:
        restore_state(_handler_states.handler_stack.pop())
```

### Pattern 2: Session-Scoped Read-Only Data

```python
@pytest.fixture(scope="session")
def cached_test_files(tmp_path_factory):
    """Create session-scoped test files - READ-ONLY."""
    base_dir = tmp_path_factory.mktemp("test_data")

    files = {
        "crash_log": create_crash_log(base_dir),
        "yaml_settings": create_yaml_file(base_dir),
    }

    return files  # Callers MUST NOT modify these files
```

### Pattern 3: Async Resource Cleanup

```python
@pytest.fixture
async def async_cleanup():
    """Track async resources for cleanup."""
    resources = []

    def track(resource):
        resources.append(resource)

    yield track

    # Cleanup in reverse order
    for resource in reversed(resources):
        if hasattr(resource, 'close'):
            await resource.close()
```

### Pattern 4: Rust Acceleration Disable

```python
@pytest.fixture(autouse=True)
def disable_rust_acceleration(monkeypatch):
    """Force Python fallback for isolated testing."""
    monkeypatch.setattr("ClassicLib.GamePath._HAS_RUST_PATH", False)
    monkeypatch.setattr("ClassicLib.DocsPath._HAS_RUST_PATH", False)
    # Additional modules as needed
```

### Pattern 5: Async Mock Configuration

```python
@pytest.fixture
def mock_yamldata():
    """YAML data mock with RustFFI-compatible string values."""
    return {
        "Game_Folder": "C:\\Games\\Fallout4",  # String, not Path
        "Docs_Folder": "C:\\Users\\Test\\Documents",
        "Version": "1.0.0",
    }
```

## Stress Test Infrastructure

### MemoryTracker Class

```python
class MemoryTracker:
    """Track memory usage during test execution."""

    def start_tracking(self):
        """Begin memory tracking."""
        self.baseline = self._get_memory()
        self.measurements = []

    def take_measurement(self, label: str) -> float:
        """Record current memory usage."""
        current = self._get_memory()
        self.measurements.append((label, current))
        return current

    def stop_tracking(self) -> dict[str, Any]:
        """End tracking and return statistics."""
        return {
            "baseline_mb": self.baseline,
            "peak_mb": max(m[1] for m in self.measurements),
            "growth_pct": self._calculate_growth(),
            "potential_leak": self.growth_pct > 10.0,
        }
```

### ConcurrencyTestHelper Class

```python
class ConcurrencyTestHelper:
    """Helper for concurrent test execution."""

    def __init__(self, num_threads: int = 20):
        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        self.results: list[Any] = []
        self.errors: list[Exception] = []

    def run_concurrent(self, func: Callable, iterations: int = 1000):
        """Run function concurrently and collect results."""
        futures = [
            self.executor.submit(func)
            for _ in range(iterations)
        ]

        for future in as_completed(futures):
            try:
                self.results.append(future.result())
            except Exception as e:
                self.errors.append(e)
```

### Production Readiness Criteria

```python
PRODUCTION_CRITERIA = {
    "memory_growth_max_pct": 10.0,
    "response_time_variance_max_pct": 50.0,
    "race_condition_iterations": 1000,
    "error_recovery_rate_min": 0.90,
    "failure_rate_max_pct": 1.0,
}
```

## Marker Auto-Application

```python
def pytest_collection_modifyitems(config, items):
    """Auto-apply markers based on test path patterns."""
    for item in items:
        path = str(item.fspath)

        # Async tests
        if "async" in path.lower():
            item.add_marker(pytest.mark.async_test)

        # GUI tests
        if any(x in path.lower() for x in ["gui", "qt", "pyside"]):
            item.add_marker(pytest.mark.gui)

        # Performance tests
        if any(x in path.lower() for x in ["performance", "benchmark"]):
            item.add_marker(pytest.mark.performance)

        # Stress tests with category detection
        if "stress" in path.lower():
            item.add_marker(pytest.mark.stress)
            if "memory" in path.lower():
                item.add_marker(pytest.mark.memory)
            if "concurrency" in path.lower():
                item.add_marker(pytest.mark.concurrency)
```

## Event Loop Management

```python
@pytest.fixture(scope="session")
def event_loop_policy():
    """Platform-specific event loop policy."""
    if sys.platform == "win32":
        return asyncio.WindowsProactorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()

@pytest.fixture
def clean_event_loop(event_loop_policy):
    """Ensure clean event loop state per test."""
    asyncio.set_event_loop_policy(event_loop_policy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    loop.close()
```

## Rust Integration Testing Patterns

### Parity Test Structure

```python
@pytest.mark.rust
def test_formid_extraction_parity(sample_crash_log):
    """Validate Rust matches Python implementation."""
    # Python implementation
    python_result = python_extract_formids(sample_crash_log)

    # Rust implementation
    rust_result = classic_scanlog.extract_formids(sample_crash_log)

    # Compare results
    assert python_result == rust_result
```

### Extension Skip Pattern

```python
def test_rust_yaml_operations():
    """Test Rust YAML operations."""
    classic_yaml = pytest.importorskip(
        "classic_yaml",
        reason="Rust extensions not available"
    )

    ops = classic_yaml.RustYamlOperations()
    result = ops.parse("key: value")
    assert result["key"] == "value"
```

## CI Environment Detection

```python
def is_ci_environment() -> bool:
    """Detect CI environment for test behavior adjustment."""
    return os.environ.get("CI", "false").lower() == "true"

def pytest_runtest_setup(item):
    """Skip timing tests in CI."""
    if is_ci_environment():
        if item.get_closest_marker("timing"):
            pytest.skip("Skipping timing test in CI")
```

## Test Execution Reference

```bash
# Standard execution
uv run pytest -n auto                          # All tests, parallel
uv run pytest -n auto -m "unit and not slow"   # Quick unit tests
uv run pytest -m integration                   # Integration tests

# By directory
uv run pytest tests/rust_integration/ -v       # Rust integration
uv run pytest tests/stress/ -v                 # Stress tests
uv run pytest tests/performance/ -v            # Performance tests

# Single test
uv run pytest tests/path/to/test.py::test_function -v

# With options
uv run pytest --run-slow                       # Include slow tests
uv run pytest --run-network                    # Include network tests
uv run pytest -v --tb=short > results.txt 2>&1 # Output to file
```

## Key Dependencies

### Python Testing Stack
- **pytest** - Core test framework
- **pytest-asyncio** - Async test support
- **pytest-xdist** - Parallel execution
- **pytest-timeout** - Test timeout protection
- **pytest-cov** - Coverage reporting

### Mock and Fixture Support
- **unittest.mock** - Standard mocking
- **pytest-mock** - Enhanced mock fixtures

### GUI Testing
- **PySide6** - Qt bindings for GUI tests
- **QT_QPA_PLATFORM=offscreen** - Headless testing
