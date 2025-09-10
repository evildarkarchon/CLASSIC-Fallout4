"""
Configuration data model for scan operations.

This module contains the ScanConfig dataclass that encapsulates
all configuration options for crash log scanning.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScanConfig:
    """
    Configuration data class for scan operations.

    This class encapsulates all configuration options that affect
    how crash logs are scanned and processed.
    """

    # Core scanning options
    fcx_mode: bool | None = None
    show_formid_values: bool | None = None
    move_unsolved_logs: bool | None = None
    simplify_logs: bool | None = None

    # Path configuration
    custom_paths: dict[str, Path] = field(default_factory=dict)

    # Performance settings
    max_concurrent: int = 10

    # Internal settings (typically set by system, not user)
    formid_db_exists: bool = True
    remove_list: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Initialize computed fields after dataclass creation."""
        # Ensure custom_paths is always a dict
        if self.custom_paths is None:
            self.custom_paths = {}

        # Validate max_concurrent
        if self.max_concurrent < 1:
            self.max_concurrent = 1
        elif self.max_concurrent > 50:  # Reasonable upper limit
            self.max_concurrent = 50


# Type alias for better code readability
ScanConfigDict = dict[str, Any]
