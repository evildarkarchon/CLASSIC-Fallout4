"""
Factory pattern and Rust conversion tests for HybridOrchestrator.

Tests the factory pattern for orchestrator creation and Rust result
conversion to Python format. This module focuses on factory behavior,
FCX mode, remove list handling, and result format validation.
"""
# ruff: noqa: PLR6301

from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ClassicLib.integration.factory import get_orchestrator
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.HybridOrchestrator import HybridOrchestrator
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.asyncio
class TestFactoryPattern:
    """Test the factory pattern for orchestrator creation."""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock async settings calls."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async") as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async") as mock_classic,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = None
            yield

    @pytest.fixture
    def yamldata(self) -> Any:
        """Load mocked YAML configuration."""
        from unittest.mock import MagicMock

        from ClassicLib.Constants import NULL_VERSION

        mock_data = MagicMock()

        # Populate basic attributes
        mock_data.crashgen_name = "Buffout 4"
        mock_data.xse_acronym = "F4SE"
        mock_data.crashgen_latest_og = "1.0.0"
        mock_data.crashgen_latest_vr = "1.0.0"
        mock_data.game_version = NULL_VERSION
        mock_data.game_version_new = NULL_VERSION
        mock_data.game_version_vr = NULL_VERSION

        # Populate dictionaries
        mock_data.game_mods_conf = {}
        mock_data.game_mods_freq = {}
        mock_data.game_mods_solu = {}
        mock_data.game_mods_core = {}
        mock_data.game_mods_core_folon = {}
        mock_data.game_mods_opc2 = {}
        mock_data.suspects_error_list = {}
        mock_data.suspects_stack_list = {}

        # Populate lists/sets
        mock_data.classic_game_hints = []
        mock_data.classic_records_list = []
        mock_data.ignore_list = []
        mock_data.crashgen_ignore = set()
        mock_data.game_ignore_plugins = []
        mock_data.game_ignore_records = []

        # Populate strings
        mock_data.warn_noplugins = "Warning: No plugins"
        mock_data.warn_outdated = "Warning: Outdated"
        mock_data.autoscan_text = "Autoscan report"

        return mock_data

    async def test_factory_returns_hybrid_when_rust_available(self, yamldata: Any, mock_rust_yaml_environment: Any) -> None:
        """Test factory returns HybridOrchestrator when Rust is available."""
        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        if is_rust_accelerated("orchestrator"):
            assert isinstance(orch, HybridOrchestrator)
            # With mock YAML files, Rust orchestrator should initialize
            assert orch._rust_orch is not None, "Rust orchestrator should be available with mock YAML files"
            print("✅ Factory returns HybridOrchestrator (Rust available)")
        else:
            assert isinstance(orch, OrchestratorCore)
            print("⚠️  Factory returns OrchestratorCore (Rust unavailable)")

    async def test_factory_with_fcx_mode(self, yamldata: Any, mock_rust_yaml_environment: Any) -> None:
        """Test factory with FCX mode enabled."""
        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=True,  # Enable FCX mode
            show_formid_values=True,
            formid_db_exists=False,
        )

        assert orch is not None
        # FCX mode should be passed to Python orchestrator's FCX handler
        assert orch._python_orch.fcx_handler.fcx_mode is True

    async def test_factory_with_remove_list(self, yamldata: Any, mock_rust_yaml_environment: Any) -> None:
        """Test factory with custom remove list."""
        remove_list = ("Test1", "Test2")

        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
            remove_list=remove_list,
        )

        assert orch is not None
        # Remove list parameter should be stored (actual remove_list is initialized in __aenter__)
        assert orch._python_orch._remove_list_param == remove_list

    async def test_multiple_orchestrator_instances(self, yamldata: Any, mock_rust_yaml_environment: Any) -> None:
        """Test creating multiple orchestrator instances."""
        orch1 = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        orch2 = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=True,
            show_formid_values=False,
            formid_db_exists=True,
        )

        # Should be separate instances
        assert orch1 is not orch2
        assert orch1._python_orch is not orch2._python_orch

        # With mock YAML files, if Rust is available both should have Rust orchestrators
        if is_rust_accelerated("orchestrator"):
            assert orch1._rust_orch is not None, "Rust orchestrator should be available with mock YAML files"
            assert orch2._rust_orch is not None, "Rust orchestrator should be available with mock YAML files"
            assert type(orch1._rust_orch) is type(orch2._rust_orch)

        print("✅ Multiple orchestrator instances created successfully")


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.asyncio
class TestRustConversion:
    """Test Rust result conversion to Python format."""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock async settings calls."""
        with (
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async") as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async") as mock_classic,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = None
            yield

    @pytest.fixture
    def yamldata(self) -> Any:
        """Load mocked YAML configuration."""
        from unittest.mock import MagicMock

        from ClassicLib.Constants import NULL_VERSION

        mock_data = MagicMock()

        # Populate basic attributes
        mock_data.crashgen_name = "Buffout 4"
        mock_data.xse_acronym = "F4SE"
        mock_data.crashgen_latest_og = "1.0.0"
        mock_data.crashgen_latest_vr = "1.0.0"
        mock_data.game_version = NULL_VERSION
        mock_data.game_version_new = NULL_VERSION
        mock_data.game_version_vr = NULL_VERSION

        # Populate dictionaries
        mock_data.game_mods_conf = {}
        mock_data.game_mods_freq = {}
        mock_data.game_mods_solu = {}
        mock_data.game_mods_core = {}
        mock_data.game_mods_core_folon = {}
        mock_data.game_mods_opc2 = {}
        mock_data.suspects_error_list = {}
        mock_data.suspects_stack_list = {}

        # Populate lists/sets
        mock_data.classic_game_hints = []
        mock_data.classic_records_list = []
        mock_data.ignore_list = []
        mock_data.crashgen_ignore = set()
        mock_data.game_ignore_plugins = []
        mock_data.game_ignore_records = []

        # Populate strings
        mock_data.warn_noplugins = "Warning: No plugins"
        mock_data.warn_outdated = "Warning: Outdated"
        mock_data.autoscan_text = "Autoscan report"

        return mock_data

    async def test_result_conversion_format(self, yamldata: Any, tmp_path: Path, mock_rust_yaml_environment: Any) -> None:
        """Test Rust results are correctly converted to Python tuple format."""
        # Skip if Rust not available
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        # Create a sample log
        log = tmp_path / "test.log"
        log.write_text("Buffout 4\nCrash log\nPLUGINS:\n[00] Fallout4.esm", encoding="utf-8")

        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Process with large enough batch to trigger Rust
            results = await orch.process_crash_logs_batch([log] * 6)

            for result in results:
                # Verify Python tuple format
                assert isinstance(result, tuple)
                assert len(result) == 4

                log_path, report_lines, scan_failed, stats = result

                # Check types
                assert isinstance(log_path, Path)
                assert isinstance(report_lines, list)
                assert isinstance(scan_failed, bool)
                assert isinstance(stats, Counter)

                # Check stats structure
                assert "scanned" in stats
                assert "incomplete" in stats
                assert "failed" in stats

        print("✅ Rust result conversion format validated")
