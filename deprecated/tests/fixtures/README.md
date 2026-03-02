# Test Fixtures

This directory contains centralized fixtures for the CLASSIC test suite. All fixtures are imported via the root `tests/conftest.py` and are automatically available to all tests.

## Fixture Modules

### `yamldata_fixtures.py`
Fixtures for mock yamldata and scanloginfo objects.

| Fixture | Description | Use For |
|---------|-------------|---------|
| `mock_yamldata` | Rust-compatible yamldata with full attributes | Rust integration, parity tests, orchestrator tests |
| `mock_yamldata_simple` | Minimal yamldata mock | Unit tests not calling Rust FFI |
| `mock_yamldata_with_data` | Yamldata with populated mod detection data | Mod detection, suspect scanning tests |
| `mock_yamldata_python_only` | Mock that disables Rust acceleration | Stress tests with complex mocking |
| `mock_scanlog_info` | Class-based mock with dict-like access | Tests needing realistic class structure |

**Rust Compatibility**: `mock_yamldata` must have all attributes as proper Python types (not Mock objects) for PyO3 type conversion.

### `crash_log_fixtures.py`
Fixtures for crash log content and files.

| Fixture | Description |
|---------|-------------|
| `sample_crash_log_content` | Standard crash log string with all sections |
| `sample_crash_log_lines` | Crash log as list of lines |
| `sample_crash_log_minimal` | Minimal valid crash log |
| `sample_crash_log_malformed` | Invalid crash log for error tests |
| `crash_log_file` | Temporary crash log file |
| `crash_log_directory` | Directory with multiple crash logs |
| `crash_log_samples` | Dict of small/medium/large crash logs |

### `rust_fixtures.py`
Fixtures for Rust integration testing.

| Fixture | Description |
|---------|-------------|
| `rust_yaml_files` | Creates YAML files for Rust YamlData initialization |
| `mock_rust_yaml_environment` | Patches environment for Rust orchestrator tests |
| `performance_timer` | Timer class for performance benchmarking |
| `mock_formid_dataset` | Comprehensive FormID test data |
| `mock_plugin_dataset` | Comprehensive plugin test data |
| `initialized_database_pool` | Real database pool for integration tests |
| `mock_orchestrator` | Mock orchestrator with async methods |

### `stress_fixtures.py`
Fixtures and utilities for stress testing.

| Fixture | Description |
|---------|-------------|
| `memory_tracker` | Session-scoped memory tracking |
| `fresh_memory_tracker` | Function-scoped memory tracking |
| `concurrency_helper` | Thread safety and race condition testing |
| `stress_data_generator` | Large dataset generation |
| `performance_profiler` | CPU/IO profiling during tests |
| `large_crash_log` | 50MB crash log file |
| `massive_plugin_list` | 500 plugins for stress testing |

**Helper Classes**:
- `MemoryTracker` - Memory leak detection
- `ConcurrencyTestHelper` - Race condition testing
- `StressDataGenerator` - Large dataset creation
- `PerformanceProfiler` - Performance monitoring

### `scanlog_fixtures.py`
Fixtures for ScanLog orchestrator and parser testing.

| Fixture | Description |
|---------|-------------|
| `mock_database_pool` | Mock database pool for FormID testing |
| `mock_database_pool_with_data` | Pool with sample FormID lookups |
| `mock_orchestrator_dependencies` | Bundled dependencies for orchestrator |
| `mock_file_io` | Mock file I/O operations |
| `mock_parser` | Mock crash log parser |
| `patch_scanlog_dependencies` | Patch context managers for integration |

### Other Modules

- `async_fixtures.py` - Event loop and async cleanup
- `data_fixtures.py` - General test data creation
- `database_pool_fixtures.py` - Database pool fixtures
- `mock_fixtures.py` - External dependency mocking
- `qt_fixtures.py` - PySide6/Qt GUI test support
- `registry_fixtures.py` - Singleton management
- `version_cache_fixtures.py` - Version cache testing

## Usage Guidelines

### Fixture Selection

1. **For Rust integration tests**: Use `mock_yamldata` (Rust-compatible)
2. **For simple unit tests**: Use `mock_yamldata_simple`
3. **For stress tests with mocking**: Use `mock_yamldata_python_only`
4. **For crash log content**: Use fixtures from `crash_log_fixtures.py`

### Rust Compatibility

When testing Rust components, fixtures must provide proper Python types:

```python
# GOOD - Rust can convert these
mock.game_ignore_plugins = []  # list
mock.game_version = "1.10.163"  # str

# BAD - Rust cannot convert Mock objects
mock.game_ignore_plugins = MagicMock()  # Will fail at FFI boundary
```

### Fixture Scope

- `scope="session"` - Expensive, read-only shared resources
- `scope="function"` (default) - Test isolation

Session-scoped fixtures must be treated as read-only.

## Adding New Fixtures

1. Determine the appropriate module based on domain
2. Add fixture with type hints and docstrings
3. Document in this README
4. If Rust-related, ensure proper type conversion
