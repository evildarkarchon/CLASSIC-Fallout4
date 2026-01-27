"""Backward compatibility module for RustAcceleration.

This package has been moved to ClassicLib.acceleration.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.acceleration instead.
"""

import warnings

warnings.warn(
    "ClassicLib.RustAcceleration is deprecated, import from ClassicLib.acceleration instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.acceleration import *  # noqa: F403, E402
