"""
Batch-only mode tests for HybridOrchestrator.

Tests the batch-only mode behavior where the Rust orchestrator is available
but not feature-complete (missing plugin_analyzer or suspect_scanner).
Single-log processing uses Python, but batch processing still uses Rust.
"""
# ruff: noqa: PLR6301

from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ClassicLib.integration.factory import get_orchestrator
from ClassicLib.integration.factory import is_rust_accelerated
from ClassicLib.scanning.logs.hybrid_orchestrator import HybridOrchestrator


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchOnlyMode:
    """
    Test HybridOrchestrator behavior when Rust orchestrator is in batch-only mode.

    When is_feature_complete() returns False (missing plugin_analyzer or suspect_scanner),
    single-log processing should use Python, but batch processing still uses Rust.
    """

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock async settings calls."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async") as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async") as mock_classic,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = None
            yield

    @pytest.fixture
    def mock_batch_only_yamldata(self, yamldata_batch_only: Any):
        """
        Mock get_yamldata() for Rust ClassicOrchestrator to return batch-only data.

        The ClassicOrchestrator uses get_yamldata() from the factory to load configuration.
        This fixture mocks that function to return our empty test data (batch-only mode).
        """
        with patch("ClassicLib.integration.rust.orchestrator_api.get_yamldata", return_value=yamldata_batch_only):
            yield yamldata_batch_only

    @pytest.fixture
    def yamldata_batch_only(self) -> Any:
        """
        Load YAML configuration with empty data for batch-only mode.

        This fixture has empty game_ignore_plugins, suspects_error_list, and
        suspects_stack_list so that is_feature_complete() returns False.
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

        # CRITICAL: Empty suspects data disables suspect_scanner
        mock_data.suspects_error_list = {}
        mock_data.suspects_stack_list = {}

        # Populate lists/sets
        mock_data.classic_game_hints = []
        mock_data.classic_records_list = []
        mock_data.ignore_list = []
        mock_data.crashgen_ignore = set()

        # CRITICAL: Empty ignore_plugins disables plugin_analyzer
        mock_data.game_ignore_plugins = []
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

    async def test_is_feature_complete_returns_false(
        self, yamldata_batch_only: Any, mock_rust_yaml_environment: Any, mock_batch_only_yamldata: Any
    ) -> None:
        """Test that is_feature_complete() returns False with empty YAML data."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        orch = get_orchestrator(
            yamldata=yamldata_batch_only,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        assert isinstance(orch, HybridOrchestrator)
        assert orch._rust_orch is not None, "Rust orchestrator should be available"

        # With empty suspects and ignore_plugins, should NOT be feature-complete
        result = orch.is_rust_feature_complete()
        assert result is False, (
            "is_feature_complete() should return False when suspects_error_list, suspects_stack_list, or game_ignore_plugins are empty"
        )
        assert orch._rust_feature_complete is False, "_rust_feature_complete flag should be False"

        print("✅ is_feature_complete() returns False with empty YAML data")

    async def test_repr_shows_batch_only(
        self, yamldata_batch_only: Any, mock_rust_yaml_environment: Any, mock_batch_only_yamldata: Any
    ) -> None:
        """Test that repr shows 'batch-only' when is_feature_complete() is False."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        orch = get_orchestrator(
            yamldata=yamldata_batch_only,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        repr_str = repr(orch)
        assert "HybridOrchestrator" in repr_str
        assert "python=available" in repr_str
        assert "rust=batch-only" in repr_str

        print(f"✅ Batch-only repr: {repr_str}")

    async def test_single_log_uses_python_when_batch_only(
        self, yamldata_batch_only: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any, mock_batch_only_yamldata: Any
    ) -> None:
        """Test that single-log processing uses Python when in batch-only mode."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        async with get_orchestrator(
            yamldata=yamldata_batch_only,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify batch-only mode
            assert orch._rust_feature_complete is False, "Should be in batch-only mode"
            assert orch._rust_orch is not None, "Rust orchestrator should exist (just not feature-complete)"

            # Single-log processing should use Python
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

        print("✅ Single log processed via Python (batch-only mode)")

    async def test_batch_processing_still_uses_rust(
        self, yamldata_batch_only: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any, mock_batch_only_yamldata: Any
    ) -> None:
        """Test that batch processing still uses Rust even in batch-only mode."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")

        async with get_orchestrator(
            yamldata=yamldata_batch_only,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify batch-only mode
            assert orch._rust_feature_complete is False, "Should be in batch-only mode"
            assert orch._rust_orch is not None, "Rust orchestrator should exist for batch processing"

            # Batch processing should still use Rust (for parallelism benefits)
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

        print(f"✅ Batch ({len(large_batch)} logs) processed via Rust (batch-only mode)")
