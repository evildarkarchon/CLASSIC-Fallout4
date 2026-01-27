"""Backward compatibility module for DocsPath.

This module has been moved to ClassicLib.support.docs_path.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.docs_path instead.
"""

import warnings

warnings.warn(
    "ClassicLib.DocsPath is deprecated, import from ClassicLib.support.docs_path instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.docs_path import *  # noqa: F403, E402
