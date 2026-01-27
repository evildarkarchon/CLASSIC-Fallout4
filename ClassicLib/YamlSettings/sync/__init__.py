"""Backward compatibility module for YamlSettings.sync.

This package has been moved to ClassicLib.io.yaml.sync.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.io.yaml.sync instead.
"""

import warnings

warnings.warn(
    "ClassicLib.YamlSettings.sync is deprecated, import from ClassicLib.io.yaml.sync instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.io.yaml.sync import *  # noqa: F403, E402
