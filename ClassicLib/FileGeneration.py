"""Backward compatibility module for FileGeneration.

This module has been moved to ClassicLib.support.file_gen.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.file_gen instead.
"""

import warnings

warnings.warn(
    "ClassicLib.FileGeneration is deprecated, import from ClassicLib.support.file_gen instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.file_gen import *  # noqa: F403, E402
