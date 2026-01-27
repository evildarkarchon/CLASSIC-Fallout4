"""Unit tests for ClassicLib.rust_loader module.

This module tests the RustExtensionLoader class and module-level
convenience functions for loading Rust extensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_rust_components_all_available() -> dict[str, bool]:
    """Create mock with all Rust components available.

    Returns:
        Dictionary with all components set to True.
    """
    return {
        "parser": True,
        "formid_analyzer": True,
        "plugin_analyzer": True,
        "record_scanner": True,
        "report_generation": True,
        "database_pool": True,
        "file_io_core": True,
        "mod_detector": True,
    }


@pytest.fixture
def mock_rust_components_none_available() -> dict[str, bool]:
    """Create mock with no Rust components available.

    Returns:
        Dictionary with all components set to False.
    """
    return {
        "parser": False,
        "formid_analyzer": False,
        "plugin_analyzer": False,
        "record_scanner": False,
        "report_generation": False,
        "database_pool": False,
        "file_io_core": False,
        "mod_detector": False,
    }


@pytest.fixture
def mock_available_components_info() -> dict[str, Any]:
    """Create mock available components info.

    Returns:
        Dictionary with component info structure.
    """
    return {
        "components": {
            "parser": True,
            "formid_analyzer": True,
        },
        "versions": {
            "classic_scanlog": "1.0.0",
        },
        "disabled": False,
    }


@pytest.fixture
def fresh_rust_loader() -> Generator[None, None, None]:
    """Provide a fresh RustExtensionLoader instance.

    Yields:
        None - resets the global loader after test.
    """
    from ClassicLib.core import rust_loader

    # Store original
    original_loader = rust_loader._rust_loader

    # Create fresh loader
    rust_loader._rust_loader = rust_loader.RustExtensionLoader()

    yield

    # Restore
    rust_loader._rust_loader = original_loader


# ============================================================================
# RustExtensionLoader Class Tests
# ============================================================================


class TestRustExtensionLoaderInit:
    """Tests for RustExtensionLoader initialization."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test RustExtensionLoader initializes with default values."""
        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()

        assert loader.loaded_module is None
        assert loader.load_path is None
        assert loader.search_paths == []


class TestRustExtensionLoaderIsLoaded:
    """Tests for RustExtensionLoader.is_loaded method."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_is_loaded_returns_true_when_components_available(
        self,
        mock_detect: MagicMock,
        mock_rust_components_all_available: dict[str, bool],
    ) -> None:
        """Test is_loaded returns True when Rust components are available."""
        mock_detect.return_value = mock_rust_components_all_available

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()

        assert loader.is_loaded() is True

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_is_loaded_returns_false_when_no_components(
        self,
        mock_detect: MagicMock,
        mock_rust_components_none_available: dict[str, bool],
    ) -> None:
        """Test is_loaded returns False when no components available."""
        mock_detect.return_value = mock_rust_components_none_available

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()

        assert loader.is_loaded() is False

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_is_loaded_returns_true_with_partial_components(
        self,
        mock_detect: MagicMock,
    ) -> None:
        """Test is_loaded returns True with at least one component."""
        mock_detect.return_value = {
            "parser": True,
            "formid_analyzer": False,
            "plugin_analyzer": False,
        }

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()

        assert loader.is_loaded() is True


class TestRustExtensionLoaderGetLoadInfo:
    """Tests for RustExtensionLoader.get_load_info method."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_load_info_returns_complete_info(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        mock_rust_components_all_available: dict[str, bool],
        mock_available_components_info: dict[str, Any],
    ) -> None:
        """Test get_load_info returns complete information structure."""
        mock_detect.return_value = mock_rust_components_all_available
        mock_get_available.return_value = mock_available_components_info

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        info = loader.get_load_info()

        # Check required keys
        assert "loaded" in info
        assert "path" in info
        assert "search_paths" in info
        assert "in_pyinstaller" in info
        assert "components" in info
        assert "versions" in info

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_load_info_loaded_status_matches_is_loaded(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        mock_rust_components_all_available: dict[str, bool],
        mock_available_components_info: dict[str, Any],
    ) -> None:
        """Test get_load_info 'loaded' field matches is_loaded()."""
        mock_detect.return_value = mock_rust_components_all_available
        mock_get_available.return_value = mock_available_components_info

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        info = loader.get_load_info()

        assert info["loaded"] == loader.is_loaded()

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_load_info_path_is_modular_packages(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        mock_rust_components_none_available: dict[str, bool],
        mock_available_components_info: dict[str, Any],
    ) -> None:
        """Test get_load_info returns 'modular_packages' as path."""
        mock_detect.return_value = mock_rust_components_none_available
        mock_get_available.return_value = mock_available_components_info

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        info = loader.get_load_info()

        assert info["path"] == "modular_packages"

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_load_info_includes_component_versions(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        mock_rust_components_all_available: dict[str, bool],
    ) -> None:
        """Test get_load_info includes version information."""
        mock_detect.return_value = mock_rust_components_all_available
        mock_get_available.return_value = {
            "components": {"parser": True},
            "versions": {"classic_scanlog": "2.0.0", "classic_yaml": "1.5.0"},
            "disabled": False,
        }

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        info = loader.get_load_info()

        assert info["versions"]["classic_scanlog"] == "2.0.0"
        assert info["versions"]["classic_yaml"] == "1.5.0"


class TestRustExtensionLoaderLoadExtension:
    """Tests for RustExtensionLoader.load_extension method."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_load_extension_returns_true_when_loaded(
        self,
        mock_detect: MagicMock,
        mock_rust_components_all_available: dict[str, bool],
    ) -> None:
        """Test load_extension returns True when components available."""
        mock_detect.return_value = mock_rust_components_all_available

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        result = loader.load_extension()

        assert result is True

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_load_extension_returns_none_when_not_loaded(
        self,
        mock_detect: MagicMock,
        mock_rust_components_none_available: dict[str, bool],
    ) -> None:
        """Test load_extension returns None when no components available."""
        mock_detect.return_value = mock_rust_components_none_available

        from ClassicLib.core.rust_loader import RustExtensionLoader

        loader = RustExtensionLoader()
        result = loader.load_extension()

        assert result is None


# ============================================================================
# Module-Level Function Tests
# ============================================================================


class TestLoadRustExtensions:
    """Tests for load_rust_extensions function."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_load_rust_extensions_returns_true_when_available(
        self,
        mock_detect: MagicMock,
        fresh_rust_loader: None,
        mock_rust_components_all_available: dict[str, bool],
    ) -> None:
        """Test load_rust_extensions returns True when components available."""
        mock_detect.return_value = mock_rust_components_all_available

        from ClassicLib.core.rust_loader import load_rust_extensions

        result = load_rust_extensions()

        assert result is True

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_load_rust_extensions_returns_false_when_unavailable(
        self,
        mock_detect: MagicMock,
        fresh_rust_loader: None,
        mock_rust_components_none_available: dict[str, bool],
    ) -> None:
        """Test load_rust_extensions returns False when no components."""
        mock_detect.return_value = mock_rust_components_none_available

        from ClassicLib.core.rust_loader import load_rust_extensions

        result = load_rust_extensions()

        assert result is False


class TestIsRustAvailable:
    """Tests for is_rust_available function."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_is_rust_available_returns_true(
        self,
        mock_detect: MagicMock,
        fresh_rust_loader: None,
        mock_rust_components_all_available: dict[str, bool],
    ) -> None:
        """Test is_rust_available returns True when Rust available."""
        mock_detect.return_value = mock_rust_components_all_available

        from ClassicLib.core.rust_loader import is_rust_available

        assert is_rust_available() is True

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_is_rust_available_returns_false(
        self,
        mock_detect: MagicMock,
        fresh_rust_loader: None,
        mock_rust_components_none_available: dict[str, bool],
    ) -> None:
        """Test is_rust_available returns False when Rust unavailable."""
        mock_detect.return_value = mock_rust_components_none_available

        from ClassicLib.core.rust_loader import is_rust_available

        assert is_rust_available() is False


class TestGetRustInfo:
    """Tests for get_rust_info function."""

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_rust_info_returns_load_info(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        fresh_rust_loader: None,
        mock_rust_components_all_available: dict[str, bool],
        mock_available_components_info: dict[str, Any],
    ) -> None:
        """Test get_rust_info returns load information."""
        mock_detect.return_value = mock_rust_components_all_available
        mock_get_available.return_value = mock_available_components_info

        from ClassicLib.core.rust_loader import get_rust_info

        info = get_rust_info()

        assert isinstance(info, dict)
        assert "loaded" in info
        assert "components" in info
        assert "versions" in info

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.get_available_components")
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    def test_get_rust_info_components_match_available(
        self,
        mock_detect: MagicMock,
        mock_get_available: MagicMock,
        fresh_rust_loader: None,
    ) -> None:
        """Test get_rust_info includes correct components."""
        mock_detect.return_value = {"parser": True, "database": False}
        mock_get_available.return_value = {
            "components": {"parser": True, "database": False},
            "versions": {},
            "disabled": False,
        }

        from ClassicLib.core.rust_loader import get_rust_info

        info = get_rust_info()

        assert info["components"]["parser"] is True
        assert info["components"]["database"] is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestRustLoaderIntegration:
    """Integration tests for rust_loader module."""

    @pytest.mark.unit
    def test_module_exports_expected_functions(self) -> None:
        """Test module exports expected public API."""
        from ClassicLib.core import rust_loader

        # Check class is exported
        assert hasattr(rust_loader, "RustExtensionLoader")

        # Check functions are exported
        assert hasattr(rust_loader, "load_rust_extensions")
        assert hasattr(rust_loader, "is_rust_available")
        assert hasattr(rust_loader, "get_rust_info")

    @pytest.mark.unit
    def test_global_loader_is_initialized(self) -> None:
        """Test global loader instance exists."""
        from ClassicLib.core import rust_loader

        assert hasattr(rust_loader, "_rust_loader")
        assert isinstance(rust_loader._rust_loader, rust_loader.RustExtensionLoader)

    @pytest.mark.unit
    @patch("ClassicLib.core.rust_loader.detect_rust_components")
    @patch("ClassicLib.core.rust_loader.get_available_components")
    def test_consistent_state_across_calls(
        self,
        mock_get_available: MagicMock,
        mock_detect: MagicMock,
        fresh_rust_loader: None,
    ) -> None:
        """Test loader maintains consistent state across calls."""
        # First call returns available
        mock_detect.return_value = {"parser": True}
        mock_get_available.return_value = {
            "components": {"parser": True},
            "versions": {},
            "disabled": False,
        }

        from ClassicLib.core.rust_loader import get_rust_info, is_rust_available

        # Multiple calls should be consistent
        assert is_rust_available() is True
        info = get_rust_info()
        assert info["loaded"] is True

        # Change mock to simulate unavailable
        mock_detect.return_value = {"parser": False}
        mock_get_available.return_value = {
            "components": {"parser": False},
            "versions": {},
            "disabled": False,
        }

        # Should reflect new state
        assert is_rust_available() is False
