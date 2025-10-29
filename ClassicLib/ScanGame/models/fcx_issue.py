"""Data models for FCX mode configuration issues."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = ["ConfigIssue", "ConfigIssueSeverity"]

ConfigIssueSeverity = Literal["error", "warning", "info"]


@dataclass
class ConfigIssue:
    """Detected configuration issue with recommendation.

    Attributes:
        file_path: Path to the configuration file
        section: INI section name (None for TOML or non-sectioned files)
        setting: Setting/key name
        current_value: Current value in the file
        recommended_value: Recommended value to fix the issue
        description: Human-readable description of the issue
        severity: Issue severity level
    """

    file_path: Path
    section: str | None
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: ConfigIssueSeverity = "warning"

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)

        if self.severity not in ("error", "warning", "info"):
            raise ValueError(f"Invalid severity: {self.severity}")

    def format_report(self) -> str:
        """Format issue as human-readable report section.

        Returns:
            Formatted markdown-style report text with emoji severity indicator,
            issue description, file path, section, setting, and value comparison.

        Example:
            ⚠️ DETECTED ISSUE: Hotkey is commented out and won't work
               File: C:\\...\\espexplorer.ini
               Section: [Main]
               Setting: HotKey
               Current Value: ; F10
               Recommended Value: 0x79

        """
        severity_icons: dict[ConfigIssueSeverity, str] = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }

        icon = severity_icons.get(self.severity, "⚠️")
        section_str = f"[{self.section}]" if self.section else "N/A"

        return f"""{icon} DETECTED ISSUE: {self.description}
   File: {self.file_path}
   Section: {section_str}
   Setting: {self.setting}
   Current Value: {self.current_value}
   Recommended Value: {self.recommended_value}

"""
