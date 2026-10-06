"""Python module for file I/O operations
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_file_io import (
    DDSAnalyzer,
    DDSHeader,
    EncodingDetector,
    FileGenerator,
    FileGeneratorConfig,
    FileHasher,
    FileIOCore,
    PyLineStreamer,
    PyLogCollector,
    PySyncLineStreamer,
    RustFileIOError,
    RustFileIOIOError,
    RustFileIOParseError,
    __debug_registered__,
    __version__,
    calculate_similarity,
    generate_ignore_file_async,
    generate_local_yaml_async,
    similarity_ratio,
)

__all__ = [
    "DDSAnalyzer",
    "DDSHeader",
    "EncodingDetector",
    "FileGenerator",
    "FileGeneratorConfig",
    "FileHasher",
    "FileIOCore",
    "PyLineStreamer",
    "PyLogCollector",
    "PySyncLineStreamer",
    "RustFileIOError",
    "RustFileIOIOError",
    "RustFileIOParseError",
    "__debug_registered__",
    "__version__",
    "calculate_similarity",
    "generate_ignore_file_async",
    "generate_local_yaml_async",
    "similarity_ratio",
]
