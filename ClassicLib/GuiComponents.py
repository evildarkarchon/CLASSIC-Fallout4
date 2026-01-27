"""Backward compatibility module for GuiComponents.

This module has been moved to ClassicLib.support.gui_components.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.gui_components instead.
"""

import warnings

warnings.warn(
    "ClassicLib.GuiComponents is deprecated, import from ClassicLib.support.gui_components instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.gui_components import *  # noqa: F403, E402
