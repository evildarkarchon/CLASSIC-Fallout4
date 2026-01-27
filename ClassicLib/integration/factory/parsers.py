"""Parser factory functions.

Provides factory functions for log parsing implementations,
selecting between Rust and Python implementations.

Classes:
    PythonParserWrapper: A wrapper class for Python-based log parser
    implementations, mimicking the interface of a Rust-based log parser.

Functions:
    get_parser: Retrieve the most efficient log parser implementation available.
"""

from __future__ import annotations

import logging
from typing import Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

logger = logging.getLogger(__name__)


class PythonParserWrapper:
    """Wrapper for Python parser functions to match RustLogParser interface."""

    @staticmethod
    def find_segments(
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
    ) -> tuple[str, str, str, list[list[str]]]:
        """Find and retrieves segments information based on the input parameters.

        This method serves as a wrapper for `find_segments` function, facilitating the
        retrieval of segments information relevant to the crash data. It processes the
        provided arguments to facilitate analysis or further processing of the crash
        data associated with specific conditions.

        Args:
            crash_data: List of strings representing lines of crash data.
            crashgen_name: The name of the crash generation process or identifier.
            xse_acronym: Acronym associated with the XSE process specifics.
            game_root_name: Name of the root directory or identifier for the game's context.

        Returns:
            tuple[str, str, str, list[list[str]]]: A tuple containing game_version,
            crashgen_version, main_error, and processed_segments.

        """
        from ClassicLib.integration.python.parser_py import find_segments

        return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

    @staticmethod
    def extract_section(
        crash_data: list[str],
        start_marker: str,
        end_marker: str,
    ) -> list[str] | None:
        """Extract a specific section of text from the given crash data.

        This method iterates through a list of text lines and collects all lines
        that appear after the start marker and before the end marker. The resulting
        lines are returned as a list. If no matching section is found, the method
        returns None.

        Args:
            crash_data: List of strings representing lines of crash data.
            start_marker: String that marks the start of the desired section.
            end_marker: String that marks the end of the desired section.

        Returns:
            list[str] | None: A list containing lines of the extracted section, or
            None if no valid section is found.

        """
        # Python implementation
        section = []
        in_section = False

        for line in crash_data:
            if line.startswith(start_marker):
                in_section = True
                continue
            if line.startswith(end_marker):
                break
            if in_section:
                section.append(line)

        return section or None  # pyright: ignore[reportUnknownVariableType]


def get_parser() -> Any:
    """Retrieve an appropriate parser based on component availability.

    This function determines whether to use a Rust-based parser or a Python-based
    fallback for parsing data. It checks the system configuration and availability
    of the Rust parser and falls back to using pure Python implementations if
    necessary. The returned parser provides the same interface regardless of the
    underlying implementation, ensuring seamless functionality.

    Returns:
        Any: An instance of the parser, which could be a Rust-based or Python-based
        implementation.

    Raises:
        ImportError: If the Rust parser module fails to import.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("parser", False):
        try:
            # Import the wrapper that handles both Rust and Python
            from ClassicLib.integration.rust.parser_rust import RustLogParser

            logger.debug("Using RustLogParser wrapper (150x speedup potential)")
            return RustLogParser()
        except ImportError as e:
            logger.warning(f"Failed to import RustLogParser: {e}")

    # Fall back to pure Python functions
    # Return a wrapper that provides the same interface
    logger.debug("Using Python parser implementation")
    return PythonParserWrapper()
