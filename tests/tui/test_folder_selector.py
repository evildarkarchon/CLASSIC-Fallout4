"""Tests for the FolderSelector widget."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

from pathlib import Path

import pytest
from textual.app import App

from ClassicLib.TUI.widgets.folder_selector import FolderSelector


class TestFolderSelectorInitialization:
    """Test FolderSelector initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_folder_selector_initialization(self):
        """Test FolderSelector initializes correctly."""
        async with App().run_test() as pilot:
            selector = FolderSelector(placeholder="Select folder", initial_path="/initial/path")
            pilot.app.mount(selector)

            # Wait for the widget to be composed
            await pilot.pause()

            # The Input widget is internal to FolderSelector
            assert selector._input is not None
            assert selector._input.placeholder == "Select folder"
            assert selector._input.value == "/initial/path"


class TestFolderSelectorValidation:
    """Test FolderSelector validation."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_folder_selector_validation(self):
        """Test folder path validation."""
        async with App().run_test() as pilot:
            selector = FolderSelector()
            pilot.app.mount(selector)

            # Wait for the widget to be composed
            await pilot.pause()

            # Test valid path
            valid_path = str(Path.home())
            selector.set_path(valid_path)

            # Should accept valid path
            assert selector.valid is True

            # Test invalid path
            invalid_path = "/nonexistent/path/that/does/not/exist"
            selector.set_path(invalid_path)
            assert selector.valid is False
