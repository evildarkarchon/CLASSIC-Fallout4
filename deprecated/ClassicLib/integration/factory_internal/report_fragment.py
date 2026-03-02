"""Lazy report fragment import helper for integration factory wrappers."""

from __future__ import annotations

_report_fragment_type: type | None = None


def get_report_fragment_type() -> type:
    """Lazily import ReportFragment to avoid circular imports."""
    global _report_fragment_type  # noqa: PLW0603
    if _report_fragment_type is None:
        from ClassicLib.scanning.logs.reporting import ReportFragment

        _report_fragment_type = ReportFragment
    return _report_fragment_type
