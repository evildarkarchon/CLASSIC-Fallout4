"""Backward compatibility module for ScanLog.models.

This package has been moved to ClassicLib.scanning.logs.models.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.logs.models instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanLog.models is deprecated, import from ClassicLib.scanning.logs.models instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.logs.models import *  # noqa: F403, E402
