"""Papyrus log statistics data model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)  # Add slots for memory optimization
class PapyrusStats:
    """Statistics from Papyrus log analysis."""

    timestamp: datetime
    dumps: int
    stacks: int
    warnings: int
    errors: int
    ratio: float
    raw_output: str

    def get_status_symbol(self, use_unicode: bool = True) -> str:
        """Get status symbol based on stats.

        Args:
            use_unicode: Whether to use Unicode symbols

        Returns:
            Status symbol (Unicode or ASCII)
        """
        if self.errors > 10:
            return "❌" if use_unicode else "[X]"
        if self.warnings > 20:
            return "⚠️" if use_unicode else "[!]"
        if self.dumps > 0:
            return "✓" if use_unicode else "[v]"
        return "✅" if use_unicode else "[OK]"

    def get_status_color(self) -> str:
        """Get status color based on stats.

        Returns:
            Color name for Textual styling
        """
        if self.errors > 10:
            return "red"
        if self.warnings > 20:
            return "yellow"
        return "green"
