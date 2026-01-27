"""Backward compatibility module for XseCheck.

This module has been moved to ClassicLib.support.xse.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.xse instead.
"""

import warnings

warnings.warn(
    "ClassicLib.XseCheck is deprecated, import from ClassicLib.support.xse instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.xse import *  # noqa: F403, E402
