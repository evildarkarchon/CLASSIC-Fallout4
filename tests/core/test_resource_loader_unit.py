"""Unit tests for ClassicLib.support.resources module.

This module provides comprehensive tests for the ResourceLoader class,
covering all path detection strategies, frozen executable detection,
package installation detection, and cache management functionality.
"""

import asyncio
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.resources import ResourceLoader, get_resource_path, is_frozen

# ============================================================================
# Frozen Executable Detection Tests
# ============================================================================


@pytest.mark.unit
class TestCheckExecutableDirectory:
    """Tests for _check_executable_directory() method."""

    def test_returns_none_when_not_frozen(self) -> None:
        """Should return None when not running as frozen executable."""
        # Ensure sys.frozen is not set
        with patch.object(sys, "frozen", False, create=True):
            result = ResourceLoader._check_executable_directory()
            assert result is None

    def test_returns_path_when_frozen_and_data_exists(self, tmp_path: Path) -> None:
        """Should return path when running as frozen exe and CLASSIC Data exists."""
        # Create CLASSIC Data directory
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        # Mock frozen executable
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", str(tmp_path / "CLASSIC.exe")),
        ):
            result = ResourceLoader._check_executable_directory()
            assert result == data_dir

    def test_returns_none_when_frozen_but_data_missing(self, tmp_path: Path) -> None:
        """Should return None when frozen but CLASSIC Data doesn't exist."""
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", str(tmp_path / "CLASSIC.exe")),
        ):
            result = ResourceLoader._check_executable_directory()
            assert result is None


@pytest.mark.unit
class TestCheckFrozenBundle:
    """Tests for _check_frozen_bundle() method."""

    def test_returns_none_when_not_frozen(self) -> None:
        """Should return None when not running as frozen executable."""
        with patch.object(sys, "frozen", False, create=True):
            result = ResourceLoader._check_frozen_bundle()
            assert result is None

    def test_returns_none_when_frozen_but_no_meipass(self) -> None:
        """Should return None when frozen but _MEIPASS not available."""
        with patch.object(sys, "frozen", True, create=True):
            # Ensure _MEIPASS is not set
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
            result = ResourceLoader._check_frozen_bundle()
            assert result is None

    def test_returns_path_when_frozen_with_meipass_and_data_exists(self, tmp_path: Path) -> None:
        """Should return path when frozen with MEIPASS and CLASSIC Data exists."""
        # Create CLASSIC Data in temp path
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(tmp_path), create=True),
        ):
            result = ResourceLoader._check_frozen_bundle()
            assert result == data_dir

    def test_returns_none_when_frozen_meipass_but_data_missing(self, tmp_path: Path) -> None:
        """Should return None when frozen with MEIPASS but no CLASSIC Data."""
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(tmp_path), create=True),
        ):
            result = ResourceLoader._check_frozen_bundle()
            assert result is None


# ============================================================================
# Local Directory Detection Tests
# ============================================================================


@pytest.mark.unit
class TestCheckLocalDir:
    """Tests for _check_local_dir() method."""

    def test_returns_none_when_local_dir_not_set(self) -> None:
        """Should return None when LOCAL_DIR is not set in GlobalRegistry."""
        # Patch the module-level function that was imported into resources.py,
        # not the class method on GlobalRegistry (which the production code doesn't use).
        with patch("ClassicLib.support.resources.get_local_dir", return_value=None):
            result = ResourceLoader._check_local_dir()
            assert result is None

    def test_returns_path_when_local_dir_set_and_data_exists(self, tmp_path: Path) -> None:
        """Should return path when LOCAL_DIR is set and CLASSIC Data exists."""
        # Create CLASSIC Data directory
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        # Patch the module-level function imported into resources.py
        with patch("ClassicLib.support.resources.get_local_dir", return_value=tmp_path):
            result = ResourceLoader._check_local_dir()
            assert result == data_dir

    def test_returns_path_even_when_data_not_exists(self, tmp_path: Path) -> None:
        """Should return constructed path even when CLASSIC Data doesn't exist.

        Note: The method returns the potential path for the caller to check/create.
        The exists() check is only for logging purposes.
        """
        # Use a path that doesn't have CLASSIC Data
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        # Patch the module-level function imported into resources.py
        with patch("ClassicLib.support.resources.get_local_dir", return_value=empty_dir):
            result = ResourceLoader._check_local_dir()
            # Method returns the path even if it doesn't exist
            assert result == empty_dir / "CLASSIC Data"
            assert not result.exists()

    def test_returns_none_on_oserror(self) -> None:
        """Should return None when OSError is raised during path operations."""
        # Patch the module-level function imported into resources.py
        with patch("ClassicLib.support.resources.get_local_dir", return_value="/some/path"):
            with patch("pathlib.Path.exists", side_effect=OSError("permission denied")):
                result = ResourceLoader._check_local_dir()
                assert result is None


# ============================================================================
# Package Installation Detection Tests
# ============================================================================


@pytest.mark.unit
class TestGetDistribution:
    """Tests for _get_distribution() method."""

    def test_returns_distribution_for_known_package(self) -> None:
        """Should return distribution when package is installed."""
        mock_dist = MagicMock()

        with patch("ClassicLib.support.resources.distribution", return_value=mock_dist) as mock_distribution:
            result = ResourceLoader._get_distribution()
            assert result == mock_dist
            # Check it tried classic-fallout4 first
            mock_distribution.assert_called()

    def test_returns_none_when_package_not_found(self) -> None:
        """Should return None when no package variant is found."""
        with patch(
            "ClassicLib.support.resources.distribution",
            side_effect=PackageNotFoundError("not found"),
        ):
            result = ResourceLoader._get_distribution()
            assert result is None

    def test_handles_import_error(self) -> None:
        """Should return None gracefully on ImportError."""
        with patch("ClassicLib.support.resources.distribution", side_effect=ImportError("error")):
            result = ResourceLoader._get_distribution()
            assert result is None

    def test_tries_multiple_package_names(self) -> None:
        """Should try multiple package name variations."""
        mock_dist = MagicMock()
        call_count = 0

        def side_effect(name: str) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if name == "classic":
                return mock_dist
            raise PackageNotFoundError(name)

        with patch("ClassicLib.support.resources.distribution", side_effect=side_effect):
            result = ResourceLoader._get_distribution()
            assert result == mock_dist
            assert call_count == 3  # Tried all three variants


@pytest.mark.unit
class TestCheckPackageLocation:
    """Tests for _check_package_location() method."""

    def test_returns_path_when_data_dir_exists(self, tmp_path: Path) -> None:
        """Should return path when CLASSIC Data exists in package location."""
        # Create CLASSIC Data directory
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        mock_dist = MagicMock()
        mock_dist.locate_file.return_value = str(tmp_path)

        result = ResourceLoader._check_package_location(mock_dist)
        assert result == data_dir

    def test_returns_none_when_data_dir_missing(self, tmp_path: Path) -> None:
        """Should return None when CLASSIC Data doesn't exist."""
        mock_dist = MagicMock()
        mock_dist.locate_file.return_value = str(tmp_path)

        result = ResourceLoader._check_package_location(mock_dist)
        assert result is None

    def test_handles_attribute_error(self) -> None:
        """Should return None on AttributeError."""
        mock_dist = MagicMock()
        mock_dist.locate_file.side_effect = AttributeError("no attribute")

        result = ResourceLoader._check_package_location(mock_dist)
        assert result is None


@pytest.mark.unit
class TestCheckPackageInstallation:
    """Tests for _check_package_installation() method."""

    def test_returns_none_when_no_distribution(self) -> None:
        """Should return None when distribution not available."""
        with patch.object(ResourceLoader, "_get_distribution", return_value=None):
            result = ResourceLoader._check_package_installation()
            assert result is None

    def test_returns_package_location_path(self, tmp_path: Path) -> None:
        """Should return path from package location when available."""
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        mock_dist = MagicMock()

        with (
            patch.object(ResourceLoader, "_get_distribution", return_value=mock_dist),
            patch.object(ResourceLoader, "_check_package_location", return_value=data_dir),
        ):
            result = ResourceLoader._check_package_installation()
            assert result == data_dir

    def test_falls_back_to_extract(self, tmp_path: Path) -> None:
        """Should fall back to extraction when package location fails."""
        data_dir = tmp_path / "extracted" / "CLASSIC Data"
        data_dir.mkdir(parents=True)

        mock_dist = MagicMock()

        with (
            patch.object(ResourceLoader, "_get_distribution", return_value=mock_dist),
            patch.object(ResourceLoader, "_check_package_location", return_value=None),
            patch.object(ResourceLoader, "_extract_from_package", return_value=data_dir),
        ):
            result = ResourceLoader._check_package_installation()
            assert result == data_dir


# ============================================================================
# Source Installation Detection Tests
# ============================================================================


@pytest.mark.unit
class TestCheckSourceInstallation:
    """Tests for _check_source_installation() method."""

    def test_returns_path_when_data_exists_in_module_parent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return path when CLASSIC Data exists in module parent directory."""
        # Create mock module structure
        module_dir = tmp_path / "ClassicLib"
        module_dir.mkdir()
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        # Mock __file__ to point to our temp location
        with patch("ClassicLib.support.resources.__file__", str(module_dir / "ResourceLoader.py")):
            result = ResourceLoader._check_source_installation()
            assert result == data_dir

    def test_returns_none_when_data_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when CLASSIC Data doesn't exist in module parent."""
        module_dir = tmp_path / "ClassicLib"
        module_dir.mkdir()

        with patch("ClassicLib.support.resources.__file__", str(module_dir / "ResourceLoader.py")):
            result = ResourceLoader._check_source_installation()
            assert result is None


@pytest.mark.unit
class TestCheckCurrentDirectory:
    """Tests for _check_current_directory() method."""

    def test_returns_path_when_data_exists_in_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return path when CLASSIC Data exists in current directory."""
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        monkeypatch.chdir(tmp_path)

        result = ResourceLoader._check_current_directory()
        assert result == data_dir

    def test_returns_none_when_data_missing_in_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when CLASSIC Data doesn't exist in current directory."""
        monkeypatch.chdir(tmp_path)

        result = ResourceLoader._check_current_directory()
        assert result is None


# ============================================================================
# App Data Creation Tests
# ============================================================================


@pytest.mark.unit
class TestCreateInAppData:
    """Tests for _create_in_app_data() method."""

    def test_creates_directory_in_app_data(self, tmp_path: Path) -> None:
        """Should create CLASSIC Data directory in app data location."""
        with patch("appdirs.user_data_dir", return_value=str(tmp_path)):
            result = ResourceLoader._create_in_app_data()
            assert result.exists()
            assert result.name == "CLASSIC Data"

    def test_falls_back_to_cwd_on_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should fall back to current directory on OSError."""
        monkeypatch.chdir(tmp_path)

        with patch("appdirs.user_data_dir", side_effect=OSError("permission denied")):
            result = ResourceLoader._create_in_app_data()
            assert result.exists()
            assert result == tmp_path / "CLASSIC Data"


# ============================================================================
# Main Entry Point Tests
# ============================================================================


@pytest.mark.unit
class TestGetDataDirectory:
    """Tests for get_data_directory() main entry point."""

    def test_returns_first_successful_strategy(self, tmp_path: Path) -> None:
        """Should return result from first successful strategy."""
        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        with patch.object(ResourceLoader, "_check_executable_directory", return_value=data_dir):
            result = ResourceLoader.get_data_directory()
            assert result == data_dir

    def test_tries_all_strategies_in_order(self) -> None:
        """Should try strategies in priority order until one succeeds."""
        strategies_called = []

        def make_tracker(name: str, return_value: Any) -> Any:
            def tracker() -> Any:
                strategies_called.append(name)
                return return_value

            return tracker

        with (
            patch.object(
                ResourceLoader,
                "_check_executable_directory",
                make_tracker("executable", None),
            ),
            patch.object(ResourceLoader, "_check_local_dir", make_tracker("local", None)),
            patch.object(ResourceLoader, "_check_source_installation", make_tracker("source", Path("/found"))),
        ):
            ResourceLoader.get_data_directory()
            assert strategies_called == ["executable", "local", "source"]

    def test_creates_app_data_as_last_resort(self, tmp_path: Path) -> None:
        """Should create app data directory when all strategies fail."""
        with (
            patch.object(ResourceLoader, "_check_executable_directory", return_value=None),
            patch.object(ResourceLoader, "_check_local_dir", return_value=None),
            patch.object(ResourceLoader, "_check_source_installation", return_value=None),
            patch.object(ResourceLoader, "_check_current_directory", return_value=None),
            patch.object(ResourceLoader, "_check_frozen_bundle", return_value=None),
            patch.object(ResourceLoader, "_check_package_installation", return_value=None),
            patch.object(
                ResourceLoader,
                "_create_in_app_data",
                return_value=tmp_path / "CLASSIC Data",
            ),
        ):
            result = ResourceLoader.get_data_directory()
            assert result == tmp_path / "CLASSIC Data"


# ============================================================================
# Data Extraction Tests
# ============================================================================


@pytest.mark.unit
class TestExtractFromPackage:
    """Tests for _extract_from_package() method."""

    def test_returns_none_when_package_files_unavailable(self) -> None:
        """Should return None when package files cannot be accessed."""
        with patch("ClassicLib.support.resources.files", side_effect=ModuleNotFoundError()):
            result = ResourceLoader._extract_from_package()
            assert result is None

    def test_returns_none_when_classic_data_not_in_package(self) -> None:
        """Should return None when CLASSIC Data not found in package."""
        mock_files = MagicMock()
        mock_classic_data = MagicMock()
        mock_classic_data.is_dir.return_value = False
        mock_files.__truediv__ = MagicMock(return_value=mock_classic_data)

        with patch("ClassicLib.support.resources.files", return_value=mock_files):
            result = ResourceLoader._extract_from_package()
            assert result is None

    def test_extracts_to_stable_location(self, tmp_path: Path) -> None:
        """Should extract package data to stable app data location."""
        mock_files = MagicMock()
        mock_classic_data = MagicMock()
        mock_classic_data.is_dir.return_value = True
        mock_files.__truediv__ = MagicMock(return_value=mock_classic_data)

        data_dir = tmp_path / "CLASSIC Data"
        data_dir.mkdir()

        with (
            patch("ClassicLib.support.resources.files", return_value=mock_files),
            patch("appdirs.user_data_dir", return_value=str(tmp_path)),
            patch.object(ResourceLoader, "_extract_bundled_data_importlib"),
        ):
            result = ResourceLoader._extract_from_package()
            assert result == data_dir


@pytest.mark.unit
class TestExtractBundledDataImportlib:
    """Tests for _extract_bundled_data_importlib() method."""

    def test_extracts_essential_files(self, tmp_path: Path) -> None:
        """Should extract essential YAML files to target directory."""
        # Create mock package structure
        mock_package = MagicMock()

        def make_resource(is_file: bool, content: bytes = b"test content") -> MagicMock:
            resource = MagicMock()
            resource.is_file.return_value = is_file
            resource.read_bytes.return_value = content
            return resource

        def joinpath_handler(part: str) -> MagicMock:
            if part == "databases":
                db_mock = MagicMock()
                db_mock.joinpath = lambda f: make_resource(True, f"content of {f}".encode())
                return db_mock
            return make_resource(False)

        mock_classic_data = MagicMock()
        mock_classic_data.joinpath = joinpath_handler
        mock_package.joinpath = lambda p: mock_classic_data if p == "CLASSIC Data" else MagicMock()

        ResourceLoader._extract_bundled_data_importlib(tmp_path, mock_package)

        # Verify directories were created
        databases_dir = tmp_path / "databases"
        assert databases_dir.exists()

    def test_handles_missing_resources(self, tmp_path: Path) -> None:
        """Should handle missing resources gracefully."""
        mock_package = MagicMock()

        def make_not_found_resource() -> MagicMock:
            resource = MagicMock()
            resource.is_file.return_value = False
            return resource

        mock_package.joinpath = lambda _p: make_not_found_resource()

        # Should not raise
        ResourceLoader._extract_bundled_data_importlib(tmp_path, mock_package)


# ============================================================================
# Essential Files Tests
# ============================================================================


@pytest.mark.unit
class TestEnsureDataFilesExist:
    """Tests for ensure_data_files_exist() method."""

    def test_returns_data_directory(self, tmp_path: Path) -> None:
        """Should return the data directory path."""
        with patch.object(ResourceLoader, "get_data_directory", return_value=tmp_path):
            result = ResourceLoader.ensure_data_files_exist()
            assert result == tmp_path

    def test_logs_warning_for_missing_files(self, tmp_path: Path) -> None:
        """Should log warning when essential files are missing."""
        with (
            patch.object(ResourceLoader, "get_data_directory", return_value=tmp_path),
            patch("ClassicLib.support.resources.logger") as mock_logger,
        ):
            ResourceLoader.ensure_data_files_exist()
            mock_logger.warning.assert_called()

    def test_no_warning_when_files_exist(self, tmp_path: Path) -> None:
        """Should not log warning when essential files exist."""
        # Create essential files
        databases_dir = tmp_path / "databases"
        databases_dir.mkdir()
        (databases_dir / "CLASSIC Main.yaml").write_text("test")
        (databases_dir / "CLASSIC Fallout4.yaml").write_text("test")

        with (
            patch.object(ResourceLoader, "get_data_directory", return_value=tmp_path),
            patch("ClassicLib.support.resources.logger") as mock_logger,
        ):
            ResourceLoader.ensure_data_files_exist()
            mock_logger.warning.assert_not_called()


# ============================================================================
# Cached Game Path Tests
# ============================================================================


@pytest.mark.unit
class TestGetCachedGamePath:
    """Tests for get_cached_game_path() method."""

    def test_returns_path_from_environment_variable(self, tmp_path: Path) -> None:
        """Should return path from environment variable when set."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        with patch.dict("os.environ", {"CLASSIC_FALLOUT4_PATH": str(tmp_path)}):
            # Ensure the path exists
            result = ResourceLoader.get_cached_game_path("Fallout4", "")
            assert result == tmp_path

    def test_returns_none_when_env_path_missing(self) -> None:
        """Should return None when environment path doesn't exist."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Patch yaml_settings at both import locations used by get_cached_game_path:
        # Strategy 2 imports from ClassicLib.io.yaml.convenience
        # Strategy 3 imports from ClassicLib.io.yaml
        with (
            patch.dict("os.environ", {"CLASSIC_FALLOUT4_PATH": "/nonexistent/path"}, clear=True),
            patch("ClassicLib.io.yaml.convenience.yaml_settings", return_value=None),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=None),
        ):
            result = ResourceLoader.get_cached_game_path("Fallout4", "")
            assert result is None

    def test_checks_cache_yaml_second(self, tmp_path: Path) -> None:
        """Should check cache.yaml when environment variable not set."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Strategy 2 uses ClassicLib.io.yaml.convenience.yaml_settings
        # Strategy 3 uses ClassicLib.io.yaml.yaml_settings
        # Patch both to ensure consistent behavior
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("ClassicLib.io.yaml.convenience.yaml_settings", return_value=str(tmp_path)),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=str(tmp_path)),
        ):
            result = ResourceLoader.get_cached_game_path("Fallout4", "")
            assert result == tmp_path

    def test_checks_local_yaml_third(self, tmp_path: Path) -> None:
        """Should check Local.yaml as third strategy."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Strategy 2 imports yaml_settings from ClassicLib.io.yaml.convenience
        # Strategy 3 imports yaml_settings from ClassicLib.io.yaml
        # We want Strategy 2 (cache.yaml) to return None and Strategy 3 (Local.yaml)
        # to return the path. Since they import from different modules, we can patch
        # each independently.
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("ClassicLib.io.yaml.convenience.yaml_settings", return_value=None),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=str(tmp_path)),
        ):
            result = ResourceLoader.get_cached_game_path("Fallout4", "")
            assert result == tmp_path

    def test_returns_none_when_all_strategies_fail(self) -> None:
        """Should return None when no strategy finds a valid path."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Patch yaml_settings at both import locations used by get_cached_game_path
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("ClassicLib.io.yaml.convenience.yaml_settings", return_value=None),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=None),
        ):
            result = ResourceLoader.get_cached_game_path("Fallout4", "")
            assert result is None

    def test_uses_default_game_when_none_provided(self) -> None:
        """Should use GlobalRegistry game when game_name is None."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Skyrim")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Patch yaml_settings at both import locations used by get_cached_game_path
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("ClassicLib.io.yaml.convenience.yaml_settings", return_value=None),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=None),
        ):
            ResourceLoader.get_cached_game_path(None, "")
            # Should have tried to read Skyrim path


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetCachedGamePathAsync:
    """Tests for get_cached_game_path_async() method."""

    async def test_returns_path_from_environment_variable(self, tmp_path: Path) -> None:
        """Should return path from environment variable when set."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        with patch.dict("os.environ", {"CLASSIC_FALLOUT4_PATH": str(tmp_path)}):
            result = await ResourceLoader.get_cached_game_path_async("Fallout4", "")
            assert result == tmp_path

    async def test_uses_async_yaml_settings(self, tmp_path: Path) -> None:
        """Should use yaml_settings_async for YAML access."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        async def mock_yaml_async(*args: Any, **kwargs: Any) -> str:
            return str(tmp_path)

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "ClassicLib.io.yaml.yaml_settings_async",
                side_effect=mock_yaml_async,
            ),
        ):
            result = await ResourceLoader.get_cached_game_path_async("Fallout4", "")
            assert result == tmp_path


# ============================================================================
# Cached Docs Path Tests
# ============================================================================


@pytest.mark.unit
class TestGetCachedDocsPath:
    """Tests for get_cached_docs_path() method."""

    def test_returns_path_from_environment_variable(self, tmp_path: Path) -> None:
        """Should return path from environment variable when set."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        with patch.dict("os.environ", {"CLASSIC_FALLOUT4_DOCS": str(tmp_path)}):
            result = ResourceLoader.get_cached_docs_path("Fallout4", "")
            assert result == tmp_path

    def test_skips_yaml_in_async_context(self) -> None:
        """Should skip YAML checks when called from async context."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        # Create a mock event loop to simulate async context
        loop = asyncio.new_event_loop()
        try:
            with (
                patch.dict("os.environ", {}, clear=True),
                patch("asyncio.get_running_loop", return_value=loop),
            ):
                result = ResourceLoader.get_cached_docs_path("Fallout4", "")
                assert result is None  # Should skip YAML checks
        finally:
            loop.close()

    def test_checks_yaml_in_sync_context(self, tmp_path: Path) -> None:
        """Should check YAML when not in async context."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")),
            patch("ClassicLib.io.yaml.yaml_settings", return_value=str(tmp_path)),
        ):
            result = ResourceLoader.get_cached_docs_path("Fallout4", "")
            assert result == tmp_path


# ============================================================================
# Save Path to Cache Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestSavePathToCacheAsync:
    """Tests for save_path_to_cache_async() method."""

    async def test_saves_game_path_to_both_caches(self, tmp_path: Path) -> None:
        """Should save GamePath to both cache.yaml and Local.yaml."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        calls: list[tuple[Any, ...]] = []

        async def mock_yaml_async(*args: Any, **kwargs: Any) -> None:
            calls.append(args)

        with patch(
            "ClassicLib.io.yaml.yaml_settings_async",
            side_effect=mock_yaml_async,
        ):
            await ResourceLoader.save_path_to_cache_async(tmp_path, "GamePath", "Fallout4", "")
            assert len(calls) == 2  # cache.yaml and Local.yaml

    async def test_saves_docs_path_correctly(self, tmp_path: Path) -> None:
        """Should save DocsPath with correct key in Local.yaml."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        calls: list[tuple[Any, ...]] = []

        async def mock_yaml_async(*args: Any, **kwargs: Any) -> None:
            calls.append(args)

        with patch(
            "ClassicLib.io.yaml.yaml_settings_async",
            side_effect=mock_yaml_async,
        ):
            await ResourceLoader.save_path_to_cache_async(tmp_path, "DocsPath", "Fallout4", "")
            # Check that Root_Folder_Docs key was used
            assert any("Root_Folder_Docs" in str(call) for call in calls)


@pytest.mark.unit
class TestSavePathToCache:
    """Tests for save_path_to_cache() sync method."""

    def test_saves_path_in_sync_context(self, tmp_path: Path) -> None:
        """Should save path when called from sync context."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        with (
            patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")),
            patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml,
        ):
            ResourceLoader.save_path_to_cache(tmp_path, "GamePath", "Fallout4", "")
            assert mock_yaml.called

    def test_creates_task_in_async_context(self, tmp_path: Path) -> None:
        """Should create async task when called from async context."""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

        mock_loop = MagicMock()

        def close_coroutine(coro):
            """Close the coroutine to prevent 'never awaited' warning."""
            coro.close()
            return MagicMock()

        with (
            patch("asyncio.get_running_loop", return_value=mock_loop),
            patch("asyncio.create_task", side_effect=close_coroutine) as mock_create_task,
        ):
            ResourceLoader.save_path_to_cache(tmp_path, "GamePath", "Fallout4", "")
            mock_create_task.assert_called_once()


# ============================================================================
# Rust Extension Tests
# ============================================================================


@pytest.mark.unit
class TestLoadRustExtension:
    """Tests for load_rust_extension() method."""

    def test_returns_true_when_rust_already_loaded(self) -> None:
        """Should return True when Rust is already loaded."""
        mock_rust_loader = MagicMock()
        mock_rust_loader.is_rust_available.return_value = True
        mock_rust_loader.load_rust_extensions.return_value = True

        with patch.dict("sys.modules", {"ClassicLib.core.rust_loader": mock_rust_loader}):
            result = ResourceLoader.load_rust_extension()
            assert result is True

    def test_loads_rust_extensions_when_not_loaded(self) -> None:
        """Should load Rust extensions when not already loaded."""
        with (
            patch("ClassicLib.core.rust_loader.is_rust_available", return_value=False),
            patch("ClassicLib.core.rust_loader.load_rust_extensions", return_value=True),
        ):
            result = ResourceLoader.load_rust_extension()
            assert result is True

    def test_returns_false_on_import_error(self) -> None:
        """Should return False when rust_loader can't be imported."""
        # Save original module
        import sys as sys_module

        original = sys_module.modules.get("ClassicLib.core.rust_loader")

        try:
            # Remove the module to force import error
            sys_module.modules["ClassicLib.core.rust_loader"] = None  # type: ignore
            # This should trigger an ImportError when trying to import
            result = ResourceLoader.load_rust_extension()
            assert result is False
        finally:
            # Restore original module
            if original is not None:
                sys_module.modules["ClassicLib.core.rust_loader"] = original
            else:
                sys_module.modules.pop("ClassicLib.core.rust_loader", None)

    def test_returns_false_when_loading_fails(self) -> None:
        """Should return False when Rust loading fails."""
        with (
            patch("ClassicLib.core.rust_loader.is_rust_available", return_value=False),
            patch("ClassicLib.core.rust_loader.load_rust_extensions", return_value=False),
        ):
            result = ResourceLoader.load_rust_extension()
            assert result is False


@pytest.mark.unit
class TestGetRustExtensionInfo:
    """Tests for get_rust_extension_info() method."""

    def test_returns_rust_info_when_available(self) -> None:
        """Should return Rust info from rust_loader when available."""
        expected_info = {
            "loaded": True,
            "path": "/path/to/rust.so",
            "search_paths": ["/path1", "/path2"],
            "in_pyinstaller": False,
        }

        with patch("ClassicLib.core.rust_loader.get_rust_info", return_value=expected_info):
            result = ResourceLoader.get_rust_extension_info()
            assert result == expected_info

    def test_returns_fallback_info_on_import_error(self) -> None:
        """Should return fallback info when rust_loader can't be imported."""
        with patch.dict("sys.modules", {"ClassicLib.core.rust_loader": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("no module"),
            ):
                result = ResourceLoader.get_rust_extension_info()
                assert result["loaded"] is False
                assert result["error"] == "rust_loader module not available"


# ============================================================================
# Convenience Function Tests
# ============================================================================


@pytest.mark.unit
class TestGetResourcePath:
    """Tests for get_resource_path() convenience function."""

    def test_returns_full_path_to_resource(self, tmp_path: Path) -> None:
        """Should return full path combining data directory and relative path."""
        with patch.object(ResourceLoader, "get_data_directory", return_value=tmp_path):
            result = get_resource_path("databases/CLASSIC Main.yaml")
            assert result == tmp_path / "databases/CLASSIC Main.yaml"

    def test_handles_nested_paths(self, tmp_path: Path) -> None:
        """Should handle nested relative paths correctly."""
        with patch.object(ResourceLoader, "get_data_directory", return_value=tmp_path):
            result = get_resource_path("images/icons/logo.png")
            assert result == tmp_path / "images/icons/logo.png"


@pytest.mark.unit
class TestIsFrozen:
    """Tests for is_frozen() function."""

    def test_returns_true_when_frozen_with_meipass(self) -> None:
        """Should return True when frozen and _MEIPASS exists."""
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/meipass", create=True),
        ):
            assert is_frozen() is True

    def test_returns_false_when_not_frozen(self) -> None:
        """Should return False when not frozen."""
        with patch.object(sys, "frozen", False, create=True):
            assert is_frozen() is False

    def test_returns_false_when_frozen_without_meipass(self) -> None:
        """Should return False when frozen but no _MEIPASS."""
        with patch.object(sys, "frozen", True, create=True):
            # Remove _MEIPASS if it exists
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
            assert is_frozen() is False
