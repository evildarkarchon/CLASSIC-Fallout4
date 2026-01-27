"""Backward compatibility module for MessageHandler.progress.

This package has been moved to ClassicLib.messaging.progress.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.messaging.progress instead.
"""

import warnings

warnings.warn(
    "ClassicLib.MessageHandler.progress is deprecated, import from ClassicLib.messaging.progress instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.messaging.progress import *  # noqa: F403, E402
