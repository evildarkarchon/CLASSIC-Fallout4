"""Unit tests for ClassicLib.integration.factory.database module.

This module tests the factory functions for database pool creation.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetDatabasePool:
    """Tests for get_database_pool function."""

    def test_returns_pool_instance(self) -> None:
        """Test returns a database pool instance."""
        from ClassicLib.integration.factory.database import get_database_pool

        result = get_database_pool()

        assert result is not None

    def test_returns_python_pool_when_rust_disabled(self) -> None:
        """Test returns Python pool when Rust is disabled."""
        from ClassicLib.Database.async_pool import AsyncDatabasePool
        from ClassicLib.integration.factory.database import get_database_pool

        with patch("ClassicLib.integration.factory.database.is_rust_disabled", return_value=True):
            result = get_database_pool()

        assert isinstance(result, AsyncDatabasePool)

    def test_returns_python_pool_when_component_not_available(self) -> None:
        """Test returns Python pool when database_pool component not available."""
        from ClassicLib.Database.async_pool import AsyncDatabasePool
        from ClassicLib.integration.factory.database import get_database_pool

        with (
            patch("ClassicLib.integration.factory.database.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.database.get_components", return_value={"database_pool": False}),
        ):
            result = get_database_pool()

        assert isinstance(result, AsyncDatabasePool)

    def test_accepts_max_connections_parameter(self) -> None:
        """Test accepts max_connections parameter."""
        from ClassicLib.integration.factory.database import get_database_pool

        result = get_database_pool(max_connections=20)

        assert result is not None

    def test_accepts_cache_ttl_parameter(self) -> None:
        """Test accepts cache_ttl_seconds parameter."""
        from ClassicLib.integration.factory.database import get_database_pool

        result = get_database_pool(cache_ttl_seconds=600)

        assert result is not None

    def test_returns_python_pool_on_import_error(self) -> None:
        """Test returns Python pool when Rust import fails."""
        from ClassicLib.Database.async_pool import AsyncDatabasePool
        from ClassicLib.integration.factory.database import get_database_pool

        with (
            patch("ClassicLib.integration.factory.database.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.database.get_components", return_value={"database_pool": True}),
        ):
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "rust_pool" in str(args) or name == "ClassicLib.Database.rust_pool":
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_database_pool()

        assert isinstance(result, AsyncDatabasePool)
