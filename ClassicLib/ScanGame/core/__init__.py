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

# Optional enhanced DDS analyzer
try:
    from .dds_analyzer import DDSInfo, EnhancedDDSAnalyzer, analyze_dds
    HAS_DDS_ANALYZER = True
except ImportError:
    HAS_DDS_ANALYZER = False
    EnhancedDDSAnalyzer = None
    DDSInfo = None
    analyze_dds = None

__all__ = [
    # Processors
    "DDSProcessor",
    "FileOperations",
    "LogProcessor",
    "ScanValidators",
    # Enhanced DDS (optional)
    "EnhancedDDSAnalyzer",
    "DDSInfo",
    "analyze_dds",
    "HAS_DDS_ANALYZER",
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
