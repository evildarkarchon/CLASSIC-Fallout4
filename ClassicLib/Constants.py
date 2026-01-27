"""Backward compatibility module for Constants.

This module has been moved to ClassicLib.core.constants.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.constants instead.
"""

import warnings

warnings.warn(
    "ClassicLib.Constants is deprecated, import from ClassicLib.core.constants instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.constants import *  # noqa: F403, E402
