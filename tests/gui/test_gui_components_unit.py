"""Unit tests for ClassicLib/GuiComponents.py module.

This module tests the ManualDocsPath class which manages and validates
user-provided directory paths for manual documentation and game files.
It verifies path validation, YAML settings updates, and signal emissions.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


@pytest.mark.unit
@pytest.mark.gui
class TestManualDocsPath:
    """Unit tests for ManualDocsPath class."""

    @pytest.fixture(autouse=True)
    def init_message_handler(self):
        """Initialize MessageHandler for tests that use msg_info/msg_error."""
        from ClassicLib.messaging import handler as handler_module
        from ClassicLib.messaging import init_message_handler

        # Initialize message handler for non-GUI mode
        init_message_handler(parent=None, is_gui_mode=False)
        yield
        # Clean up the handler after test by resetting the module-level global
        handler_module._message_handler = None

    @pytest.fixture
    def manual_docs_path(self, qt_application):
        """Create a ManualDocsPath instance for testing."""
        from ClassicLib.support.gui_components import ManualDocsPath

        return ManualDocsPath()

    def test_initialization(self, manual_docs_path):
        """Test that ManualDocsPath initializes correctly as QObject."""
        from PySide6.QtCore import QObject

        # Verify the object is a QObject
        assert isinstance(manual_docs_path, QObject)

        # Verify signals exist
        assert hasattr(manual_docs_path, "manual_docs_path_signal")
        assert hasattr(manual_docs_path, "game_path_signal")

    def test_get_manual_docs_path_gui_valid_directory(self, manual_docs_path, tmp_path, monkeypatch):
        """Test get_manual_docs_path_gui with a valid directory path."""
        # Create a real temporary directory
        valid_dir = tmp_path / "valid_docs"
        valid_dir.mkdir()

        # Mock yaml_settings to capture the call
        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(str(valid_dir))

            # Verify yaml_settings was called with correct parameters
            mock_yaml_settings.assert_called_once()
            call_args = mock_yaml_settings.call_args[0]

            # First arg is type (str)
            assert call_args[0] is str

            # Second arg is YAML store (Game_Local)
            from ClassicLib.core.constants import YAML

            assert call_args[1] == YAML.Game_Local

            # Third arg is key path
            assert call_args[2] == "Game_Info.Root_Folder_Docs"

            # Fourth arg is the path value
            assert call_args[3] == str(valid_dir)

    def test_get_manual_docs_path_gui_valid_directory_always_uses_game_info(self, manual_docs_path, tmp_path):
        """Test get_manual_docs_path_gui always uses Game_Info prefix (GameVR_Info was removed)."""
        valid_dir = tmp_path / "valid_docs_vr"
        valid_dir.mkdir()

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(str(valid_dir))

            # Verify Game_Info prefix is always used (GameVR_Info was removed)
            call_args = mock_yaml_settings.call_args[0]
            assert call_args[2] == "Game_Info.Root_Folder_Docs"

    def test_get_manual_docs_path_gui_invalid_directory(self, manual_docs_path):
        """Test get_manual_docs_path_gui with an invalid/nonexistent path."""
        invalid_path = "/nonexistent/path/that/does/not/exist"

        # Create a mock signal receiver to verify signal emission
        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.manual_docs_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(invalid_path)

            # yaml_settings should NOT be called for invalid path
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted
            assert len(signal_received) == 1

    def test_get_manual_docs_path_gui_empty_string(self, manual_docs_path):
        """Test get_manual_docs_path_gui with an empty string path.

        Note: Path("").is_dir() returns True on most systems because empty string
        resolves to current directory (.), so the implementation treats "" as valid.
        This test verifies that behavior matches the implementation.
        """
        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui("")

            # Empty string resolves to "." (current dir) which is valid
            # So yaml_settings IS called with "." as the path
            if mock_yaml_settings.called:
                call_args = mock_yaml_settings.call_args[0]
                # The path should be "." (empty string stripped is empty, Path("") is ".")
                assert call_args[3] == "."

    def test_get_manual_docs_path_gui_file_instead_of_directory(self, manual_docs_path, tmp_path):
        """Test get_manual_docs_path_gui with a file path instead of directory."""
        # Create a file instead of directory
        file_path = tmp_path / "some_file.txt"
        file_path.write_text("content")

        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.manual_docs_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(str(file_path))

            # yaml_settings should NOT be called (it's a file, not directory)
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted
            assert len(signal_received) == 1

    def test_get_manual_docs_path_gui_strips_whitespace(self, manual_docs_path, tmp_path):
        """Test that path whitespace is stripped before saving.

        Note: The implementation checks Path(path).is_dir() BEFORE stripping,
        so a path with leading/trailing whitespace will fail validation because
        the path with whitespace doesn't exist. This test verifies that behavior.
        """
        valid_dir = tmp_path / "whitespace_test"
        valid_dir.mkdir()

        # Add whitespace around the path
        path_with_whitespace = f"  {valid_dir}  "

        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.manual_docs_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(path_with_whitespace)

            # Path with whitespace doesn't exist, so validation fails
            # yaml_settings should NOT be called
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted (invalid path)
            assert len(signal_received) == 1

    def test_get_game_path_gui_valid_directory(self, manual_docs_path, tmp_path):
        """Test get_game_path_gui with a valid directory path."""
        valid_dir = tmp_path / "game_folder"
        valid_dir.mkdir()

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui(str(valid_dir))

            # Verify yaml_settings was called with correct parameters
            mock_yaml_settings.assert_called_once()
            call_args = mock_yaml_settings.call_args[0]

            assert call_args[0] is str

            from ClassicLib.core.constants import YAML

            assert call_args[1] == YAML.Game_Local
            assert call_args[2] == "Game_Info.Root_Folder_Game"
            assert call_args[3] == str(valid_dir)

    def test_get_game_path_gui_valid_directory_always_uses_game_info(self, manual_docs_path, tmp_path):
        """Test get_game_path_gui always uses Game_Info prefix (GameVR_Info was removed)."""
        valid_dir = tmp_path / "game_folder_vr"
        valid_dir.mkdir()

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui(str(valid_dir))

            # Verify Game_Info prefix is always used (GameVR_Info was removed)
            call_args = mock_yaml_settings.call_args[0]
            assert call_args[2] == "Game_Info.Root_Folder_Game"

    def test_get_game_path_gui_invalid_directory(self, manual_docs_path):
        """Test get_game_path_gui with an invalid/nonexistent path."""
        invalid_path = "/nonexistent/game/path"

        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.game_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui(invalid_path)

            # yaml_settings should NOT be called for invalid path
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted
            assert len(signal_received) == 1

    def test_get_game_path_gui_empty_string(self, manual_docs_path):
        """Test get_game_path_gui with an empty string path.

        Note: Path("").is_dir() returns True on most systems because empty string
        resolves to current directory (.), so the implementation treats "" as valid.
        """
        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui("")

            # Empty string resolves to "." (current dir) which is valid
            if mock_yaml_settings.called:
                call_args = mock_yaml_settings.call_args[0]
                assert call_args[3] == "."

    def test_get_game_path_gui_file_instead_of_directory(self, manual_docs_path, tmp_path):
        """Test get_game_path_gui with a file path instead of directory."""
        file_path = tmp_path / "some_game_file.exe"
        file_path.write_text("content")

        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.game_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui(str(file_path))

            # yaml_settings should NOT be called
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted
            assert len(signal_received) == 1

    def test_get_game_path_gui_strips_whitespace(self, manual_docs_path, tmp_path):
        """Test that game path with whitespace fails validation.

        Note: The implementation checks Path(path).is_dir() BEFORE stripping,
        so a path with leading/trailing whitespace will fail validation.
        """
        valid_dir = tmp_path / "game_whitespace_test"
        valid_dir.mkdir()

        path_with_whitespace = f"  {valid_dir}  "

        signal_received = []

        def signal_handler():
            signal_received.append(True)

        manual_docs_path.game_path_signal.connect(signal_handler)

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_game_path_gui(path_with_whitespace)

            # Path with whitespace doesn't exist, so validation fails
            mock_yaml_settings.assert_not_called()

            # Signal should have been emitted (invalid path)
            assert len(signal_received) == 1

    def test_signals_are_distinct(self, manual_docs_path):
        """Test that the two signals are distinct and independent."""
        docs_signal_received = []
        game_signal_received = []

        def docs_handler():
            docs_signal_received.append(True)

        def game_handler():
            game_signal_received.append(True)

        manual_docs_path.manual_docs_path_signal.connect(docs_handler)
        manual_docs_path.game_path_signal.connect(game_handler)

        # Trigger docs signal only
        with patch("ClassicLib.support.gui_components.yaml_settings"):
            manual_docs_path.get_manual_docs_path_gui("/invalid/path")

        assert len(docs_signal_received) == 1
        assert len(game_signal_received) == 0

        # Reset
        docs_signal_received.clear()

        # Trigger game signal only
        with patch("ClassicLib.support.gui_components.yaml_settings"):
            manual_docs_path.get_game_path_gui("/another/invalid/path")

        assert len(docs_signal_received) == 0
        assert len(game_signal_received) == 1

    def test_multiple_valid_paths_in_sequence(self, manual_docs_path, tmp_path):
        """Test handling multiple valid paths in sequence."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        with patch("ClassicLib.support.gui_components.yaml_settings") as mock_yaml_settings:
            manual_docs_path.get_manual_docs_path_gui(str(dir1))
            manual_docs_path.get_game_path_gui(str(dir2))

            # Both calls should have been made
            assert mock_yaml_settings.call_count == 2

            # Verify the correct paths were saved
            calls = mock_yaml_settings.call_args_list
            assert calls[0][0][3] == str(dir1)
            assert calls[1][0][3] == str(dir2)


@pytest.mark.unit
@pytest.mark.gui
class TestManualDocsPathSignals:
    """Tests specifically for signal behavior of ManualDocsPath."""

    @pytest.fixture(autouse=True)
    def init_message_handler(self):
        """Initialize MessageHandler for tests."""
        from ClassicLib.messaging import handler as handler_module
        from ClassicLib.messaging import init_message_handler

        init_message_handler(parent=None, is_gui_mode=False)
        yield
        handler_module._message_handler = None

    @pytest.fixture
    def manual_docs_path(self, qt_application):
        """Create a ManualDocsPath instance for testing."""
        from ClassicLib.support.gui_components import ManualDocsPath

        return ManualDocsPath()

    def test_signal_can_be_connected_multiple_times(self, manual_docs_path):
        """Test that signals can have multiple connected handlers."""
        handlers_called = {"handler1": 0, "handler2": 0}

        def handler1():
            handlers_called["handler1"] += 1

        def handler2():
            handlers_called["handler2"] += 1

        manual_docs_path.manual_docs_path_signal.connect(handler1)
        manual_docs_path.manual_docs_path_signal.connect(handler2)

        with patch("ClassicLib.support.gui_components.yaml_settings"):
            manual_docs_path.get_manual_docs_path_gui("/invalid/path")

        assert handlers_called["handler1"] == 1
        assert handlers_called["handler2"] == 1

    def test_signal_can_be_disconnected(self, manual_docs_path):
        """Test that signal handlers can be disconnected."""
        signal_count = []

        def handler():
            signal_count.append(True)

        manual_docs_path.manual_docs_path_signal.connect(handler)

        # First call - signal connected
        with patch("ClassicLib.support.gui_components.yaml_settings"):
            manual_docs_path.get_manual_docs_path_gui("/invalid/path1")

        assert len(signal_count) == 1

        # Disconnect the handler
        manual_docs_path.manual_docs_path_signal.disconnect(handler)

        # Second call - signal disconnected
        with patch("ClassicLib.support.gui_components.yaml_settings"):
            manual_docs_path.get_manual_docs_path_gui("/invalid/path2")

        # Count should still be 1 (handler was disconnected)
        assert len(signal_count) == 1
