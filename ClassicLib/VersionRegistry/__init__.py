"""Backward compatibility module for VersionRegistry.

This package has been moved to ClassicLib.support.versions.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.support.versions instead.
"""

import warnings

warnings.warn(
    "ClassicLib.VersionRegistry is deprecated, import from ClassicLib.support.versions instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.support.versions import *  # noqa: F403, E402, I001
from ClassicLib.support.versions import (  # noqa: E402
    AddressLibraryConfig as AddressLibraryConfig,
    CompatibleRange as CompatibleRange,
    CrashgenConfig as CrashgenConfig,
    CrashgenVersionResult as CrashgenVersionResult,
    CrashgenVersionStatus as CrashgenVersionStatus,
    MatchConfidence as MatchConfidence,
    MatchResult as MatchResult,
    UnknownVersionHandling as UnknownVersionHandling,
    VersionInfo as VersionInfo,
    VersionMatcher as VersionMatcher,
    VersionRegistry as VersionRegistry,
    XseConfig as XseConfig,
    check_crashgen_version as check_crashgen_version,
    check_crashgen_version_for_detected_game as check_crashgen_version_for_detected_game,
    get_detected_version_info as get_detected_version_info,
    get_matching_crashgen_config as get_matching_crashgen_config,
    get_version_registry as get_version_registry,
)
