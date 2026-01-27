"""Unit tests for ClassicLib.scanning.game.CheckCrashgen module.

This module tests the Crash Generator (Buffout4) configuration checking
functionality including plugin detection, TOML settings validation,
and FCX read-only mode compliance.

Following TDD methodology - tests written to define expected behavior.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ClassicLib.scanning.game.CheckCrashgen import (
    CrashgenChecker,
    check_crashgen_settings,
)

from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue

pytestmark = pytest.mark.unit


# ==============================================================================
# CrashgenChecker._get_plugins_path Tests
# ==============================================================================


class TestGetPluginsPath:
    """Tests for the _get_plugins_path static method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_plugins_path_returns_path_from_yaml(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_get_plugins_path should return Path from YAML settings."""
        mock_registry.get_vr.return_value = ""
        mock_yaml.return_value = tmp_path / "plugins"

        result = CrashgenChecker._get_plugins_path()

        assert result == tmp_path / "plugins"

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_plugins_path_returns_none_when_not_configured(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_plugins_path should return None when not configured."""
        mock_registry.get_vr.return_value = ""
        mock_yaml.return_value = None

        result = CrashgenChecker._get_plugins_path()

        assert result is None


# ==============================================================================
# CrashgenChecker._get_crashgen_name Tests
# ==============================================================================


class TestGetCrashgenName:
    """Tests for the _get_crashgen_name static method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_crashgen_name_returns_name_from_yaml(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_crashgen_name should return name from YAML settings."""
        mock_registry.get_vr.return_value = ""
        mock_yaml.return_value = "Custom Crashgen"

        result = CrashgenChecker._get_crashgen_name()

        assert result == "Custom Crashgen"

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_crashgen_name_defaults_to_buffout4(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_crashgen_name should default to Buffout4 when not configured."""
        mock_registry.get_vr.return_value = ""
        mock_yaml.return_value = None

        result = CrashgenChecker._get_crashgen_name()

        assert result == "Buffout4"


# ==============================================================================
# CrashgenChecker._find_config_file Tests
# ==============================================================================


class TestFindConfigFile:
    """Tests for the _find_config_file method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_find_config_file_returns_none_when_no_plugins_path(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_find_config_file should return None when plugins_path is None."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()

        assert checker.config_file is None

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_find_config_file_finds_og_config(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_find_config_file should find Buffout4/config.toml."""
        plugins_path = tmp_path / "plugins"
        buffout_dir = plugins_path / "Buffout4"
        buffout_dir.mkdir(parents=True)
        config_file = buffout_dir / "config.toml"
        config_file.write_text("[Patches]\nAchievements = true")

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        assert checker.config_file == config_file

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_find_config_file_finds_vr_config(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_find_config_file should find Buffout4.toml (VR style)."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir(parents=True)
        config_file = plugins_path / "Buffout4.toml"
        config_file.write_text("[Patches]\nAchievements = true")

        mock_registry.get_vr.return_value = "VR"
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        assert checker.config_file == config_file

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_find_config_file_warns_about_duplicate_configs(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_find_config_file should warn when both config files exist."""
        plugins_path = tmp_path / "plugins"
        buffout_dir = plugins_path / "Buffout4"
        buffout_dir.mkdir(parents=True)

        og_config = buffout_dir / "config.toml"
        og_config.write_text("[Patches]")
        vr_config = plugins_path / "Buffout4.toml"
        vr_config.write_text("[Patches]")

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        # Should have duplicate warning in message list
        messages = "".join(checker.message_list)
        assert "BOTH VERSIONS" in messages


# ==============================================================================
# CrashgenChecker._detect_installed_plugins Tests
# ==============================================================================


class TestDetectInstalledPlugins:
    """Tests for the _detect_installed_plugins method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_detect_installed_plugins_returns_set(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_detect_installed_plugins should return a set of plugin names."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "plugin1.dll").touch()
        (plugins_path / "plugin2.dll").touch()

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        assert isinstance(checker.installed_plugins, set)
        assert "plugin1.dll" in checker.installed_plugins
        assert "plugin2.dll" in checker.installed_plugins

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_detect_installed_plugins_lowercases_names(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """_detect_installed_plugins should lowercase all plugin names."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "UpperCase.DLL").touch()

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        assert "uppercase.dll" in checker.installed_plugins

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_detect_installed_plugins_returns_empty_when_no_path(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_detect_installed_plugins should return empty set when path is None."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()

        assert checker.installed_plugins == set()


# ==============================================================================
# CrashgenChecker.has_plugin Tests
# ==============================================================================


class TestHasPlugin:
    """Tests for the has_plugin method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_has_plugin_returns_true_when_found(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """has_plugin should return True when plugin is installed."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "x-cell-fo4.dll").touch()

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        assert checker.has_plugin(["x-cell-fo4.dll"]) is True

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_has_plugin_returns_false_when_not_found(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """has_plugin should return False when plugin is not installed."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()

        assert checker.has_plugin(["x-cell-fo4.dll"]) is False

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_has_plugin_checks_multiple_names(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """has_plugin should return True if any plugin from list is found."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "achievements.dll").touch()

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()

        result = checker.has_plugin(["other.dll", "achievements.dll", "third.dll"])
        assert result is True


# ==============================================================================
# CrashgenChecker._get_settings_to_check Tests
# ==============================================================================


class TestGetSettingsToCheck:
    """Tests for the _get_settings_to_check method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_settings_to_check_returns_empty_for_non_fallout4(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_settings_to_check should return empty list for non-Fallout4 games."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "SkyrimSE"  # Not Fallout4
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        result = checker._get_settings_to_check()

        assert result == []

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_settings_to_check_returns_list_for_fallout4(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_settings_to_check should return settings list for Fallout4."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        result = checker._get_settings_to_check()

        assert isinstance(result, list)
        assert len(result) > 0

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_settings_to_check_includes_achievements_setting(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_settings_to_check should include Achievements setting."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        result = checker._get_settings_to_check()

        achievement_settings = [s for s in result if s.get("key") == "Achievements"]
        assert len(achievement_settings) == 1

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_get_settings_to_check_includes_f4ee_setting(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """_get_settings_to_check should include F4EE setting."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        result = checker._get_settings_to_check()

        f4ee_settings = [s for s in result if s.get("key") == "F4EE"]
        assert len(f4ee_settings) == 1


# ==============================================================================
# CrashgenChecker._detect_toml_issue Tests
# ==============================================================================


class TestDetectTomlIssue:
    """Tests for the _detect_toml_issue static method."""

    def test_detect_toml_issue_returns_config_issue_when_mismatch(self, tmp_path: Path) -> None:
        """_detect_toml_issue should return ConfigIssue when value doesn't match."""
        config_file = tmp_path / "config.toml"
        setting: dict[str, Any] = {
            "section": "Patches",
            "key": "Achievements",
            "name": "Achievements",
            "desired_value": False,
            "description": "Achievements mod installed",
            "reason": "to prevent conflicts",
        }

        result = CrashgenChecker._detect_toml_issue(config_file, setting, True)

        assert isinstance(result, ConfigIssue)
        assert result.setting == "Achievements"
        assert result.current_value == "True"
        assert result.recommended_value == "False"

    def test_detect_toml_issue_returns_none_when_correct(self, tmp_path: Path) -> None:
        """_detect_toml_issue should return None when value matches desired."""
        config_file = tmp_path / "config.toml"
        setting: dict[str, Any] = {
            "section": "Patches",
            "key": "Achievements",
            "name": "Achievements",
            "desired_value": False,
            "description": "Achievements mod installed",
            "reason": "to prevent conflicts",
        }

        result = CrashgenChecker._detect_toml_issue(config_file, setting, False)

        assert result is None


# ==============================================================================
# CrashgenChecker.check Tests
# ==============================================================================


class TestCheck:
    """Tests for the check method."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_returns_tuple(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """check should return a tuple of (string, list)."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        result = checker.check()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], list)

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_returns_notice_when_no_config_file(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """check should return notice message when config file not found."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        checker = CrashgenChecker()
        message, issues = checker.check()

        assert "NOTICE" in message
        assert "settings check will be skipped" in message
        assert issues == []

    @patch("ClassicLib.scanning.game.CheckCrashgen.mod_toml_config")
    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_detects_issues_without_modifying_files(
        self, mock_registry: MagicMock, mock_yaml: MagicMock, mock_toml: MagicMock, tmp_path: Path
    ) -> None:
        """check should detect issues without modifying configuration files (FCX read-only)."""
        plugins_path = tmp_path / "plugins"
        buffout_dir = plugins_path / "Buffout4"
        buffout_dir.mkdir(parents=True)
        config_file = buffout_dir / "config.toml"
        config_file.write_text("[Patches]\nAchievements = true\n[Compatibility]\nF4EE = false")
        original_content = config_file.read_text()

        # Create achievements.dll to trigger the check
        (plugins_path / "achievements.dll").touch()

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_toml.return_value = True  # Current value is True (should be False)

        checker = CrashgenChecker()
        message, issues = checker.check()

        # File should not be modified (FCX read-only)
        assert config_file.read_text() == original_content


# ==============================================================================
# check_crashgen_settings Function Tests
# ==============================================================================


class TestCheckCrashgenSettings:
    """Tests for the check_crashgen_settings module-level function."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_crashgen_settings_returns_tuple(self, mock_registry: MagicMock, mock_yaml: MagicMock) -> None:
        """check_crashgen_settings should return a tuple."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        result = check_crashgen_settings()

        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("ClassicLib.scanning.game.CheckCrashgen.CrashgenChecker")
    def test_check_crashgen_settings_creates_checker_instance(self, mock_checker_class: MagicMock) -> None:
        """check_crashgen_settings should create a CrashgenChecker instance."""
        mock_instance = MagicMock()
        mock_instance.check.return_value = ("message", [])
        mock_checker_class.return_value = mock_instance

        check_crashgen_settings()

        mock_checker_class.assert_called_once()
        mock_instance.check.assert_called_once()


# ==============================================================================
# ConfigIssue Integration Tests
# ==============================================================================


class TestConfigIssueIntegration:
    """Integration tests for ConfigIssue objects returned by check."""

    def test_config_issue_has_required_attributes(self, tmp_path: Path) -> None:
        """ConfigIssue should have all required attributes."""
        issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Patches",
            setting="Achievements",
            current_value="true",
            recommended_value="false",
            description="Test issue",
            severity="warning",
        )

        assert issue.file_path == tmp_path / "config.toml"
        assert issue.section == "Patches"
        assert issue.setting == "Achievements"
        assert issue.current_value == "true"
        assert issue.recommended_value == "false"
        assert issue.description == "Test issue"
        assert issue.severity == "warning"

    def test_config_issue_format_report_includes_all_info(self, tmp_path: Path) -> None:
        """ConfigIssue.format_report should include all issue information."""
        issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Patches",
            setting="Achievements",
            current_value="true",
            recommended_value="false",
            description="Achievements should be disabled",
            severity="warning",
        )

        report = issue.format_report()

        assert "config.toml" in report
        assert "Patches" in report
        assert "Achievements" in report
        assert "true" in report
        assert "false" in report
        assert "disabled" in report

    def test_config_issue_severity_icons(self, tmp_path: Path) -> None:
        """ConfigIssue.format_report should use correct severity icons."""
        warning_issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Test",
            setting="Key",
            current_value="a",
            recommended_value="b",
            description="Warning",
            severity="warning",
        )

        error_issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Test",
            setting="Key",
            current_value="a",
            recommended_value="b",
            description="Error",
            severity="error",
        )

        info_issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Test",
            setting="Key",
            current_value="a",
            recommended_value="b",
            description="Info",
            severity="info",
        )

        assert "⚠️" in warning_issue.format_report()
        assert "❌" in error_issue.format_report()
        assert "ℹ️" in info_issue.format_report()


# ==============================================================================
# FCX Read-Only Mode Compliance Tests
# ==============================================================================


class TestFCXReadOnlyCompliance:
    """Tests to verify FCX read-only mode compliance."""

    @patch("ClassicLib.scanning.game.CheckCrashgen.mod_toml_config")
    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_never_calls_mod_toml_config_with_new_value(
        self, mock_registry: MagicMock, mock_yaml: MagicMock, mock_toml: MagicMock, tmp_path: Path
    ) -> None:
        """check should never call mod_toml_config with a new_value parameter."""
        plugins_path = tmp_path / "plugins"
        buffout_dir = plugins_path / "Buffout4"
        buffout_dir.mkdir(parents=True)
        config_file = buffout_dir / "config.toml"
        config_file.write_text("[Patches]\nAchievements = true")

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_toml.return_value = True

        checker = CrashgenChecker()
        checker.check()

        # All calls to mod_toml_config should only have 3 args (no new_value)
        for call in mock_toml.call_args_list:
            args = call[0]
            # mod_toml_config(toml_path, section, key, new_value=None)
            # If new_value is passed, it would be the 4th positional arg
            assert len(args) <= 3, "mod_toml_config should not be called with new_value"

    @patch("ClassicLib.scanning.game.CheckCrashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.CheckCrashgen.GlobalRegistry")
    def test_check_only_detects_issues_never_fixes(self, mock_registry: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """check should only detect and report issues, never fix them."""
        plugins_path = tmp_path / "plugins"
        buffout_dir = plugins_path / "Buffout4"
        buffout_dir.mkdir(parents=True)
        config_file = buffout_dir / "config.toml"
        config_content = "[Patches]\nAchievements = true\nMemoryManager = true"
        config_file.write_text(config_content)

        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        checker = CrashgenChecker()
        checker.check()

        # Config file content should be unchanged
        assert config_file.read_text() == config_content
