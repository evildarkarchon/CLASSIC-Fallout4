"""Backward compatibility module for SetupCoordinator.

This module has been moved to ClassicLib.support.setup.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.setup instead.
"""

import warnings

warnings.warn(
    "ClassicLib.SetupCoordinator is deprecated, import from ClassicLib.support.setup instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.setup import *  # noqa: F403, E402
