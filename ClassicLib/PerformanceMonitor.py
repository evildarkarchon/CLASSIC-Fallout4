"""Backward compatibility module for PerformanceMonitor.

This module has been moved to ClassicLib.core.performance.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.performance instead.
"""

import warnings

warnings.warn(
    "ClassicLib.PerformanceMonitor is deprecated, import from ClassicLib.core.performance instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.performance import *  # noqa: F403, E402
