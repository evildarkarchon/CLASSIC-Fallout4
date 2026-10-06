"""Version detection and parsing utilities for CLASSIC
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_version import (
    __version__,
    compare_versions,
    extract_all_versions,
    extract_pe_version,
    extract_version_from_filename,
    extract_version_from_log,
    format_version,
    is_known_f4se_version,
    is_known_fallout4_version,
    is_valid_pe_path,
    parse_version,
    try_parse_version,
)

__all__ = [
    "__version__",
    "compare_versions",
    "extract_all_versions",
    "extract_pe_version",
    "extract_version_from_filename",
    "extract_version_from_log",
    "format_version",
    "is_known_f4se_version",
    "is_known_fallout4_version",
    "is_valid_pe_path",
    "parse_version",
    "try_parse_version",
]
