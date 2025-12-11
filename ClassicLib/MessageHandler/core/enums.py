"""Message type and target enums for the MessageHandler system.

This module provides enumerations for message categorization and routing.
When Rust acceleration is available, these can interoperate with the
Rust enums via the classic_message module.

Attributes:
    RUST_ENUMS: Whether Rust enum integration is available.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Self

# Try to import Rust enums for interop
try:
    from classic_message import MessageTarget as RustMessageTarget
    from classic_message import MessageType as RustMessageType

    _RUST_ENUMS_AVAILABLE = True
except ImportError:
    _RUST_ENUMS_AVAILABLE = False
    RustMessageType = None  # type: ignore[assignment, misc]
    RustMessageTarget = None  # type: ignore[assignment, misc]

# Export as module constant
RUST_ENUMS: bool = _RUST_ENUMS_AVAILABLE


class MessageType(Enum):
    """Message type enumeration for categorizing messages.

    Attributes:
        INFO: Informational message.
        WARNING: Warning message indicating a potential issue.
        ERROR: Error message indicating a failure or problem.
        SUCCESS: Message indicating successful completion.
        PROGRESS: Message signaling progress of an ongoing operation.
        DEBUG: Message intended for debugging purposes.
        CRITICAL: Message indicating a critical issue requiring attention.
    """

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    PROGRESS = auto()
    DEBUG = auto()
    CRITICAL = auto()

    def to_rust(self) -> Any | None:
        """Convert to Rust MessageType if available.

        Returns:
            Rust MessageType enum value or None if Rust unavailable.
        """
        if not RUST_ENUMS or RustMessageType is None:
            return None

        mapping = {
            MessageType.INFO: RustMessageType.Info,
            MessageType.WARNING: RustMessageType.Warning,
            MessageType.ERROR: RustMessageType.Error,
            MessageType.SUCCESS: RustMessageType.Success,
            MessageType.PROGRESS: RustMessageType.Progress,
            MessageType.DEBUG: RustMessageType.Debug,
            MessageType.CRITICAL: RustMessageType.Critical,
        }
        return mapping.get(self)

    @classmethod
    def from_rust(cls, rust_type: Any) -> Self:
        """Convert from Rust MessageType.

        Args:
            rust_type: Rust MessageType enum value.

        Returns:
            Corresponding Python MessageType.

        Raises:
            ValueError: If unknown Rust type.
        """
        if not RUST_ENUMS:
            msg = "Rust enums not available"
            raise ValueError(msg)

        # Use the name for mapping
        name = str(rust_type).lower()
        for member in cls:
            if member.name.lower() == name:
                return member

        msg = f"Unknown Rust MessageType: {rust_type}"
        raise ValueError(msg)


class MessageTarget(Enum):
    """Message target enumeration for routing messages.

    Attributes:
        ALL: Show in both GUI and CLI.
        GUI: Show only in GUI mode.
        CONSOLE: Show only in CLI mode.
        LOG_ONLY: Only write to log file, no display.
    """

    ALL = auto()
    GUI = auto()
    CONSOLE = auto()
    LOG_ONLY = auto()

    def normalize(self) -> MessageTarget:
        """Return self (no normalization needed with canonical values only).

        Returns:
            The same MessageTarget value.
        """
        return self

    def should_display_in_gui(self) -> bool:
        """Check if message should display in GUI mode.

        Returns:
            True if should display in GUI.
        """
        normalized = self.normalize()
        return normalized in {MessageTarget.ALL, MessageTarget.GUI}

    def should_display_in_cli(self) -> bool:
        """Check if message should display in CLI mode.

        Returns:
            True if should display in CLI.
        """
        normalized = self.normalize()
        return normalized in {MessageTarget.ALL, MessageTarget.CONSOLE}

    def should_display(self) -> bool:
        """Check if message should display at all (not log-only).

        Returns:
            True if should display.
        """
        normalized = self.normalize()
        return normalized != MessageTarget.LOG_ONLY

    def to_rust(self) -> Any | None:
        """Convert to Rust MessageTarget if available.

        Returns:
            Rust MessageTarget enum value or None if Rust unavailable.
        """
        if not RUST_ENUMS or RustMessageTarget is None:
            return None

        # Normalize first, then map
        normalized = self.normalize()
        mapping = {
            MessageTarget.ALL: RustMessageTarget.All,
            MessageTarget.GUI: RustMessageTarget.Gui,
            MessageTarget.CONSOLE: RustMessageTarget.Console,
            MessageTarget.LOG_ONLY: RustMessageTarget.LogOnly,
        }
        return mapping.get(normalized)

    @classmethod
    def from_rust(cls, rust_target: Any) -> MessageTarget:
        """Convert from Rust MessageTarget.

        Args:
            rust_target: Rust MessageTarget enum value.

        Returns:
            Corresponding Python MessageTarget.

        Raises:
            ValueError: If unknown Rust target.
        """
        if not RUST_ENUMS:
            msg = "Rust enums not available"
            raise ValueError(msg)

        # Use string representation for mapping
        name = str(rust_target).lower()
        # Map to canonical names
        if "gui" in name:
            return cls.GUI
        if "console" in name or "cli" in name:
            return cls.CONSOLE
        if "all" in name:
            return cls.ALL
        if "log" in name:
            return cls.LOG_ONLY

        msg = f"Unknown Rust MessageTarget: {rust_target}"
        raise ValueError(msg)
