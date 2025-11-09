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
        """
        Validates and initializes class attributes after object creation.

        This method verifies and converts the `file_path` attribute into a `Path` object
        if it is not already of type `Path`. Additionally, it ensures that the `severity`
        attribute is one of the accepted values, specifically "error", "warning", or
        "info". If the value of `severity` is invalid, a `ValueError` is raised to
        indicate the issue.

        Raises:
            ValueError: If the `severity` attribute is not one of the accepted
                values ("error", "warning", "info").
        """
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)

        if self.severity not in {"error", "warning", "info"}:
            raise ValueError(f"Invalid severity: {self.severity}")

    def format_report(self) -> str:
        """
        Formats a configuration issue report into a human-readable string format with relevant
        details, including a severity icon, file path, affected section, and recommended values
        for corrections.

        Returns:
            str: A formatted string representation of the configuration issue.

        """
        severity_icons: dict[ConfigIssueSeverity, str] = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",  # noqa: RUF001
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
