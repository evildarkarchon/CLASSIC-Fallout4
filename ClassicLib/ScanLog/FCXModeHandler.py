"""
FCX mode handler module for CLASSIC.

This module manages FCX mode operations including:
- Performing file integrity checks
- Handling game file validation
- Managing thread-safe FCX operations
- Caching FCX check results to avoid redundant operations
"""

import threading
from typing import Literal


class FCXModeHandler:
    """Handles FCX mode file integrity checking operations."""
    
    # Class-level variables for thread-safe caching
    _fcx_lock: threading.RLock = threading.RLock()
    _fcx_checks_run: bool = False
    _main_files_result: str = ""
    _game_files_result: str = ""
    
    def __init__(self, fcx_mode: bool | None) -> None:
        """
        Initialize FCX mode handler.
        
        Args:
            fcx_mode: Whether FCX mode is enabled
        """
        self.fcx_mode: bool | None = fcx_mode
        self.main_files_check: str | Literal[''] = ""
        self.game_files_check: str | Literal[''] = ""
        
    def check_fcx_mode(self) -> None:
        """
        Check FCX mode status and perform file integrity checks if enabled.
        
        Thread-safe implementation using a lock to ensure multiple threads
        don't run the expensive checks simultaneously.
        """
        if self.fcx_mode:
            # Import here to avoid circular imports
            from CLASSIC_Main import main_combined_result
            from CLASSIC_ScanGame import game_combined_result
            
            # Use class-level lock to ensure thread safety
            with FCXModeHandler._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not FCXModeHandler._fcx_checks_run:
                    # Run the checks once and store results in class variables
                    FCXModeHandler._main_files_result = main_combined_result()
                    FCXModeHandler._game_files_result = game_combined_result()
                    FCXModeHandler._fcx_checks_run = True
                    
            # Always assign the stored results to instance variables
            self.main_files_check = FCXModeHandler._main_files_result
            self.game_files_check = FCXModeHandler._game_files_result
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""
            
    @classmethod
    def reset_fcx_checks(cls) -> None:
        """Reset the FCX checks state for a new scan session."""
        with cls._fcx_lock:
            cls._fcx_checks_run = False
            cls._main_files_result = ""
            cls._game_files_result = ""
            
    def get_fcx_messages(self, autoscan_report: list[str]) -> None:
        """
        Add FCX mode messages to the autoscan report.
        
        Args:
            autoscan_report: List to append FCX messages
        """
        from ClassicLib.Util import append_or_extend
        
        if self.fcx_mode:
            append_or_extend(
                (
                    "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                    "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n",
                ),
                autoscan_report,
            )
            append_or_extend(self.main_files_check, autoscan_report)
            append_or_extend(self.game_files_check, autoscan_report)
        else:
            append_or_extend(
                (
                    "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                    "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
                ),
                autoscan_report,
            )