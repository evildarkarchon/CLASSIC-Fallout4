"""ScanGame core module - refactored components."""

from .dds_processor import DDSProcessor
from .file_operations import FileOperations
from .log_processor import LogProcessor
from .utils import (
    ASYNC_ENCODING_AVAILABLE,
    MAX_CONCURRENT_DDS_READS,
    MAX_CONCURRENT_FILE_OPS,
    MAX_CONCURRENT_LOG_READS,
    MAX_CONCURRENT_SUBPROCESSES,
    SCAN_GAME_CORE_KEY,
    get_optimal_limits,
    read_lines_with_encoding_async,
)
from .validators import ScanValidators

__all__ = [
    # Processors
    "DDSProcessor",
    "FileOperations",
    "LogProcessor",
    "ScanValidators",
    # Utils
    "ASYNC_ENCODING_AVAILABLE",
    "read_lines_with_encoding_async",
    "get_optimal_limits",
    "MAX_CONCURRENT_SUBPROCESSES",
    "MAX_CONCURRENT_FILE_OPS",
    "MAX_CONCURRENT_LOG_READS",
    "MAX_CONCURRENT_DDS_READS",
    "SCAN_GAME_CORE_KEY",
]
