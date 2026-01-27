"""Backward compatibility module for PapyrusLog.

This module has been moved to ClassicLib.support.papyrus.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.papyrus instead.
"""

import warnings

warnings.warn(
    "ClassicLib.PapyrusLog is deprecated, import from ClassicLib.support.papyrus instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.papyrus import *  # noqa: F403, E402
