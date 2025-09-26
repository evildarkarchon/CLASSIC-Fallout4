"""TUI test safety utilities and guidelines.

This module provides utilities and documentation for safely testing TUI components
without blocking test execution with interactive interfaces.

IMPORTANT: All TUI tests MUST use one of these approaches:
1. Use app.run_test() for Textual applications (non-interactive test runner)
2. Mock the interactive components entirely
3. Use the @pytest.mark.skip_interactive marker if unavoidable

Never call app.run() directly in tests as it will block waiting for user interaction!
"""

import pytest
from typing import Any
from unittest.mock import MagicMock, patch


# Custom marker for tests that would launch interactive UI
skip_interactive = pytest.mark.skip(
    reason="Skipped: Would launch interactive TUI interface and block test execution"
)


def mock_tui_app() -> MagicMock:
    """Create a properly mocked TUI application for testing.

    Returns:
        MagicMock configured to simulate TUI app without interaction
    """
    mock_app = MagicMock()
    mock_app.run = MagicMock(side_effect=RuntimeError(
        "DO NOT call app.run() in tests! Use app.run_test() or mock instead"
    ))
    mock_app.run_test = MagicMock()
    return mock_app


class SafeTUITestBase:
    """Base class for TUI tests with safety checks."""

    @pytest.fixture(autouse=True)
    def ensure_no_interactive_launch(self):
        """Automatically patch interactive methods to prevent blocking."""
        with patch("ClassicLib.TUI.app.CLASSICTuiApp.run") as mock_run:
            mock_run.side_effect = RuntimeError(
                "Interactive UI launch detected in test! Use run_test() instead"
            )
            yield


def test_tui_safety_documentation():
    """Test that documents TUI testing best practices."""
    # This test serves as documentation
    from textual.app import App

    class TestApp(App):
        """Example test app."""
        pass

    # CORRECT: Using run_test() for testing
    async def correct_test():
        app = TestApp()
        async with app.run_test() as pilot:
            # Test interactions without blocking
            await pilot.press("q")

    # WRONG: Would block test execution
    def wrong_test():
        app = TestApp()
        # app.run()  # DON'T DO THIS - will block!

    # CORRECT: Mocking the app entirely
    def correct_mock_test():
        app = mock_tui_app()
        # Safe to test without any UI launch
        assert app.run_test.called is False

    assert correct_test is not None
    assert wrong_test is not None
    assert correct_mock_test is not None


@skip_interactive
def test_example_skipped_interactive():
    """Example of a test that would be skipped due to interactive UI.

    This test is marked with @skip_interactive and will not run.
    """
    from ClassicLib.TUI.app import CLASSICTuiApp
    app = CLASSICTuiApp()
    # This would block:
    # app.run()
    pass


def test_verify_all_tui_tests_are_safe():
    """Verify that TUI tests are not calling interactive methods."""
    import os
    from pathlib import Path

    # Get all Python test files in this directory
    tui_test_dir = Path(__file__).parent
    test_files = list(tui_test_dir.glob("test_*.py"))

    # Check that no test file contains direct .run() calls
    dangerous_patterns = [
        "app.run()",
        "application.run()",
        ".run()  # Don't skip this",
    ]

    issues = []
    for test_file in test_files:
        if test_file.name == "test_tui_safety.py":
            continue  # Skip this file

        content = test_file.read_text()
        for pattern in dangerous_patterns:
            if pattern in content:
                # Check if it's in a comment or docstring
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if pattern in line and not line.strip().startswith("#"):
                        issues.append(f"{test_file.name}:{i} - Found '{pattern}'")

    # This assertion documents that we've verified the tests are safe
    assert len(issues) == 0, f"Found potentially blocking TUI calls: {issues}"