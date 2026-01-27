"""Backward compatibility module for ResourceLoader.

This module has been moved to ClassicLib.support.resources.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.resources instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ResourceLoader is deprecated, import from ClassicLib.support.resources instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.resources import *  # noqa: F403, E402
