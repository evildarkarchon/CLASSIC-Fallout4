"""Type stubs for classic_message.

Python bindings for classic-message-core, providing Rust-accelerated message handling
with type-safe message types, targets, and formatting utilities.

Architecture:
    - classic-message-core: Business logic (message routing, formatting, logging)
    - classic-message-py: Python bindings (this module - PyO3 adapters)

Features:
    - Type-safe message categorization (INFO, WARNING, ERROR, etc.)
    - Flexible message routing (GUI, CLI, log-only)
    - Emoji stripping for Windows console compatibility
    - Centralized logging with Rust integration
    - Builder pattern for message construction

Usage:
    from classic_message import MessageType, MessageTarget, Message, Logger

    # Create and route messages
    msg = Message("Operation started", MessageType.INFO)
    msg = msg.with_title("Process").with_details("Processing 100 items")

    # Check routing
    if msg.target().should_display():
        print(msg.content())

    # Format for logging
    log_text = format_log_message(msg.content(), msg.details())

    # Use the logger
    logger = Logger()
    logger.info("Application started")
    logger.log_message(msg)
"""

from __future__ import annotations

from enum import IntEnum

__version__: str

class MessageType(IntEnum):
    """Message type enumeration for categorizing messages.

    This enum provides various message categories for logging and display purposes.
    Each variant maps to a specific severity or purpose level.

    Attributes:
        Info: Informational message (value: 0).
        Warning: Warning message indicating a potential issue (value: 1).
        Error: Error message indicating a failure or problem (value: 2).
        Success: Message indicating successful completion (value: 3).
        Progress: Message signaling the progress of an ongoing operation (value: 4).
        Debug: Message intended for debugging purposes (value: 5).
        Critical: Message indicating a critical issue requiring immediate attention (value: 6).

    Example:
        >>> msg_type = MessageType.INFO
        >>> print(msg_type.name())
        'Info'
        >>> print(msg_type.value)
        0
    """

    Info = 0
    Warning = 1
    Error = 2
    Success = 3
    Progress = 4
    Debug = 5
    Critical = 6

    def name(self) -> str: # pyright: ignore[reportIncompatibleMethodOverride]
        """Gets the human-readable name of the message type.

        Returns:
            The name of the message type (e.g., "Info", "Warning").

        Example:
            >>> msg_type = MessageType.WARNING
            >>> msg_type.name()
            'Warning'
        """

    def __repr__(self) -> str:
        """Return the debug representation of this MessageType.

        Returns:
            A string representation suitable for debugging.
        """

    def __str__(self) -> str:
        """Return the string representation of this MessageType.

        Returns:
            The name of the message type.
        """

class MessageTarget(IntEnum):
    """Message target enumeration for routing messages.

    This enum provides various message routing targets to control where
    messages are displayed or logged.

    Attributes:
        All: Show in both GUI and CLI (value: 0).
        GuiOnly: Show only in GUI mode - legacy (value: 1).
        CliOnly: Show only in CLI mode - legacy (value: 2).
        LogOnly: Only write to log file, no display (value: 3).
        Gui: Show only in GUI mode (value: 4).
        Console: Show only in CLI mode (value: 5).

    Example:
        >>> target = MessageTarget.GUI
        >>> print(target.should_display_in_gui())
        True
        >>> print(target.value)
        4
    """

    All = 0
    GuiOnly = 1
    CliOnly = 2
    LogOnly = 3
    Gui = 4
    Console = 5

    def should_display_in_gui(self) -> bool:
        """Determines if the message should be displayed in GUI mode.

        Returns:
            True if the message should be displayed in GUI.

        Example:
            >>> target = MessageTarget.GUI
            >>> target.should_display_in_gui()
            True
        """

    def should_display_in_cli(self) -> bool:
        """Determines if the message should be displayed in CLI mode.

        Returns:
            True if the message should be displayed in CLI.

        Example:
            >>> target = MessageTarget.CONSOLE
            >>> target.should_display_in_cli()
            True
        """

    def should_display(self) -> bool:
        """Determines if the message should be displayed at all (not log-only).

        Returns:
            True if the message should be displayed.

        Example:
            >>> target = MessageTarget.ALL
            >>> target.should_display()
            True
            >>> target = MessageTarget.LOG_ONLY
            >>> target.should_display()
            False
        """

    def __repr__(self) -> str:
        """Return the debug representation of this MessageTarget.

        Returns:
            A string representation suitable for debugging.
        """

    def __str__(self) -> str:
        """Return the string representation of this MessageTarget.

        Returns:
            The name of the message target.
        """

class Message:
    """Message data structure with content, type, target, and optional metadata.

    This class provides a standardized way to handle messages with type-safe
    categorization and routing. Supports builder pattern for fluent construction.

    Attributes:
        content: The main message content.
        msg_type: The message type/severity.
        target: The message routing target.
        title: Optional message title.
        details: Optional additional details or context.

    Example:
        >>> msg = Message("Hello", MessageType.INFO)
        >>> print(msg.content())
        'Hello'
        >>> msg = msg.with_title("Greeting").with_details("User logged in")
        >>> print(msg.title())
        'Greeting'
    """

    def __init__(self, content: str, msg_type: MessageType) -> None:
        """Creates a new message with the specified content and type.

        Args:
            content: The main content of the message.
            msg_type: The type/severity of the message.

        Example:
            >>> msg = Message("Operation completed", MessageType.SUCCESS)
            >>> print(msg.content())
            'Operation completed'
        """

    @staticmethod
    def with_target(content: str, msg_type: MessageType, target: MessageTarget) -> Message:
        """Creates a new message with the specified content, type, and target.

        Args:
            content: The main content of the message.
            msg_type: The type/severity of the message.
            target: The target audience for the message.

        Returns:
            A new Message instance.

        Example:
            >>> msg = Message.with_target(
            ...     "Debug info",
            ...     MessageType.DEBUG,
            ...     MessageTarget.LOG_ONLY
            ... )
            >>> print(msg.target())
            MessageTarget.LogOnly
        """

    def with_title(self, title: str) -> Message:
        """Builder method to set the message title.

        Args:
            title: The title for the message.

        Returns:
            Self for method chaining.

        Example:
            >>> msg = Message("Content", MessageType.INFO)
            >>> msg = msg.with_title("Important")
            >>> print(msg.title())
            'Important'
        """

    def with_details(self, details: str) -> Message:
        """Builder method to set the message details.

        Args:
            details: Additional details or context for the message.

        Returns:
            Self for method chaining.

        Example:
            >>> msg = Message("Error", MessageType.ERROR)
            >>> msg = msg.with_details("Stack trace: ...")
            >>> print(msg.details())
            'Stack trace: ...'
        """

    def content(self) -> str:
        """Gets the message content.

        Returns:
            The message content.
        """

    def msg_type(self) -> MessageType:
        """Gets the message type.

        Returns:
            The message type.
        """

    def target(self) -> MessageTarget:
        """Gets the message target.

        Returns:
            The message target.
        """

    def title(self) -> str | None:
        """Gets the optional message title.

        Returns:
            The title if set, None otherwise.
        """

    def details(self) -> str | None:
        """Gets the optional message details.

        Returns:
            The details if set, None otherwise.
        """

    def set_content(self, content: str) -> None:
        """Sets the message content.

        Args:
            content: The new content for the message.
        """

    def set_msg_type(self, msg_type: MessageType) -> None:
        """Sets the message type.

        Args:
            msg_type: The new type for the message.
        """

    def set_target(self, target: MessageTarget) -> None:
        """Sets the message target.

        Args:
            target: The new target for the message.
        """

    def set_title(self, title: str | None) -> None:
        """Sets the message title.

        Args:
            title: The new title for the message, or None to clear it.
        """

    def set_details(self, details: str | None) -> None:
        """Sets the message details.

        Args:
            details: The new details for the message, or None to clear them.
        """

    def __repr__(self) -> str:
        """Return the debug representation of this Message.

        Returns:
            A string representation suitable for debugging.
        """

    def __str__(self) -> str:
        """Return the string representation of this Message.

        Returns:
            The message content.
        """

class Logger:
    """Centralized logging facility that integrates with Rust's log crate.

    This class provides a thread-safe logging interface that uses the logger
    name "CLASSIC" to match the Python logging configuration. All methods are
    thread-safe and can be called from multiple Python threads concurrently.

    Example:
        >>> logger = Logger()
        >>> logger.info("Application started")
        >>> logger.warning("Configuration file missing")
        >>> logger.error("Failed to connect to database")

    Thread Safety:
        The Logger is thread-safe and can be shared across multiple Python threads.
    """

    def __init__(self) -> None:
        """Creates a new Logger instance with the name "CLASSIC".

        Example:
            >>> logger = Logger()
            >>> print(logger.name())
            'CLASSIC'
        """

    def name(self) -> str:
        """Gets the logger name.

        Returns:
            The logger name (always "CLASSIC").

        Example:
            >>> logger = Logger()
            >>> logger.name()
            'CLASSIC'
        """

    def info(self, msg: str) -> None:
        """Logs an info-level message.

        Args:
            msg: The message to log.

        Example:
            >>> logger = Logger()
            >>> logger.info("Application initialized")
        """

    def warning(self, msg: str) -> None:
        """Logs a warning-level message.

        Args:
            msg: The message to log.

        Example:
            >>> logger = Logger()
            >>> logger.warning("Configuration file not found, using defaults")
        """

    def error(self, msg: str) -> None:
        """Logs an error-level message.

        Args:
            msg: The message to log.

        Example:
            >>> logger = Logger()
            >>> logger.error("Failed to load database")
        """

    def debug(self, msg: str) -> None:
        """Logs a debug-level message.

        Args:
            msg: The message to log.

        Example:
            >>> logger = Logger()
            >>> logger.debug("Request ID: 12345")
        """

    def trace(self, msg: str) -> None:
        """Logs a trace-level message.

        Args:
            msg: The message to log.

        Example:
            >>> logger = Logger()
            >>> logger.trace("Function entry: process_data")
        """

    def log(self, level: str, msg: str) -> None:
        """Logs a message at the specified log level.

        Args:
            level: The log level as a string ("info", "warning", "error", "debug", "trace").
            msg: The message to log.

        Raises:
            ValueError: If the level string is not recognized.

        Example:
            >>> logger = Logger()
            >>> logger.log("info", "Dynamic log level")
        """

    def log_message(self, message: Message) -> None:
        """Logs a Message instance at the appropriate log level.

        The log level is determined by the Message's MessageType.

        Args:
            message: The Message to log.

        Example:
            >>> logger = Logger()
            >>> msg = Message("Operation completed", MessageType.SUCCESS)
            >>> logger.log_message(msg)
        """

    def is_enabled_for(self, level: str) -> bool:
        """Checks if the logger is enabled for the specified log level.

        This is useful for avoiding expensive computations when the log level
        is not enabled.

        Args:
            level: The log level as a string ("info", "warning", "error", "debug", "trace").

        Returns:
            True if the logger is enabled for the specified level.

        Raises:
            ValueError: If the level string is not recognized.

        Example:
            >>> logger = Logger()
            >>> if logger.is_enabled_for("debug"):
            ...     expensive_debug_info = compute_expensive_debug_info()
            ...     logger.debug(expensive_debug_info)
        """

    def is_info_enabled(self) -> bool:
        """Checks if info-level logging is enabled.

        Returns:
            True if info-level logging is enabled.

        Example:
            >>> logger = Logger()
            >>> if logger.is_info_enabled():
            ...     logger.info("Info logging is enabled")
        """

    def is_debug_enabled(self) -> bool:
        """Checks if debug-level logging is enabled.

        Returns:
            True if debug-level logging is enabled.

        Example:
            >>> logger = Logger()
            >>> if logger.is_debug_enabled():
            ...     logger.debug("Debug logging is enabled")
        """

    def is_trace_enabled(self) -> bool:
        """Checks if trace-level logging is enabled.

        Returns:
            True if trace-level logging is enabled.

        Example:
            >>> logger = Logger()
            >>> if logger.is_trace_enabled():
            ...     logger.trace("Trace logging is enabled")
        """

def strip_emoji(text: str) -> str:
    """Strips emojis from the given text.

    This function removes all emojis and symbols within specified Unicode ranges from
    the input text. This is particularly useful for logging to avoid encoding issues
    on Windows console.

    Args:
        text: The input text string possibly containing emojis.

    Returns:
        A string with all emojis removed and whitespace trimmed.

    Example:
        >>> text = "Hello 👋 World 🌍!"
        >>> clean = strip_emoji(text)
        >>> print(clean)
        'Hello  World !'
    """

def format_log_message(content: str, details: str | None) -> str:
    """Formats a message for logging by stripping emojis from content and details.

    Args:
        content: The main message content.
        details: Optional additional details.

    Returns:
        A formatted string suitable for logging.

    Example:
        >>> formatted = format_log_message("Success! ✅", "All tests passed 🎉")
        >>> print(formatted)
        'Success!
        Details: All tests passed'
    """
