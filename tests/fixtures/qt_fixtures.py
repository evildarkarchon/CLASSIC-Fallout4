"""Qt/PySide6 fixtures for GUI testing."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="function")
def qt_application():
    """
    Ensure a QApplication instance exists for Qt/PySide6 tests.

    This fixture handles the complex lifecycle of QApplication:
    - Creates an instance if none exists
    - Reuses existing instance if present (Qt requirement)
    - Properly cleans up after tests
    """
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    # Check if QApplication already exists
    app = QApplication.instance()

    if app is None:
        # Create new QApplication
        app = QApplication([])
        created = True
    else:
        created = False

    yield app

    # Clean up if we created the app
    if created:
        app.quit()
        # Process remaining events
        app.processEvents()
        # Delete the application
        del app
        # Ensure it's really gone
        QCoreApplication.instance = lambda: None


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
    import ClassicLib.MessageHandler
    from ClassicLib.MessageHandler import init_message_handler

    # Initialize in GUI mode with parent widget
    handler = init_message_handler(parent=qt_parent_widget, is_gui_mode=True)

    # Mock the message signal to prevent actual dialog creation
    # This prevents blocking dialogs during tests
    handler.message_signal = MagicMock()

    yield handler

    # Clean up
    ClassicLib.MessageHandler._message_handler = None


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
    mock_msgbox.information = MagicMock(return_value=QMessageBox.Ok)
    mock_msgbox.warning = MagicMock(return_value=QMessageBox.Ok)
    mock_msgbox.critical = MagicMock(return_value=QMessageBox.Ok)
    mock_msgbox.question = MagicMock(return_value=QMessageBox.Yes)

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

    return {
        "msgbox": mock_msgbox,
        "file_dialog": mock_file_dialog,
        "input_dialog": mock_input_dialog
    }
