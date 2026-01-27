"""Backward compatibility module for BackupManager.

This module has been moved to ClassicLib.support.backup.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.backup instead.
"""

import warnings

warnings.warn(
    "ClassicLib.BackupManager is deprecated, import from ClassicLib.support.backup instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.backup import *  # noqa: F403, E402
