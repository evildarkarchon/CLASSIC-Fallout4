"""Help and About dialog controller for CLASSIC interface.

This module provides the HelpAboutController class that handles displaying
help information and about dialogs to users.

Example:
    >>> from ClassicLib.Interface.controllers.help_about import HelpAboutController
    >>> help_ctrl = HelpAboutController(context)
    >>> help_ctrl.show_about()

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from ClassicLib.core.constants import YAML
from ClassicLib.Interface.dialogs.Dialogs import CustomAboutDialog
from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.io.yaml import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.Interface.shared.context import FeatureContext


class HelpAboutController:
    """Controller for help and about dialog functionality.

    This controller handles displaying the "About" dialog with application
    information and help popups with usage guidance.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.

    Example:
        >>> controller = HelpAboutController(context)
        >>> controller.show_about()  # Shows about dialog
        >>> controller.help_popup_main()  # Shows help dialog

    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the HelpAboutController.

        Args:
            context: FeatureContext providing access to main_window and signal_hub.

        """
        self._ctx = context

    def show_about(self) -> None:
        """Display the "About" dialog.

        Shows a custom dialog containing application version, credits,
        and other relevant information about CLASSIC.
        """
        dialog = CustomAboutDialog(self._ctx.main_window)
        dialog.exec()

    def help_popup_main(self) -> None:
        """Display a help dialog with main interface guidance.

        Retrieves help text from YAML settings and displays it in a
        modal information dialog. The help text provides guidance on
        using the main CLASSIC interface features.
        """
        help_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.help_popup_main") or ""
        QMessageBox.information(
            self._ctx.main_window,
            "NEED HELP?",
            help_popup_text,
            QMessageBox.StandardButton.Ok,
        )

    def open_settings(self) -> None:
        """Open the settings dialog.

        Displays the settings dialog and applies any changes if the user
        accepts the dialog.
        """
        dialog = SettingsDialog(self._ctx.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Emit signal to notify that settings may have changed
            self._ctx.signal_hub.settings_changed.emit()
