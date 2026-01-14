"""UI helper functions and style constants for the CLASSIC interface.

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
from ClassicLib.YamlSettings import classic_settings, yaml_settings

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
    QPushButton:hover {
        background-color: rgba(230, 230, 230, 0.95);
        border: 1px solid #cccccc;
    }
    QPushButton:pressed {
        background-color: rgba(200, 200, 200, 0.95);
        border: 1px solid #999999;
    }
    QPushButton:disabled {
        color: gray;
        background-color: rgba(10, 10, 10, 0.75);
    }
"""


def create_separator() -> QFrame:
    """Create and returns a horizontal line separator.

    This function creates a QFrame widget configured to represent
    a horizontal line separator with a sunken shadow.

    Returns:
        QFrame: The QFrame instance configured as a horizontal line separator.

    """
    separator: QFrame = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    return separator


def create_checkbox(label_text: str, setting: str, style: str = CHECKBOX_STYLE) -> QCheckBox:
    """Create a QCheckBox with specified label text, initializes its state based on provided
    settings, and applies a given style.

    The checkbox state is synchronized with the settings dynamically. If the initial state
    is not found in the settings, a default value is used and updated in the settings.

    Args:
        label_text (str): The text to display alongside the QCheckBox.
        setting (str): The key name used to retrieve and store the checkbox state
            in the settings.
        style (str, optional): The stylesheet to apply to the checkbox. Defaults
            to CHECKBOX_STYLE.

    Returns:
        QCheckBox: A checkbox widget initialized with the specified label, style,
        and linked to the settings.

    """
    checkbox: QCheckBox = QCheckBox(label_text)

    # Initialize checkbox state from settings or create default
    value: bool | None = classic_settings(bool, setting)
    if value is None:
        value = False
        yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", False)

    checkbox.setChecked(value)

    # Connect state change to settings update
    checkbox.stateChanged.connect(lambda state: yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", bool(state)))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

    checkbox.setStyleSheet(style)
    return checkbox


def supports_add_layout(layout: QLayout) -> bool:
    """Check if the given layout is supported.

    This function verifies whether the provided layout is an instance of QVBoxLayout
    or QHBoxLayout, effectively determining if it is a supported type of layout.

    Args:
        layout: The layout to be checked, provided as an instance of QLayout.

    Returns:
        bool: True if the layout is supported (QVBoxLayout or QHBoxLayout).
        False otherwise.

    """
    return isinstance(layout, (QVBoxLayout, QHBoxLayout))


def setup_folder_section(
    layout: QBoxLayout, title: str, box_name: str, browse_callback: Callable[[], None], tooltip: str = ""
) -> QLineEdit | None:
    """Set up a folder selection section within the provided layout using a label, line edit,
    and a browse button. This creates a horizontal arrangement of these widgets which
    is added into the given parent layout (usually a QVBoxLayout or QHBoxLayout).

    Args:
        layout (QBoxLayout): The parent layout where the folder section should be added.
                             Typically a vertical or horizontal box layout.
        title (str): The text to display on the label.
        box_name (str): The object name to assign to the QLineEdit widget for identification.
        browse_callback (Callable[[], None]): A callback function to handle actions when the
                                              browse button is clicked.
        tooltip (str, optional): An optional tooltip for the browse button. If not provided,
                                 a default tooltip based on the label title is generated.

    Returns:
        QLineEdit | None: Returns the QLineEdit widget created for the folder input, or None
                          if the provided layout type is not expected.

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
    browse_button.setToolTip(tooltip or f"Browse for {title.lower()}")
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
    """Add a main button to the specified layout with customizable appearance and behavior.

    This function creates a QPushButton with a predefined style and size policy,
    sets its tooltip if provided, connects it to a callback, and adds it to the
    given layout.

    Args:
        layout (QLayout): The layout where the button will be added as a widget.
        text (str): The text to be displayed on the button.
        callback (Callable[[], None]): The function to be executed when the button is
            clicked.
        tooltip (str, optional): The tooltip text to be displayed on hover. Defaults
            to an empty string.

    Returns:
        QPushButton: The created QPushButton instance.

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
    """Add a styled button to the specified layout. The button expands horizontally, has a fixed
    height, and a custom visual appearance. Optionally, a tooltip can be added to the button.

    Args:
        layout: The layout to which the button will be added.
        text: The text displayed on the button.
        callback: The function to be triggered when the button is clicked.
        tooltip: Optional tooltip text for the button.

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


def open_url(url: str) -> None:
    """Open a given URL in the default system web browser.

    This function utilizes the QDesktopServices class from the Qt framework to
    open the specified URL. It ensures that the URL is parsed and handled using
    the QUrl class before being opened. It does not return any value.

    Args:
        url (str): The URL to be opened in the default web browser.

    """
    QDesktopServices.openUrl(QUrl(url))
