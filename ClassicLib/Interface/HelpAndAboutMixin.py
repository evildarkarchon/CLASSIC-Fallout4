"""
Help and About dialog functionality for the CLASSIC interface.

This module contains a mixin class that handles the "About" and "Help" dialogs.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Dialogs import CustomAboutDialog
from ClassicLib.YamlSettingsCache import yaml_settings


class HelpAndAboutMixin:
    """
    Provides mixin functionality for displaying "About" information and help popups
    in the application.

    This mixin class includes methods to show an "About" dialog and a help popup,
    both used to enhance user interaction by providing helpful information about
    the application.

    Attributes:
        No public attributes available in this class.
    """

    # noinspection PyUnresolvedReferences
    def show_about(self) -> None:
        """
        Displays the "About" dialog.

        This method initializes and displays a custom "About" dialog using the
        CustomAboutDialog class. It does not return any value.

        Args:
            self: The instance of the class.
        """
        dialog: CustomAboutDialog = CustomAboutDialog(self) # pyright: ignore[reportArgumentType]
        dialog.exec()

    def help_popup_main(self) -> None:
        """
        Displays a help dialog with information related to the main interface.

        This method accesses a YAML settings file to retrieve the help text associated
        with the main interface. It then displays this information in a modal dialog
        using a QMessageBox.

        Args:
            self: Reference to the current instance of the class.
        """
        help_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.help_popup_main") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok) # pyright: ignore[reportArgumentType]
