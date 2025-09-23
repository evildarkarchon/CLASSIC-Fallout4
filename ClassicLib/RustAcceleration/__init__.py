"""Rust acceleration module for CLASSIC.

This module provides Python wrappers for the high-performance Rust extensions,
with automatic fallback to pure Python implementations when Rust is not available.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import Rust extensions
try:
    import classic_core
    from classic_core import utils as rust_utils

    RUST_AVAILABLE = True
    logger.info("Rust extensions loaded successfully")
except ImportError as e:
    RUST_AVAILABLE = False
    rust_utils = None
    logger.warning(f"Rust extensions not available: {e}. Using pure Python implementations.")


class AcceleratedPathHandler:
    """Path handler with Rust acceleration when available."""

    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize the path handler.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)
        """
        if RUST_AVAILABLE:
            self._handler = rust_utils.PathHandler(cache_ttl_seconds=cache_ttl_seconds)
            self._use_rust = True
        else:
            self._handler = None
            self._use_rust = False
            self._cache = {}

    def normalize_path(self, path: str) -> str:
        """Normalize a path (resolve .. and ., convert to absolute).

        Args:
            path: Path to normalize

        Returns:
            Normalized path string
        """
        if self._use_rust:
            return self._handler.normalize_path(path)
        # Python fallback
        from ClassicLib.Utils.path_utils import validate_path

        path_obj = Path(path)
        try:
            return str(path_obj.resolve())
        except Exception:
            return str(path_obj)

    def validate_paths_batch(self, paths: list[str]) -> list[tuple[str, bool, str]]:
        """Validate multiple paths in parallel.

        Args:
            paths: List of paths to validate

        Returns:
            List of (path, is_valid, error_message) tuples
        """
        if self._use_rust:
            return self._handler.validate_paths_batch(paths)
        # Python fallback
        from ClassicLib.Utils.path_utils import validate_path

        results = []
        for path in paths:
            is_valid, msg = validate_path(path)
            results.append((path, is_valid, msg))
        return results

    def clear_cache(self):
        """Clear all caches."""
        if self._use_rust:
            self._handler.clear_cache()
        else:
            self._cache.clear()


class AcceleratedLogProcessor:
    """Log processor with Rust acceleration when available."""

    def __init__(self):
        """Initialize the log processor."""
        if RUST_AVAILABLE:
            self._processor = rust_utils.LogProcessor()
            self._use_rust = True
        else:
            self._processor = None
            self._use_rust = False

    def extract_formids(self, text: str) -> list[str]:
        """Extract FormIDs from text using optimized pattern matching.

        Args:
            text: Text to search

        Returns:
            List of FormID strings found
        """
        if self._use_rust:
            return self._processor.extract_formids(text)
        # Python fallback
        import re

        pattern = re.compile(r"(?i)(?:0x)?([0-9a-f]{6,8})\b")
        return [m.group(0) for m in pattern.finditer(text)]

    def extract_plugins(self, text: str) -> list[str]:
        """Extract plugin names from crash log.

        Args:
            text: Log text to search

        Returns:
            List of plugin names found
        """
        if self._use_rust:
            return self._processor.extract_plugins(text)
        # Python fallback
        plugins = []
        extensions = [".esp", ".esm", ".esl", ".esq"]

        for line in text.splitlines():
            line_lower = line.lower()
            for ext in extensions:
                if ext in line_lower:
                    # Simple extraction
                    start = line_lower.rfind("/", 0, line_lower.index(ext))
                    if start == -1:
                        start = line_lower.rfind("\\", 0, line_lower.index(ext))
                    if start == -1:
                        start = 0
                    else:
                        start += 1

                    end = line_lower.index(ext) + len(ext)
                    plugin = line[start:end]
                    if plugin and plugin not in plugins:
                        plugins.append(plugin)
        return plugins

    def parse_segments(self, lines: list[str]) -> list[tuple[str, list[str]]]:
        """Parse log into segments based on section headers.

        Args:
            lines: Log lines to parse

        Returns:
            List of (section_name, section_lines) tuples
        """
        if self._use_rust:
            return self._processor.parse_segments(lines)
        # Python fallback
        segments = []
        current_section = "HEADER"
        current_lines = []

        markers = ["MODULES:", "STACK:", "REGISTERS:", "STACK WALK:", "PROBABLE CALL STACK:"]

        for line in lines:
            line_upper = line.upper()

            found_section = False
            for marker in markers:
                if marker in line_upper:
                    if current_lines:
                        segments.append((current_section, current_lines))
                        current_lines = []
                    current_section = marker
                    found_section = True
                    break

            if not found_section:
                current_lines.append(line)

        if current_lines:
            segments.append((current_section, current_lines))

        return segments

    def filter_lines(
        self,
        lines: list[str],
        include_keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
    ) -> list[str]:
        """Fast line filtering based on keywords.

        Args:
            lines: Lines to filter
            include_keywords: Keywords that must be present
            exclude_keywords: Keywords that must not be present

        Returns:
            Filtered list of lines
        """
        if self._use_rust:
            return self._processor.filter_lines(lines, include_keywords, exclude_keywords)
        # Python fallback
        result = []
        for line in lines:
            line_lower = line.lower()

            if include_keywords:
                if not any(kw.lower() in line_lower for kw in include_keywords):
                    continue

            if exclude_keywords:
                if any(kw.lower() in line_lower for kw in exclude_keywords):
                    continue

            result.append(line)
        return result


class AcceleratedStringProcessor:
    """String processor with Rust acceleration when available."""

    def __init__(self):
        """Initialize the string processor."""
        if RUST_AVAILABLE:
            self._processor = rust_utils.StringProcessor()
            self._use_rust = True
        else:
            self._processor = None
            self._use_rust = False
            self._intern_pool = {}

    def process_batch(self, strings: list[str], operation: str) -> list[str]:
        """Process multiple strings in parallel.

        Args:
            strings: Strings to process
            operation: Operation to perform (upper, lower, trim, normalize)

        Returns:
            Processed strings
        """
        if self._use_rust:
            return self._processor.process_batch(strings, operation)
        # Python fallback
        if operation == "upper":
            return [s.upper() for s in strings]
        if operation == "lower":
            return [s.lower() for s in strings]
        if operation == "trim":
            return [s.strip() for s in strings]
        if operation == "normalize":
            return [" ".join(s.lower().split()) for s in strings]
        return strings

    def common_prefix(self, strings: list[str]) -> str:
        """Find common prefix of multiple strings.

        Args:
            strings: Strings to analyze

        Returns:
            Common prefix string
        """
        if self._use_rust:
            return self._processor.common_prefix(strings)
        # Python fallback
        if not strings:
            return ""

        min_len = min(len(s) for s in strings)
        first = strings[0]

        for i in range(min_len):
            if not all(s[i] == first[i] for s in strings):
                return first[:i]

        return first[:min_len]


class RustPerformanceMonitor:
    """Performance monitor with Rust integration."""

    def __init__(self):
        """Initialize the performance monitor."""
        if RUST_AVAILABLE:
            self._monitor = rust_utils.RustPerformanceMonitor()
            self._use_rust = True
        else:
            self._monitor = None
            self._use_rust = False
            self._metrics = {}

    def record_metric(self, operation: str, duration_ms: int, bytes_processed: int | None = None):
        """Record a performance metric.

        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            bytes_processed: Optional bytes processed
        """
        if self._use_rust:
            self._monitor.record_metric(operation, duration_ms, bytes_processed)
        else:
            # Python fallback
            if operation not in self._metrics:
                self._metrics[operation] = []
            self._metrics[operation].append((duration_ms, bytes_processed))

    def get_operation_stats(self, operation: str) -> dict[str, Any] | None:
        """Get statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Statistics dictionary or None if no data
        """
        if self._use_rust:
            return self._monitor.get_operation_stats(operation)
        # Python fallback
        if operation not in self._metrics:
            return None

        data = self._metrics[operation]
        durations = [d[0] for d in data]
        bytes_list = [d[1] for d in data if d[1] is not None]

        return {
            "count": len(data),
            "total_ms": sum(durations),
            "avg_ms": sum(durations) // len(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
            "max_ms": max(durations) if durations else 0,
            "bytes_processed": sum(bytes_list) if bytes_list else 0,
        }

    def clear_metrics(self):
        """Clear all metrics."""
        if self._use_rust:
            self._monitor.clear_metrics()
        else:
            self._metrics.clear()


# Convenience functions
def get_accelerated_path_handler(cache_ttl_seconds: int = 300) -> AcceleratedPathHandler:
    """Get an accelerated path handler instance.

    Args:
        cache_ttl_seconds: Cache TTL in seconds

    Returns:
        AcceleratedPathHandler instance
    """
    return AcceleratedPathHandler(cache_ttl_seconds)


def get_accelerated_log_processor() -> AcceleratedLogProcessor:
    """Get an accelerated log processor instance.

    Returns:
        AcceleratedLogProcessor instance
    """
    return AcceleratedLogProcessor()


def get_accelerated_string_processor() -> AcceleratedStringProcessor:
    """Get an accelerated string processor instance.

    Returns:
        AcceleratedStringProcessor instance
    """
    return AcceleratedStringProcessor()


def is_rust_available() -> bool:
    """Check if Rust extensions are available.

    Returns:
        True if Rust extensions are loaded, False otherwise
    """
    return RUST_AVAILABLE


__all__ = [
    "RUST_AVAILABLE",
    "AcceleratedLogProcessor",
    "AcceleratedPathHandler",
    "AcceleratedStringProcessor",
    "RustPerformanceMonitor",
    "get_accelerated_log_processor",
    "get_accelerated_path_handler",
    "get_accelerated_string_processor",
    "is_rust_available",
]
