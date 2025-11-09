"""
Python integration tests for Rust RecordScanner.

This module provides Python-side integration tests that mirror the comprehensive
Rust tests in classic-rust/tests/test_record_scanner.rs to ensure Python-Rust parity.

Tests cover:
- Basic record scanning and extraction
- Record validation and filtering
- Aho-Corasick multi-pattern matching
- Batch processing with parallel operations
- RSP marker detection and offset extraction
- Edge cases and error handling
- Performance characteristics (40x speedup target)
"""

from types import SimpleNamespace

import pytest

try:
    from classic_scanlog import RecordScanner, contains_record, scan_records_batch

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


# ============================================================================
# Test Data Helpers
# ============================================================================


def create_mock_yamldata():
    """Create mock yamldata object for RecordScanner."""
    return SimpleNamespace(
        classic_records_list=[
            "BSResource",
            "TESObjectREFR",
            "Actor",
            "BSGeometrySegmentData",
            "TESForm",
        ],
        game_ignore_records=[
            "void*",
            "char*",
            "NULL",
            "size_t",
        ],
        crashgen_name="Buffout 4",
    )


# ============================================================================
# Pure Function Tests (contains_record)
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust RecordScanner not available")
class TestContainsRecord:
    """Test the pure contains_record function."""

    def test_contains_record_basic(self):
        """Test basic record detection."""
        target_records = ["BSResource", "Archive"]
        ignore_records = ["void*"]

        # Should match - contains target and no ignored terms
        assert contains_record("0x7FF6F1E52E60    (BSResource::Archive2**)", target_records, ignore_records)

        # Should not match - contains ignored term
        assert not contains_record("0x7FF6EF4B2DC8    (void* -> Fallout4.exe+0712DC8)", target_records, ignore_records)

        # Should not match - doesn't contain target
        assert not contains_record("0x1AC             (size_t)", target_records, ignore_records)

    def test_contains_record_case_insensitive(self):
        """Test case-insensitive record detection."""
        target_records = ["bsresource"]
        ignore_records = []

        # Should match regardless of case
        assert contains_record("0x123 (BSResource::Archive)", target_records, ignore_records)
        assert contains_record("0x123 (bsresource::archive)", target_records, ignore_records)
        assert contains_record("0x123 (BSRESOURCE::ARCHIVE)", target_records, ignore_records)

    def test_contains_record_multiple_targets(self):
        """Test matching against multiple target records."""
        target_records = [
            "BSResource",
            "TESObjectREFR",
            "Actor",
        ]
        ignore_records = []

        # Should match any target
        assert contains_record("0x123 (BSResource*)", target_records, ignore_records)
        assert contains_record("0x456 (TESObjectREFR*)", target_records, ignore_records)
        assert contains_record("0x789 (Actor*)", target_records, ignore_records)

    def test_contains_record_multiple_ignores(self):
        """Test filtering with multiple ignore terms."""
        target_records = ["test"]
        ignore_records = [
            "void*",
            "NULL",
            "char*",
        ]

        # Should not match if any ignore term is present
        assert not contains_record("test (void*)", target_records, ignore_records)
        assert not contains_record("test (NULL)", target_records, ignore_records)
        assert not contains_record('test (char*) "string"', target_records, ignore_records)

        # Should match if no ignore terms present
        assert contains_record("test (int)", target_records, ignore_records)

    def test_contains_record_empty_lists(self):
        """Test with empty target or ignore lists."""
        # Empty targets - should never match
        assert not contains_record("0x123 (BSResource*)", [], [])

        # Empty ignores - should match if target present
        targets = ["BSResource"]
        assert contains_record("0x123 (BSResource*)", targets, [])


# ============================================================================
# Batch Processing Tests (scan_records_batch)
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust RecordScanner not available")
class TestScanRecordsBatch:
    """Test batch record scanning."""

    def test_scan_records_batch_single_segment(self):
        """Test scanning a single segment."""
        # Note: RSP format is "[RSP+NN ] 0xADDRESS      " which is 30 chars total
        segments = [
            [
                "[RSP+8  ] 0x80ECFDFA90      (void*)",
                "[RSP+10 ] 0x1AC             (size_t)",
                '[RSP+18 ] 0x22FCA037A78     (char*) "WCLINS_PRP_Patch - Main.ba2"',
                "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)",
                "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)",
            ]
        ]

        target_records = ["BSResource", "BSGeometrySegmentData"]
        ignore_records = ["void*", "char*"]

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        assert len(results[0]) == 2

        # Check extracted records (after RSP offset of 30 chars)
        assert "BSResource::Archive2**" in results[0][0]
        assert "BSGeometrySegmentData*" in results[0][1]

    def test_scan_records_batch_multiple_segments(self):
        """Test scanning multiple segments."""
        segments = [
            [
                "[RSP+8  ] 0x123             (BSResource*)",
                "[RSP+10 ] 0x456             (void*)",
            ],
            [
                "[RSP+8  ] 0x789             (TESObjectREFR*)",
            ],
            [
                "No records here",
            ],
        ]

        target_records = ["BSResource", "TESObjectREFR"]
        ignore_records = ["void*"]

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 3
        assert len(results[0]) == 1  # Only BSResource (void* ignored)
        assert len(results[1]) == 1  # TESObjectREFR
        assert len(results[2]) == 0  # No matches

    def test_scan_records_batch_rsp_extraction(self):
        """Test RSP marker detection and offset extraction."""
        # Test RSP marker detection and offset extraction
        # RSP format: "[RSP+NN ] 0xADDRESS      " = 30 chars
        segments = [
            [
                "[RSP+8  ] 0x123               (BSResource::Archive*)",
                "Non-RSP line with BSResource::Archive*",
            ]
        ]

        target_records = ["BSResource"]
        ignore_records = []

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        assert len(results[0]) == 2

        # First should be extracted after offset (30 chars)
        # Second should be the full line (trimmed)
        assert results[0][0] == "(BSResource::Archive*)"
        assert results[0][1] == "Non-RSP line with BSResource::Archive*"

    def test_scan_records_batch_empty(self):
        """Test with empty inputs."""
        # Empty segments
        results = scan_records_batch([], ["test"], [])
        assert len(results) == 0

        # Segments with no matches
        segments = [["no match"]]
        results = scan_records_batch(segments, ["target"], [])
        assert len(results) == 1
        assert len(results[0]) == 0

    def test_scan_records_batch_short_rsp_line(self):
        """Test handling of short RSP lines."""
        # Line with RSP marker but shorter than offset
        segments = [
            [
                "[RSP+8  ] short",  # Only 15 chars, offset is 30
                "[RSP+10 ] 0x123456789ABCDEF0123456789 (BSResource*)",  # Long enough
            ]
        ]

        target_records = ["BSResource", "short"]
        ignore_records = []

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        # Short line should be skipped (len <= offset check)
        # Long line should be extracted
        assert len(results[0]) == 1


# ============================================================================
# RecordScanner Class Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust RecordScanner not available")
class TestRecordScanner:
    """Test RecordScanner class functionality."""

    def test_record_scanner_creation(self):
        """Test RecordScanner creation."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        assert scanner is not None

    def test_extract_records_basic(self):
        """Test basic record extraction."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        # Ensure proper 30-char offset: "[RSP+NN ] 0xADDRESS      "
        callstack = [
            "[RSP+8  ] 0x80ECFDFA90      (void*)",
            "[RSP+10 ] 0x1AC             (size_t)",
            "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)",
            "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)",
        ]

        records = scanner.extract_records(callstack)

        assert len(records) == 2
        assert "BSResource" in records[0]
        assert "BSGeometrySegmentData" in records[1]

    def test_extract_records_empty_callstack(self):
        """Test extraction with empty callstack."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        records = scanner.extract_records([])

        assert len(records) == 0

    def test_extract_records_no_matches(self):
        """Test extraction with no matching records."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        callstack = [
            "[RSP+8  ] 0x123             (void*)",
            "[RSP+10 ] 0x456             (char*)",
            "[RSP+18 ] 0x789             (size_t)",
        ]

        records = scanner.extract_records(callstack)

        # All should be filtered by ignore list
        assert len(records) == 0

    def test_extract_records_case_insensitive(self):
        """Test case-insensitive record extraction."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        callstack = [
            "[RSP+8  ] 0x123             (bsresource*)",
            "[RSP+10 ] 0x456             (TESOBJECTREFR*)",
            "[RSP+18 ] 0x789             (AcToR*)",
        ]

        records = scanner.extract_records(callstack)

        assert len(records) == 3

    def test_extract_records_non_rsp_lines(self):
        """Test extraction of non-RSP formatted lines."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        callstack = [
            "BSResource::Archive loading",
            "  TESObjectREFR reference",
            "Actor processing",
        ]

        records = scanner.extract_records(callstack)

        # Should extract full lines (trimmed) since no RSP marker
        assert len(records) == 3
        assert records[0] == "BSResource::Archive loading"
        assert records[1] == "TESObjectREFR reference"
        assert records[2] == "Actor processing"

    def test_extract_records_mixed_format(self):
        """Test extraction with mixed RSP and non-RSP lines."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        callstack = [
            "[RSP+8  ] 0x123               (BSResource*)",
            "TESObjectREFR without RSP",
            "[RSP+10 ] 0x456               (Actor*)",
        ]

        records = scanner.extract_records(callstack)

        assert len(records) == 3
        # RSP lines should be extracted after offset (30 chars)
        assert records[0] == "(BSResource*)"
        # Non-RSP line should be full line
        assert records[1] == "TESObjectREFR without RSP"
        assert records[2] == "(Actor*)"

    def test_clear_cache(self):
        """Test cache clearing."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        # Clear cache should not error (even if currently no-op)
        scanner.clear_cache()

    def test_record_counting_and_sorting(self):
        """Test that duplicate records are counted correctly."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        callstack = [
            "[RSP+8  ] 0x123               (BSResource*)",
            "[RSP+10 ] 0x456               (BSResource*)",
            "[RSP+18 ] 0x789               (BSResource*)",
            "[RSP+20 ] 0xABC               (TESObjectREFR*)",
            "[RSP+28 ] 0xDEF               (TESObjectREFR*)",
            "[RSP+30 ] 0x111               (Actor*)",
        ]

        records = scanner.extract_records(callstack)

        assert len(records) == 6

        # Count occurrences
        bsresource_count = sum(1 for r in records if "bsresource" in r.lower())
        tesobject_count = sum(1 for r in records if "tesobject" in r.lower())
        actor_count = sum(1 for r in records if "actor" in r.lower())

        assert bsresource_count == 3
        assert tesobject_count == 2
        assert actor_count == 1

    def test_realistic_crash_log_segment(self):
        """Test with realistic crash log segment."""
        yamldata = create_mock_yamldata()
        scanner = RecordScanner(yamldata)

        # Real-world crash log segment from test data
        callstack = [
            "[RSP+8  ] 0x80ECFDFA90      (void*)",
            "[RSP+10 ] 0x1AC             (size_t)",
            '[RSP+18 ] 0x22FCA037A78     (char*) "WCLINS_PRP_Patch - Main.ba2"',
            "[RSP+20 ] 0x0               (NULL)",
            "[RSP+28 ] 0x80ECFDFB30      (void*)",
            "[RSP+30 ] 0x22FCA037950     (void*)",
            "[RSP+38 ] 0x7FF6EF4B2DC8    (void* -> Fallout4.exe+0712DC8)",
            "[RSP+40 ] 0x7FF6F1E52E60      (BSResource::Archive2**)",
            "[RSP+48 ] 0x2302DDAB040       (BSGeometrySegmentData*)",
        ]

        records = scanner.extract_records(callstack)

        # Should find BSResource and BSGeometrySegmentData
        assert len(records) == 2
        assert "BSResource::Archive2**" in records[0]
        assert "BSGeometrySegmentData*" in records[1]


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust RecordScanner not available")
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_scan_records_batch_special_characters(self):
        """Test with special characters in record types."""
        segments = [
            [
                "[RSP+8  ] 0x123             (BSResource::Archive<T>*)",
                "[RSP+10 ] 0x456             (TESForm[100])",
            ]
        ]

        target_records = ["BSResource", "TESForm"]
        ignore_records = []

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        assert len(results[0]) == 2

    def test_scan_records_batch_unicode(self):
        """Test with unicode characters."""
        segments = [
            [
                "[RSP+8  ] 0x123             (Record with émojis 🎮)",
            ]
        ]

        target_records = ["Record"]
        ignore_records = []

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        assert len(results[0]) == 1

    def test_scan_records_batch_very_long_lines(self):
        """Test with very long record lines."""
        long_record = f"BSResource{'A' * 10000}"
        segments = [
            [
                f"[RSP+8  ] 0x123             ({long_record})",
            ]
        ]

        target_records = ["BSResource"]
        ignore_records = []

        results = scan_records_batch(segments, target_records, ignore_records)

        assert len(results) == 1
        assert len(results[0]) == 1
        assert len(results[0][0]) > 10000

    def test_contains_record_partial_matches(self):
        """Test partial substring matching."""
        target_records = ["BS"]
        ignore_records = []

        # Should match partial substring
        assert contains_record("BSResource", target_records, ignore_records)
        assert contains_record("ABSTRACT", target_records, ignore_records)

    def test_contains_record_exact_boundary(self):
        """Test when target and ignore both match."""
        target_records = ["test"]
        ignore_records = ["test"]

        # Target and ignore both match - ignore should win
        assert not contains_record("test", target_records, ignore_records)


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust RecordScanner not available")
@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics."""

    def test_batch_scanning_performance(self):
        """Test batch scanning performance (40x speedup target)."""
        import time

        # Create realistic crash log segments
        segments = []
        for i in range(1000):
            segment = [
                f"[RSP+{i % 100}  ] 0x{i * 123456:016X}      (void*)",
                f"[RSP+{(i % 100) + 8}  ] 0x{i * 654321:016X}      (BSResource::Archive2**)",
                f"[RSP+{(i % 100) + 16}  ] 0x{i:016X}      (size_t)",
                f"[RSP+{(i % 100) + 24}  ] 0x{i * 111111:016X}      (TESObjectREFR*)",
                f'[RSP+{(i % 100) + 32}  ] 0x{i * 222222:016X}      (char*) "test.ba2"',
            ]
            segments.append(segment)

        target_records = [
            "BSResource",
            "TESObjectREFR",
            "Actor",
        ]
        ignore_records = ["void*", "char*"]

        start = time.perf_counter()
        results = scan_records_batch(segments, target_records, ignore_records)
        elapsed = time.perf_counter() - start

        assert len(results) == 1000
        # Each segment should find 2 matches (BSResource and TESObjectREFR)
        assert all(len(r) == 2 for r in results)

        # Should be fast (< 50ms for 1000 segments)
        assert elapsed < 0.05, f"Expected < 50ms, got {elapsed * 1000:.2f}ms"

    def test_aho_corasick_efficiency(self):
        """Test Aho-Corasick multi-pattern matching efficiency."""
        import time

        # Test that Aho-Corasick provides efficient multi-pattern matching
        segments = []
        for i in range(100):
            segment = [f"Line {j} with pattern{i % 10}" for j in range(100)]
            segments.append(segment)

        # Many target patterns (Aho-Corasick should be efficient)
        target_records = [f"pattern{i}" for i in range(20)]
        ignore_records = []

        start = time.perf_counter()
        results = scan_records_batch(segments, target_records, ignore_records)
        elapsed = time.perf_counter() - start

        # Verify results
        assert len(results) == 100

        # Aho-Corasick should make this very fast
        assert elapsed < 0.1, f"Expected < 100ms, got {elapsed * 1000:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
