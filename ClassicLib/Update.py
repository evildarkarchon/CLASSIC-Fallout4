"""Backward compatibility module for Update.

This module has been moved to ClassicLib.support.update.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.update instead.
"""

import warnings

warnings.warn(
    "ClassicLib.Update is deprecated, import from ClassicLib.support.update instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.update import *  # noqa: F403, E402
