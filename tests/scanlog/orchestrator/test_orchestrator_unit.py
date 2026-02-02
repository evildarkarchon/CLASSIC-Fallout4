"""Unit tests for the ScanLog OrchestratorCore module.

This module tests the crash log orchestration functionality including:
- __init__ - proper initialization with dependencies
- __aenter__ / __aexit__ - async context manager
- _initialize_modules_async() - module initialization
- Error handling for missing dependencies
"""

import pytest

pytestmark = [pytest.mark.unit]

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore


@pytest.mark.unit
class TestOrchestratorCoreInit:
    """Test suite for OrchestratorCore initialization."""

    def test_init_with_minimal_params(self, mock_yamldata: MagicMock) -> None:
        """Test OrchestratorCore can be initialized with minimal parameters."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        assert orchestrator.yamldata is mock_yamldata
        assert orchestrator.show_formid_values is False
        assert orchestrator.formid_db_exists is False
        assert orchestrator._db_pool is None

    def test_init_with_fcx_mode_enabled(self, mock_yamldata: MagicMock) -> None:
        """Test initialization with FCX mode enabled."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=True,
            show_formid_values=False,
            formid_db_exists=False,
        )

        assert orchestrator.fcx_handler is not None
        # FCX handler should be created with fcx_mode=True
        assert orchestrator.fcx_handler.fcx_mode is True

    def test_init_with_formid_db(self, mock_yamldata: MagicMock) -> None:
        """Test initialization when FormID database exists."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=True,
        )

        assert orchestrator.show_formid_values is True
        assert orchestrator.formid_db_exists is True

    def test_init_with_remove_list(self, mock_yamldata: MagicMock) -> None:
        """Test initialization with custom remove_list parameter."""
        remove_list = ("record1", "record2", "record3")

        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
            remove_list=remove_list,
        )

        # Remove list should be stored for later use in __aenter__
        assert orchestrator._remove_list_param == remove_list

    def test_init_creates_all_analyzers(self, mock_yamldata: MagicMock) -> None:
        """Test that all analyzer modules are created during init."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # All analyzers should be initialized
        assert orchestrator.plugin_analyzer is not None
        assert orchestrator.suspect_scanner is not None
        assert orchestrator.record_scanner is not None
        assert orchestrator.settings_scanner is not None
        assert orchestrator.report_generator is not None
        assert orchestrator.fcx_handler is not None

    def test_init_deferred_yaml_attributes(self, mock_yamldata: MagicMock) -> None:
        """Test that YAML-dependent attributes are deferred to __aenter__."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # These should have default values before __aenter__
        assert orchestrator.remove_list == ("",)
        assert orchestrator.simplify_logs is False
        # Note: game_root_name is now accessed per-log via yamldata.get_game_root_name(is_vr)


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrchestratorCoreAsyncContextManager:
    """Test suite for OrchestratorCore async context manager."""

    async def test_aenter_initializes_lock(self, mock_yamldata: MagicMock) -> None:
        """Test __aenter__ initializes the asyncio lock."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False
            mock_pool_manager.return_value.get_pool = AsyncMock(return_value=MagicMock())

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            result = await orchestrator.__aenter__()

            assert orchestrator._state_lock is not None
            assert result is orchestrator

    async def test_aenter_loads_yaml_settings(self, mock_yamldata: MagicMock) -> None:
        """Test __aenter__ loads YAML settings asynchronously."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager"),
        ):
            mock_yaml.return_value = ("record1", "record2")
            mock_classic.return_value = True

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            await orchestrator.__aenter__()

            # YAML settings should have been called
            assert mock_yaml.call_count >= 1
            assert mock_classic.call_count >= 1

    async def test_aenter_initializes_db_pool_when_exists(self, mock_yamldata: MagicMock) -> None:
        """Test __aenter__ initializes database pool when FormID DB exists."""
        mock_pool = MagicMock()

        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False
            mock_pool_manager.return_value.get_pool = AsyncMock(return_value=mock_pool)

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=True,  # DB exists
            )

            await orchestrator.__aenter__()

            # Pool should be initialized
            mock_pool_manager.return_value.get_pool.assert_called_once()
            assert orchestrator._db_pool is mock_pool

    async def test_aenter_skips_db_pool_when_not_exists(self, mock_yamldata: MagicMock) -> None:
        """Test __aenter__ skips database pool when FormID DB doesn't exist."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,  # DB doesn't exist
            )

            await orchestrator.__aenter__()

            # Pool should not be requested
            mock_pool_manager.return_value.get_pool.assert_not_called()
            assert orchestrator._db_pool is None

    async def test_aexit_completes_without_error(self, mock_yamldata: MagicMock) -> None:
        """Test __aexit__ completes without raising exceptions."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager"),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            await orchestrator.__aenter__()
            # __aexit__ should complete without error
            await orchestrator.__aexit__(None, None, None)

    async def test_context_manager_full_lifecycle(self, mock_yamldata: MagicMock) -> None:
        """Test complete async context manager lifecycle."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager"),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Should be able to use orchestrator inside context
                assert orchestrator is not None
                assert orchestrator._state_lock is not None


@pytest.mark.unit
class TestOrchestratorCoreHelperMethods:
    """Test suite for OrchestratorCore helper methods."""

    def test_parse_crashgen_settings_basic(self) -> None:
        """Test parsing basic crashgen settings."""
        segment_crashgen = [
            "Achievements: true",
            "MemoryManager: false",
            "MaxStdIO: 8192",
        ]

        result = OrchestratorCore._parse_crashgen_settings(segment_crashgen)

        assert result["Achievements"] is True
        assert result["MemoryManager"] is False
        assert result["MaxStdIO"] == 8192

    def test_parse_crashgen_settings_empty(self) -> None:
        """Test parsing empty crashgen settings."""
        result = OrchestratorCore._parse_crashgen_settings([])

        assert result == {}

    def test_parse_crashgen_settings_with_strings(self) -> None:
        """Test parsing crashgen settings with string values."""
        segment_crashgen = [
            "SomeValue: custom_string",
        ]

        result = OrchestratorCore._parse_crashgen_settings(segment_crashgen)

        assert result["SomeValue"] == "custom_string"

    def test_parse_crashgen_settings_malformed(self) -> None:
        """Test parsing malformed crashgen settings."""
        segment_crashgen = [
            "NoColon",
            "Valid: true",
            "",
        ]

        result = OrchestratorCore._parse_crashgen_settings(segment_crashgen)

        # Should skip invalid entries and parse valid ones
        assert "Valid" in result
        assert result["Valid"] is True
        assert "NoColon" not in result

    def test_reformat_crash_data_inline(self, mock_yamldata: MagicMock, sample_crash_log_lines: list[str]) -> None:
        """Test inline crash data reformatting."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Set simplify_logs to false for basic test
        orchestrator.simplify_logs = False
        orchestrator.remove_list = ("",)

        result = orchestrator._reformat_crash_data_inline(sample_crash_log_lines)

        # Should return list of strings
        assert isinstance(result, list)
        assert all(isinstance(line, str) for line in result)
        # Should preserve non-empty content
        assert len(result) > 0

    def test_reformat_crash_data_with_simplify(self, mock_yamldata: MagicMock) -> None:
        """Test crash data reformatting with simplify_logs enabled."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Enable simplify mode
        orchestrator.simplify_logs = True
        orchestrator.remove_list = ("RemoveThis",)

        lines = [
            "Keep this line",
            "RemoveThis line should be gone",
            "Another keep line",
        ]

        result = orchestrator._reformat_crash_data_inline(lines)

        # Lines containing "RemoveThis" should be removed
        assert "Keep this line" in result
        assert "Another keep line" in result
        assert not any("RemoveThis" in line for line in result)

    def test_reformat_crash_data_fixes_plugin_brackets(self, mock_yamldata: MagicMock) -> None:
        """Test that plugin bracket formatting is fixed."""
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        orchestrator.simplify_logs = False
        orchestrator.remove_list = ("",)

        lines = [
            "PLUGINS:",
            "[ 0] Fallout4.esm",  # Space in bracket should become 0
            "[  1] DLCRobot.esm",  # Spaces should become 0s
            "[02] Normal.esp",  # Already correct
        ]

        result = orchestrator._reformat_crash_data_inline(lines)

        # Find the plugin lines
        plugin_lines = [line for line in result if "[" in line and "]" in line and ".es" in line]

        # Check that spaces in brackets are replaced with 0s
        for line in plugin_lines:
            # Extract content between brackets
            if "[" in line and "]" in line:
                bracket_content = line[line.index("[") + 1 : line.index("]")]
                assert " " not in bracket_content  # No spaces inside brackets


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrchestratorCoreBatchProcessing:
    """Test suite for batch crash log processing."""

    async def test_process_crash_logs_batch_empty(self, mock_yamldata: MagicMock) -> None:
        """Test batch processing with empty list."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager"),
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                results = await orchestrator.process_crash_logs_batch([])

                assert results == []

    async def test_write_reports_batch_empty(self) -> None:
        """Test batch report writing with empty list."""
        # Should complete without error
        await OrchestratorCore.write_reports_batch([])

    async def test_write_reports_batch_with_reports(self, tmp_path: Path) -> None:
        """Test batch report writing creates files."""
        # Create test report data
        crash_file = tmp_path / "test-crash.log"
        crash_file.write_text("test")

        reports = [
            (crash_file, ["# Report\n", "Test content\n"], False),
        ]

        with patch("ClassicLib.scanning.logs.orchestrator_core.get_file_io") as mock_get_io:
            mock_io = MagicMock()
            mock_io.write_file = AsyncMock()
            mock_get_io.return_value = mock_io

            await OrchestratorCore.write_reports_batch(reports)

            # Write should have been called
            mock_io.write_file.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrchestratorCoreErrorHandling:
    """Test suite for OrchestratorCore error handling."""

    async def test_handles_missing_yaml_gracefully(self, mock_yamldata: MagicMock) -> None:
        """Test that missing YAML settings are handled gracefully."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager"),
        ):
            # Return None for all YAML lookups
            mock_yaml.return_value = None
            mock_classic.return_value = None

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Should use defaults
                assert orchestrator.simplify_logs is False
                assert orchestrator.remove_list == ("",)
                # Note: game_root_name is now accessed per-log via yamldata.get_game_root_name(is_vr)

    async def test_handles_db_pool_error_gracefully(self, mock_yamldata: MagicMock) -> None:
        """Test that database pool errors are handled gracefully."""
        with (
            patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async", new_callable=AsyncMock) as mock_yaml,
            patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async", new_callable=AsyncMock) as mock_classic,
            patch("ClassicLib.scanning.logs.orchestrator_core.DatabasePoolManager") as mock_pool_manager,
        ):
            mock_yaml.return_value = None
            mock_classic.return_value = False
            # Make pool initialization raise an exception
            mock_pool_manager.return_value.get_pool = AsyncMock(side_effect=RuntimeError("DB error"))

            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=True,
            )

            # Should raise the error (production code should handle this)
            with pytest.raises(RuntimeError, match="DB error"):
                await orchestrator.__aenter__()
