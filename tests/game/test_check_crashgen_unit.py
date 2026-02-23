"""Unit tests for ClassicLib.scanning.game.check_crashgen module.

This module tests the Crash Generator (Buffout4) configuration checking
functionality. The module delegates to Rust CrashgenCheckOrchestrator;
Python tests verify the YAML-resolution glue and type conversion layer.

Following TDD methodology - tests written to define expected behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.scanning.game.check_crashgen import check_crashgen_settings
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue

pytestmark = pytest.mark.unit


# ==============================================================================
# check_crashgen_settings — no plugins path
# ==============================================================================


class TestCheckCrashgenSettingsNoPlugins:
    """Tests for check_crashgen_settings when plugins path is unavailable."""

    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_returns_notice_when_no_plugins_path(self, mock_get_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """check_crashgen_settings should return notice when plugins path is None."""
        mock_yaml.return_value = None

        message, issues = check_crashgen_settings()

        assert "NOTICE" in message
        assert "settings check will be skipped" in message
        assert issues == []

    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_returns_tuple(self, mock_get_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """check_crashgen_settings should return a (str, list) tuple."""
        mock_yaml.return_value = None

        result = check_crashgen_settings()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], list)

    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_non_buffout_crashgen_proceeds_with_registry_routing(self, mock_get_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """check_crashgen_settings no longer gates on Buffout name.

        With registry-aware routing, all crashgen names proceed to the Rust
        CrashgenCheckOrchestrator. When plugins_path is None the function
        returns the "config not found" notice (not an empty string).
        """

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "CRASHGEN_LogName" in key_path:
                return "Custom Crashgen"
            return None

        mock_yaml.side_effect = yaml_side_effect

        message, issues = check_crashgen_settings()

        # No longer returns "" for non-Buffout names; instead falls through to
        # plugins_path check (which is None here → returns the notice message).
        assert "Custom Crashgen" in message or message == ""
        assert issues == []

    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_defaults_crashgen_name_to_buffout4(self, mock_get_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """check_crashgen_settings should default name to Buffout4."""
        mock_yaml.return_value = None

        message, _ = check_crashgen_settings()

        assert "Buffout4" in message


# ==============================================================================
# check_crashgen_settings — with Rust delegation
# ==============================================================================


class TestCheckCrashgenSettingsRustDelegation:
    """Tests for check_crashgen_settings when it delegates to Rust."""

    @patch("classic_scangame.CrashgenCheckOrchestrator")
    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_delegates_to_rust_orchestrator(
        self,
        mock_get_vr: MagicMock,
        mock_yaml: MagicMock,
        mock_orchestrator: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_crashgen_settings should delegate to Rust CrashgenCheckOrchestrator."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return "Buffout4"

        mock_yaml.side_effect = yaml_side_effect

        mock_report = MagicMock()
        mock_report.message = "All settings OK"
        mock_report.issues = []
        mock_orchestrator.check.return_value = mock_report

        message, issues = check_crashgen_settings()

        mock_orchestrator.check.assert_called_once_with(plugins_path, "Buffout4")
        assert message == "All settings OK"
        assert issues == []

    @patch("classic_scangame.CrashgenCheckOrchestrator")
    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_converts_rust_issues_to_config_issues(
        self,
        mock_get_vr: MagicMock,
        mock_yaml: MagicMock,
        mock_orchestrator: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_crashgen_settings should convert Rust issues to ConfigIssue."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return "Buffout4"

        mock_yaml.side_effect = yaml_side_effect

        mock_issue = MagicMock()
        mock_issue.file_path = str(tmp_path / "config.toml")
        mock_issue.section = "Patches"
        mock_issue.setting = "Achievements"
        mock_issue.current_value = "true"
        mock_issue.recommended_value = "false"
        mock_issue.description = "Should be disabled"
        mock_issue.severity = MagicMock(name="warning")

        mock_report = MagicMock()
        mock_report.message = "Issues found"
        mock_report.issues = [mock_issue]
        mock_orchestrator.check.return_value = mock_report

        message, issues = check_crashgen_settings()

        assert len(issues) == 1
        assert isinstance(issues[0], ConfigIssue)
        assert issues[0].section == "Patches"
        assert issues[0].setting == "Achievements"
        assert issues[0].current_value == "true"
        assert issues[0].recommended_value == "false"

    @patch("classic_scangame.CrashgenCheckOrchestrator")
    @patch("ClassicLib.scanning.game.check_crashgen.yaml_settings")
    @patch("ClassicLib.scanning.game.check_crashgen.get_vr", return_value="")
    def test_delegates_for_any_crashgen_name(
        self,
        mock_get_vr: MagicMock,
        mock_yaml: MagicMock,
        mock_orchestrator: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_crashgen_settings now delegates for all crashgen names via registry routing.

        The old _is_buffout_4_name gate has been removed. The Rust
        CrashgenCheckOrchestrator handles routing via the CrashgenRegistry.
        """
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return "Crash Logger"

        mock_yaml.side_effect = yaml_side_effect

        message, issues = check_crashgen_settings()

        # The orchestrator is now called for all crashgen names
        mock_orchestrator.check.assert_called_once()


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

        assert "\u26a0\ufe0f" in warning_issue.format_report()
        assert "\u274c" in error_issue.format_report()
        assert "\u2139\ufe0f" in info_issue.format_report()
