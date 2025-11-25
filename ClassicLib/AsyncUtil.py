"""
DEPRECATED: Use ClassicLib.FileIO.Async instead.
"""

import warnings

from ClassicLib.FileIO.Async import (
    detect_encoding_async,
    fallback_to_sync_encoding_detection,
    get_encoding_detection_available,
    open_file_with_encoding_async,
    read_file_with_encoding_async,
    read_lines_with_encoding_async,
)

warnings.warn(
    "ClassicLib.AsyncUtil is deprecated. Use ClassicLib.FileIO.Async instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "detect_encoding_async",
    "open_file_with_encoding_async",
    "read_file_with_encoding_async",
    "read_lines_with_encoding_async",
    "get_encoding_detection_available",
    "fallback_to_sync_encoding_detection",
]