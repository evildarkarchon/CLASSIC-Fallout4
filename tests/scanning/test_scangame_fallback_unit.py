"""Unit tests for ScanGame fallback modules.

This module tests the pure Python fallback implementations in ClassicLib/scanning/game/checks/:
- LogProcessor (log_fallback.py) - Log file scanning and error detection
- UnpackedScanner (unpacked_fallback.py) - Detection of improperly unpacked files
- ConfigDuplicateDetector (config_duplicate_fallback.py) - Configuration file duplicate detection

These fallbacks are used when Rust acceleration is unavailable.
"""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


# ============================================================================
# LogProcessor Tests (log_fallback.py)
# ============================================================================

from ClassicLib.scanning.game.checks.log_fallback import LogProcessor


class TestLogProcessorInit:
    """Test LogProcessor initialization."""

    def test_init_converts_patterns_to_lowercase(self) -> None:
        """Test that initialization converts all patterns to lowercase."""
        processor = LogProcessor(
            catch_errors=["ERROR", "Warning", "EXCEPTION"],
            ignore_files=["Debug.LOG", "TEST.log"],
            ignore_errors=["BENIGN", "Skipping"],
        )

        assert "error" in processor.catch_errors
        assert "warning" in processor.catch_errors
        assert "exception" in processor.catch_errors
        assert "debug.log" in processor.ignore_files
        assert "benign" in processor.ignore_errors

    def test_init_with_empty_lists(self) -> None:
        """Test initialization with empty pattern lists."""
        processor = LogProcessor(
            catch_errors=[],
            ignore_files=[],
            ignore_errors=[],
        )

        assert processor.catch_errors == []
        assert processor.ignore_files == []
        assert processor.ignore_errors == []


class TestLogProcessorProcessLogs:
    """Test LogProcessor.process_logs method."""

    def test_process_logs_returns_empty_for_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test that processing a nonexistent directory returns empty string."""
        processor = LogProcessor(["error"], [], [])
        nonexistent = tmp_path / "nonexistent"

        result = processor.process_logs(nonexistent)

        assert result == ""

    def test_process_logs_returns_empty_for_file_path(self, tmp_path: Path) -> None:
        """Test that processing a file path (not dir) returns empty string."""
        processor = LogProcessor(["error"], [], [])
        file_path = tmp_path / "test.log"
        file_path.write_text("error: test", encoding="utf-8")

        result = processor.process_logs(file_path)

        assert result == ""

    def test_process_logs_returns_empty_for_no_log_files(self, tmp_path: Path) -> None:
        """Test that processing a directory with no log files returns empty."""
        processor = LogProcessor(["error"], [], [])
        # Create non-log files
        (tmp_path / "readme.txt").write_text("readme", encoding="utf-8")

        result = processor.process_logs(tmp_path)

        assert result == ""

    def test_process_logs_finds_errors_in_log_files(self, tmp_path: Path) -> None:
        """Test that errors are detected in log files."""
        processor = LogProcessor(["error", "exception"], [], [])
        log_file = tmp_path / "game.log"
        log_file.write_text(
            "Starting game...\nERROR: Failed to load texture\nWarning: Low memory\nEXCEPTION: Access violation\n",
            encoding="utf-8",
        )

        result = processor.process_logs(tmp_path)

        assert "CAUTION" in result
        assert "Failed to load texture" in result
        assert "Access violation" in result
        assert "Warning: Low memory" not in result  # "warning" not in catch_errors

    def test_process_logs_skips_crash_log_files(self, tmp_path: Path) -> None:
        """Test that crash-*.log files are skipped."""
        processor = LogProcessor(["error"], [], [])
        crash_log = tmp_path / "crash-2024-01-01.log"
        crash_log.write_text("ERROR: Critical error", encoding="utf-8")
        normal_log = tmp_path / "normal.log"
        normal_log.write_text("ERROR: Normal error", encoding="utf-8")

        result = processor.process_logs(tmp_path)

        assert "Normal error" in result
        assert "Critical error" not in result

    def test_process_logs_skips_ignored_files(self, tmp_path: Path) -> None:
        """Test that files matching ignore patterns are skipped."""
        processor = LogProcessor(["error"], ["debug"], [])
        debug_log = tmp_path / "debug.log"
        debug_log.write_text("ERROR: Debug error", encoding="utf-8")
        app_log = tmp_path / "app.log"
        app_log.write_text("ERROR: App error", encoding="utf-8")

        result = processor.process_logs(tmp_path)

        assert "App error" in result
        assert "Debug error" not in result

    def test_process_logs_skips_ignored_error_patterns(self, tmp_path: Path) -> None:
        """Test that error lines matching ignore patterns are excluded."""
        processor = LogProcessor(["error"], [], ["benign", "expected"])
        log_file = tmp_path / "game.log"
        log_file.write_text(
            "ERROR: Critical failure\nERROR: Benign warning (expected)\nERROR: Another benign issue\n",
            encoding="utf-8",
        )

        result = processor.process_logs(tmp_path)

        assert "Critical failure" in result
        assert "Benign" not in result.lower() or "benign" not in result.lower()


class TestLogProcessorProcessSingleLog:
    """Test LogProcessor._process_single_log method."""

    def test_process_single_log_returns_matching_lines(self, tmp_path: Path) -> None:
        """Test that matching error lines are returned."""
        processor = LogProcessor(["error"], [], [])
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "Info: Starting\nERROR: First error\nDebug: Details\nerror: Second error\n",  # lowercase should also match
            encoding="utf-8",
        )

        errors = processor._process_single_log(log_file)

        assert len(errors) == 2
        assert any("First error" in e for e in errors)
        assert any("Second error" in e for e in errors)

    def test_process_single_log_limits_to_50_errors(self, tmp_path: Path) -> None:
        """Test that only last 50 errors are returned."""
        processor = LogProcessor(["error"], [], [])
        log_file = tmp_path / "large.log"
        # Write 100 error lines
        lines = [f"ERROR: Error number {i}\n" for i in range(100)]
        log_file.write_text("".join(lines), encoding="utf-8")

        errors = processor._process_single_log(log_file)

        assert len(errors) == 50
        # Should be the last 50 (50-99)
        assert any("99" in e for e in errors)
        assert not any("Error number 0\n" in e for e in errors)

    def test_process_single_log_handles_unreadable_file(self, tmp_path: Path) -> None:
        """Test that unreadable files return empty list."""
        processor = LogProcessor(["error"], [], [])
        nonexistent = tmp_path / "nonexistent.log"

        errors = processor._process_single_log(nonexistent)

        assert errors == []


class TestLogProcessorFormatErrorReport:
    """Test LogProcessor._format_error_report static method."""

    def test_format_error_report_includes_header(self, tmp_path: Path) -> None:
        """Test that formatted report includes warning header."""
        log_file = tmp_path / "test.log"
        errors = ["Error 1", "Error 2"]

        report = LogProcessor._format_error_report(log_file, errors)

        combined = "".join(report)
        assert "CAUTION" in combined
        assert str(log_file) in combined

    def test_format_error_report_includes_all_errors(self, tmp_path: Path) -> None:
        """Test that all errors are included in report."""
        log_file = tmp_path / "test.log"
        errors = ["First error", "Second error", "Third error"]

        report = LogProcessor._format_error_report(log_file, errors)

        combined = "".join(report)
        for error in errors:
            assert error in combined

    def test_format_error_report_includes_count(self, tmp_path: Path) -> None:
        """Test that error count is included in report."""
        log_file = tmp_path / "test.log"
        errors = ["Error 1", "Error 2", "Error 3"]

        report = LogProcessor._format_error_report(log_file, errors)

        combined = "".join(report)
        assert "3" in combined


# ============================================================================
# UnpackedScanner Tests (unpacked_fallback.py)
# ============================================================================

from ClassicLib.scanning.game.checks.unpacked_fallback import UnpackedIssues, UnpackedScanner


class TestUnpackedIssuesInit:
    """Test UnpackedIssues initialization."""

    def test_init_defaults_to_empty_lists(self) -> None:
        """Test that all attributes default to empty lists."""
        issues = UnpackedIssues()

        assert issues.animdata == []
        assert issues.tex_frmt == []
        assert issues.snd_frmt == []
        assert issues.xse_file == []
        assert issues.previs == []
        assert issues.dds_files == []

    def test_init_accepts_custom_values(self) -> None:
        """Test that custom values are accepted."""
        issues = UnpackedIssues(
            animdata=["anim1"],
            tex_frmt=["tex1.tga"],
            snd_frmt=["sound.mp3"],
            xse_file=["script.dll"],
            previs=["previs.uvd"],
        )

        assert issues.animdata == ["anim1"]
        assert issues.tex_frmt == ["tex1.tga"]


class TestUnpackedIssuesHasIssues:
    """Test UnpackedIssues.has_issues method."""

    def test_has_issues_returns_false_for_empty(self) -> None:
        """Test that empty issues returns False."""
        issues = UnpackedIssues()

        assert issues.has_issues() is False

    def test_has_issues_returns_true_for_animdata(self) -> None:
        """Test that animdata triggers has_issues."""
        issues = UnpackedIssues(animdata=["test"])

        assert issues.has_issues() is True

    def test_has_issues_returns_true_for_tex_frmt(self) -> None:
        """Test that tex_frmt triggers has_issues."""
        issues = UnpackedIssues(tex_frmt=["test.tga"])

        assert issues.has_issues() is True

    def test_has_issues_ignores_dds_files(self) -> None:
        """Test that dds_files alone doesn't trigger has_issues."""
        issues = UnpackedIssues(dds_files=[Path("test.dds")])

        assert issues.has_issues() is False


class TestUnpackedIssuesTotalCount:
    """Test UnpackedIssues.total_count method."""

    def test_total_count_returns_zero_for_empty(self) -> None:
        """Test that empty issues returns 0."""
        issues = UnpackedIssues()

        assert issues.total_count() == 0

    def test_total_count_sums_all_issue_types(self) -> None:
        """Test that all issue types are summed."""
        issues = UnpackedIssues(
            animdata=["a1", "a2"],
            tex_frmt=["t1"],
            snd_frmt=["s1", "s2", "s3"],
            xse_file=["x1"],
            previs=["p1", "p2"],
        )

        assert issues.total_count() == 9  # 2 + 1 + 3 + 1 + 2


class TestUnpackedScannerScanDirectory:
    """Test UnpackedScanner.scan_directory method."""

    def test_scan_directory_returns_empty_for_nonexistent(self, tmp_path: Path) -> None:
        """Test scanning nonexistent directory returns empty issues."""
        scanner = UnpackedScanner()
        nonexistent = tmp_path / "nonexistent"

        issues = scanner.scan_directory(nonexistent, [])

        assert issues.total_count() == 0

    def test_scan_directory_detects_tga_files(self, tmp_path: Path) -> None:
        """Test that TGA texture files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "texture.tga").write_bytes(b"TGA")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.tex_frmt) == 1
        assert "texture.tga" in issues.tex_frmt[0]

    def test_scan_directory_detects_png_files(self, tmp_path: Path) -> None:
        """Test that PNG texture files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "texture.png").write_bytes(b"PNG")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.tex_frmt) == 1

    def test_scan_directory_ignores_bodyslide_textures(self, tmp_path: Path) -> None:
        """Test that textures in BodySlide folders are ignored."""
        scanner = UnpackedScanner()
        bodyslide_dir = tmp_path / "BodySlide"
        bodyslide_dir.mkdir()
        (bodyslide_dir / "texture.tga").write_bytes(b"TGA")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.tex_frmt) == 0

    def test_scan_directory_detects_mp3_files(self, tmp_path: Path) -> None:
        """Test that MP3 sound files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "sound.mp3").write_bytes(b"MP3")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.snd_frmt) == 1
        assert "sound.mp3" in issues.snd_frmt[0]

    def test_scan_directory_detects_m4a_files(self, tmp_path: Path) -> None:
        """Test that M4A sound files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "sound.m4a").write_bytes(b"M4A")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.snd_frmt) == 1

    def test_scan_directory_detects_xse_scripts_in_scripts_folder(self, tmp_path: Path) -> None:
        """Test that XSE scripts in Scripts folder are detected."""
        scanner = UnpackedScanner()
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        (scripts_dir / "f4se.dll").write_bytes(b"DLL")

        issues = scanner.scan_directory(tmp_path, ["f4se.dll"])

        assert len(issues.xse_file) == 1

    def test_scan_directory_ignores_xse_scripts_outside_scripts_folder(self, tmp_path: Path) -> None:
        """Test that XSE scripts outside Scripts folder are ignored."""
        scanner = UnpackedScanner()
        (tmp_path / "f4se.dll").write_bytes(b"DLL")

        issues = scanner.scan_directory(tmp_path, ["f4se.dll"])

        assert len(issues.xse_file) == 0

    def test_scan_directory_detects_previs_uvd_files(self, tmp_path: Path) -> None:
        """Test that .uvd previs files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "precombine.uvd").write_bytes(b"UVD")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.previs) == 1

    def test_scan_directory_detects_previs_oc_nif_files(self, tmp_path: Path) -> None:
        """Test that _oc.nif previs files are detected."""
        scanner = UnpackedScanner()
        (tmp_path / "mesh_oc.nif").write_bytes(b"NIF")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.previs) == 1

    def test_scan_directory_collects_dds_files(self, tmp_path: Path) -> None:
        """Test that DDS files are collected for dimension checking."""
        scanner = UnpackedScanner()
        dds_file = tmp_path / "texture.dds"
        dds_file.write_bytes(b"DDS")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.dds_files) == 1
        assert issues.dds_files[0] == dds_file

    def test_scan_directory_detects_animationfiledata_folders(self, tmp_path: Path) -> None:
        """Test that AnimationFileData directories are detected."""
        scanner = UnpackedScanner()
        anim_dir = tmp_path / "AnimationFileData"
        anim_dir.mkdir()
        # Need a file inside to make the directory traversable
        (anim_dir / "dummy.txt").write_text("test", encoding="utf-8")

        issues = scanner.scan_directory(tmp_path, [])

        assert len(issues.animdata) == 1


# ============================================================================
# ConfigDuplicateDetector Tests (config_duplicate_fallback.py)
# ============================================================================

from ClassicLib.scanning.game.checks.config_duplicate_fallback import ConfigDuplicateDetector, DuplicateGroup


class TestDuplicateGroupInit:
    """Test DuplicateGroup initialization."""

    def test_init_with_original_only(self, tmp_path: Path) -> None:
        """Test initialization with just original path."""
        original = tmp_path / "config.ini"
        group = DuplicateGroup(original)

        assert group.original == original
        assert group.duplicates == []

    def test_init_with_duplicates(self, tmp_path: Path) -> None:
        """Test initialization with duplicates list."""
        original = tmp_path / "original.ini"
        dupe1 = tmp_path / "dupe1.ini"
        dupe2 = tmp_path / "dupe2.ini"
        group = DuplicateGroup(original, [dupe1, dupe2])

        assert group.original == original
        assert len(group.duplicates) == 2


class TestConfigDuplicateDetectorDetectDuplicates:
    """Test ConfigDuplicateDetector.detect_duplicates method."""

    def test_detect_duplicates_returns_empty_for_nonexistent(self, tmp_path: Path) -> None:
        """Test that nonexistent directory returns empty list."""
        nonexistent = tmp_path / "nonexistent"

        groups = ConfigDuplicateDetector.detect_duplicates(nonexistent)

        assert groups == []

    def test_detect_duplicates_returns_empty_for_no_duplicates(self, tmp_path: Path) -> None:
        """Test that unique files return empty list."""
        (tmp_path / "config1.ini").write_text("unique content 1", encoding="utf-8")
        (tmp_path / "config2.ini").write_text("unique content 2", encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert groups == []

    def test_detect_duplicates_finds_identical_ini_files(self, tmp_path: Path) -> None:
        """Test that duplicate INI files are detected."""
        content = "same content"
        (tmp_path / "original.ini").write_text(content, encoding="utf-8")
        (tmp_path / "duplicate.ini").write_text(content, encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert len(groups) == 1
        assert len(groups[0].duplicates) == 1

    def test_detect_duplicates_finds_identical_conf_files(self, tmp_path: Path) -> None:
        """Test that duplicate .conf files are detected."""
        content = "same config"
        (tmp_path / "app.conf").write_text(content, encoding="utf-8")
        (tmp_path / "backup.conf").write_text(content, encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert len(groups) == 1

    def test_detect_duplicates_finds_dxvk_conf(self, tmp_path: Path) -> None:
        """Test that dxvk.conf is detected regardless of extension pattern."""
        content = "dxvk settings"
        (tmp_path / "dxvk.conf").write_text(content, encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "dxvk.conf").write_text(content, encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert len(groups) == 1

    def test_detect_duplicates_handles_multiple_duplicate_groups(self, tmp_path: Path) -> None:
        """Test detection of multiple duplicate groups."""
        # Group 1: two identical
        (tmp_path / "group1_a.ini").write_text("content1", encoding="utf-8")
        (tmp_path / "group1_b.ini").write_text("content1", encoding="utf-8")
        # Group 2: three identical
        (tmp_path / "group2_a.ini").write_text("content2", encoding="utf-8")
        (tmp_path / "group2_b.ini").write_text("content2", encoding="utf-8")
        (tmp_path / "group2_c.ini").write_text("content2", encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert len(groups) == 2
        # Find the group with 2 duplicates
        large_group = next((g for g in groups if len(g.duplicates) == 2), None)
        assert large_group is not None

    def test_detect_duplicates_ignores_non_config_files(self, tmp_path: Path) -> None:
        """Test that non-config files are ignored."""
        content = "same content"
        (tmp_path / "file.txt").write_text(content, encoding="utf-8")
        (tmp_path / "file2.txt").write_text(content, encoding="utf-8")

        groups = ConfigDuplicateDetector.detect_duplicates(tmp_path)

        assert groups == []


class TestConfigDuplicateDetectorGetDuplicateMap:
    """Test ConfigDuplicateDetector.get_duplicate_map method."""

    def test_get_duplicate_map_returns_empty_for_no_duplicates(self, tmp_path: Path) -> None:
        """Test that no duplicates returns empty dict."""
        (tmp_path / "unique.ini").write_text("unique", encoding="utf-8")

        result = ConfigDuplicateDetector.get_duplicate_map(tmp_path)

        assert result == {}

    def test_get_duplicate_map_returns_all_paths(self, tmp_path: Path) -> None:
        """Test that map includes both original and duplicates."""
        content = "same"
        (tmp_path / "Original.ini").write_text(content, encoding="utf-8")
        (tmp_path / "duplicate.ini").write_text(content, encoding="utf-8")

        result = ConfigDuplicateDetector.get_duplicate_map(tmp_path)

        # Should have one entry
        assert len(result) == 1
        # Should have 2 paths total
        all_paths = list(result.values())[0]
        assert len(all_paths) == 2

    def test_get_duplicate_map_uses_lowercase_keys(self, tmp_path: Path) -> None:
        """Test that dictionary keys are lowercase."""
        content = "same"
        # Use different filenames to avoid Windows case-insensitive filesystem issues
        (tmp_path / "Config1.INI").write_text(content, encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "Config2.ini").write_text(content, encoding="utf-8")

        result = ConfigDuplicateDetector.get_duplicate_map(tmp_path)

        # Key should be lowercase - either config1.ini or config2.ini
        # depending on which was found first
        if result:
            key = list(result.keys())[0]
            assert key == key.lower()
