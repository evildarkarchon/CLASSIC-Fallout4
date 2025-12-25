"""Integration tests for Rust scanner implementations.

Tests the actual functionality of Rust-accelerated scanners when available.
These tests only run when classic_scangame is installed.
"""

from pathlib import Path

import pytest

from ClassicLib.integration import scangame_factory

# Skip all tests in this module if Rust is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.rust,
    pytest.mark.skipif(
        not scangame_factory.is_rust_available(),
        reason="Rust acceleration not available",
    ),
]


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


class TestRustBA2Scanner:
    """Test Rust BA2Scanner implementation."""

    def test_ba2_scanner_initialization(self):
        """Test that BA2Scanner can be instantiated."""
        scanner = scangame_factory.get_ba2_scanner()
        assert scanner is not None

    def test_ba2_scanner_scan_nonexistent_archive(self):
        """Test scanning a nonexistent BA2 archive."""
        scanner = scangame_factory.get_ba2_scanner()
        nonexistent = Path("/nonexistent/test.ba2")

        # Rust implementation raises RuntimeError (os error) for nonexistent files
        with pytest.raises(RuntimeError):
            scanner.scan_archive(nonexistent)

    def test_ba2_scanner_batch_with_multiple_files(self, temp_dir):
        """Test batch scanning with multiple archives."""
        scanner = scangame_factory.get_ba2_scanner()

        # Create fake archives
        archives = []
        for i in range(3):
            path = temp_dir / f"archive{i}.ba2"
            path.touch()  # Create empty file
            archives.append(path)

        # Empty files might raise error or return empty results depending on parser strictness
        try:
            results = scanner.scan_archives_batch(archives)
            assert isinstance(results, list)
        except RuntimeError:
            pass


class TestRustConfigDuplicateDetector:
    """Test Rust ConfigDuplicateDetector implementation."""

    def test_config_duplicate_detector_initialization(self):
        """Test that ConfigDuplicateDetector can be instantiated."""
        detector = scangame_factory.get_config_duplicate_detector()
        assert detector is not None

    def test_config_duplicate_detector_empty_directory(self, temp_dir):
        """Test detecting duplicates in empty directory."""
        detector = scangame_factory.get_config_duplicate_detector()

        duplicates = detector.detect_duplicates(temp_dir)

        assert isinstance(duplicates, list)
        assert len(duplicates) == 0

    def test_config_duplicate_detector_single_file(self, temp_dir):
        """Test with a single INI file (no duplicates)."""
        detector = scangame_factory.get_config_duplicate_detector()

        # Create single INI file
        ini_file = temp_dir / "test.ini"
        ini_file.write_text("[Section]\nkey=value\n")

        duplicates = detector.detect_duplicates(temp_dir)

        # No duplicates for single file
        assert len(duplicates) == 0

    def test_config_duplicate_detector_get_duplicate_map(self, temp_dir):
        """Test get_duplicate_map method."""
        detector = scangame_factory.get_config_duplicate_detector()

        dup_map = detector.get_duplicate_map(temp_dir)

        assert isinstance(dup_map, dict)


class TestRustUnpackedScanner:
    """Test Rust UnpackedScanner implementation."""

    def test_unpacked_scanner_initialization(self):
        """Test that UnpackedScanner can be instantiated."""
        scanner = scangame_factory.get_unpacked_scanner()
        assert scanner is not None

    def test_unpacked_scanner_empty_directory(self, temp_dir):
        """Test scanning empty directory."""
        scanner = scangame_factory.get_unpacked_scanner()

        issues = scanner.scan_directory(temp_dir, ["f4se.dll"])

        assert hasattr(issues, "animdata")
        assert hasattr(issues, "tex_frmt")
        assert hasattr(issues, "snd_frmt")
        assert hasattr(issues, "xse_file")
        assert hasattr(issues, "previs")
        assert hasattr(issues, "dds_files")
        assert issues.has_issues() is False
        assert issues.total_count() == 0

    def test_unpacked_scanner_with_texture_files(self, temp_dir):
        """Test detection of texture format issues."""
        scanner = scangame_factory.get_unpacked_scanner()

        # Create TGA and PNG files
        (temp_dir / "texture.tga").write_bytes(b"fake tga data")
        (temp_dir / "texture.png").write_bytes(b"fake png data")

        issues = scanner.scan_directory(temp_dir, [])

        # Should detect texture format issues
        assert len(issues.tex_frmt) > 0
        assert issues.has_issues() is True
        assert issues.total_count() > 0

    def test_unpacked_scanner_with_sound_files(self, temp_dir):
        """Test detection of sound format issues."""
        scanner = scangame_factory.get_unpacked_scanner()

        # Create MP3 and M4A files
        (temp_dir / "sound.mp3").write_bytes(b"fake mp3 data")
        (temp_dir / "sound.m4a").write_bytes(b"fake m4a data")

        issues = scanner.scan_directory(temp_dir, [])

        # Should detect sound format issues
        assert len(issues.snd_frmt) > 0
        assert issues.has_issues() is True

    def test_unpacked_scanner_with_animation_data(self, temp_dir):
        """Test detection of animation data directories."""
        scanner = scangame_factory.get_unpacked_scanner()

        # Create AnimationFileData directory
        anim_dir = temp_dir / "AnimationFileData"
        anim_dir.mkdir()

        issues = scanner.scan_directory(temp_dir, [])

        # Should detect animation data
        assert len(issues.animdata) > 0
        assert issues.has_issues() is True


class TestRustLogProcessor:
    """Test Rust LogProcessor implementation."""

    def test_log_processor_initialization(self):
        """Test that LogProcessor can be instantiated."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=[],
            ignore_errors=[],
        )
        assert processor is not None

    def test_log_processor_empty_directory(self, temp_dir):
        """Test processing logs in empty directory."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=[],
            ignore_errors=[],
        )

        report = processor.process_logs(temp_dir)

        assert isinstance(report, str)
        assert len(report) == 0  # No logs, empty report

    def test_log_processor_with_clean_log(self, temp_dir):
        """Test processing log file with no errors."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=[],
            ignore_errors=[],
        )

        # Create log file with no errors
        log_file = temp_dir / "test.log"
        log_file.write_text("INFO: Application started\nINFO: Processing complete\n")

        report = processor.process_logs(temp_dir)

        assert isinstance(report, str)
        assert len(report) == 0  # No errors detected

    def test_log_processor_with_errors(self, temp_dir):
        """Test processing log file with errors."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=[],
            ignore_errors=[],
        )

        # Create log file with errors
        log_file = temp_dir / "test.log"
        log_file.write_text("INFO: Started\nERROR: Something went wrong\nINFO: Finished\n")

        report = processor.process_logs(temp_dir)

        assert isinstance(report, str)
        assert len(report) > 0  # Should have error report
        assert "ERROR" in report or "error" in report.lower()

    def test_log_processor_ignore_files(self, temp_dir):
        """Test that ignored files are skipped."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=["debug.log"],
            ignore_errors=[],
        )

        # Create ignored log file with errors
        log_file = temp_dir / "debug.log"
        log_file.write_text("ERROR: This should be ignored\n")

        report = processor.process_logs(temp_dir)

        assert isinstance(report, str)
        assert len(report) == 0  # File was ignored

    def test_log_processor_ignore_errors(self, temp_dir):
        """Test that ignored error patterns are filtered."""
        processor = scangame_factory.get_log_processor(
            catch_errors=["error"],
            ignore_files=[],
            ignore_errors=["benign"],
        )

        # Create log file with ignorable error
        log_file = temp_dir / "test.log"
        log_file.write_text("ERROR: This is a benign error\n")

        report = processor.process_logs(temp_dir)

        assert isinstance(report, str)
        assert len(report) == 0  # Error pattern was ignored


class TestRustIniValidator:
    """Test Rust IniValidator implementation."""

    def test_ini_validator_initialization(self):
        """Test that IniValidator can be instantiated."""
        validator = scangame_factory.get_ini_validator("Fallout4")
        assert validator is not None

    def test_ini_validator_detect_all_issues_with_empty_config(self):
        """Test detect_all_issues with empty configuration."""
        validator = scangame_factory.get_ini_validator("Fallout4")

        issues = validator.detect_all_issues({})

        assert isinstance(issues, list)


class TestRustCrashgenChecker:
    """Test Rust CrashgenChecker implementation."""

    def test_crashgen_checker_initialization(self, temp_dir):
        """Test that CrashgenChecker can be instantiated."""
        checker = scangame_factory.get_crashgen_checker(
            plugins_path=temp_dir,
            crashgen_name="Buffout4",
        )
        assert checker is not None

    def test_crashgen_checker_check_method(self, temp_dir):
        """Test check method returns tuple."""
        checker = scangame_factory.get_crashgen_checker(
            plugins_path=temp_dir,
            crashgen_name="Buffout4",
        )

        message, issues = checker.check()

        assert isinstance(message, str)
        assert isinstance(issues, list)


class TestRustXseChecker:
    """Test Rust XseChecker implementation."""

    def test_xse_checker_initialization(self, temp_dir):
        """Test that XseChecker can be instantiated."""
        checker = scangame_factory.get_xse_checker(plugins_path=temp_dir)
        assert checker is not None

    def test_xse_checker_check_method(self, temp_dir):
        """Test check method returns ValidationResult."""
        checker = scangame_factory.get_xse_checker(plugins_path=temp_dir)

        result = checker.check()

        # Should return a ValidationResult enum
        assert "ValidationResult" in str(result)

    def test_xse_checker_validate_method(self, temp_dir):
        """Test validate method returns formatted message."""
        checker = scangame_factory.get_xse_checker(plugins_path=temp_dir)

        message = checker.validate()

        assert isinstance(message, str)
        assert len(message) > 0

    def test_xse_checker_with_vr_mode(self, temp_dir):
        """Test XseChecker with VR mode enabled."""
        checker = scangame_factory.get_xse_checker(
            plugins_path=temp_dir,
            is_vr_mode=True,
        )

        result = checker.check()
        assert "ValidationResult" in str(result)

    def test_xse_checker_with_game_version(self, temp_dir):
        """Test XseChecker with explicit game version."""
        game_version = scangame_factory._classic_scangame.GameVersion.NextGen  # pyright: ignore[reportOptionalMemberAccess]

        checker = scangame_factory.get_xse_checker(
            plugins_path=temp_dir,
            is_vr_mode=False,
            game_version=game_version,
        )

        result = checker.check()
        assert "ValidationResult" in str(result)


class TestRustPerformance:
    """Test Rust performance characteristics (basic smoke tests)."""

    def test_batch_scanning_handles_large_lists(self, temp_dir):
        """Test that batch scanning can handle large file lists."""
        scanner = scangame_factory.get_ba2_scanner()

        # Generate list of 100 fake archive paths
        archives = []
        for i in range(100):
            p = temp_dir / f"archive{i}.ba2"
            p.touch()
            archives.append(p)

        # Should complete without hanging or crashing
        try:
            results = scanner.scan_archives_batch(archives)
            assert len(results) == 100
        except RuntimeError:
            pass

    def test_unpacked_scanner_handles_deep_trees(self, temp_dir):
        """Test that unpacked scanner handles deep directory trees."""
        scanner = scangame_factory.get_unpacked_scanner()

        # Create deep directory structure
        deep_dir = temp_dir
        for i in range(10):
            deep_dir = deep_dir / f"level{i}"
            deep_dir.mkdir()

        # Add a file at the bottom
        (deep_dir / "texture.png").write_bytes(b"fake png")

        # Should complete without stack overflow
        issues = scanner.scan_directory(temp_dir, [])

        assert issues.has_issues()
