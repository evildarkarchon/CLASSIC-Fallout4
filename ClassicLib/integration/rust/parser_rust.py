"""Rust-accelerated LogParser wrapper.

Thin delegation layer for Rust LogParser. Rust is required.
All methods are synchronous. Use AsyncBridge for GUI contexts.
"""

from __future__ import annotations

import logging

from ClassicLib.integration.exceptions import RustError, RustParseError
from ClassicLib.integration.factory import detect_component

logger = logging.getLogger(__name__)

# Segment boundary definitions used by parse_complete
SEGMENT_BOUNDARIES_TEMPLATE = [
    ("\t[Compatibility]", "SYSTEM SPECS:"),
    ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
    ("PROBABLE CALL STACK:", "MODULES:"),
    ("MODULES:", "{xse} PLUGINS:"),
    ("{xse} PLUGINS:", "PLUGINS:"),
    ("PLUGINS:", "EOF"),
]


class RustLogParser:
    """Wrapper for Rust LogParser. Rust is required.

    Provides 150x performance improvement over pure Python.
    """

    def __init__(self) -> None:
        """Initialize with Rust parser. Raises RuntimeError if unavailable."""
        rust_available, LogParser = detect_component("classic_scanlog", "LogParser")
        if not rust_available or not LogParser:
            msg = "Required Rust module classic_scanlog.LogParser not available. Reinstall CLASSIC."
            raise RuntimeError(msg)

        try:
            self._rust_parser = LogParser()
            logger.debug("RustLogParser: Using RUST implementation")
        except (RustError, TypeError, ValueError) as e:
            msg = f"Failed to initialize Rust parser: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e

    def find_segments(
        self, crash_data: list[str], _crashgen_name: str, xse_acronym: str, _game_root_name: str
    ) -> tuple[str, str, str, list[list[str]]]:
        """Find and extract crash log segments.

        Args:
            crash_data: Crash log lines.
            crashgen_name: Crash generator name.
            xse_acronym: XSE acronym (e.g. "F4SE").
            game_root_name: Game root folder name.

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments).

        Raises:
            RuntimeError: If Rust parser fails.

        """
        xse_upper = xse_acronym.upper()
        segment_boundaries = [(s.replace("{xse}", xse_upper), e.replace("{xse}", xse_upper)) for s, e in SEGMENT_BOUNDARIES_TEMPLATE]
        try:
            scan_output = self._rust_parser.parse_complete(crash_data, segment_boundaries, xse_acronym)
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust parser failed: {e}"
            raise RuntimeError(msg) from e

        segments = scan_output.segments
        # Pad missing segments with empty lists
        missing = len(segment_boundaries) - len(segments)
        if missing > 0:
            segments.extend([[]] * missing)

        return scan_output.game_version, scan_output.crashgen_version, scan_output.main_error, segments

    def extract_section(self, crash_data: list[str], start_marker: str, end_marker: str) -> list[str] | None:
        """Extract a section between two markers.

        Args:
            crash_data: Crash log lines.
            start_marker: Section start marker.
            end_marker: Section end marker.

        Returns:
            List of section lines, or None if not found.

        Raises:
            RuntimeError: If Rust extract_section fails.

        """
        try:
            return self._rust_parser.extract_section(crash_data, start_marker, end_marker)
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust extract_section failed: {e}"
            raise RuntimeError(msg) from e

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active."""
        return True
