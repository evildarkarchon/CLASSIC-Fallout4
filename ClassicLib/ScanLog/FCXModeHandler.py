"""
Fragment-based FCX mode handler for CLASSIC.

This module provides fragment-returning version of FCX mode handling,
replacing the mutable list pattern with immutable fragment composition.
"""

import asyncio
import threading
from typing import ClassVar

from ClassicLib.rust.report_rust import ReportFragment


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
    _detected_issues: ClassVar[list] = []  # List of ConfigIssue objects

    def __init__(self, fcx_mode: bool | None) -> None:
        """
        Initialize the FCX mode handler.

        Args:
            fcx_mode: Whether FCX mode is enabled
        """
        self.game_files_check = None
        self.main_files_check = None
        self.fcx_mode = fcx_mode

    async def check_fcx_mode_async(self) -> None:
        """
        Asynchronously checks and updates the FCX mode status.

        This is the async version that should be used from async contexts.
        It runs the sync FCX checks in a thread pool to avoid blocking the event loop
        and prevent async context violations from sync YAML operations.

        In FCX mode, this method detects configuration issues without modifying files,
        storing detected issues in the class-level _detected_issues list for reporting.

        Raises:
            ImportError: Raised when necessary external modules fail to import during execution.
        """
        if self.fcx_mode:
            try:
                from ClassicLib.ScanGame import generate_game_combined_result as scan_game_files
            except ImportError:
                # Fallback if the function doesn't exist
                def scan_game_files() -> tuple[str, list]:
                    return "Game files check not available\n", []

            from ClassicLib.SetupCoordinator import SetupCoordinator

            # Define sync function to run in thread pool
            def run_fcx_checks() -> tuple[str, str, list]:
                """Run FCX checks synchronously in thread pool.

                Returns:
                    A tuple containing (main_result, game_result, detected_issues) where:
                        - main_result: String containing the main files check result
                        - game_result: String containing the game files check result
                        - detected_issues: List of ConfigIssue objects detected during scan
                """
                coordinator = SetupCoordinator()
                main_result = coordinator.generate_combined_results()
                game_result, detected_issues = scan_game_files()
                return main_result, game_result, detected_issues

            # Use class-level lock to ensure thread safety
            with FCXModeHandlerFragments._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not FCXModeHandlerFragments._fcx_checks_run:
                    # Run the checks in a thread pool to avoid blocking async event loop
                    main_result, game_result, detected_issues = await asyncio.to_thread(run_fcx_checks)
                    FCXModeHandlerFragments._main_files_result = main_result
                    FCXModeHandlerFragments._game_files_result = game_result
                    FCXModeHandlerFragments._detected_issues = detected_issues
                    FCXModeHandlerFragments._fcx_checks_run = True

            # Always assign the stored results to instance variables
            self.main_files_check = FCXModeHandlerFragments._main_files_result
            self.game_files_check = FCXModeHandlerFragments._game_files_result
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    def check_fcx_mode(self) -> None:
        """
        Checks and updates the FCX mode status, ensuring checks are performed only once per session.

        This method is responsible for verifying the FCX mode and performing validations by invoking
        necessary external components or fallback mechanisms. The FCX mode dictates whether certain
        checks for main and game files are executed. If the FCX mode is disabled, the checks are
        bypassed, and default messages are assigned.

        In FCX mode, this method now also detects configuration issues without modifying files,
        storing detected issues in the class-level _detected_issues list for reporting.

        Raises:
            ImportError: Raised when necessary external modules fail to import during execution.
        """
        if self.fcx_mode:
            try:
                from ClassicLib.ScanGame import generate_game_combined_result as scan_game_files
            except ImportError:
                # Fallback if the function doesn't exist
                def scan_game_files() -> tuple[str, list]:
                    return "Game files check not available\n", []

            from ClassicLib.SetupCoordinator import SetupCoordinator

            # Use class-level lock to ensure thread safety
            with FCXModeHandlerFragments._fcx_lock:
                # Check if we've already run the FCX checks in this scan session
                if not FCXModeHandlerFragments._fcx_checks_run:
                    # Run the checks once and store results in class variables
                    coordinator = SetupCoordinator()
                    FCXModeHandlerFragments._main_files_result = coordinator.generate_combined_results()
                    # Unpack tuple: scan_game_files now returns (report_text, detected_issues)
                    FCXModeHandlerFragments._game_files_result, FCXModeHandlerFragments._detected_issues = scan_game_files()

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
        Resets the state of FCX checks to their initial state.

        This method is responsible for resetting all the state variables related to FCX
        checks. It ensures that the checks can start from a clean state by acquiring
        a lock to prevent race conditions in a multi-threaded environment. All internal
        tracking variables such as results and detected issues are cleared and reset.
        """
        with cls._fcx_lock:
            cls._fcx_checks_run = False
            cls._main_files_result = ""
            cls._game_files_result = ""
            cls._detected_issues = []

    def get_fcx_messages(self) -> ReportFragment:
        """
        Generates a detailed report fragment related to the FCX mode status and any detected
        configuration issues.

        This method is responsible for aggregating information about the current FCX mode
        state, mod and game file checks, and any configuration issues that have been detected.
        Depending on whether FCX mode is enabled or not, it prepares and formats an appropriate
        message. If FCX mode is enabled, additional details about detected issues with the
        configuration may also be appended to the report.

        Returns:
            ReportFragment: An object representing the aggregated and formatted report
            detailing FCX mode status and its associated information.
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

            # Add detected configuration issues section if any issues were found
            if FCXModeHandlerFragments._detected_issues:
                lines.append("\n--- DETECTED CONFIGURATION ISSUES ---\n\n")
                # Each ConfigIssue has a format_report() method that returns formatted text
                lines.extend(issue.format_report() for issue in FCXModeHandlerFragments._detected_issues)
        else:
            lines.extend([
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n\n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
            ])

        return ReportFragment.from_lines(lines)
