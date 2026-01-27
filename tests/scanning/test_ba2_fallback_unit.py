"""Unit tests for ClassicLib.scanning.game.checks.ba2_fallback module.

This module tests the BA2Issues container and BA2Scanner fallback implementation
for scanning BA2 archives.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestBA2Issues:
    """Tests for BA2Issues container class."""

    def test_default_initialization(self) -> None:
        """Test BA2Issues initializes with empty lists by default."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues

        issues = BA2Issues()

        assert issues.tex_dims == []
        assert issues.tex_frmt == []
        assert issues.snd_frmt == []
        assert issues.xse_file == []

    def test_initialization_with_values(self) -> None:
        """Test BA2Issues initializes with provided values."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues

        tex_dims = ["odd_texture1.dds", "odd_texture2.dds"]
        tex_frmt = ["wrong_format.png"]
        snd_frmt = ["sound.mp3"]
        xse_file = ["script.dll"]

        issues = BA2Issues(
            tex_dims=tex_dims,
            tex_frmt=tex_frmt,
            snd_frmt=snd_frmt,
            xse_file=xse_file,
        )

        assert issues.tex_dims == tex_dims
        assert issues.tex_frmt == tex_frmt
        assert issues.snd_frmt == snd_frmt
        assert issues.xse_file == xse_file

    def test_partial_initialization(self) -> None:
        """Test BA2Issues with partial initialization."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues

        issues = BA2Issues(tex_dims=["texture.dds"])

        assert issues.tex_dims == ["texture.dds"]
        assert issues.tex_frmt == []
        assert issues.snd_frmt == []
        assert issues.xse_file == []

    def test_none_values_become_empty_lists(self) -> None:
        """Test that None values are converted to empty lists."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues

        issues = BA2Issues(tex_dims=None, tex_frmt=None, snd_frmt=None, xse_file=None)

        assert issues.tex_dims == []
        assert issues.tex_frmt == []
        assert issues.snd_frmt == []
        assert issues.xse_file == []

    def test_lists_are_independent(self) -> None:
        """Test that issue lists are independent instances."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues

        issues1 = BA2Issues()
        issues2 = BA2Issues()

        issues1.tex_dims.append("test.dds")

        assert issues1.tex_dims == ["test.dds"]
        assert issues2.tex_dims == []


class TestBA2Scanner:
    """Tests for BA2Scanner class."""

    def test_initialization(self) -> None:
        """Test BA2Scanner initializes successfully."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        scanner = BA2Scanner()

        assert scanner is not None

    def test_scan_archive_nonexistent_file(self, tmp_path: Path) -> None:
        """Test scanning a nonexistent file returns empty issues."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        result = BA2Scanner.scan_archive(tmp_path / "nonexistent.ba2")

        assert result.tex_dims == []
        assert result.tex_frmt == []
        assert result.snd_frmt == []
        assert result.xse_file == []

    def test_scan_archive_non_ba2_extension(self, tmp_path: Path) -> None:
        """Test scanning a file with wrong extension returns empty issues."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        # Create a file with wrong extension
        wrong_file = tmp_path / "test.zip"
        wrong_file.write_text("test content")

        result = BA2Scanner.scan_archive(wrong_file)

        assert result.tex_dims == []
        assert result.tex_frmt == []
        assert result.snd_frmt == []
        assert result.xse_file == []

    def test_scan_archive_valid_ba2_file(self, tmp_path: Path) -> None:
        """Test scanning a valid .ba2 file returns BA2Issues object."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues, BA2Scanner

        # Create a mock .ba2 file
        ba2_file = tmp_path / "test.ba2"
        ba2_file.write_bytes(b"BA2\x00test data")

        result = BA2Scanner.scan_archive(ba2_file)

        assert isinstance(result, BA2Issues)

    def test_scan_archive_case_insensitive_extension(self, tmp_path: Path) -> None:
        """Test scanning works with different case extensions."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues, BA2Scanner

        # Create .BA2 with uppercase extension
        ba2_file = tmp_path / "test.BA2"
        ba2_file.write_bytes(b"BA2\x00test data")

        result = BA2Scanner.scan_archive(ba2_file)

        assert isinstance(result, BA2Issues)


class TestBA2ScannerBatch:
    """Tests for BA2Scanner.scan_archives_batch method."""

    def test_scan_empty_batch(self) -> None:
        """Test scanning an empty batch returns empty results."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        results = BA2Scanner.scan_archives_batch([])

        assert results == []

    def test_scan_single_archive_batch(self, tmp_path: Path) -> None:
        """Test scanning a batch with single archive."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues, BA2Scanner

        ba2_file = tmp_path / "test.ba2"
        ba2_file.write_bytes(b"BA2\x00test")

        results = BA2Scanner.scan_archives_batch([ba2_file])

        assert len(results) == 1
        assert results[0][0] == ba2_file
        assert isinstance(results[0][1], BA2Issues)

    def test_scan_multiple_archives_batch(self, tmp_path: Path) -> None:
        """Test scanning a batch with multiple archives."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues, BA2Scanner

        ba2_files = []
        for i in range(3):
            ba2_file = tmp_path / f"test{i}.ba2"
            ba2_file.write_bytes(b"BA2\x00test")
            ba2_files.append(ba2_file)

        results = BA2Scanner.scan_archives_batch(ba2_files)

        assert len(results) == 3
        for i, (path, issues) in enumerate(results):
            assert path == ba2_files[i]
            assert isinstance(issues, BA2Issues)

    def test_scan_mixed_batch(self, tmp_path: Path) -> None:
        """Test scanning a batch with mix of valid and invalid archives."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        # Create valid .ba2
        valid_ba2 = tmp_path / "valid.ba2"
        valid_ba2.write_bytes(b"BA2\x00test")

        # Create invalid file (wrong extension)
        invalid_file = tmp_path / "invalid.zip"
        invalid_file.write_bytes(b"ZIP data")

        # Nonexistent file
        nonexistent = tmp_path / "nonexistent.ba2"

        results = BA2Scanner.scan_archives_batch([valid_ba2, invalid_file, nonexistent])

        assert len(results) == 3
        # All should return BA2Issues, even for invalid files

    def test_batch_preserves_order(self, tmp_path: Path) -> None:
        """Test that batch scanning preserves input order."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        paths = []
        for name in ["first.ba2", "second.ba2", "third.ba2"]:
            path = tmp_path / name
            path.write_bytes(b"BA2\x00test")
            paths.append(path)

        results = BA2Scanner.scan_archives_batch(paths)

        for i, (result_path, _) in enumerate(results):
            assert result_path == paths[i]


class TestBA2ScannerStaticMethods:
    """Tests for BA2Scanner static method behavior."""

    def test_scan_archive_is_static(self) -> None:
        """Test that scan_archive can be called without instance."""
        from pathlib import Path

        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Issues, BA2Scanner

        # Call directly on class without instance
        result = BA2Scanner.scan_archive(Path("nonexistent.ba2"))

        assert isinstance(result, BA2Issues)

    def test_scan_archives_batch_is_static(self) -> None:
        """Test that scan_archives_batch can be called without instance."""
        from ClassicLib.scanning.game.checks.ba2_fallback import BA2Scanner

        # Call directly on class without instance
        result = BA2Scanner.scan_archives_batch([])

        assert result == []
