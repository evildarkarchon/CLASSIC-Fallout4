"""Rust-accelerated ReportFragment wrapper.

This module provides the RustAcceleratedReportFragment class for
seamless integration between Rust and Python report fragment implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ClassicLib.integration.detector import detect_component
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment

if TYPE_CHECKING:
    from classic_scanlog import ReportFragment as RustReportFragment

    RUST_AVAILABLE: bool = True
else:
    _has_fragment, RustReportFragment = detect_component("classic_scanlog", "ReportFragment")
    RUST_AVAILABLE = _has_fragment

    if not RUST_AVAILABLE:
        RustReportFragment = None  # type: ignore[assignment, misc]


class RustAcceleratedReportFragment:
    """Wrapper for Rust-accelerated ReportFragment with Python fallback.

    This class provides seamless integration between Rust and Python implementations,
    automatically falling back to Python if Rust is not available.
    """

    def __init__(self, lines: list[str] | tuple[str, ...] | None = None, check_content: bool = True, use_rust: bool = True) -> None:
        """Initialize the object with optional lines of text and configuration for content checking
        and internal Rust implementation usage.

        Args:
            lines (list[str] | tuple[str, ...] | None): The sequence of lines to be processed.
                It can be a list or a tuple of strings. If None, no lines are initialized.
            check_content (bool): Flag to determine whether content validation should be performed.
                Defaults to True.
            use_rust (bool): Flag to determine whether the Rust-based implementation should be
                used when available. Defaults to True.

        """
        self._use_rust = use_rust and RUST_AVAILABLE

        if self._use_rust:
            assert RustReportFragment is not None, "Rust should be available when _use_rust is True"
            # Use Rust implementation
            if lines is None:
                self._fragment = RustReportFragment.empty()
            else:
                lines_list = list(lines) if isinstance(lines, tuple) else lines
                # Note: Rust from_lines doesn't take check_content parameter
                self._fragment = RustReportFragment.from_lines(lines_list)
        # Fall back to Python implementation
        elif lines is None:
            self._fragment = PyReportFragment.empty()
        else:
            self._fragment = PyReportFragment.from_lines(lines, check_content)

    @classmethod
    def empty(cls) -> RustAcceleratedReportFragment:
        """Create and returns a new empty instance of RustAcceleratedReportFragment.

        This method is a class method that initializes an empty instance of
        RustAcceleratedReportFragment. It determines whether to use the Rust
        implementation or the Python fallback, based on the availability of
        Rust, and sets up the corresponding empty report fragment.

        Returns:
            RustAcceleratedReportFragment: An instance of the class initialized
            with either the Rust or Python empty report fragment, depending on
            Rust availability.

        """
        instance = cls.__new__(cls)
        instance._use_rust = RUST_AVAILABLE

        if instance._use_rust:
            assert RustReportFragment is not None, "Rust should be available when _use_rust is True"
            instance._fragment = RustReportFragment.empty()
        else:
            instance._fragment = PyReportFragment.empty()

        return instance

    @classmethod
    def from_lines(cls, lines: list[str] | tuple[str, ...], check_content: bool = True) -> RustAcceleratedReportFragment:
        """Create an instance of the `RustAcceleratedReportFragment` class from a list or tuple of string lines.

        Args:
            lines (list[str] | tuple[str, ...]): A sequence of strings representing the report details.
            check_content (bool): Specifies whether to validate the content of the provided lines. Defaults to True.

        Returns:
            RustAcceleratedReportFragment: A new instance of the class initialized using the given `lines` and
                                           `check_content` parameters.

        """
        return cls(lines, check_content)

    @classmethod
    def wrap_fragment(
        cls,
        fragment: RustReportFragment | PyReportFragment,  # type: ignore[name-defined]
        use_rust: bool,
    ) -> RustAcceleratedReportFragment:
        """Create an instance from an existing internal fragment.

        This factory method is for use by related classes like
        RustAcceleratedReportGenerator that need to wrap pre-created fragments.

        Args:
            fragment: The underlying Rust or Python fragment to wrap.
            use_rust: Whether the fragment is a Rust implementation.

        Returns:
            RustAcceleratedReportFragment: A new instance wrapping the provided fragment.

        """
        instance = cls.__new__(cls)
        instance._use_rust = use_rust
        instance._fragment = fragment
        return instance

    def with_header(self, header_lines: list[str] | tuple[str, ...]) -> RustAcceleratedReportFragment:
        """Add headers to the current report fragment, either by using Rust acceleration
        or Python fallback depending on the internal configuration.

        This method modifies the fragment by prepending the provided header lines.
        The exact behavior depends on whether the object is utilizing Rust
        acceleration or not.

        Args:
            header_lines (list[str] | tuple[str, ...]): A list or tuple of strings
                representing the header lines to be added to the report fragment.

        Returns:
            RustAcceleratedReportFragment: A new instance of
                RustAcceleratedReportFragment with the provided headers included.

        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        # Convert tuple to list for consistency
        header_list = list(header_lines) if isinstance(header_lines, tuple) else header_lines

        if self._use_rust:
            result._fragment = self._fragment.with_header(header_list)  # type: ignore[union-attr]
        else:
            result._fragment = self._fragment.with_header(header_list)

        return result

    def __add__(self, other: RustAcceleratedReportFragment | PyReportFragment) -> RustAcceleratedReportFragment:
        """Add two report fragments together to combine their
        internal fragments, with Rust acceleration if enabled. If Rust acceleration
        is not supported, it falls back to Python-based implementation for combining
        the fragments.

        Args:
            other (RustAcceleratedReportFragment | PyReportFragment): Another report fragment
                to combine with the current instance.

        Returns:
            RustAcceleratedReportFragment: A new instance containing the combined
                result of both fragments.

        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)

        # Check if other is RustAcceleratedReportFragment or PyReportFragment
        other_use_rust = getattr(other, "_use_rust", False)
        result._use_rust = self._use_rust and other_use_rust

        if result._use_rust:
            # Rust uses combine() method instead of __add__
            result._fragment = self._fragment.combine(other._fragment)  # type: ignore[union-attr]
        else:
            # Convert to Python if needed
            self_py = PyReportFragment.from_lines(self._fragment.to_list()) if self._use_rust else self._fragment  # type: ignore[union-attr,assignment]

            # Handle both RustAcceleratedReportFragment and PyReportFragment
            if hasattr(other, "_fragment"):
                other_py = PyReportFragment.from_lines(other._fragment.to_list()) if other_use_rust else other._fragment  # type: ignore[union-attr,assignment]
            else:
                # other is already a PyReportFragment
                other_py = other  # type: ignore[assignment]

            result._fragment = self_py + other_py  # type: ignore[assignment,operator]

        return result

    def to_list(self) -> list[str]:
        """Convert the internal fragment structure into a list of strings.

        Returns:
            list[str]: A list containing string representations of the internal fragment
            elements.

        """
        return self._fragment.to_list()

    @property
    def content(self) -> tuple[str, ...]:
        """Get the content of the fragment as a tuple of strings.

        This property retrieves the fragment content. If `use_rust` is enabled,
        it converts the content from Rust's internal to a Python tuple.

        Returns:
            tuple[str, ...]: A tuple containing all strings from the fragment content.

        """
        if self._use_rust:
            # Rust doesn't have content property, convert from to_list()
            return tuple(self._fragment.to_list())  # type: ignore[union-attr]
        return self._fragment.content  # type: ignore[union-attr]

    @property
    def has_content(self) -> bool:
        """Indicate whether the instance has any content.

        This property determines if there is content present within the instance.
        It either uses a Rust-based implementation to check content or relies
        on the corresponding Python-based method.

        Returns:
            bool: True if content is present, False otherwise.

        """
        if self._use_rust:
            # Rust has is_empty() method, invert it for has_content
            return not self._fragment.is_empty()  # type: ignore[union-attr]
        return self._fragment.has_content  # type: ignore[union-attr]

    def __len__(self) -> int:
        """Calculate the length of the fragment.

        This method determines the length of the fragment object. If the
        `_use_rust` flag is enabled, it utilizes the Rust implementation to
        obtain the length; otherwise, it uses Python's built-in length
        function.

        Returns:
            int: The length of the fragment.

        """
        if self._use_rust:
            # Rust has len() method
            return self._fragment.len()  # type: ignore[union-attr]
        return len(self._fragment)  # type: ignore[arg-type]

    def __bool__(self) -> bool:
        """Determine the truth value of the object.

        This method evaluates the truthiness of the object based on the state
        of its internal `_fragment` attribute and possibly additional logic
        depending on the `_use_rust` flag.

        Returns:
            bool: True if the `_fragment` has content; False otherwise.

        """
        if self._use_rust:
            assert RustReportFragment is not None, "Rust should be available when _use_rust is True"
            return not cast("RustReportFragment", self._fragment).is_empty()  # type: ignore[misc]
        return bool(self._fragment)


__all__ = [
    "RUST_AVAILABLE",
    "RustAcceleratedReportFragment",
]
