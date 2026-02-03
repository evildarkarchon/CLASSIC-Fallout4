"""Unit tests for YAML cache Rust delegation.

Verifies YamlSettingsCache and AsyncYamlSettingsCore correctly delegate
to Rust classic_settings module per Phase 6 requirements.

SETT-01: Settings cache uses Rust DashMap, not Python dict
SETT-02: Cache clear operations delegate to Rust
SETT-03: Batch loading uses Rust with tokio parallelism
"""

from pathlib import Path

import pytest
import classic_settings

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml.cache import YamlSettingsCache


pytestmark = pytest.mark.unit


class TestYamlSettingsCacheRustDelegation:
    """Test YamlSettingsCache delegates to Rust classic_settings."""

    def test_debug_info_returns_rust_cache_state(self) -> None:
        """Verify debug_info() calls Rust cache_size and cache_keys.

        SETT-01: debug_info() exposes Rust cache state for debugging.
        """
        info = YamlSettingsCache.debug_info()
        assert "cache_size" in info
        assert "cache_keys" in info
        assert isinstance(info["cache_size"], int)
        assert isinstance(info["cache_keys"], list)

    def test_load_yaml_calls_rust_load_settings_sync(self, tmp_path: Path) -> None:
        """Verify load_yaml calls classic_settings.load_settings_sync.

        SETT-01: load_yaml() delegates to Rust for caching.
        """
        # Create a test YAML file
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\n", encoding="utf-8")

        # Clear cache first
        classic_settings.clear_cache()

        cache = YamlSettingsCache.get_instance()
        # This should go through Rust
        result = cache.load_yaml(yaml_file)

        # Verify Rust cached it
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key), "File should be cached in Rust"
        assert result.get("key") == "value"

    def test_invalidate_calls_rust_invalidate(self, tmp_path: Path) -> None:
        """Verify invalidate() calls classic_settings.invalidate.

        SETT-02: invalidate() removes specific entry from Rust cache.
        """
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\n", encoding="utf-8")

        classic_settings.clear_cache()
        cache = YamlSettingsCache.get_instance()

        # Load to cache
        cache.load_yaml(yaml_file)
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key), "Should be cached after load"

        # Invalidate
        result = cache.invalidate(key)
        assert result is True, "invalidate() should return True when key existed"
        assert not classic_settings.is_cached(key), "Should not be cached after invalidate"

    def test_invalidate_returns_false_for_nonexistent_key(self) -> None:
        """Verify invalidate() returns False for non-existent keys."""
        cache = YamlSettingsCache.get_instance()
        result = cache.invalidate("nonexistent_key_12345")
        assert result is False, "invalidate() should return False for non-existent key"

    def test_rust_error_raises_runtime_error(self) -> None:
        """Verify Rust errors surface as RuntimeError with details.

        SETT-01: Hard error on Rust failure, no silent fallback.
        """
        cache = YamlSettingsCache.get_instance()
        nonexistent = Path("/nonexistent/path/12345/file.yaml")

        with pytest.raises((RuntimeError, IOError)):
            cache.load_yaml(nonexistent)

    def test_load_yaml_returns_first_document(self, tmp_path: Path) -> None:
        """Verify load_yaml returns first document from multi-doc YAML."""
        yaml_file = tmp_path / "multi_doc.yaml"
        yaml_file.write_text("doc1_key: doc1_value\n---\ndoc2_key: doc2_value\n", encoding="utf-8")

        classic_settings.clear_cache()
        cache = YamlSettingsCache.get_instance()

        result = cache.load_yaml(yaml_file)
        assert result.get("doc1_key") == "doc1_value", "Should return first document"

    def test_debug_info_reflects_cache_changes(self, tmp_path: Path) -> None:
        """Verify debug_info() accurately reflects cache state changes."""
        classic_settings.clear_cache()

        # Initially empty
        info = YamlSettingsCache.debug_info()
        assert info["cache_size"] == 0
        assert len(info["cache_keys"]) == 0

        # Add a file
        yaml_file = tmp_path / "debug_test.yaml"
        yaml_file.write_text("test: data\n", encoding="utf-8")

        cache = YamlSettingsCache.get_instance()
        cache.load_yaml(yaml_file)

        info = YamlSettingsCache.debug_info()
        assert info["cache_size"] == 1
        assert len(info["cache_keys"]) == 1
        assert str(yaml_file.resolve()) in info["cache_keys"]


@pytest.mark.asyncio
class TestAsyncYamlSettingsCoreRustDelegation:
    """Test AsyncYamlSettingsCore delegates to Rust classic_settings."""

    async def test_load_yaml_async_uses_rust_cache(self, tmp_path: Path) -> None:
        """Verify async loading goes through Rust cache.

        SETT-01: Async operations use Rust cache.
        """
        from ClassicLib.io.yaml.cache import YamlSettingsCache

        yaml_file = tmp_path / "async_test.yaml"
        yaml_file.write_text("async_key: async_value\n", encoding="utf-8")

        classic_settings.clear_cache()
        cache = YamlSettingsCache.get_instance()

        # Load via async method
        result = await cache.load_yaml_async(yaml_file)

        # Verify Rust cached it
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key), "File should be cached in Rust"
        assert result.get("async_key") == "async_value"

    async def test_clear_cache_clears_rust_cache(self, tmp_path: Path) -> None:
        """Verify clear_cache() calls classic_settings.clear_cache().

        SETT-02: clear_cache() delegates to Rust.
        """
        from ClassicLib.io.yaml.async_.core import get_async_yaml_core

        yaml_file = tmp_path / "clear_test.yaml"
        yaml_file.write_text("clear_key: clear_value\n", encoding="utf-8")

        # Load something
        cache = YamlSettingsCache.get_instance()
        await cache.load_yaml_async(yaml_file)
        assert classic_settings.cache_size() > 0, "Should have entries before clear"

        # Clear all via async core
        core = await get_async_yaml_core()
        await core.clear_cache()

        # Rust cache should be empty
        assert classic_settings.cache_size() == 0, "Rust cache should be empty after clear"

    async def test_async_settings_read_uses_rust_cache(self, tmp_path: Path) -> None:
        """Verify async_yaml_settings READ path uses Rust cache.

        SETT-01: Settings reads go through Rust cache.
        """
        from ClassicLib.io.yaml.async_.core import get_async_yaml_core

        yaml_file = tmp_path / "settings_test.yaml"
        yaml_file.write_text("section:\n  key: value123\n", encoding="utf-8")

        classic_settings.clear_cache()

        core = await get_async_yaml_core()

        # Mock path resolution to use our test file
        def mock_get_path(store):
            return yaml_file

        core.file_ops.get_path_for_store = mock_get_path

        # Read setting
        result = await core.async_yaml_settings(str, YAML.TEST, "section.key")
        assert result == "value123"

        # Verify cached in Rust
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key)

    async def test_async_settings_write_invalidates_rust_cache(self, tmp_path: Path) -> None:
        """Verify async_yaml_settings WRITE path invalidates Rust cache.

        SETT-02: After write, Rust cache is invalidated for consistency.
        """
        from ClassicLib.io.yaml.async_.core import get_async_yaml_core

        yaml_file = tmp_path / "write_test.yaml"
        yaml_file.write_text("section:\n  key: old_value\n", encoding="utf-8")

        classic_settings.clear_cache()

        core = await get_async_yaml_core()

        def mock_get_path(store):
            return yaml_file

        core.file_ops.get_path_for_store = mock_get_path

        # Read to populate cache
        await core.async_yaml_settings(str, YAML.TEST, "section.key")
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key), "Should be cached after read"

        # Write operation
        await core.async_yaml_settings(str, YAML.TEST, "section.key", "new_value")

        # After write, cache should be invalidated
        assert not classic_settings.is_cached(key), "Cache should be invalidated after write"

    async def test_reload_settings_uses_rust_cache(self, tmp_path: Path) -> None:
        """Verify reload_settings invalidates and reloads via Rust.

        SETT-02: reload_settings() uses Rust cache operations.
        """
        from ClassicLib.io.yaml.async_.core import get_async_yaml_core

        yaml_file = tmp_path / "reload_test.yaml"
        yaml_file.write_text("reload_key: original\n", encoding="utf-8")

        classic_settings.clear_cache()

        core = await get_async_yaml_core()

        def mock_get_path(store):
            return yaml_file

        core.file_ops.get_path_for_store = mock_get_path

        # Load initially
        await core.async_yaml_settings(str, YAML.TEST, "reload_key")
        key = str(yaml_file.resolve())
        assert classic_settings.is_cached(key)

        # Modify file
        yaml_file.write_text("reload_key: updated\n", encoding="utf-8")

        # Reload should get fresh data
        data = await core.reload_settings(YAML.TEST)
        assert data.get("reload_key") == "updated"

        # Should be re-cached in Rust
        assert classic_settings.is_cached(key)


class TestBatchLoadingRustDelegation:
    """Test batch loading uses Rust with tokio parallelism.

    SETT-03: Batch loading uses Rust load_batch_sync/load_batch_async.
    """

    def test_prefetch_uses_rust_batch_loading(self, tmp_path: Path, monkeypatch) -> None:
        """Verify prefetch_all_settings uses Rust load_batch_sync."""
        classic_settings.clear_cache()

        # Create test files
        main_file = tmp_path / "CLASSIC Main.yaml"
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        game_file = tmp_path / "CLASSIC Fallout4.yaml"

        main_file.write_text("main: data\n", encoding="utf-8")
        settings_file.write_text("settings: data\n", encoding="utf-8")
        game_file.write_text("game: data\n", encoding="utf-8")

        cache = YamlSettingsCache.get_instance()
        core = cache._get_async_core()

        # Mock path resolution
        def mock_get_path(store):
            if store == YAML.Main:
                return main_file
            elif store == YAML.Settings:
                return settings_file
            elif store == YAML.Game:
                return game_file
            return tmp_path / "nonexistent.yaml"

        core.file_ops.get_path_for_store = mock_get_path

        # Prefetch
        cache.prefetch_all_settings()

        # All three should be cached in Rust
        assert classic_settings.cache_size() >= 3, "Should have at least 3 entries from prefetch"
