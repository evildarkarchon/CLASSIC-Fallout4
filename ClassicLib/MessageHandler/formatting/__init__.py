"""Backward compatibility module for MessageHandler.formatting.

This package has been moved to ClassicLib.messaging.formatting.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.messaging.formatting instead.
"""

import warnings

warnings.warn(
    "ClassicLib.MessageHandler.formatting is deprecated, import from ClassicLib.messaging.formatting instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.messaging.formatting import *  # noqa: F403, E402
