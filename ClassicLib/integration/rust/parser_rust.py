"""Rust-accelerated LogParser wrapper.

Thin delegation layer for Rust LogParser. Rust is required.
All methods are synchronous. Use AsyncBridge for GUI contexts.
"""

from __future__ import annotations

import logging

from ClassicLib.integration.exceptions import RustError, RustParseError
from ClassicLib.integration.factory import detect_component

logger = logging.getLogger(__name__)


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
        self,
        crash_data: list[str],
        crashgen_name: str,  # noqa: ARG002
        xse_acronym: str,  # noqa: ARG002
        game_root_name: str,  # noqa: ARG002
    ) -> tuple[str, str, str, dict[str, list[str]]]:
        """Find and extract crash log segments using anchor-first segmentation.

        Args:
            crash_data: Crash log lines.
            crashgen_name: Crash generator name (unused; registry-driven routing).
            xse_acronym: XSE acronym (unused; anchor-first detection is XSE-agnostic).
            game_root_name: Game root folder name (unused; header parsing is separate).

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments) where
            ``segments`` is a ``dict[str, list[str]]`` with all 8 named keys always
            present: ``settings``, ``system``, ``callstack``, ``modules``,
            ``xse_modules``, ``plugins``, ``registers``, ``stack_dump``.

        Raises:
            RuntimeError: If Rust parser fails.

        """
        try:
            # parse_complete now returns a ScanOutput with segments as dict[str, list[str]].
            # The segment_boundaries parameter is accepted but ignored (anchor-first is always used).
            scan_output = self._rust_parser.parse_complete(crash_data, [], "")
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust parser failed: {e}"
            raise RuntimeError(msg) from e

        # segments is now a dict[str, list[str]] with all 8 keys guaranteed present.
        segments: dict[str, list[str]] = scan_output.segments

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

    def get_stats(self) -> dict[str, int]:
        """Get parser performance statistics from Rust implementation.

        Returns:
            Statistics dictionary from Rust parser.

        Raises:
            RuntimeError: If Rust stats retrieval fails.

        """
        try:
            return self._rust_parser.get_stats()
        except (RustParseError, RustError, AttributeError, TypeError, ValueError) as e:
            msg = f"Rust get_stats failed: {e}"
            raise RuntimeError(msg) from e

    def detect_vr_log(self, content: str) -> bool:
        """Detect whether crash log content is from Fallout 4 VR.

        Uses Rust detection when available. Falls back to a lightweight Python
        check if the bound Rust parser does not expose detect_vr_log.

        Args:
            content: Full crash log content.

        Returns:
            True when VR indicators are present, else False.

        Raises:
            RuntimeError: If Rust VR detection fails unexpectedly.

        """
        try:
            return self._rust_parser.detect_vr_log(content)
        except AttributeError:
            content_lower = content.lower()
            return "fallout4vr.exe" in content_lower or "fallout4vr.esm" in content_lower
        except (RustParseError, RustError, TypeError, ValueError) as e:
            msg = f"Rust detect_vr_log failed: {e}"
            raise RuntimeError(msg) from e

    @property
    def is_rust_accelerated(self) -> bool:
        """Whether Rust acceleration is active."""
        return True
