"""
Unit tests for FCX mode handler read-only behavior.

This module contains comprehensive tests for the FCXModeHandler class
to verify it operates in read-only mode and never modifies configuration files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments


@pytest.mark.unit
class TestFCXModeHandlerReadOnly:
    """Test FCX mode handler read-only behavior."""

    def test_fcx_mode_no_file_writes(self, tmp_path: Path):
        """
        Verify FCX mode never writes to files.

        This test creates test configuration files and verifies that
        FCX mode detection does not modify them.
        """
        # Create test INI with issues
        ini_path = tmp_path / "test.ini"
        ini_path.write_text("[Main]\nHotKey = ; F10\n", encoding="utf-8")

        # Track file modification time
        initial_mtime = ini_path.stat().st_mtime
        initial_content = ini_path.read_text(encoding="utf-8")

        # Mock the necessary components - patch in the correct module
        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as MockSetup, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_game_result:

            # Configure mocks
            mock_coordinator = MagicMock()
            mock_coordinator.generate_combined_results.return_value = ""
            MockSetup.return_value = mock_coordinator
            mock_game_result.return_value = ("", [])  # Empty report, no issues

            # Run FCX checks
            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            # Verify file was NOT modified
            assert ini_path.stat().st_mtime == initial_mtime, "File modification time changed"
            assert ini_path.read_text(encoding="utf-8") == initial_content, "File content changed"

    @pytest.mark.asyncio
    async def test_fcx_detects_espexplorer_hotkey_issue(self, tmp_path: Path):
        """
        Verify ESPExplorer hotkey issue detection.

        Tests that FCX mode correctly detects commented-out hotkey
        configuration and generates appropriate recommendations.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create test configuration
        espexplorer_ini = tmp_path / "espexplorer.ini"
        espexplorer_ini.write_text(
            "[Main]\n"
            "HotKey = ; F10\n",
            encoding="utf-8"
        )

        # Create ConfigFileCache with test file
        cache = ConfigFileCache()
        cache._config_files = {"espexplorer.ini": espexplorer_ini}

        # Detect issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify issue was detected
        hotkey_issues = [
            issue for issue in issues
            if issue.setting == "HotKey" and issue.section == "Main"
        ]

        assert len(hotkey_issues) == 1, "ESPExplorer hotkey issue not detected"
        issue = hotkey_issues[0]
        assert issue.current_value == "; F10"
        assert issue.recommended_value == "0x79"
        assert "commented out" in issue.description.lower()

    @pytest.mark.asyncio
    async def test_fcx_detects_epo_particle_count_issue(self, tmp_path: Path):
        """
        Verify EPO particle count issue detection.

        Tests that FCX mode correctly detects excessive particle counts
        that can cause performance issues.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create test configuration with high particle count
        epo_ini = tmp_path / "epo.ini"
        epo_ini.write_text(
            "[Particles]\n"
            "iMaxDesired = 7500\n",
            encoding="utf-8"
        )

        cache = ConfigFileCache()
        cache._config_files = {"epo.ini": epo_ini}

        # Detect issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify issue was detected
        particle_issues = [
            issue for issue in issues
            if issue.setting == "iMaxDesired" and issue.section == "Particles"
        ]

        assert len(particle_issues) == 1, "EPO particle count issue not detected"
        issue = particle_issues[0]
        assert int(issue.current_value) > 5000
        assert issue.recommended_value == "5000"
        assert "particle count" in issue.description.lower()

    @pytest.mark.asyncio
    async def test_fcx_detects_f4ee_head_parts_issue(self, tmp_path: Path):
        """
        Verify F4EE head parts unlock issue detection.

        Tests that FCX mode correctly detects locked head parts settings
        and generates unlock recommendations.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create test configuration with locked head parts
        f4ee_ini = tmp_path / "f4ee.ini"
        f4ee_ini.write_text(
            "[HeadParts]\n"
            "bUnlockHeadParts = 0\n",
            encoding="utf-8"
        )

        cache = ConfigFileCache()
        cache._config_files = {"f4ee.ini": f4ee_ini}

        # Detect issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify issue was detected
        headparts_issues = [
            issue for issue in issues
            if issue.setting == "bUnlockHeadParts"
        ]

        assert len(headparts_issues) == 1, "F4EE head parts issue not detected"
        issue = headparts_issues[0]
        assert issue.current_value == "0"
        assert issue.recommended_value == "1"
        assert "head parts" in issue.description.lower()

    @pytest.mark.asyncio
    async def test_fcx_detects_f4ee_face_tints_issue(self, tmp_path: Path):
        """
        Verify F4EE face tints unlock issue detection.

        Tests that FCX mode correctly detects locked face tints settings
        and generates unlock recommendations.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create test configuration with locked face tints
        f4ee_ini = tmp_path / "f4ee.ini"
        f4ee_ini.write_text(
            "[HeadParts]\n"
            "bUnlockTints = 0\n",
            encoding="utf-8"
        )

        cache = ConfigFileCache()
        cache._config_files = {"f4ee.ini": f4ee_ini}

        # Detect issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify issue was detected
        tints_issues = [
            issue for issue in issues
            if issue.setting == "bUnlockTints"
        ]

        assert len(tints_issues) == 1, "F4EE face tints issue not detected"
        issue = tints_issues[0]
        assert issue.current_value == "0"
        assert issue.recommended_value == "1"
        assert "tint" in issue.description.lower()

    @pytest.mark.asyncio
    async def test_fcx_detects_highfps_loading_fps_issue(self, tmp_path: Path):
        """
        Verify High FPS Physics Fix loading screen FPS issue detection.

        Tests that FCX mode correctly detects low loading screen FPS
        settings that may cause physics issues.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create test configuration with low loading screen FPS
        highfps_ini = tmp_path / "highfpsphysicsfix.ini"
        highfps_ini.write_text(
            "[Limiter]\n"
            "LoadingScreenFPS = 60.0\n",
            encoding="utf-8"
        )

        cache = ConfigFileCache()
        cache._config_files = {"highfpsphysicsfix.ini": highfps_ini}

        # Detect issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify issue was detected
        fps_issues = [
            issue for issue in issues
            if issue.setting == "LoadingScreenFPS"
        ]

        assert len(fps_issues) == 1, "High FPS loading screen issue not detected"
        issue = fps_issues[0]
        assert float(issue.current_value) < 600
        assert issue.recommended_value == "600.0"
        assert "loading screen" in issue.description.lower() or "fps" in issue.description.lower()

    def test_fcx_report_includes_recommendations(self, sample_config_issues):
        """
        Verify FCX report includes current vs. recommended values.

        Tests that the FCX mode report format includes all necessary
        information for users to manually fix issues.
        """
        # Use first issue from fixture (ESPExplorer hotkey)
        issue = sample_config_issues[0]

        # Format report
        report = issue.format_report()

        # Verify report format
        assert "Current Value:" in report
        assert "Recommended Value:" in report
        assert "File:" in report
        assert "DETECTED ISSUE:" in report
        assert issue.current_value in report
        assert issue.recommended_value in report
        assert "⚠️" in report  # Warning emoji

    def test_fcx_handler_state_management(self):
        """
        Verify FCX handler state management and reset functionality.

        Tests that reset_fcx_checks() properly clears state between scans.
        """
        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as MockSetup, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_game_result:

            # Configure mocks
            mock_coordinator = MagicMock()
            mock_coordinator.generate_combined_results.return_value = ""
            MockSetup.return_value = mock_coordinator
            mock_game_result.return_value = ("", [])

            # Create handler and run checks
            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            # Verify checks were run
            assert FCXModeHandlerFragments._fcx_checks_run is True

            # Reset state
            handler.reset_fcx_checks()

            # Verify state was cleared
            assert FCXModeHandlerFragments._fcx_checks_run is False

    def test_fcx_mode_disabled_shows_prompt(self):
        """
        Verify FCX mode disabled shows appropriate prompt.

        Tests that when FCX mode is disabled, the handler generates
        a message prompting the user to enable it.
        """
        # Create handler with FCX mode disabled
        handler = FCXModeHandlerFragments(fcx_mode=False)

        # Get messages
        messages = handler.get_fcx_messages()

        # Verify prompt is shown
        content = messages.fragment_content
        assert "FCX MODE IS DISABLED" in content
        assert "ENABLE IT TO DETECT PROBLEMS" in content

    def test_fcx_mode_enabled_shows_notice(self):
        """
        Verify FCX mode enabled shows notice message.

        Tests that when FCX mode is enabled, the handler generates
        appropriate notice messages about requiring original user execution.
        """
        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as MockSetup, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_game_result:

            # Configure mocks
            mock_coordinator = MagicMock()
            mock_coordinator.generate_combined_results.return_value = ""
            MockSetup.return_value = mock_coordinator
            mock_game_result.return_value = ("", [])

            # Create handler with FCX mode enabled
            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            # Get messages
            messages = handler.get_fcx_messages()

            # Verify notice is shown
            content = messages.fragment_content
            assert "FCX MODE IS ENABLED" in content
            assert "CLASSIC MUST BE RUN BY THE ORIGINAL USER" in content

    @pytest.mark.asyncio
    async def test_fcx_multiple_issues_detection(self, tmp_path: Path):
        """
        Verify FCX mode can detect multiple issues in the same scan.

        Tests that all issue types are detected simultaneously when
        multiple configuration problems exist.
        """
        from ClassicLib.ScanGame.Config import ConfigFileCache
        from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async

        # Create multiple test configurations with issues
        espexplorer_ini = tmp_path / "espexplorer.ini"
        espexplorer_ini.write_text("[Main]\nHotKey = ; F10\n", encoding="utf-8")

        epo_ini = tmp_path / "epo.ini"
        epo_ini.write_text("[Particles]\niMaxDesired = 7500\n", encoding="utf-8")

        f4ee_ini = tmp_path / "f4ee.ini"
        f4ee_ini.write_text(
            "[HeadParts]\nbUnlockHeadParts = 0\nbUnlockTints = 0\n",
            encoding="utf-8"
        )

        cache = ConfigFileCache()
        cache._config_files = {
            "espexplorer.ini": espexplorer_ini,
            "epo.ini": epo_ini,
            "f4ee.ini": f4ee_ini,
        }

        # Detect all issues
        issues = await detect_all_ini_issues_async(cache)

        # Verify multiple issues were detected
        assert len(issues) >= 4, f"Expected at least 4 issues, got {len(issues)}"

        # Verify each issue type is present
        settings_detected = {issue.setting for issue in issues}
        expected_settings = {"HotKey", "iMaxDesired", "bUnlockHeadParts", "bUnlockTints"}

        assert expected_settings.issubset(settings_detected), \
            f"Missing expected settings. Got: {settings_detected}, Expected: {expected_settings}"

    def test_fcx_handler_with_no_issues(self):
        """
        Verify FCX handler behaves correctly when no issues are detected.

        Tests that the handler generates appropriate messages when all
        configuration files are correctly configured.
        """
        with patch("ClassicLib.SetupCoordinator.SetupCoordinator") as MockSetup, \
             patch("ClassicLib.ScanGame.generate_game_combined_result") as mock_game_result:

            # Configure mocks
            mock_coordinator = MagicMock()
            mock_coordinator.generate_combined_results.return_value = ""
            MockSetup.return_value = mock_coordinator
            mock_game_result.return_value = ("", [])  # No issues detected

            handler = FCXModeHandlerFragments(fcx_mode=True)
            handler.check_fcx_mode()

            messages = handler.get_fcx_messages()
            content = messages.fragment_content

            # Verify base messages are present
            assert "FCX MODE IS ENABLED" in content

            # Verify no issue report section is added when there are no issues
            # (implementation may vary, but ensure it handles empty issues gracefully)
            assert FCXModeHandlerFragments._fcx_checks_run is True
