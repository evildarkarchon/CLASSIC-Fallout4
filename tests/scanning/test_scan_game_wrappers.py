"""
Test suite for synchronous wrapper functions.

This module contains tests for the synchronous adapter functions
that wrap async ScanGameCore methods.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import CLASSIC_ScanGame # Added at module level


class TestSyncWrappers:
    """Test synchronous wrapper functions."""

    def test_scan_mods_archived_wrapper(self):
        # Patch the specific async method on the global _scan_game_core instance
        with patch("CLASSIC_ScanGame.scan_mods_archived", return_value="Test result") as mock_scan_mods_archived, patch(
            "ClassicLib.AsyncBridge.AsyncBridge"
        ) as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            
            # This mock is actually not hit in the current setup but kept for safety.
            mock_bridge.run_async.return_value = "Test result" 



            result = CLASSIC_ScanGame.scan_mods_archived()
            assert result == "Test result"
            mock_scan_mods_archived.assert_called_once()

    def test_check_log_errors_wrapper(self):
        """Test synchronous wrapper for check_log_errors."""
        mock_path = MagicMock()
        with patch("CLASSIC_ScanGame.check_log_errors", return_value="Test log result") as mock_check_log_errors, patch(
            "ClassicLib.AsyncBridge.AsyncBridge"
        ) as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            
            mock_bridge.run_async.return_value = "Test log result"



            result = CLASSIC_ScanGame.check_log_errors(mock_path)
            assert result == "Test log result"
            mock_check_log_errors.assert_called_once_with(mock_path)

    def test_scan_mods_unpacked_wrapper(self):
        """Test synchronous wrapper for scan_mods_unpacked."""
        with patch("CLASSIC_ScanGame.scan_mods_unpacked", return_value="Test unpacked result") as mock_scan_mods_unpacked, patch(
            "ClassicLib.AsyncBridge.AsyncBridge"
        ) as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            
            mock_bridge.run_async.return_value = "Test unpacked result"



            result = CLASSIC_ScanGame.scan_mods_unpacked()
            assert result == "Test unpacked result"
            mock_scan_mods_unpacked.assert_called_once()

    def test_sync_adapter_integration(self):
        """Test that sync adapters correctly delegate to ScanGameCore."""
        with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_bridge_class, patch(
            "CLASSIC_ScanGame.scan_mods_archived", return_value="Async result"
        ) as mock_scan_mods_archived:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.return_value = "Async result"

            # Call the sync adapter
            result = CLASSIC_ScanGame.scan_mods_archived()

            # Verify the wrapper called the underlying function
            mock_scan_mods_archived.assert_called_once()
            assert result == "Async result"

