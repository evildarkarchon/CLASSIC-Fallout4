"""Pastebin fetch controller for CLASSIC interface.

This module provides the PastebinController class that handles fetching
crash logs from Pastebin URLs.

Example:
    >>> from ClassicLib.Interface.controllers.pastebin_controller import PastebinController
    >>> pastebin_ctrl = PastebinController(context)
    >>> pastebin_ctrl.fetch_pastebin_log()
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ClassicLib.Interface.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from ClassicLib.Interface.context import FeatureContext


class PastebinController:
    """Controller for Pastebin log fetching functionality.

    This controller manages fetching crash logs from Pastebin URLs:
    - Creating UI elements for Pastebin input
    - Validating Pastebin URLs/IDs
    - Fetching logs in a background thread
    - Displaying success/error messages

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _pastebin_url_regex: Compiled regex for validating Pastebin URLs.
        _pastebin_thread: Current fetch thread (or None).
        _pastebin_worker: Current fetch worker (or None).

    Example:
        >>> controller = PastebinController(context)
        >>> controller.setup_pastebin_elements(layout)
        >>> controller.fetch_pastebin_log()
    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the PastebinController.

        Args:
            context: FeatureContext providing access to main_window, thread_manager,
                and ui_widgets.
        """
        self._ctx = context
        self._pastebin_url_regex: re.Pattern[str] = re.compile(r"^https?://pastebin\.com/(\w+)$")
        self._pastebin_thread: QThread | None = None
        self._pastebin_worker: PastebinFetchWorker | None = None

    def setup_pastebin_elements(self, layout: QVBoxLayout) -> None:
        """Set up UI elements for Pastebin log fetching.

        Creates and adds to the layout:
        - A label describing the feature
        - A text input for Pastebin URL/ID
        - A button to trigger the fetch

        Args:
            layout: The parent layout to add elements to.
        """
        pastebin_layout = QHBoxLayout()

        # Label
        pastebin_label = QLabel("PASTEBIN LOG FETCH")
        pastebin_label.setToolTip("Fetch a log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(pastebin_label)
        self._ctx.ui_widgets.pastebin_label = pastebin_label

        pastebin_layout.addSpacing(50)

        # Input field
        pastebin_id_input = QLineEdit()
        pastebin_id_input.setPlaceholderText("Enter Pastebin URL or ID")
        pastebin_id_input.setToolTip("Enter the Pastebin URL or ID to fetch the log.")
        pastebin_layout.addWidget(pastebin_id_input)
        self._ctx.ui_widgets.pastebin_id_input = pastebin_id_input

        # Fetch button
        pastebin_fetch_button = QPushButton("Fetch Log")
        pastebin_fetch_button.clicked.connect(self.fetch_pastebin_log)
        pastebin_fetch_button.clicked.connect(pastebin_id_input.clear)
        pastebin_fetch_button.setToolTip("Fetch the log file from Pastebin.")
        pastebin_layout.addWidget(pastebin_fetch_button)
        self._ctx.ui_widgets.pastebin_fetch_button = pastebin_fetch_button

        layout.addLayout(pastebin_layout)

    def fetch_pastebin_log(self) -> None:
        """Fetch a log from the entered Pastebin URL or ID.

        Validates the input, constructs the full URL if needed, and
        starts a background thread to fetch the log content.
        """
        pastebin_id_input = self._ctx.ui_widgets.pastebin_id_input
        if pastebin_id_input is None:
            return

        input_text: str = pastebin_id_input.text().strip()
        if not input_text:
            return

        # Construct URL from input
        if self._pastebin_url_regex.match(input_text):
            url = input_text
        else:
            url = f"https://pastebin.com/{input_text}"

        # Check if a fetch is already in progress
        if self._ctx.thread_manager.is_thread_running(ThreadType.PASTEBIN_FETCH):
            QMessageBox.warning(
                self._ctx.main_window,
                "Fetch in Progress",
                "A Pastebin fetch is already in progress. Please wait for it to complete.",
            )
            return

        # Create new thread and worker
        self._pastebin_thread = QThread()
        self._pastebin_worker = PastebinFetchWorker(url)
        self._pastebin_worker.moveToThread(self._pastebin_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.PASTEBIN_FETCH,
            self._pastebin_thread,
            self._pastebin_worker,
        ):
            logger.error("Failed to register Pastebin fetch thread")
            return

        # Connect signals
        self._pastebin_thread.started.connect(self._pastebin_worker.run)
        self._pastebin_worker.finished.connect(self._pastebin_thread.quit)
        self._pastebin_worker.finished.connect(self._pastebin_worker.deleteLater)
        self._pastebin_thread.finished.connect(self._pastebin_thread.deleteLater)

        # Clean up references when done
        self._pastebin_thread.finished.connect(self._cleanup_thread_refs)

        # Connect result signals
        self._pastebin_worker.success.connect(self._on_fetch_success)
        self._pastebin_worker.error.connect(self._on_fetch_error)

        # Start through thread manager
        self._ctx.thread_manager.start_thread(ThreadType.PASTEBIN_FETCH)

    def _cleanup_thread_refs(self) -> None:
        """Clean up thread and worker references after completion."""
        self._pastebin_thread = None
        self._pastebin_worker = None

    def _on_fetch_success(self, pb_source: str) -> None:
        """Handle successful Pastebin fetch.

        Args:
            pb_source: The source URL that was fetched.
        """
        QMessageBox.information(
            self._ctx.main_window,
            "Success",
            f"Log fetched from: {pb_source}",
        )

    def _on_fetch_error(self, error_message: str) -> None:
        """Handle Pastebin fetch error.

        Args:
            error_message: Description of the error.
        """
        QMessageBox.warning(
            self._ctx.main_window,
            "Error",
            f"Failed to fetch log: {error_message}",
        )
