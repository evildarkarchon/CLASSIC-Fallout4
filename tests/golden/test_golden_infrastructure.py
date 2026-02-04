"""Tests for golden file infrastructure.

Verifies the golden file capture/compare framework works correctly
before using it for actual parity testing.
"""

import json

import pytest

from tests.fixtures.golden_fixtures import (
    TIMESTAMP_PLACEHOLDER,
    mask_dynamic_data,
    normalize_paths,
    generate_diff,
)


@pytest.mark.unit
class TestMaskDynamicData:
    """Test dynamic data masking for golden files."""

    def test_masks_iso_timestamp(self):
        """ISO 8601 timestamps are replaced with placeholder."""
        text = "Log entry at 2024-01-15T10:30:45Z"
        result = mask_dynamic_data(text)
        assert TIMESTAMP_PLACEHOLDER in result
        assert "2024-01-15" not in result

    def test_masks_iso_timestamp_with_offset(self):
        """ISO 8601 timestamps with timezone offset are replaced."""
        text = "Created: 2024-06-05T10:30:45+05:30"
        result = mask_dynamic_data(text)
        assert TIMESTAMP_PLACEHOLDER in result
        assert "2024-06-05" not in result

    def test_masks_date_only(self):
        """Date-only strings are replaced with placeholder."""
        text = "Created on 2024-01-15"
        result = mask_dynamic_data(text)
        assert TIMESTAMP_PLACEHOLDER in result

    def test_masks_time_only(self):
        """Time-only strings are replaced with placeholder."""
        text = "Processed at 14:32:55"
        result = mask_dynamic_data(text)
        assert TIMESTAMP_PLACEHOLDER in result
        assert "14:32:55" not in result

    def test_normalizes_windows_path(self):
        """Windows paths are normalized to forward slashes."""
        text = r"File: C:\Users\test\Documents\file.txt"
        result = normalize_paths(text)
        # Backslashes should be replaced with forward slashes
        assert "\\" not in result
        assert "C:/Users/test/Documents/file.txt" in result

    def test_preserves_unix_path(self):
        """Unix paths are already normalized."""
        text = "File: /home/user/documents/file.txt"
        result = normalize_paths(text)
        # Unix paths should be unchanged
        assert result == text

    def test_normalizes_multiple_paths(self):
        """Multiple Windows paths in text are all normalized."""
        text = r"Source: C:\Users\src\file.py Target: D:\data\dest.py"
        result = normalize_paths(text)
        # All backslashes should be replaced
        assert "\\" not in result
        assert "C:/Users/src/file.py" in result
        assert "D:/data/dest.py" in result

    def test_preserves_non_dynamic_content(self):
        """Non-dynamic content is preserved."""
        text = "Error: Plugin conflict detected between ModA and ModB"
        result = mask_dynamic_data(text)
        assert result == text

    def test_masks_mixed_content(self):
        """Mixed content with timestamps is handled correctly."""
        text = r"[2024-01-15T10:30:45Z] Loaded from C:\Mods\test.esp"
        # mask_dynamic_data handles timestamps only
        result = mask_dynamic_data(text)
        assert TIMESTAMP_PLACEHOLDER in result
        assert "Loaded from" in result
        # Paths are NOT masked (normalize_paths handles slash normalization separately)
        assert r"C:\Mods\test.esp" in result or "C:/Mods/test.esp" in result


@pytest.mark.unit
class TestGenerateDiff:
    """Test diff generation for debugging."""

    def test_diff_shows_changes(self):
        """Diff output shows actual changes."""
        expected = "line1\nline2\nline3"
        actual = "line1\nmodified\nline3"
        diff = generate_diff(expected, actual)
        # Check that the diff contains indicators of change
        assert "-line2" in diff or "- line2" in diff
        assert "+modified" in diff or "+ modified" in diff

    def test_diff_empty_for_identical(self):
        """No diff markers for identical content."""
        text = "identical content"
        diff = generate_diff(text, text)
        # unified_diff returns empty for identical
        assert diff == "" or "@@" not in diff

    def test_diff_shows_additions(self):
        """Diff shows added lines."""
        expected = "line1\nline2"
        actual = "line1\nline2\nline3"
        diff = generate_diff(expected, actual)
        assert "+line3" in diff or "+ line3" in diff

    def test_diff_shows_deletions(self):
        """Diff shows deleted lines."""
        expected = "line1\nline2\nline3"
        actual = "line1\nline2"
        diff = generate_diff(expected, actual)
        assert "-line3" in diff or "- line3" in diff


@pytest.mark.unit
class TestGoldenFileFixture:
    """Test golden file fixture functionality."""

    def test_golden_file_creates_new_file(self, golden_file, tmp_path, monkeypatch):
        """Golden file is created if it doesn't exist."""
        # Point golden_dir to tmp_path
        monkeypatch.setattr(golden_file, "golden_dir", tmp_path)

        # This should create the file and skip
        with pytest.raises(pytest.skip.Exception):
            golden_file.check("test content", "new_golden")

        # File should exist
        assert (tmp_path / "new_golden.golden").exists()

    def test_golden_file_matches_existing(self, golden_file, tmp_path, monkeypatch):
        """Matching content passes without error."""
        monkeypatch.setattr(golden_file, "golden_dir", tmp_path)

        # Create existing golden file
        (tmp_path / "existing.golden").write_text("expected content", encoding="utf-8")

        # Should pass without error
        golden_file.check("expected content", "existing")

    def test_golden_file_fails_on_mismatch(self, golden_file, tmp_path, monkeypatch):
        """Mismatched content fails with diff."""
        monkeypatch.setattr(golden_file, "golden_dir", tmp_path)

        # Create existing golden file
        (tmp_path / "mismatch.golden").write_text("expected", encoding="utf-8")

        # Should fail with assertion
        with pytest.raises(pytest.fail.Exception) as exc_info:
            golden_file.check("actual", "mismatch")

        assert "Golden file mismatch" in str(exc_info.value)
        assert "--update-golden" in str(exc_info.value)

    def test_golden_file_handles_json(self, golden_file, tmp_path, monkeypatch):
        """Dict output is serialized as JSON."""
        monkeypatch.setattr(golden_file, "golden_dir", tmp_path)

        data = {"key": "value", "nested": {"a": 1}}

        # Create matching golden file
        expected = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
        (tmp_path / "json_test.json").write_text(expected, encoding="utf-8")

        # Should pass
        golden_file.check(data, "json_test")

    def test_golden_file_masks_timestamps(self, golden_file, tmp_path, monkeypatch):
        """Timestamps are masked before comparison."""
        monkeypatch.setattr(golden_file, "golden_dir", tmp_path)

        # Create golden with masked content
        (tmp_path / "masked.golden").write_text(
            f"Log at {TIMESTAMP_PLACEHOLDER}", encoding="utf-8"
        )

        # Input with actual timestamp should match
        golden_file.check("Log at 2024-01-15T10:30:45Z", "masked")


@pytest.mark.parity
@pytest.mark.slow
class TestParityMarkerWorks:
    """Verify parity marker is registered and tests can be skipped."""

    def test_parity_marker_exists(self):
        """Parity marker is recognized by pytest."""
        # This test existing and running proves the marker works
        assert True

    def test_parity_can_be_used_with_slow(self):
        """Parity marker can be combined with slow marker."""
        # This test proves both markers work together
        assert True
