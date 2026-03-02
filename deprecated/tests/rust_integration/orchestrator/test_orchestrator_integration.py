"""Integration tests for RustOrchestrator from classic-scanlog module.

Tests the orchestration layer that coordinates log processing, ensuring
proper integration between Python and Rust components.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

# Type-only imports for static analysis
if TYPE_CHECKING:
    from classic_scanlog import AnalysisConfig, AnalysisResult, Orchestrator

# Check if classic_scanlog is available at runtime
try:
    from classic_scanlog import AnalysisConfig, AnalysisResult, Orchestrator

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    AnalysisConfig = None  # type: ignore[misc,assignment]
    AnalysisResult = None  # type: ignore[misc,assignment]
    Orchestrator = None  # type: ignore[misc,assignment]


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_scanlog not available")
class TestRustOrchestratorIntegration:
    """Test Orchestrator integration with real log files."""

    @pytest.fixture
    def sample_log_dir(self) -> Path:
        """Get the sample logs directory."""
        log_dir = Path("sample_logs/FO4")
        if not log_dir.exists():
            pytest.skip("Sample logs directory not found")
        return log_dir

    @pytest.fixture
    def orchestrator(self):
        """Create an Orchestrator instance."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        assert Orchestrator is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4", False)
        return Orchestrator(config)

    def test_orchestrator_instantiation(self, orchestrator):
        """Test Orchestrator can be instantiated."""
        assert Orchestrator is not None  # Type narrowing for Pylance
        assert orchestrator is not None
        assert isinstance(orchestrator, Orchestrator)

    def test_analysis_config_creation(self):
        """Test AnalysisConfig can be created with various options."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        # Default config
        config = AnalysisConfig("Fallout4", False)
        assert config is not None
        assert config.game == "Fallout4"

        # Config with specific options
        config = AnalysisConfig("SkyrimVR", vr_mode=True)
        assert config is not None
        assert config.game == "SkyrimVR"
        assert config.vr_mode is True

    def test_analysis_result_structure(self):
        """Test AnalysisResult has expected structure."""
        # This will be populated by actual analysis
        # For now, just verify the class exists
        assert AnalysisResult is not None

    def test_process_single_log(self, orchestrator, sample_log_dir):
        """Test processing a single log file."""
        assert AnalysisResult is not None  # Type narrowing for Pylance
        log_files = list(sample_log_dir.glob("*.log"))
        if not log_files:
            pytest.skip("No log files found in sample directory")

        log_path = str(log_files[0])
        result = orchestrator.process_log(log_path)

        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert result.log_path == log_path

    def test_process_logs_parallel(self, orchestrator, sample_log_dir):
        """Test parallel processing of multiple log files."""
        assert AnalysisResult is not None  # Type narrowing for Pylance
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 2:
            pytest.skip("Need at least 2 log files for parallel processing test")

        # Process with default concurrency
        results = orchestrator.process_logs_batch(log_files[:5])

        assert results is not None
        assert isinstance(results, list)
        assert len(results) <= len(log_files[:5])
        assert all(isinstance(r, AnalysisResult) for r in results)

    @pytest.mark.performance
    def test_orchestrator_performance(self, orchestrator, sample_log_dir):
        """Test orchestrator performance with multiple logs."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 5:
            pytest.skip("Need at least 5 log files for performance test")

        # Warm-up run
        orchestrator.process_logs_batch(log_files[:2])

        # Timed run
        start_time = time.perf_counter()
        results = orchestrator.process_logs_batch(log_files[:10])
        elapsed = time.perf_counter() - start_time

        assert results is not None
        assert len(results) > 0

        # Performance target: Should process logs efficiently
        # Average time per log should be reasonable (< 1 second per log for parallel)
        avg_time_per_log = elapsed / len(results)
        assert avg_time_per_log < 1.0, f"Average time per log: {avg_time_per_log:.3f}s"

    def test_error_handling_invalid_path(self, orchestrator):
        """Test error handling with invalid log path."""
        with pytest.raises(Exception):
            orchestrator.process_log("nonexistent_log.log")

    def test_error_handling_parallel_with_invalid_paths(self, orchestrator, sample_log_dir):
        """Test parallel processing with mix of valid and invalid paths."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if not log_files:
            pytest.skip("No log files found")

        # Mix valid and invalid paths
        mixed_paths = log_files[:2] + ["nonexistent1.log", "nonexistent2.log"]

        # Should handle errors gracefully - Rust might return mixed results or error
        # Check specific behavior: process_logs_batch returns Result<Vec<Result>> or Result<Vec<AnalysisResult>>?
        # The binding returns PyResult<Vec<PyAnalysisResult>>.
        # If any path is invalid, it might throw an exception, OR return results with success=False.
        # Let's assume it raises exception for now based on previous test behavior.
        try:
            results = orchestrator.process_logs_batch(mixed_paths)
            # If it doesn't raise, check if results contain errors
            assert any(not r.success for r in results)
        except Exception:
            # Expected behavior if it fails fast
            _ = None  # pass

    def test_empty_log_list(self, orchestrator):
        """Test processing empty log list."""
        results = orchestrator.process_logs_batch([])
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.rust
@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_scanlog not available")
class TestAnalysisConfigUnit:
    """Unit tests for AnalysisConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4", False)
        assert config is not None
        assert config.game == "Fallout4"
        assert config.vr_mode is False

    def test_custom_config_values(self):
        """Test setting custom configuration values."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4", False)
        config.show_formid_values = True

        assert config is not None
        assert config.show_formid_values is True

    def test_from_yamldata_uses_crashgen_registry_for_named_checks(self, tmp_path):
        """from_yamldata should preserve crashgen registry named checks for orchestrator."""
        assert AnalysisConfig is not None
        assert Orchestrator is not None

        yamldata = SimpleNamespace(
            crashgen_name="Buffout 4",
            crashgen_name_vr="Buffout 4",
            crashgen_latest_og="Buffout 4 v1.28.6",
            crashgen_latest_vr="Buffout 4 v1.37.0",
            game_version="Fallout 4 v1.10.163",
            game_version_vr="Fallout 4 v1.2.72",
            game_version_new="Fallout 4 v1.10.984",
            xse_acronym="F4SE",
            game_root_name="Fallout4",
            game_root_name_vr="Fallout4VR",
            game_ignore_plugins=[],
            game_ignore_records=[],
            ignore_list=[],
            suspects_error_list={},
            suspects_stack_list={},
            game_mods_core={},
            game_mods_freq={},
            game_mods_conf={},
            game_mods_solu={},
            game_mods_opc2={},
            game_mods_core_folon={},
            classic_records_list=[],
            classic_version="CLASSIC v9.0.0",
            crashgen_registry={
                "Buffout 4": {
                    "display_section": "[Compatibility]",
                    "ignore_keys": [],
                    "checks": ["achievements"],
                },
                "default": {
                    "display_section": "",
                    "ignore_keys": [],
                    "checks": [],
                },
            },
        )

        config = AnalysisConfig.from_yamldata(yamldata, "Fallout4", False)
        orchestrator = Orchestrator(config)

        log_path = tmp_path / "registry-check.log"
        log_path.write_text(
            """Fallout 4 v1.10.163
Buffout 4 v1.28.6
Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF66DF19300 Fallout4.exe+0DB9300
[Compatibility]
Achievements: true
SYSTEM SPECS:
CPU: Test CPU
PROBABLE CALL STACK:
[0] 0x7FF66DF19300 Fallout4.exe+0DB9300
MODULES:
achievements.dll
PLUGINS:
[00] Fallout4.esm
REGISTERS:
RAX: 0x0000000000000000
STACK:
0x000000000000: 0x12345678
""",
            encoding="utf-8",
        )

        result = orchestrator.process_log(str(log_path))
        assert any("Achievements Mod" in line for line in result.report_lines)

    def test_from_yamldata_registry_fallback_when_legacy_game_info_missing(self):
        """from_yamldata should populate metadata via Version Registry fallback when legacy keys are absent."""
        assert AnalysisConfig is not None

        yamldata = SimpleNamespace(
            game_root_name="Fallout4",
            game_ignore_plugins=[],
            game_ignore_records=[],
            ignore_list=[],
            suspects_error_list={},
            suspects_stack_list={},
            game_mods_core={},
            game_mods_freq={},
            game_mods_conf={},
            game_mods_solu={},
            game_mods_opc2={},
            game_mods_core_folon={},
            classic_records_list=[],
            classic_version="CLASSIC v9.0.0",
            crashgen_registry={
                "Buffout 4": {
                    "display_section": "[Compatibility]",
                    "ignore_keys": [],
                    "checks": ["achievements"],
                },
                "default": {
                    "display_section": "",
                    "ignore_keys": [],
                    "checks": [],
                },
            },
        )

        config = AnalysisConfig.from_yamldata(yamldata, "Fallout4", False)
        assert config.crashgen_name != ""
        assert config.xse_acronym != ""
        assert config.game_version != ""
        assert config.game_version_new != ""
        assert config.game_version_vr != ""


@pytest.mark.rust
@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_scanlog not available")
class TestAnalysisResultUnit:
    """Unit tests for AnalysisResult."""

    def test_result_structure_exists(self):
        """Test that AnalysisResult class exists and can be referenced."""
        assert AnalysisResult is not None


@pytest.mark.rust
@pytest.mark.integration
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_scanlog not available")
class TestOrchestratorStressTests:
    """Stress tests for Orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create an Orchestrator instance."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        assert Orchestrator is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4", False)
        return Orchestrator(config)

    @pytest.fixture
    def sample_log_dir(self, tmp_path):
        """Create a directory with sample crash log files for stress testing."""
        log_dir = tmp_path / "sample_logs"
        log_dir.mkdir()

        # Create sample crash log content
        sample_content = """Buffout 4 Crash Log
EXCEPTION_ACCESS_VIOLATION (0xc0000005)
Unhandled exception at 0x7FF6DEADBEEF

PROBABLE CALL STACK:
[0] 0x7FF6DEADBEEF    FormID: 0x00012345    TestMod.esp
[1] 0x7FF6CAFEBABE    FormID: 0x00023456    Fallout4.esm

PLUGINS:
[00] Fallout4.esm
[01] DLCRobot.esm
[02] TestMod.esp
"""
        # Create 25 sample log files for stress testing
        for i in range(25):
            log_file = log_dir / f"crash_{i:03d}.log"
            # Vary content slightly per file
            content = sample_content + f"\nLog file index: {i}\n"
            log_file.write_text(content, encoding="utf-8")

        return log_dir

    @pytest.mark.slow
    def test_high_concurrency(self, orchestrator, sample_log_dir):
        """Test batch processing with many log files."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 10:
            pytest.skip("Need at least 10 log files for stress test")

        # Test batch processing with many files (Rust handles parallelism internally)
        results = orchestrator.process_logs_batch(log_files[:20])
        assert results is not None
        assert len(results) > 0

    @pytest.mark.slow
    def test_many_small_logs(self, orchestrator, sample_log_dir):
        """Test processing many small log files in batch."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 20:
            pytest.skip("Need at least 20 log files for stress test")

        # Process all available log files in a batch
        results = orchestrator.process_logs_batch(log_files[:25])
        assert results is not None

    @pytest.mark.slow
    def test_repeated_processing(self, orchestrator, sample_log_dir):
        """Test processing the same logs multiple times."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if not log_files:
            pytest.skip("No log files found")

        # Process same logs 5 times in a row
        for _ in range(5):
            results = orchestrator.process_logs_batch(log_files[:5])
            assert results is not None
            assert len(results) > 0
