"""
Fragment-based FCX mode handler for CLASSIC.

This module provides fragment-returning version of FCX mode handling,
replacing the mutable list pattern with immutable fragment composition.
"""

import threading
from typing import ClassVar

from ClassicLib.ScanLog.ReportFragment import ReportFragment


class FCXModeHandlerFragments:
    """Fragment-based FCX mode handler for crash log analysis."""

    # Class-level attributes shared across all instances
    _fcx_lock: ClassVar[threading.Lock] = threading.Lock()
    _fcx_checks_run: ClassVar[bool] = False
    _main_files_result: ClassVar[str] = ""
    _game_files_result: ClassVar[str] = ""

    def __init__(self, fcx_mode: bool | None) -> None:
        """
        Initialize the FCX mode handler.

        Args:
            fcx_mode: Whether FCX mode is enabled
        """
        self.fcx_mode = fcx_mode

    def check_fcx_mode(self) -> None:
        """Check FCX mode and run necessary file checks if enabled."""
        if self.fcx_mode:
            from ClassicLib.ScanGame import game_combined_result
            from ClassicLib.SetupCoordinator import SetupCoordinator

            # Use class-level lock to ensure thread safety
            with FCXModeHandlerFragments._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not FCXModeHandlerFragments._fcx_checks_run:
                    # Run the checks once and store results in class variables
                    coordinator = SetupCoordinator()
                    FCXModeHandlerFragments._main_files_result = coordinator.generate_combined_results()
                    FCXModeHandlerFragments._game_files_result = game_combined_result()
                    FCXModeHandlerFragments._fcx_checks_run = True

            # Always assign the stored results to instance variables
            self.main_files_check = FCXModeHandlerFragments._main_files_result
            self.game_files_check = FCXModeHandlerFragments._game_files_result
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    @classmethod
    def reset_fcx_checks(cls) -> None:
        """Reset FCX checks and results."""
        with cls._fcx_lock:
            cls._fcx_checks_run = False
            cls._main_files_result = ""
            cls._game_files_result = ""

    def get_fcx_messages(self) -> ReportFragment:
        """
        Get FCX mode-related messages as a fragment.

        Returns:
            ReportFragment containing FCX mode messages and file check results.
        """
        lines = []

        if self.fcx_mode:
            lines.extend([
                "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n\n",
                "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n",
            ])
            if self.main_files_check:
                lines.append(self.main_files_check)
            if self.game_files_check:
                lines.append(self.game_files_check)
        else:
            lines.extend([
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n\n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
            ])

        return ReportFragment.from_lines(lines)
