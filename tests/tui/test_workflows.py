"""End-to-end workflow tests for CLASSIC TUI.

These tests verify complete user workflows and interactions
across the TUI interface using the Textual async testing utilities.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_tui_services():
    """Mock all TUI services for isolated testing."""
    patches = {
        "classic_settings": patch("ClassicLib.io.yaml.classic_settings", return_value=None),
        "yaml_settings": patch("ClassicLib.io.yaml.yaml_settings"),
        "GlobalRegistry": patch("ClassicLib.core.registry.GlobalRegistry"),
    }
    mocks = {}
    for name, p in patches.items():
        mocks[name] = p.start()

    # Configure GlobalRegistry mock
    mocks["GlobalRegistry"].get_local_dir.return_value = Path.home() / ".classic-test"

    yield mocks

    for p in patches.values():
        p.stop()


class TestTabNavigation:
    """Test tab switching and navigation workflows."""

    @pytest.mark.asyncio
    async def test_keyboard_tab_switching(self, mock_tui_services):
        """Verify keyboard shortcuts switch between tabs correctly."""
        from ClassicLib.TUI.app import CLASSICApp

        app = CLASSICApp()
        async with app.run_test() as pilot:
            # Should start on main tab (tab 1)
            tabs = app.query_one("#main-tabs")
            assert tabs.active == "main"

            # Switch to backup tab
            await pilot.press("2")
            assert tabs.active == "backup"

            # Switch to articles tab
            await pilot.press("3")
            assert tabs.active == "articles"

            # Switch to results tab
            await pilot.press("4")
            assert tabs.active == "results"

            # Back to main tab
            await pilot.press("1")
            assert tabs.active == "main"


class TestHelpScreen:
    """Test help screen modal behavior."""

    @pytest.mark.asyncio
    async def test_help_opens_and_closes(self, mock_tui_services):
        """Verify F1 opens help and Escape closes it."""
        from ClassicLib.TUI.app import CLASSICApp
        from ClassicLib.TUI.screens.help_screen import HelpScreen

        app = CLASSICApp()
        async with app.run_test() as pilot:
            # Verify we start with just the main screen
            initial_screen_count = len(app.screen_stack)

            # Open help with F1
            await pilot.press("f1")
            await pilot.pause()

            # Verify a new screen was pushed (help screen)
            assert len(app.screen_stack) > initial_screen_count
            # Check the current screen is HelpScreen
            assert isinstance(app.screen, HelpScreen)

            # Close with Escape
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to the initial screen count
            assert len(app.screen_stack) == initial_screen_count


class TestSettingsScreen:
    """Test settings screen modal behavior."""

    @pytest.mark.asyncio
    async def test_settings_opens_and_closes(self, mock_tui_services):
        """Verify Ctrl+O opens settings and Escape closes it."""
        from ClassicLib.TUI.app import CLASSICApp
        from ClassicLib.TUI.screens.settings_screen import SettingsScreen

        app = CLASSICApp()
        async with app.run_test() as pilot:
            initial_screen_count = len(app.screen_stack)

            # Open settings with Ctrl+O
            await pilot.press("ctrl+o")
            await pilot.pause()

            # Verify settings screen was pushed
            assert len(app.screen_stack) > initial_screen_count
            assert isinstance(app.screen, SettingsScreen)

            # Close with Escape
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back
            assert len(app.screen_stack) == initial_screen_count


class TestMainTabActions:
    """Test main tab button actions and interactions."""

    @pytest.mark.asyncio
    async def test_papyrus_toggle_button(self, mock_tui_services):
        """Verify Papyrus monitor toggle changes button state."""
        from textual.widgets import Button

        from ClassicLib.TUI.app import CLASSICApp
        from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor

        # Mock the PapyrusMonitor to prevent actual monitoring
        with patch.object(PapyrusMonitor, "start_monitoring"), patch.object(PapyrusMonitor, "stop_monitoring"):
            app = CLASSICApp()
            async with app.run_test() as pilot:
                # Find the toggle button
                toggle_btn = app.query_one("#btn-papyrus-toggle", Button)
                assert "[OFF]" in str(toggle_btn.label)

                # Click to toggle ON
                await pilot.click("#btn-papyrus-toggle")
                await pilot.pause()
                await pilot.pause()  # Extra pause for state update
                assert "[ON]" in str(toggle_btn.label)

                # Click to toggle OFF - give extra time for button state reset
                await pilot.pause()
                await pilot.click("#btn-papyrus-toggle")
                await pilot.pause()
                await pilot.pause()  # Extra pause for state update
                assert "[OFF]" in str(toggle_btn.label)

    @pytest.mark.asyncio
    async def test_crash_scan_button_opens_modal(self, mock_tui_services):
        """Verify crash scan button opens progress modal."""
        from ClassicLib.TUI.app import CLASSICApp
        from ClassicLib.TUI.widgets.scan_progress import ScanProgressModal

        # Mock the _start_scan method to prevent actual scanning
        with patch.object(ScanProgressModal, "_start_scan"):
            app = CLASSICApp()
            async with app.run_test() as pilot:
                initial_screen_count = len(app.screen_stack)

                # Click crash scan button
                await pilot.click("#btn-crash-scan")
                await pilot.pause()

                # Verify modal was pushed
                assert len(app.screen_stack) > initial_screen_count
                assert isinstance(app.screen, ScanProgressModal)


class TestQuitBehavior:
    """Test application quit behavior."""

    @pytest.mark.asyncio
    async def test_ctrl_q_quits_app(self, mock_tui_services):
        """Verify Ctrl+Q triggers app quit."""
        from ClassicLib.TUI.app import CLASSICApp

        app = CLASSICApp()
        async with app.run_test() as pilot:
            # Verify app is running
            assert app.is_running

            # Send quit command
            await pilot.press("ctrl+q")
            # App should stop running (run_test handles this gracefully)

    @pytest.mark.asyncio
    async def test_q_quits_app(self, mock_tui_services):
        """Verify 'q' key triggers app quit."""
        from ClassicLib.TUI.app import CLASSICApp

        app = CLASSICApp()
        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should stop running
