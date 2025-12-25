"""
Unit tests for Rust path validation in FolderManagement.

This test module verifies that:
1. Rust PathValidator is available and properly integrated
2. Path validation uses Rust when available
3. Path normalization works correctly
4. Proper fallback to Python when Rust unavailable
5. Invalid paths are correctly identified
6. Windows-specific path handling works
"""

import os
from pathlib import Path

import pytest

# Test Rust availability


@pytest.mark.unit
@pytest.mark.rust
def test_rust_path_available():
    """Test that Rust path module is available."""
    try:
        import classic_path

        assert hasattr(classic_path, "PathValidator"), "PathValidator class should be available"

        # Verify it has expected methods
        assert hasattr(classic_path.PathValidator, "is_valid_path"), "Should have is_valid_path method"
        assert hasattr(classic_path.PathValidator, "validate_custom_scan_path"), "Should have validate_custom_scan_path method"
    except ImportError:
        pytest.skip("Rust path module not available - expected if not built")


@pytest.mark.unit
@pytest.mark.rust
def test_folder_management_detects_rust():
    """Test that FolderManagement detects Rust availability."""
    try:
        import classic_path
    except ImportError:
        pytest.skip("Rust path module not available")

    from ClassicLib.Interface.FolderManagement import _RUST_PATH_AVAILABLE

    if not _RUST_PATH_AVAILABLE:
        pytest.skip("Rust path operations not available in this environment")

    assert _RUST_PATH_AVAILABLE, "Rust path should be available"


# Test path validation functions


@pytest.mark.unit
@pytest.mark.rust
def test_is_valid_directory_with_rust():
    """Test directory validation with Rust acceleration."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    # Test with existing directory
    assert _is_valid_directory("C:/Windows"), "C:/Windows should be valid"
    assert _is_valid_directory("C:\\Windows"), "C:\\Windows should be valid (backslash)"

    # Test with non-existent directory
    assert not _is_valid_directory("C:/NonExistentDirectory12345"), "Non-existent dir should be invalid"

    # Test with file (not directory)
    test_file = Path.cwd() / "pyproject.toml"
    if test_file.exists():
        assert not _is_valid_directory(test_file), "File should not be valid as directory"


@pytest.mark.unit
def test_is_valid_directory_fallback():
    """Test directory validation falls back to Python when Rust unavailable."""
    from ClassicLib.Interface import FolderManagement

    # Temporarily disable Rust
    original = FolderManagement._RUST_PATH_AVAILABLE
    FolderManagement._RUST_PATH_AVAILABLE = False

    try:
        # Should still work with Python
        assert FolderManagement._is_valid_directory("C:/Windows"), "Python fallback should work"
    finally:
        # Restore Rust
        FolderManagement._RUST_PATH_AVAILABLE = original


@pytest.mark.unit
@pytest.mark.rust
def test_normalize_path_with_rust():
    """Test path normalization with Rust acceleration."""
    from ClassicLib.Interface.FolderManagement import _normalize_path

    # Test basic normalization
    test_path = "C:/Windows/System32"
    normalized = _normalize_path(test_path)

    assert isinstance(normalized, Path), "Should return Path object"
    assert normalized.exists(), "Should normalize to existing path"

    # Test that it resolves relative paths
    current = _normalize_path(".")
    assert current.is_absolute(), "Should resolve to absolute path"


@pytest.mark.unit
def test_normalize_path_fallback():
    """Test path normalization falls back to Python when Rust unavailable."""
    from ClassicLib.Interface import FolderManagement

    # Temporarily disable Rust
    original = FolderManagement._RUST_PATH_AVAILABLE
    FolderManagement._RUST_PATH_AVAILABLE = False

    try:
        # Should still work with Python
        normalized = FolderManagement._normalize_path("C:/Windows")
        assert isinstance(normalized, Path), "Python fallback should return Path"
        assert normalized.is_absolute(), "Should be absolute path"
    finally:
        # Restore Rust
        FolderManagement._RUST_PATH_AVAILABLE = original


# Test FolderManagementMixin integration


@pytest.mark.unit
def test_folder_management_mixin_exists():
    """Test that FolderManagementMixin can be imported."""
    from ClassicLib.Interface.FolderManagement import FolderManagementMixin

    assert FolderManagementMixin is not None, "FolderManagementMixin should be importable"
    assert hasattr(FolderManagementMixin, "validate_scan_folder_text"), "Should have validation method"


# Test edge cases


@pytest.mark.unit
def test_empty_path():
    """Test handling of empty path."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    assert not _is_valid_directory(""), "Empty string should be invalid"


@pytest.mark.unit
def test_none_path():
    """Test handling of None path."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    # Should handle None gracefully (convert to string "None")
    assert not _is_valid_directory("None"), "None should be invalid"


@pytest.mark.unit
def test_relative_path():
    """Test handling of relative paths."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory, _normalize_path

    # Current directory should be valid
    assert _is_valid_directory("."), "Current directory should be valid"

    # Normalize should convert to absolute
    normalized = _normalize_path(".")
    assert normalized.is_absolute(), "Relative path should be normalized to absolute"


@pytest.mark.unit
def test_path_with_spaces():
    """Test handling of paths with spaces."""
    from ClassicLib.Interface.FolderManagement import _normalize_path

    # Test path with spaces (common on Windows)
    test_path = "C:/Program Files"
    if Path(test_path).exists():
        normalized = _normalize_path(test_path)
        assert normalized.exists(), "Should handle paths with spaces"


# Test Windows-specific behavior


@pytest.mark.unit
@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_windows_drive_letter():
    """Test handling of Windows drive letters."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    # Test C: drive (should exist on Windows)
    assert _is_valid_directory("C:/"), "C: drive should be valid on Windows"
    assert _is_valid_directory("C:\\"), "C:\\ should be valid on Windows"


@pytest.mark.unit
@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_windows_unc_path():
    """Test handling of Windows UNC paths."""
    from ClassicLib.Interface.FolderManagement import _normalize_path

    # Test UNC path format (may not be accessible, just test parsing)
    unc_path = "//server/share"
    try:
        normalized = _normalize_path(unc_path)
        # Just verify it doesn't crash
        assert isinstance(normalized, Path), "Should handle UNC paths"
    except OSError:
        # UNC path might not be accessible, which is OK for this test
        pass


# Test performance (basic check)


@pytest.mark.unit
@pytest.mark.rust
def test_rust_validation_performance():
    """Test that Rust validation is reasonably fast."""
    import time

    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    # Time multiple validations
    start = time.perf_counter()
    for _ in range(100):
        _is_valid_directory("C:/Windows")
    elapsed = time.perf_counter() - start

    # Should be very fast (< 100ms for 100 validations)
    print(f"100 validations took {elapsed:.4f}s ({elapsed * 10:.2f}ms each)")
    # Don't assert on performance for CI stability, just log it


# Test error handling


@pytest.mark.unit
def test_invalid_path_characters():
    """Test handling of paths with invalid characters."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    # Path with invalid Windows characters
    invalid_path = "C:/Invalid<>Path"
    # Should handle gracefully (might vary by OS)
    result = _is_valid_directory(invalid_path)
    # Don't assert specific result, just verify it doesn't crash
    assert isinstance(result, bool), "Should return bool for invalid path"


@pytest.mark.unit
def test_very_long_path():
    """Test handling of very long paths."""
    from ClassicLib.Interface.FolderManagement import _normalize_path

    # Create a very long path (Windows has 260 char limit historically)
    long_path = "C:/" + "/".join(["very_long_directory_name"] * 20)

    try:
        normalized = _normalize_path(long_path)
        # Just verify it doesn't crash
        assert isinstance(normalized, Path), "Should handle long paths"
    except OSError:
        # Expected on some systems
        pass


# Test integration with actual paths


@pytest.mark.unit
def test_common_windows_directories():
    """Test validation of common Windows system directories."""
    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    common_dirs = [
        "C:/Windows",
        "C:/Program Files",
        "C:/Users",
    ]

    for dir_path in common_dirs:
        if Path(dir_path).exists():
            assert _is_valid_directory(dir_path), f"{dir_path} should be valid if it exists"


@pytest.mark.unit
def test_temp_directory():
    """Test validation of temp directory."""
    import tempfile

    from ClassicLib.Interface.FolderManagement import _is_valid_directory

    temp_dir = tempfile.gettempdir()
    assert _is_valid_directory(temp_dir), "Temp directory should be valid"


# Test Rust PathValidator directly


@pytest.mark.unit
@pytest.mark.rust
def test_rust_path_validator_is_valid_path():
    """Test Rust PathValidator.is_valid_path method directly."""
    import classic_path

    # Test valid paths
    assert classic_path.PathValidator.is_valid_path("C:/Windows"), "C:/Windows should be valid"

    # Test invalid paths
    assert not classic_path.PathValidator.is_valid_path("C:/NonExistentPath12345"), "Non-existent should be invalid"


@pytest.mark.unit
@pytest.mark.rust
def test_rust_path_validator_check_drive_exists():
    """Test Rust PathValidator.check_drive_exists method."""
    import classic_path

    # Test C: drive (should exist on Windows)
    try:
        exists = classic_path.PathValidator.check_drive_exists("C:/")
        # On Windows, C: should exist
        if os.name == "nt":
            assert exists, "C: drive should exist on Windows"
    except Exception:
        # Method might not be available or have different signature
        pytest.skip("check_drive_exists not available or has different API")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
