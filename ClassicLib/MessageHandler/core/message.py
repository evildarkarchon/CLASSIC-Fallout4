"""Message data structure for the MessageHandler system.

This module provides the Message dataclass for encapsulating message content,
type, target, and optional metadata such as title, details, and parent widget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


@dataclass
class Message:
    """Message data structure with content, type, target, and optional metadata.

    Attributes:
        content: The core content or body of the message.
        msg_type: The type or category of the message.
        target: The intended audience or target for the message.
        title: An optional title for the message.
        details: Additional details or context related to the message.
        parent: The optional parent widget associated with the message (GUI only).

    """

    content: str
    msg_type: MessageType
    target: MessageTarget = field(default=MessageTarget.ALL)
    title: str | None = field(default=None)
    details: str | None = field(default=None)
    parent: QWidget | Any | None = field(default=None)

    def with_title(self, title: str) -> Message:
        """Create a copy with a new title.

        Args:
            title: The title to set.

        Returns:
            New Message with the title set.

        """
        return Message(
            content=self.content,
            msg_type=self.msg_type,
            target=self.target,
            title=title,
            details=self.details,
            parent=self.parent,
        )

    def with_details(self, details: str) -> Message:
        """Create a copy with new details.

        Args:
            details: The details to set.

        Returns:
            New Message with the details set.

        """
        return Message(
            content=self.content,
            msg_type=self.msg_type,
            target=self.target,
            title=self.title,
            details=details,
            parent=self.parent,
        )

    def get_display_title(self) -> str:
        """Get the title to display, falling back to message type name.

        Returns:
            Title string for display.

        """
        if self.title:
            return self.title
        return self.msg_type.name.title()
