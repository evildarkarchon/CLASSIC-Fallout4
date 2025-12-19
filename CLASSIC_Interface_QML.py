"""QML-based graphical user interface for CLASSIC Fallout 4 crash log analyzer.

This module provides the Qt/QML backend implementation for CLASSIC, including:
- ClassicBackend: Main QObject exposing properties and slots to QML
- ScanWorker: Background worker for crash log and game file scanning
- PapyrusWorker: Real-time Papyrus script log monitoring
"""

import asyncio
import sys
from operator import itemgetter
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

# Add project root to path
sys.path.append(str(Path(Path(__file__).resolve()).parent))

from ClassicLib import GlobalRegistry
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.PapyrusLog import papyrus_logging
from ClassicLib.ScanGame import manage_game_files, write_combined_results_async
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettings import classic_settings, yaml_settings


class ScanWorker(QObject):
    """Worker thread for executing scan operations in the background.

    This worker runs crash log or game file scans in a separate QThread
    to prevent blocking the main UI thread. It communicates results and
    errors back to the main thread via Qt signals.

    Attributes:
        finished: Signal emitted when the scan completes successfully.
        error: Signal emitted when the scan fails, carrying title, message,
            and details strings.
        scan_type: The type of scan to perform ("crashlogs" or "gamefiles").

    """

    finished = Signal()
    error = Signal(str, str, str)

    def __init__(self, scan_type: str) -> None:
        """Initialize the scan worker with the specified scan type.

        Args:
            scan_type: The type of scan to perform. Valid values are
                "crashlogs" for crash log analysis or "gamefiles" for
                game file integrity scanning.

        """
        super().__init__()
        self.scan_type = scan_type

    @Slot()
    def run(self) -> None:
        """Execute the scan operation.

        Runs the appropriate scan based on the configured scan_type.
        Emits the finished signal on success or the error signal on failure.
        This method is intended to be called from a QThread.

        Note:
            Uses asyncio.run() directly since we're in a QThread worker.
            AsyncBridge is designed for the main Qt thread and creates
            threading conflicts when used from QThread workers (it spawns
            a plain Python thread which can't use Qt timers).

        """
        try:
            if self.scan_type == "crashlogs":
                executor = ScanLogsExecutor()
                # Use asyncio.run() directly - we're in a QThread worker
                asyncio.run(executor.execute_scan())
            elif self.scan_type == "gamefiles":
                # Use asyncio.run() directly - we're in a QThread worker
                asyncio.run(write_combined_results_async())

            self.finished.emit()
        except Exception as e:  # noqa: BLE001
            self.error.emit("Scan Failed", str(e), "")
            logger.error(f"Scan failed: {e}")


class PapyrusWorker(QObject):
    """Worker thread for continuous Papyrus log monitoring.

    This worker monitors Papyrus script logs in real-time, parsing statistics
    about script dumps, stacks, warnings, and errors. It runs in a loop,
    updating statistics every second until stopped.

    Attributes:
        statsUpdated: Signal emitted with updated statistics (dumps, stacks,
            ratio, warnings, errors).
        error: Signal emitted when an error occurs during monitoring.

    """

    statsUpdated = Signal(int, int, float, int, int)  # dumps, stacks, ratio, warns, errors
    error = Signal(str)

    def __init__(self) -> None:
        """Initialize the Papyrus monitoring worker."""
        super().__init__()
        self._should_run = True

    @Slot()
    def run(self) -> None:
        """Execute the continuous monitoring loop.

        Polls Papyrus log statistics every second and emits the statsUpdated
        signal with current values. The loop continues until stop() is called
        or an error occurs.
        """
        while self._should_run:
            try:
                message, count = papyrus_logging()
                stats = self._parse_stats(message, count)
                self.statsUpdated.emit(*stats)
                QThread.msleep(1000)
            except Exception as e:  # noqa: BLE001
                self.error.emit(str(e))
                break

    def stop(self) -> None:
        """Signal the monitoring loop to stop.

        Sets the internal flag that causes the run() loop to exit on its
        next iteration.
        """
        self._should_run = False

    @staticmethod
    def _parse_stats(message: str, dump_count: int) -> tuple[int, int, float, int, int]:
        """Parse Papyrus log statistics from the output message.

        Args:
            message: Raw output from the papyrus_logging function containing
                statistics in "key: value" format.
            dump_count: The number of script dumps detected.

        Returns:
            A tuple containing (dump_count, stacks, ratio, warnings, errors)
            where ratio is dumps/stacks or 0 if stacks is 0.

        """
        stacks = 0
        warnings = 0
        errors = 0
        for line in message.splitlines():
            if ": " in line:
                key, value = line.split(": ")
                key = key.strip().lower()
                if key == "number of stacks":
                    stacks = int(value)
                elif key == "number of warnings":
                    warnings = int(value)
                elif key == "number of errors":
                    errors = int(value)

        ratio = 0.0 if dump_count == 0 else dump_count / stacks if stacks > 0 else 0
        return dump_count, stacks, ratio, warnings, errors


class ClassicBackend(QObject):
    """Backend controller for the QML-based CLASSIC GUI.

    This class serves as the bridge between the QML frontend and the Python
    backend, exposing properties, signals, and slots that QML can bind to
    and invoke. It manages application settings, scan operations, Papyrus
    monitoring, and report management.

    Attributes:
        scanFinished: Signal emitted when a scan operation completes.
        scanError: Signal emitted on scan error with (title, message).
        papyrusStatsUpdated: Signal with Papyrus stats (dumps, stacks, ratio,
            warnings, errors).
        reportsUpdated: Signal emitted when the reports list changes.
        stagingModsPath: Path to the mod staging folder.
        customScanPath: Custom path for crash log scanning.
        vrMode: Whether VR mode is enabled.
        fcxMode: Whether FCX (Fallout Custom xEdit) mode is enabled.
        simplifyLogs: Whether to simplify crash log output.
        showFidValues: Whether to show FormID values in reports.
        moveInvalidLogs: Whether to move unsolved logs to a separate folder.
        updateCheck: Whether to check for application updates.
        iniPath: Custom path for INI configuration files.
        papyrusMonitoring: Whether Papyrus log monitoring is active.

    """

    # Signals
    scanFinished = Signal()
    scanError = Signal(str, str)  # title, message
    papyrusStatsUpdated = Signal(int, int, float, int, int)  # dumps, stacks, ratio, warns, errors
    reportsUpdated = Signal()

    # Property Notify Signals
    stagingModsPathChanged = Signal()
    customScanPathChanged = Signal()
    vrModeChanged = Signal()
    fcxModeChanged = Signal()
    simplifyLogsChanged = Signal()
    showFidValuesChanged = Signal()
    moveInvalidLogsChanged = Signal()
    updateCheckChanged = Signal()
    iniPathChanged = Signal()
    papyrusMonitoringChanged = Signal()

    def __init__(self) -> None:
        """Initialize the CLASSIC backend with settings from configuration.

        Loads all user settings from the YAML configuration cache and
        initializes internal state for thread management.
        """
        super().__init__()
        self._staging_mods_path = classic_settings(str, "MODS Folder Path") or ""
        self._custom_scan_path = classic_settings(str, "SCAN Custom Path") or ""
        self._papyrus_monitoring = False
        self._papyrus_thread = None
        self._papyrus_worker = None
        self._scan_thread = None

        # Settings cache
        self._vr_mode = classic_settings(bool, "VR Mode")
        self._fcx_mode = classic_settings(bool, "FCX Mode")
        self._simplify_logs = classic_settings(bool, "Simplify Logs")
        self._show_fid_values = classic_settings(bool, "Show FormID Values")
        self._move_invalid_logs = classic_settings(bool, "Move Unsolved Logs")
        self._update_check = classic_settings(bool, "Update Check")
        self._ini_path = classic_settings(str, "INI Folder Path") or ""

    # Properties
    @Property(str, notify=stagingModsPathChanged)
    def stagingModsPath(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get the path to the mod staging folder."""
        return self._staging_mods_path

    @stagingModsPath.setter
    def stagingModsPath(self, val: str) -> None:
        if self._staging_mods_path != val:
            self._staging_mods_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", val)
            self.stagingModsPathChanged.emit()

    @Property(str, notify=customScanPathChanged)
    def customScanPath(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get the custom scan path."""
        return self._custom_scan_path

    @customScanPath.setter
    def customScanPath(self, val: str) -> None:
        if self._custom_scan_path != val:
            self._custom_scan_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", val)
            self.customScanPathChanged.emit()

    @Property(bool, notify=vrModeChanged)
    def vrMode(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get VR mode enabled status."""
        return self._vr_mode or False

    @vrMode.setter
    def vrMode(self, val: bool) -> None:
        if self._vr_mode != val:
            self._vr_mode = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", val)
            self.vrModeChanged.emit()

    @Property(bool, notify=fcxModeChanged)
    def fcxMode(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get FCX mode enabled status."""
        return self._fcx_mode or False

    @fcxMode.setter
    def fcxMode(self, val: bool) -> None:
        if self._fcx_mode != val:
            self._fcx_mode = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", val)
            self.fcxModeChanged.emit()

    @Property(bool, notify=simplifyLogsChanged)
    def simplifyLogs(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get simplify logs setting."""
        return self._simplify_logs or False

    @simplifyLogs.setter
    def simplifyLogs(self, val: bool) -> None:
        if self._simplify_logs != val:
            self._simplify_logs = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", val)
            self.simplifyLogsChanged.emit()

    @Property(bool, notify=showFidValuesChanged)
    def showFidValues(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get show FormID values setting."""
        return self._show_fid_values or False

    @showFidValues.setter
    def showFidValues(self, val: bool) -> None:
        if self._show_fid_values != val:
            self._show_fid_values = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values", val)
            self.showFidValuesChanged.emit()

    @Property(bool, notify=moveInvalidLogsChanged)
    def moveInvalidLogs(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get move invalid logs setting."""
        return self._move_invalid_logs or False

    @moveInvalidLogs.setter
    def moveInvalidLogs(self, val: bool) -> None:
        if self._move_invalid_logs != val:
            self._move_invalid_logs = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", val)  # YAML key differs slightly
            self.moveInvalidLogsChanged.emit()

    @Property(bool, notify=updateCheckChanged)
    def updateCheck(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get update check setting."""
        return self._update_check or False

    @updateCheck.setter
    def updateCheck(self, val: bool) -> None:
        if self._update_check != val:
            self._update_check = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Update Check", val)
            self.updateCheckChanged.emit()

    @Property(str, notify=iniPathChanged)
    def iniPath(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get the INI folder path."""
        return self._ini_path

    @iniPath.setter
    def iniPath(self, val: str) -> None:
        if self._ini_path != val:
            self._ini_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", val)
            self.iniPathChanged.emit()

    @Property(bool, notify=papyrusMonitoringChanged)
    def papyrusMonitoring(self):  # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        """Get papyrus monitoring status."""
        return self._papyrus_monitoring

    @papyrusMonitoring.setter
    def papyrusMonitoring(self, val: bool) -> None:
        if self._papyrus_monitoring != val:
            self._papyrus_monitoring = val
            self.papyrusMonitoringChanged.emit()

    # Methods
    @Slot()
    def scanCrashLogs(self) -> None:
        """Start a crash log scan in a background thread.

        Creates a ScanWorker in a separate QThread to analyze crash logs
        without blocking the UI. Does nothing if a scan is already running.
        Emits scanFinished when complete or scanError on failure.
        """
        if self._scan_thread and self._scan_thread.isRunning():
            return

        self._scan_thread = QThread()
        self._worker = ScanWorker("crashlogs")
        self._worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._scan_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self.scanError)

        self._scan_thread.start()

    @Slot()
    def scanGameFiles(self) -> None:
        """Start a game file integrity scan in a background thread.

        Creates a ScanWorker in a separate QThread to check game file
        integrity without blocking the UI. Does nothing if a scan is
        already running. Emits scanFinished when complete or scanError
        on failure.
        """
        if self._scan_thread and self._scan_thread.isRunning():
            return

        self._scan_thread = QThread()
        self._worker = ScanWorker("gamefiles")
        self._worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._scan_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self.scanError)

        self._scan_thread.start()

    def _on_scan_finished(self) -> None:
        """Handle scan completion by emitting signals and refreshing reports."""
        self.scanFinished.emit()
        self.refreshReports()  # Update reports list

    @Slot(str, str)
    def backupOperation(self, category: str, action: str) -> None:
        """Perform a backup operation on game files.

        Args:
            category: The type of files to backup. Valid values are "XSE",
                "RESHADE", "VULKAN", or "ENB".
            action: The operation to perform. Valid values are "BACKUP",
                "RESTORE", or "REMOVE".

        Note:
            Emits scanError signal if the operation fails.

        """
        # Map category to what BackupManager or manage_game_files expects
        # manage_game_files(selected_list, selected_mode)
        # selected_list format: "Backup TYPE"
        # selected_mode: "BACKUP", "RESTORE", "REMOVE"
        try:
            manage_game_files(f"Backup {category}", action)  # pyright: ignore[reportArgumentType]
            logger.info(f"Backup operation {action} {category} completed.")
        except Exception as e:  # noqa: BLE001
            self.scanError.emit("Backup Error", str(e))

    @Slot(str)
    def fetchPastebin(self, url_or_id: str) -> None:
        """Fetch and process a crash log from Pastebin.

        Downloads a crash log from Pastebin using either a full URL or
        just the paste ID, then processes it for analysis.

        Args:
            url_or_id: Either a full Pastebin URL or just the paste ID.

        Note:
            Emits scanFinished on success or scanError on failure.

        """
        from ClassicLib.Utils.web_utils import async_pastebin_fetch as pastebin_fetch_async

        async def do_fetch() -> None:
            await pastebin_fetch_async(url_or_id)

        bridge = AsyncBridge.get_instance()
        try:
            bridge.run_async(do_fetch())
            self.scanFinished.emit()  # Just to notify completion
        except Exception as e:  # noqa: BLE001
            self.scanError.emit("Pastebin Error", str(e))

    @Slot()
    def togglePapyrus(self) -> None:
        """Toggle Papyrus log monitoring on or off.

        Starts or stops the background Papyrus monitoring thread. When
        enabled, emits papyrusStatsUpdated signal every second with
        current script statistics.
        """
        # Use the property setter to ensure signal is emitted
        self._papyrus_monitoring = not self._papyrus_monitoring
        self.papyrusMonitoringChanged.emit()

        if self._papyrus_monitoring:
            # Start monitoring
            self._papyrus_thread = QThread()
            self._papyrus_worker = PapyrusWorker()
            self._papyrus_worker.moveToThread(self._papyrus_thread)

            self._papyrus_thread.started.connect(self._papyrus_worker.run)
            self._papyrus_worker.statsUpdated.connect(self.papyrusStatsUpdated)
            self._papyrus_worker.error.connect(lambda e: self.scanError.emit("Papyrus Error", e))
            self._papyrus_worker.finished.connect(self._papyrus_thread.quit)  # type: ignore[union-attr]  # Qt signal connection

            self._papyrus_thread.start()
        else:
            # Stop monitoring
            if self._papyrus_worker:
                self._papyrus_worker.stop()
            if self._papyrus_thread:
                self._papyrus_thread.quit()
                self._papyrus_thread.wait()
                self._papyrus_thread = None
                self._papyrus_worker = None

        # papyrusMonitoringChanged is emitted by the setter
        # Signal update
        self.papyrusStatsUpdated.emit(0, 0, 0.0, 0, 0)  # Clear or update state logic if needed

    @Slot()
    @staticmethod
    def openCrashLogsFolder() -> None:
        """Open the crash logs folder in the system file browser.

        Creates the folder if it doesn't exist, then opens it using
        the default system file manager.
        """
        from PySide6.QtGui import QDesktopServices

        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            path = Path(local_dir) / "Crash Logs"
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot()
    @staticmethod
    def openBackupFolder() -> None:
        """Open the CLASSIC backup folder in the system file browser.

        Opens the backup folder using the default system file manager.
        Does nothing if the local directory is not configured.
        """
        from PySide6.QtGui import QDesktopServices

        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            path = Path(local_dir) / "CLASSIC Backup"
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot(result=list)
    def getReports(self) -> list[dict[str, Any]]:
        """Get a list of available scan reports.

        Searches both the default crash logs folder and any custom scan
        path for AUTOSCAN report files.

        Returns:
            A list of dictionaries containing report metadata with keys:
            - name: The filename of the report
            - path: The full path to the report file
            - date: The file modification timestamp

        """
        reports: list[dict[str, Any]] = []

        # 1. Default Crash Logs Folder
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            crash_logs_dir = Path(local_dir) / "Crash Logs"
            if crash_logs_dir.exists():
                files = [{"name": f.name, "path": str(f), "date": f.stat().st_mtime} for f in crash_logs_dir.glob("*-AUTOSCAN.md")]
                reports.extend(files)

        # 2. Custom Scan Folder
        custom_path = self._custom_scan_path
        if custom_path:
            custom_dir = Path(custom_path)
            if custom_dir.exists() and custom_dir.is_dir():
                for f in custom_dir.glob("*-AUTOSCAN.md"):
                    # Avoid duplicates if custom path is same as default path (unlikely but possible)
                    if not any(r["path"] == str(f) for r in reports):
                        reports.append({"name": f.name, "path": str(f), "date": f.stat().st_mtime})

        # Sort by date desc
        reports.sort(key=itemgetter("name"), reverse=True)
        return reports

    @Slot(str, result=str)
    @staticmethod
    def readReport(path: str) -> str:
        """Read the contents of a report file.

        Args:
            path: The full path to the report file.

        Returns:
            The text contents of the file, or an error message if the
            file cannot be read.

        """
        try:
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            return "Error reading file."

    @Slot()
    def refreshReports(self) -> None:
        """Emit the reportsUpdated signal to trigger a UI refresh."""
        self.reportsUpdated.emit()

    @Slot(str)
    def deleteReport(self, path_str: str) -> None:
        """Delete a report file from the filesystem.

        Args:
            path_str: The full path to the report file to delete.

        Note:
            Automatically refreshes the reports list on success.
            Logs an error if deletion fails.

        """
        try:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                self.refreshReports()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to delete report: {e}")


def main() -> None:
    """Entry point for the QML-based CLASSIC GUI application.

    Initializes the Qt application, sets up the QML engine with the ClassicBackend,
    and starts the main event loop.
    """
    app = QApplication(sys.argv)
    app.setOrganizationName("CLASSIC")
    app.setOrganizationDomain("classic.fallout4")

    # Use Basic style which is good for custom theming
    QQuickStyle.setStyle("Basic")

    # Initialize Application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=True)

    engine = QQmlApplicationEngine()

    # Backend should be created AFTER global registry and settings are initialized
    backend = ClassicBackend()
    backend.setParent(app)  # Explicitly set parent to QApplication
    engine.rootContext().setContextProperty("backend", backend)

    # Load Main.qml
    # PyInstaller bundle or Development
    base_path = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent  # pyright: ignore[reportAttributeAccessIssue]

    qml_file = base_path / "qml" / "Main.qml"
    if not qml_file.exists():
        logger.error(f"QML file not found at: {qml_file}")
        sys.exit(-1)

    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
