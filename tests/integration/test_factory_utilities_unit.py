"""Unit tests for utility factory functions in ClassicLib.integration.factory.

This module tests the factory functions for Rust utility modules,
verifying fallback behavior when Rust is unavailable.
"""

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetConstants:
    """Tests for get_constants function."""

    def test_raises_on_import_error(self) -> None:
        """Test raises ImportError when required binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_constants

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_constants":
                raise ImportError("No module named 'classic_constants'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_constants"):
                get_constants()


class TestGetVersionUtils:
    """Tests for get_version_utils function."""

    def test_raises_on_import_error(self) -> None:
        """Test raises ImportError when required binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_version_utils

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_version":
                raise ImportError("No module named 'classic_version'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_version"):
                get_version_utils()


class TestGetResourceMgmt:
    """Tests for get_resource_mgmt function."""

    def test_raises_on_import_error(self) -> None:
        """Test raises ImportError when required binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_resource_mgmt

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_resource":
                raise ImportError("No module named 'classic_resource'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_resource"):
                get_resource_mgmt()


class TestGetXseUtils:
    """Tests for get_xse_utils function."""

    def test_raises_on_import_error(self) -> None:
        """Test raises ImportError when required binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_xse_utils

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_xse":
                raise ImportError("No module named 'classic_xse'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_xse"):
                get_xse_utils()


class TestGetWebUtils:
    """Tests for get_web_utils function."""

    def test_raises_on_import_error(self) -> None:
        """Test raises ImportError when required binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_web_utils

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_web":
                raise ImportError("No module named 'classic_web'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_web"):
                get_web_utils()


class TestGetPathOperations:
    """Tests for get_path_operations function.

    Note: classic_path is a required Rust module. Unlike other utility modules,
    ImportError propagates rather than returning None.
    """

    def test_raises_import_error_when_unavailable(self) -> None:
        """Test raises ImportError when Rust module is unavailable."""
        import builtins

        from ClassicLib.integration.factory import get_path_operations

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_path":
                raise ImportError("No module named 'classic_path'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_path"):
                get_path_operations()
