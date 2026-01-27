"""Backward compatibility module for PathValidator.

This module has been moved to ClassicLib.support.path_validator.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.path_validator instead.
"""

import warnings

warnings.warn(
    "ClassicLib.PathValidator is deprecated, import from ClassicLib.support.path_validator instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.path_validator import *  # noqa: F403, E402
