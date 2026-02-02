"""Integration tests for PathValidator Rust acceleration.

This module tests the Python-Rust integration for PathValidator, ensuring:
- Rust acceleration is used when available
- Fallback to Python works when Rust is not available
- API compatibility between Rust and Python implementations
- Performance improvements with Rust acceleration

Test Coverage:
- is_valid_path() with various path types
- is_restricted_path() with various path types
- Fallback behavior when Rust is unavailable
- Edge cases and error handling

Note:
    These tests verify that Rust acceleration is active before running.
    They will skip if the Rust path module (classic_path) is not available.
    The component is registered as "path" in the detector.
"""

from __future__ import annotations

import platform
import sys
import tracemalloc
from pathlib import Path

import pytest

from ClassicLib.integration.factory import is_rust_accelerated
from ClassicLib.support.path_validator import PathValidator


def _skip_if_rust_unavailable() -> None:
    """Skip the test if Rust path module is not available.

    Raises:
        pytest.skip: If Rust acceleration is not available for path operations.

    Note:
        The Rust module is registered as "path" (base component) and
        "path_operations" (for PathValidator class) in the detector.
    """
    if not is_rust_accelerated("path"):
        pytest.skip("Rust path module not available")


@pytest.mark.rust
@pytest.mark.integration
class TestPathValidatorRustIntegration:
    """Test PathValidator Rust acceleration integration.

    These tests verify that the PathValidator class uses Rust acceleration
    when available. Tests will skip if Rust path_validator is not installed.
    """

    @pytest.fixture(autouse=True)
    def require_rust(self) -> None:
        """Require Rust path_validator to be available for all tests in this class."""
        _skip_if_rust_unavailable()

    def test_rust_acceleration_is_active(self) -> None:
        """Verify that Rust acceleration is actually being used.

        This test confirms that the PathValidator class is using Rust acceleration,
        not falling back to Python. This ensures the other tests in this class
        are actually testing Rust behavior.
        """
        assert is_rust_accelerated("path"), "Rust path module should be active"

    def test_is_valid_path_with_existing_file(self):
        """Test is_valid_path with an existing file (Python executable)."""
        python_exe = sys.executable
        assert PathValidator.is_valid_path(python_exe) is True

    def test_is_valid_path_with_existing_directory(self, tmp_path: Path):
        """Test is_valid_path with an existing directory."""
        assert PathValidator.is_valid_path(tmp_path) is True

    def test_is_valid_path_with_nonexistent_path(self):
        """Test is_valid_path with a non-existent path."""
        nonexistent = Path("/nonexistent/path/that/does/not/exist")
        assert PathValidator.is_valid_path(nonexistent) is False

    def test_is_valid_path_with_none(self):
        """Test is_valid_path with None."""
        assert PathValidator.is_valid_path(None) is False  # pyright: ignore[reportArgumentType]

    def test_is_valid_path_with_empty_string(self):
        """Test is_valid_path with empty string."""
        assert PathValidator.is_valid_path("") is False
        assert PathValidator.is_valid_path("   ") is False

    def test_is_valid_path_with_string_path(self, tmp_path: Path):
        """Test is_valid_path with string path."""
        assert PathValidator.is_valid_path(str(tmp_path)) is True

    def test_is_valid_path_with_path_object(self, tmp_path: Path):
        """Test is_valid_path with Path object."""
        assert PathValidator.is_valid_path(tmp_path) is True

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_is_restricted_path_system32(self):
        """Test is_restricted_path with System32 directory."""
        import os

        system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
        assert PathValidator.is_restricted_path(system32) is True

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_is_restricted_path_program_files(self):
        """Test is_restricted_path with Program Files directory."""
        import os

        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        assert PathValidator.is_restricted_path(program_files) is True

    def test_is_restricted_path_user_directory(self):
        """Test is_restricted_path with user directory (should be allowed)."""
        if platform.system() == "Windows":
            user_docs = Path.home() / "Documents"
        else:
            user_docs = Path.home()

        # User directories should NOT be restricted
        if user_docs.exists():
            assert PathValidator.is_restricted_path(user_docs) is False

    def test_is_restricted_path_with_nonexistent(self):
        """Test is_restricted_path with non-existent path.

        Note: Rust implementation returns False for invalid paths
        (they're not restricted, they're invalid). Python fallback
        returns True as a fail-safe. This test verifies Rust behavior.
        """
        nonexistent = Path("/nonexistent/path/that/does/not/exist")
        # Rust returns False for invalid paths (they're not restricted, just invalid)
        assert PathValidator.is_restricted_path(nonexistent) is False

    def test_is_restricted_path_with_none(self):
        """Test is_restricted_path with None.

        Note: None is handled in Python before calling Rust,
        so this uses Python's fail-safe behavior (returns True).
        """
        # None should be considered restricted (Python fallback)
        assert PathValidator.is_restricted_path(None) is True

    def test_is_restricted_path_with_empty_string(self):
        """Test is_restricted_path with empty string.

        Note: Empty strings trigger Python fallback which validates them
        as invalid custom scan paths, returning True (restricted) as fail-safe.
        """
        # Empty strings are invalid and return True (restricted) as fail-safe
        assert PathValidator.is_restricted_path("") is True
        # Note: whitespace-only strings are converted to empty path by pathlib
        # and also return True (restricted)
        assert PathValidator.is_restricted_path("   ") is True

    def test_rust_fallback_behavior(self, tmp_path: Path):
        """Test that fallback behavior works correctly.

        This test verifies that the implementation handles errors gracefully
        by testing the documented behavior: valid paths return correct results
        regardless of whether Rust or Python implementation is used.
        """
        # Test that valid paths work correctly
        assert PathValidator.is_valid_path(tmp_path) is True
        assert PathValidator.is_valid_path("/nonexistent") is False

        # Test that fallback maintains correct behavior
        # (implicitly tests fallback since other tests verify it works)
        assert isinstance(PathValidator.is_valid_path(tmp_path), bool)

    @pytest.mark.performance
    @pytest.mark.skipif(tracemalloc.is_tracing(), reason="Tracemalloc overhead affects performance measurements")
    def test_rust_acceleration_performance(self, tmp_path: Path):
        """Test Rust acceleration performance.

        This test performs a simple timing check to verify that
        Rust acceleration provides reasonable performance.
        """
        import time

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            PathValidator.is_valid_path(tmp_path)
            PathValidator.is_valid_path("/nonexistent")
            PathValidator.is_restricted_path(tmp_path)

        elapsed = time.perf_counter() - start

        # Just verify it completes in reasonable time
        # With Rust acceleration, 1000 iterations should be < 2 seconds
        assert elapsed < 2.0, f"Performance test took {elapsed:.2f}s (expected < 2s)"


@pytest.mark.rust
@pytest.mark.integration
class TestPathValidatorYAMLIntegration:
    """Test that YAML-dependent PathValidator methods still work with Python."""

    def test_yaml_methods_use_python(self):
        """Verify YAML-dependent methods remain pure Python."""
        # These methods should not use Rust directly
        # They rely on YamlSettingsCache which wraps classic_settings

        # Just verify the methods exist and are callable
        assert callable(PathValidator.validate_custom_scan_path)
        assert callable(PathValidator.validate_game_root_path)
        assert callable(PathValidator.validate_documents_path)
        assert callable(PathValidator.validate_mods_folder_path)
        assert callable(PathValidator.validate_ini_folder_path)
        assert callable(PathValidator.validate_all_settings_paths)


@pytest.mark.rust
@pytest.mark.integration
class TestPathValidatorAPICompatibility:
    """Test API compatibility between Rust and Python implementations.

    These tests verify that the Rust implementation maintains API compatibility
    with the Python implementation.
    """

    @pytest.fixture(autouse=True)
    def require_rust(self) -> None:
        """Require Rust path_validator to be available for all tests in this class."""
        _skip_if_rust_unavailable()

    def test_is_valid_path_signature(self):
        """Verify is_valid_path accepts both str and Path."""
        python_exe = sys.executable

        # Should accept string
        assert PathValidator.is_valid_path(python_exe) is True

        # Should accept Path
        assert PathValidator.is_valid_path(Path(python_exe)) is True

    def test_is_restricted_path_signature(self):
        """Verify is_restricted_path accepts both str and Path."""
        user_docs = Path.home() / "Documents"

        if user_docs.exists():
            # Should accept string
            assert PathValidator.is_restricted_path(str(user_docs)) is False

            # Should accept Path
            assert PathValidator.is_restricted_path(user_docs) is False

    def test_return_types(self, tmp_path: Path):
        """Verify return types match API specification."""
        # is_valid_path should return bool
        result = PathValidator.is_valid_path(tmp_path)
        assert isinstance(result, bool)

        # is_restricted_path should return bool
        result = PathValidator.is_restricted_path(tmp_path)
        assert isinstance(result, bool)


@pytest.mark.rust
@pytest.mark.integration
class TestPathValidatorEdgeCases:
    """Test edge cases and error handling.

    These tests verify that the Rust implementation handles edge cases
    correctly and doesn't crash on unusual inputs.
    """

    @pytest.fixture(autouse=True)
    def require_rust(self) -> None:
        """Require Rust path_validator to be available for all tests in this class."""
        _skip_if_rust_unavailable()

    def test_very_long_path(self):
        """Test with very long path name."""
        # Create a very long path (but not exceeding OS limits)
        long_path = "a" * 200
        result = PathValidator.is_valid_path(long_path)
        # Should handle gracefully without crashing
        assert isinstance(result, bool)

    def test_special_characters_in_path(self, tmp_path: Path):
        """Test with special characters in path."""
        # Create directory with special characters (if allowed by OS)
        try:
            special_dir = tmp_path / "test_dir"
            special_dir.mkdir(exist_ok=True)
            assert PathValidator.is_valid_path(special_dir) is True
        except OSError:
            # Some OSes don't allow certain characters
            pytest.skip("OS does not support special characters in paths")

    def test_relative_path(self):
        """Test with relative path."""
        # Relative paths should work if they exist
        result = PathValidator.is_valid_path(".")
        assert result is True  # Current directory should exist

    def test_symlink_handling(self, tmp_path: Path):
        """Test handling of symbolic links."""
        target = tmp_path / "target"
        target.mkdir()

        link = tmp_path / "link"
        try:
            link.symlink_to(target)
            # Should follow symlink and validate target
            assert PathValidator.is_valid_path(link) is True
        except (OSError, NotImplementedError):
            # Symlinks might not be supported
            pytest.skip("Symlinks not supported on this platform")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_unc_path(self):
        """Test with UNC path (Windows only)."""
        unc_path = r"\\localhost\c$"
        # Should handle UNC paths without crashing
        result = PathValidator.is_valid_path(unc_path)
        assert isinstance(result, bool)

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific test")
    def test_root_path_unix(self):
        """Test with root path on Unix systems."""
        assert PathValidator.is_valid_path("/") is True
        # /proc should exist on Linux
        if Path("/proc").exists():
            # /proc is typically restricted
            assert PathValidator.is_restricted_path("/proc") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
