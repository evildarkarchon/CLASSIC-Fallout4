"""Rust-accelerated LogParser wrapper.

Thin delegation layer: tries Rust LogParser, falls back to Python.
All methods are synchronous. Use AsyncBridge for GUI contexts.
"""

from __future__ import annotations

import logging

from ClassicLib.integration.factory import detect_component
from ClassicLib.integration.exceptions import RustError, RustParseError

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
    """Wrapper for Rust LogParser with Python fallback.

    Provides 150x performance improvement when Rust is available.
    """

    def __init__(self) -> None:
        """Initialize with Rust parser if available, otherwise Python fallback."""
        self._rust_parser = None
        self._use_rust = False

        rust_available, LogParser = detect_component("classic_scanlog", "LogParser")
        if rust_available and LogParser:
            try:
                self._rust_parser = LogParser()
                self._use_rust = True
                logger.debug("RustLogParser: Using RUST implementation")
            except (RustError, TypeError, ValueError) as e:
                logger.error(f"Failed to initialize Rust parser: {e}")

        if not self._use_rust:
            logger.debug("RustLogParser: Falling back to Python implementation")

    def find_segments(
        self, crash_data: list[str], crashgen_name: str, xse_acronym: str, game_root_name: str
    ) -> tuple[str, str, str, list[list[str]]]:
        """Find and extract crash log segments.

        Args:
            crash_data: Crash log lines.
            crashgen_name: Crash generator name.
            xse_acronym: XSE acronym (e.g. "F4SE").
            game_root_name: Game root folder name.

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments).

        """
        if self._use_rust and self._rust_parser:
            try:
                xse_upper = xse_acronym.upper()
                segment_boundaries = [
                    (s.replace("{xse}", xse_upper), e.replace("{xse}", xse_upper))
                    for s, e in SEGMENT_BOUNDARIES_TEMPLATE
                ]
                scan_output = self._rust_parser.parse_complete(crash_data, segment_boundaries, xse_acronym)

                segments = scan_output.segments
                # Pad missing segments with empty lists
                missing = len(segment_boundaries) - len(segments)
                if missing > 0:
                    segments.extend([[]] * missing)

                return scan_output.game_version, scan_output.crashgen_version, scan_output.main_error, segments
            except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
                logger.warning(f"Rust parser failed, falling back to Python: {e}")

        from ClassicLib.integration.python.parser_py import find_segments

        return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

    def extract_section(self, crash_data: list[str], start_marker: str, end_marker: str) -> list[str] | None:
        """Extract a section between two markers.

        Args:
            crash_data: Crash log lines.
            start_marker: Section start marker.
            end_marker: Section end marker.

        Returns:
            List of section lines, or None if not found.

        """
        if self._use_rust and self._rust_parser:
            try:
                return self._rust_parser.extract_section(crash_data, start_marker, end_marker)
            except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
                logger.debug(f"Rust extract_section failed: {e}")

        # Python fallback
        section: list[str] = []
        in_section = False
        for line in crash_data:
            if line.startswith(start_marker):
                in_section = True
                continue
            if line.startswith(end_marker):
                break
            if in_section:
                section.append(line)
        return section or None

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active."""
        return self._use_rust
