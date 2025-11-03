"""Unit tests for FCX mode ConfigIssue data model."""

from pathlib import Path

import pytest

from ClassicLib.ScanGame.models.fcx_issue import ConfigIssue


@pytest.mark.unit
class TestConfigIssueDataModel:
    """Test ConfigIssue data structure and validation."""

    def test_config_issue_creation_with_valid_data(self) -> None:
        """Verify ConfigIssue can be created with valid data."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Main",
            setting="HotKey",
            current_value="; F10",
            recommended_value="0x79",
            description="Hotkey is commented out",
            severity="warning",
        )

        assert issue.file_path == Path("/test/file.ini")
        assert issue.section == "Main"
        assert issue.setting == "HotKey"
        assert issue.current_value == "; F10"
        assert issue.recommended_value == "0x79"
        assert issue.description == "Hotkey is commented out"
        assert issue.severity == "warning"

    def test_config_issue_with_no_section(self) -> None:
        """Verify ConfigIssue works with None section (TOML or non-sectioned)."""
        issue = ConfigIssue(
            file_path=Path("/test/file.toml"),
            section=None,
            setting="some_key",
            current_value="old",
            recommended_value="new",
            description="Test issue",
        )

        assert issue.section is None

    def test_config_issue_default_severity(self) -> None:
        """Verify ConfigIssue defaults to 'warning' severity."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Test",
            setting="key",
            current_value="1",
            recommended_value="2",
            description="Test",
        )

        assert issue.severity == "warning"

    def test_config_issue_converts_string_path_to_path_object(self) -> None:
        """Verify ConfigIssue converts string file_path to Path object."""
        issue = ConfigIssue(
            file_path="C:\\test\\file.ini",  # String, not Path
            section="Test",
            setting="key",
            current_value="1",
            recommended_value="2",
            description="Test",
        )

        assert isinstance(issue.file_path, Path)
        assert issue.file_path == Path("C:\\test\\file.ini")

    def test_config_issue_invalid_severity_raises_error(self) -> None:
        """Verify ConfigIssue raises ValueError for invalid severity."""
        with pytest.raises(ValueError, match="Invalid severity: invalid"):
            ConfigIssue(
                file_path=Path("/test/file.ini"),
                section="Test",
                setting="key",
                current_value="1",
                recommended_value="2",
                description="Test",
                severity="invalid",  # type: ignore[arg-type]
            )

    def test_format_report_with_warning_severity(self) -> None:
        """Verify format_report() generates correct markdown for warning."""
        issue = ConfigIssue(
            file_path=Path("C:\\test\\espexplorer.ini"),
            section="Main",
            setting="HotKey",
            current_value="; F10",
            recommended_value="0x79",
            description="Hotkey is commented out and won't work",
            severity="warning",
        )

        report = issue.format_report()

        assert "⚠️ DETECTED ISSUE:" in report
        assert "Hotkey is commented out and won't work" in report
        assert "File: C:\\test\\espexplorer.ini" in report
        assert "Section: [Main]" in report
        assert "Setting: HotKey" in report
        assert "Current Value: ; F10" in report
        assert "Recommended Value: 0x79" in report

    def test_format_report_with_error_severity(self) -> None:
        """Verify format_report() uses ❌ icon for error severity."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Test",
            setting="key",
            current_value="bad",
            recommended_value="good",
            description="Critical issue",
            severity="error",
        )

        report = issue.format_report()
        assert "❌ DETECTED ISSUE:" in report

    def test_format_report_with_info_severity(self) -> None:
        """Verify format_report() uses ℹ️ icon for info severity."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Test",
            setting="key",
            current_value="current",
            recommended_value="recommended",
            description="Informational issue",
            severity="info",
        )

        report = issue.format_report()
        assert "ℹ️ DETECTED ISSUE:" in report

    def test_format_report_with_no_section(self) -> None:
        """Verify format_report() shows 'N/A' for None section."""
        issue = ConfigIssue(
            file_path=Path("/test/file.toml"),
            section=None,
            setting="some_key",
            current_value="old",
            recommended_value="new",
            description="TOML issue",
        )

        report = issue.format_report()
        assert "Section: N/A" in report

    def test_format_report_ends_with_blank_line(self) -> None:
        """Verify format_report() ends with blank line for separation."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Test",
            setting="key",
            current_value="1",
            recommended_value="2",
            description="Test",
        )

        report = issue.format_report()
        assert report.endswith("\n\n")


@pytest.mark.asyncio
class TestGenerateGameCombinedResultTuple:
    """Test suite for Phase 5: tuple return signature from generate_game_combined_result()."""

    @pytest.mark.unit
    async def test_async_function_returns_tuple(self) -> None:
        """Test that generate_game_combined_result_async returns tuple[str, list[ConfigIssue]]."""
        from unittest.mock import patch

        from ClassicLib.ScanGame import generate_game_combined_result_async

        # Mock settings to return None (early return path)
        with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.yaml_settings") as mock_yaml_settings, \
             patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.GlobalRegistry") as mock_global_registry:

            mock_yaml_settings.return_value = None
            mock_global_registry.get_vr.return_value = ""

            # Call async function
            result = await generate_game_combined_result_async()

            # Verify tuple return
            assert isinstance(result, tuple), "Should return tuple"
            assert len(result) == 2, "Tuple should have 2 elements"
            assert isinstance(result[0], str), "First element should be str"
            assert isinstance(result[1], list), "Second element should be list"
            assert result == ("", []), "Should return empty tuple when paths missing"

    @pytest.mark.unit
    def test_sync_function_returns_tuple(self) -> None:
        """Test that generate_game_combined_result sync adapter returns tuple[str, list[ConfigIssue]]."""
        from unittest.mock import patch

        from ClassicLib.ScanGame import generate_game_combined_result

        # Mock settings to return None (early return path)
        with patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.yaml_settings") as mock_yaml_settings, \
             patch("ClassicLib.ScanGame.GameIntegrityOrchestrator.GlobalRegistry") as mock_global_registry:

            mock_yaml_settings.return_value = None
            mock_global_registry.get_vr.return_value = ""

            # Call sync function
            result = generate_game_combined_result()

            # Verify tuple return
            assert isinstance(result, tuple), "Should return tuple"
            assert len(result) == 2, "Tuple should have 2 elements"
            assert isinstance(result[0], str), "First element should be str"
            assert isinstance(result[1], list), "Second element should be list"

    @pytest.mark.unit
    def test_cli_wrapper_returns_str_only(self) -> None:
        """Test that CLI wrapper unpacks tuple and returns only string for backward compatibility."""
        from unittest.mock import patch

        from CLASSIC_ScanGame import game_combined_result

        with patch("CLASSIC_ScanGame.generate_game_combined_result") as mock_generate:
            # Mock to return tuple
            mock_generate.return_value = ("Test report content\n", [])

            # Call CLI wrapper
            result = game_combined_result()

            # Verify only string returned
            assert isinstance(result, str), "CLI wrapper should return str only"
            assert result == "Test report content\n"
            mock_generate.assert_called_once()


@pytest.mark.integration
class TestFCXModeHandlerPhase5Integration:
    """Integration tests for Phase 5: FCXModeHandler tuple unpacking."""

    @pytest.mark.unit
    def test_fcx_handler_unpacks_tuple_correctly(self) -> None:
        """Test that FCXModeHandler properly unpacks tuple from scan_game_files()."""
        from unittest.mock import Mock, patch

        from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments

        # Reset state
        FCXModeHandlerFragments.reset_fcx_checks()

        # Mock coordinator (patching at the import location inside the method)
        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as mock_coordinator_class, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_generate:

            mock_coordinator = Mock()
            mock_coordinator.generate_combined_results.return_value = "Main files OK\n"
            mock_coordinator_class.return_value = mock_coordinator

            # Mock generate_game_combined_result to return tuple
            test_issue = ConfigIssue(
                file_path=Path("/test/file.ini"),
                section="Main",
                setting="TestSetting",
                current_value="0",
                recommended_value="1",
                description="Test configuration issue",
                severity="warning"
            )
            mock_generate.return_value = ("Game files OK\n", [test_issue])

            # Create handler and run checks
            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            # Verify tuple was unpacked correctly
            assert handler.game_files_check == "Game files OK\n"
            assert len(FCXModeHandlerFragments._detected_issues) == 1
            assert FCXModeHandlerFragments._detected_issues[0] == test_issue

            # Verify report includes detected issue
            fragment = handler.get_fcx_messages()
            report_content = "".join(fragment.content)  # Join tuple of strings

            assert "DETECTED CONFIGURATION ISSUES" in report_content
            assert "Test configuration issue" in report_content

    @pytest.mark.unit
    def test_fcx_handler_handles_empty_issues_list(self) -> None:
        """Test that FCXModeHandler handles empty issues list correctly."""
        from unittest.mock import Mock, patch

        from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments

        # Reset state
        FCXModeHandlerFragments.reset_fcx_checks()

        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as mock_coordinator_class, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_generate:

            mock_coordinator = Mock()
            mock_coordinator.generate_combined_results.return_value = "Main files OK\n"
            mock_coordinator_class.return_value = mock_coordinator

            # Mock with empty issues list
            mock_generate.return_value = ("Game files OK\n", [])

            # Create handler and run checks
            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            # Verify empty issues list
            assert len(FCXModeHandlerFragments._detected_issues) == 0

            # Verify report does NOT include issues section when list is empty
            fragment = handler.get_fcx_messages()
            report_content = "".join(fragment.content)  # Join tuple of strings

            # Should not show issues section if no issues detected
            if not FCXModeHandlerFragments._detected_issues:
                assert "DETECTED CONFIGURATION ISSUES" not in report_content
