"""Backward compatibility module for ScanLog.composition.

This package has been moved to ClassicLib.scanning.logs.reporting.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.logs.reporting instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanLog.composition is deprecated, import from ClassicLib.scanning.logs.reporting instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.logs.reporting import ConditionalSection, ReportComposer  # noqa: F401, E402
