"""Tests for the OutputViewer widget."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

import pytest
from textual.app import App

from ClassicLib.TUI.widgets.output_viewer import OutputViewer


class TestOutputViewerInitialization:
    """Test OutputViewer initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_viewer_initialization(self):
        """Test OutputViewer initializes correctly."""
        async with App().run_test() as pilot:
            viewer = OutputViewer(max_lines=100, auto_scroll=True)
            pilot.app.mount(viewer)

            assert viewer.max_lines == 100
            assert viewer.auto_scroll is True
            assert viewer.show_timestamps is True
            assert len(viewer._output_buffer) == 0


class TestOutputViewerOperations:
    """Test OutputViewer operations."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_viewer_append_output(self):
        """Test appending output to viewer."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("Test message", style="info")
            assert len(viewer._output_buffer) == 1
            assert "Test message" in viewer._output_buffer[0]

            viewer.append_output("Error message", style="error")
            assert len(viewer._output_buffer) == 2

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_viewer_clear(self):
        """Test clearing output viewer."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("Message 1")
            viewer.append_output("Message 2")
            assert len(viewer._output_buffer) == 2

            viewer.clear()
            assert len(viewer._output_buffer) == 0

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_viewer_search(self):
        """Test search functionality."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("First message")
            viewer.append_output("Second message")
            viewer.append_output("Third message")

            matches = viewer.search("message")
            assert matches == 3

            matches = viewer.search("Second")
            assert matches == 1

            matches = viewer.search("nonexistent")
            assert matches == 0

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_viewer_toggle_auto_scroll(self):
        """Test toggling auto-scroll."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            # Wait for the widget to be fully composed
            await pilot.pause()

            initial_state = viewer.auto_scroll
            viewer.toggle_auto_scroll()
            assert viewer.auto_scroll != initial_state

            viewer.toggle_auto_scroll()
            assert viewer.auto_scroll == initial_state
