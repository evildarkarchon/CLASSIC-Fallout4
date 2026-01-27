"""Backward compatibility module for GlobalRegistry.

This module has been moved to ClassicLib.core.registry.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.registry instead.
"""

import warnings

warnings.warn(
    "ClassicLib.GlobalRegistry is deprecated, import from ClassicLib.core.registry instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.registry import *  # noqa: F403, E402
