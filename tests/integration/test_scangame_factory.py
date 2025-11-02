"""Integration tests for ScanGame factory module.

Tests the transparent Rust acceleration layer with automatic fallback
to Python implementations when Rust modules are not available.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from ClassicLib.integration import scangame_factory


@pytest.mark.integration
class TestFactoryRustDetection:
    """Test Rust availability detection."""

    def test_is_rust_available_reflects_import_state(self):
        """Test that is_rust_available() reflects actual Rust module state."""
        result = scangame_factory.is_rust_available()
        assert isinstance(result, bool)
        assert result == scangame_factory._RUST_AVAILABLE

    def test_get_rust_status_returns_complete_info(self):
        """Test that get_rust_status() returns complete status information."""
        status = scangame_factory.get_rust_status()

        assert isinstance(status, dict)
        assert "available" in status
        assert "version" in status
        assert "components" in status

        assert isinstance(status["available"], bool)
        assert status["version"] is None or isinstance(status["version"], str)
        assert isinstance(status["components"], list)

        if status["available"]:
            assert len(status["components"]) == 7


@pytest.mark.integration
class TestFactoryBA2Scanner:
    """Test BA2Scanner factory function."""

    def test_get_ba2_scanner_returns_scanner_instance(self):
        """Test that get_ba2_scanner() returns a valid scanner instance."""
        scanner = scangame_factory.get_ba2_scanner()

        assert hasattr(scanner, "scan_archive")
        assert hasattr(scanner, "scan_archives_batch")
        assert callable(scanner.scan_archive)
        assert callable(scanner.scan_archives_batch)

    def test_ba2_scanner_scan_archives_batch_with_empty_list(self):
        """Test BA2Scanner.scan_archives_batch() with empty list."""
        scanner = scangame_factory.get_ba2_scanner()
        results = scanner.scan_archives_batch([])

        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.integration
class TestFactoryConfigDuplicateDetector:
    """Test ConfigDuplicateDetector factory function."""

    def test_get_config_duplicate_detector_returns_detector_instance(self):
        """Test that get_config_duplicate_detector() returns valid detector."""
        detector = scangame_factory.get_config_duplicate_detector()

        assert hasattr(detector, "detect_duplicates")
        assert hasattr(detector, "get_duplicate_map")
        assert callable(detector.detect_duplicates)
        assert callable(detector.get_duplicate_map)

    def test_config_duplicate_detector_with_nonexistent_path(self):
        """Test ConfigDuplicateDetector with nonexistent directory."""
        detector = scangame_factory.get_config_duplicate_detector()
        nonexistent = Path("/nonexistent/directory")

        duplicates = detector.detect_duplicates(nonexistent)

        assert isinstance(duplicates, list)
        assert len(duplicates) == 0

    def test_config_duplicate_detector_get_duplicate_map_returns_dict(self):
        """Test ConfigDuplicateDetector.get_duplicate_map() returns dict."""
        detector = scangame_factory.get_config_duplicate_detector()
        nonexistent = Path("/nonexistent")

        dup_map = detector.get_duplicate_map(nonexistent)

        assert isinstance(dup_map, dict)


@pytest.mark.integration
class TestFactoryUnpackedScanner:
    """Test UnpackedScanner factory function."""

    def test_get_unpacked_scanner_returns_scanner_instance(self):
        """Test that get_unpacked_scanner() returns valid scanner."""
        scanner = scangame_factory.get_unpacked_scanner()

        assert hasattr(scanner, "scan_directory")
        assert callable(scanner.scan_directory)


@pytest.mark.integration
class TestFactoryLogProcessor:
    """Test LogProcessor factory function."""

    def test_get_log_processor_returns_processor_instance(self):
        """Test that get_log_processor() returns valid processor."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=["debug.log"],
            ignore_errors=["benign"],
        )

        assert hasattr(processor, "process_logs")
        assert callable(processor.process_logs)


@pytest.mark.integration
class TestFactoryIniValidator:
    """Test IniValidator factory function."""

    def test_get_ini_validator_returns_validator_instance(self):
        """Test that get_ini_validator() returns valid validator."""
        validator = scangame_factory.get_ini_validator("Fallout4")

        assert hasattr(validator, "validate_inis")
        assert hasattr(validator, "detect_all_issues")
        assert callable(validator.validate_inis)
        assert callable(validator.detect_all_issues)


@pytest.mark.integration
class TestFactoryCrashgenChecker:
    """Test CrashgenChecker factory function."""

    def test_get_crashgen_checker_returns_checker_instance(self):
        """Test that get_crashgen_checker() returns valid checker."""
        checker = scangame_factory.get_crashgen_checker(
            plugins_path=Path("/fake/plugins"),
            crashgen_name="Buffout4",
        )

        assert hasattr(checker, "check")
        assert callable(checker.check)


@pytest.mark.integration
class TestFactoryXseChecker:
    """Test XseChecker factory function."""

    def test_get_xse_checker_returns_checker_instance(self, tmp_path):
        """Test that get_xse_checker() returns valid checker."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        checker = scangame_factory.get_xse_checker(plugins_path=plugins_path)

        assert hasattr(checker, "check")
        assert hasattr(checker, "validate")
        assert callable(checker.check)
        assert callable(checker.validate)

    def test_get_xse_checker_with_vr_mode(self, tmp_path):
        """Test get_xse_checker() with VR mode enabled."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        checker = scangame_factory.get_xse_checker(
            plugins_path=plugins_path,
            is_vr_mode=True,
        )

        assert hasattr(checker, "check")
        assert callable(checker.check)


@pytest.mark.integration
class TestFactoryFallbackBehavior:
    """Test fallback behavior when Rust is unavailable."""

    def test_factory_with_rust_disabled(self):
        """Test that factory falls back to Python when Rust import fails."""
        with patch.object(scangame_factory, "_RUST_AVAILABLE", False):
            with patch.object(scangame_factory, "_classic_scangame", None):
                scanner = scangame_factory.get_ba2_scanner()
                assert hasattr(scanner, "scan_archive")

                detector = scangame_factory.get_config_duplicate_detector()
                assert hasattr(detector, "detect_duplicates")

                unpacked = scangame_factory.get_unpacked_scanner()
                assert hasattr(unpacked, "scan_directory")

                log_proc = scangame_factory.get_log_processor([], [], [])
                assert hasattr(log_proc, "process_logs")

                ini_val = scangame_factory.get_ini_validator("Fallout4")
                assert hasattr(ini_val, "validate_inis")

    def test_is_rust_available_with_rust_disabled(self):
        """Test is_rust_available() returns False when Rust unavailable."""
        with patch.object(scangame_factory, "_RUST_AVAILABLE", False):
            assert scangame_factory.is_rust_available() is False

    def test_get_rust_status_with_rust_disabled(self):
        """Test get_rust_status() with Rust unavailable."""
        with patch.object(scangame_factory, "_RUST_AVAILABLE", False):
            status = scangame_factory.get_rust_status()

            assert status["available"] is False
            assert status["version"] is None
            assert status["components"] == []


@pytest.mark.integration
@pytest.mark.rust
@pytest.mark.skipif(
    not scangame_factory.is_rust_available(),
    reason="Rust acceleration not available",
)
class TestFactoryRustAcceleration:
    """Test factory with Rust acceleration enabled."""

    def test_rust_scanner_returns_rust_types(self):
        """Test that factory returns actual Rust types when available."""
        scanner = scangame_factory.get_ba2_scanner()

        rust_scanner_type = type(scangame_factory._classic_scangame.BA2Scanner())
        assert isinstance(scanner, rust_scanner_type)

    def test_rust_status_shows_version(self):
        """Test that Rust status includes version information."""
        status = scangame_factory.get_rust_status()

        assert status["available"] is True
        assert status["version"] is not None
        assert len(status["components"]) == 7

    def test_all_rust_scanners_available(self, tmp_path):
        """Test that all 7 scanner types return Rust implementations."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        ba2 = scangame_factory.get_ba2_scanner()
        assert isinstance(ba2, type(scangame_factory._classic_scangame.BA2Scanner()))

        config = scangame_factory.get_config_duplicate_detector()
        assert isinstance(config, type(scangame_factory._classic_scangame.ConfigDuplicateDetector()))

        unpacked = scangame_factory.get_unpacked_scanner()
        assert isinstance(unpacked, type(scangame_factory._classic_scangame.UnpackedScanner()))

        log_proc = scangame_factory.get_log_processor([], [], [])
        assert isinstance(log_proc, type(scangame_factory._classic_scangame.LogProcessor([], [], [])))

        ini_val = scangame_factory.get_ini_validator("Fallout4")
        assert isinstance(ini_val, type(scangame_factory._classic_scangame.IniValidator("Fallout4")))

        crashgen = scangame_factory.get_crashgen_checker(plugins_path, "Buffout4")
        assert isinstance(crashgen, type(scangame_factory._classic_scangame.CrashgenChecker(plugins_path, "Buffout4")))

        xse = scangame_factory.get_xse_checker(plugins_path)
        game_version = scangame_factory._classic_scangame.GameVersion.Original
        assert isinstance(xse, type(scangame_factory._classic_scangame.XseChecker(plugins_path, False, game_version)))
