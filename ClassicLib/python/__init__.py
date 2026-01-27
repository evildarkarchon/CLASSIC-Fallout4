"""Backward compatibility module for python.

This package has been moved to ClassicLib.integration.python.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.integration.python instead.
"""

import warnings

warnings.warn(
    "ClassicLib.python is deprecated, import from ClassicLib.integration.python instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.integration.python import *  # noqa: F403, E402
