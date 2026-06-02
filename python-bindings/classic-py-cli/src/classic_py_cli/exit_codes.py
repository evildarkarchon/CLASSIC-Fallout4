"""Stable process exit status values for the CLASSIC Python CLI."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process statuses promised by the Python CLI output contract."""

    SUCCESS = 0
    PRODUCT_FAILURE = 1
    USAGE = 2
    BINDING_IMPORT = 3
    INTERRUPTED = 4


def worst_exit_code(codes: list[int]) -> int:
    """Return the highest-priority non-success status from a list of results."""

    for code in (ExitCode.BINDING_IMPORT, ExitCode.USAGE, ExitCode.INTERRUPTED, ExitCode.PRODUCT_FAILURE):
        if int(code) in codes:
            return int(code)
    return int(ExitCode.SUCCESS)
