"""
Fragment-based FCX mode handler for CLASSIC.

This module provides fragment-returning version of FCX mode handling,
replacing the mutable list pattern with immutable fragment composition.
"""

import threading
from typing import ClassVar

from ClassicLib.ScanLog.ReportFragment import ReportFragment


class FCXModeHandlerFragments:
    """
    Handles operations and checks related to the FCX mode for system setups.

    This class manages FCX mode by providing file checking mechanisms specific to the FCX mode
    configuration. Its functionality includes running the necessary checks, retrieving messages
    related to FCX mode, and resetting the state for subsequent operations. It is designed to
    ensure thread safety through the use of a shared lock mechanism for class-level attributes.

    Attributes:
        fcx_mode (bool | None): Indicates whether FCX mode is enabled. This attribute is initialized
            during object construction and determines if FCX-related checks and operations should be
            performed.
    """

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
        self.game_files_check = None
        self.main_files_check = None
        self.fcx_mode = fcx_mode

    def check_fcx_mode(self) -> None:
        """
        Checks and updates the FCX mode status, ensuring checks are performed only once per session.

        This method is responsible for verifying the FCX mode and performing validations by invoking
        necessary external components or fallback mechanisms. The FCX mode dictates whether certain
        checks for main and game files are executed. If the FCX mode is disabled, the checks are
        bypassed, and default messages are assigned.

        Raises:
            ImportError: Raised when necessary external modules fail to import during execution.
        """
        if self.fcx_mode:
            try:
                from CLASSIC_ScanGame import game_combined_result as scan_game_files
            except ImportError:
                # Fallback if the function doesn't exist
                def scan_game_files() -> str:
                    return "Game files check not available\n"

            from ClassicLib.SetupCoordinator import SetupCoordinator

            # Use class-level lock to ensure thread safety
            with FCXModeHandlerFragments._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not FCXModeHandlerFragments._fcx_checks_run:
                    # Run the checks once and store results in class variables
                    coordinator = SetupCoordinator()
                    FCXModeHandlerFragments._main_files_result = coordinator.generate_combined_results()
                    FCXModeHandlerFragments._game_files_result = scan_game_files()
                    FCXModeHandlerFragments._fcx_checks_run = True

            # Always assign the stored results to instance variables
            self.main_files_check = FCXModeHandlerFragments._main_files_result
            self.game_files_check = FCXModeHandlerFragments._game_files_result
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    @classmethod
    def reset_fcx_checks(cls) -> None:
        """
        Resets the FCX checks by updating related class-level indicators. This method ensures
        thread-safe modifications to attributes by utilizing a lock mechanism.
        """
        with cls._fcx_lock:
            cls._fcx_checks_run = False
            cls._main_files_result = ""
            cls._game_files_result = ""

    def get_fcx_messages(self) -> ReportFragment:
        """
        Generates and returns FCX messages as a ReportFragment object.

        Depending on the FCX mode status, this method generates appropriate messages
        regarding FCX Mode being enabled or disabled. The messages include guidance
        for enabling/disabling the mode and additional checks if necessary.

        Returns:
            ReportFragment: An object containing the generated messages as lines,
            reflecting the current FCX mode status and associated checks.
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
