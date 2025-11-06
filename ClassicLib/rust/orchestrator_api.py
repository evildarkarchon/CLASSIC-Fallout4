"""
Python API layer for Rust backend orchestrator.

This module provides a thin wrapper around classic_scanlog's Orchestrator,
handling configuration and result processing. Configuration data is
automatically loaded using classic-config crate (15-30x faster than Python).

Phase 3 Integration - Part of the full backend migration plan.

Async/Sync Behavior:
    All methods in ClassicOrchestrator are SYNCHRONOUS (blocking):
    - process_crash_log() - Blocks while processing log with Rust
    - process_crash_logs_batch() - Blocks with parallel processing in Rust

    These methods call synchronous Rust functions with internal parallelism.

AsyncBridge Usage (GUI Applications Only):
    For Qt GUI applications, wrap with AsyncBridge:

    ```python
    from ClassicLib.AsyncBridge import AsyncBridge
    from ClassicLib.rust.orchestrator_api import ClassicOrchestrator

    orchestrator = ClassicOrchestrator()
    bridge = AsyncBridge.get_instance()

    # Wrap blocking orchestrator calls
    result = bridge.run_async(lambda: orchestrator.process_crash_log(log_path))

    # Or batch processing
    results = bridge.run_async(lambda: orchestrator.process_crash_logs_batch(
        log_paths, max_concurrent=10
    ))
    ```

CLI Usage:
    For CLI applications, use directly without AsyncBridge:

    ```python
    from pathlib import Path
    from ClassicLib.rust.orchestrator_api import process_crash_log

    # Direct usage - Rust handles parallelism internally
    result = process_crash_log(Path("crash.log"))
    print(f"Success: {result.success}")
    print(f"Time: {result.processing_time_ms}ms")
    ```
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Always import for type checking, conditionally at runtime
if TYPE_CHECKING:
    from classic_config import YamlData
    from classic_scanlog import AnalysisConfig, AnalysisResult, Orchestrator
    RUST_AVAILABLE: bool
else:
    # Runtime imports - these will be the actual classes or None
    try:
        from classic_config import YamlData
        from classic_scanlog import AnalysisConfig, AnalysisResult, Orchestrator
        RUST_AVAILABLE = True
    except ImportError:
        RUST_AVAILABLE = False
        # Runtime fallbacks - never used due to RUST_AVAILABLE check
        YamlData = Any  # type: ignore[misc, assignment]
        AnalysisConfig = Any  # type: ignore[misc, assignment]
        AnalysisResult = Any  # type: ignore[misc, assignment]
        Orchestrator = Any  # type: ignore[misc, assignment]

from ClassicLib.integration.factory import get_yamldata


@dataclass
class BatchAnalysisResult:
    """
    Represents the results of a batch analysis with summarization and report-saving
    capabilities.

    This class holds the detailed outcomes of an analysis conducted on a batch of
    inputs. It provides mechanisms to filter results based on their success or
    failure and to persist generated reports associated with the analysis.

    Attributes:
        results (List[AnalysisResult]): List of individual analysis results.
        total_time_ms (int): Total time taken to process the batch analysis,
            measured in milliseconds.
        parallelism_factor (float): Degree of parallelism used during the analysis
            process, indicating how many analyses were executed in parallel.
    """

    results: list[AnalysisResult]
    total_time_ms: int
    parallelism_factor: float

    def successful_results(self) -> list[AnalysisResult]:
        """
        Filters and returns a list of successful analysis results.

        This method iterates over the `results` attribute and checks if
        each result meets the success condition. If the condition is met,
        the result is considered successful and it will be included in
        the returned list.

        Returns:
            list[AnalysisResult]: A list containing only successful analysis results.
        """
        return [r for r in self.results if r.success]

    def failed_results(self) -> list[AnalysisResult]:
        """
        Gets a list of failed analysis results.

        This method iterates over the `results` attribute and filters out
        the analysis results that are marked as unsuccessful.

        Returns:
            List[AnalysisResult]: A list of `AnalysisResult` objects where the
            `success` attribute is set to False.
        """
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
    Orchestrates analysis configuration and crash log processing.

    ClassicOrchestrator serves as a bridge between Python and Rust components, managing
    the configuration and processing of crash logs. It can process logs individually or
    in batches using Rust for maximum performance, with optional progress feedback.

    Attributes:
        yamldata (YamlData): Configuration data loaded from a YAML source.
        config (AnalysisConfig): Parsed analysis configuration created from the YAML data.
        orchestrator (Orchestrator): Rust-driven orchestrator for crash log processing.
    """

    def __init__(self) -> None:
        """
        Initializes the class and sets up the required components for configuration
        and data orchestration.

        The constructor ensures the availability of Rust components and reliably
        constructs instances of `YamlData`, `AnalysisConfig`, and `Orchestrator`.
        It uses a fallback mechanism to handle scenarios where Rust components are
        not available.

        Raises:
            RuntimeError: If Rust components are unavailable or missing. Provides
            instructions to install required modules.
        """
        if not RUST_AVAILABLE:
            raise RuntimeError(
                "Rust components not available. Install classic_scanlog and classic_config modules."
            )

        # Get YamlData from factory (uses Rust if available, Python fallback otherwise)
        self.yamldata = get_yamldata()

        # Create AnalysisConfig from YamlData
        self.config = AnalysisConfig.from_yamldata(self.yamldata)

        # Create Orchestrator
        self.orchestrator = Orchestrator(self.config)

    def process_crash_log(
        self,
        log_path: Path,
    ) -> AnalysisResult:
        """
        Processes a single crash log and returns the analysis result.

        This method processes a crash log file located at the specified `log_path`
        and retrieves the corresponding analysis result. If no results are produced,
        an exception is raised. Internally, this method delegates the processing
        to another method that handles multiple crash logs but limits the scope
        to a single log in this case.

        Args:
            log_path (Path): The file path of the crash log to be processed.

        Returns:
            AnalysisResult: The result of analyzing the provided crash log.

        Raises:
            RuntimeError: If no results are returned for the provided `log_path`.
        """
        results = self.process_crash_logs_batch([log_path])
        if not results.results:
            raise RuntimeError(f"No results returned for {log_path}")

        return results.results[0]

    def process_crash_logs_batch(
        self,
        log_paths: list[Path],
        max_concurrent: int = 10,
        progress_callback: Callable[[str], None] | None = None,
    ) -> BatchAnalysisResult:
        """
        Processes a batch of crash log files in parallel and returns the analysis results.

        This method processes logs in a parallel fashion using the Orchestrator tool,
        which allows for higher efficiency when handling multiple files. It also computes
        the total processing time and evaluates the parallelism factor.

        Args:
            log_paths (List[Path]): A list of Path objects representing the paths to the crash logs.
            max_concurrent (int): Maximum number of concurrent processes allowed during analysis.
            progress_callback (Optional[Callable[[str], None]]): Optional callback function to provide
                progress updates. The function takes a single string argument.

        Returns:
            BatchAnalysisResult: An object containing the processed results for each log, the total
            processing time (in milliseconds), and the parallelism factor.
        """
        import time

        start = time.perf_counter()

        # Convert Path objects to strings
        log_paths_str = [str(p) for p in log_paths]

        # Process logs in parallel using Orchestrator
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
        """
        Retrieves the configuration for analysis.

        This method returns the current `AnalysisConfig` object assigned to the instance,
        which contains the necessary configuration details for analysis operations.

        Returns:
            AnalysisConfig: The configuration object for analysis.

        """
        return self.config

    def __repr__(self) -> str:
        """
        Provides a string representation of the instance for debugging and logging purposes.

        Returns:
            str: A string that contains a readable summary of key attributes of the
            ClassicOrchestrator instance.
        """
        return (
            f"ClassicOrchestrator(game='{self.config.game}', "
            f"vr_mode={self.config.vr_mode}, "
            f"rust_available={RUST_AVAILABLE})"
        )


# Convenience function for quick processing
def process_crash_log(log_path: Path) -> AnalysisResult:
    """
    Processes a crash log and returns its analysis result.

    This function utilizes a `ClassicOrchestrator` instance to perform
    the processing of a given crash log file. It extracts and analyzes
    the contents of the log file provided through the given path and
    returns the resulting analysis.

    Args:
        log_path (Path): The file path to the crash log that needs to be processed.

    Returns:
        AnalysisResult: The result of the processed crash log.
    """
    orchestrator = ClassicOrchestrator()
    return orchestrator.process_crash_log(log_path)


def process_crash_logs_batch(
    log_paths: list[Path],
    max_concurrent: int = 10,
    progress_callback: Callable[[str], None] | None = None,
) -> BatchAnalysisResult:
    """
    Processes a batch of crash logs concurrently and provides the analysis result.

    This function uses a ClassicOrchestrator to process multiple crash logs
    simultaneously. It supports specifying the maximum number of concurrent tasks
    as well as an optional progress callback that is invoked with updates during
    the process.

    Args:
        log_paths: A list of file paths representing crash logs to be processed.
        max_concurrent: The maximum number of concurrent crash log processing tasks
            allowed. Default is 10.
        progress_callback: An optional callable that accepts a string argument to
            report progress updates during batch processing.

    Returns:
        BatchAnalysisResult: The result of the batch crash log analysis including
            details for each processed log.
    """
    orchestrator = ClassicOrchestrator()
    return orchestrator.process_crash_logs_batch(
        log_paths=log_paths,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback,
    )
