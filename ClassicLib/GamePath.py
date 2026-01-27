"""Backward compatibility module for GamePath.

This module has been moved to ClassicLib.support.game_path.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.game_path instead.
"""

import warnings

warnings.warn(
    "ClassicLib.GamePath is deprecated, import from ClassicLib.support.game_path instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.game_path import *  # noqa: F403, E402
