"""Backward compatibility module for ScanLog.scanloginfo.

This package has been moved to ClassicLib.scanning.logs.scanloginfo.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.logs.scanloginfo instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanLog.scanloginfo is deprecated, import from ClassicLib.scanning.logs.scanloginfo instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.logs.scanloginfo import *  # noqa: F403, E402
