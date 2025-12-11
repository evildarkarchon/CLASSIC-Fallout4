"""Qt/PySide6 fixtures for GUI testing."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from ClassicLib.MessageHandler.qt_handler import QtMessageHandler


@pytest.fixture(scope="session", autouse=True)
def qt_application_session():
    """
    Session-scoped QApplication management.

    This fixture ensures:
    - A single QApplication instance for the entire test session
    - Proper cleanup at the end of all tests
    - Prevents app.quit() from being called between tests
    """
    from PySide6.QtWidgets import QApplication

    # Create or get QApplication for the session
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    # Clean up at the end of the session
    if app:
        app.quit()
        app.deleteLater()
        # Process events to ensure deletion
        try:
            app.processEvents()
        except:
            pass  # App may already be deleted


@pytest.fixture(scope="function")
def qt_application(qt_application_session):
    """
    Function-scoped fixture that provides the session QApplication.

    This fixture:
    - Provides the QApplication instance to tests
    - Processes events after each test to prevent freezing
    - Does NOT quit or delete the app (managed by session fixture)
    - Cleans up AsyncBridge singleton state to prevent interference between tests
    """
    app = qt_application_session

    yield app

    # Clean up after each test
    if app:
        # Process any pending events to avoid freezing
        try:
            app.processEvents()
        except:
            pass  # App may be in an invalid state

        # Clean up AsyncBridge singleton to prevent state pollution between tests
        try:
            # Get the current thread's AsyncBridge instance if it exists
            import sys
            import threading

            # Only try to import if it might have been used
            if "ClassicLib.AsyncBridge" in sys.modules:
                from ClassicLib.AsyncBridge import AsyncBridge

                thread_id = threading.get_ident()
                # We need to be careful about accessing the lock if it might be held
                if AsyncBridge._instances:
                    # Use a copy of keys to avoid modification during iteration
                    for tid, instance in list(AsyncBridge._instances.items()):
                        try:
                            instance.shutdown()
                        except:
                            pass  # Ignore shutdown errors

                    # Clear instances
                    with AsyncBridge._lock:
                        AsyncBridge._instances.clear()
        except:
            pass  # Ignore if AsyncBridge not yet imported or other errors


@pytest.fixture(scope="function")
def qt_parent_widget(qt_application):
    """
    Provide a parent widget for dialog tests.

    Many Qt dialogs require a parent widget to function properly.
    This fixture provides a clean parent widget for each test.
    """
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.setObjectName("TestParentWidget")

    yield parent

    # Clean up
    parent.close()
    parent.deleteLater()
    # Process events to ensure deletion
    qt_application.processEvents()


@pytest.fixture(scope="function")
def gui_message_handler(qt_parent_widget):
    """
    Initialize MessageHandler in GUI mode with proper parent widget.

    This fixture ensures MessageHandler is configured for GUI operations,
    which affects how messages are displayed (dialogs vs console).
    Messages are mocked to prevent blocking dialogs during tests.
    """
    from ClassicLib.MessageHandler import handler as _handler_module
    from ClassicLib.MessageHandler import init_message_handler

    # Store any existing handler from the actual module where it's defined
    old_handler = getattr(_handler_module, "_message_handler", None)

    try:
        # Initialize in GUI mode with parent widget
        # Note: init_message_handler returns QtMessageHandler when is_gui_mode=True
        handler = init_message_handler(parent=qt_parent_widget, is_gui_mode=True)

        # Mock the GUI backend's show method to prevent blocking QMessageBox.exec()
        # The _gui_backend.show() method emits a signal that triggers _handle_message()
        # which calls msg_box.exec() - a blocking modal dialog
        # Use hasattr check since base MessageHandler doesn't have _gui_backend
        if hasattr(handler, "_gui_backend"):
            qt_handler: QtMessageHandler = handler  # type: ignore[assignment]
            qt_handler._gui_backend.show = MagicMock()

        yield handler
    finally:
        # Restore previous state or clean up
        _handler_module._message_handler = old_handler

        # Clear any cached references
        if hasattr(_handler_module, "_cached_handler"):
            delattr(_handler_module, "_cached_handler")


@pytest.fixture(scope="function")
def mock_qt_dialogs(monkeypatch):
    """
    Mock Qt dialog methods to prevent actual dialogs from appearing during tests.

    This fixture mocks common dialog methods like QMessageBox, QFileDialog, etc.
    to return predictable values without showing actual dialogs.
    """
    from unittest.mock import MagicMock

    from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

    # Mock QMessageBox methods
    mock_msgbox = MagicMock()
    mock_msgbox.information = MagicMock(return_value=QMessageBox.Ok)  # pyright: ignore[reportAttributeAccessIssue]
    mock_msgbox.warning = MagicMock(return_value=QMessageBox.Ok)  # pyright: ignore[reportAttributeAccessIssue]
    mock_msgbox.critical = MagicMock(return_value=QMessageBox.Ok)  # pyright: ignore[reportAttributeAccessIssue]
    mock_msgbox.question = MagicMock(return_value=QMessageBox.Yes)  # pyright: ignore[reportAttributeAccessIssue]

    monkeypatch.setattr(QMessageBox, "information", mock_msgbox.information)
    monkeypatch.setattr(QMessageBox, "warning", mock_msgbox.warning)
    monkeypatch.setattr(QMessageBox, "critical", mock_msgbox.critical)
    monkeypatch.setattr(QMessageBox, "question", mock_msgbox.question)

    # Mock QFileDialog methods
    mock_file_dialog = MagicMock()
    mock_file_dialog.getOpenFileName = MagicMock(return_value=("/path/to/file.txt", "Text Files (*.txt)"))
    mock_file_dialog.getSaveFileName = MagicMock(return_value=("/path/to/save.txt", "Text Files (*.txt)"))
    mock_file_dialog.getExistingDirectory = MagicMock(return_value="/path/to/directory")

    monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_file_dialog.getOpenFileName)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", mock_file_dialog.getSaveFileName)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", mock_file_dialog.getExistingDirectory)

    # Mock QInputDialog methods
    mock_input_dialog = MagicMock()
    mock_input_dialog.getText = MagicMock(return_value=("Test Input", True))
    mock_input_dialog.getInt = MagicMock(return_value=(42, True))

    monkeypatch.setattr(QInputDialog, "getText", mock_input_dialog.getText)
    monkeypatch.setattr(QInputDialog, "getInt", mock_input_dialog.getInt)

    return {"msgbox": mock_msgbox, "file_dialog": mock_file_dialog, "input_dialog": mock_input_dialog}
