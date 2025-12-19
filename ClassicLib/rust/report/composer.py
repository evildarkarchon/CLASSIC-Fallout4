"""Rust-accelerated ReportComposer wrapper.

This module provides the RustAcceleratedReportComposer class for
parallel fragment processing with automatic fallback to Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ClassicLib.integration.detector import detect_component
from ClassicLib.ScanLog.fragments.report_composer import ReportComposer as PyReportComposer
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment

if TYPE_CHECKING:
    from classic_scanlog import ReportComposer as RustReportComposer
    from classic_scanlog import ReportFragment as RustReportFragment

    RUST_AVAILABLE: bool = True
else:
    _has_fragment, RustReportFragment = detect_component("classic_scanlog", "ReportFragment")
    _has_composer, RustReportComposer = detect_component("classic_scanlog", "ReportComposer")
    RUST_AVAILABLE = _has_fragment and _has_composer

    if not RUST_AVAILABLE:
        RustReportFragment = None  # type: ignore[assignment, misc]
        RustReportComposer = None  # type: ignore[assignment, misc]

# Import fragment wrapper - using lazy import to avoid circular imports


def _get_fragment_class() -> type:
    """Get RustAcceleratedReportFragment class lazily to avoid circular imports.

    Returns:
        The RustAcceleratedReportFragment class.

    """
    from ClassicLib.rust.report.fragment import RustAcceleratedReportFragment
    return RustAcceleratedReportFragment


class RustAcceleratedReportComposer:
    """Wrapper for Rust-accelerated ReportComposer with Python fallback.

    Provides parallel fragment processing when using Rust implementation,
    with automatic fallback to Python for compatibility.
    """

    def __init__(self, _parallel_threshold: int = 10) -> None:
        """Initialize the class with the desired threshold for parallel processing.

        The constructor determines whether to use a Rust-based composer or a
        Python-based composer depending on the availability of Rust.

        Args:
            _parallel_threshold: Reserved for future use. Currently unused as
                Rust ReportComposer handles parallelization internally.

        """
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            assert RustReportComposer is not None, "Rust should be available when _use_rust is True"
            # Rust ReportComposer takes no parameters
            self._composer = RustReportComposer()
        else:
            self._composer = PyReportComposer()

        self._fragments: list[Any] = []

    def add(self, fragment: Any) -> RustAcceleratedReportComposer:
        """Add a fragment to the report composer. The fragment can be a Python or Rust
        oriented report fragment, or any compatible data structure, depending on
        implementation and requirements.

        This method supports both Python-based and Rust-accelerated processing. If the
        composer is Rust-accelerated and the provided fragment is not already in a
        native Rust-compatible format, it attempts to convert the fragment to a
        Rust-compatible representation before adding it to the composer. Similarly,
        for Python-based composition, it handles fragments that need conversion into
        a Python-compatible format.

        Supports chaining by returning the instance of the composer.

        Args:
            fragment: The fragment to add to the composer. Can be of type
                RustAcceleratedReportFragment, PyReportFragment, or any type
                convertible to a compatible fragment for the composer.

        Returns:
            RustAcceleratedReportComposer: The current instance of the composer,
                allowing method chaining.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        if self._use_rust:
            # Convert Python fragment to Rust if needed
            if isinstance(fragment, RustAcceleratedReportFragment):
                if fragment._use_rust:
                    # Rust add() returns None, we return self for chaining
                    self._composer.add(fragment._fragment)  # type: ignore[union-attr]
                else:
                    # Convert Python to Rust
                    rust_frag = RustReportFragment.from_lines(fragment._fragment.to_list())  # type: ignore[union-attr]
                    self._composer.add(rust_frag)  # type: ignore[union-attr]
            elif isinstance(fragment, PyReportFragment):
                rust_frag = RustReportFragment.from_lines(fragment.to_list())  # type: ignore[union-attr]
                self._composer.add(rust_frag)  # type: ignore[union-attr]
            elif hasattr(fragment, "_fragment"):
                # Handle wrapped fragments
                self._composer.add(fragment._fragment)  # type: ignore[union-attr]
            else:
                # Assume it's a Rust fragment
                self._composer.add(fragment)  # type: ignore[union-attr]
        # Python composer
        elif isinstance(fragment, RustAcceleratedReportFragment):
            self._composer.add(fragment._fragment)  # type: ignore[arg-type,union-attr]
        elif isinstance(fragment, PyReportFragment):
            self._composer.add(fragment)  # type: ignore[arg-type]
        # Try to convert
        elif hasattr(fragment, "to_list"):
            py_frag = PyReportFragment.from_lines(fragment.to_list())
            self._composer.add(py_frag)  # type: ignore[arg-type]
        else:
            self._composer.add(fragment)  # type: ignore[arg-type]

        return self

    def compose(self) -> Any:
        """Generate and returns a report fragment, utilizing Rust optimization if enabled.

        The composing process is optimized using Rust-based functionality when applicable.
        If Rust is not enabled, the composing reverts to a standard method. The optimization
        leverages Rust for producing a processed list of strings, which are then wrapped in
        a `RustReportFragment`.

        Returns:
            RustAcceleratedReportFragment: The composed report fragment.

        """
        RustAcceleratedReportFragment = _get_fragment_class()

        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            assert RustReportComposer is not None, "Rust should be available when _use_rust is True"
            assert RustReportFragment is not None, "Rust should be available when _use_rust is True"
            # Rust compose_optimized() returns list[str], need to wrap in ReportFragment
            lines = cast("RustReportComposer", self._composer).compose_optimized()  # type: ignore[misc]
            result._fragment = RustReportFragment.from_lines(lines)  # type: ignore[union-attr,assignment]
        else:
            result._fragment = self._composer.compose()  # type: ignore[assignment,union-attr]

        return result

    def build(self) -> Any:
        """Build and returns a RustAcceleratedReportFragment instance.

        This method creates and composes an instance of RustAcceleratedReportFragment
        by utilizing the compose method.

        Returns:
            RustAcceleratedReportFragment: The resulting instance created by the compose method.

        """
        return self.compose()

    def to_list(self) -> list[str]:
        """Convert the internal composed object into a list of strings.

        This method determines whether to use a Rust-optimized composition
        or a Python-based composition, depending on the internal configuration.

        Returns:
            list[str]: A list of strings representing the composed object.

        """
        if self._use_rust:
            assert RustReportComposer is not None, "Rust should be available when _use_rust is True"
            # Rust compose_optimized() directly returns list[str]
            return cast("RustReportComposer", self._composer).compose_optimized()  # type: ignore[misc]
        return self._composer.to_list()  # type: ignore[union-attr]

    def build_string(self) -> str:
        """Build a string from the composer using either Rust implementation or a Python fallback.

        This method determines the string construction approach based on the use of
        Rust for computation. If Rust is enabled, it delegates the operation to the
        Rust-based implementation; otherwise, it falls back to a Python-based
        construction method by using the underlying composer.

        Returns:
            str: The constructed string from the composer.

        """
        if self._use_rust:
            assert RustReportComposer is not None, "Rust should be available when _use_rust is True"
            return cast("RustReportComposer", self._composer).build_string()  # type: ignore[misc]

        # Python fallback
        lines = self._composer.to_list()  # type: ignore[union-attr]
        return "\n".join(lines)

    @property
    def pool_stats(self) -> tuple[int, int, int, int] | None:
        """Get the statistics of the pool.

        Provides information about the pool's current state in a tuple format if available.

        Returns:
            tuple[int, int, int, int] | None: A tuple containing pool statistics
            (size, lookups, hits, insertions) if the Rust-based composer is used,
            otherwise None.

            - size: Number of unique interned strings in the pool
            - lookups: Total number of intern attempts
            - hits: Number of cache hits (string already in pool)
            - insertions: Number of new strings added to pool

        """
        if self._use_rust:
            assert RustReportComposer is not None, "Rust should be available when _use_rust is True"
            return cast("RustReportComposer", self._composer).pool_stats()  # type: ignore[misc]

        # Python fallback doesn't have string pool
        return None


__all__ = [
    "RUST_AVAILABLE",
    "RustAcceleratedReportComposer",
]
