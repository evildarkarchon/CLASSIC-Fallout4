"""Papyrus Monitor Widget for CLASSIC TUI.

Compact real-time Papyrus statistics display.
"""

from dataclasses import dataclass
from pathlib import Path

from textual.reactive import reactive
from textual.widgets import Static


@dataclass
class PapyrusStats:
    """Statistics from Papyrus log monitoring.

    Attributes:
        dumps: Number of stack dumps detected.
        stacks: Number of stack traces.
        errors: Number of error messages.
        warnings: Number of warning messages.
        suspended: Number of suspended stacks.
        is_active: Whether monitoring is currently active.

    """

    dumps: int = 0
    stacks: int = 0
    errors: int = 0
    warnings: int = 0
    suspended: int = 0
    is_active: bool = False


class PapyrusMonitor(Static):
    """Compact Papyrus monitoring stats display widget.

    Shows real-time statistics from Papyrus log monitoring in a single line.
    Updates via polling when monitoring is active.

    Attributes:
        stats: Current Papyrus statistics (reactive).

    """

    DEFAULT_CSS = """
    PapyrusMonitor {
        background: #2d2d2d;
        border: solid #3c3c3c;
        padding: 0 1;
        height: 3;
    }
    """

    stats: reactive[PapyrusStats] = reactive(PapyrusStats, init=False)

    def __init__(self, id: str | None = None) -> None:  # noqa: A002
        """Initialize the Papyrus monitor widget.

        Args:
            id: Optional widget ID.

        """
        super().__init__(id=id)
        self.stats = PapyrusStats()
        self._monitoring = False
        self._timer = None

    def render(self) -> str:
        """Render the Papyrus stats display.

        Returns:
            Formatted string with status and statistics.

        """
        s = self.stats
        status = "[green]●[/] Active" if s.is_active else "[dim]○[/] Inactive"

        return (
            f"Status: {status}  │  "
            f"Dumps: {s.dumps}  Stacks: {s.stacks}  "
            f"Errors: [red]{s.errors}[/]  Warnings: [yellow]{s.warnings}[/]  "
            f"Suspended: {s.suspended}"
        )

    def start_monitoring(self) -> None:
        """Start Papyrus log monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self.stats = PapyrusStats(is_active=True)

        # Start polling timer
        self._timer = self.set_interval(1.0, self._poll_papyrus_log)

    def stop_monitoring(self) -> None:
        """Stop Papyrus log monitoring."""
        self._monitoring = False

        if self._timer:
            self._timer.stop()
            self._timer = None

        # Reset stats but mark as inactive
        self.stats = PapyrusStats(is_active=False)

    def _poll_papyrus_log(self) -> None:
        """Poll the Papyrus log file for updates."""
        if not self._monitoring:
            return

        log_path = self._find_papyrus_log()
        if log_path is None or not log_path.exists():
            return

        try:
            content = log_path.read_text(encoding="utf-8", errors="ignore")
            self.stats = PapyrusStats(
                dumps=content.count("Dumping"),
                stacks=content.count("stack:"),
                errors=content.count("[ERROR]"),
                warnings=content.count("[WARNING]"),
                suspended=content.count("suspended"),
                is_active=True,
            )
        except (OSError, UnicodeDecodeError):
            # Silently handle read errors
            pass

    @staticmethod
    def _find_papyrus_log() -> Path | None:
        """Locate the Papyrus log file based on game settings.

        Returns:
            Path to Papyrus log file, or None if not found.

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
