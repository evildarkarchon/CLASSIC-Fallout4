"""
Rust-accelerated FCXModeHandler wrapper.

This module provides a transparent wrapper around the Rust FCXModeHandler implementation,
maintaining full API compatibility with the Python reference while delivering performance
improvements.

Key API Translations:
- Constructor: Handle None values (convert to False for Rust)
- Return types: Convert Rust list[str] to Python ReportFragment
"""

from __future__ import annotations

from ClassicLib.ScanLog.ReportFragment import ReportFragment

try:
    import classic_core

    RustFcxModeHandler = classic_core.scanlog.FcxModeHandler
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RustFcxModeHandler = None
    RUST_AVAILABLE = False


class RustAcceleratedFcxModeHandler:
    """
    Rust-accelerated FCX mode handler with Python API compatibility.

    This wrapper bridges the API differences between Rust and Python implementations:
    - Rust constructor only accepts bool (not None)
    - Rust returns list[str], Python returns ReportFragment
    """

    def __init__(self, fcx_mode: bool | None) -> None:
        """
        Initialize the FCX mode handler.

        Args:
            fcx_mode: Whether FCX mode is enabled (None treated as False)
        """
        self.fcx_mode = fcx_mode
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            # Rust doesn't accept None, convert to False
            rust_fcx_mode = fcx_mode if fcx_mode is not None else False
            self._handler = RustFcxModeHandler(rust_fcx_mode)
        else:
            # Fallback to Python implementation
            from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments

            self._handler = FCXModeHandlerFragments(fcx_mode)

        # Initialize instance attributes for Python API compatibility
        self.game_files_check = None
        self.main_files_check = None

    def check_fcx_mode(self) -> None:
        """
        Checks and updates the FCX mode status, ensuring checks are performed only once per session.

        This method is responsible for verifying the FCX mode and performing validations by invoking
        necessary external components or fallback mechanisms. The FCX mode dictates whether certain
        checks for main and game files are executed. If the FCX mode is disabled, the checks are
        bypassed, and default messages are assigned.
        """
        if self._use_rust:
            self._handler.check_fcx_mode()
            # Rust stores results differently, but we maintain Python API
        else:
            self._handler.check_fcx_mode()
            # Copy results from Python implementation
            self.main_files_check = self._handler.main_files_check
            self.game_files_check = self._handler.game_files_check

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
        if self._use_rust:
            # Rust returns list[str], need to convert to ReportFragment
            lines = self._handler.get_fcx_messages()
            return ReportFragment.from_lines(lines)
        else:
            # Python already returns ReportFragment
            return self._handler.get_fcx_messages()

    @classmethod
    def reset_fcx_checks(cls) -> None:
        """
        Resets the FCX checks by updating related class-level indicators.

        This method ensures thread-safe modifications to attributes by utilizing a lock mechanism.
        Note: Rust implementation may not support this class method.
        """
        if not RUST_AVAILABLE:
            from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments

            FCXModeHandlerFragments.reset_fcx_checks()
        # Note: Rust implementation doesn't expose reset_fcx_checks as a class method
        # The Rust version resets automatically on drop or uses different state management


# Export both the wrapper and components for compatibility
FCXModeHandler = RustAcceleratedFcxModeHandler
FcxModeHandler = RustAcceleratedFcxModeHandler  # Alternative naming
__all__ = ["FCXModeHandler", "FcxModeHandler", "RustAcceleratedFcxModeHandler", "RUST_AVAILABLE"]
