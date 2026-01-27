"""Backward compatibility module for ScanGame.core.

This package has been moved to ClassicLib.scanning.game.checks.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.game.checks instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanGame.core is deprecated, import from ClassicLib.scanning.game.checks instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.game.checks import *  # noqa: F403, E402
