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
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ScanWorker(QObject):
    finished = Signal()
    error = Signal(str, str, str)
    
    def __init__(self, scan_type: str) -> None:
        super().__init__()
        self.scan_type = scan_type

    @Slot()
    def run(self) -> None:
        try:
            if self.scan_type == "crashlogs":
                executor = ScanLogsExecutor()
                executor.scan_sync()
            elif self.scan_type == "gamefiles":
                # Create a wrapper for the async function
                async def run_game_scan() -> None:
                    await write_combined_results_async()
                
                bridge = AsyncBridge.get_instance()
                bridge.run_async(run_game_scan())
            
            self.finished.emit()
        except Exception as e: # noqa: BLE001
            self.error.emit("Scan Failed", str(e), "")
            logger.error(f"Scan failed: {e}")

class PapyrusWorker(QObject):
    statsUpdated = Signal(int, int, float, int, int) # dumps, stacks, ratio, warns, errors
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._should_run = True

    @Slot()
    def run(self) -> None:
        while self._should_run:
            try:
                message, count = papyrus_logging()
                stats = self._parse_stats(message, count)
                self.statsUpdated.emit(*stats)
                QThread.msleep(1000)
            except Exception as e: # noqa: BLE001
                self.error.emit(str(e))
                break
    
    def stop(self) -> None:
        self._should_run = False

    @staticmethod
    def _parse_stats(message: str, dump_count: int) -> tuple[int, int, float, int, int]:
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
    # Signals
    scanFinished = Signal()
    scanError = Signal(str, str) # title, message
    papyrusStatsUpdated = Signal(int, int, float, int, int) # dumps, stacks, ratio, warns, errors
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
    def stagingModsPath(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._staging_mods_path

    @stagingModsPath.setter
    def stagingModsPath(self, val: str) -> None:
        if self._staging_mods_path != val:
            self._staging_mods_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", val)
            self.stagingModsPathChanged.emit()

    @Property(str, notify=customScanPathChanged)
    def customScanPath(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._custom_scan_path

    @customScanPath.setter
    def customScanPath(self, val: str) -> None:
        if self._custom_scan_path != val:
            self._custom_scan_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", val)
            self.customScanPathChanged.emit()

    @Property(bool, notify=vrModeChanged)
    def vrMode(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._vr_mode or False

    @vrMode.setter
    def vrMode(self, val: bool) -> None:
        if self._vr_mode != val:
            self._vr_mode = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", val)
            self.vrModeChanged.emit()

    @Property(bool, notify=fcxModeChanged)
    def fcxMode(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._fcx_mode or False

    @fcxMode.setter
    def fcxMode(self, val: bool) -> None:
        if self._fcx_mode != val:
            self._fcx_mode = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", val)
            self.fcxModeChanged.emit()

    @Property(bool, notify=simplifyLogsChanged)
    def simplifyLogs(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._simplify_logs or False

    @simplifyLogs.setter
    def simplifyLogs(self, val: bool) -> None:
        if self._simplify_logs != val:
            self._simplify_logs = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", val)
            self.simplifyLogsChanged.emit()

    @Property(bool, notify=showFidValuesChanged)
    def showFidValues(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._show_fid_values or False

    @showFidValues.setter
    def showFidValues(self, val: bool) -> None:
        if self._show_fid_values != val:
            self._show_fid_values = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values", val)
            self.showFidValuesChanged.emit()

    @Property(bool, notify=moveInvalidLogsChanged)
    def moveInvalidLogs(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._move_invalid_logs or False

    @moveInvalidLogs.setter
    def moveInvalidLogs(self, val: bool) -> None:
        if self._move_invalid_logs != val:
            self._move_invalid_logs = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", val) # YAML key differs slightly
            self.moveInvalidLogsChanged.emit()

    @Property(bool, notify=updateCheckChanged)
    def updateCheck(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._update_check or False

    @updateCheck.setter
    def updateCheck(self, val: bool) -> None:
        if self._update_check != val:
            self._update_check = val
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Update Check", val)
            self.updateCheckChanged.emit()

    @Property(str, notify=iniPathChanged)
    def iniPath(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._ini_path

    @iniPath.setter
    def iniPath(self, val: str) -> None:
        if self._ini_path != val:
            self._ini_path = val
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", val)
            self.iniPathChanged.emit()

    @Property(bool, notify=papyrusMonitoringChanged)
    def papyrusMonitoring(self): # pyright: ignore[reportRedeclaration]  # noqa: ANN201
        return self._papyrus_monitoring

    @papyrusMonitoring.setter
    def papyrusMonitoring(self, val: bool) -> None:
        if self._papyrus_monitoring != val:
            self._papyrus_monitoring = val
            self.papyrusMonitoringChanged.emit()

    # Methods
    @Slot()
    def scanCrashLogs(self) -> None:
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
        self.scanFinished.emit()
        self.refreshReports() # Update reports list

    @Slot(str, str)
    def backupOperation(self, category: str, action: str) -> None:
        """
        Perform backup operation.
        category: XSE, RESHADE, VULKAN, ENB
        action: BACKUP, RESTORE, REMOVE
        """
        # Map category to what BackupManager or manage_game_files expects
        # manage_game_files(selected_list, selected_mode)
        # selected_list format: "Backup TYPE"
        # selected_mode: "BACKUP", "RESTORE", "REMOVE"
        try:
            manage_game_files(f"Backup {category}", action) # pyright: ignore[reportArgumentType]
            logger.info(f"Backup operation {action} {category} completed.")
        except Exception as e: # noqa: BLE001
            self.scanError.emit("Backup Error", str(e))

    @Slot(str)
    def fetchPastebin(self, url_or_id: str) -> None:
        # Implement pastebin fetch
        # Reuse logic from ClassicLib.Util.pastebin_fetch_async via wrapper if needed
        from ClassicLib.Util import pastebin_fetch_async
        
        async def do_fetch() -> None:
            await pastebin_fetch_async(url_or_id)
            
        bridge = AsyncBridge.get_instance()
        try:
            bridge.run_async(do_fetch())
            self.scanFinished.emit() # Just to notify completion
        except Exception as e: # noqa: BLE001
            self.scanError.emit("Pastebin Error", str(e))

    @Slot()
    def togglePapyrus(self) -> None:
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
            self._papyrus_worker.finished.connect(self._papyrus_thread.quit) # type: ignore
            
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
        self.papyrusStatsUpdated.emit(0, 0, 0.0, 0, 0) # Clear or update state logic if needed

    @Slot()
    @staticmethod
    def openCrashLogsFolder() -> None:
        from PySide6.QtGui import QDesktopServices
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            path = Path(local_dir) / "Crash Logs"
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot()
    @staticmethod
    def openBackupFolder() -> None:
        from PySide6.QtGui import QDesktopServices
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            path = Path(local_dir) / "CLASSIC Backup"
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            
    @Slot(result=list)
    def getReports(self) -> list[dict[str, Any]]:
        # Return list of reports (name, path, date)
        reports: list[dict[str, Any]] = []
        
        # 1. Default Crash Logs Folder
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            crash_logs_dir = Path(local_dir) / "Crash Logs"
            if crash_logs_dir.exists():
                files = [
                    {
                        "name": f.name,
                        "path": str(f),
                        "date": f.stat().st_mtime
                    }
                    for f in crash_logs_dir.glob("*-AUTOSCAN.md")
                ]
                reports.extend(files)
        
        # 2. Custom Scan Folder
        custom_path = self._custom_scan_path
        if custom_path:
            custom_dir = Path(custom_path)
            if custom_dir.exists() and custom_dir.is_dir():
                for f in custom_dir.glob("*-AUTOSCAN.md"):
                    # Avoid duplicates if custom path is same as default path (unlikely but possible)
                    if not any(r["path"] == str(f) for r in reports):
                        reports.append({
                            "name": f.name,
                            "path": str(f),
                            "date": f.stat().st_mtime
                        })

        # Sort by date desc
        reports.sort(key=itemgetter("name"), reverse=True)
        return reports
    
    @Slot(str, result=str)
    @staticmethod
    def readReport(path: str) -> str:
        try:
            return Path(path).read_text(encoding='utf-8', errors='ignore')
        except Exception:  # noqa: BLE001
            return "Error reading file."

    @Slot()
    def refreshReports(self) -> None:
        self.reportsUpdated.emit()
    
    @Slot(str)
    def deleteReport(self, path_str: str) -> None:
        try:
            p = Path(path_str)
            if p.exists():
                p.unlink()
                self.refreshReports()
        except Exception as e: # noqa: BLE001
            logger.error(f"Failed to delete report: {e}")

if __name__ == "__main__":
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
    backend.setParent(app) # Explicitly set parent to QApplication
    engine.rootContext().setContextProperty("backend", backend)

    # Load Main.qml
    # PyInstaller bundle or Development
    base_path = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent # pyright: ignore[reportAttributeAccessIssue]

    qml_file = base_path / "qml" / "Main.qml"
    if not qml_file.exists():
        logger.error(f"QML file not found at: {qml_file}")
        sys.exit(-1)
        
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())
