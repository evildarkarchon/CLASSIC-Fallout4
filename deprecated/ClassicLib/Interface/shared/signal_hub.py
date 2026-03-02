"""Central signal hub for inter-component communication in CLASSIC interface.

This module provides a SignalHub class that acts as a centralized Qt signal
routing system, enabling decoupled communication between UI controllers
without direct method calls or dependencies.

Example:
    >>> from ClassicLib.Interface.signal_hub import SignalHub
    >>> hub = SignalHub(parent_widget)
    >>> # Controller A connects to signals
    >>> hub.scan_completed.connect(on_scan_done)
    >>> # Controller B emits signals
    >>> hub.scan_completed.emit("crash_logs")

"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal


class SignalHub(QObject):
    """Central hub for inter-component Qt signal communication.

    SignalHub provides a decoupled communication mechanism between UI controllers.
    Instead of controllers calling methods on each other directly, they emit
    signals through the hub, and interested controllers connect to those signals.

    This pattern enables:
    - Loose coupling between components
    - Independent testing of controllers
    - Easy addition of new signal consumers
    - Clear documentation of inter-component events

    Attributes:
        scan_started: Emitted when a scan begins. Payload is scan_type string.
        scan_completed: Emitted when a scan finishes. Payload is scan_type string.
        scan_failed: Emitted on scan error. Payload is (scan_type, error_message).

    Example:
        >>> hub = SignalHub(main_window)
        >>> hub.scan_started.connect(lambda t: print(f"Scan started: {t}"))
        >>> hub.scan_started.emit("crash_logs")
        Scan started: crash_logs

    """

    # =========================================================================
    # Scan Lifecycle Signals
    # =========================================================================

    scan_started = Signal(str)
    """Emitted when a scan operation begins.

    Args:
        scan_type (str): Type of scan - "crash_logs" or "game_files"
    """

    scan_completed = Signal(str)
    """Emitted when a scan operation completes successfully.

    Args:
        scan_type (str): Type of scan that completed
    """

    scan_failed = Signal(str, str)
    """Emitted when a scan operation fails.

    Args:
        scan_type (str): Type of scan that failed
        error_message (str): Description of the error
    """

    # =========================================================================
    # File Watching Control Signals (ScanController -> ResultsViewer)
    # =========================================================================

    pause_file_watching = Signal()
    """Emitted to pause file system watching during scans.

    This prevents I/O bottlenecks where each new report triggers a directory
    change event that reads ALL existing reports.
    """

    resume_file_watching = Signal()
    """Emitted to resume file system watching after scan completion.

    The consumer should trigger a single refresh after resuming to show
    all new reports created during the scan.
    """

    # =========================================================================
    # Reports Management Signals
    # =========================================================================

    refresh_reports_requested = Signal()
    """Emitted to request a refresh of the reports list.

    Used by:
    - ScanController: After scan completion
    - WindowGeometryManager: When switching to results tab
    """

    report_loaded = Signal(Path)
    """Emitted when a report is successfully loaded.

    Args:
        report_path (Path): Path to the loaded report file
    """

    reports_count_changed = Signal(int)
    """Emitted when the number of available reports changes.

    Args:
        count (int): New total number of reports
    """

    # =========================================================================
    # Papyrus Monitoring Signals (ScanController <-> PapyrusManager)
    # =========================================================================

    start_papyrus_monitoring = Signal()
    """Emitted to request Papyrus monitoring to start.

    Used by ScanController after game_files_scan completes if the
    papyrus button is checked.
    """

    stop_papyrus_monitoring = Signal()
    """Emitted to request Papyrus monitoring to stop.

    Used by ScanController after game_files_scan completes if the
    papyrus button is not checked.
    """

    papyrus_stats_updated = Signal(object)
    """Emitted when Papyrus monitoring stats are updated.

    Args:
        stats (PapyrusStats): Updated statistics object
    """

    papyrus_monitoring_state_changed = Signal(bool)
    """Emitted when Papyrus monitoring state changes.

    Args:
        is_monitoring (bool): True if monitoring is active, False otherwise
    """

    # =========================================================================
    # UI State Signals
    # =========================================================================

    tab_changed = Signal(int)
    """Emitted when the active tab changes.

    Args:
        tab_index (int): Index of the newly active tab
    """

    scan_buttons_enable = Signal(bool)
    """Emitted to enable/disable scan buttons.

    Args:
        enabled (bool): True to enable buttons, False to disable
    """

    papyrus_button_style_update = Signal(bool)
    """Emitted to update Papyrus button styling.

    Args:
        is_monitoring (bool): True for "stop" style, False for "start" style
    """

    # =========================================================================
    # Update Manager Signals
    # =========================================================================

    update_check_started = Signal()
    """Emitted when an update check begins."""

    update_check_completed = Signal(bool)
    """Emitted when an update check completes.

    Args:
        is_up_to_date (bool): True if current version is latest
    """

    update_check_failed = Signal(str)
    """Emitted when an update check fails.

    Args:
        error_message (str): Description of the error
    """

    # =========================================================================
    # Error Dialog Signals
    # =========================================================================

    show_error_dialog = Signal(str, str, str)
    """Emitted to show an error dialog.

    Args:
        title (str): Dialog title
        message (str): Main error message
        details (str): Detailed error information (e.g., traceback)
    """

    # =========================================================================
    # Settings Signals
    # =========================================================================

    settings_changed = Signal()
    """Emitted when settings have been changed via the settings dialog.

    Used to notify components that may need to refresh their state based
    on updated configuration.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize the SignalHub.

        Args:
            parent: Optional parent QObject for Qt memory management.

        """
        super().__init__(parent)
