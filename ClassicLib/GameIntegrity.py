"""Backward compatibility module for GameIntegrity.

This module has been moved to ClassicLib.support.integrity.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.integrity instead.
"""

import warnings

warnings.warn(
    "ClassicLib.GameIntegrity is deprecated, import from ClassicLib.support.integrity instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.integrity import *  # noqa: F403, E402
