"""
Feature-complete mode tests for HybridOrchestrator.

Tests the feature-complete mode behavior where both plugin_analyzer and
suspect_scanner are available in the Rust orchestrator, allowing single-log
processing to use Rust instead of Python.
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


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.asyncio
class TestFeatureCompleteMode:
    """
    Test HybridOrchestrator behavior when Rust orchestrator is feature-complete.

    When is_feature_complete() returns True (plugin_analyzer and suspect_scanner
    are both available), single-log processing should use Rust instead of Python.
    """

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
    def mock_feature_complete_yamldata(self, yamldata_feature_complete: Any):
        """
        Mock get_yamldata() for Rust ClassicOrchestrator to return feature-complete data.

        The ClassicOrchestrator uses get_yamldata() from the factory to load configuration.
        This fixture mocks that function to return our populated test data.
        """
        with patch("ClassicLib.rust.orchestrator_api.get_yamldata", return_value=yamldata_feature_complete):
            yield yamldata_feature_complete

    @pytest.fixture
    def yamldata_feature_complete(self) -> Any:
        """
        Load YAML configuration with populated data for feature-complete mode.

        This fixture populates game_ignore_plugins, suspects_error_list, and
        suspects_stack_list so that the Rust orchestrator's is_feature_complete()
        method returns True.
        """
        from unittest.mock import MagicMock

        mock_data = MagicMock()

        # Populate basic attributes - use strings for version fields
        mock_data.crashgen_name = "Buffout 4"
        mock_data.xse_acronym = "F4SE"
        mock_data.crashgen_latest_og = "1.0.0"
        mock_data.crashgen_latest_vr = "1.0.0"
        mock_data.game_version = "0.0.0.0"  # String, not Version object
        mock_data.game_version_new = "0.0.0.0"
        mock_data.game_version_vr = "0.0.0.0"

        # Populate dictionaries
        mock_data.game_mods_conf = {}
        mock_data.game_mods_freq = {}
        mock_data.game_mods_solu = {}
        mock_data.game_mods_core = {}
        mock_data.game_mods_core_folon = {}
        mock_data.game_mods_opc2 = {}

        # CRITICAL: Non-empty suspects data enables suspect_scanner
        # Note: Rust bindings expect HashMap<String, String> (not List values)
        # The string values are split on newlines internally
        mock_data.suspects_error_list = {
            "test_error_1": "Error pattern 1\nError description 1",
            "test_error_2": "Error pattern 2\nError description 2",
        }
        mock_data.suspects_stack_list = {
            "test_stack_1": "Stack pattern 1\nStack description 1",
            "test_stack_2": "Stack pattern 2\nStack description 2",
        }

        # Populate lists/sets
        mock_data.classic_game_hints = []
        mock_data.classic_records_list = []
        mock_data.ignore_list = []
        mock_data.crashgen_ignore = set()

        # CRITICAL: Non-empty ignore_plugins enables plugin_analyzer
        mock_data.game_ignore_plugins = ["Fallout4.esm", "DLCCoast.esm", "DLCRobot.esm"]
        mock_data.game_ignore_records = []

        # Populate strings
        mock_data.warn_noplugins = "Warning: No plugins"
        mock_data.warn_outdated = "Warning: Outdated"
        mock_data.autoscan_text = "Autoscan report"

        return mock_data

    @pytest.fixture
    def sample_logs(self, tmp_path: Path) -> list[Path]:
        """Create sample crash log files for testing."""
        logs = []
        for i in range(10):
            log_path = tmp_path / f"crash-{i:02d}.log"
            content = f"""Buffout 4 v1.26.2
Crash Log On: 2024-01-{i + 1:02d}

SYSTEM SPECS:
    OS: Windows 10

PROBABLE CALL STACK:
    [0] 0x7FF6AB{i:06X} (Fallout4.exe)
    [1] FormID 0x00{i:06X} (Plugin{i}.esp)

F4SE PLUGINS:
    BuffoutNG v1.0

PLUGINS:
    [00] Fallout4.esm
    [01] Plugin{i}.esp
"""
            log_path.write_text(content, encoding="utf-8")
            logs.append(log_path)
        return logs

    async def test_is_feature_complete_returns_true(
        self, yamldata_feature_complete: Any, mock_rust_yaml_environment: Any, mock_feature_complete_yamldata: Any
    ) -> None:
        """Test that is_feature_complete() returns True with populated YAML data."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        orch = get_orchestrator(
            yamldata=yamldata_feature_complete,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        assert isinstance(orch, HybridOrchestrator)
        assert orch._rust_orch is not None, "Rust orchestrator should be available"

        # With populated suspects and ignore_plugins, should be feature-complete
        result = orch.is_rust_feature_complete()
        assert result is True, (
            "is_feature_complete() should return True when suspects_error_list, suspects_stack_list, and game_ignore_plugins are populated"
        )
        assert orch._rust_feature_complete is True, "_rust_feature_complete flag should be True"

        print("✅ is_feature_complete() returns True with populated YAML data")

    async def test_repr_shows_feature_complete(
        self, yamldata_feature_complete: Any, mock_rust_yaml_environment: Any, mock_feature_complete_yamldata: Any
    ) -> None:
        """Test that repr shows 'feature-complete' when is_feature_complete() is True."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        orch = get_orchestrator(
            yamldata=yamldata_feature_complete,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        repr_str = repr(orch)
        assert "HybridOrchestrator" in repr_str
        assert "python=available" in repr_str
        assert "rust=feature-complete" in repr_str

        print(f"✅ Feature-complete repr: {repr_str}")

    async def test_single_log_uses_rust_when_feature_complete(
        self, yamldata_feature_complete: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any, mock_feature_complete_yamldata: Any
    ) -> None:
        """Test that single-log processing uses Rust when feature-complete."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        async with get_orchestrator(
            yamldata=yamldata_feature_complete,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify feature-complete mode
            assert orch._rust_feature_complete is True, "Should be in feature-complete mode"

            # Single-log processing should now use Rust
            result = await orch.process_crash_log(sample_logs[0])

            # Verify result structure
            assert isinstance(result, tuple)
            assert len(result) == 4
            log_path, report_lines, scan_failed, stats = result

            assert isinstance(log_path, Path)
            assert log_path == sample_logs[0]
            assert isinstance(report_lines, list)
            assert len(report_lines) > 0
            assert isinstance(scan_failed, bool)
            assert isinstance(stats, Counter)
            assert "scanned" in stats

        print("✅ Single log processed via Rust (feature-complete mode)")

    async def test_batch_processing_feature_complete(
        self, yamldata_feature_complete: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any, mock_feature_complete_yamldata: Any
    ) -> None:
        """Test batch processing in feature-complete mode."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        async with get_orchestrator(
            yamldata=yamldata_feature_complete,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify feature-complete mode
            assert orch._rust_feature_complete is True, "Should be in feature-complete mode"

            # Batch processing should use Rust
            large_batch = sample_logs[:8]
            results = await orch.process_crash_logs_batch(large_batch)

            assert len(results) == len(large_batch)

            for result in results:
                assert isinstance(result, tuple)
                assert len(result) == 4
                log_path, report_lines, scan_failed, stats = result
                assert isinstance(log_path, Path)
                assert log_path in large_batch
                assert isinstance(report_lines, list)
                assert isinstance(scan_failed, bool)
                assert isinstance(stats, Counter)

        print(f"✅ Batch ({len(large_batch)} logs) processed via Rust (feature-complete mode)")

    async def test_context_manager_preserves_feature_complete(
        self, yamldata_feature_complete: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any, mock_feature_complete_yamldata: Any
    ) -> None:
        """Test that context manager preserves feature-complete state."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        async with get_orchestrator(
            yamldata=yamldata_feature_complete,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Before any processing
            assert orch._rust_feature_complete is True

            # Process a log
            await orch.process_crash_log(sample_logs[0])

            # After processing, should still be feature-complete
            assert orch._rust_feature_complete is True
            assert orch.is_rust_feature_complete() is True

        print("✅ Context manager preserves feature-complete state")
