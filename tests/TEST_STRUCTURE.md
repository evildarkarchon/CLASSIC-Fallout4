# Test Suite Structure Documentation

## Overview
The test suite has been refactored to improve maintainability by splitting large, monolithic test files into smaller, focused modules. This refactoring follows pytest best practices and makes the test suite easier to navigate and maintain.

### Recent Reorganization (2025-09-05)
All 35 root-level test files have been reorganized into logical subdirectories:
- **async_tests/** - 11 async-related test files (renamed from `async/` to avoid Python keyword conflict)
- **core/** - 8 core functionality test files
- **scanning/** - 6 scanning-related test files
- **game/** - 4 game path test files
- **settings/** - 3 YAML/settings test files (plus existing ones)
- **performance/** - 2 performance test files (plus existing ones)
- **concurrency/** - 1 thread safety test file (plus existing ones)

This reorganization improves test discoverability and allows for more targeted test execution.

## Directory Structure

```
tests/
├── conftest.py                      # Shared fixtures and configuration
├── async_tests/                     # Async-related tests (REORGANIZED)
│   ├── test_async_adapters.py      # Sync/async adapter tests
│   ├── test_async_base_patterns.py # AsyncBase pattern tests
│   ├── test_async_caching.py       # Async caching tests
│   ├── test_async_database.py      # AsyncDatabasePool tests
│   ├── test_async_error_handling.py # Error handling tests
│   ├── test_async_file_io.py       # Async file I/O tests
│   ├── test_async_orchestrator.py  # OrchestratorCore tests
│   ├── test_async_pipeline_core.py # Pipeline core tests
│   ├── test_async_util.py          # Async utility tests
│   ├── test_async_utilities.py     # More async utilities
│   └── test_async_utils.py         # Additional async utils
├── core/                            # Core functionality tests (REORGANIZED)
│   ├── test_crash_log_processing.py # Crash log processing tests
│   ├── test_documents_checker.py   # Documents checker tests
│   ├── test_file_generation.py     # File generation tests
│   ├── test_formid_analyzer.py     # FormID analyzer tests
│   ├── test_formid_matching.py     # FormID matching tests
│   ├── test_fragment_migration.py  # Fragment migration tests
│   ├── test_message_handler.py     # MessageHandler tests
│   └── test_path_validator.py      # Path validation tests
├── scanning/                        # Scanning-related tests (REORGANIZED)
│   ├── test_scan_game_integration.py # Game scan integration
│   ├── test_scan_game_wrappers.py  # Synchronous wrappers
│   ├── test_scan_log_errors.py     # Log error checking
│   ├── test_scan_logs.py           # Log scanning tests
│   ├── test_scan_mods_archived.py  # Archive scanning
│   └── test_scan_mods_unpacked.py  # Unpacked mod scanning
├── game/                            # Game path tests (REORGANIZED)
│   ├── test_game_path_generation.py # Path generation tests
│   ├── test_game_path_platform.py  # Platform-specific tests
│   ├── test_game_path_registry.py  # Registry detection tests
│   └── test_game_path_validation.py # Path validation tests
├── settings/                        # YAML settings tests (REORGANIZED)
│   ├── test_async_yaml_core.py     # AsyncYamlSettingsCore tests
│   ├── test_async_yaml_batch.py    # Batch operations tests
│   ├── test_async_yaml_caching.py  # Caching behavior tests
│   ├── test_async_yaml_error_handling.py # Error handling tests
│   ├── test_async_yaml_convenience.py # Convenience functions
│   ├── test_async_yaml_performance.py # Performance tests
│   ├── test_yaml_integration.py    # YAML integration tests
│   ├── test_yaml_settings_cache.py # Settings cache tests
│   └── test_yaml_sync_wrapper.py   # Sync wrapper tests
├── performance/                     # Performance tests (REORGANIZED)
│   ├── test_async_performance.py   # Async performance tests
│   ├── test_detect_mods_performance.py # Mod detection perf
│   ├── test_performance_benchmarks.py # General benchmarks
│   └── test_real_world_performance.py # Real-world perf tests
├── concurrency/                     # Thread safety tests (REORGANIZED)
│   ├── test_thread_safe_log_cache.py # Thread-safe log cache
│   └── [other concurrency tests]
├── async_resources/                 # Async resource management tests
│   ├── conftest.py                # Resource fixtures
│   ├── test_database_pool.py      # Database pool tests
│   ├── test_memory_leak.py        # Memory leak detection
│   ├── test_pipeline_resources.py # Pipeline resource tests
│   └── test_resource_tracker.py   # Resource tracking tests
├── tui/                            # TUI-specific tests (COMPLETED)
│   ├── conftest.py                # TUI-specific fixtures
│   ├── test_main_screen.py        # MainScreen component tests
│   ├── test_help_screen.py        # HelpScreen component tests
│   ├── test_settings_screen.py    # SettingsScreen component tests
│   ├── test_papyrus_screen.py     # PapyrusScreen component tests
│   ├── test_scan_handler.py       # TuiScanHandler tests
│   ├── test_message_handler.py    # TuiMessageHandler tests
│   ├── test_papyrus_handler.py    # TuiPapyrusHandler tests
│   ├── test_keyboard_shortcuts.py # Keyboard interaction tests
│   ├── test_status_bar.py         # StatusBar widget tests
│   ├── test_output_viewer.py      # OutputViewer widget tests
│   ├── test_folder_selector.py    # FolderSelector widget tests
│   ├── test_scan_buttons.py       # ScanButton widget tests
│   ├── test_confirmation_dialogs.py # Dialog widget tests
│   ├── test_papyrus_monitor_widget.py # PapyrusMonitorWidget tests
│   ├── test_workflows.py          # End-to-end workflow tests
│   ├── test_edge_cases.py         # Edge case and boundary tests
│   ├── test_performance.py        # TUI performance benchmarks
│   └── test_concurrency.py        # TUI concurrency tests
├── setup/                          # Setup and initialization tests
│   ├── test_setup_initialization.py # Application initialization
│   ├── test_initial_setup.py      # Initial setup sequence
│   └── test_integrity_checks.py   # Integrity checking
├── documents/                      # Document path and INI tests
│   ├── test_document_manager.py   # DocumentsPathManager tests
│   ├── test_path_detection.py     # Path detection tests
│   ├── test_ini_validation.py     # INI validation tests
│   └── test_public_api.py         # Public API tests
├── backup/                         # Backup-related tests
├── gui/                           # GUI-specific tests
├── io/                            # I/O operation tests
├── mods/                          # Mod-related tests
├── registry/                      # Registry-related tests
├── utils/                         # Utility function tests
└── test_data/                     # Test data files
```

## Refactored Test Files

### 1. test_async_pipeline.py (Refactored)
**Original:** 1666 lines, mixed concerns
**New structure:**
- `test_async_pipeline_core.py` - Core AsyncCrashLogPipeline tests
- `test_async_orchestrator.py` - OrchestratorCore tests
- `test_formid_analyzer.py` - FormID analysis and matching tests
- `test_async_file_io.py` - Async file I/O operations
- `test_async_database.py` - AsyncDatabasePool tests
- `test_async_utilities.py` - Utility function tests
- `performance/test_async_performance.py` - Performance benchmarks
- `performance/test_real_world_performance.py` - Real-world performance tests

### 2. test_async_core.py (Refactored)
**Original:** 693 lines, 12 test classes
**New structure:**
- `test_async_base_patterns.py` - AsyncBase and AsyncProcessor tests
- `test_async_error_handling.py` - Error handling, retry, circuit breaker tests
- `test_async_adapters.py` - Sync/async adapter and hybrid method tests
- `test_async_caching.py` - Cache implementation tests

### 3. test_game_path.py (Refactored)
**Original:** 658 lines, registry detection, path validation, generation
**New structure:**
- `test_game_path_registry.py` (~200 lines) - Windows registry detection tests
- `test_game_path_validation.py` (~250 lines) - Path validation and XSE log parsing
- `test_game_path_generation.py` (~180 lines) - Game folder/file path generation
- `test_game_path_platform.py` (~50 lines) - Cross-platform compatibility tests

### 4. test_async_scan_game.py (Refactored)
**Original:** 599 lines, mixed scanning and wrapper tests
**New structure:**
- `test_scan_mods_archived.py` (~150 lines) - BA2 archive scanning tests
- `test_scan_mods_unpacked.py` (~200 lines) - Unpacked mod file scanning
- `test_scan_log_errors.py` (~100 lines) - Log file error checking
- `test_scan_game_wrappers.py` (~80 lines) - Synchronous wrapper tests
- `test_scan_game_integration.py` (~70 lines) - Integration and performance tests

### 5. test_tui_integration.py (Refactored)
**Original:** 679 lines, 8 test classes
**New structure:**
- `tui/test_main_screen.py` - MainScreen initialization and button tests
- `tui/test_help_screen.py` - HelpScreen navigation tests
- `tui/test_settings_screen.py` - SettingsScreen display and save tests
- `tui/test_papyrus_screen.py` - PapyrusScreen monitoring tests
- `tui/test_scan_handler.py` - TuiScanHandler crash and game scan tests
- `tui/test_message_handler.py` - TuiMessageHandler routing tests
- `tui/test_papyrus_handler.py` - TuiPapyrusHandler monitoring and parsing tests
- `tui/test_keyboard_shortcuts.py` - Application and scan keyboard shortcuts

### 6. test_tui_widgets.py (Refactored)
**Original:** 458 lines, 6 test classes
**New structure:**
- `tui/test_status_bar.py` - StatusBar widget tests
- `tui/test_output_viewer.py` - OutputViewer widget tests
- `tui/test_folder_selector.py` - FolderSelector widget tests
- `tui/test_scan_buttons.py` - ScanButton widget tests
- `tui/test_confirmation_dialogs.py` - Dialog widget tests
- `tui/test_papyrus_monitor_widget.py` - PapyrusMonitorWidget tests

### 7. test_tui_e2e.py (Refactored)
**Original:** 454 lines, mixed workflows and edge cases
**New structure:**
- `tui/test_workflows.py` - Complete user workflows and navigation tests
- `tui/test_edge_cases.py` - Edge cases, boundary conditions, and error handling

### 8. test_tui_performance.py (Moved)
**Original location:** tests/test_tui_performance.py
**New location:** tests/tui/test_performance.py
- Contains TUI-specific performance benchmarks

### 9. test_tui_concurrency.py (Moved)
**Original location:** tests/test_tui_concurrency.py
**New location:** tests/tui/test_concurrency.py
- Contains thread-safety and concurrency tests

### 10. test_setup_coordinator.py (Refactored)
**Original:** 492 lines, mixed setup orchestration
**New structure:**
- `setup/test_setup_initialization.py` (~240 lines) - Application initialization tests
- `setup/test_initial_setup.py` (~160 lines) - Initial setup sequence tests
- `setup/test_integrity_checks.py` (~90 lines) - Integrity checking and results generation

### 11. test_docs_path.py (Refactored)
**Original:** 491 lines, mixed document path handling
**New structure:**
- `documents/test_document_manager.py` (~115 lines) - DocumentsPathManager core functionality
- `documents/test_path_detection.py` (~165 lines) - Platform-specific path detection
- `documents/test_ini_validation.py` (~120 lines) - INI file validation and checking
- `documents/test_public_api.py` (~50 lines) - Public API function tests

### 12. test_async_yaml_settings.py (Refactored)
**Original:** 470 lines, mixed YAML settings tests
**New structure:**
- `settings/test_async_yaml_core.py` (~110 lines) - Basic AsyncYamlSettingsCore tests
- `settings/test_async_yaml_batch.py` (~110 lines) - Batch operations and concurrent access
- `settings/test_async_yaml_caching.py` (~75 lines) - Caching and TTL behavior
- `settings/test_async_yaml_error_handling.py` (~60 lines) - Error handling and recovery
- `settings/test_async_yaml_convenience.py` (~60 lines) - Convenience function tests
- `settings/test_async_yaml_performance.py` (~90 lines) - Performance regression tests

## Benefits of New Structure

### 1. Improved Maintainability
- Each test file focuses on a single concern
- Easier to locate specific tests
- Reduced file size makes navigation simpler

### 2. Better Organization
- Related tests are grouped together
- Performance tests separated into dedicated directory
- Clear separation between unit and integration tests

### 3. Faster Development
- Developers can run specific test modules during development
- Parallel test execution is more efficient with smaller files
- Less cognitive load when working on specific componentsA

## Running Tests

### Run all tests
```bash
uv run pytest tests/ -n 4
```

### Run specific component tests
```bash
# Async tests
uv run pytest tests/async_tests/

# Core functionality tests
uv run pytest tests/core/

# Scanning tests
uv run pytest tests/scanning/

# Game path tests
uv run pytest tests/game/

# Settings and YAML tests
uv run pytest tests/settings/

# Performance tests only
uv run pytest tests/performance/

# Concurrency and thread safety tests
uv run pytest tests/concurrency/

# Setup and initialization tests
uv run pytest tests/setup/

# Document path and INI tests
uv run pytest tests/documents/

# Exclude slow tests
uv run pytest tests/ -m "not slow"
```

### Run tests by marker
```bash
# Integration tests
uv run pytest -m integration

# Async tests
uv run pytest -m asyncio

# Performance benchmarks
uv run pytest -m performance
```

## Test Markers

The following pytest markers are used throughout the test suite:

- `@pytest.mark.asyncio` - Asynchronous test functions
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.performance` - Performance benchmark tests
- `@pytest.mark.gui` - GUI-dependent tests
- `@pytest.mark.unit` - Unit tests

## Shared Fixtures

Common fixtures are defined in `conftest.py`:

- `init_message_handler_fixture` - Initializes MessageHandler for tests
- `cached_test_files` - Provides cached test files to avoid repeated I/O
- `sample_crash_log_content` - Standard crash log content for testing
- `mock_yamldata` - Mock ClassicScanLogsInfo object

## Future Improvements

1. **Add more performance baselines** - Establish baseline metrics for all critical paths
2. **Improve test isolation** - Ensure all tests are fully independent
3. **Add property-based tests** - Use hypothesis for complex input scenarios
4. **Create test utilities module** - Common test helpers and factories
5. **Add snapshot testing** - For complex UI component output

## Notes for Developers

- When adding new tests, place them in the appropriate focused module
- Use descriptive test names that explain what is being tested
- Include docstrings for complex test scenarios
- Add appropriate markers for test categorization
- Keep test files under 500 lines when possible
- Group related tests in classes for better organization

## Known Issues

(None currently - all known issues have been resolved)

## Recently Fixed Issues

- ✅ **test_async_error_handling.py** - Fixed API mismatches with actual AsyncCore implementation
- ✅ **test_formid_analyzer.py** - Clarified that NULL FormID (0x00000000) extraction is intentional - these represent errors/invalid references that users need to investigate
- ✅ **test_real_world_performance.py** - Fixed test isolation violation by using test fixtures instead of production `Crash Logs/` directory
  - Added `conftest.py` with fixtures that create test crash logs from samples
  - Tests now use `performance_test_logs` and `small_performance_test_logs` fixtures
  - Ensures reproducibility and doesn't depend on production data
