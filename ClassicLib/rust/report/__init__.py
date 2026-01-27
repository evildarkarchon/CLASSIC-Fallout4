"""Backward compatibility module for rust.report.

This package has been moved to ClassicLib.integration.rust.report.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.integration.rust.report instead.
"""

import warnings

warnings.warn(
    "ClassicLib.rust.report is deprecated, import from ClassicLib.integration.rust.report instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.integration.rust.report import *  # noqa: F403, E402
