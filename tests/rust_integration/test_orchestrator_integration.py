"""Integration tests for RustOrchestrator from classic-scanlog module.

Tests the orchestration layer that coordinates log processing, ensuring
proper integration between Python and Rust components.
"""

from __future__ import annotations

import time
from pathlib import Path
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
        log_dir = Path("tests/sample_logs")
        if not log_dir.exists():
            pytest.skip("Sample logs directory not found")
        return log_dir

    @pytest.fixture
    def orchestrator(self):
        """Create an Orchestrator instance."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        assert Orchestrator is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4")
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
        config = AnalysisConfig("Fallout4")
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
        results = orchestrator.process_logs_parallel(log_files[:5])

        assert results is not None
        assert isinstance(results, list)
        assert len(results) <= len(log_files[:5])
        assert all(isinstance(r, AnalysisResult) for r in results)

    def test_process_logs_parallel_with_callback(self, orchestrator, sample_log_dir):
        """Test parallel processing with progress callback."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 2:
            pytest.skip("Need at least 2 log files for parallel processing test")

        processed = []

        def progress_callback(path: str):
            processed.append(path)

        results = orchestrator.process_logs_parallel(
            log_files[:5],
            max_concurrent=3,
            progress_callback=progress_callback,
        )

        assert results is not None
        assert len(processed) > 0
        assert all(p in log_files[:5] for p in processed)

    def test_process_logs_parallel_custom_concurrency(self, orchestrator, sample_log_dir):
        """Test parallel processing with custom concurrency limit."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 3:
            pytest.skip("Need at least 3 log files for concurrency test")

        # Test with different concurrency levels
        for concurrency in [1, 2, 4]:
            results = orchestrator.process_logs_parallel(
                log_files[:5],
                max_concurrent=concurrency,
            )
            assert results is not None
            assert isinstance(results, list)

    @pytest.mark.performance
    def test_orchestrator_performance(self, orchestrator, sample_log_dir):
        """Test orchestrator performance with multiple logs."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 5:
            pytest.skip("Need at least 5 log files for performance test")

        # Warm-up run
        orchestrator.process_logs_parallel(log_files[:2])

        # Timed run
        start_time = time.perf_counter()
        results = orchestrator.process_logs_parallel(log_files[:10], max_concurrent=5)
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

        # Should handle errors gracefully
        with pytest.raises(Exception):
            orchestrator.process_logs_parallel(mixed_paths)

    def test_empty_log_list(self, orchestrator):
        """Test processing empty log list."""
        results = orchestrator.process_logs_parallel([])
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.performance
    def test_parallel_vs_sequential_performance(self, orchestrator, sample_log_dir):
        """Compare parallel vs sequential processing performance."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 4:
            pytest.skip("Need at least 4 log files for comparison")

        # Sequential (concurrency = 1)
        start_seq = time.perf_counter()
        results_seq = orchestrator.process_logs_parallel(log_files[:8], max_concurrent=1)
        time_seq = time.perf_counter() - start_seq

        # Parallel (concurrency = 4)
        start_par = time.perf_counter()
        results_par = orchestrator.process_logs_parallel(log_files[:8], max_concurrent=4)
        time_par = time.perf_counter() - start_par

        assert len(results_seq) == len(results_par)

        # Parallel should be faster (allow 10% margin for overhead)
        speedup = time_seq / time_par
        assert speedup > 0.9, f"Parallel speedup: {speedup:.2f}x (expected > 0.9x)"


@pytest.mark.rust
@pytest.mark.unit
@pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_scanlog not available")
class TestAnalysisConfigUnit:
    """Unit tests for AnalysisConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4")
        assert config is not None
        assert config.game == "Fallout4"
        assert config.vr_mode is False

    def test_custom_config_values(self):
        """Test setting custom configuration values."""
        assert AnalysisConfig is not None  # Type narrowing for Pylance
        config = AnalysisConfig("Fallout4")
        config.show_formid_values = True

        assert config is not None
        assert config.show_formid_values is True


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
        config = AnalysisConfig("Fallout4")
        return Orchestrator(config)

    @pytest.mark.slow
    def test_high_concurrency(self, orchestrator, sample_log_dir):
        """Test with high concurrency level."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 10:
            pytest.skip("Need at least 10 log files for stress test")

        # Test with very high concurrency
        results = orchestrator.process_logs_parallel(log_files[:20], max_concurrent=20)
        assert results is not None
        assert len(results) > 0

    @pytest.mark.slow
    def test_many_small_logs(self, orchestrator, sample_log_dir):
        """Test processing many small log files."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if len(log_files) < 20:
            pytest.skip("Need at least 20 log files for stress test")

        results = orchestrator.process_logs_parallel(log_files[:50], max_concurrent=10)
        assert results is not None

    @pytest.mark.slow
    def test_repeated_processing(self, orchestrator, sample_log_dir):
        """Test processing the same logs multiple times."""
        log_files = [str(f) for f in sample_log_dir.glob("*.log")]
        if not log_files:
            pytest.skip("No log files found")

        # Process same logs 5 times
        for _ in range(5):
            results = orchestrator.process_logs_parallel(log_files[:5], max_concurrent=3)
            assert results is not None
            assert len(results) > 0
