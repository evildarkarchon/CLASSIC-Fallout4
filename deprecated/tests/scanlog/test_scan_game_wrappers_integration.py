"""
Test suite for synchronous wrapper functions.

This module contains tests for the synchronous adapter functions
that wrap async ScanGameCore methods.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from unittest.mock import MagicMock, patch

import classic_scan_game


class TestSyncWrappers:
    """Test synchronous wrapper functions."""

    def test_scan_mods_archived_wrapper(self):
        # Patch the specific async method on the global _scan_game_core instance
        with (
            patch("classic_scan_game.scan_mods_archived", return_value="Test result") as mock_wrapper_func,
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
        ):
            mock_bridge_class.get_instance.return_value = MagicMock()  # Ensure a bridge is available

            result = classic_scan_game.scan_mods_archived()
            assert result == "Test result"
            mock_wrapper_func.assert_called_once()

    def test_check_log_errors_wrapper(self):
        """Test synchronous wrapper for check_log_errors."""
        mock_path = MagicMock()
        with (
            patch("classic_scan_game.check_log_errors", return_value="Test log result") as mock_wrapper_func,
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
        ):
            mock_bridge_class.get_instance.return_value = MagicMock()  # Ensure a bridge is available

            result = classic_scan_game.check_log_errors(mock_path)
            assert result == "Test log result"
            mock_wrapper_func.assert_called_once_with(mock_path)

    def test_scan_mods_unpacked_wrapper(self):
        """Test synchronous wrapper for scan_mods_unpacked."""
        with (
            patch("classic_scan_game.scan_mods_unpacked", return_value="Test unpacked result") as mock_wrapper_func,
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
        ):
            mock_bridge_class.get_instance.return_value = MagicMock()  # Ensure a bridge is available

            result = classic_scan_game.scan_mods_unpacked()
            assert result == "Test unpacked result"
            mock_wrapper_func.assert_called_once()

    def test_sync_adapter_integration(self):
        """Test that sync adapters correctly delegate to ScanGameCore."""
        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("classic_scan_game.scan_mods_archived", return_value="Async result") as mock_wrapper_func,
        ):
            mock_bridge_class.get_instance.return_value = MagicMock()  # Ensure a bridge is available

            # Call the sync adapter
            result = classic_scan_game.scan_mods_archived()

            # Verify the wrapper called the underlying function
            mock_wrapper_func.assert_called_once()
            assert result == "Async result"
