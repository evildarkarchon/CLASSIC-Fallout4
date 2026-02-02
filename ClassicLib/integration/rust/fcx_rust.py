"""Rust-accelerated FCXModeHandler wrapper.

This module provides a transparent wrapper around the Rust FCXModeHandler implementation,
maintaining full API compatibility with the Python reference while delivering performance
improvements.

Key API Translations:
- Constructor: Handle None values (convert to False for Rust)
- Return types: Convert Rust list[str] to Python ReportFragment
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.integration.factory import detect_component
from ClassicLib.scanning.logs.reporting import ReportFragment

if TYPE_CHECKING:
    from classic_scanlog import FcxModeHandler as RustFcxModeHandlerType

    from ClassicLib.scanning.logs.fcx_mode_handler import (
        FCXModeHandlerFragments as PythonFcxModeHandlerType,
    )

# Centralized detection of Rust FcxModeHandler
RUST_AVAILABLE, RustFcxModeHandler = detect_component("classic_scanlog", "FcxModeHandler")
if not RUST_AVAILABLE:
    RustFcxModeHandler = None  # type: ignore[assignment]


class RustAcceleratedFcxModeHandler:
    """Rust-accelerated FCX mode handler with Python API compatibility.

    This wrapper bridges the API differences between Rust and Python implementations:
    - Rust constructor only accepts bool (not None)
    - Rust returns list[str], Python returns ReportFragment
    """

    def __init__(self, fcx_mode: bool | None) -> None:
        """Initialize an instance of the class, handling the configuration and setup
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
            self._handler: RustFcxModeHandlerType | PythonFcxModeHandlerType = RustFcxModeHandler(rust_fcx_mode)  # type: ignore[misc]
        else:
            # Fallback to Python implementation
            from ClassicLib.scanning.logs.fcx_mode_handler import FCXModeHandlerFragments

            self._handler: RustFcxModeHandlerType | PythonFcxModeHandlerType = FCXModeHandlerFragments(fcx_mode)

        # Initialize instance attributes for Python API compatibility
        # Note: Rust implementation doesn't use these attributes
        self.game_files_check: str | None = None
        self.main_files_check: str | None = None

    def check_fcx_mode(self) -> None:
        """Determine the FCX mode and synchronizes results from the handler.

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
            self._handler.check_fcx_mode()  # type: ignore[attr-defined]
            # Copy results from Python implementation
            self.main_files_check = self._handler.main_files_check  # type: ignore[attr-defined]
            self.game_files_check = self._handler.game_files_check  # type: ignore[attr-defined]

    def get_fcx_messages(self) -> ReportFragment:
        """Generate and returns FCX messages as a ReportFragment object.

        Depending on the FCX mode status, this method generates appropriate messages
        regarding FCX Mode being enabled or disabled. The messages include guidance
        for enabling/disabling the mode and additional checks if necessary.

        Returns:
            ReportFragment: An object containing the generated messages as lines,
            reflecting the current FCX mode status and associated checks.

        """
        if self._use_rust:
            # Rust has method named get_fcx_messages() and returns list[str]
            # Need to convert to ReportFragment for API compatibility
            lines: list[str] = self._handler.get_fcx_messages()  # type: ignore[attr-defined]
            return ReportFragment.from_lines(lines)
        # Python already returns ReportFragment
        return self._handler.get_fcx_messages()  # type: ignore[attr-defined]

    @classmethod
    def reset_fcx_checks(cls) -> None:
        """Reset the FCX checks state for the current mode, depending on the implementation.

        This method provides compatibility between the Rust-based and Python-based
        FCX mode handlers. The Python implementation explicitly resets the state using
        the `FCXModeHandlerFragments` class, while the Rust implementation manages
        the state internally and does not expose this reset functionality directly.

        Note:
            Rust implementation doesn't expose reset_fcx_checks as a class method.
            The Rust version resets automatically on drop or uses different state management.

        """
        if not RUST_AVAILABLE:
            from ClassicLib.scanning.logs.fcx_mode_handler import FCXModeHandlerFragments

            FCXModeHandlerFragments.reset_fcx_checks()
        # Note: Rust implementation doesn't expose reset_fcx_checks as a class method
        # The Rust version resets automatically on drop or uses different state management


# Export both the wrapper and components for compatibility
FCXModeHandler = RustAcceleratedFcxModeHandler
FcxModeHandler = RustAcceleratedFcxModeHandler  # Alternative naming
__all__ = ["FCXModeHandler", "FcxModeHandler", "RustAcceleratedFcxModeHandler", "RUST_AVAILABLE"]
