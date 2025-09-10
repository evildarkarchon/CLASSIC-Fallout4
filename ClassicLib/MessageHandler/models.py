"""Data models for the MessageHandler system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .enums import MessageTarget, MessageType

if TYPE_CHECKING:
    # Try to import PySide6 for GUI mode
    try:
        from PySide6.QtWidgets import QWidget
    except ImportError:
        # Define dummy class for type checking when Qt is not available
        class QWidget:
            pass


@dataclass
class Message:
    """Container for a message with its metadata."""

    content: str
    msg_type: MessageType
    target: MessageTarget = MessageTarget.ALL
    title: str | None = None
    details: str | None = None
    parent: QWidget | None = None
