"""Script Extender (XSE) utilities for CLASSIC
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_xse import (
    XseInfo,
    XseType,
    __version__,
    detect_xse_version,
    get_xse_info,
    is_xse_installed,
    parse_xse_type,
    resolve_xse_log_for_scan,
)

__all__ = [
    "XseInfo",
    "XseType",
    "__version__",
    "detect_xse_version",
    "get_xse_info",
    "is_xse_installed",
    "parse_xse_type",
    "resolve_xse_log_for_scan",
]
