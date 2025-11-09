"""
Test suite for synchronous wrapper functions.

This module contains tests for the synchronous adapter functions
that wrap async ScanGameCore methods.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from unittest.mock import MagicMock, patch

import pytest


class TestSyncWrappers:
    """Test synchronous wrapper functions."""

    def test_scan_mods_archived_wrapper(self):
        """Test synchronous wrapper for scan_mods_archived."""
        # Mock the get_scan_game_core function and AsyncBridge
        with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core, patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Create a regular mock for the core
            mock_core = mock_get_core.return_value

            # Since AsyncBridge.run_async will handle the async execution,
            # we just need to mock what run_async returns
            mock_bridge.run_async.return_value = "Test result"

            # Test the sync adapter in the main module
            import CLASSIC_ScanGame

            result = CLASSIC_ScanGame.scan_mods_archived()
            assert result == "Test result"

    def test_check_log_errors_wrapper(self):
        """Test synchronous wrapper for check_log_errors."""
        # Create a mock path
        mock_path = MagicMock()

        # Mock the get_scan_game_core function and AsyncBridge
        with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core, patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Create a regular mock for the core
            mock_core = mock_get_core.return_value

            # Since AsyncBridge.run_async will handle the async execution,
            # we just need to mock what run_async returns
            mock_bridge.run_async.return_value = "Test log result"

            # Test the sync adapter in the main module
            import CLASSIC_ScanGame

            result = CLASSIC_ScanGame.check_log_errors(mock_path)
            assert result == "Test log result"

    def test_scan_mods_unpacked_wrapper(self):
        """Test synchronous wrapper for scan_mods_unpacked."""
        # Mock the get_scan_game_core function and AsyncBridge
        with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core, patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge

            # Create a regular mock for the core
            mock_core = mock_get_core.return_value

            # Since AsyncBridge.run_async will handle the async execution,
            # we just need to mock what run_async returns
            mock_bridge.run_async.return_value = "Test unpacked result"

            # Test the sync adapter in the main module
            import CLASSIC_ScanGame

            result = CLASSIC_ScanGame.scan_mods_unpacked()
            assert result == "Test unpacked result"

    def test_sync_adapter_integration(self):
        """Test that sync adapters correctly delegate to ScanGameCore."""
        # Test that sync adapters correctly delegate to async core
        with patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.return_value = "Async result"

            with patch("CLASSIC_ScanGame.ScanGameCore") as mock_core:
                mock_instance = mock_core.return_value
                # Don't create an AsyncMock here, the bridge handles the async part
                mock_instance.scan_mods_archived = MagicMock()

                # Call the sync adapter
                import CLASSIC_ScanGame

                result = CLASSIC_ScanGame.scan_mods_archived()

                # Verify core was instantiated
                mock_core.assert_called_once()
                assert result == "Async result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
