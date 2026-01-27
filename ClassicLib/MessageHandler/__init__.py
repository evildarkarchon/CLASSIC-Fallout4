"""Backward compatibility module for MessageHandler.

This package has been moved to ClassicLib.messaging.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.messaging instead.
"""

import warnings

warnings.warn(
    "ClassicLib.MessageHandler is deprecated, import from ClassicLib.messaging instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.messaging import *  # noqa: F403, E402
