"""Backward compatibility module for YamlSettings.

This package has been moved to ClassicLib.io.yaml.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.io.yaml instead.
"""

import warnings

warnings.warn(
    "ClassicLib.YamlSettings is deprecated, import from ClassicLib.io.yaml instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.io.yaml import *  # noqa: F403, E402
