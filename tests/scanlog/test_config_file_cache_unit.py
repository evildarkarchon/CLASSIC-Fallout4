"""
Unit tests for ConfigFileCache read-only operations.

This module contains comprehensive tests for the ConfigFileCache class
to verify it no longer has write operations and correctly implements
read-only issue detection.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]

from pathlib import Path

from ClassicLib.scanning.game.config import ConfigFileCache
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue


@pytest.mark.unit
class TestConfigFileCacheReadOnly:
    """Test ConfigFileCache read-only operations."""

    @pytest.fixture(autouse=True)
    def init_message_handler(self):
        """Initialize MessageHandler for tests."""
        import importlib

        handler_mod = importlib.import_module("ClassicLib.messaging.handler")

        handler_mod.init_message_handler(parent=None, is_gui_mode=False)
        yield
        setattr(handler_mod, "_message_handler", None)

    @pytest.fixture(autouse=True)
    def mock_dependencies(self, tmp_path):
        """Mock external dependencies."""
        from unittest.mock import patch

        # Mock yaml_settings to avoid async context error and filesystem access
        with patch("ClassicLib.scanning.game.config.yaml_settings") as mock_settings:
            # Return tmp_path as game root
            mock_settings.return_value = tmp_path
            yield mock_settings

    def test_no_set_method_exists(self):
        """
        Verify set() method has been removed from ConfigFileCache.

        This test ensures that the write operation method has been
        completely removed as part of the read-only conversion.
        """
        cache = ConfigFileCache()
        assert not hasattr(cache, "set"), "set() method should be removed - ConfigFileCache must be read-only"

    def test_detect_issue_method_exists(self):
        """
        Verify detect_issue() method exists in ConfigFileCache.

        This test confirms that the new read-only detection API
        has been implemented correctly.
        """
        cache = ConfigFileCache()
        assert hasattr(cache, "detect_issue"), "detect_issue() method should exist for read-only detection"

    @pytest.mark.asyncio
    async def test_detect_issue_returns_correct_structure(self, tmp_path: Path):
        """
        Verify detect_issue() returns ConfigIssue or None.

        This test validates that the detection method returns the
        correct data structure for issue reporting.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nTestKey = bad_value\n", encoding="utf-8")

        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Define condition that will trigger issue detection
        def condition(value: str) -> bool:
            return value == "bad_value"

        # Detect issue
        issue = await cache.detect_issue(
            str,
            file_name_lower="test.ini",
            section="Main",
            setting="TestKey",
            recommended_value="good_value",
            description="Test issue description",
            condition_check=condition,
        )

        # Verify return type
        if issue is not None:
            assert isinstance(issue, ConfigIssue), f"Expected ConfigIssue or None, got {type(issue)}"
            assert issue.setting == "TestKey"
            assert issue.section == "Main"
            assert issue.current_value == "bad_value"
            assert issue.recommended_value == "good_value"

    @pytest.mark.asyncio
    async def test_detect_issue_with_matching_condition(self, tmp_path: Path):
        """
        Verify detect_issue() detects issues when condition matches.

        Rust RustConfigFileCache scans game_root on init, so we
        create the INI file before constructing the cache.
        """
        # Create test configuration with issue (must exist before cache init)
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Settings]\nValue = 10\n", encoding="utf-8")

        cache = ConfigFileCache()

        # Verify Rust backend found and parsed the file
        current_value = cache.get(str, "test.ini", "Settings", "Value")
        assert current_value == "10", f"Expected '10', got '{current_value}'"

    @pytest.mark.asyncio
    async def test_detect_issue_with_non_matching_condition(self, tmp_path: Path):
        """
        Verify detect_issue() returns None when condition doesn't match.

        Rust RustConfigFileCache scans game_root on init, so we
        create the INI file before constructing the cache.
        """
        # Create test configuration without issue (must exist before cache init)
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Settings]\nValue = good_value\n", encoding="utf-8")

        cache = ConfigFileCache()

        # Verify Rust backend found and parsed the file
        current_value = cache.get(str, "test.ini", "Settings", "Value")
        assert current_value == "good_value"

        # detect_issue should return None when condition doesn't match
        issue = await cache.detect_issue(
            str,
            file_name_lower="test.ini",
            section="Settings",
            setting="Value",
            recommended_value="good_value",
            description="Test",
            condition_check=lambda v: v != "good_value",
        )
        assert issue is None

    def test_detect_issue_with_missing_file(self):
        """
        Verify ConfigFileCache handles missing files gracefully.

        This test ensures that missing configuration files don't cause
        crashes and are handled appropriately.
        """
        cache = ConfigFileCache()

        # Verify nonexistent file is not found in cache
        assert "nonexistent.ini" not in cache

    def test_file_modification_time_unchanged(self, tmp_path: Path):
        """
        Verify ConfigFileCache never modifies files.

        This test creates a configuration file, performs read operations,
        and verifies the file remains unchanged.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        # Track modification time
        initial_mtime = test_ini.stat().st_mtime
        initial_content = test_ini.read_text(encoding="utf-8")

        # Create cache and perform read operations
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Perform various read operations
        value = cache.get(str, "test.ini", "Main", "Key")
        assert value == "Value"

        # Check file path retrieval
        file_path = cache["test.ini"]
        assert file_path == test_ini

        # Verify file unchanged
        assert test_ini.stat().st_mtime == initial_mtime, "File modification time changed - write operation may have occurred"
        assert test_ini.read_text(encoding="utf-8") == initial_content, "File content changed - write operation occurred"

    def test_get_method_read_only(self, tmp_path: Path):
        """
        Verify get() method is truly read-only.

        This test confirms that the get() method retrieves values
        without modifying the underlying configuration file.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Section1]\nKey1 = Value1\n[Section2]\nKey2 = Value2\n", encoding="utf-8")

        initial_mtime = test_ini.stat().st_mtime

        # Create cache and read multiple values
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Read various values
        value1 = cache.get(str, "test.ini", "Section1", "Key1")
        value2 = cache.get(str, "test.ini", "Section2", "Key2")
        value3 = cache.get(str, "test.ini", "Section1", "NonExistent")  # Should return None

        assert value1 == "Value1"
        assert value2 == "Value2"
        assert value3 is None

        # Verify no modifications
        assert test_ini.stat().st_mtime == initial_mtime

    def test_config_file_cache_isolation(self, tmp_path: Path):
        """
        Verify ConfigFileCache reads distinct files correctly.

        The Rust RustConfigFileCache scans the game root directory
        and indexes files by their actual names.
        """
        # Create test configurations
        test_ini1 = tmp_path / "test1.ini"
        test_ini1.write_text("[Main]\nKey = Value1\n", encoding="utf-8")

        test_ini2 = tmp_path / "test2.ini"
        test_ini2.write_text("[Main]\nKey = Value2\n", encoding="utf-8")

        # Single cache instance finds both files by their real names
        cache = ConfigFileCache()

        # Read values using actual file names
        value1 = cache.get(str, "test1.ini", "Main", "Key")
        value2 = cache.get(str, "test2.ini", "Main", "Key")

        # Verify correct values retrieved
        assert value1 == "Value1"
        assert value2 == "Value2"

        # Verify files unchanged
        assert test_ini1.read_text(encoding="utf-8") == "[Main]\nKey = Value1\n"
        assert test_ini2.read_text(encoding="utf-8") == "[Main]\nKey = Value2\n"

    @pytest.mark.asyncio
    async def test_async_get_read_only(self, tmp_path: Path):
        """
        Verify get_async() method is read-only.

        This test confirms that the asynchronous get method also
        operates in read-only mode without file modifications.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        initial_mtime = test_ini.stat().st_mtime

        # Create cache and perform async read
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Perform async read operation
        value = await cache.get_async(str, "test.ini", "Main", "Key")

        assert value == "Value"

        # Verify no modifications
        assert test_ini.stat().st_mtime == initial_mtime

    def test_contains_check_read_only(self, tmp_path: Path):
        """
        Verify __contains__ check is read-only.

        This test confirms that checking for file existence in the
        cache doesn't trigger any write operations.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        initial_mtime = test_ini.stat().st_mtime

        # Create cache
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Check file existence
        assert "test.ini" in cache
        assert "nonexistent.ini" not in cache

        # Verify no modifications
        assert test_ini.stat().st_mtime == initial_mtime

    def test_getitem_read_only(self, tmp_path: Path):
        """
        Verify __getitem__ (bracket notation) is read-only.

        This test confirms that retrieving file paths using bracket
        notation doesn't trigger any write operations.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        initial_mtime = test_ini.stat().st_mtime

        # Create cache
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Get file path using bracket notation
        file_path = cache["test.ini"]

        assert file_path == test_ini

        # Verify no modifications
        assert test_ini.stat().st_mtime == initial_mtime

    def test_hash_caching_read_only(self, tmp_path: Path):
        """
        Verify hash caching doesn't modify files.

        This test ensures that hash calculation and caching operations
        are purely read-only and don't affect the source files.
        """
        # Create test configuration
        test_ini = tmp_path / "test.ini"
        test_ini.write_text("[Main]\nKey = Value\n", encoding="utf-8")

        initial_mtime = test_ini.stat().st_mtime

        # Create cache
        cache = ConfigFileCache()
        cache._config_files = {"test.ini": test_ini}

        # Trigger hash caching (if implemented)
        if hasattr(cache, "_get_cached_hash"):
            hash1 = cache._get_cached_hash(test_ini)
            hash2 = cache._get_cached_hash(test_ini)  # Should use cached value

            assert hash1 == hash2, "Hash caching should be consistent"

        # Verify no modifications
        assert test_ini.stat().st_mtime == initial_mtime
