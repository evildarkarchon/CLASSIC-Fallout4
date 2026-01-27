"""Backward compatibility module for YamlSettings.async_.

This package has been moved to ClassicLib.io.yaml.async_.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.io.yaml.async_ instead.
"""

import warnings

warnings.warn(
    "ClassicLib.YamlSettings.async_ is deprecated, import from ClassicLib.io.yaml.async_ instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.io.yaml.async_ import *  # noqa: F403, E402
