import re
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from ClassicLib.Interface.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from ClassicLib.Interface.ThreadManager import ThreadManager


class PastebinMixin:
    """
    Mixin class providing Pastebin log fetching functionality for the MainWindow.

    This class requires the following attributes to be present in the class it's mixed into:
    - thread_manager: ThreadManager instance
    - pastebin_thread: QThread for Pastebin operations
    - pastebin_worker: PastebinFetchWorker instance
    - pastebin_id_input: QLineEdit for user input
    - pastebin_label: QLabel for instructions
    - pastebin_fetch_button: QPushButton for fetch action
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        thread_manager: ThreadManager
        pastebin_thread: QThread | None
        pastebin_worker: PastebinFetchWorker | None
        pastebin_id_input: QLineEdit
        pastebin_label: QLabel
        pastebin_fetch_button: QPushButton

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the PastebinMixin with required patterns."""
        super().__init__(*args, **kwargs)
        self.pastebin_url_regex: re.Pattern = re.compile(r"^https?://pastebin\.com/(\w+)$")

    def setup_pastebin_elements(self, layout: QVBoxLayout) -> None:
        """
        Set up the UI elements to fetch logs from Pastebin and add them to the provided layout.

        This method initializes and configures UI components, including a QLabel for Pastebin
        instructions, a QLineEdit for Pastebin URL or ID input, and a QPushButton to trigger
        the fetch operation. These components are arranged in a horizontal layout before
        being added to the parent vertical layout.

        Args:
            layout (QVBoxLayout): The parent layout to which the Pastebin elements are added.
        """
        pastebin_layout: QHBoxLayout = QHBoxLayout()

        self.pastebin_label = QLabel("PASTEBIN LOG FETCH")
        self.pastebin_label.setToolTip("Fetch a log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_label)

        pastebin_layout.addSpacing(50)

        self.pastebin_id_input = QLineEdit()
        self.pastebin_id_input.setPlaceholderText("Enter Pastebin URL or ID")
        self.pastebin_id_input.setToolTip("Enter the Pastebin URL or ID to fetch the log. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_id_input)

        self.pastebin_fetch_button = QPushButton("Fetch Log")
        self.pastebin_fetch_button.clicked.connect(self.fetch_pastebin_log)
        if self.pastebin_id_input:  # Ensure pastebin_id_input is not None
            self.pastebin_fetch_button.clicked.connect(self.pastebin_id_input.clear)
        self.pastebin_fetch_button.setToolTip("Fetch the log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_fetch_button)

        layout.addLayout(pastebin_layout)

    def fetch_pastebin_log(self) -> None:
        """
            Fetches a log from a Pastebin URL or ID provided by the user and processes it in a separate thread
            using asynchronous operations.

            This method retrieves the text from a user input field, verifies if it matches a Pastebin URL pattern,
            or formats it into a valid Pastebin URL if an ID is provided. It then sets up a separate thread and a
            worker object to handle the fetching process asynchronously using the pastebin_fetch_async function,
            ensuring the main application's UI remains responsive. User feedback is provided through message boxes
            based on the success or failure of the log retrieval process.

        Raises:
            SignalErrors: Raised when the worker encounters an error during network operations or data processing.

        Returns:
            None
        """
        if self.pastebin_id_input is None:
            return  # Should not happen if UI is setup correctly

        input_text: str = self.pastebin_id_input.text().strip()
        url: str = input_text if self.pastebin_url_regex.match(input_text) else f"https://pastebin.com/{input_text}"

        # Create thread and worker
        # Check if a fetch is already in progress
        if self.thread_manager.is_thread_running(ThreadType.PASTEBIN_FETCH):
            QMessageBox.warning(self, "Fetch in Progress", "A Pastebin fetch is already in progress. Please wait for it to complete.")
            return

        # Create new thread and worker for each fetch operation to prevent thread reuse
        self.pastebin_thread = QThread()
        self.pastebin_worker = PastebinFetchWorker(url)
        self.pastebin_worker.moveToThread(self.pastebin_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.PASTEBIN_FETCH, self.pastebin_thread, self.pastebin_worker):
            logger.error("Failed to register Pastebin fetch thread")
            return

        # Connect signals
        self.pastebin_thread.started.connect(self.pastebin_worker.run)
        self.pastebin_worker.finished.connect(self.pastebin_thread.quit)
        self.pastebin_worker.finished.connect(self.pastebin_worker.deleteLater)
        self.pastebin_thread.finished.connect(self.pastebin_thread.deleteLater)

        # Clean up thread reference when done to allow garbage collection
        self.pastebin_thread.finished.connect(lambda: setattr(self, "pastebin_thread", None))
        self.pastebin_thread.finished.connect(lambda: setattr(self, "pastebin_worker", None))

        # Use lambdas or functools.partial if arguments need to be passed to slots
        self.pastebin_worker.success.connect(lambda pb_source: QMessageBox.information(self, "Success", f"Log fetched from: {pb_source}"))
        self.pastebin_worker.error.connect(lambda err: QMessageBox.warning(self, "Error", f"Failed to fetch log: {err}"))

        # Start through thread manager
        self.thread_manager.start_thread(ThreadType.PASTEBIN_FETCH)
