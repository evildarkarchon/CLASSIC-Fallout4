"""Unit tests for ClassicLib.integration.factory.database module.

This module tests the factory functions for database pool creation.
"""

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetDatabasePool:
    """Tests for get_database_pool function."""

    def test_returns_pool_instance(self) -> None:
        """Test returns a database pool instance."""
        from ClassicLib.integration.factory import get_database_pool

        result = get_database_pool()

        assert result is not None

    def test_raises_import_error_on_rust_import_failure(self) -> None:
        """Test raises ImportError when required Rust pool import fails."""
        import builtins

        from ClassicLib.integration.factory import get_database_pool

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "rust_pool" in str(args) or name == "ClassicLib.io.database.rust_pool":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="No module"):
                get_database_pool()

    def test_accepts_max_connections_parameter(self) -> None:
        """Test accepts max_connections parameter."""
        from ClassicLib.integration.factory import get_database_pool

        result = get_database_pool(max_connections=20)

        assert result is not None

    def test_accepts_cache_ttl_parameter(self) -> None:
        """Test accepts cache_ttl_seconds parameter."""
        from ClassicLib.integration.factory import get_database_pool

        result = get_database_pool(cache_ttl_seconds=600)

        assert result is not None
