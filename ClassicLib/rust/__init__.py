"""Backward compatibility module for rust.

This package has been moved to ClassicLib.integration.rust.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.integration.rust instead.
"""

import warnings

warnings.warn(
    "ClassicLib.rust is deprecated, import from ClassicLib.integration.rust instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.integration.rust import *  # noqa: F403, E402
