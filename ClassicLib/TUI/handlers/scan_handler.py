"""Scan operation handler for TUI."""

import asyncio
from pathlib import Path
from typing import Any, Callable, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from CLASSIC_ScanLogs import ClassicScanLogs
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import classic_settings


class TuiScanHandler:
    """Bridges TUI events with core scan operations."""
    
    def __init__(self, output_callback: Optional[Callable[[str], None]] = None):
        """Initialize the scan handler.
        
        Args:
            output_callback: Function to call with output messages
        """
        self.output_callback = output_callback
        self.scanner: Optional[ClassicScanLogs] = None
        self.current_task: Optional[asyncio.Task] = None
        self.is_scanning = False
        
    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set the output callback function."""
        self.output_callback = callback
    
    def _send_output(self, message: str) -> None:
        """Send output to the callback if available."""
        if self.output_callback:
            self.output_callback(message)
    
    async def perform_crash_scan(
        self,
        scan_folder: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Perform crash logs scan.
        
        Args:
            scan_folder: Custom folder to scan, or None for default
            progress_callback: Function to call with progress updates (0.0-1.0)
            
        Returns:
            True if scan succeeded, False otherwise
        """
        if self.is_scanning:
            self._send_output("❌ Scan already in progress")
            return False
        
        try:
            self.is_scanning = True
            self._send_output("🔍 Starting crash logs scan...")
            
            # Initialize scanner
            self.scanner = ClassicScanLogs()
            
            # Initialize message handler for TUI mode
            init_message_handler(parent=None, is_gui_mode=False)
            
            # Set custom scan folder if provided
            if scan_folder:
                scan_path = Path(scan_folder)
                if scan_path.exists() and scan_path.is_dir():
                    # Store original folder setting
                    original_folder = classic_settings(str, "Scan Folder")
                    try:
                        # Temporarily set custom folder
                        classic_settings.set_value("Scan Folder", scan_folder)
                        self._send_output(f"📁 Scanning folder: {scan_folder}")
                    finally:
                        # Restore original setting after scan
                        if original_folder:
                            classic_settings.set_value("Scan Folder", original_folder)
                else:
                    self._send_output(f"❌ Invalid scan folder: {scan_folder}")
                    return False
            
            # Run the scan
            if hasattr(self.scanner.orchestrator, 'async_scan_logs'):
                # Use async version if available
                await self.scanner.orchestrator.async_scan_logs()
            else:
                # Fall back to sync version
                await asyncio.to_thread(self.scanner.scan_logs)
            
            self._send_output("✅ Crash logs scan completed successfully")
            
            if progress_callback:
                progress_callback(1.0)
            
            return True
            
        except Exception as e:
            self._send_output(f"❌ Error during crash scan: {str(e)}")
            return False
        finally:
            self.is_scanning = False
    
    async def perform_game_scan(
        self,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Perform game files scan.
        
        Args:
            progress_callback: Function to call with progress updates (0.0-1.0)
            
        Returns:
            True if scan succeeded, False otherwise
        """
        if self.is_scanning:
            self._send_output("❌ Scan already in progress")
            return False
        
        try:
            self.is_scanning = True
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
            
            return True
            
        except Exception as e:
            self._send_output(f"❌ Error during game scan: {str(e)}")
            return False
        finally:
            self.is_scanning = False
    
    def cancel_scan(self) -> None:
        """Cancel the current scan operation."""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self._send_output("⚠️ Scan cancelled by user")
        self.is_scanning = False
    
    def is_scan_running(self) -> bool:
        """Check if a scan is currently running."""
        return self.is_scanning