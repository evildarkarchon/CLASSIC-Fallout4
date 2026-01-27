"""Backward compatibility module for MessageHandler.core.

This package has been moved to ClassicLib.messaging.core.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.messaging.core instead.
"""

import warnings

warnings.warn(
    "ClassicLib.MessageHandler.core is deprecated, import from ClassicLib.messaging.core instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.messaging.core import *  # noqa: F403, E402
