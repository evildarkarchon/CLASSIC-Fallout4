"""Backward compatibility module for Logger.

This module has been moved to ClassicLib.core.logger.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.logger instead.
"""

import warnings

warnings.warn(
    "ClassicLib.Logger is deprecated, import from ClassicLib.core.logger instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.logger import *  # noqa: F403, E402
