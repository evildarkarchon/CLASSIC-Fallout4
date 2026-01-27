"""Backward compatibility module for ScanGame.models.

This package has been moved to ClassicLib.scanning.game.models.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.game.models instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanGame.models is deprecated, import from ClassicLib.scanning.game.models instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.game.models import *  # noqa: F403, E402
