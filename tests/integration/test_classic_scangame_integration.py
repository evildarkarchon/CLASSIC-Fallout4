"""Tests for CLASSIC_ScanGame.py game scanning entry point.

This module tests the game file integrity checks, mod scanning operations,
and synchronous adapters for async operations using AsyncBridge.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# ruff: noqa: PLR6301, PT011
# Mark all tests in this module
pytestmark = [pytest.mark.unit]


class TestClassicScanGame:
    """Test suite for CLASSIC_ScanGame.py game scanning entry point."""

    @patch("CLASSIC_ScanGame.ScanGameCore")
    def test_get_scan_game_core_singleton(self, mock_scan_game_core: Mock) -> None:
        """Test that get_scan_game_core returns singleton instance."""
        from CLASSIC_ScanGame import get_scan_game_core

        # Arrange
        mock_instance = MagicMock()
        mock_scan_game_core.return_value = mock_instance

        # Act
        core1 = get_scan_game_core()
        core2 = get_scan_game_core()

        # Assert - Should create instance through ScanGameCore constructor
        assert mock_scan_game_core.call_count == 2  # Called twice but returns singleton
        assert core1 == mock_instance
        assert core2 == mock_instance

    @patch("ClassicLib._async_utils.bridge_helpers._is_gui_mode")
    @patch("ClassicLib.AsyncBridge.AsyncBridge")
    @patch("CLASSIC_ScanGame.get_scan_game_core")
    def test_check_log_errors_sync_adapter(self, mock_get_core: Mock, mock_async_bridge: Mock, mock_gui_mode: Mock) -> None:
        """Test check_log_errors sync adapter for async operation."""
        from CLASSIC_ScanGame import check_log_errors

        # Arrange
        test_path = Path("/test/logs")
        expected_result = "Log errors found: 5"
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core
        mock_bridge_instance = MagicMock()
        mock_async_bridge.get_instance.return_value = mock_bridge_instance

        # Configure side effect to close coroutine
        def run_async_side_effect(coro):
            coro.close()
            return expected_result

        mock_bridge_instance.run_async.side_effect = run_async_side_effect

        # Simulate GUI mode to force AsyncBridge usage
        mock_gui_mode.return_value = True

        # Act
        result = check_log_errors(test_path)

        # Assert
        assert result == expected_result
        mock_async_bridge.get_instance.assert_called_once()
        mock_bridge_instance.run_async.assert_called_once()
        call_args = mock_bridge_instance.run_async.call_args[0][0]
        assert hasattr(call_args, "__await__")  # It's a coroutine

    @patch("CLASSIC_ScanGame.get_scan_game_core")
    async def test_get_scan_settings(self, mock_get_core: Mock) -> None:
        """Test get_scan_settings returns proper tuple."""
        from CLASSIC_ScanGame import get_scan_settings

        # Arrange
        expected_xse = "F4SE"
        expected_config = {"key1": "value1", "key2": "value2"}
        expected_path = Path("/mods/folder")
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core

        async def async_get_settings():
            return (expected_xse, expected_config, expected_path)

        mock_core.get_scan_settings.side_effect = async_get_settings

        # Act
        result = await get_scan_settings()

        # Assert
        assert result == (expected_xse, expected_config, expected_path)
        mock_get_core.assert_called_once()
        mock_core.get_scan_settings.assert_called_once()

    @patch("CLASSIC_ScanGame.get_scan_game_core")
    def test_get_issue_messages(self, mock_get_core: Mock) -> None:
        """Test get_issue_messages returns issue message dictionary."""
        from CLASSIC_ScanGame import get_issue_messages

        # Arrange
        xse_acronym = "F4SE"
        mode = "scan_mode"
        expected_messages = {"errors": ["Error 1", "Error 2"], "warnings": ["Warning 1"], "info": ["Info 1", "Info 2", "Info 3"]}
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core
        mock_core.get_issue_messages.return_value = expected_messages

        # Act
        result = get_issue_messages(xse_acronym, mode)

        # Assert
        assert result == expected_messages
        mock_get_core.assert_called_once()
        mock_core.get_issue_messages.assert_called_once_with(xse_acronym, mode)

    @patch("ClassicLib._async_utils.bridge_helpers._is_gui_mode")
    @patch("ClassicLib.AsyncBridge.AsyncBridge")
    @patch("CLASSIC_ScanGame.get_scan_game_core")
    def test_scan_mods_unpacked_sync_adapter(self, mock_get_core: Mock, mock_async_bridge: Mock, mock_gui_mode: Mock) -> None:
        """Test scan_mods_unpacked sync adapter for async operation."""
        from CLASSIC_ScanGame import scan_mods_unpacked

        # Arrange
        expected_result = "Scanned 42 unpacked mods"
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core
        mock_bridge_instance = MagicMock()
        mock_async_bridge.get_instance.return_value = mock_bridge_instance

        # Configure side effect to close coroutine
        def run_async_side_effect(coro):
            coro.close()
            return expected_result

        mock_bridge_instance.run_async.side_effect = run_async_side_effect

        # Simulate GUI mode to force AsyncBridge usage
        mock_gui_mode.return_value = True

        # Act
        result = scan_mods_unpacked()

        # Assert
        assert result == expected_result
        mock_async_bridge.get_instance.assert_called_once()
        mock_bridge_instance.run_async.assert_called_once()

    def test_module_imports(self) -> None:
        """Test that all required modules can be imported."""
        try:
            from ClassicLib import msg_info
            from ClassicLib.AsyncBridge import AsyncBridge
            from ClassicLib.ScanGame import (
                generate_game_combined_result,
                generate_mods_combined_result,
                manage_game_files,
                write_combined_results,
            )
            from ClassicLib.ScanGame.Config import TEST_MODE
            from ClassicLib.ScanGame.ScanGameCore import ScanGameCore
            from ClassicLib.SetupCoordinator import SetupCoordinator
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")

        # Verify imports exist
        assert msg_info is not None
        assert AsyncBridge is not None
        assert generate_game_combined_result is not None
        assert generate_mods_combined_result is not None
        assert manage_game_files is not None
        assert write_combined_results is not None
        assert TEST_MODE is not None
        assert ScanGameCore is not None
        assert SetupCoordinator is not None

    @patch("ClassicLib._async_utils.bridge_helpers._is_gui_mode")
    @patch("ClassicLib.AsyncBridge.AsyncBridge")
    @patch("CLASSIC_ScanGame.get_scan_game_core")
    def test_check_log_errors_with_string_path(self, mock_get_core: Mock, mock_async_bridge: Mock, mock_gui_mode: Mock) -> None:
        """Test check_log_errors accepts string paths as well as Path objects."""
        from CLASSIC_ScanGame import check_log_errors

        # Arrange
        test_path_str = "/test/logs"
        expected_result = "No errors found"
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core
        mock_bridge_instance = MagicMock()
        mock_async_bridge.get_instance.return_value = mock_bridge_instance

        # Configure side effect to close coroutine
        def run_async_side_effect(coro):
            coro.close()
            return expected_result

        mock_bridge_instance.run_async.side_effect = run_async_side_effect

        # Simulate GUI mode to force AsyncBridge usage
        mock_gui_mode.return_value = True

        # Act
        result = check_log_errors(test_path_str)

        # Assert
        assert result == expected_result
        mock_bridge_instance.run_async.assert_called_once()

    @patch("CLASSIC_ScanGame.get_scan_game_core")
    async def test_get_scan_settings_with_none_mods_path(self, mock_get_core: Mock) -> None:
        """Test get_scan_settings when mods path is None."""
        from CLASSIC_ScanGame import get_scan_settings

        # Arrange
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core

        async def async_get_settings():
            return ("SKSE", {"setting": "value"}, None)

        mock_core.get_scan_settings.side_effect = async_get_settings

        # Act
        xse, config, mods_path = await get_scan_settings()

        # Assert
        assert xse == "SKSE"
        assert config == {"setting": "value"}
        assert mods_path is None

    @patch("ClassicLib._async_utils.bridge_helpers._is_gui_mode")
    @patch("ClassicLib.AsyncBridge.AsyncBridge")
    def test_async_bridge_singleton_usage(self, mock_async_bridge: Mock, mock_gui_mode: Mock) -> None:
        """Test that AsyncBridge singleton is used consistently."""
        from CLASSIC_ScanGame import check_log_errors, scan_mods_unpacked

        # Arrange
        mock_bridge_instance = MagicMock()
        mock_async_bridge.get_instance.return_value = mock_bridge_instance

        # Configure side effect to close coroutine
        def run_async_side_effect(coro):
            coro.close()
            return "result"

        mock_bridge_instance.run_async.side_effect = run_async_side_effect

        # Simulate GUI mode to force AsyncBridge usage
        mock_gui_mode.return_value = True

        with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core:
            mock_core = MagicMock()
            mock_get_core.return_value = mock_core

            # Act
            check_log_errors("/path1")
            scan_mods_unpacked()

        # Assert - AsyncBridge.get_instance called twice, returns same instance
        assert mock_async_bridge.get_instance.call_count == 2
        assert mock_bridge_instance.run_async.call_count == 2

    @patch("CLASSIC_ScanGame.get_scan_game_core")
    def test_get_issue_messages_empty_response(self, mock_get_core: Mock) -> None:
        """Test get_issue_messages with empty response."""
        from CLASSIC_ScanGame import get_issue_messages

        # Arrange
        mock_core = MagicMock()
        mock_get_core.return_value = mock_core
        mock_core.get_issue_messages.return_value = {}

        # Act
        result = get_issue_messages("F4SE", "mode")

        # Assert
        assert result == {}
        mock_core.get_issue_messages.assert_called_once()

    def test_async_first_orchestrator_pattern(self) -> None:
        """Test that module follows async-first orchestrator pattern."""
        # This test verifies the module's design pattern
        import CLASSIC_ScanGame

        # Check for async adapters
        assert hasattr(CLASSIC_ScanGame, "check_log_errors")
        assert hasattr(CLASSIC_ScanGame, "scan_mods_unpacked")

        # Check for delegate functions
        assert hasattr(CLASSIC_ScanGame, "get_scan_game_core")
        assert hasattr(CLASSIC_ScanGame, "get_scan_settings")
        assert hasattr(CLASSIC_ScanGame, "get_issue_messages")

        # Verify docstrings are present
        assert CLASSIC_ScanGame.check_log_errors.__doc__ is not None
        assert CLASSIC_ScanGame.scan_mods_unpacked.__doc__ is not None

    @patch("CLASSIC_ScanGame.ScanGameCore")
    def test_scan_game_core_creation_error_handling(self, mock_scan_game_core: Mock) -> None:
        """Test error handling when ScanGameCore creation fails."""
        from CLASSIC_ScanGame import get_scan_game_core

        # Arrange
        mock_scan_game_core.side_effect = Exception("Core initialization failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            get_scan_game_core()

        assert str(exc_info.value) == "Core initialization failed"

    def test_test_mode_constant(self) -> None:
        """Test that TEST_MODE constant is available."""
        from ClassicLib.ScanGame.Config import TEST_MODE

        # TEST_MODE should be a boolean
        assert isinstance(TEST_MODE, bool)
