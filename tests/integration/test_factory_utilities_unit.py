"""Unit tests for ClassicLib.integration.factory.utilities module.

This module tests the factory functions for Rust utility modules,
verifying fallback behavior and component detection.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetConstants:
    """Tests for get_constants function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_constants

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_constants()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when constants component not available."""
        from ClassicLib.integration.factory.utilities import get_constants

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"constants": False}),
        ):
            result = get_constants()

        assert result is None

    def test_returns_none_on_import_error(self) -> None:
        """Test returns None when import fails."""
        from ClassicLib.integration.factory.utilities import get_constants

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"constants": True}),
            patch.dict("sys.modules", {"classic_constants": None}),
        ):
            # Force ImportError by making import fail
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "classic_constants":
                    raise ImportError("No module named 'classic_constants'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_constants()

        assert result is None


class TestGetVersionUtils:
    """Tests for get_version_utils function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_version_utils

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_version_utils()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when version_utils component not available."""
        from ClassicLib.integration.factory.utilities import get_version_utils

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"version_utils": False}),
        ):
            result = get_version_utils()

        assert result is None


class TestGetResourceMgmt:
    """Tests for get_resource_mgmt function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_resource_mgmt

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_resource_mgmt()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when resource_mgmt component not available."""
        from ClassicLib.integration.factory.utilities import get_resource_mgmt

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"resource_mgmt": False}),
        ):
            result = get_resource_mgmt()

        assert result is None


class TestGetXseUtils:
    """Tests for get_xse_utils function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_xse_utils

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_xse_utils()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when xse_utils component not available."""
        from ClassicLib.integration.factory.utilities import get_xse_utils

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"xse_utils": False}),
        ):
            result = get_xse_utils()

        assert result is None


class TestGetWebUtils:
    """Tests for get_web_utils function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_web_utils

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_web_utils()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when web_utils component not available."""
        from ClassicLib.integration.factory.utilities import get_web_utils

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"web_utils": False}),
        ):
            result = get_web_utils()

        assert result is None


class TestGetPathOperations:
    """Tests for get_path_operations function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.utilities import get_path_operations

        with patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=True):
            result = get_path_operations()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when path_operations component not available."""
        from ClassicLib.integration.factory.utilities import get_path_operations

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"path_operations": False}),
        ):
            result = get_path_operations()

        assert result is None

    def test_returns_none_on_import_error(self) -> None:
        """Test returns None when import fails."""
        from ClassicLib.integration.factory.utilities import get_path_operations

        with (
            patch("ClassicLib.integration.factory.utilities.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.utilities.get_components", return_value={"path_operations": True}),
        ):
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "classic_path":
                    raise ImportError("No module named 'classic_path'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_path_operations()

        assert result is None
