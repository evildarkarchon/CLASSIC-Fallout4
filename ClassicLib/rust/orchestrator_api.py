"""
Python API layer for Rust backend orchestrator.

This module provides a thin wrapper around classic_scanlog's RustOrchestrator,
handling configuration and result processing. Configuration data is
automatically loaded using classic-config crate (15-30x faster than Python).

Phase 3 Integration - Part of the full backend migration plan.
"""

from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

try:
    from classic_scanlog import RustOrchestrator, AnalysisConfig, AnalysisResult
    from classic_config import YamlData
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    RustOrchestrator = None
    AnalysisConfig = None
    AnalysisResult = None
    YamlData = None

from ClassicLib.integration.factory import get_yamldata


@dataclass
class BatchAnalysisResult:
    """Result of batch crash log analysis"""

    results: List['AnalysisResult']
    total_time_ms: int
    parallelism_factor: float

    def successful_results(self) -> List['AnalysisResult']:
        """Get only successful results"""
        return [r for r in self.results if r.success]

    def failed_results(self) -> List['AnalysisResult']:
        """Get only failed results"""
        return [r for r in self.results if not r.success]

    def save_all_reports(self, output_dir: Path) -> None:
        """Save all reports to output directory"""
        output_dir.mkdir(parents=True, exist_ok=True)

        for result in self.successful_results():
            log_path = Path(result.log_path)
            report_path = output_dir / f"{log_path.stem}_report.md"
            report_path.write_text("\n".join(result.report_lines), encoding="utf-8")


class ClassicOrchestrator:
    """
    Python API layer for Rust backend.

    This class provides a thin wrapper around classic_scanlog's Rust orchestrator,
    handling configuration and result processing. Configuration data is
    automatically loaded using classic-config crate (15-30x faster than Python).

    Usage:
        >>> orchestrator = ClassicOrchestrator()
        >>> results = orchestrator.process_crash_logs_batch(
        ...     log_paths=[Path("crash1.log"), Path("crash2.log")],
        ...     progress_callback=lambda path: print(f"Processing {path}")
        ... )
        >>> for result in results.successful_results():
        ...     print(f"Processed {result.log_path} in {result.processing_time_ms}ms")
    """

    def __init__(self):
        """
        Initialize orchestrator with Rust-generated configuration.

        Raises:
            RuntimeError: If Rust components are not available
        """
        if not RUST_AVAILABLE:
            raise RuntimeError(
                "Rust components not available. Install classic_scanlog and classic_config modules."
            )

        # Get YamlData from factory (uses Rust if available, Python fallback otherwise)
        self.yamldata = get_yamldata()

        # Create AnalysisConfig from YamlData
        self.config = AnalysisConfig.from_yamldata(self.yamldata)

        # Create RustOrchestrator
        self.orchestrator = RustOrchestrator(self.config)

    def process_crash_log(
        self,
        log_path: Path,
    ) -> AnalysisResult:
        """
        Process a single crash log.

        Convenience wrapper around process_crash_logs_batch for single logs.

        Args:
            log_path: Path to crash log file

        Returns:
            AnalysisResult for the log

        Raises:
            RuntimeError: If analysis fails
            IOError: If log file cannot be read
        """
        results = self.process_crash_logs_batch([log_path])
        if not results.results:
            raise RuntimeError(f"No results returned for {log_path}")

        return results.results[0]

    def process_crash_logs_batch(
        self,
        log_paths: List[Path],
        max_concurrent: int = 10,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> BatchAnalysisResult:
        """
        Process multiple crash logs in parallel.

        This is the primary entry point for batch crash log analysis.
        All analysis happens in Rust for maximum performance.

        Args:
            log_paths: Paths to crash log files
            max_concurrent: Maximum number of logs to process concurrently (default: 10)
            progress_callback: Optional callback for progress updates (called with log path)

        Returns:
            BatchAnalysisResult with all analysis results and statistics

        Raises:
            RuntimeError: If analysis fails catastrophically
            IOError: If log files cannot be read

        Performance:
            - Single log: 15-20ms (Rust-accelerated)
            - 10 logs: 150-200ms (parallel)
            - 100 logs: 1.5-2s (parallel)
        """
        import time

        start = time.perf_counter()

        # Convert Path objects to strings
        log_paths_str = [str(p) for p in log_paths]

        # Process logs in parallel using RustOrchestrator
        results = self.orchestrator.process_logs_parallel(
            log_paths=log_paths_str,
            max_concurrent=max_concurrent,
            progress_callback=progress_callback,
        )

        total_time_ms = int((time.perf_counter() - start) * 1000)

        # Calculate parallelism factor
        # (total sequential time / actual parallel time)
        sequential_time = sum(r.processing_time_ms for r in results)
        parallelism_factor = sequential_time / total_time_ms if total_time_ms > 0 else 1.0

        return BatchAnalysisResult(
            results=results,
            total_time_ms=total_time_ms,
            parallelism_factor=parallelism_factor,
        )

    def get_config(self) -> AnalysisConfig:
        """Get the current analysis configuration"""
        return self.config

    def __repr__(self) -> str:
        return (
            f"ClassicOrchestrator(game='{self.config.game}', "
            f"vr_mode={self.config.vr_mode}, "
            f"rust_available={RUST_AVAILABLE})"
        )


# Convenience function for quick processing
def process_crash_log(log_path: Path) -> AnalysisResult:
    """
    Convenience function to process a single crash log.

    Args:
        log_path: Path to crash log file

    Returns:
        AnalysisResult with report and statistics
    """
    orchestrator = ClassicOrchestrator()
    return orchestrator.process_crash_log(log_path)


def process_crash_logs_batch(
    log_paths: List[Path],
    max_concurrent: int = 10,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> BatchAnalysisResult:
    """
    Convenience function to process multiple crash logs in parallel.

    Args:
        log_paths: Paths to crash log files
        max_concurrent: Maximum concurrent logs (default: 10)
        progress_callback: Optional progress callback

    Returns:
        BatchAnalysisResult with all results and statistics
    """
    orchestrator = ClassicOrchestrator()
    return orchestrator.process_crash_logs_batch(
        log_paths=log_paths,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback,
    )
