"""ScanGame core module - refactored components."""
# ruff: noqa: TID252 - Relative imports intentional for __init__.py re-exports

from .ba2_scanner import BA2ArchiveScanner
from .dds_processor import DDSProcessor
from .file_operations import FileOperations
from .log_processor import LogProcessor
from .report_builder import ScanReportBuilder
from .unpacked_scanner import UnpackedModsScanner
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
    "BA2ArchiveScanner",
    "DDSProcessor",
    "FileOperations",
    "LogProcessor",
    "ScanReportBuilder",
    "ScanValidators",
    "UnpackedModsScanner",
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
