"""Backward compatibility module for MessageHandler.output.

This package has been moved to ClassicLib.messaging.backends.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.messaging.backends instead.
"""

import warnings

warnings.warn(
    "ClassicLib.MessageHandler.output is deprecated, import from ClassicLib.messaging.backends instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.messaging.backends import *  # noqa: F403, E402
