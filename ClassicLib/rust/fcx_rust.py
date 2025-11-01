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

from ClassicLib.ScanLog.fragments import ReportFragment

try:
    import classic_scanlog

    RustFcxModeHandler = classic_scanlog.FcxModeHandler
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
        Initializes an instance of the class, handling the configuration and setup
        based on the specified mode. Depending on the system configuration, the
        handler will either use a Rust-based implementation (if available) or a
        Python fallback implementation.

        Args:
            fcx_mode: Indicates whether FCX mode is enabled. If None, it will default
                      to False for the Rust-based implementation.
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
        Determines the FCX mode and synchronizes results from the handler.

        If the Rust implementation is enabled, the method executes the handler's FCX
        mode check using the Rust logic. For the Python implementation, the method
        executes the handler's FCX mode check and then copies necessary results to the
        corresponding attributes for maintaining consistency in the Python API.

        Raises:
            Any exception raised internally by the handler's check_fcx_mode method.
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
        Resets the FCX checks state for the current mode, depending on the implementation.
        This method provides compatibility between the Rust-based and Python-based
        FCX mode handlers. The Python implementation explicitly resets the state using
        the `FCXModeHandlerFragments` class, while the Rust implementation manages
        the state internally and does not expose this reset functionality directly.

        Returns:
            None: This method does not return any value.
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
