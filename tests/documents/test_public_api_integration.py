"""Tests for the public API functions in DocsPath module."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.docs_path import docs_check_ini, docs_generate_paths, docs_path_find

pytestmark = [pytest.mark.unit]


class TestPublicAPIFunctions:
    """Tests for the public API functions."""

    @patch("ClassicLib.support.docs_path.DocumentsPathManager")
    def test_docs_path_find_gui_mode(self, mock_manager_class: MagicMock) -> None:
        """Test docs_path_find function in GUI mode."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_path_find(is_gui_mode=True)

        mock_manager_class.assert_called_once_with(True)
        mock_manager.find_docs_path.assert_called_once()

    @patch("ClassicLib.support.docs_path.DocumentsPathManager")
    def test_docs_path_find_cli_mode(self, mock_manager_class: MagicMock) -> None:
        """Test docs_path_find function in CLI mode."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_path_find(is_gui_mode=False)

        mock_manager_class.assert_called_once_with(False)
        mock_manager.find_docs_path.assert_called_once()

    @patch("ClassicLib.support.docs_path.DocumentsPathManager")
    def test_docs_generate_paths(self, mock_manager_class: MagicMock) -> None:
        """Test docs_generate_paths function."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        docs_generate_paths()

        mock_manager_class.assert_called_once_with()
        mock_manager.generate_paths.assert_called_once()

    @patch("ClassicLib.support.docs_path.DocumentsPathManager")
    def test_docs_check_ini(self, mock_manager_class: MagicMock) -> None:
        """Test docs_check_ini function."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.check_ini.return_value = "✔️ INI file is OK"

        result = docs_check_ini("Fallout4.ini")

        mock_manager_class.assert_called_once_with()
        mock_manager.check_ini.assert_called_once_with("Fallout4.ini")
        assert result == "✔️ INI file is OK"


if __name__ == "__main__":
    pytest.main()
