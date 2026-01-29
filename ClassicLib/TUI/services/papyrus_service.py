"""Papyrus Service for CLASSIC TUI.

Background Papyrus log monitoring using polling.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PapyrusStats:
    """Statistics from Papyrus log monitoring."""

    dumps: int = 0
    stacks: int = 0
    errors: int = 0
    warnings: int = 0
    suspended: int = 0
    is_active: bool = False


class PapyrusService:
    """Service for Papyrus log monitoring using polling.

    Provides utility methods for Papyrus log analysis.
    The actual polling logic is implemented inline in the PapyrusMonitor
    widget for better integration with Textual's Worker API.
    """

    POLL_INTERVAL_SECONDS: float = 1.0

    @staticmethod
    def find_papyrus_log() -> Path | None:
        """Locate the Papyrus log file based on game settings.

        Returns:
            Path to the Papyrus log file if found, None otherwise.

        """
        from ClassicLib.io.yaml import classic_settings

        game = classic_settings(str, "Game") or "Fallout4"

        if game == "Fallout4":
            possible_paths = [
                Path.home() / "Documents/My Games/Fallout4/Logs/Script/Papyrus.0.log",
            ]
        else:  # Skyrim variants
            possible_paths = [
                Path.home() / "Documents/My Games/Skyrim Special Edition/Logs/Script/Papyrus.0.log",
            ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    @staticmethod
    def parse_log_content(content: str) -> PapyrusStats:
        """Parse Papyrus log content and extract statistics.

        Args:
            content: Raw log file content to parse.

        Returns:
            PapyrusStats with extracted counts.

        """
        return PapyrusStats(
            dumps=content.count("Dumping"),
            stacks=content.count("stack:"),
            errors=content.count("[ERROR]"),
            warnings=content.count("[WARNING]"),
            suspended=content.count("suspended"),
            is_active=True,
        )
