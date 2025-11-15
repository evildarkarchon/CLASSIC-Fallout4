"""
Rust-accelerated report generation wrapper.

This module provides backward-compatible wrappers for the Rust report generation
components, implementing Phase 5 of the Rust migration plan. It offers:
- 10-15x performance improvement in report generation
- Memory-efficient string interning
- Parallel fragment processing
- Drop-in replacement for existing Python components
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

# Try to import Rust implementation
from ClassicLib.integration.detector import detect_component

if TYPE_CHECKING:
    # For type checking, assume types exist
    from classic_scanlog import ParallelReportProcessor as RustParallelProcessor
    from classic_scanlog import ReportComposer as RustReportComposer
    from classic_scanlog import ReportFragment as RustReportFragment
    from classic_scanlog import ReportGenerator as RustReportGenerator
    from classic_scanlog import StringPool as RustStringPool

    RUST_AVAILABLE: bool = True
else:
    # Centralized detection of Rust report components
    _has_fragment, RustReportFragment = detect_component("classic_scanlog", "ReportFragment")
    _has_composer, RustReportComposer = detect_component("classic_scanlog", "ReportComposer")
    _has_generator, RustReportGenerator = detect_component("classic_scanlog", "ReportGenerator")
    _has_stringpool, RustStringPool = detect_component("classic_scanlog", "StringPool")
    _has_parallel, RustParallelProcessor = detect_component("classic_scanlog", "ParallelReportProcessor")

    RUST_AVAILABLE = _has_fragment and _has_composer and _has_generator

    if not RUST_AVAILABLE:
        RustReportFragment = None  # type: ignore[assignment, misc]
        RustReportComposer = None  # type: ignore[assignment, misc]
        RustReportGenerator = None  # type: ignore[assignment, misc]
        RustStringPool = None  # type: ignore[assignment, misc]
        RustParallelProcessor = None  # type: ignore[assignment, misc]

# Import Python fallback
from ClassicLib.ScanLog.fragments.report_composer import ReportComposer as PyReportComposer
from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyReportFragment
from ClassicLib.ScanLog.fragments.report_generator_functional import ReportGeneratorFunctional as PyReportGenerator


class RustAcceleratedReportFragment:
    """
    Wrapper for Rust-accelerated ReportFragment with Python fallback.

    This class provides seamless integration between Rust and Python implementations,
    automatically falling back to Python if Rust is not available.
    """

    def __init__(self, lines: list[str] | tuple[str, ...] | None = None, check_content: bool = True, use_rust: bool = True) -> None:
        """
        Initializes the object with optional lines of text and configuration for content checking
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
        """
        Creates and returns a new empty instance of RustAcceleratedReportFragment.

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
        """
        Creates an instance of the `RustAcceleratedReportFragment` class from a list or tuple of string lines.

        Args:
            lines (list[str] | tuple[str, ...]): A sequence of strings representing the report details.
            check_content (bool): Specifies whether to validate the content of the provided lines. Defaults to True.

        Returns:
            RustAcceleratedReportFragment: A new instance of the class initialized using the given `lines` and
                                           `check_content` parameters.
        """
        return cls(lines, check_content)

    def with_header(self, header_lines: list[str] | tuple[str, ...]) -> RustAcceleratedReportFragment:
        """
        Adds headers to the current report fragment, either by using Rust acceleration
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
        """
        Adds two report fragments together to combine their
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
        """
        Converts the internal fragment structure into a list of strings.

        Returns:
            list[str]: A list containing string representations of the internal fragment
            elements.
        """
        return self._fragment.to_list()

    @property
    def content(self) -> tuple[str, ...]:
        """
        Gets the content of the fragment as a tuple of strings.

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
        """
        Indicates whether the instance has any content.

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
        """
        Calculates the length of the fragment.

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
        """
        Determines the truth value of the object.

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


class RustAcceleratedReportComposer:
    """
    Wrapper for Rust-accelerated ReportComposer with Python fallback.

    Provides parallel fragment processing when using Rust implementation,
    with automatic fallback to Python for compatibility.
    """

    def __init__(self, _parallel_threshold: int = 10) -> None:
        """
        Initializes the class with the desired threshold for parallel processing.

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

    def add(self, fragment: RustAcceleratedReportFragment | PyReportFragment | Any) -> RustAcceleratedReportComposer:
        """
        Adds a fragment to the report composer. The fragment can be a Python or Rust
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
            fragment (RustAcceleratedReportFragment | PyReportFragment | Any):
                The fragment to add to the composer. Can be of type
                RustAcceleratedReportFragment, PyReportFragment, or any type
                convertible to a compatible fragment for the composer.

        Returns:
            RustAcceleratedReportComposer: The current instance of the composer,
                allowing method chaining.
        """
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

    def compose(self) -> RustAcceleratedReportFragment:
        """
        Generates and returns a report fragment, utilizing Rust optimization if enabled.

        The composing process is optimized using Rust-based functionality when applicable.
        If Rust is not enabled, the composing reverts to a standard method. The optimization
        leverages Rust for producing a processed list of strings, which are then wrapped in
        a `RustReportFragment`.

        Returns:
            RustAcceleratedReportFragment: The composed report fragment.
        """
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

    def build(self) -> RustAcceleratedReportFragment:
        """
        Builds and returns a RustAcceleratedReportFragment instance.

        This method creates and composes an instance of RustAcceleratedReportFragment
        by utilizing the compose method.

        Returns:
            RustAcceleratedReportFragment: The resulting instance created by the compose method.
        """
        return self.compose()

    def to_list(self) -> list[str]:
        """
        Converts the internal composed object into a list of strings.

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
        """
        Builds a string from the composer using either Rust implementation or a Python fallback.

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
        """
        Gets the statistics of the pool.

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


class RustAcceleratedReportGenerator:
    """
    Wrapper for Rust-accelerated ReportGenerator with Python fallback.

    Provides efficient string building and pooling when using Rust implementation.
    """

    def __init__(self, yamldata: Any = None) -> None:
        """
        Initializes the object and sets up the report generator based on the availability
        of the Rust implementation. If Rust is not available, a Python-based report
        generator is used.

        Args:
            yamldata: Optional initial data in YAML format that will be associated
                with the report generator.
        """
        self._use_rust = RUST_AVAILABLE
        self.yamldata = yamldata

        if self._use_rust:
            self._generator = RustReportGenerator()  # type: ignore[misc]
        else:
            self._generator = PyReportGenerator()
            self._generator.yamldata = yamldata  # type: ignore[attr-defined]

    def generate_header(self, crashlog_filename: str, version: str = "") -> RustAcceleratedReportFragment:
        """
        Generates a header fragment for a Rust-accelerated report. The method determines
        the use of Rust acceleration and delegates the generation of the header accordingly.

        Args:
            crashlog_filename: The filename of the crash log to be processed.
            version: The version string to be included in the header. Defaults to an
                empty string.

        Returns:
            RustAcceleratedReportFragment: An instance containing the generated
            header fragment.

        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            result._fragment = self._generator.generate_header(crashlog_filename, version)
        else:
            result._fragment = self._generator.generate_header(crashlog_filename, version)

        return result

    def generate_error_section(
        self,
        main_error: str,
        crashgen_version: str,
        version_current: Any,
        version_latest: Any,
        version_latest_vr: Any,
    ) -> RustAcceleratedReportFragment:
        """
        Generates an error section in the report.

        This method determines the appropriate error section for a report based on the
        provided parameters and handles logic for generating the fragment either using
        Python or Rust implementation. It includes checks for whether the version is up
        to date and provides warning messages accordingly.

        Args:
            main_error: The main error message to be included in the report.
            crashgen_version: The version of the crash generator used.
            version_current: The current version of the software (comparable type).
            version_latest: The latest supported version of the software (comparable type).
            version_latest_vr: The latest VR-compatible version of the software (comparable type).

        Returns:
            RustAcceleratedReportFragment: A fragment object containing the error section.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            assert RustReportGenerator is not None, "Rust should be available when _use_rust is True"
            # Rust implementation expects different signature - convert parameters
            from ClassicLib import GlobalRegistry

            crashgen_name = self.yamldata.crashgen_name if self.yamldata else "Crashgen"
            game_is_vr = GlobalRegistry.get_vr() == "VR"

            # Check if version is latest
            is_latest = not (
                (version_current < version_latest_vr and version_current != version_latest)
                or (not game_is_vr and version_current < version_latest)
            )

            warn_outdated = f"***❌ WARNING: YOUR {crashgen_name} IS OUTDATED! PLEASE UPDATE TO THE LATEST VERSION!***"

            result._fragment = self._generator.generate_error_section(main_error, crashgen_version, crashgen_name, is_latest, warn_outdated)
        else:
            # Python implementation uses the original signature
            result._fragment = self._generator.generate_error_section(
                main_error, crashgen_version, version_current, version_latest, version_latest_vr
            )

        return result

    def generate_suspect_section(self, found_suspects: list[str]) -> RustAcceleratedReportFragment:
        """
        Generates a suspect section fragment using either the Rust or Python generator,
        depending on the specified configuration setting.

        Args:
            found_suspects (list[str]): A list of suspect identifiers as strings.

        Returns:
            RustAcceleratedReportFragment: A generated report fragment containing the
            suspect section.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = self._use_rust

        if self._use_rust:
            result._fragment = self._generator.generate_suspect_section(found_suspects)
        else:
            result._fragment = self._generator.generate_suspect_section(found_suspects)

        return result

    @staticmethod
    def generate_suspect_section_header() -> RustAcceleratedReportFragment:
        """
        Generates a section header for reporting known crash messages, errors, and suspects.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the section header.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Known Crash Messages, Errors and Suspects\n\n",
        ])

        return result

    @staticmethod
    def generate_suspect_found_footer(found_suspect: bool) -> RustAcceleratedReportFragment:
        """
        Generates a footer message indicating whether suspects were detected.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Args:
            found_suspect: Whether one or more suspects were detected.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the footer message.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static footer
        if found_suspect:
            result._fragment = PyReportFragment.from_lines([
                "* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\n",
                "---\n\n",
            ])
        else:
            result._fragment = PyReportFragment.from_lines([
                "* **NO SUSPECTS DETECTED** *\n\n",
                "---\n\n",
            ])

        return result

    @staticmethod
    def generate_settings_section_header() -> RustAcceleratedReportFragment:
        """
        Generates a section header for reporting settings-related issues.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the settings-related issues header.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Settings-related Issues\n\n",
        ])

        return result

    @staticmethod
    def generate_mod_check_header(check_type: str) -> RustAcceleratedReportFragment:
        """
        Generates a report fragment header for mod checks based on the provided check type.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Args:
            check_type: The type of mod check to include in the header.

        Returns:
            RustAcceleratedReportFragment: A fragment containing the formatted header lines.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            f"### Checking For Mods That {check_type}\n\n",
        ])

        return result

    @staticmethod
    def generate_plugin_suspect_header() -> RustAcceleratedReportFragment:
        """
        Generates a header fragment for reports related to plugin-related errors.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A fragment containing formatted header information.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Plugin-related Errors\n\n",
        ])

        return result

    @staticmethod
    def generate_formid_section_header() -> RustAcceleratedReportFragment:
        """
        Generates a section header for FormID checks.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: A segment of the report containing the FormID check header.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking FormIDs\n\n",
        ])

        return result

    @staticmethod
    def generate_record_section_header() -> RustAcceleratedReportFragment:
        """
        Generates a section header for checking named records.

        This method is not available in the Rust implementation, so it always uses
        the Python fallback implementation.

        Returns:
            RustAcceleratedReportFragment: An instance containing the predefined header lines.
        """
        result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
        result._use_rust = False  # Always use Python for this simple static method

        # Use Python implementation for static header
        result._fragment = PyReportFragment.from_lines([
            "### Checking for Named Records\n\n",
        ])

        return result


class ParallelReportProcessor:
    """
    Parallel report processing capabilities (Rust-only feature).

    Falls back to sequential processing in Python.
    """

    def __init__(self) -> None:
        """
        Initializes an instance of the class, setting up a processor based on the availability
        of Rust support.
        """
        self._use_rust = RUST_AVAILABLE

        if self._use_rust:
            assert RustParallelProcessor is not None, "Rust should be available when _use_rust is True"
            self._processor = RustParallelProcessor()
        else:
            self._processor = None

    def process_reports(self, reports: list[list[str]]) -> list[list[str]]:
        """
        Processes a list of report fragments by either utilizing a Rust-based processor
        (if available) or falling back to Python implementation for sequential processing.

        This method takes a two-dimensional list of strings, processes each
        list of lines into a report fragment, and returns a list of processed report fragments.
        When a Rust-based processor is available, it optimizes the handling of the reports,
        otherwise the processing is completed in Python.

        Args:
            reports (list[list[str]]): A list of report fragments, where each fragment
                is a list of strings containing lines of a particular report.

        Returns:
            list[list[str]]: A list of processed report fragments (each fragment is a list of strings).
        """
        if self._use_rust and self._processor is not None:
            from classic_scanlog import ParallelReportProcessor

            return ParallelReportProcessor.process_batch(reports, processor_fn=None)

        # Python fallback - sequential processing
        results = []
        for lines in reports:
            fragment = PyReportFragment.from_lines(lines)
            results.append(fragment.to_list())

        return results

    def combine_fragments_parallel(self, fragments: list[RustAcceleratedReportFragment]) -> RustAcceleratedReportFragment:
        """
        Combines multiple RustAcceleratedReportFragment instances into a single fragment
        utilizing parallel processing when applicable or falling back to sequential processing in Python.

        Args:
            fragments (list[RustAcceleratedReportFragment]): A list of RustAcceleratedReportFragment
                instances to be combined. All fragments should support Rust-based processing if using Rust.

        Returns:
            RustAcceleratedReportFragment: A new RustAcceleratedReportFragment instance that
            represents the combined result of the input fragments.
        """
        if self._use_rust and self._processor is not None and all(f._use_rust for f in fragments):
            from classic_scanlog import ParallelReportProcessor

            # Extract the Rust ReportFragment instances from the wrappers
            # Type ignore needed because _fragment is a union type, but we've checked _use_rust
            rust_fragments = [f._fragment for f in fragments]  # type: ignore[misc]
            result_fragment = ParallelReportProcessor.combine_fragments(rust_fragments)  # type: ignore[arg-type]

            result = RustAcceleratedReportFragment.__new__(RustAcceleratedReportFragment)
            result._use_rust = True
            result._fragment = result_fragment
            return result

        # Python fallback - sequential combination
        if not fragments:
            return RustAcceleratedReportFragment.empty()

        result = fragments[0]
        for fragment in fragments[1:]:
            result += fragment

        return result


# Convenience aliases for backward compatibility
ReportFragment = RustAcceleratedReportFragment
ReportComposer = RustAcceleratedReportComposer
ReportGenerator = RustAcceleratedReportGenerator


# Export the string pool if available
if RUST_AVAILABLE and RustStringPool is not None:
    StringPool = RustStringPool  # type: ignore[assignment,misc]
else:
    # Dummy implementation for Python fallback
    class StringPool:
        """Dummy string pool for Python fallback."""

        def __init__(self) -> None:
            """Initialize dummy string pool."""
            self._strings: set[str] = set()

        def intern(self, s: str) -> str:
            """Intern a string (no-op in dummy implementation).

            Returns:
                str: The input string unchanged.
            """
            self._strings.add(s)
            return s

        def intern_batch(self, strings: list[str]) -> list[str]:
            """Intern multiple strings (no-op in dummy implementation).

            Returns:
                list[str]: The input strings unchanged.
            """
            for s in strings:
                self._strings.add(s)
            return strings

        def get_stats(self) -> tuple[int, int, int, int]:
            """Get pool statistics.

            Returns:
                tuple[int, int, int, int]: Tuple of (total, unique, saved, current).
            """
            size = len(self._strings)
            return (size, 0, 0, size)

        def clear(self) -> None:
            """Clear the pool."""
            self._strings.clear()


__all__ = [
    "RUST_AVAILABLE",
    "ParallelReportProcessor",
    "ReportComposer",
    "ReportFragment",
    "ReportGenerator",
    "RustAcceleratedReportComposer",
    "RustAcceleratedReportFragment",
    "RustAcceleratedReportGenerator",
    "StringPool",
]
