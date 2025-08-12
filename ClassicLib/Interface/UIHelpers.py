"""
UI helper functions and style constants for the CLASSIC interface.

This module contains utility methods for creating UI components and style definitions.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import msg_warning
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Style constants
ENABLED_BUTTON_STYLE = """
    QPushButton {
        color: black;
        background: rgb(250, 250, 250);
        border-radius: 10px;
        border: 2px solid black;
    }
"""

CHECKBOX_STYLE = """
    QCheckBox {
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 25px;
        height: 25px;
    }
    QCheckBox::indicator:unchecked {
        image: url("CLASSIC Data/graphics/unchecked.svg");
    }
    QCheckBox::indicator:checked {
        image: url("CLASSIC Data/graphics/checked.svg");
    }
"""

BOTTOM_BUTTON_STYLE = """
    QPushButton {
        color: white;
        background: rgba(60, 60, 60, 0.9);
        border-radius: 5px;
        border: 1px solid #5c5c5c;
        font-size: 11px;
        padding: 6px 10px;
        min-height: 30px;
    }
    QPushButton:hover { background-color: rgba(80, 80, 80, 0.9); }
    QPushButton:pressed { background-color: rgba(40, 40, 40, 0.9); }
"""

MAIN_BUTTON_STYLE = """
    QPushButton {
        color: black;
        background: rgba(250, 250, 250, 0.90);
        border-radius: 10px;
        border: 1px solid white;
        font-size: 17px;
        font-weight: bold;
        min-height: 48px;
        max-height: 48px;
    }
    QPushButton:disabled {
        color: gray;
        background-color: rgba(10, 10, 10, 0.75);
    }
"""


def create_separator() -> QFrame:
    """
    Creates a horizontal line separator widget.

    Returns:
        QFrame: A QFrame object configured as a horizontal line separator with a sunken shadow.
    """
    separator: QFrame = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    return separator


def create_checkbox(label_text: str, setting: str, style: str = CHECKBOX_STYLE) -> QCheckBox:
    """
    Creates a styled QCheckBox widget linked to a specific setting and its state.

    Args:
        label_text (str): The text label to display next to the checkbox.
        setting (str): The name of the setting to bind with the checkbox.
        style (str): Optional custom style for the checkbox. Defaults to CHECKBOX_STYLE.

    Returns:
        QCheckBox: A QCheckBox widget connected to the specified setting's state.
    """
    checkbox: QCheckBox = QCheckBox(label_text)

    # Initialize checkbox state from settings or create default
    value: bool | None = classic_settings(bool, setting)
    if value is None:
        value = False
        yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", False)

    checkbox.setChecked(value)

    # Connect state change to settings update
    checkbox.stateChanged.connect(lambda state: yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", bool(state)))

    checkbox.setStyleSheet(style)
    return checkbox


def setup_folder_section(
    layout: QBoxLayout, title: str, box_name: str, browse_callback: Callable[[], None], tooltip: str = ""
) -> QLineEdit | None:
    """
    Sets up a folder selection section within a provided layout. This method creates a section
    consisting of a label, a QLineEdit for folder path input, and a browse button. Clicking the
    browse button triggers a callback function specified by the user.

    Args:
        layout (QBoxLayout): The layout to which the folder section will be added.
        title (str): The text to display in the label.
        box_name (str): The object name of the QLineEdit, used for identification.
        browse_callback (Callable[[], None]): The function to execute when the browse button is clicked.
        tooltip (str, optional): The tooltip text to display when hovering over the browse button. Defaults to an empty string.

    Returns:
        QLineEdit: The QLineEdit widget created for folder input.
    """
    section_layout: QHBoxLayout = QHBoxLayout()
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.setSpacing(5)

    label: QLabel = QLabel(title)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    section_layout.addWidget(label)

    line_edit: QLineEdit = QLineEdit()
    line_edit.setObjectName(box_name)
    line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
    section_layout.addWidget(line_edit)

    browse_button: QPushButton = QPushButton("Browse...")  # Shorter text
    browse_button.setToolTip(tooltip if tooltip else f"Browse for {title.lower()}")
    browse_button.clicked.connect(browse_callback)
    browse_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    section_layout.addWidget(browse_button)

    # Add the QHBoxLayout to the parent QVBoxLayout (or other QBoxLayout)
    if isinstance(layout, QVBoxLayout | QHBoxLayout):
        layout.addLayout(section_layout)
    else:
        # Fallback if layout type is unexpected, though typically it's one of these.
        # This might indicate a need to adjust how sections are added.
        msg_warning(f"Unexpected layout type ({type(layout)}) for folder section '{title}'")

    return line_edit


def add_main_button(layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton:
    """
    Adds a main button to the specified layout with the given text, click callback, and optional tooltip.

    This method creates a QPushButton with a specific style and behavior. The button's text, callback, and optional
    tooltip can be customized. It is then added to the provided layout and returned.

    Args:
        layout (QLayout): The layout to which the button will be added.
        text (str): The text to display on the button.
        callback (Callable[[], None]): The function to be called when the button is clicked.
        tooltip (str, optional): The tooltip text to display on hover. Defaults to an empty string.

    Returns:
        QPushButton: The created button that has been added to the layout.
    """
    button: QPushButton = QPushButton(text)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    button.setStyleSheet(MAIN_BUTTON_STYLE)
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    layout.addWidget(button)
    return button


def add_bottom_button(layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> None:
    """
    Adds a configurable button to the bottom of a given layout. The button adopts a specific
    styling, size policy, and allows optional tooltip text. A callback function is associated
    with the button's "clicked" event to define its behavior when clicked.

    Args:
        layout (QLayout): The layout where the button should be added.
        text (str): The text to display on the button.
        callback (Callable[[], None]): The function to invoke when the button is clicked.
        tooltip (str, optional): The tooltip text to display when hovering over the button.
            Defaults to an empty string.
    """
    button: QPushButton = QPushButton(text)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    button.setStyleSheet(
        """
        color: white;
        background: rgba(10, 10, 10, 0.75);
        border-radius: 10px;
        border: 1px solid white;
        font-size: 11px;
        min-height: 38px;
        max-height: 38px;
    """
    )
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    layout.addWidget(button)


def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton:  # noqa: ANN001, ARG001
    """
    Creates and configures a button with common styling and properties.

    Args:
        text: The button text
        tooltip: The button tooltip
        callback: Function to call when button is clicked

    Returns:
        Configured QPushButton instance
    """
    button: QPushButton = QPushButton(text)
    button.setToolTip(tooltip)

    # Connect appropriate signal based on whether it's a toggle button or regular
    if isinstance(button, QPushButton) and button.isCheckable():
        button.toggled.connect(callback)
    else:
        button.clicked.connect(callback)

    # Apply common styling
    button.setStyleSheet(BOTTOM_BUTTON_STYLE)
    button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    return button


def open_url(url: str) -> None:
    """
    Opens the specified URL in the default web browser.

    Args:
        url (str): The URL to open in the browser.
    """
    QDesktopServices.openUrl(QUrl(url))
