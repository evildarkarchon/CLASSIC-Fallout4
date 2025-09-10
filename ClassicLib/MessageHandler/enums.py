"""Message type and target enums for the MessageHandler system."""

from enum import Enum, auto


class MessageType(Enum):
    """Types of messages that can be displayed."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    PROGRESS = auto()
    DEBUG = auto()
    CRITICAL = auto()


class MessageTarget(Enum):
    """Target destinations for messages."""

    ALL = auto()  # Show in both GUI and CLI
    GUI_ONLY = auto()  # Show only in GUI mode
    CLI_ONLY = auto()  # Show only in CLI mode
    LOG_ONLY = auto()  # Only write to log file, no display
