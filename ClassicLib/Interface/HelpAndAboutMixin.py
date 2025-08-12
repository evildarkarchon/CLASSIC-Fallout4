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
    Mixin class providing "Help" and "About" dialog functionality for the MainWindow.
    """

    # noinspection PyUnresolvedReferences
    def show_about(self) -> None:
        """
        Displays the "About" dialog for the application by initializing and executing
        a custom dialog window.

        This method creates an instance of the `CustomAboutDialog` class, passing the
        current instance (self) as an argument. It then displays the dialog window
        modally by invoking the `exec()` method on the dialog instance.

        Returns:
            None
        """
        dialog: CustomAboutDialog = CustomAboutDialog(self)
        dialog.exec()

    def help_popup_main(self) -> None:
        """
        Displays a help popup with information retrieved from the YAML settings.

        The method retrieves the help text from the YAML configuration file under
        the specified key. It then displays the retrieved text in a message box
        with a title and an "OK" button.

        Returns:
            None
        """
        help_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.help_popup_main") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok)
