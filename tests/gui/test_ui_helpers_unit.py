"""
Unit tests for UIHelpers module.

This module tests UI helper functions and style constants for the CLASSIC interface,
including widget creation, styling, and configuration.
"""
# ruff: noqa: ANN201, ANN001, PLR6301, ARG002, ANN202, PLC2701

import os
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ClassicLib import init_message_handler
from ClassicLib.Interface.widgets.UIHelpers import (
    BOTTOM_BUTTON_STYLE,
    CHECKBOX_STYLE,
    ENABLED_BUTTON_STYLE,
    MAIN_BUTTON_STYLE,
    add_bottom_button,
    add_main_button,
    create_checkbox,
    create_separator,
    open_url,
    setup_folder_section,
    supports_add_layout,
)


@pytest.fixture(autouse=True)
def init_message_handler_fixture():
    """Initialize MessageHandler for all tests in this module."""
    # Initialize the MessageHandler to prevent RuntimeError
    init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up the global message handler after tests
    import ClassicLib.messaging

    ClassicLib.messaging._message_handler = None  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.unit
@pytest.mark.gui
class TestStyleConstants:
    """Test style constant definitions."""

    def test_style_constants_defined(self):
        """Test that all style constants are defined and non-empty."""
        assert ENABLED_BUTTON_STYLE
        assert CHECKBOX_STYLE
        assert BOTTOM_BUTTON_STYLE
        assert MAIN_BUTTON_STYLE

        # Verify they contain expected CSS properties
        assert "QPushButton" in ENABLED_BUTTON_STYLE
        assert "QCheckBox" in CHECKBOX_STYLE
        assert "border-radius" in BOTTOM_BUTTON_STYLE
        assert "font-size" in MAIN_BUTTON_STYLE


@pytest.mark.unit
@pytest.mark.gui
class TestCreateSeparator:
    """Test create_separator function."""

    def test_create_separator_returns_qframe(self, qt_application):
        """Test that create_separator returns a properly configured QFrame."""
        separator = create_separator()

        # Verify it's a QFrame
        assert isinstance(separator, QFrame)

        # Verify frame shape and shadow
        assert separator.frameShape() == QFrame.Shape.HLine
        assert separator.frameShadow() == QFrame.Shadow.Sunken


@pytest.mark.unit
@pytest.mark.gui
class TestCreateCheckbox:
    """Test create_checkbox function."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings functions."""
        with (
            patch("ClassicLib.Interface.widgets.UIHelpers.classic_settings") as mock_classic,
            patch("ClassicLib.Interface.widgets.UIHelpers.yaml_settings") as mock_yaml,
        ):
            yield mock_classic, mock_yaml

    def test_create_checkbox_with_existing_setting(self, qt_application, mock_settings):
        """Test creating checkbox with existing setting value."""
        mock_classic, _ = mock_settings
        mock_classic.return_value = True  # Existing setting is True

        checkbox = create_checkbox("Test Label", "test_setting")

        # Verify checkbox properties
        assert isinstance(checkbox, QCheckBox)
        assert checkbox.text() == "Test Label"
        assert checkbox.isChecked() is True

        # Verify setting was read
        mock_classic.assert_called_once_with(bool, "test_setting")

        # Verify style was applied
        assert CHECKBOX_STYLE in checkbox.styleSheet()

    def test_create_checkbox_without_existing_setting(self, qt_application, mock_settings):
        """Test creating checkbox when setting doesn't exist."""
        mock_classic, mock_yaml = mock_settings
        mock_classic.return_value = None  # No existing setting

        checkbox = create_checkbox("New Setting", "new_setting")

        # Verify checkbox is unchecked by default
        assert checkbox.isChecked() is False

        # Verify default setting was created
        mock_yaml.assert_called_once_with(bool, ANY, "CLASSIC_Settings.new_setting", False)

    def test_create_checkbox_state_change_updates_setting(self, qt_application, mock_settings):
        """Test that checkbox state changes update the setting."""
        mock_classic, mock_yaml = mock_settings
        mock_classic.return_value = False

        checkbox = create_checkbox("Toggle Setting", "toggle_setting")

        # Simulate checking the checkbox
        checkbox.setChecked(True)

        # Verify setting was updated
        # The connection is made with a lambda, so we need to trigger it
        checkbox.stateChanged.emit(Qt.CheckState.Checked.value)

        # Find the call that updates the setting to True
        calls = mock_yaml.call_args_list
        setting_update_call = None
        for call in calls:
            if len(call[0]) > 3 and call[0][3] is True:
                setting_update_call = call
                break

        assert setting_update_call is not None
        assert setting_update_call[0][2] == "CLASSIC_Settings.toggle_setting"

    def test_create_checkbox_custom_style(self, qt_application, mock_settings):
        """Test creating checkbox with custom style."""
        mock_classic, _ = mock_settings
        mock_classic.return_value = True

        custom_style = "QCheckBox { color: red; }"
        checkbox = create_checkbox("Styled", "styled_setting", custom_style)

        # Verify custom style was applied
        assert custom_style in checkbox.styleSheet()


@pytest.mark.unit
@pytest.mark.gui
class TestSupportsAddLayout:
    """Test supports_add_layout helper function."""

    def test_supports_add_layout_vbox(self, qt_application):
        """Test that QVBoxLayout supports addLayout."""
        layout = QVBoxLayout()
        assert supports_add_layout(layout) is True

    def test_supports_add_layout_hbox(self, qt_application):
        """Test that QHBoxLayout supports addLayout."""
        layout = QHBoxLayout()
        assert supports_add_layout(layout) is True

    def test_supports_add_layout_unsupported(self, qt_application):
        """Test that other layouts return False."""
        # Create a mock layout that's not VBox or HBox
        mock_layout = MagicMock(spec=QBoxLayout)
        mock_layout.__class__ = QBoxLayout  # pyright: ignore[reportAttributeAccessIssue]
        assert supports_add_layout(mock_layout) is False


@pytest.mark.unit
@pytest.mark.gui
class TestSetupFolderSection:
    """Test setup_folder_section function."""

    def test_setup_folder_section_creates_widgets(self, qt_application):
        """Test that folder section creates all necessary widgets."""
        layout = QVBoxLayout()
        callback = Mock()

        line_edit = setup_folder_section(layout, "Test Folder:", "test_folder", callback, "Select test folder")

        # Verify line edit was returned
        assert isinstance(line_edit, QLineEdit)
        assert line_edit.objectName() == "test_folder"

        # Verify layout has items added
        assert layout.count() > 0

        # Get the added layout
        added_layout = layout.itemAt(0).layout()
        assert isinstance(added_layout, QHBoxLayout)

        # Verify components in the horizontal layout
        assert added_layout.count() == 3  # Label, LineEdit, Button

        # Check label
        label = added_layout.itemAt(0).widget()
        assert isinstance(label, QLabel)
        assert label.text() == "Test Folder:"

        # Check button
        button = added_layout.itemAt(2).widget()
        assert isinstance(button, QPushButton)
        assert button.text() == "Browse..."
        assert button.toolTip() == "Select test folder"

    def test_setup_folder_section_button_callback(self, qt_application):
        """Test that browse button connects to callback."""
        layout = QVBoxLayout()
        callback = Mock()

        setup_folder_section(layout, "Folder:", "folder", callback)

        # Get the button
        h_layout = layout.itemAt(0).layout()
        button = h_layout.itemAt(2).widget()  # pyright: ignore[reportOptionalMemberAccess]

        # Click the button
        button.click()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]

        # Verify callback was called
        callback.assert_called_once()

    def test_setup_folder_section_default_tooltip(self, qt_application):
        """Test default tooltip generation."""
        layout = QVBoxLayout()
        callback = Mock()

        setup_folder_section(layout, "My Folder:", "my_folder", callback)

        # Get the button
        h_layout = layout.itemAt(0).layout()
        button = h_layout.itemAt(2).widget()  # pyright: ignore[reportOptionalMemberAccess]

        # Check default tooltip
        assert button.toolTip() == "Browse for my folder:"  # pyright: ignore[reportOptionalMemberAccess]

    def test_setup_folder_section_unexpected_layout_type(self, qt_application):
        """Test warning when layout type is unexpected."""
        # Create a mock layout that doesn't support addLayout
        mock_layout = MagicMock(spec=QBoxLayout)
        callback = Mock()

        with (
            patch("ClassicLib.Interface.widgets.UIHelpers.isinstance", return_value=False),
            patch("ClassicLib.Interface.widgets.UIHelpers.msg_warning") as mock_warning,
        ):
            result = setup_folder_section(mock_layout, "Test:", "test", callback)

            # Verify warning was issued
            mock_warning.assert_called_once()
            warning_msg = mock_warning.call_args[0][0]
            assert "Unexpected layout type" in warning_msg
            assert "Test:" in warning_msg

            # Should still return a QLineEdit
            assert isinstance(result, QLineEdit)


@pytest.mark.unit
@pytest.mark.gui
class TestAddMainButton:
    """Test add_main_button function."""

    def test_add_main_button_creates_styled_button(self, qt_application):
        """Test creating a main button with proper styling."""
        layout = QVBoxLayout()
        callback = Mock()

        button = add_main_button(layout, "Main Action", callback, "Do main action")

        # Verify button properties
        assert isinstance(button, QPushButton)
        assert button.text() == "Main Action"
        assert button.toolTip() == "Do main action"
        assert MAIN_BUTTON_STYLE in button.styleSheet()

        # Verify button was added to layout
        assert layout.count() == 1
        assert layout.itemAt(0).widget() == button

        # Verify size policy
        policy = button.sizePolicy()
        assert policy.horizontalPolicy() == policy.Policy.Expanding
        assert policy.verticalPolicy() == policy.Policy.Fixed

    def test_add_main_button_callback_connected(self, qt_application):
        """Test that button callback is properly connected."""
        layout = QVBoxLayout()
        callback = Mock()

        button = add_main_button(layout, "Click Me", callback)

        # Click the button
        button.click()

        # Verify callback was called
        callback.assert_called_once()

    def test_add_main_button_no_tooltip(self, qt_application):
        """Test creating button without tooltip."""
        layout = QVBoxLayout()
        callback = Mock()

        button = add_main_button(layout, "No Tooltip", callback)

        # Default tooltip should be empty
        assert not button.toolTip()


@pytest.mark.unit
@pytest.mark.gui
class TestAddBottomButton:
    """Test add_bottom_button function."""

    def test_add_bottom_button_creates_styled_button(self, qt_application):
        """Test creating a bottom button with inline styling."""
        layout = QVBoxLayout()
        callback = Mock()

        add_bottom_button(layout, "Bottom Action", callback, "Bottom tooltip")

        # Verify button was added
        assert layout.count() == 1
        button = layout.itemAt(0).widget()

        assert isinstance(button, QPushButton)
        assert button.text() == "Bottom Action"
        assert button.toolTip() == "Bottom tooltip"

        # Verify inline style (not using constant)
        style = button.styleSheet()
        assert "rgba(10, 10, 10, 0.75)" in style
        assert "min-height: 38px" in style

    def test_add_bottom_button_callback_connected(self, qt_application):
        """Test that bottom button callback works."""
        layout = QVBoxLayout()
        callback = Mock()

        add_bottom_button(layout, "Test", callback)

        button = layout.itemAt(0).widget()
        button.click()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]

        callback.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestOpenUrl:
    """Test open_url function."""

    def test_open_url_calls_desktop_services(self):
        """Test that open_url properly calls QDesktopServices."""
        with patch("ClassicLib.Interface.widgets.UIHelpers.QDesktopServices.openUrl") as mock_open:
            test_url = "https://example.com"
            open_url(test_url)

            # Verify openUrl was called
            mock_open.assert_called_once()

            # Verify QUrl was created with correct URL
            call_args = mock_open.call_args[0]
            qurl = call_args[0]
            assert isinstance(qurl, QUrl)
            assert qurl.toString() == test_url

    def test_open_url_various_protocols(self):
        """Test opening URLs with various protocols."""
        with patch("ClassicLib.Interface.widgets.UIHelpers.QDesktopServices.openUrl") as mock_open:
            urls = ["http://example.com", "https://secure.example.com", "file:///C:/path/to/file.txt", "mailto:test@example.com"]

            for url in urls:
                mock_open.reset_mock()
                open_url(url)

                mock_open.assert_called_once()
                qurl = mock_open.call_args[0][0]
                assert url in qurl.toString()


@pytest.mark.unit
@pytest.mark.gui
class TestIntegrationScenarios:
    """Integration tests for UI helpers working together."""

    def test_complete_form_section(self, qt_application):
        """Test creating a complete form section with multiple helpers."""
        main_layout = QVBoxLayout()

        # Add separator
        separator1 = create_separator()
        main_layout.addWidget(separator1)

        # Add folder section
        folder_callback = Mock()
        folder_edit = setup_folder_section(main_layout, "Output Folder:", "output_folder", folder_callback)

        # Add separator
        separator2 = create_separator()
        main_layout.addWidget(separator2)

        # Add checkbox
        with patch("ClassicLib.Interface.widgets.UIHelpers.classic_settings", return_value=True):
            checkbox = create_checkbox("Enable Feature", "feature_enabled")
            main_layout.addWidget(checkbox)

        # Add main button
        main_callback = Mock()
        main_button = add_main_button(main_layout, "Process", main_callback)

        # Add bottom button
        help_callback = Mock()
        add_bottom_button(main_layout, "Help", help_callback)

        # Verify all components were added
        assert main_layout.count() >= 6  # All widgets/layouts added

        # Verify components work
        folder_edit.setText("/test/path")  # pyright: ignore[reportOptionalMemberAccess]
        assert folder_edit.text() == "/test/path"  # pyright: ignore[reportOptionalMemberAccess]

        assert checkbox.isChecked() is True

        main_button.click()
        main_callback.assert_called_once()

    def test_size_policies_consistency(self, qt_application):
        """Test that size policies are consistent across helpers."""
        layout = QVBoxLayout()

        # Create various buttons
        main_button = add_main_button(layout, "Main", Mock())
        add_bottom_button(layout, "Bottom", Mock())

        # Both should have expanding horizontal policy
        main_policy = main_button.sizePolicy()
        bottom_button = layout.itemAt(1).widget()
        bottom_policy = bottom_button.sizePolicy()  # pyright: ignore[reportOptionalMemberAccess]

        assert main_policy.horizontalPolicy() == main_policy.Policy.Expanding
        assert bottom_policy.horizontalPolicy() == bottom_policy.Policy.Expanding
