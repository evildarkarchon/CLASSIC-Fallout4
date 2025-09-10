"""Utilities and constants for ScanGame operations."""

import os
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None  # Handle gracefully if not installed

# Import async utilities if available
try:
    from ClassicLib.AsyncUtil import read_lines_with_encoding_async

    ASYNC_ENCODING_AVAILABLE = True
except ImportError:
    ASYNC_ENCODING_AVAILABLE = False

    # Provide a stub to satisfy type checker
    async def read_lines_with_encoding_async(file_path: Path) -> list[str]:
        """Stub function - should never be called when ASYNC_ENCODING_AVAILABLE is False."""
        raise NotImplementedError("Async encoding utilities not available")


def get_optimal_limits() -> dict[str, int]:
    """Calculate optimal concurrency limits based on system resources."""
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
    "read_lines_with_encoding_async",
    "get_optimal_limits",
    "MAX_CONCURRENT_SUBPROCESSES",
    "MAX_CONCURRENT_FILE_OPS",
    "MAX_CONCURRENT_LOG_READS",
    "MAX_CONCURRENT_DDS_READS",
    "SCAN_GAME_CORE_KEY",
]
