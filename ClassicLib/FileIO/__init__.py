"""Backward compatibility module for FileIO.

This package has been moved to ClassicLib.io.files.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.io.files instead.
"""

import warnings

warnings.warn(
    "ClassicLib.FileIO is deprecated, import from ClassicLib.io.files instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.io.files import *  # noqa: F403, E402, I001
from ClassicLib.io.files import (  # noqa: E402
    FileIOCore as FileIOCore,
    append_file_sync as append_file_sync,
    cached_path_conversion as cached_path_conversion,
    ensure_path as ensure_path,
    read_bytes_sync as read_bytes_sync,
    read_crash_log_sync as read_crash_log_sync,
    read_file_sync as read_file_sync,
    read_lines_sync as read_lines_sync,
    stream_lines_sync as stream_lines_sync,
    write_bytes_sync as write_bytes_sync,
    write_crash_report_sync as write_crash_report_sync,
    write_file_sync as write_file_sync,
    write_lines_sync as write_lines_sync,
)
