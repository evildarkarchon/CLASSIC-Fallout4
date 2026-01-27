"""Backward compatibility module for AsyncBridge.

This module has been moved to ClassicLib.core.async_bridge.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.async_bridge instead.
"""

import warnings

warnings.warn(
    "ClassicLib.AsyncBridge is deprecated, import from ClassicLib.core.async_bridge instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.async_bridge import *  # noqa: F403, E402
from ClassicLib.core.async_bridge import AsyncBridge  # noqa: F401, E402
