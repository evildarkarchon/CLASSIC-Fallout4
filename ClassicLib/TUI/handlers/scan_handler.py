"""Scan operation handler for TUI."""

import asyncio
import sys
from collections.abc import Callable
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class TuiScanHandler:
    """Bridges TUI events with core scan operations."""

    def __init__(self, output_callback: Callable[[str], None] | None = None) -> None:
        """Initialize the scan handler.

        Args:
            output_callback: Function to call with output messages
        """
        self.output_callback = output_callback
        self.scanner: ClassicScanLogs | None = None
        self.current_task: asyncio.Task | None = None
        self.is_scanning = False
        self._scan_lock = asyncio.Lock()

    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the output callback function."""
        self.output_callback = callback

    def _send_output(self, message: str) -> None:
        """Send output to the callback if available."""
        if self.output_callback:
            self.output_callback(message)

    async def perform_crash_scan(self, scan_folder: str | None = None, progress_callback: Callable[[float], None] | None = None) -> bool:
        """Perform crash logs scan.

        Args:
            scan_folder: Custom folder to scan, or None for default
            progress_callback: Function to call with progress updates (0.0-1.0)

        Returns:
            True if scan succeeded, False otherwise
        """
        # Acquire lock to check and set scanning state atomically
        async with self._scan_lock:
            if self.is_scanning:
                self._send_output("❌ Scan already in progress")
                return False
            self.is_scanning = True

        try:
            self._send_output("🔍 Starting crash logs scan...")

            # Initialize scanner
            self.scanner = ClassicScanLogs()

            # Initialize message handler for TUI mode
            init_message_handler(parent=None, is_gui_mode=False)

            # Set custom scan folder if provided
            original_folder = None
            if scan_folder:
                scan_path = Path(scan_folder)
                if scan_path.exists() and scan_path.is_dir():
                    # Batch settings operations to minimize thread transitions
                    try:
                        # Single thread transition for both read and write
                        def batch_settings_operation() -> str:
                            orig = classic_settings(str, "Scan Folder")
                            yaml_settings(str, YAML.Settings, "Scan Folder", scan_folder)
                            return orig

                        original_folder = await asyncio.to_thread(batch_settings_operation)
                        self._send_output(f"📁 Scanning folder: {scan_folder}")
                    except (OSError, KeyError, ValueError, TypeError) as e:
                        # If settings update fails, continue with default folder
                        self._send_output(f"⚠️ Could not update scan folder setting: {e}")
                        original_folder = None
                else:
                    self._send_output(f"❌ Invalid scan folder: {scan_folder}")
                    async with self._scan_lock:
                        self.is_scanning = False
                    return False

            # Run the scan using OrchestratorCore
            from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

            try:
                # Create orchestrator with context manager like in crashlogs_scan_async_pure
                async with OrchestratorCore(
                    self.scanner.yamldata,
                    self.scanner.crashlogs,
                    self.scanner.fcx_mode,
                    self.scanner.show_formid_values,
                    self.scanner.formid_db_exists,
                ) as orchestrator:
                    # Run FCX checks if enabled
                    if self.scanner.fcx_mode:
                        orchestrator.fcx_handler.check_fcx_mode()

                    # Process all crash logs
                    tasks = [self.scanner.process_crashlog_async(log, orchestrator) for log in self.scanner.crashlog_list]

                    # Execute all tasks
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results and write reports
                    for i, result in enumerate(results):
                        if isinstance(result, BaseException):
                            self._send_output(f"❌ Error processing {self.scanner.crashlog_list[i].name}: {result}")
                        else:
                            crashlog_file, autoscan_report, trigger_scan_failed, local_stats = result
                            # Write report using the existing async function
                            from CLASSIC_ScanLogs import write_report_to_file_async

                            await write_report_to_file_async(crashlog_file, autoscan_report, trigger_scan_failed, self.scanner)
            finally:
                # Restore original setting after scan if we changed it
                if original_folder:
                    await asyncio.to_thread(yaml_settings, str, YAML.Settings, "SCAN Custom Path", original_folder)

            self._send_output("✅ Crash logs scan completed successfully")

            if progress_callback:
                progress_callback(1.0)

        except (OSError, ValueError, TypeError, asyncio.CancelledError, ImportError) as e:
            self._send_output(f"❌ Error during crash scan: {e!s}")
            return False
        else:
            return True
        finally:
            async with self._scan_lock:
                self.is_scanning = False
                self.current_task = None

    async def perform_game_scan(self, progress_callback: Callable[[float], None] | None = None) -> bool:
        """Perform game files scan.

        Args:
            progress_callback: Function to call with progress updates (0.0-1.0)

        Returns:
            True if scan succeeded, False otherwise
        """
        # Acquire lock to check and set scanning state atomically
        async with self._scan_lock:
            if self.is_scanning:
                self._send_output("❌ Scan already in progress")
                return False
            self.is_scanning = True

        try:
            self._send_output("🔍 Starting game files scan...")

            # Import game scanner
            from CLASSIC_ScanGame import main as scan_game_main

            # Initialize message handler for TUI mode
            init_message_handler(parent=None, is_gui_mode=False)

            # Run the game scan
            await asyncio.to_thread(scan_game_main)

            self._send_output("✅ Game files scan completed successfully")

            if progress_callback:
                progress_callback(1.0)

        except (OSError, ValueError, TypeError, asyncio.CancelledError, ImportError) as e:
            self._send_output(f"❌ Error during game scan: {e!s}")
            return False
        else:
            return True
        finally:
            async with self._scan_lock:
                self.is_scanning = False
                self.current_task = None

    async def cancel_scan(self) -> None:
        """Cancel the current scan operation."""
        async with self._scan_lock:
            if self.current_task and not self.current_task.done():
                self.current_task.cancel()
                self._send_output("⚠️ Scan cancelled by user")
            self.is_scanning = False
            self.current_task = None

    def is_scan_running(self) -> bool:
        """Check if a scan is currently running (thread-safe check)."""
        # Note: This is a simple read, but for complete thread safety,
        # callers should use this with awareness that state might change immediately after
        return self.is_scanning
