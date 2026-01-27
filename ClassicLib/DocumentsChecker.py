"""Backward compatibility module for DocumentsChecker.

This module has been moved to ClassicLib.support.documents.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.documents instead.
"""

import warnings

warnings.warn(
    "ClassicLib.DocumentsChecker is deprecated, import from ClassicLib.support.documents instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.documents import *  # noqa: F403, E402
