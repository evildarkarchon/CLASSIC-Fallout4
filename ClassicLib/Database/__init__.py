"""Backward compatibility module for Database.

This package has been moved to ClassicLib.io.database.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.io.database instead.
"""

import warnings

warnings.warn(
    "ClassicLib.Database is deprecated, import from ClassicLib.io.database instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.io.database import *  # noqa: F403, E402
