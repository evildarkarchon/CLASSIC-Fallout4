"""Unit tests for ClassicLib.support.xse module.

This module tests the XSE (Script Extender) integrity checking functionality
including Address Library validation, XSE installation verification, log file
parsing, and script hash validation.

Following TDD methodology - tests written first to define expected behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.xse import (
    Tokens,
    _calculate_script_hashes,
    _check_address_library,
    _check_xse_installation,
    _generate_result_message,
    _get_expected_script_hashes,
    _get_scripts_folder_path,
    _load_xse_config,
    xse_check_hashes,
    xse_check_integrity,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# Tokens Class Tests
# ==============================================================================


class TestTokens:
    """Tests for the Tokens class constants."""

    def test_tokens_has_xse_hashed_scripts_type_error_raised_attribute(self) -> None:
        """Tokens class should have the XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED attribute."""
        assert hasattr(Tokens, "XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED")

    def test_tokens_xse_hashed_scripts_type_error_raised_default_is_false(self) -> None:
        """XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED should default to False."""
        assert Tokens.XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED is False


# ==============================================================================
# _load_xse_config Tests
# ==============================================================================


class TestLoadXseConfig:
    """Tests for the _load_xse_config function."""

    @patch("ClassicLib.support.xse.yaml_settings")
    def test_load_xse_config_returns_dict_with_expected_keys(self, mock_yaml_settings: MagicMock) -> None:
        """_load_xse_config should return a dict with all expected keys."""
        mock_yaml_settings.return_value = "test_value"

        result = _load_xse_config("")

        assert isinstance(result, dict)
        assert "acronym" in result
        assert "full_name" in result
        assert "latest_version" in result
        assert "log_file" in result
        assert "adlib_file" in result

    @patch("ClassicLib.support.xse.yaml_settings")
    def test_load_xse_config_uses_game_vr_in_key_paths(self, mock_yaml_settings: MagicMock) -> None:
        """_load_xse_config should use game_vr suffix in YAML key paths."""
        mock_yaml_settings.return_value = None
        game_vr = "VR"

        _load_xse_config(game_vr)

        # Verify the YAML settings were called with VR suffix
        calls = mock_yaml_settings.call_args_list
        key_paths = [call[0][2] for call in calls]

        assert any("GameVR_Info.XSE_Acronym" in key for key in key_paths)
        assert any("GameVR_Info.XSE_FullName" in key for key in key_paths)

    @patch("ClassicLib.support.xse.yaml_settings")
    def test_load_xse_config_converts_adlib_file_to_path(self, mock_yaml_settings: MagicMock) -> None:
        """_load_xse_config should convert adlib_file string to Path."""

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Game_File_AddressLib" in key_path:
                return r"C:\Game\Data\AddressLib.bin"
            return None

        mock_yaml_settings.side_effect = yaml_side_effect

        result = _load_xse_config("")

        assert isinstance(result["adlib_file"], Path)
        assert result["adlib_file"] == Path(r"C:\Game\Data\AddressLib.bin")

    @patch("ClassicLib.support.xse.yaml_settings")
    def test_load_xse_config_returns_none_adlib_when_not_configured(self, mock_yaml_settings: MagicMock) -> None:
        """_load_xse_config should return None for adlib_file when not configured."""
        mock_yaml_settings.return_value = None

        result = _load_xse_config("")

        assert result["adlib_file"] is None


# ==============================================================================
# _check_address_library Tests
# ==============================================================================


class TestCheckAddressLibrary:
    """Tests for the _check_address_library function."""

    def test_check_address_library_success_when_file_exists(self, tmp_path: Path) -> None:
        """_check_address_library should add success message when file exists."""
        adlib_file = tmp_path / "version.bin"
        adlib_file.touch()
        messages: list[str] = []

        _check_address_library(adlib_file, "Fallout4", messages)

        assert len(messages) == 1
        assert "✔️ REQUIRED: *Address Library*" in messages[0]
        assert "installed" in messages[0]

    def test_check_address_library_warning_when_file_missing(self, tmp_path: Path) -> None:
        """_check_address_library should add warning message when file is missing."""
        adlib_file = tmp_path / "nonexistent.bin"
        messages: list[str] = []

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = "⚠️ Address Library Warning Message"

            _check_address_library(adlib_file, "Fallout4", messages)

        assert len(messages) == 1
        assert "Address Library Warning" in messages[0]

    def test_check_address_library_raises_type_error_when_warning_not_string(self, tmp_path: Path) -> None:
        """_check_address_library should raise TypeError when warning is not a string."""
        adlib_file = tmp_path / "nonexistent.bin"
        messages: list[str] = []

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = 123  # Not a string

            with pytest.raises(TypeError, match="must be a string"):
                _check_address_library(adlib_file, "Fallout4", messages)

    def test_check_address_library_invalid_path_none(self) -> None:
        """_check_address_library should add error message when adlib_file is None."""
        messages: list[str] = []

        _check_address_library(None, "Fallout4", messages)

        assert len(messages) == 1
        assert "❌" in messages[0]
        assert "invalid or missing" in messages[0]
        assert "Fallout4" in messages[0]


# ==============================================================================
# _check_xse_installation Tests
# ==============================================================================


class TestCheckXseInstallation:
    """Tests for the _check_xse_installation function."""

    def test_check_xse_installation_error_when_log_file_invalid(self) -> None:
        """_check_xse_installation should add error when log_file is not a string or Path."""
        messages: list[str] = []

        # Need to patch at the source module since import is done inside the function
        with patch("ClassicLib.core.registry.GlobalRegistry.get_game") as mock_get_game:
            mock_get_game.return_value = "Fallout4"

            _check_xse_installation(
                log_file=None,
                acronym="F4SE",
                full_name="Fallout 4 Script Extender",
                latest_version="0.6.23",
                error_patterns=["error"],
                messages=messages,
            )

        assert len(messages) == 1
        assert "❌" in messages[0]
        assert "f4se.log" in messages[0]

    def test_check_xse_installation_error_when_log_file_missing(self, tmp_path: Path) -> None:
        """_check_xse_installation should add error when log file doesn't exist."""
        log_path = tmp_path / "f4se.log"  # Doesn't exist
        messages: list[str] = []

        _check_xse_installation(
            log_file=str(log_path),
            acronym="F4SE",
            full_name="Fallout 4 Script Extender",
            latest_version="0.6.23",
            error_patterns=["error"],
            messages=messages,
        )

        assert len(messages) == 3
        assert "❌ CAUTION" in messages[0]
        assert "MISSING" in messages[0]
        assert "f4se_loader.exe" in messages[1]

    def test_check_xse_installation_success_when_latest_version(self, tmp_path: Path) -> None:
        """_check_xse_installation should report success when version is latest."""
        log_path = tmp_path / "f4se.log"
        log_path.write_text("F4SE version 0.6.23 loaded\n")
        messages: list[str] = []

        with patch("ClassicLib.support.xse._read_lines") as mock_read:
            mock_read.return_value = ["F4SE version 0.6.23 loaded", "No errors"]

            _check_xse_installation(
                log_file=str(log_path),
                acronym="F4SE",
                full_name="Fallout 4 Script Extender",
                latest_version="0.6.23",
                error_patterns=["error"],
                messages=messages,
            )

        assert any("✔️ REQUIRED: *Fallout 4 Script Extender* is installed" in msg for msg in messages)
        assert any("latest version" in msg for msg in messages)

    def test_check_xse_installation_warning_when_outdated(self, tmp_path: Path) -> None:
        """_check_xse_installation should warn when version is outdated."""
        log_path = tmp_path / "f4se.log"
        log_path.write_text("F4SE version 0.6.20 loaded\n")
        messages: list[str] = []

        with patch("ClassicLib.support.xse._read_lines") as mock_read:
            mock_read.return_value = ["F4SE version 0.6.20 loaded", "No errors"]

            with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
                mock_yaml.return_value = "⚠️ XSE is outdated!"

                _check_xse_installation(
                    log_file=str(log_path),
                    acronym="F4SE",
                    full_name="Fallout 4 Script Extender",
                    latest_version="0.6.23",
                    error_patterns=["error"],
                    messages=messages,
                )

        assert any("XSE is outdated" in msg for msg in messages)

    def test_check_xse_installation_raises_type_error_when_outdated_warning_not_string(self, tmp_path: Path) -> None:
        """_check_xse_installation should raise TypeError when outdated warning is not a string."""
        log_path = tmp_path / "f4se.log"
        log_path.write_text("F4SE version 0.6.20 loaded\n")
        messages: list[str] = []

        with patch("ClassicLib.support.xse._read_lines") as mock_read:
            mock_read.return_value = ["F4SE version 0.6.20 loaded"]

            with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
                mock_yaml.return_value = None  # Not a string

                with pytest.raises(TypeError, match="must be a string"):
                    _check_xse_installation(
                        log_file=str(log_path),
                        acronym="F4SE",
                        full_name="Fallout 4 Script Extender",
                        latest_version="0.6.23",
                        error_patterns=["error"],
                        messages=messages,
                    )

    def test_check_xse_installation_detects_errors_in_log(self, tmp_path: Path) -> None:
        """_check_xse_installation should detect errors in the log file."""
        log_path = tmp_path / "f4se.log"
        log_path.write_text("F4SE version 0.6.23\n")
        messages: list[str] = []

        with patch("ClassicLib.support.xse._read_lines") as mock_read:
            mock_read.return_value = [
                "F4SE version 0.6.23 loaded",
                "ERROR: Plugin failed to load",
                "WARNING: Something went wrong",
            ]

            _check_xse_installation(
                log_file=str(log_path),
                acronym="F4SE",
                full_name="Fallout 4 Script Extender",
                latest_version="0.6.23",
                error_patterns=["error", "warning"],
                messages=messages,
            )

        # Should have error header and error lines
        assert any("REPORTS THE FOLLOWING ERRORS" in msg for msg in messages)
        assert any("ERROR >" in msg for msg in messages)


# ==============================================================================
# xse_check_integrity Tests
# ==============================================================================


class TestXseCheckIntegrity:
    """Tests for the xse_check_integrity function."""

    @patch("ClassicLib.support.xse.get_vr")
    @patch("ClassicLib.support.xse.get_game")
    @patch("ClassicLib.support.xse.yaml_settings")
    @patch("ClassicLib.support.xse._load_xse_config")
    @patch("ClassicLib.support.xse._check_address_library")
    @patch("ClassicLib.support.xse._check_xse_installation")
    def test_xse_check_integrity_returns_string(
        self,
        mock_check_xse: MagicMock,
        mock_check_adlib: MagicMock,
        mock_load_config: MagicMock,
        mock_yaml: MagicMock,
        mock_get_game: MagicMock,
        mock_get_vr: MagicMock,
    ) -> None:
        """xse_check_integrity should return a string result."""
        mock_get_vr.return_value = ""
        mock_get_game.return_value = "Fallout4"
        mock_yaml.return_value = ["error", "warning"]
        mock_load_config.return_value = {
            "acronym": "F4SE",
            "full_name": "Fallout 4 Script Extender",
            "latest_version": "0.6.23",
            "log_file": None,
            "adlib_file": None,
        }

        result = xse_check_integrity()

        assert isinstance(result, str)

    @patch("ClassicLib.support.xse.get_vr")
    @patch("ClassicLib.support.xse.get_game")
    @patch("ClassicLib.support.xse.yaml_settings")
    def test_xse_check_integrity_raises_type_error_when_patterns_not_list(
        self,
        mock_yaml: MagicMock,
        mock_get_game: MagicMock,
        mock_get_vr: MagicMock,
    ) -> None:
        """xse_check_integrity should raise TypeError when error patterns is not a list."""
        mock_get_vr.return_value = ""
        mock_get_game.return_value = "Fallout4"
        mock_yaml.return_value = "not a list"  # Invalid type

        with pytest.raises(TypeError, match="must be a list"):
            xse_check_integrity()


# ==============================================================================
# _get_expected_script_hashes Tests
# ==============================================================================


class TestGetExpectedScriptHashes:
    """Tests for the _get_expected_script_hashes function."""

    def test_get_expected_script_hashes_returns_dict(self) -> None:
        """_get_expected_script_hashes should return a dictionary."""
        mock_version_info = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_script_hashes_for_version.return_value = {
            "script1.pex": "abc123",
            "script2.pex": "def456",
        }

        # Patch both the core module and the __init__ re-exports
        with (
            patch("ClassicLib.support.versions.get_detected_version_info") as mock_get_version_info,
            patch("ClassicLib.support.versions.get_version_registry") as mock_get_registry_func,
        ):
            mock_get_version_info.return_value = mock_version_info
            mock_get_registry_func.return_value = mock_registry

            result = _get_expected_script_hashes()

        assert isinstance(result, dict)
        assert result == {"script1.pex": "abc123", "script2.pex": "def456"}

    def test_get_expected_script_hashes_returns_empty_when_no_version_detected(
        self,
    ) -> None:
        """_get_expected_script_hashes should return empty dict when version detection fails."""
        mock_registry = MagicMock()

        with (
            patch("ClassicLib.support.versions.get_detected_version_info") as mock_get_version_info,
            patch("ClassicLib.support.versions.get_version_registry") as mock_get_registry_func,
            patch("ClassicLib.support.xse.logger"),
        ):
            mock_get_version_info.return_value = None
            mock_get_registry_func.return_value = mock_registry

            result = _get_expected_script_hashes()

        assert result == {}

    @patch("ClassicLib.support.xse.logger")
    def test_get_expected_script_hashes_logs_warning_on_failure(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """_get_expected_script_hashes should log warning when version detection fails."""
        mock_registry = MagicMock()

        with (
            patch("ClassicLib.support.versions.get_detected_version_info") as mock_get_version_info,
            patch("ClassicLib.support.versions.get_version_registry") as mock_get_registry_func,
        ):
            mock_get_version_info.return_value = None
            mock_get_registry_func.return_value = mock_registry

            _get_expected_script_hashes()

        mock_logger.warning.assert_called_once()
        assert "version" in mock_logger.warning.call_args[0][0].lower()


# ==============================================================================
# _get_scripts_folder_path Tests
# ==============================================================================


class TestGetScriptsFolderPath:
    """Tests for the _get_scripts_folder_path function."""

    @patch("ClassicLib.support.xse.get_vr")
    @patch("ClassicLib.support.xse.yaml_settings")
    def test_get_scripts_folder_path_returns_string(
        self,
        mock_yaml: MagicMock,
        mock_get_vr: MagicMock,
    ) -> None:
        """_get_scripts_folder_path should return a string path."""
        mock_get_vr.return_value = ""
        mock_yaml.return_value = r"C:\Game\Data\Scripts"

        result = _get_scripts_folder_path()

        assert result == r"C:\Game\Data\Scripts"

    @patch("ClassicLib.support.xse.get_vr")
    @patch("ClassicLib.support.xse.yaml_settings")
    def test_get_scripts_folder_path_raises_value_error_when_none(
        self,
        mock_yaml: MagicMock,
        mock_get_vr: MagicMock,
    ) -> None:
        """_get_scripts_folder_path should raise ValueError when path is None."""
        mock_get_vr.return_value = ""
        mock_yaml.return_value = None

        with pytest.raises(ValueError, match="cannot be None"):
            _get_scripts_folder_path()


# ==============================================================================
# _calculate_script_hashes Tests
# ==============================================================================


class TestCalculateScriptHashes:
    """Tests for the _calculate_script_hashes function."""

    def test_calculate_script_hashes_returns_dict(self, tmp_path: Path) -> None:
        """_calculate_script_hashes should return a dictionary."""
        result = _calculate_script_hashes([], str(tmp_path))

        assert isinstance(result, dict)

    def test_calculate_script_hashes_calculates_sha256_for_existing_files(self, tmp_path: Path) -> None:
        """_calculate_script_hashes should calculate SHA-256 hashes for existing files."""
        script_file = tmp_path / "test_script.pex"
        script_file.write_bytes(b"test content")

        with patch("ClassicLib.support.xse._read_bytes") as mock_read:
            mock_read.return_value = b"test content"

            result = _calculate_script_hashes(["test_script.pex"], str(tmp_path))

        assert "test_script.pex" in result
        assert result["test_script.pex"] is not None
        # SHA-256 of "test content" should be a valid hex string
        assert len(result["test_script.pex"]) == 64  # SHA-256 produces 64 hex chars

    def test_calculate_script_hashes_returns_none_for_missing_files(self, tmp_path: Path) -> None:
        """_calculate_script_hashes should return None for missing files."""
        result = _calculate_script_hashes(["nonexistent.pex"], str(tmp_path))

        assert "nonexistent.pex" in result
        assert result["nonexistent.pex"] is None

    def test_calculate_script_hashes_handles_read_errors(self, tmp_path: Path) -> None:
        """_calculate_script_hashes should handle file read errors gracefully."""
        script_file = tmp_path / "test_script.pex"
        script_file.touch()

        with patch("ClassicLib.support.xse._read_bytes") as mock_read:
            mock_read.side_effect = OSError("Permission denied")

            with patch("ClassicLib.support.xse.msg_warning"):
                result = _calculate_script_hashes(["test_script.pex"], str(tmp_path))

        assert result["test_script.pex"] is None

    def test_calculate_script_hashes_processes_multiple_files(self, tmp_path: Path) -> None:
        """_calculate_script_hashes should process multiple files."""
        # Create some test files
        (tmp_path / "script1.pex").touch()
        (tmp_path / "script2.pex").touch()

        with patch("ClassicLib.support.xse._read_bytes") as mock_read:
            mock_read.return_value = b"content"

            result = _calculate_script_hashes(
                ["script1.pex", "script2.pex", "missing.pex"],
                str(tmp_path),
            )

        assert "script1.pex" in result
        assert "script2.pex" in result
        assert "missing.pex" in result
        assert result["missing.pex"] is None


# ==============================================================================
# _generate_result_message Tests
# ==============================================================================


class TestGenerateResultMessage:
    """Tests for the _generate_result_message function."""

    def test_generate_result_message_success_when_all_hashes_match(self) -> None:
        """_generate_result_message should report success when all hashes match."""
        expected_hashes = {"script1.pex": "abc123", "script2.pex": "def456"}
        actual_hashes = {"script1.pex": "abc123", "script2.pex": "def456"}

        result = _generate_result_message(expected_hashes, actual_hashes)

        assert "✔️" in result
        assert "found and accounted for" in result

    def test_generate_result_message_reports_missing_scripts(self) -> None:
        """_generate_result_message should report missing scripts."""
        expected_hashes = {"script1.pex": "abc123"}
        actual_hashes = {"script1.pex": None}

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = "⚠️ Missing warning"

            result = _generate_result_message(expected_hashes, actual_hashes)

        assert "❌ CAUTION" in result
        assert "missing" in result.lower()

    def test_generate_result_message_reports_mismatched_scripts(self) -> None:
        """_generate_result_message should report mismatched/outdated scripts."""
        expected_hashes = {"script1.pex": "abc123"}
        actual_hashes = {"script1.pex": "xyz789"}

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = "⚠️ Mismatch warning"

            result = _generate_result_message(expected_hashes, actual_hashes)

        assert "[!] CAUTION" in result
        assert "outdated or overriden" in result

    def test_generate_result_message_raises_type_error_for_invalid_missing_warning(
        self,
    ) -> None:
        """_generate_result_message should raise TypeError for invalid missing warning."""
        expected_hashes = {"script1.pex": "abc123"}
        actual_hashes = {"script1.pex": None}

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = 123  # Invalid type

            with pytest.raises(TypeError, match="must be a string"):
                _generate_result_message(expected_hashes, actual_hashes)

    def test_generate_result_message_raises_type_error_for_invalid_mismatch_warning(
        self,
    ) -> None:
        """_generate_result_message should raise TypeError for invalid mismatch warning."""
        expected_hashes = {"script1.pex": "abc123"}
        actual_hashes = {"script1.pex": "xyz789"}

        with patch("ClassicLib.support.xse.yaml_settings") as mock_yaml:
            mock_yaml.return_value = None  # Invalid type

            with pytest.raises(TypeError, match="must be a string"):
                _generate_result_message(expected_hashes, actual_hashes)

    def test_generate_result_message_returns_empty_for_empty_hashes(self) -> None:
        """_generate_result_message should handle empty hash dicts."""
        result = _generate_result_message({}, {})

        assert "✔️" in result
        assert "found and accounted for" in result


# ==============================================================================
# xse_check_hashes Tests
# ==============================================================================


class TestXseCheckHashes:
    """Tests for the xse_check_hashes function."""

    @patch("ClassicLib.support.xse._get_expected_script_hashes")
    @patch("ClassicLib.support.xse._get_scripts_folder_path")
    @patch("ClassicLib.support.xse._calculate_script_hashes")
    @patch("ClassicLib.support.xse._generate_result_message")
    def test_xse_check_hashes_returns_string(
        self,
        mock_generate: MagicMock,
        mock_calculate: MagicMock,
        mock_get_path: MagicMock,
        mock_get_expected: MagicMock,
    ) -> None:
        """xse_check_hashes should return a string result."""
        mock_get_expected.return_value = {"script.pex": "abc123"}
        mock_get_path.return_value = r"C:\Game\Data\Scripts"
        mock_calculate.return_value = {"script.pex": "abc123"}
        mock_generate.return_value = "✔️ All good!"

        result = xse_check_hashes()

        assert isinstance(result, str)
        assert result == "✔️ All good!"

    @patch("ClassicLib.support.xse._get_expected_script_hashes")
    @patch("ClassicLib.support.xse._get_scripts_folder_path")
    @patch("ClassicLib.support.xse._calculate_script_hashes")
    @patch("ClassicLib.support.xse._generate_result_message")
    def test_xse_check_hashes_calls_functions_in_order(
        self,
        mock_generate: MagicMock,
        mock_calculate: MagicMock,
        mock_get_path: MagicMock,
        mock_get_expected: MagicMock,
    ) -> None:
        """xse_check_hashes should call helper functions in correct order."""
        expected_hashes = {"script.pex": "abc123"}
        scripts_folder = r"C:\Game\Data\Scripts"
        actual_hashes = {"script.pex": "abc123"}

        mock_get_expected.return_value = expected_hashes
        mock_get_path.return_value = scripts_folder
        mock_calculate.return_value = actual_hashes
        mock_generate.return_value = "result"

        xse_check_hashes()

        mock_get_expected.assert_called_once()
        mock_get_path.assert_called_once()
        mock_calculate.assert_called_once_with(expected_hashes.keys(), scripts_folder)
        mock_generate.assert_called_once_with(expected_hashes, actual_hashes)

    @patch("ClassicLib.support.xse._get_expected_script_hashes")
    @patch("ClassicLib.support.xse._get_scripts_folder_path")
    @patch("ClassicLib.support.xse._calculate_script_hashes")
    @patch("ClassicLib.support.xse._generate_result_message")
    def test_xse_check_hashes_handles_empty_expected_hashes(
        self,
        mock_generate: MagicMock,
        mock_calculate: MagicMock,
        mock_get_path: MagicMock,
        mock_get_expected: MagicMock,
    ) -> None:
        """xse_check_hashes should handle empty expected hashes gracefully."""
        mock_get_expected.return_value = {}
        mock_get_path.return_value = r"C:\Game\Data\Scripts"
        mock_calculate.return_value = {}
        mock_generate.return_value = "No scripts to validate"

        result = xse_check_hashes()

        assert result == "No scripts to validate"
        mock_calculate.assert_called_once()
