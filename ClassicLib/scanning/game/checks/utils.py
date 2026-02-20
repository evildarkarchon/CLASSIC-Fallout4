"""System resource-based concurrency utility.

This module provides functionality to derive optimal concurrency limits
based on system resources such as CPU and memory availability. Additionally,
it offers asynchronous file handling utilities and constants for managing
concurrent limits.

The module handles dependencies gracefully where certain utilities, such as
`psutil` or async encoding utilities, may not be available at runtime.
"""

import os
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None  # Handle gracefully if not installed

# Import async utilities if available
try:
    from ClassicLib.io.files.async_files import read_lines_with_encoding_async  # pyright: ignore[reportUnknownVariableType]

    ASYNC_ENCODING_AVAILABLE = True
except ImportError:
    ASYNC_ENCODING_AVAILABLE = False

    # Provide a stub to satisfy type checker
    async def read_lines_with_encoding_async(file_path: Path) -> list[str]:
        """Stub function - should never be called when ASYNC_ENCODING_AVAILABLE is False.

        Args:
            file_path: Path to the file to read.

        Returns:
            Never returns - always raises NotImplementedError.

        Raises:
            NotImplementedError: Always raised when called.

        """
        raise NotImplementedError("Async encoding utilities not available")


def get_optimal_limits() -> dict[str, int]:
    """Determine optimal limits for various operations based on system resources.

    This function calculates optimal limits for subprocesses, file operations, log
    reads, and DDS (data distribution service) reads by considering the available
    CPU count and system memory. If the `psutil` module is available, the memory
    factor is dynamically adjusted based on the total memory to improve accuracy.
    The results are capped at predefined maximums to ensure stability across
    different environments.

    Returns:
        dict[str, int]: A dictionary containing optimal limits for subprocesses,
        file operations (`file_ops`), log reads (`log_reads`), and DDS reads
        (`dds_reads`).

    """
    cpu_count = os.cpu_count() or 4

    # Try to get memory if psutil is available
    if psutil:
        memory_gb = psutil.virtual_memory().total / (1024**3)
        memory_factor = min(memory_gb / 8, 2.0)  # Scale based on memory (8GB baseline)
    else:
        memory_factor = 1.0

    return {
        "subprocesses": min(int(cpu_count * memory_factor), 8),  # Cap at 8 for stability
        "file_ops": min(int(cpu_count * 4 * memory_factor), 32),
        "log_reads": min(int(cpu_count * 8 * memory_factor), 64),
        "dds_reads": min(int(cpu_count * 16 * memory_factor), 128),
    }


# Get optimal limits based on system
_LIMITS = get_optimal_limits()
MAX_CONCURRENT_SUBPROCESSES = _LIMITS["subprocesses"]
MAX_CONCURRENT_FILE_OPS = _LIMITS["file_ops"]
MAX_CONCURRENT_LOG_READS = _LIMITS["log_reads"]
MAX_CONCURRENT_DDS_READS = _LIMITS["dds_reads"]

# Registry key for ScanGameCore singleton
SCAN_GAME_CORE_KEY = "scan_game_core"

# Re-export for convenience
__all__ = [
    "ASYNC_ENCODING_AVAILABLE",
    "MAX_CONCURRENT_DDS_READS",
    "MAX_CONCURRENT_FILE_OPS",
    "MAX_CONCURRENT_LOG_READS",
    "MAX_CONCURRENT_SUBPROCESSES",
    "SCAN_GAME_CORE_KEY",
    "get_optimal_limits",
    "read_lines_with_encoding_async",
]
