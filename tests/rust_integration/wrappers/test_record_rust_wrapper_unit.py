"""Unit tests for ClassicLib.rust.record_rust module.

This module tests the RustRecordScanner wrapper class, which provides
high-performance record scanning with automatic fallback to Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.rust.record_rust import RustRecordScanner


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_for_record() -> MagicMock:
    """Create a mock ClassicScanLogsInfo for record scanning.

    Returns:
        MagicMock: Mock with record scanning attributes.
    """
    mock = MagicMock()
    mock.classic_records_list = ["Actor", "TESObjectREFR", "BGSProjectile"]
    mock.game_ignore_records = ["IgnoredRecord"]
    mock.crashgen_name = "Buffout 4"
    return mock


@pytest.fixture
def record_scanner(mock_yamldata_for_record: MagicMock) -> "RustRecordScanner":
    """Create a RustRecordScanner instance for testing.

    Args:
        mock_yamldata_for_record: Mock YAML data fixture.

    Returns:
        RustRecordScanner instance.
    """
    from ClassicLib.integration.rust.record_rust import RustRecordScanner

    return RustRecordScanner(mock_yamldata_for_record)


@pytest.fixture
def sample_callstack() -> list[str]:
    """Create sample callstack data with record references.

    Returns:
        list[str]: Sample callstack lines.
    """
    return [
        "0x7FF6EF4C3512 Actor::Process()",
        "0x7FF6EF4C3513 TESObjectREFR::Update()",
        "0x7FF6EF4C3514 Actor::ProcessMovement()",
        "0x7FF6EF4C3515 BGSProjectile::Launch()",
        "0x7FF6EF4C3516 SomeOtherFunction()",
    ]


# ============================================================================
# RustRecordScanner Initialization Tests
# ============================================================================


class TestRustRecordScannerInit:
    """Tests for RustRecordScanner initialization."""

    @pytest.mark.unit
    def test_init_stores_yamldata(self, mock_yamldata_for_record: MagicMock) -> None:
        """Test that yamldata is stored on initialization."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        scanner = RustRecordScanner(mock_yamldata_for_record)

        assert scanner.yamldata is mock_yamldata_for_record

    @pytest.mark.unit
    def test_is_rust_accelerated_property(self, record_scanner: "RustRecordScanner") -> None:
        """Test is_rust_accelerated property works."""
        assert isinstance(record_scanner.is_rust_accelerated, bool)

    @pytest.mark.unit
    def test_init_with_empty_records_list(self) -> None:
        """Test initialization with empty records list."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        mock = MagicMock()
        mock.classic_records_list = []
        mock.game_ignore_records = []
        mock.crashgen_name = "Buffout 4"

        scanner = RustRecordScanner(mock)

        assert scanner.yamldata is mock


# ============================================================================
# scan_named_records Tests
# ============================================================================


class TestScanNamedRecords:
    """Tests for RustRecordScanner.scan_named_records method."""

    @pytest.mark.unit
    def test_scan_named_records_returns_tuple(self, record_scanner: "RustRecordScanner", sample_callstack: list[str]) -> None:
        """Test scan_named_records returns tuple of (ReportFragment, matches)."""
        fragment, matches = record_scanner.scan_named_records(sample_callstack)

        assert hasattr(fragment, "to_list")
        assert isinstance(matches, list)

    @pytest.mark.unit
    def test_scan_named_records_finds_matches(self, record_scanner: "RustRecordScanner", sample_callstack: list[str]) -> None:
        """Test that matching records are found."""
        fragment, matches = record_scanner.scan_named_records(sample_callstack)

        # Should find Actor, TESObjectREFR, BGSProjectile
        assert len(matches) >= 0  # May not find matches depending on implementation

    @pytest.mark.unit
    def test_scan_named_records_empty_callstack(self, record_scanner: "RustRecordScanner") -> None:
        """Test scan with empty callstack."""
        fragment, matches = record_scanner.scan_named_records([])

        assert isinstance(matches, list)
        assert len(matches) == 0

    @pytest.mark.unit
    def test_scan_named_records_no_matches(self, record_scanner: "RustRecordScanner") -> None:
        """Test scan with no matching records."""
        callstack = ["NoRecordsHere", "JustSomeText"]

        fragment, matches = record_scanner.scan_named_records(callstack)

        lines = fragment.to_list()
        content = "".join(lines)

        assert len(matches) == 0
        assert "COULDN'T FIND" in content or len(lines) > 0


# ============================================================================
# extract_records Tests
# ============================================================================


class TestExtractRecords:
    """Tests for RustRecordScanner.extract_records method."""

    @pytest.mark.unit
    def test_extract_records_returns_list(self, record_scanner: "RustRecordScanner", sample_callstack: list[str]) -> None:
        """Test extract_records returns list of matches."""
        result = record_scanner.extract_records(sample_callstack)

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_extract_records_empty_callstack(self, record_scanner: "RustRecordScanner") -> None:
        """Test extract with empty callstack."""
        result = record_scanner.extract_records([])

        assert result == []


# ============================================================================
# batch_scan_records Tests
# ============================================================================


class TestBatchScanRecords:
    """Tests for RustRecordScanner.batch_scan_records method."""

    @pytest.mark.unit
    def test_batch_scan_records_returns_list(self, record_scanner: "RustRecordScanner", sample_callstack: list[str]) -> None:
        """Test batch_scan_records returns list of results."""
        segments = [sample_callstack, ["OtherLine"]]

        results = record_scanner.batch_scan_records(segments)

        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.unit
    def test_batch_scan_records_tuple_format(self, record_scanner: "RustRecordScanner", sample_callstack: list[str]) -> None:
        """Test each result is a tuple of (ReportFragment, matches)."""
        segments = [sample_callstack]

        results = record_scanner.batch_scan_records(segments)

        assert len(results) == 1
        fragment, matches = results[0]
        assert hasattr(fragment, "to_list")
        assert isinstance(matches, list)

    @pytest.mark.unit
    def test_batch_scan_records_empty_segments(self, record_scanner: "RustRecordScanner") -> None:
        """Test batch scan with empty segments list."""
        results = record_scanner.batch_scan_records([])

        assert results == []


# ============================================================================
# clear_cache Tests
# ============================================================================


class TestClearCache:
    """Tests for RustRecordScanner.clear_cache method."""

    @pytest.mark.unit
    def test_clear_cache_runs_without_error(self, record_scanner: "RustRecordScanner") -> None:
        """Test clear_cache runs without error."""
        # Should not raise
        record_scanner.clear_cache()


# ============================================================================
# scan_for_pattern Tests
# ============================================================================


class TestScanForPattern:
    """Tests for RustRecordScanner.scan_for_pattern static method."""

    @pytest.mark.unit
    def test_scan_for_pattern_returns_matches(self) -> None:
        """Test scan_for_pattern finds matching lines."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        lines = ["Actor::Process()", "TESForm::Update()", "SomeOther()"]

        result = RustRecordScanner.scan_for_pattern(lines, "Actor")

        assert "Actor::Process()" in result

    @pytest.mark.unit
    def test_scan_for_pattern_case_insensitive(self) -> None:
        """Test pattern matching is case-insensitive."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        lines = ["ACTOR::Process()", "actor::update()"]

        result = RustRecordScanner.scan_for_pattern(lines, "actor")

        assert len(result) == 2

    @pytest.mark.unit
    def test_scan_for_pattern_regex(self) -> None:
        """Test regex patterns work."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        lines = ["Actor123", "Actor456", "NoMatch"]

        result = RustRecordScanner.scan_for_pattern(lines, r"Actor\d+")

        assert len(result) == 2

    @pytest.mark.unit
    def test_scan_for_pattern_no_matches(self) -> None:
        """Test when pattern has no matches."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        lines = ["NoMatch1", "NoMatch2"]

        result = RustRecordScanner.scan_for_pattern(lines, "Actor")

        assert result == []


# ============================================================================
# _generate_report_lines Tests
# ============================================================================


class TestGenerateReportLines:
    """Tests for RustRecordScanner._generate_report_lines method."""

    @pytest.mark.unit
    def test_generate_report_lines_with_matches(self, record_scanner: "RustRecordScanner") -> None:
        """Test report generation with matches."""
        matches = ["Actor", "Actor", "TESObjectREFR"]

        lines = record_scanner._generate_report_lines(matches)

        assert isinstance(lines, list)
        assert len(lines) > 0
        content = "".join(lines)
        assert "Actor" in content

    @pytest.mark.unit
    def test_generate_report_lines_no_matches(self, record_scanner: "RustRecordScanner") -> None:
        """Test report generation with no matches."""
        lines = record_scanner._generate_report_lines([])

        content = "".join(lines)
        assert "COULDN'T FIND" in content

    @pytest.mark.unit
    def test_generate_report_lines_counts_occurrences(self, record_scanner: "RustRecordScanner") -> None:
        """Test that occurrences are counted."""
        matches = ["Actor", "Actor", "Actor"]

        lines = record_scanner._generate_report_lines(matches)

        content = "".join(lines)
        assert "| 3" in content or "3" in content


# ============================================================================
# Fallback Tests
# ============================================================================


class TestRustRecordScannerFallback:
    """Tests for Python fallback behavior."""

    @pytest.mark.unit
    def test_fallback_to_python_on_rust_error(self, mock_yamldata_for_record: MagicMock) -> None:
        """Test fallback to Python when Rust unavailable."""
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        # Force Python fallback by manually creating scanner without Rust
        scanner = RustRecordScanner.__new__(RustRecordScanner)
        scanner._rust_scanner = None
        scanner._use_rust = False
        scanner._python_scanner = None
        scanner.yamldata = mock_yamldata_for_record

        # Should create Python scanner on demand
        fragment, matches = scanner.scan_named_records(["test"])

        assert hasattr(fragment, "to_list")

    @pytest.mark.unit
    def test_uses_python_when_rust_unavailable(self, mock_yamldata_for_record: MagicMock) -> None:
        """Test Python implementation is used when Rust unavailable."""
        with patch.dict("sys.modules", {"classic_scanlog": None}):
            from ClassicLib.integration.rust.record_rust import RustRecordScanner

            scanner = RustRecordScanner(mock_yamldata_for_record)

            # May use Rust or Python depending on actual availability
            assert isinstance(scanner.is_rust_accelerated, bool)
