"""
Test fixtures module for CLASSIC-Fallout4 test suite.

This module provides organized fixtures for testing, split by category
for better maintainability and discoverability.

All fixtures are centralized here according to .claude/rules/09-test-fixtures.md.
"""

# Re-export all fixtures for backward compatibility
from tests.fixtures.async_fixtures import *  # noqa: F403
from tests.fixtures.backup_fixtures import *  # noqa: F403
from tests.fixtures.concurrency_fixtures import *  # noqa: F403
from tests.fixtures.crash_log_fixtures import *  # noqa: F403
from tests.fixtures.data_fixtures import *  # noqa: F403
from tests.fixtures.database_pool_fixtures import *  # noqa: F403
from tests.fixtures.fcx_fixtures import *  # noqa: F403
from tests.fixtures.game_fixtures import *  # noqa: F403
from tests.fixtures.gui_settings_fixtures import *  # noqa: F403
from tests.fixtures.io_fixtures import *  # noqa: F403
from tests.fixtures.mock_fixtures import *  # noqa: F403
from tests.fixtures.mods_fixtures import *  # noqa: F403
from tests.fixtures.parity_fixtures import *  # noqa: F403
from tests.fixtures.performance_fixtures import *  # noqa: F403
from tests.fixtures.qt_fixtures import *  # noqa: F403
from tests.fixtures.registry_fixtures import *  # noqa: F403
from tests.fixtures.rust_fixtures import *  # noqa: F403
from tests.fixtures.scanlog_fixtures import *  # noqa: F403
from tests.fixtures.stress_fixtures import *  # noqa: F403
from tests.fixtures.version_cache_fixtures import *  # noqa: F403
from tests.fixtures.yamldata_fixtures import *  # noqa: F403

__all__ = [
    # Async fixtures
    "async_cleanup",
    "clean_event_loop",
    "event_loop_policy",
    # Backup fixtures
    "backup_manager",
    "backup_mock_config",
    "backup_test_game_dir",
    # Concurrency fixtures
    "concurrency_test_worker",
    "concurrency_test_worker_long",
    "concurrency_create_test_logs",
    "ThreadTestWorker",
    # Data fixtures
    "cached_test_files",
    "sample_crash_logs_dir",
    "temp_game_installation",
    "sample_ini_files",
    # Game fixtures
    "game_integrity_checker",
    "game_mock_config",
    "game_test_exe",
    "game_test_steam_ini",
    # GUI settings fixtures
    "gui_settings_mock_cache",
    "gui_settings_app",
    "gui_settings_dialog",
    "gui_settings_reset",
    "MockSettingsCache",
    "TestWindowMock",
    # IO fixtures
    "io_file_core",
    "io_temp_file",
    "io_temp_binary_file",
    "io_temp_crash_log",
    "io_temp_files_set",
    "io_sample_text_file",
    "io_sample_binary_file",
    "io_empty_file",
    # Mock fixtures
    "mock_yaml_settings",
    "mock_network_responses",
    "mock_registry_entries",
    # Mods fixtures
    "mods_empty_fragment",
    "mods_sample_yaml_dict",
    "mods_sample_conflict_dict",
    "mods_sample_important_dict",
    "mods_sample_crashlog_plugins",
    "mods_empty_crashlog_plugins",
    # Parity fixtures
    "parity_crash_generator",
    "parity_mock_yaml_cache",
    "parity_sample_crash_data",
    "parity_mock_scanlog_info",
    "parity_async_bridge",
    "ParityResult",
    "ParityTestCase",
    "ParityValidator",
    "CrashLogParityGenerator",
    "ParityMockYamlSettingsCache",
    "ParityTestRunner",
    # Performance fixtures
    "perf_sample_crash_logs_dir",
    "perf_test_logs",
    "perf_small_test_logs",
    "perf_minimal_test_logs",
    # Qt fixtures
    "qt_application",
    "qt_parent_widget",
    "gui_message_handler",
    "mock_qt_dialogs",
    # Registry fixtures
    "setup_global_registry_session",
    "setup_global_registry",
    "mock_global_registry",
    "init_message_handler_fixture",
    # ScanLog fixtures
    "sample_crash_log_content",
    "sample_crash_log_lines",
    "malformed_crash_log_content",
    "minimal_crash_log_content",
    "crash_log_file",
    "malformed_crash_log_file",
    "crash_logs_directory",
    "mock_yamldata",
    "mock_database_pool",
    "mock_database_pool_with_data",
    "segment_boundaries",
    "expected_segments",
    "mock_orchestrator_dependencies",
    "mock_file_io",
    "mock_parser",
    "patch_scanlog_dependencies",
    # YAML fixtures
    "yaml_async_core",
    "yaml_temp_file",
]
