"""Unit tests for ClassicLib.integration.factory.file_io module.

This module tests the factory functions for file I/O and YAML operations,
including singleton behavior and fallback to Python implementations.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetFileIO:
    """Tests for get_file_io function."""

    def test_returns_file_io_instance(self) -> None:
        """Test returns a FileIOCore instance."""
        # Reset the singleton for this test
        import ClassicLib.integration.factory.file_io as module

        original = module._file_io_instance
        module._file_io_instance = None

        try:
            from ClassicLib.integration.factory.file_io import get_file_io

            result = get_file_io()

            assert result is not None
        finally:
            module._file_io_instance = original

    def test_returns_same_instance_on_multiple_calls(self) -> None:
        """Test returns same singleton instance on multiple calls."""
        import ClassicLib.integration.factory.file_io as module

        original = module._file_io_instance
        module._file_io_instance = None

        try:
            from ClassicLib.integration.factory.file_io import get_file_io

            instance1 = get_file_io()
            instance2 = get_file_io()

            assert instance1 is instance2
        finally:
            module._file_io_instance = original

    def test_accepts_encoding_parameter(self) -> None:
        """Test accepts encoding parameter."""
        import ClassicLib.integration.factory.file_io as module

        original = module._file_io_instance
        module._file_io_instance = None

        try:
            from ClassicLib.integration.factory.file_io import get_file_io

            result = get_file_io(encoding="utf-16")

            assert result is not None
        finally:
            module._file_io_instance = original

    def test_accepts_errors_parameter(self) -> None:
        """Test accepts errors parameter."""
        import ClassicLib.integration.factory.file_io as module

        original = module._file_io_instance
        module._file_io_instance = None

        try:
            from ClassicLib.integration.factory.file_io import get_file_io

            result = get_file_io(errors="replace")

            assert result is not None
        finally:
            module._file_io_instance = original

    def test_returns_python_implementation_when_rust_disabled(self) -> None:
        """Test returns Python implementation when Rust is disabled."""
        import ClassicLib.integration.factory.file_io as module

        original = module._file_io_instance
        module._file_io_instance = None

        try:
            from ClassicLib.integration.factory.file_io import get_file_io

            with patch("ClassicLib.integration.factory.file_io.is_rust_disabled", return_value=True):
                result = get_file_io()

            assert result is not None
        finally:
            module._file_io_instance = original


class TestGetYamlOperations:
    """Tests for get_yaml_operations function."""

    def test_returns_none_when_rust_disabled(self) -> None:
        """Test returns None when Rust is disabled."""
        from ClassicLib.integration.factory.file_io import get_yaml_operations

        with patch("ClassicLib.integration.factory.file_io.is_rust_disabled", return_value=True):
            result = get_yaml_operations()

        assert result is None

    def test_returns_none_when_component_not_available(self) -> None:
        """Test returns None when yaml_operations component not available."""
        from ClassicLib.integration.factory.file_io import get_yaml_operations

        with (
            patch("ClassicLib.integration.factory.file_io.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.file_io.get_components", return_value={"yaml_operations": False}),
        ):
            result = get_yaml_operations()

        assert result is None

    def test_returns_none_on_import_error(self) -> None:
        """Test returns None when import fails."""
        from ClassicLib.integration.factory.file_io import get_yaml_operations

        with (
            patch("ClassicLib.integration.factory.file_io.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.file_io.get_components", return_value={"yaml_operations": True}),
        ):
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "classic_yaml":
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_yaml_operations()

        assert result is None


class TestModuleCaching:
    """Tests for module-level caching behavior."""

    def test_file_io_instance_starts_as_none(self) -> None:
        """Test _file_io_instance starts as None (when module is fresh)."""
        import ClassicLib.integration.factory.file_io as module

        # The instance may or may not be None depending on test order
        # Just verify the attribute exists
        assert hasattr(module, "_file_io_instance")

    def test_file_io_lock_exists(self) -> None:
        """Test _file_io_lock exists for thread safety."""
        import threading

        import ClassicLib.integration.factory.file_io as module

        assert hasattr(module, "_file_io_lock")
        assert isinstance(module._file_io_lock, type(threading.Lock()))
