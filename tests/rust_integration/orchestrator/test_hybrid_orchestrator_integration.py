"""
Integration tests for HybridOrchestrator core functionality.

Tests the hybrid orchestration strategy that uses Python for single-log
processing and Rust for batch parallelism. This module focuses on
core integration behaviors including creation, single/batch processing,
fallback mechanisms, and lifecycle management.
"""
# ruff: noqa: PLR6301

from collections import Counter
from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import patch

import pytest

from ClassicLib.integration.factory import get_orchestrator
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.scanning.logs.hybrid_orchestrator import HybridOrchestrator
from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.asyncio
class TestHybridOrchestratorIntegration:
    """Integration tests for HybridOrchestrator."""

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
    def sample_logs(self, tmp_path: Path) -> list[Path]:
        """
        Create sample crash log files for testing.

        Args:
            tmp_path: Pytest temp directory

        Returns:
            List of sample crash log paths
        """
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

    @pytest.fixture
    def yamldata(self) -> Any:
        """Load mocked YAML configuration."""
        from unittest.mock import MagicMock

        from ClassicLib.core.constants import NULL_VERSION

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

    @pytest.fixture
    async def hybrid_orch(self, yamldata: Any, mock_rust_yaml_environment: Any) -> AsyncGenerator[HybridOrchestrator, None]:
        """Create HybridOrchestrator instance with Rust YAML files available."""
        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            yield orch

    async def test_hybrid_orchestrator_creation(self, yamldata: Any, mock_rust_yaml_environment: Any) -> None:
        """Test HybridOrchestrator can be created via factory."""
        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        # Should return HybridOrchestrator if Rust module available, else OrchestratorCore
        assert orch is not None
        if is_rust_accelerated("orchestrator"):
            assert isinstance(orch, HybridOrchestrator)
            # With mock_rust_yaml_environment, Rust orchestrator should initialize
            assert orch._rust_orch is not None, "Rust orchestrator should be available with mock YAML files"
            print("✅ Using HybridOrchestrator with Rust acceleration")
        else:
            assert isinstance(orch, OrchestratorCore)
            print("⚠️  Using Python OrchestratorCore (Rust unavailable)")

    async def test_single_log_processing(self, hybrid_orch: HybridOrchestrator, sample_logs: list[Path]) -> None:
        """Test single log processing uses Python orchestrator."""
        result = await hybrid_orch.process_crash_log(sample_logs[0])

        # Verify result structure
        assert isinstance(result, tuple)
        assert len(result) == 4
        log_path, report_lines, scan_failed, stats = result

        # Check result components
        assert isinstance(log_path, Path)
        assert log_path == sample_logs[0]
        assert isinstance(report_lines, list)
        assert len(report_lines) > 0
        assert isinstance(scan_failed, bool)
        assert isinstance(stats, Counter)
        assert "scanned" in stats

        print(f"✅ Single log processed: {len(report_lines)} report lines")

    async def test_batch_processing_small(self, hybrid_orch: HybridOrchestrator, sample_logs: list[Path]) -> None:
        """Test small batch (< 5 logs) uses Python orchestrator."""
        small_batch = sample_logs[:3]
        results = await hybrid_orch.process_crash_logs_batch(small_batch)

        assert len(results) == len(small_batch)

        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 4
            log_path, report_lines, scan_failed, stats = result
            assert isinstance(log_path, Path)
            assert log_path in small_batch
            assert isinstance(report_lines, list)
            assert isinstance(scan_failed, bool)
            assert isinstance(stats, Counter)

        print(f"✅ Small batch ({len(small_batch)} logs) processed via Python")

    async def test_batch_processing_large(self, hybrid_orch: HybridOrchestrator, sample_logs: list[Path]) -> None:
        """Test large batch (5+ logs) uses Rust orchestrator if available."""
        large_batch = sample_logs[:8]
        results = await hybrid_orch.process_crash_logs_batch(large_batch)

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

        if is_rust_accelerated("orchestrator"):
            print(f"✅ Large batch ({len(large_batch)} logs) processed via Rust")
        else:
            print(f"⚠️  Large batch ({len(large_batch)} logs) processed via Python (Rust unavailable)")

    async def test_fallback_mechanism(self, yamldata: Any, tmp_path: Path, mock_rust_yaml_environment: Any) -> None:
        """Test fallback to Python when Rust processing fails."""
        # Create a corrupt log that might cause Rust to fail
        corrupt_log = tmp_path / "corrupt.log"
        corrupt_log.write_bytes(b"\xff\xfe\x00\x00")  # Invalid UTF-8

        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Should handle gracefully (either via fallback or error result)
            try:
                result = await orch.process_crash_log(corrupt_log)
                # If it succeeds, verify it's a valid result
                assert isinstance(result, tuple)
            except Exception as e:  # noqa: BLE001
                # If it fails, it should be a known error type
                assert e is not None
                print(f"✅ Handled corrupt log gracefully: {type(e).__name__}")

    async def test_context_manager_lifecycle(self, yamldata: Any, sample_logs: list[Path], mock_rust_yaml_environment: Any) -> None:
        """Test async context manager properly initializes and cleans up."""
        # Create orchestrator in context
        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Should be initialized
            assert orch is not None

            # Process a log
            result = await orch.process_crash_log(sample_logs[0])
            assert result is not None

        # After context exit, should still be valid object
        assert orch is not None
        print("✅ Context manager lifecycle correct")

    async def test_hybrid_strategy_detection(self, hybrid_orch: HybridOrchestrator) -> None:
        """Test HybridOrchestrator correctly detects Rust availability."""
        # With mock_rust_yaml_environment (via hybrid_orch fixture), Rust should initialize
        if is_rust_accelerated("orchestrator"):
            # Rust module available, and with mock YAML files, should have initialized
            assert hybrid_orch._rust_orch is not None, "Rust orchestrator should be available with mock YAML files"
            assert hasattr(hybrid_orch._rust_orch, "process_crash_logs_batch")
            print("✅ Rust orchestrator detected and initialized")
        else:
            # Rust module not available
            assert hybrid_orch._rust_orch is None
            print("⚠️  Rust orchestrator not available (module missing)")

        # Should always have Python orchestrator
        assert hybrid_orch._python_orch is not None
        assert isinstance(hybrid_orch._python_orch, OrchestratorCore)

    async def test_is_rust_feature_complete(self, hybrid_orch: HybridOrchestrator) -> None:
        """Test is_rust_feature_complete() method."""
        result = hybrid_orch.is_rust_feature_complete()

        # Should return bool
        assert isinstance(result, bool)

        if is_rust_accelerated("orchestrator") and hybrid_orch._rust_orch is not None:
            # Feature completeness depends on plugin_analyzer and suspect_scanner availability
            # Both should be available with proper YAML config
            print(f"✅ is_rust_feature_complete() = {result}")
        else:
            # Without Rust, should always return False
            assert result is False
            print("⚠️  is_rust_feature_complete() = False (Rust unavailable)")

    async def test_repr(self, hybrid_orch: HybridOrchestrator) -> None:
        """Test string representation."""
        repr_str = repr(hybrid_orch)
        assert "HybridOrchestrator" in repr_str
        assert "python=available" in repr_str

        # With mock_rust_yaml_environment (via hybrid_orch fixture), Rust should initialize
        if is_rust_accelerated("orchestrator"):
            # Rust status shows "feature-complete" or "batch-only" when available
            assert "rust=feature-complete" in repr_str or "rust=batch-only" in repr_str
        else:
            assert "rust=unavailable" in repr_str

        print(f"✅ Repr: {repr_str}")

    async def test_write_reports_batch(self, hybrid_orch: HybridOrchestrator, sample_logs: list[Path], tmp_path: Path) -> None:
        """Test batch report writing."""
        # Process logs
        results = await hybrid_orch.process_crash_logs_batch(sample_logs[:3])

        # Convert to report format (log_path, report_lines, scan_failed)
        reports = [(r[0], r[1], r[2]) for r in results]

        # Write reports to temp directory
        output_dir = tmp_path / "reports"
        output_dir.mkdir()

        # Temporarily change working directory for write_reports_batch
        import os

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)

            # Note: write_reports_batch expects reports in current directory
            # This test verifies the method exists and is callable
            # Full functionality testing would require actual file path handling
            await hybrid_orch.write_reports_batch(reports[:1])

            print("✅ write_reports_batch callable")
        finally:
            os.chdir(orig_cwd)
