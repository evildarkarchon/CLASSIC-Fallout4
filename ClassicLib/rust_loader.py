"""Backward compatibility module for rust_loader.

This module has been moved to ClassicLib.core.rust_loader.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.core.rust_loader instead.
"""

import warnings

warnings.warn(
    "ClassicLib.rust_loader is deprecated, import from ClassicLib.core.rust_loader instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.core.rust_loader import *  # noqa: F403, E402
