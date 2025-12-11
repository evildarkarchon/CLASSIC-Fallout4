"""Helper functions for properly mocking Qt classes in tests."""

from unittest.mock import MagicMock

from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


def create_layout_mock_factory(base_class):
    """
    Create a factory that returns mock instances while preserving the class for union checks.

    This approach keeps the original class reference for union type operations
    while returning mock instances when the class is instantiated.
    """

    def mock_factory(*args, **kwargs):
        """Factory function that returns a mock instance."""
        mock = MagicMock()
        # Set the __class__ so isinstance checks work
        mock.__class__ = base_class
        mock.addLayout = MagicMock()
        mock.addWidget = MagicMock()
        mock.addSpacing = MagicMock()
        mock.setSpacing = MagicMock()
        return mock

    # Return the factory function directly
    return mock_factory


def create_qt_widget_mock(spec_class=QWidget):
    """
    Create a mock widget that PySide6 layouts can accept as a parent.

    This creates a mock that mimics enough of the Qt meta-object system
    to be accepted by PySide6 constructors.
    """
    mock = MagicMock(spec=spec_class)
    # Add required Qt meta-object attributes
    mock._qt_object = True
    mock.__class__ = spec_class  # pyright: ignore[reportAttributeAccessIssue]
    return mock


def create_button_mock(text="", checkable=False):
    """Create a mock QPushButton with common properties set."""
    button = MagicMock(spec=QPushButton)
    button.text.return_value = text
    button.isCheckable.return_value = checkable
    button.setCheckable = MagicMock()
    button.setStyleSheet = MagicMock()
    button.setToolTip = MagicMock()
    button.clicked = MagicMock()
    button.clicked.connect = MagicMock()
    return button


def create_mock_layout_with_union_support():
    """
    Create a mock layout that works with isinstance union checks.

    Returns a mock that:
    1. Has all the methods of a QBoxLayout
    2. Passes isinstance checks for QVBoxLayout | QHBoxLayout
    """
    mock = MagicMock()
    # Make it pass isinstance checks by setting __class__
    mock.__class__ = QVBoxLayout  # pyright: ignore[reportAttributeAccessIssue]
    mock.addLayout = MagicMock()
    mock.addWidget = MagicMock()
    mock.addSpacing = MagicMock()
    mock.setSpacing = MagicMock()
    return mock
