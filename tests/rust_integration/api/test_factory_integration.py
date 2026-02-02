"""Factory integration tests for Rust acceleration usage.

This module tests that production code properly uses factory functions
to enable Rust acceleration where available.

Tests verify:
- OrchestratorCore uses get_record_scanner() factory
- Factory functions return Rust implementations when available
- Fallback to Python implementations works correctly
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.integration.factory import (
    get_file_io,
    get_record_scanner,
    reset_cache,
)
from ClassicLib.integration.factory import is_rust_accelerated

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def reset_factory_cache() -> None:
    """Reset factory cache before each test."""
    reset_cache()


@pytest.mark.unit
class TestOrchestratorUsesRecordScannerFactory:
    """Verify OrchestratorCore uses factory pattern for RecordScanner."""

    def test_orchestrator_init_uses_get_record_scanner(self, mock_yamldata: MagicMock) -> None:
        """Verify OrchestratorCore calls get_record_scanner() in __init__."""
        with patch("ClassicLib.scanning.logs.orchestrator_core.get_record_scanner") as mock_factory:
            mock_scanner = MagicMock()
            mock_factory.return_value = mock_scanner

            # Import here to apply patch
            from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore

            # Create orchestrator
            orch = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Verify factory was called with yamldata
            mock_factory.assert_called_once_with(mock_yamldata)

            # Verify orchestrator uses the factory result
            assert orch.record_scanner is mock_scanner

    def test_orchestrator_record_scanner_not_none(self, mock_yamldata: MagicMock) -> None:
        """Verify OrchestratorCore's record_scanner is never None."""
        from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore

        orch = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # record_scanner should never be None - factory always returns a scanner
        assert orch.record_scanner is not None


@pytest.mark.unit
class TestRecordScannerFactory:
    """Test get_record_scanner() factory behavior."""

    def test_get_record_scanner_returns_scanner(self, mock_yamldata: MagicMock) -> None:
        """Verify get_record_scanner() returns a valid scanner instance."""
        scanner = get_record_scanner(mock_yamldata)

        # Scanner should never be None
        assert scanner is not None

        # Scanner should have the required interface
        assert hasattr(scanner, "scan_named_records")

    def test_get_record_scanner_rust_when_available(self, mock_yamldata: MagicMock) -> None:
        """Verify get_record_scanner() returns Rust scanner when available."""
        if not is_rust_accelerated("record_scanner"):
            pytest.skip("Rust record_scanner not available")

        scanner = get_record_scanner(mock_yamldata)

        # Should be the Rust wrapper class
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        assert isinstance(scanner, RustRecordScanner)

    def test_get_record_scanner_python_fallback(self, mock_yamldata: MagicMock) -> None:
        """Verify get_record_scanner() returns Python scanner when Rust disabled."""
        with patch.dict("os.environ", {"CLASSIC_DISABLE_RUST": "1"}):
            # Reset cache to pick up env change
            reset_cache()

            scanner = get_record_scanner(mock_yamldata)

            # Should be Python implementation
            from ClassicLib.integration.python.record_py import RecordScanner as PythonRecordScanner

            assert isinstance(scanner, PythonRecordScanner)


@pytest.mark.unit
class TestFileIOFactory:
    """Test get_file_io() factory behavior."""

    def test_get_file_io_returns_instance(self) -> None:
        """Verify get_file_io() returns a valid FileIOCore instance."""
        io_core = get_file_io()

        # Should never be None
        assert io_core is not None

        # Should have the required interface
        assert hasattr(io_core, "read_file")
        assert hasattr(io_core, "write_file")
        assert hasattr(io_core, "file_exists")

    def test_get_file_io_singleton_behavior(self) -> None:
        """Verify get_file_io() returns the same instance (singleton)."""
        io1 = get_file_io()
        io2 = get_file_io()

        # Should be the exact same instance
        assert io1 is io2

    def test_get_file_io_rust_when_available(self) -> None:
        """Verify get_file_io() returns Rust FileIOCore when available."""
        if not is_rust_accelerated("file_io_core"):
            pytest.skip("Rust file_io_core not available")

        io_core = get_file_io()

        # Should be the Rust implementation
        from ClassicLib.integration.rust.file_io_rust import FileIOCore as RustFileIOCore

        assert isinstance(io_core, RustFileIOCore)


@pytest.mark.integration
class TestFactoryIntegrationWithRust:
    """Integration tests for factory functions with Rust components."""

    @pytest.mark.skipif(
        not is_rust_accelerated("record_scanner"),
        reason="Rust record_scanner not available",
    )
    def test_rust_record_scanner_integration(self, mock_yamldata: MagicMock) -> None:
        """Test Rust RecordScanner works correctly through factory."""
        scanner = get_record_scanner(mock_yamldata)

        # Test basic functionality
        sample_callstack = [
            "[0] 0x7FF6DEADBEEF -> TESForm at 0x12345678",
            "[1] 0x7FF6CAFEBABE -> BGSKeyword at 0xABCDEF01",
        ]

        # scan_named_records should return a tuple (fragment, found_records)
        result = scanner.scan_named_records(sample_callstack)

        # Verify result structure
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.skipif(
        not is_rust_accelerated("file_io_core"),
        reason="Rust file_io_core not available",
    )
    @pytest.mark.asyncio
    async def test_rust_file_io_integration(self, tmp_path) -> None:
        """Test Rust FileIOCore works correctly through factory."""
        io_core = get_file_io()

        # Test file operations
        test_file = tmp_path / "test.txt"
        test_content = "Hello, Rust acceleration!"

        # Write and read back
        await io_core.write_file(test_file, test_content)
        content = await io_core.read_file(test_file)

        assert content == test_content
