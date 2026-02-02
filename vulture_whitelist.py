"""Vulture whitelist -- verified false positives for dead code detection.

Each entry references a name that vulture cannot detect as used because it is
invoked dynamically (Qt signals, pytest discovery, PyO3 C-level imports, etc.)
or is inside a TYPE_CHECKING block used only for string annotations.
"""

# --- TYPE_CHECKING imports (used in string annotations, invisible to vulture) ---

# ClassicLib/integration/rust/report/generator.py:42
# Used in cast("PyReportGenerator", ...) on line 174
PyReportGenerator  # noqa: F821

# ClassicLib/scanning/game/check_xse_plugins.py:13
# Used in return type annotations: KeysView[str], ValuesView[...]
KeysView  # noqa: F821
ValuesView  # noqa: F821

# ClassicLib/scanning/logs/executor.py:19
# Used in cast("ScanLogsExecutorType", self) on line 319
ScanLogsExecutorType  # noqa: F821

# --- PySide6 Qt stub parameters (must match Qt API signature) ---

# ClassicLib/messaging/qt_compat.py:81-84
# QProgressDialog.__init__ stub parameters matching PySide6 API
labelText  # noqa: F821
cancelButtonText  # noqa: F821
minimum  # noqa: F821
maximum  # noqa: F821
