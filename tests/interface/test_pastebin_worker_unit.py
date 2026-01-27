"""Unit tests for PastebinFetchWorker.

This module tests the PastebinFetchWorker class which handles fetching data from
Pastebin URLs in a Qt-compatible way:
- Initialization and URL storage
- Successful fetch and signal emission
- Network error handling (aiohttp.ClientError)
- File system and value error handling
- Import error handling
- Unexpected exception handling
- Signal emission guarantees (finished always emitted)

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_run_async_handler(return_value=None, side_effect=None):
    """Create a side_effect for run_async that properly closes coroutines.

    Args:
        return_value: Value to return after closing the coroutine.
        side_effect: Exception to raise after closing the coroutine.

    Returns:
        A function that closes the coroutine and returns/raises appropriately.
    """

    def handler(coro):
        # Close the coroutine to prevent "never awaited" warning
        coro.close()
        if side_effect is not None:
            raise side_effect
        return return_value

    return handler


# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


# =============================================================================
# PastebinFetchWorker Initialization Tests
# =============================================================================


class TestPastebinFetchWorkerInit:
    """Tests for PastebinFetchWorker initialization."""

    @pytest.mark.unit
    def test_worker_creation(self, qt_application):
        """Test PastebinFetchWorker can be created with URL."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        assert worker is not None
        assert worker.url == url

    @pytest.mark.unit
    def test_worker_stores_url(self, qt_application):
        """Test PastebinFetchWorker stores the provided URL."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        test_urls = [
            "https://pastebin.com/raw/abc123",
            "https://paste.ee/p/XYZ789",
            "https://hastebin.com/def456",
        ]

        for url in test_urls:
            worker = PastebinFetchWorker(url)
            assert worker.url == url

    @pytest.mark.unit
    def test_worker_has_signals(self, qt_application):
        """Test PastebinFetchWorker has required signals."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("https://pastebin.com/test")

        # Verify signal attributes exist
        assert hasattr(worker, "finished")
        assert hasattr(worker, "error")
        assert hasattr(worker, "success")


# =============================================================================
# PastebinFetchWorker Success Tests
# =============================================================================


class TestPastebinFetchWorkerSuccess:
    """Tests for successful PastebinFetchWorker operations."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_success_emits_signals(self, qt_application):
        """Test run() emits success and finished signals on successful fetch."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        # Track signal emissions
        success_spy = MagicMock()
        finished_spy = MagicMock()
        error_spy = MagicMock()

        worker.success.connect(success_spy)
        worker.finished.connect(finished_spy)
        worker.error.connect(error_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            # Use handler to close coroutine and return value
            mock_bridge.run_async.side_effect = make_run_async_handler(return_value="content")

            worker.run()

        # Verify signals
        success_spy.assert_called_once_with(url)
        finished_spy.assert_called_once()
        error_spy.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_calls_async_bridge(self, qt_application):
        """Test run() uses AsyncBridge to run the async fetch function."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            # Use handler to close coroutine
            mock_bridge.run_async.side_effect = make_run_async_handler()

            worker.run()

            # Verify AsyncBridge was used
            mock_bridge_class.get_instance.assert_called_once()
            mock_fetch.assert_called_once_with(url)
            # Verify run_async was called (with a coroutine)
            mock_bridge.run_async.assert_called_once()


# =============================================================================
# PastebinFetchWorker Error Handling Tests
# =============================================================================


class TestPastebinFetchWorkerErrors:
    """Tests for PastebinFetchWorker error handling."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_network_error_emits_error_signal(self, qt_application):
        """Test run() emits error signal on network errors."""
        import aiohttp

        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        # Track signal emissions
        success_spy = MagicMock()
        finished_spy = MagicMock()
        error_spy = MagicMock()

        worker.success.connect(success_spy)
        worker.finished.connect(finished_spy)
        worker.error.connect(error_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            # Use handler to close coroutine and raise error
            mock_bridge.run_async.side_effect = make_run_async_handler(side_effect=aiohttp.ClientError("Connection failed"))

            worker.run()

        # Verify error signal was emitted with network error message
        error_spy.assert_called_once()
        error_message = error_spy.call_args[0][0]
        assert "Network error" in error_message
        assert "Connection failed" in error_message

        # success should not be called, finished should still be called
        success_spy.assert_not_called()
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_oserror_emits_error_signal(self, qt_application):
        """Test run() emits error signal on OSError."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        error_spy = MagicMock()
        finished_spy = MagicMock()

        worker.error.connect(error_spy)
        worker.finished.connect(finished_spy)

        # Simulate OSError by having AsyncBridge.get_instance raise it
        # The OSError is caught in the outer try/except block
        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge_class.get_instance.side_effect = OSError("File system error")

            worker.run()

        error_spy.assert_called_once()
        error_message = error_spy.call_args[0][0]
        assert "File system or value error" in error_message
        assert "File system error" in error_message
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_valueerror_emits_error_signal(self, qt_application):
        """Test run() emits error signal on ValueError."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        error_spy = MagicMock()
        finished_spy = MagicMock()

        worker.error.connect(error_spy)
        worker.finished.connect(finished_spy)

        # Simulate ValueError by having AsyncBridge.get_instance raise it
        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge_class.get_instance.side_effect = ValueError("Invalid config")

            worker.run()

        error_spy.assert_called_once()
        error_message = error_spy.call_args[0][0]
        assert "File system or value error" in error_message
        assert "Invalid config" in error_message
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_importerror_emits_error_signal(self, qt_application):
        """Test run() emits error signal on ImportError."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        error_spy = MagicMock()
        finished_spy = MagicMock()

        worker.error.connect(error_spy)
        worker.finished.connect(finished_spy)

        # Simulate ImportError by patching at the module where the import happens
        # We patch the module that would be imported
        import sys

        # Temporarily remove aiohttp from sys.modules and prevent re-import
        saved_aiohttp = sys.modules.get("aiohttp")
        sys.modules["aiohttp"] = None  # type: ignore[assignment]

        try:
            worker.run()
        finally:
            # Restore the module
            if saved_aiohttp is not None:
                sys.modules["aiohttp"] = saved_aiohttp
            elif "aiohttp" in sys.modules:
                del sys.modules["aiohttp"]

        # When aiohttp is None in sys.modules, importing it will raise ImportError
        error_spy.assert_called_once()
        error_message = error_spy.call_args[0][0]
        # The actual error depends on how Python handles None in sys.modules
        # Just verify an error was emitted
        assert error_message  # Non-empty error message
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_unexpected_exception_emits_error_signal(self, qt_application):
        """Test run() emits error signal on unexpected exceptions."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        url = "https://pastebin.com/abc123"
        worker = PastebinFetchWorker(url)

        error_spy = MagicMock()
        finished_spy = MagicMock()

        worker.error.connect(error_spy)
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            # Use handler to close coroutine and raise error
            mock_bridge.run_async.side_effect = make_run_async_handler(side_effect=RuntimeError("Unexpected failure"))

            worker.run()

        error_spy.assert_called_once()
        error_message = error_spy.call_args[0][0]
        assert "Unexpected error" in error_message
        assert "Unexpected failure" in error_message
        finished_spy.assert_called_once()


# =============================================================================
# PastebinFetchWorker Signal Guarantee Tests
# =============================================================================


class TestPastebinFetchWorkerSignalGuarantees:
    """Tests for PastebinFetchWorker signal emission guarantees."""

    @pytest.mark.unit
    @pytest.mark.gui
    def test_finished_signal_always_emitted_on_success(self, qt_application):
        """Test finished signal is always emitted on success."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("https://pastebin.com/test")
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler()

            worker.run()

        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_finished_signal_always_emitted_on_network_error(self, qt_application):
        """Test finished signal is always emitted on network error."""
        import aiohttp

        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("https://pastebin.com/test")
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler(side_effect=aiohttp.ClientError("Network error"))

            worker.run()

        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_finished_signal_always_emitted_on_value_error(self, qt_application):
        """Test finished signal is always emitted on ValueError."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("https://pastebin.com/test")
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge_class.get_instance.side_effect = ValueError("Bad value")

            worker.run()

        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_finished_signal_always_emitted_on_unexpected_error(self, qt_application):
        """Test finished signal is always emitted on unexpected error."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("https://pastebin.com/test")
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            # Use handler to close coroutine and raise exception
            mock_bridge.run_async.side_effect = make_run_async_handler(side_effect=RecursionError("Unexpected depth"))

            worker.run()

        # Finished should always emit even on unexpected errors
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_mutually_exclusive_success_error_signals(self, qt_application):
        """Test that success and error signals are mutually exclusive."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        # Test success case - only success signal emitted
        worker_success = PastebinFetchWorker("https://pastebin.com/test")
        success_spy = MagicMock()
        error_spy = MagicMock()
        worker_success.success.connect(success_spy)
        worker_success.error.connect(error_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler()

            worker_success.run()

        assert success_spy.call_count == 1
        assert error_spy.call_count == 0

        # Test error case - only error signal emitted
        worker_error = PastebinFetchWorker("https://pastebin.com/test")
        success_spy2 = MagicMock()
        error_spy2 = MagicMock()
        worker_error.success.connect(success_spy2)
        worker_error.error.connect(error_spy2)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock),
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler(side_effect=RuntimeError("Error"))

            worker_error.run()

        assert success_spy2.call_count == 0
        assert error_spy2.call_count == 1


# =============================================================================
# PastebinFetchWorker URL Handling Tests
# =============================================================================


class TestPastebinFetchWorkerURLHandling:
    """Tests for PastebinFetchWorker URL handling."""

    @pytest.mark.unit
    @pytest.mark.gui
    @pytest.mark.parametrize(
        "url",
        [
            "https://pastebin.com/abc123",
            "https://pastebin.com/raw/abc123",
            "https://paste.ee/p/XYZ789",
            "https://paste.ee/r/XYZ789",
            "https://hastebin.com/share/def456",
            "https://haste.zneix.eu/raw/ghi012",
        ],
    )
    def test_run_with_various_pastebin_urls(self, url, qt_application):
        """Test run() works with various pastebin URL formats."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker(url)
        success_spy = MagicMock()
        finished_spy = MagicMock()

        worker.success.connect(success_spy)
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler()

            worker.run()

            # Verify the correct URL was passed to the fetch function
            mock_fetch.assert_called_once_with(url)

        success_spy.assert_called_once_with(url)
        finished_spy.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_run_with_empty_url(self, qt_application):
        """Test run() handles empty URL (passes it to the fetch function)."""
        from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker

        worker = PastebinFetchWorker("")
        finished_spy = MagicMock()
        worker.finished.connect(finished_spy)

        with (
            patch("ClassicLib.core.async_bridge.AsyncBridge") as mock_bridge_class,
            patch("ClassicLib.Utils.web_utils.async_pastebin_fetch", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.side_effect = make_run_async_handler()

            worker.run()

            # Empty URL is passed through - let the fetch function handle validation
            mock_fetch.assert_called_once_with("")

        finished_spy.assert_called_once()
