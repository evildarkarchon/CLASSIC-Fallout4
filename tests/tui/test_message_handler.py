"""Tests for the TuiMessageHandler component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.handlers.message_handler import TuiMessageHandler
from ClassicLib.TUI.widgets.output_viewer import OutputViewer

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


class TestMessageHandlerRouting:
    """Test message routing in TuiMessageHandler."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_message_handler_routing(self, message_handler):
        """Test message handler routes messages correctly."""
        app = CLASSICTuiApp()
        async with app.run_test():
            output_viewer = OutputViewer()
            app.mount(output_viewer)

            handler = TuiMessageHandler(output_viewer)

            # Test info message
            handler.show_message("Info message", "Info")
            assert len(output_viewer._output_buffer) == 1
            assert "Info message" in output_viewer._output_buffer[0]

            # Test error message
            handler.show_error("Error message")
            assert len(output_viewer._output_buffer) == 2
            assert "Error message" in output_viewer._output_buffer[1]

            # Test warning message
            handler.show_warning("Warning message")
            assert len(output_viewer._output_buffer) == 3
            assert "Warning message" in output_viewer._output_buffer[2]


class TestMessageHandlerProgress:
    """Test progress handling in TuiMessageHandler."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_message_handler_progress(self, message_handler):
        """Test message handler handles progress updates."""
        app = CLASSICTuiApp()
        async with app.run_test():
            output_viewer = OutputViewer()
            app.mount(output_viewer)

            handler = TuiMessageHandler(output_viewer)

            # Send progress updates
            handler.show_progress("Starting...", 0, 100)
            handler.show_progress("Halfway there...", 50, 100)
            handler.show_progress("Complete!", 100, 100)

            # Check messages were added
            assert len(output_viewer._output_buffer) >= 3
