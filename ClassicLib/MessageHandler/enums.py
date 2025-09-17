"""Message type and target enums for the MessageHandler system."""

from enum import Enum, auto


class MessageType(Enum):
    """
    Represents various types of messages categorized by their context and severity.

    This enumeration helps to define and manage message categories efficiently
    for logging or displaying purposes. It provides a predefined set of message
    types that can be used across an application to standardize how messages are
    identified and processed.

    Attributes:
        INFO (MessageType): Denotes an informational message.
        WARNING (MessageType): Denotes a warning message indicating a potential issue.
        ERROR (MessageType): Denotes an error message indicating a failure or problem.
        SUCCESS (MessageType): Denotes a message indicating the successful completion
            of an operation or process.
        PROGRESS (MessageType): Denotes a message signaling the progress of an ongoing
            operation.
        DEBUG (MessageType): Denotes a message intended for debugging purposes.
        CRITICAL (MessageType): Denotes a message indicating a critical issue
            requiring immediate attention.
    """

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    PROGRESS = auto()
    DEBUG = auto()
    CRITICAL = auto()


class MessageTarget(Enum):
    """Enumeration to specify where a message should be directed.

    This class defines various message targets such as both GUI and CLI,
    only GUI, only CLI, or logs. It is used to control and direct how
    messages are processed and displayed in an application context.
    """

    ALL = auto()  # Show in both GUI and CLI
    GUI_ONLY = auto()  # Show only in GUI mode (legacy, replaced by GUI)
    CLI_ONLY = auto()  # Show only in CLI mode (legacy, replaced by CONSOLE)
    LOG_ONLY = auto()  # Only write to log file, no display
    GUI = auto()  # Show only in GUI mode
    CONSOLE = auto()  # Show only in CLI mode
