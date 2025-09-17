"""
Defines a data structure for managing messages and their associated metadata.

This module provides a `Message` class for encapsulating message content,
type, target, optional metadata such as title and details, and an optional
parent widget for GUI context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ClassicLib.MessageHandler.enums import MessageTarget, MessageType

if TYPE_CHECKING:
    # Try to import PySide6 for GUI mode
    try:
        from PySide6.QtWidgets import QWidget
    except ImportError:
        # Define dummy class for type checking when Qt is not available
        class QWidget:  # noqa: D101
            pass


@dataclass
class Message:
    """
    Represents a message with various attributes for content, type, target, and optional metadata.

    This data class is used to structure message data, including its content, type, target audience,
    and optional attributes such as title, additional details, and an associated parent widget.
    It provides a standardized way to handle messages across different components or systems.

    Attributes:
        content (str): The core content or body of the message.
        msg_type (MessageType): The type or category of the message.
        target (MessageTarget): The intended audience or target for the message.
        title (str | None): An optional title for the message.
        details (str | None): Additional details or context related to the message.
        parent (QWidget | None): The optional parent widget associated with the message.
    """

    content: str
    msg_type: MessageType
    target: MessageTarget = MessageTarget.ALL
    title: str | None = None
    details: str | None = None
    parent: QWidget | None = None
