"""
Mode-specific tests for HybridOrchestrator.

Tests the Python fallback behavior, feature-complete mode, and batch-only
mode of HybridOrchestrator. This module focuses on testing orchestrator
behavior under different Rust availability and configuration scenarios.
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
class TestPythonFallback:
    """
    Test Python fallback behavior when Rust orchestrator initialization fails.

    These tests specifically verify that HybridOrchestrator gracefully degrades
    to Python-only mode when Rust initialization fails (e.g., missing YAML files).
    This is the expected behavior in CI environments without full YAML fixtures.
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
    def force_rust_init_failure(self, tmp_path: Path):
        """
        Force Rust orchestrator initialization to fail by pointing to non-existent YAML files.

        This fixture patches ResourceLoader and GlobalRegistry to point to a temp directory
        that does NOT have the required YAML files, simulating the CI environment.
        """
        # Create an empty directory (no YAML files)
        empty_data_dir = tmp_path / "empty_data"
        empty_data_dir.mkdir(parents=True)

        with (
            patch("ClassicLib.ResourceLoader.ResourceLoader.get_data_directory", return_value=empty_data_dir),
            patch("ClassicLib.GlobalRegistry.get_game", return_value="Fallout4"),
            patch("ClassicLib.GlobalRegistry.get_vr", return_value=""),
        ):
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

    @pytest.fixture
    def sample_logs(self, tmp_path: Path) -> list[Path]:
        """Create sample crash log files for testing."""
        logs = []
        for i in range(5):
            log_path = tmp_path / f"crash-{i:02d}.log"
            content = f"""Buffout 4 v1.26.2
Crash Log On: 2024-01-{i + 1:02d}

SYSTEM SPECS:
    OS: Windows 10

PROBABLE CALL STACK:
    [0] 0x7FF6AB{i:06X} (Fallout4.exe)

F4SE PLUGINS:
    BuffoutNG v1.0

PLUGINS:
    [00] Fallout4.esm
    [01] Plugin{i}.esp
"""
            log_path.write_text(content, encoding="utf-8")
            logs.append(log_path)
        return logs

    async def test_fallback_when_rust_init_fails(self, yamldata: Any, force_rust_init_failure: Any) -> None:
        """Test that HybridOrchestrator falls back to Python when Rust init fails.

        Uses force_rust_init_failure fixture to simulate missing YAML files,
        causing Rust orchestrator initialization to fail. The HybridOrchestrator
        should gracefully fall back to Python-only mode.
        """
        # Skip if Rust module not available (nothing to fall back from)
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust module not available - fallback test not applicable")

        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        # Should still return HybridOrchestrator (Rust module is importable)
        assert isinstance(orch, HybridOrchestrator)

        # But _rust_orch should be None (initialization failed due to missing YAML files)
        assert orch._rust_orch is None, "Rust orchestrator should be None when YAML files are missing"

        # Python orchestrator should always be available
        assert orch._python_orch is not None
        assert isinstance(orch._python_orch, OrchestratorCore)

        print("✅ HybridOrchestrator correctly falls back to Python when Rust init fails")

    async def test_fallback_repr_shows_unavailable(self, yamldata: Any, force_rust_init_failure: Any) -> None:
        """Test that repr shows Rust as unavailable when init fails."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust module not available - fallback test not applicable")

        orch = get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        repr_str = repr(orch)
        assert "HybridOrchestrator" in repr_str
        assert "python=available" in repr_str
        assert "rust=unavailable" in repr_str

        print(f"✅ Fallback repr: {repr_str}")

    async def test_fallback_single_log_processing(self, yamldata: Any, sample_logs: list[Path], force_rust_init_failure: Any) -> None:
        """Test single log processing works with Python fallback."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust module not available - fallback test not applicable")

        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify we're in fallback mode
            assert orch._rust_orch is None, "Should be in Python fallback mode"

            # Should use Python orchestrator for single log (always does)
            result = await orch.process_crash_log(sample_logs[0])

            assert isinstance(result, tuple)
            assert len(result) == 4
            log_path, report_lines, scan_failed, stats = result

            assert isinstance(log_path, Path)
            assert isinstance(report_lines, list)
            assert isinstance(scan_failed, bool)
            assert isinstance(stats, Counter)

        print("✅ Single log processing works with Python fallback")

    async def test_fallback_batch_processing(self, yamldata: Any, sample_logs: list[Path], force_rust_init_failure: Any) -> None:
        """Test batch processing falls back to Python when Rust init fails."""
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust module not available - fallback test not applicable")

        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify we're in fallback mode
            assert orch._rust_orch is None, "Should be in Python fallback mode"

            # Process batch - should use Python fallback since Rust is unavailable
            results = await orch.process_crash_logs_batch(sample_logs)

            assert len(results) == len(sample_logs)

            for result in results:
                assert isinstance(result, tuple)
                assert len(result) == 4
                log_path, report_lines, scan_failed, stats = result
                assert isinstance(log_path, Path)
                assert isinstance(report_lines, list)
                assert isinstance(scan_failed, bool)
                assert isinstance(stats, Counter)

        print(f"✅ Batch processing ({len(sample_logs)} logs) works with Python fallback")

    async def test_fallback_large_batch_uses_python(self, yamldata: Any, sample_logs: list[Path], force_rust_init_failure: Any) -> None:
        """Test that large batches use Python when Rust is unavailable.

        Normally, batches of 5+ logs would trigger Rust processing.
        When Rust init fails, should gracefully use Python instead.
        """
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust module not available - fallback test not applicable")

        # Create more logs to ensure we'd normally trigger Rust processing
        large_batch = sample_logs * 2  # 10 logs

        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            # Verify we're in fallback mode
            assert orch._rust_orch is None, "Should be in Python fallback mode"

            # Process large batch - would normally use Rust, but should fall back to Python
            results = await orch.process_crash_logs_batch(large_batch)

            assert len(results) == len(large_batch)

            for result in results:
                assert isinstance(result, tuple)
                assert len(result) == 4

        print(f"✅ Large batch ({len(large_batch)} logs) processed via Python fallback")


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
            patch("ClassicLib.ScanLog.OrchestratorCore.yaml_settings_async") as mock_yaml,
            patch("ClassicLib.ScanLog.OrchestratorCore.classic_settings_async") as mock_classic,
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
        with patch("ClassicLib.rust.orchestrator_api.get_yamldata", return_value=yamldata_batch_only):
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
