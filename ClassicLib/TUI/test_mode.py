"""Test mode support for CLASSIC TUI.

This module provides environment-based test mode detection and mock
services for use with pytest-textual-snapshot, which runs the app
in a subprocess where test-level mocks don't propagate.

Environment Variables:
    CLASSIC_TUI_TEST_MODE: Set to "1" to enable test mode.

Example:
    In snapshot tests, set the environment variable before running::

        import os
        os.environ["CLASSIC_TUI_TEST_MODE"] = "1"

"""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path

# Environment variable name for test mode
_TEST_MODE_ENV_VAR = "CLASSIC_TUI_TEST_MODE"


def is_test_mode() -> bool:
    """Check if the TUI is running in test mode.

    Test mode is enabled when the CLASSIC_TUI_TEST_MODE environment
    variable is set to "1".

    Returns:
        True if test mode is enabled, False otherwise.

    """
    return os.environ.get(_TEST_MODE_ENV_VAR) == "1"


@lru_cache(maxsize=1)
def get_test_local_dir() -> Path:
    """Get a temporary directory for test mode operations.

    Creates a temporary directory that persists for the process lifetime.
    This ensures consistent paths within a single test run.

    Returns:
        Path to the test-mode local directory.

    """
    # lru_cache ensures this is only created once per process
    return Path(tempfile.mkdtemp(prefix="classic_tui_test_"))


def get_test_setting(setting: str) -> str | bool | None:
    """Get a mock value for a CLASSIC setting in test mode.

    Provides stable, predictable values for settings during snapshot tests.

    Args:
        setting: The setting name (e.g., "VR Mode", "MODS Folder Path").

    Returns:
        A mock value appropriate for the setting, or None.

    """
    # Map of settings to stable test values
    test_defaults: dict[str, str | bool | None] = {
        "VR Mode": False,
        "Game Version": "auto",
        "MODS Folder Path": "",
        "SCAN Custom Path": "",
        "Auto Switch After Scan": False,
        "Show Notifications": True,
    }
    return test_defaults.get(setting)


def initialize_test_mode() -> None:
    """Initialize test mode if enabled.

    This function should be called early in the TUI startup sequence.
    It sets up mock services and registry entries for test mode.

    When test mode is enabled:
    - Creates a temporary local directory
    - Pre-populates the test directory structure
    """
    if not is_test_mode():
        return

    # Create the test directory structure
    test_dir = get_test_local_dir()

    # Create standard subdirectories that the app expects
    (test_dir / "Crash Logs").mkdir(parents=True, exist_ok=True)
    (test_dir / "CLASSIC Backup" / "Game Files").mkdir(parents=True, exist_ok=True)


__all__ = [
    "get_test_local_dir",
    "get_test_setting",
    "initialize_test_mode",
    "is_test_mode",
]
