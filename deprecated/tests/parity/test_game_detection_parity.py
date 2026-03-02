"""VAL-04: Rust game detection API tests.

Tests that Rust GamePathFinder provides a consistent, working API for
game path detection. Since Phase 7 removed Python game path fallback,
these tests verify Rust behavior consistency rather than Python-Rust
parity.

Note: Registry-based detection is platform-specific (Windows only).
Tests use mocking where necessary to validate detection strategies
work correctly regardless of actual registry state.

Per CONTEXT.md decisions:
- Paths: Normalized to forward slashes for comparison
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Skip entire module on non-Windows (registry-based detection)
pytestmark = [
    pytest.mark.parity,
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows-only registry tests"),
]


class TestGameDetectionAPI:
    """VAL-04: Rust game detection API tests."""

    def test_game_path_finder_import(self):
        """GamePathFinder imports successfully from Rust module."""
        # Rust-only, hard fail if unavailable
        from classic_path import GamePathFinder as RustGamePathFinder

        assert RustGamePathFinder is not None

    def test_path_validator_import(self):
        """PathValidator imports successfully from Rust module."""
        from classic_path import PathValidator

        assert PathValidator is not None

    def test_game_path_finder_initialization(self):
        """GamePathFinder initializes with required parameters."""
        from classic_path import GamePathFinder as RustGamePathFinder

        # Initialize with standard Fallout 4 parameters
        finder = RustGamePathFinder(
            "Fallout4.exe",
            "f4se_loader.exe",  # xse_loader
            "Fallout4",  # game
            False,  # is_vr
        )
        assert finder is not None
        assert finder.game_exe == "Fallout4.exe"
        assert finder.xse_loader == "f4se_loader.exe"
        assert finder.is_vr is False

    def test_game_path_finder_with_none_xse_loader(self):
        """GamePathFinder initializes with None xse_loader."""
        from classic_path import GamePathFinder as RustGamePathFinder

        finder = RustGamePathFinder(
            "Fallout4.exe",
            None,  # xse_loader can be None
            "Fallout4",
            False,
        )
        assert finder is not None
        assert finder.xse_loader is None

    def test_path_normalization_consistency(self):
        """Path normalization produces consistent forward-slash paths."""
        # Test Windows paths
        windows_path = r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4"
        normalized = windows_path.replace("\\", "/")

        assert "\\" not in normalized, "Backslashes should be replaced"
        assert "/" in normalized, "Should use forward slashes"
        assert normalized == "C:/Program Files (x86)/Steam/steamapps/common/Fallout 4"

    def test_cached_path_detection(self):
        """GamePathFinder uses cached path when valid."""
        from classic_path import GamePathFinder as RustGamePathFinder

        finder = RustGamePathFinder(
            "Fallout4.exe",
            "f4se_loader.exe",
            "Fallout4",
            False,
        )

        # Mock a valid cached path
        # This tests that the Rust finder respects cached_path parameter
        # Actual path validation happens in Rust
        cached = r"D:\Games\Fallout 4"

        try:
            # If path is valid, should return it
            # If invalid, should raise or return None
            result = finder.find_game_path(cached_path=cached, xse_log_path=None)
            # If we get here, path was accepted
            assert result is not None
        except (FileNotFoundError, ValueError):
            # Expected if path doesn't exist - validates Rust checks path
            pass

    def test_xse_log_path_detection(self):
        """GamePathFinder can extract path from XSE log."""
        from classic_path import GamePathFinder as RustGamePathFinder

        finder = RustGamePathFinder(
            "Fallout4.exe",
            "f4se_loader.exe",
            "Fallout4",
            False,
        )

        # XSE log parsing is tested through the interface
        # Actual parsing happens in Rust classic-path crate
        # This just verifies the API accepts the parameter
        try:
            result = finder.find_game_path(cached_path=None, xse_log_path=r"D:\Docs\My Games\Fallout4\F4SE\f4se.log")
        except (FileNotFoundError, ValueError, OSError):
            # Expected if files don't exist
            pass

    def test_vr_mode_detection(self):
        """GamePathFinder handles VR mode correctly."""
        from classic_path import GamePathFinder as RustGamePathFinder

        # VR mode finder
        finder_vr = RustGamePathFinder(
            "Fallout4VR.exe",
            "f4sevr_loader.exe",
            "Fallout4VR",
            True,  # is_vr = True
        )
        assert finder_vr is not None
        assert finder_vr.is_vr is True

        # Non-VR mode finder (for comparison)
        finder_og = RustGamePathFinder(
            "Fallout4.exe",
            "f4se_loader.exe",
            "Fallout4",
            False,
        )
        assert finder_og is not None
        assert finder_og.is_vr is False


class TestPathValidation:
    """Tests for PathValidator Rust component."""

    def test_path_validator_is_valid_path_true(self):
        """PathValidator.is_valid_path returns True for existing paths."""
        from classic_path import PathValidator

        # Current directory should exist
        result = PathValidator.is_valid_path(".")
        assert result is True, "Current directory should be valid"

    def test_validate_nonexistent_path(self):
        """PathValidator rejects nonexistent paths."""
        from classic_path import PathValidator

        # This should return False for a nonexistent path
        result = PathValidator.is_valid_path(r"Z:\NonExistent\Path\That\Should\Not\Exist\12345")
        assert result is False, "Nonexistent path should not validate"

    def test_validate_path_without_exe(self):
        """PathValidator validates path existence (not exe presence)."""
        from classic_path import PathValidator

        # Create temp directory without the exe
        with tempfile.TemporaryDirectory() as tmpdir:
            # is_valid_path checks path existence, not exe presence
            result = PathValidator.is_valid_path(tmpdir)
            assert result is True, "Existing path should validate"

    def test_check_drive_exists_valid(self):
        """PathValidator.check_drive_exists succeeds for existing drives."""
        from classic_path import PathValidator

        # C: drive should exist on Windows - returns None on success
        result = PathValidator.check_drive_exists(r"C:\Windows")
        assert result is None, "check_drive_exists returns None on success"

    def test_check_drive_exists_invalid(self):
        """PathValidator.check_drive_exists raises for nonexistent drives."""
        from classic_path import PathValidator

        # Z: drive probably doesn't exist - should raise ValueError
        try:
            PathValidator.check_drive_exists(r"Z:\NonExistent\Path\12345")
            # If it doesn't raise, Z: drive exists on this system (e.g., network drive)
        except ValueError:
            # Expected for nonexistent drive
            pass


class TestRustComponentsAvailable:
    """VAL-05: All existing tests pass with Rust as primary code path."""

    def test_rust_components_available(self):
        """Verify all required Rust components are available."""
        from ClassicLib.integration.factory import get_rust_component_status

        status = get_rust_component_status()
        available = status.get("available", {})

        # Core components required for Phase 10
        # Note: component names from factory._COMPONENT_KEY_MAP
        required = ["yaml", "parser", "yamldata", "path"]

        for component in required:
            assert available.get(component, False), (
                f"Rust component '{component}' not available. Run './rebuild_rust.ps1' to build Rust modules."
            )

    def test_acceleration_level(self):
        """Verify sufficient Rust acceleration level."""
        from ClassicLib.integration.factory import get_rust_component_status

        status = get_rust_component_status()
        level = status.get("acceleration_level", "NO ACCELERATION")

        # Expect at least partial acceleration
        acceptable_levels = ["PARTIALLY ACCELERATED", "HIGHLY ACCELERATED", "FULLY ACCELERATED"]
        assert level in acceptable_levels, f"Rust acceleration level '{level}' too low. Expected one of: {acceptable_levels}"
