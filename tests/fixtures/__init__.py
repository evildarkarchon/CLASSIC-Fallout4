"""
Test fixtures module for CLASSIC-Fallout4 test suite.

This module provides organized fixtures for testing, split by category
for better maintainability and discoverability.
"""

# Re-export all fixtures for backward compatibility
from tests.fixtures.async_fixtures import *  # noqa: F403
from tests.fixtures.data_fixtures import *  # noqa: F403
from tests.fixtures.mock_fixtures import *  # noqa: F403
from tests.fixtures.qt_fixtures import *  # noqa: F403
from tests.fixtures.registry_fixtures import *  # noqa: F403
from tests.fixtures.scanlog_fixtures import *  # noqa: F403

__all__ = [
    # Async fixtures
    "async_cleanup",
    "clean_event_loop",
    "event_loop_policy",
    # Data fixtures
    "cached_test_files",
    "sample_crash_logs_dir",
    "temp_game_installation",
    "sample_ini_files",
    # Mock fixtures
    "mock_yaml_settings",
    "mock_network_responses",
    "mock_registry_entries",
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
    "mock_yamldata_async",
    "mock_database_pool",
    "mock_database_pool_with_data",
    "segment_boundaries",
    "expected_segments",
    "mock_orchestrator_dependencies",
    "mock_file_io",
    "mock_parser",
    "patch_scanlog_dependencies",
]
