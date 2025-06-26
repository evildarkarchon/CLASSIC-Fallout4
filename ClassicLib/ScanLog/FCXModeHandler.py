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
        self.main_files_check: str | Literal[""] = ""
        self.game_files_check: str | Literal[""] = ""

    def check_fcx_mode(self) -> None:
        """
        Checks the current FCX mode and performs necessary validations.

        This method evaluates whether the FCX mode is enabled. If enabled, it ensures that
        FCX checks are performed only once per scan session using thread-safe class-level
        variables. The results of these checks are then assigned to instance variables.
        If FCX mode is disabled, default values are assigned to instance variables.

        Attributes:
            main_files_check: str
                Stores the result of the main files check, either from the check or a
                default message when FCX mode is disabled.
            game_files_check: str
                Stores the result of the game files check, either from the check or an
                empty string when FCX mode is disabled.
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
        """
        Resets specific checks and results related to FCX processing.

        This method is responsible for reinitializing the FCX-related checks and clearing
        any previously stored results for the main and game files. It ensures that the
        associated states are reset to their default values. This method utilizes a class-level
        lock to guarantee thread safety during the reset operation.

        Sections:
            - Parameters:
                This method does not accept any parameters.
            - Returns:
                None: This method does not return any value.

        Raises:
            This method does not raise any exceptions.
        """
        with cls._fcx_lock:
            cls._fcx_checks_run = False
            cls._main_files_result = ""
            cls._game_files_result = ""

    def get_fcx_messages(self, autoscan_report: list[str]) -> None:
        """
        Processes and appends FCX mode-related messages to the provided autoscan report.
        This method determines whether FCX mode is enabled or disabled and appends
        specific notification messages accordingly. It also appends the results
        of checks on main files and game files to the autoscan report if FCX mode
        is enabled.

        Parameters:
            autoscan_report (list[str]): The list to which the FCX mode messages and
            other file check results will be appended.

        Returns:
            None
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
