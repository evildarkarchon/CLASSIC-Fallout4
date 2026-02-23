"""Unit tests for FCX mode ConfigIssue data model."""

from pathlib import Path

import pytest

from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue


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
            file_path=Path("C:\\test\\file.ini"),  # String, not Path
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


class TestGenerateGameCombinedResultTuple:
    """Test suite for Phase 5: tuple return signature from generate_game_combined_result()."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_function_returns_tuple(self) -> None:
        """Test that generate_game_combined_result_async returns tuple[str, list[ConfigIssue]]."""
        from unittest.mock import patch

        from ClassicLib.scanning.game import generate_game_combined_result_async

        # Mock settings to return None (early return path)
        with patch("ClassicLib.scanning.game.orchestrator.yaml_settings") as mock_yaml_settings:
            mock_yaml_settings.return_value = None

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

        from ClassicLib.scanning.game import generate_game_combined_result

        # Mock settings to return None (early return path)
        with patch("ClassicLib.scanning.game.orchestrator.yaml_settings") as mock_yaml_settings:
            mock_yaml_settings.return_value = None

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

        from classic_scan_game import game_combined_result

        with patch("classic_scan_game.generate_game_combined_result") as mock_generate:
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
    """Integration tests for Phase 5: FCXModeHandler tuple unpacking.

    NOTE: The Python FCXModeHandlerFragments class was removed during the Rust
    migration. FCX handling is now done via get_fcx_handler() factory function
    which returns a Rust-backed wrapper. These tests now verify the factory
    behavior and the wrapper's basic functionality.
    """

    @pytest.mark.unit
    def test_fcx_handler_factory_returns_wrapper(self) -> None:
        """Test that get_fcx_handler returns a valid wrapper instance."""
        from unittest.mock import patch

        # Mock the Rust FcxModeHandler to avoid requiring actual Rust module
        with patch("ClassicLib.integration.factory.RustFcxModeHandler", create=True) as mock_rust:
            mock_rust.return_value = mock_rust
            from ClassicLib.integration.factory import get_fcx_handler

            handler = get_fcx_handler(fcx_mode=True)

            # Verify wrapper has expected attributes
            assert hasattr(handler, "fcx_mode")
            assert hasattr(handler, "check_fcx_mode")
            assert hasattr(handler, "get_fcx_messages")
            assert handler.fcx_mode is True

    @pytest.mark.unit
    def test_fcx_handler_reset_is_noop(self) -> None:
        """Test that reset_fcx_checks is a no-op for Rust wrapper."""
        from ClassicLib.integration.factory import FcxHandlerWrapper

        # Should not raise - just a no-op for Rust (resets automatically)
        FcxHandlerWrapper.reset_fcx_checks()
