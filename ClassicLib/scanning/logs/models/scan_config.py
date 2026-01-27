"""Configuration data model for scan operations.

This module contains the ScanConfig dataclass that encapsulates
all configuration options for crash log scanning.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScanConfig:
    """Configuration class for managing scan options and performance settings.

    This class is designed to encapsulate various scan configuration options,
    customizable path mappings, and performance-related settings for executing
    scans. It provides flexible and structured control over scanning behavior,
    with defaults and safeguards to maintain reasonable operational limits.

    Attributes:
        fcx_mode (bool | None): Enables or disables the FCX mode for the scan.
            If None, default system behavior applies.
        show_formid_values (bool | None): Indicates whether to display FormID
            values during the scan. If None, behavior defaults to the system's
            settings.
        move_unsolved_logs (bool | None): If set to True, unsolved logs are moved
            as part of the scan process. If None, system defaults are used.
        simplify_logs (bool | None): Determines whether logs should be simplified
            for easier readability or storage purposes. None defaults to system
            behavior.
        custom_paths (dict[str, Path]): User-defined mappings for custom paths
            related to scan operations. Defaults to an empty dictionary.
        max_concurrent (int): The maximum number of concurrent scan processes
            allowed. Defaults to 0 (automatic), with a permissible range of 0 to 32.
            When set to 0, the Rust orchestrator determines optimal concurrency
            based on CPU count.

    """

    # Core scanning options
    fcx_mode: bool | None = None
    show_formid_values: bool | None = None
    move_unsolved_logs: bool | None = None
    simplify_logs: bool | None = None

    # Path configuration
    custom_paths: dict[str, Path] = field(default_factory=dict)

    # Performance settings
    # 0 = Automatic (Rust determines optimal concurrency based on CPU count)
    # 1-32 = Explicit concurrency limit
    max_concurrent: int = 0

    # Internal settings (typically set by system, not user)
    formid_db_exists: bool = True
    remove_list: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Ensure the proper initialization of instance attributes after dataclass creation.

        This method is automatically invoked after the creation of a dataclass instance. It
        performs additional setup and validation for specific attributes to ensure they meet
        expected constraints or default states.
        """
        # Ensure custom_paths is always a dict
        if not self.custom_paths:
            self.custom_paths = {}

        # Validate max_concurrent (0 = auto, 1-32 = explicit)
        if self.max_concurrent < 0:
            self.max_concurrent = 0
        elif self.max_concurrent > 32:  # Reasonable upper limit for most systems
            self.max_concurrent = 32


# Type alias for better code readability
ScanConfigDict = dict[str, Any]
