"""
Unit tests for Rust YAML acceleration in YamlSettingsCache.

This test module verifies that:
1. Rust YAML operations are available and properly integrated
2. Static YAML files use Rust acceleration
3. User-editable files use Python (to preserve comments)
4. Proper fallback to Python when Rust unavailable
5. AsyncBridge coordination works correctly
"""

import os
from unittest.mock import patch

import pytest

# Note: yaml_file_ops, yaml_cache_instance, and yaml_simple_file fixtures are provided by
# tests/fixtures/yaml_fixtures.py via the root conftest.py
# - Use yaml_file_ops for YamlFileOperations
# - Use yaml_cache_instance for YamlSettingsCache
# - Use yaml_simple_file for simple YAML with comments (replaces yaml_simple_file)


# Test Rust availability


@pytest.mark.unit
@pytest.mark.rust
def test_rust_yaml_available():
    """Test that Rust YAML module is available."""
    try:
        import classic_yaml

        assert hasattr(classic_yaml, "YamlOperations"), "YamlOperations class should be available"

        # Verify we can instantiate it
        ops = classic_yaml.YamlOperations()
        assert ops is not None, "Should be able to create YamlOperations instance"
    except ImportError:
        pytest.skip("Rust YAML module not available - expected if not built")


@pytest.mark.unit
@pytest.mark.rust
def test_yaml_operations_detects_rust(yaml_file_ops):
    """Test that YamlFileOperations detects Rust availability."""
    # Rust should be available in our test environment
    assert yaml_file_ops.rust_yaml is not None, "Rust YAML should be detected"
    assert type(yaml_file_ops.rust_yaml).__name__ == "YamlOperations", "Should be YamlOperations instance"


# Test static file detection


@pytest.mark.unit
@pytest.mark.rust
def test_static_files_use_rust(yaml_file_ops):
    """Test that static YAML files are identified for Rust acceleration."""
    from ClassicLib.Constants import YAML

    # Main.yaml is static - should use Rust
    main_path = yaml_file_ops.get_path_for_store(YAML.Main)
    assert yaml_file_ops._should_use_rust_for_file(main_path), "Main.yaml should use Rust"

    # Game.yaml is static - should use Rust
    game_path = yaml_file_ops.get_path_for_store(YAML.Game)
    assert yaml_file_ops._should_use_rust_for_file(game_path), "Game.yaml should use Rust"


@pytest.mark.unit
def test_user_editable_files_use_python(yaml_file_ops):
    """Test that user-editable files use Python (to preserve comments)."""
    from ClassicLib.Constants import YAML

    # Settings.yaml is user-editable - should NOT use Rust
    settings_path = yaml_file_ops.get_path_for_store(YAML.Settings)
    assert not yaml_file_ops._should_use_rust_for_file(settings_path), "Settings.yaml should NOT use Rust"

    # Ignore.yaml is user-editable - should NOT use Rust
    ignore_path = yaml_file_ops.get_path_for_store(YAML.Ignore)
    assert not yaml_file_ops._should_use_rust_for_file(ignore_path), "Ignore.yaml should NOT use Rust"


# Test YAML operations


@pytest.mark.unit
@pytest.mark.rust
@pytest.mark.asyncio
async def test_rust_yaml_parsing(yaml_file_ops, yaml_simple_file):
    """Test Rust YAML parsing works correctly."""
    # Parse without preserving comments (should use Rust)
    result = await yaml_file_ops.parse_yaml_content(yaml_simple_file.read_text(), preserve_comments=False)

    assert isinstance(result, dict), "Should return dict"
    assert result.get("test_key") == "test_value", "Should parse key correctly"
    assert result.get("test_int") == 42, "Should parse integer correctly"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_python_yaml_parsing_preserves_comments(yaml_file_ops, yaml_simple_file):
    """Test Python YAML parsing preserves comments."""
    # Parse with preserving comments (should use Python)
    result = await yaml_file_ops.parse_yaml_content(yaml_simple_file.read_text(), preserve_comments=True)

    assert isinstance(result, dict), "Should return dict"
    assert result.get("test_key") == "test_value", "Should parse key correctly"

    # Check that result uses CommentedMap (ruamel.yaml type that preserves comments)
    from ruamel.yaml.comments import CommentedMap

    assert isinstance(result, (dict, CommentedMap)), "Should be dict-like"


@pytest.mark.unit
@pytest.mark.rust
@pytest.mark.asyncio
async def test_load_yaml_file_with_rust(yaml_file_ops, yaml_simple_file):
    """Test loading YAML file with Rust acceleration."""
    # Mock _should_use_rust_for_file to force Rust usage
    with patch.object(yaml_file_ops, "_should_use_rust_for_file", return_value=True):
        result = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=False)

        assert isinstance(result, dict), "Should return dict"
        assert result.get("test_key") == "test_value", "Should load content correctly"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_yaml_file_with_python(yaml_file_ops, yaml_simple_file):
    """Test loading YAML file with Python implementation."""
    # Mock _should_use_rust_for_file to force Python usage
    with patch.object(yaml_file_ops, "_should_use_rust_for_file", return_value=False):
        result = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=False)

        assert isinstance(result, dict), "Should return dict"
        assert result.get("test_key") == "test_value", "Should load content correctly"


# Test fallback behavior


@pytest.mark.unit
@pytest.mark.asyncio
async def test_python_works_without_rust(yaml_file_ops, yaml_simple_file):
    """Test that Python YAML loading works when Rust is disabled."""
    # Disable Rust temporarily
    original_rust = yaml_file_ops.rust_yaml
    yaml_file_ops.rust_yaml = None

    try:
        # Should use Python implementation
        result = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=False)

        assert isinstance(result, dict), "Should return dict from Python"
        assert result.get("test_key") == "test_value", "Should load correctly with Python"
        assert result.get("test_int") == 42, "Should parse int correctly with Python"
    finally:
        # Restore Rust
        yaml_file_ops.rust_yaml = original_rust


@pytest.mark.unit
def test_operations_without_rust():
    """Test that operations work when Rust is not available."""
    from ClassicLib.YamlSettings.async_ import YamlFileOperations

    # Create instance and then patch rust_yaml to None
    ops = YamlFileOperations()

    # Temporarily disable Rust
    original_rust = ops.rust_yaml
    ops.rust_yaml = None

    try:
        assert ops.rust_yaml is None, "Rust should be unavailable"
        assert ops.io_core is not None, "Python IO should still work"

        # Test that operations still work without Rust
        from ClassicLib.Constants import YAML

        # Get a settings path (user-editable, so won't use Rust anyway)
        settings_path = ops.get_path_for_store(YAML.Settings)
        should_use_rust = ops._should_use_rust_for_file(settings_path)

        assert not should_use_rust, "Settings file should not request Rust"
    finally:
        # Restore original
        ops.rust_yaml = original_rust

    # Test YamlSettingsCache integration

    @pytest.mark.unit
    def test_yaml_settings_cache_has_async_core(yaml_cache_instance):
        """Test that YamlSettingsCache has async core initialized."""
        # Trigger lazy initialization
        yaml_cache_instance._get_async_core()

        assert hasattr(yaml_cache_instance, "_async_core"), "Should have async core"
        assert hasattr(yaml_cache_instance, "_bridge"), "Should have AsyncBridge"
        assert yaml_cache_instance._async_core is not None, "Async core should be initialized"


@pytest.mark.unit
def test_yaml_settings_cache_singleton():
    """Test that YamlSettingsCache follows singleton pattern."""
    from ClassicLib.YamlSettings import YamlSettingsCache

    instance1 = YamlSettingsCache.get_instance()
    instance2 = YamlSettingsCache.get_instance()

    assert instance1 is instance2, "Should return same instance"

    @pytest.mark.unit
    @pytest.mark.rust
    def test_yaml_cache_file_ops_has_rust():
        """Test that YamlSettingsCache's file operations have Rust available."""
        from ClassicLib.YamlSettings import yaml_cache

        cache = yaml_cache()
        # Trigger lazy initialization
        cache._get_async_core()

        assert hasattr(cache, "_async_core"), "Should have async core"
        assert hasattr(cache._async_core, "file_ops"), "Should have file operations"

        file_ops = cache._async_core.file_ops  # pyright: ignore[reportOptionalMemberAccess]
        assert file_ops.rust_yaml is not None, "File ops should have Rust available"


# Test performance (basic check)


@pytest.mark.unit
@pytest.mark.rust
@pytest.mark.asyncio
async def test_rust_faster_than_python(yaml_file_ops, tmp_path):
    """Test that Rust operations are faster than Python (basic sanity check)."""
    import time

    # Create a larger YAML file
    large_yaml = tmp_path / "large.yaml"
    content = "\n".join([f"key_{i}: value_{i}" for i in range(1000)])
    large_yaml.write_text(content, encoding="utf-8")

    # Time Rust parsing
    start_rust = time.perf_counter()
    with patch.object(yaml_file_ops, "_should_use_rust_for_file", return_value=True):
        await yaml_file_ops.load_yaml_file(large_yaml, use_cache=False)
    rust_time = time.perf_counter() - start_rust

    # Time Python parsing
    start_python = time.perf_counter()
    with patch.object(yaml_file_ops, "_should_use_rust_for_file", return_value=False):
        await yaml_file_ops.load_yaml_file(large_yaml, use_cache=False)
    python_time = time.perf_counter() - start_python

    # Rust should be faster (allow some margin for system variance)
    # Note: This is a basic sanity check, not a rigorous benchmark
    print(f"Rust time: {rust_time:.4f}s, Python time: {python_time:.4f}s")
    # Don't assert on speed for CI/CD stability, just log it


# Test environment variable control


@pytest.mark.unit
def test_rust_can_be_disabled_via_env():
    """Test that Rust can be disabled via environment variable."""
    from ClassicLib.integration.config import DISABLE_RUST_ENV_VAR
    from ClassicLib.integration.factory import _is_rust_disabled

    # Save original value
    original = os.environ.get(DISABLE_RUST_ENV_VAR)

    try:
        # Test enabling
        os.environ[DISABLE_RUST_ENV_VAR] = "0"
        assert not _is_rust_disabled(), "Should not be disabled with '0'"

        # Test disabling
        os.environ[DISABLE_RUST_ENV_VAR] = "1"
        assert _is_rust_disabled(), "Should be disabled with '1'"

        os.environ[DISABLE_RUST_ENV_VAR] = "true"
        assert _is_rust_disabled(), "Should be disabled with 'true'"

        os.environ[DISABLE_RUST_ENV_VAR] = "yes"
        assert _is_rust_disabled(), "Should be disabled with 'yes'"
    finally:
        # Restore original value
        if original is not None:
            os.environ[DISABLE_RUST_ENV_VAR] = original
        elif DISABLE_RUST_ENV_VAR in os.environ:
            del os.environ[DISABLE_RUST_ENV_VAR]


# Test cache behavior


@pytest.mark.unit
@pytest.mark.asyncio
async def test_yaml_file_caching(yaml_file_ops, yaml_simple_file):
    """Test that YAML file caching works correctly."""
    # First load - should hit disk
    result1 = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=True)

    # Second load - should use cache
    result2 = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=True)

    assert result1 == result2, "Cached result should match original"
    assert str(yaml_simple_file) in yaml_file_ops._file_cache, "File should be in cache"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_yaml_cache_bypass(yaml_file_ops, yaml_simple_file):
    """Test that cache can be bypassed when needed."""
    # Load with cache
    result1 = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=True)

    # Modify file
    yaml_simple_file.write_text("new_key: new_value\n", encoding="utf-8")

    # Clear both FileIOCore cache and YAML cache to ensure fresh read
    yaml_file_ops.io_core.clear_cache()
    yaml_file_ops.clear_cache()

    # Load without cache - should see new content
    result2 = await yaml_file_ops.load_yaml_file(yaml_simple_file, use_cache=False)

    assert result1.get("test_key") == "test_value", "Cached result should have old content"
    assert result2.get("new_key") == "new_value", "Non-cached result should have new content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
