# Test Suite Organization

## Overview

The CLASSIC test suite has been reorganized into a domain-driven structure for better maintainability and discoverability. Tests are now grouped by functionality and domain areas rather than by source file.

## Test Directory Structure

```
tests/
├── async_resources/           # Async resource management tests
│   ├── conftest.py
│   ├── test_async_bridge.py
│   ├── test_async_database.py
│   └── test_resource_cleanup.py
│
├── backup/                    # Backup management tests
│   ├── conftest.py
│   ├── test_backup_configuration.py
│   ├── test_backup_creation.py
│   ├── test_backup_metadata.py
│   └── test_backup_workflow.py
│
├── concurrency/              # Thread safety and concurrency tests
│   ├── conftest.py
│   ├── test_race_conditions.py
│   ├── test_thread_manager.py
│   └── test_worker_lifecycle.py
│
├── documents/                # Document path validation tests
│   ├── conftest.py
│   ├── test_document_locations.py
│   ├── test_ini_validation.py
│   └── test_path_cleaning.py
│
├── game/
│   └── integrity/           # Game integrity checking tests
│       ├── conftest.py
│       ├── test_file_validation.py
│       ├── test_integrity_algorithms.py
│       ├── test_integrity_configuration.py
│       └── test_integrity_workflow.py
│
├── gui/
│   └── settings/           # GUI settings dialog tests
│       ├── conftest.py
│       ├── test_apply_settings.py
│       ├── test_load_settings.py
│       ├── test_settings_ui.py
│       └── test_widget_state.py
│
├── io/                      # File I/O operations tests
│   ├── conftest.py
│   ├── test_encoding_detection.py
│   ├── test_file_reading.py
│   └── test_file_writing.py
│
├── mods/                    # Mod detection and analysis tests
│   ├── conftest.py
│   ├── test_conflict_detection.py
│   ├── test_mod_detection.py
│   └── test_mod_metadata.py
│
├── performance/            # Performance and benchmarking tests
│   ├── conftest.py
│   ├── test_benchmarks.py
│   └── test_performance_monitoring.py
│
├── registry/               # Global registry tests
│   ├── conftest.py
│   ├── test_game_detection.py
│   ├── test_mo2_integration.py
│   ├── test_registry_initialization.py
│   └── test_vr_mode.py
│
├── settings/              # Settings and configuration tests
│   ├── conftest.py
│   ├── test_batch_operations.py
│   ├── test_cache_management.py
│   ├── test_setting_access.py
│   └── test_yaml_operations.py
│
└── setup/                 # Application setup tests
    ├── conftest.py
    ├── test_file_generation.py
    ├── test_setup_coordinator.py
    └── test_setup_workflow.py
```

## Test Categories

### Core Functionality
- **async_resources/** - Tests for async/await patterns, resource management
- **io/** - File I/O operations, encoding detection, crash log handling
- **concurrency/** - Thread safety, worker management, race conditions
- **performance/** - Performance monitoring and benchmarking

### Application Features
- **backup/** - Game file backup and restoration
- **documents/** - Document path validation and INI file handling
- **game/integrity/** - Game installation and version checking
- **mods/** - Mod detection, conflict checking, metadata extraction
- **registry/** - Global game registry and MO2 integration
- **settings/** - YAML settings management and caching

### User Interface
- **gui/settings/** - Settings dialog and widget state management

### Setup & Configuration
- **setup/** - Application initialization and file generation

## Running Tests

### Run All Tests
```bash
poetry run python -m pytest tests/ -n auto -v
```

### Run Tests by Category
```bash
# Core functionality tests
poetry run python -m pytest tests/async_resources tests/io tests/concurrency -n 4

# Application feature tests
poetry run python -m pytest tests/backup tests/mods tests/game -n 4

# GUI tests (may require display)
poetry run python -m pytest tests/gui -v

# Performance tests (may take longer)
poetry run python -m pytest tests/performance -v
```

### Run Specific Test Domains
```bash
# Backup system tests
poetry run python -m pytest tests/backup/ -v

# Mod detection tests
poetry run python -m pytest tests/mods/ -v

# Game integrity tests
poetry run python -m pytest tests/game/integrity/ -v
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.asyncio` - Async tests requiring event loop
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.gui` - Tests requiring GUI components
- `@pytest.mark.performance` - Performance regression tests
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests

### Running Tests by Marker
```bash
# Run only unit tests
poetry run python -m pytest -m "unit" -n auto

# Run integration tests
poetry run python -m pytest -m "integration" -v

# Skip slow tests
poetry run python -m pytest -m "not slow" -n auto
```

## Test Fixtures

Each subdirectory contains a `conftest.py` file with shared fixtures specific to that domain. Common fixtures include:

- **async_resources/conftest.py** - Async database connections, event loops
- **backup/conftest.py** - Backup manager instances, mock configurations
- **concurrency/conftest.py** - Qt application, test workers
- **mods/conftest.py** - Sample mod dictionaries, plugin lists
- **settings/conftest.py** - Temporary YAML files, cache instances

## Writing New Tests

When adding new tests:

1. **Choose the Right Location** - Place tests in the subdirectory that best matches the functionality being tested
2. **Use Existing Fixtures** - Check the local `conftest.py` for reusable fixtures
3. **Follow Naming Conventions** - Test files should start with `test_`, test classes with `Test`, test methods with `test_`
4. **Add Appropriate Markers** - Mark tests with relevant pytest markers
5. **Keep Tests Focused** - Each test should verify one specific behavior

## Test Coverage

To run tests with coverage reporting:
```bash
poetry run python -m pytest tests/ --cov=ClassicLib --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## Migration Notes

The test suite was refactored from a flat structure to this domain-driven organization. The refactoring:
- Maintained 100% of existing tests
- Improved test discoverability
- Reduced file sizes (target: 100-200 lines per file)
- Extracted common fixtures to conftest.py files
- Preserved all pytest markers and test functionality

Total test count remains unchanged from the original implementation.
