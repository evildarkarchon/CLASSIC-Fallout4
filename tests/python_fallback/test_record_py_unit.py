"""Unit tests for ClassicLib.python.record_py module.

This module tests the PythonRecordScanner class, which provides the pure Python
fallback implementation for named record scanning when Rust acceleration is
not available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from ClassicLib.python.record_py import PythonRecordScanner

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata_records() -> MagicMock:
    """Create mock yamldata for record scanner tests.

    Returns:
        MagicMock with required attributes for record scanning.
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    mock.classic_records_list = ["TESForm", "BGSKeyword", "ActorValue", "NPC_"]
    mock.game_ignore_records = ["TESFileRecord", "Unknown"]
    return mock


@pytest.fixture
def mock_yamldata_empty_records() -> MagicMock:
    """Create mock yamldata with empty record lists.

    Returns:
        MagicMock with empty record lists.
    """
    mock = MagicMock()
    mock.crashgen_name = "Buffout 4"
    mock.classic_records_list = []
    mock.game_ignore_records = []
    return mock


@pytest.fixture
def record_scanner(mock_yamldata_records: MagicMock) -> "PythonRecordScanner":
    """Create a record scanner instance for testing.

    Args:
        mock_yamldata_records: Mock yamldata fixture.

    Returns:
        PythonRecordScanner instance configured for testing.
    """
    from ClassicLib.python.record_py import PythonRecordScanner

    return PythonRecordScanner(mock_yamldata_records)


@pytest.fixture
def record_scanner_empty(mock_yamldata_empty_records: MagicMock) -> "PythonRecordScanner":
    """Create a record scanner with empty configuration.

    Args:
        mock_yamldata_empty_records: Mock yamldata fixture with empty lists.

    Returns:
        PythonRecordScanner instance with empty configuration.
    """
    from ClassicLib.python.record_py import PythonRecordScanner

    return PythonRecordScanner(mock_yamldata_empty_records)


@pytest.fixture
def sample_callstack() -> list[str]:
    """Create sample callstack lines for testing.

    Returns:
        List of sample callstack lines.
    """
    return [
        "0x0000000140001234 [RSP+10] SomeModule.dll+12345 [TESForm]",
        "0x0000000140005678 [RSP+20] AnotherModule.dll+67890 [BGSKeyword]",
        "0x0000000140009ABC OtherFunction [ActorValue]",
        "0x000000014000DEF0 IgnoredLine [TESFileRecord]",
        "Random line without records",
    ]


# ============================================================================
# PythonRecordScanner Initialization Tests
# ============================================================================


class TestPythonRecordScannerInit:
    """Tests for PythonRecordScanner initialization."""

    @pytest.mark.unit
    def test_init_stores_yamldata(self, mock_yamldata_records: MagicMock) -> None:
        """Test scanner stores yamldata reference."""
        from ClassicLib.python.record_py import PythonRecordScanner

        scanner = PythonRecordScanner(mock_yamldata_records)

        assert scanner.yamldata == mock_yamldata_records

    @pytest.mark.unit
    def test_init_creates_lowercase_records_set(self, mock_yamldata_records: MagicMock) -> None:
        """Test scanner creates lowercase set of records."""
        from ClassicLib.python.record_py import PythonRecordScanner

        scanner = PythonRecordScanner(mock_yamldata_records)

        assert "tesform" in scanner.lower_records
        assert "bgskeyword" in scanner.lower_records
        assert "actorvalue" in scanner.lower_records
        assert "npc_" in scanner.lower_records

    @pytest.mark.unit
    def test_init_creates_lowercase_ignore_set(self, mock_yamldata_records: MagicMock) -> None:
        """Test scanner creates lowercase set of ignored records."""
        from ClassicLib.python.record_py import PythonRecordScanner

        scanner = PythonRecordScanner(mock_yamldata_records)

        assert "tesfilerecord" in scanner.lower_ignore
        assert "unknown" in scanner.lower_ignore

    @pytest.mark.unit
    def test_init_handles_empty_lists(self, mock_yamldata_empty_records: MagicMock) -> None:
        """Test scanner handles empty record lists."""
        from ClassicLib.python.record_py import PythonRecordScanner

        scanner = PythonRecordScanner(mock_yamldata_empty_records)

        assert scanner.lower_records == set()
        assert scanner.lower_ignore == set()


# ============================================================================
# scan_named_records Tests
# ============================================================================


class TestScanNamedRecords:
    """Tests for PythonRecordScanner.scan_named_records method."""

    @pytest.mark.unit
    def test_scan_named_records_returns_tuple(self, record_scanner: "PythonRecordScanner", sample_callstack: list[str]) -> None:
        """Test scan_named_records returns tuple of fragment and matches."""
        fragment, matches = record_scanner.scan_named_records(sample_callstack)

        from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment

        assert isinstance(fragment, ReportFragment)
        assert isinstance(matches, list)

    @pytest.mark.unit
    def test_scan_named_records_finds_matching_records(self, record_scanner: "PythonRecordScanner", sample_callstack: list[str]) -> None:
        """Test scan_named_records finds matching records."""
        _, matches = record_scanner.scan_named_records(sample_callstack)

        # Should find TESForm, BGSKeyword, ActorValue but not TESFileRecord (ignored)
        assert len(matches) >= 2

    @pytest.mark.unit
    def test_scan_named_records_excludes_ignored(self, record_scanner: "PythonRecordScanner", sample_callstack: list[str]) -> None:
        """Test scan_named_records excludes ignored records."""
        _, matches = record_scanner.scan_named_records(sample_callstack)

        # TESFileRecord should be ignored
        for match in matches:
            assert "TESFileRecord" not in match

    @pytest.mark.unit
    def test_scan_named_records_empty_callstack(self, record_scanner: "PythonRecordScanner") -> None:
        """Test scan_named_records handles empty callstack."""
        fragment, matches = record_scanner.scan_named_records([])

        assert matches == []
        content = "".join(fragment.content)
        assert "COULDN'T FIND ANY NAMED RECORDS" in content

    @pytest.mark.unit
    def test_scan_named_records_no_matches(self, record_scanner: "PythonRecordScanner") -> None:
        """Test scan_named_records handles no matching records."""
        callstack = [
            "Random line 1",
            "Random line 2",
            "No named records here",
        ]

        fragment, matches = record_scanner.scan_named_records(callstack)

        assert matches == []
        content = "".join(fragment.content)
        assert "COULDN'T FIND ANY NAMED RECORDS" in content

    @pytest.mark.unit
    def test_scan_named_records_fragment_has_content(self, record_scanner: "PythonRecordScanner", sample_callstack: list[str]) -> None:
        """Test scan_named_records fragment has content when matches found."""
        fragment, matches = record_scanner.scan_named_records(sample_callstack)

        if matches:
            assert fragment.has_content is True


# ============================================================================
# _find_matching_records Tests
# ============================================================================


class TestFindMatchingRecords:
    """Tests for PythonRecordScanner._find_matching_records method."""

    @pytest.mark.unit
    def test_find_matching_records_appends_to_list(self, record_scanner: "PythonRecordScanner") -> None:
        """Test _find_matching_records appends found records to list."""
        callstack = ["0x1234 [RSP+10] Module.dll+1234 [TESForm]"]
        matches: list[str] = []

        record_scanner._find_matching_records(callstack, matches, "[RSP+", 30)

        assert len(matches) == 1

    @pytest.mark.unit
    def test_find_matching_records_extracts_after_rsp_marker(self, record_scanner: "PythonRecordScanner") -> None:
        """Test _find_matching_records extracts content after RSP marker."""
        callstack = ["0x00000000DEADBEEF [RSP+10] SomeModule.dll+12345 [TESForm]"]
        matches: list[str] = []

        record_scanner._find_matching_records(callstack, matches, "[RSP+", 30)

        # Should extract starting from offset 30
        assert len(matches) == 1
        # The extracted part should include the module info
        assert "TESForm" in matches[0]

    @pytest.mark.unit
    def test_find_matching_records_without_rsp_marker(self, record_scanner: "PythonRecordScanner") -> None:
        """Test _find_matching_records handles lines without RSP marker."""
        callstack = ["SomeFunction [TESForm]"]
        matches: list[str] = []

        record_scanner._find_matching_records(callstack, matches, "[RSP+", 30)

        assert len(matches) == 1
        assert matches[0] == "SomeFunction [TESForm]"

    @pytest.mark.unit
    def test_find_matching_records_case_insensitive(self, record_scanner: "PythonRecordScanner") -> None:
        """Test _find_matching_records is case insensitive."""
        callstack = [
            "Line with tesform lowercase",  # lowercase
            "Line with TESFORM uppercase",  # uppercase
            "Line with TesForm mixedcase",  # mixed
        ]
        matches: list[str] = []

        record_scanner._find_matching_records(callstack, matches, "[RSP+", 30)

        assert len(matches) == 3

    @pytest.mark.unit
    def test_find_matching_records_ignores_excluded(self, record_scanner: "PythonRecordScanner") -> None:
        """Test _find_matching_records ignores excluded records."""
        callstack = [
            "Line with TESForm",  # Should be found
            "Line with TESFileRecord",  # Should be ignored
            "Line with Unknown",  # Should be ignored
        ]
        matches: list[str] = []

        record_scanner._find_matching_records(callstack, matches, "[RSP+", 30)

        assert len(matches) == 1
        assert "TESForm" in matches[0]


# ============================================================================
# _generate_found_records_fragment Tests
# ============================================================================


class TestGenerateFoundRecordsFragment:
    """Tests for PythonRecordScanner._generate_found_records_fragment method."""

    @pytest.mark.unit
    def test_generate_fragment_counts_duplicates(self, record_scanner: "PythonRecordScanner") -> None:
        """Test fragment generation counts duplicate records."""
        matches = ["TESForm", "TESForm", "TESForm", "BGSKeyword"]

        fragment = record_scanner._generate_found_records_fragment(matches)

        content = "".join(fragment.content)
        # Should show count of 3 for TESForm
        assert "TESForm | 3" in content
        assert "BGSKeyword | 1" in content

    @pytest.mark.unit
    def test_generate_fragment_sorts_records(self, record_scanner: "PythonRecordScanner") -> None:
        """Test fragment generation sorts records."""
        matches = ["ZZZRecord", "AAARecord", "MMMRecord"]

        fragment = record_scanner._generate_found_records_fragment(matches)

        content = "".join(fragment.content)
        # Should be sorted alphabetically
        aaa_pos = content.find("AAARecord")
        mmm_pos = content.find("MMMRecord")
        zzz_pos = content.find("ZZZRecord")

        assert aaa_pos < mmm_pos < zzz_pos

    @pytest.mark.unit
    def test_generate_fragment_includes_footer(self, record_scanner: "PythonRecordScanner") -> None:
        """Test fragment generation includes explanatory footer."""
        matches = ["TESForm"]

        fragment = record_scanner._generate_found_records_fragment(matches)

        content = "".join(fragment.content)
        assert "Buffout 4" in content  # crashgen_name
        assert "Named Record" in content or "named record" in content.lower()

    @pytest.mark.unit
    def test_generate_fragment_has_content(self, record_scanner: "PythonRecordScanner") -> None:
        """Test generated fragment has_content is True."""
        matches = ["TESForm"]

        fragment = record_scanner._generate_found_records_fragment(matches)

        assert fragment.has_content is True


# ============================================================================
# extract_records Tests
# ============================================================================


class TestExtractRecords:
    """Tests for PythonRecordScanner.extract_records method."""

    @pytest.mark.unit
    def test_extract_records_returns_list(self, record_scanner: "PythonRecordScanner", sample_callstack: list[str]) -> None:
        """Test extract_records returns list of matches."""
        result = record_scanner.extract_records(sample_callstack)

        assert isinstance(result, list)

    @pytest.mark.unit
    def test_extract_records_finds_matching_records(self, record_scanner: "PythonRecordScanner") -> None:
        """Test extract_records finds matching records."""
        callstack = [
            "Line with TESForm record",
            "Line with BGSKeyword record",
        ]

        result = record_scanner.extract_records(callstack)

        assert len(result) == 2

    @pytest.mark.unit
    def test_extract_records_empty_callstack(self, record_scanner: "PythonRecordScanner") -> None:
        """Test extract_records handles empty callstack."""
        result = record_scanner.extract_records([])

        assert result == []

    @pytest.mark.unit
    def test_extract_records_no_matches(self, record_scanner: "PythonRecordScanner") -> None:
        """Test extract_records returns empty list when no matches."""
        callstack = ["No records here", "Just regular lines"]

        result = record_scanner.extract_records(callstack)

        assert result == []


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================


class TestRecordScannerEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.unit
    def test_scanner_with_empty_configuration(self, record_scanner_empty: "PythonRecordScanner") -> None:
        """Test scanner handles empty configuration gracefully."""
        callstack = ["Line with TESForm", "Line with BGSKeyword"]

        fragment, matches = record_scanner_empty.scan_named_records(callstack)

        # With empty records list, nothing should match
        assert matches == []
        content = "".join(fragment.content)
        assert "COULDN'T FIND ANY NAMED RECORDS" in content

    @pytest.mark.unit
    def test_scanner_record_partially_in_ignore_list(self, mock_yamldata_records: MagicMock) -> None:
        """Test scanner doesn't match partial ignore patterns incorrectly."""
        from ClassicLib.python.record_py import PythonRecordScanner

        # TESForm should not be blocked by TESFileRecord in ignore list
        scanner = PythonRecordScanner(mock_yamldata_records)

        callstack = ["Line with TESForm only"]
        result = scanner.extract_records(callstack)

        assert len(result) == 1
        assert "TESForm" in result[0]

    @pytest.mark.unit
    def test_scanner_multiple_records_same_line(self, record_scanner: "PythonRecordScanner") -> None:
        """Test scanner handles line with multiple matching records."""
        # Line contains multiple record types
        callstack = ["Line with TESForm and BGSKeyword together"]

        result = record_scanner.extract_records(callstack)

        # Should find the line (matches any record)
        assert len(result) == 1

    @pytest.mark.unit
    def test_scanner_unicode_content(self, record_scanner: "PythonRecordScanner") -> None:
        """Test scanner handles unicode content."""
        callstack = ["Unicode: 日本語 TESForm テスト"]

        result = record_scanner.extract_records(callstack)

        assert len(result) == 1
        assert "TESForm" in result[0]

    @pytest.mark.unit
    def test_scanner_very_long_line(self, record_scanner: "PythonRecordScanner") -> None:
        """Test scanner handles very long lines."""
        long_prefix = "A" * 1000
        callstack = [f"{long_prefix} TESForm {long_prefix}"]

        result = record_scanner.extract_records(callstack)

        assert len(result) == 1


# ============================================================================
# Alias Tests
# ============================================================================


class TestRecordScannerAlias:
    """Tests for RecordScanner alias."""

    @pytest.mark.unit
    def test_record_scanner_alias_exists(self) -> None:
        """Test RecordScanner is an alias for PythonRecordScanner."""
        from ClassicLib.python.record_py import PythonRecordScanner, RecordScanner

        assert RecordScanner is PythonRecordScanner


# ============================================================================
# Integration with ReportFragment
# ============================================================================


class TestRecordScannerReportFragmentIntegration:
    """Tests for ReportFragment integration."""

    @pytest.mark.unit
    def test_fragment_can_be_combined(self, record_scanner: "PythonRecordScanner") -> None:
        """Test generated fragment can be combined with other fragments."""
        from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment

        callstack1 = ["Line with TESForm"]
        callstack2 = ["Line with BGSKeyword"]

        fragment1, _ = record_scanner.scan_named_records(callstack1)
        fragment2, _ = record_scanner.scan_named_records(callstack2)

        combined = fragment1 + fragment2

        assert combined.has_content is True

    @pytest.mark.unit
    def test_fragment_can_add_header(self, record_scanner: "PythonRecordScanner") -> None:
        """Test generated fragment can have header added."""
        callstack = ["Line with TESForm"]

        fragment, _ = record_scanner.scan_named_records(callstack)
        with_header = fragment.with_header(["# Named Records\n"])

        content = "".join(with_header.content)
        assert "# Named Records" in content

    @pytest.mark.unit
    def test_fragment_to_list(self, record_scanner: "PythonRecordScanner") -> None:
        """Test generated fragment can be converted to list."""
        callstack = ["Line with TESForm"]

        fragment, _ = record_scanner.scan_named_records(callstack)
        lines = fragment.to_list()

        assert isinstance(lines, list)
        assert len(lines) > 0
