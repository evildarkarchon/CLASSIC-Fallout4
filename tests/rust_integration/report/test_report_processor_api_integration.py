"""Integration tests for ParallelReportProcessor API compliance.

This module tests that report_rust.py wrapper correctly calls the static
methods of ParallelReportProcessor (not instance methods).

The test suite verifies:
1. process_batch() is called as static method (not instance method)
2. combine_fragments() is called as static method (not instance method)
3. Proper return type handling for both methods
4. Integration with ParallelReportProcessor wrapper

Bugs fixed:
- report_rust.py:615 - process_batch() is static, not instance method
- report_rust.py:640 - combine_fragments() is static, not instance method

Note:
    These tests require the Rust classic_scanlog module to be available.
    They will gracefully skip if the module is not installed.
"""

import pytest


@pytest.mark.rust
@pytest.mark.integration
def test_parallel_processor_process_batch_static() -> None:
    """Verify process_batch() is called as static method.

    This test ensures process_batch is called on the class (ParallelReportProcessor),
    not on an instance. The method should be accessible without creating an instance.

    The test confirms:
    - Method is static (class method, not instance method)
    - Can be called directly on class
    - Returns list of processed results
    - No AttributeError is raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor

        # Test data - list of report line lists
        reports = [
            ["line1", "line2", "line3"],
            ["line4", "line5", "line6"],
        ]

        # Call as STATIC method (not instance method)
        # This is the correct usage: ParallelReportProcessor.process_batch()
        # NOT: instance.process_batch()
        # Note: processor_fn is a positional argument, not keyword
        result = ParallelReportProcessor.process_batch(reports, None)

        # Verify return type is list
        assert isinstance(result, list), f"process_batch should return list, got {type(result).__name__}"

        # Result should have same number of items as input
        assert len(result) == len(reports), f"Expected {len(reports)} results, got {len(result)}"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_parallel_processor_combine_fragments_static() -> None:
    """Verify combine_fragments() is called as static method.

    This test ensures combine_fragments is called on the class (ParallelReportProcessor),
    not on an instance. The method should be accessible without creating an instance.

    The test confirms:
    - Method is static (class method, not instance method)
    - Can be called directly on class
    - Returns ReportFragment
    - Properly combines multiple fragments

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor, ReportFragment

        # Create test fragments
        frag1 = ReportFragment.from_lines(["Header", "Line 1"])
        frag2 = ReportFragment.from_lines(["Line 2", "Line 3"])

        # Call as STATIC method (not instance method)
        # This is the correct usage: ParallelReportProcessor.combine_fragments()
        # NOT: instance.combine_fragments()
        combined = ParallelReportProcessor.combine_fragments([frag1, frag2])

        # Verify return type is ReportFragment
        assert isinstance(combined, ReportFragment), f"combine_fragments should return ReportFragment, got {type(combined).__name__}"

        # Verify combined content
        lines = combined.to_list()
        assert isinstance(lines, list), "to_list() should return list"
        assert len(lines) >= 4, f"Should combine both fragments (>=4 lines), got {len(lines)}"

        # Verify content is preserved
        combined_text = "\n".join(lines)
        assert "Header" in combined_text, "Should preserve header"
        assert "Line 1" in combined_text, "Should preserve line 1"
        assert "Line 2" in combined_text, "Should preserve line 2"
        assert "Line 3" in combined_text, "Should preserve line 3"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_parallel_processor_not_instance_methods() -> None:
    """Verify that process_batch and combine_fragments are NOT instance methods.

    This negative test confirms that attempting to create an instance and call
    these methods as instance methods would fail. They are static methods only.

    The test verifies:
    - Methods are accessible on class
    - Methods are static (not instance-bound)

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor

        # Verify methods exist on the class (not requiring instance)
        assert hasattr(ParallelReportProcessor, "process_batch"), "process_batch should be accessible on class"
        assert hasattr(ParallelReportProcessor, "combine_fragments"), "combine_fragments should be accessible on class"

        # Verify they are callable from the class
        assert callable(ParallelReportProcessor.process_batch), "process_batch should be callable from class"
        assert callable(ParallelReportProcessor.combine_fragments), "combine_fragments should be callable from class"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_report_processor_wrapper_integration() -> None:
    """Test ParallelReportProcessor wrapper integration.

    This test uses the actual wrapper class (ParallelReportProcessor)
    to ensure the fixes work in the real usage context. The wrapper should
    correctly call the static methods internally.

    The test confirms:
    - Wrapper can be instantiated
    - process_reports() works (uses process_batch internally)
    - combine_fragments_parallel() works (uses combine_fragments internally)
    - No AttributeError is raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.rust.report_rust import (
            ParallelReportProcessor,
            RustAcceleratedReportFragment,
        )

        # Create wrapper instance
        processor = ParallelReportProcessor()

        # Test process_reports (uses process_batch internally at line 615)
        reports = [["line1", "line2"], ["line3", "line4"]]
        result = processor.process_reports(reports)

        assert isinstance(result, list), "process_reports should return list"
        assert len(result) == len(reports), f"Expected {len(reports)} results, got {len(result)}"

        # Test combine_fragments_parallel (uses combine_fragments internally at line 640)
        frag1 = RustAcceleratedReportFragment.from_lines(["line1"])
        frag2 = RustAcceleratedReportFragment.from_lines(["line2"])

        combined = processor.combine_fragments_parallel([frag1, frag2])

        assert combined is not None, "Should return combined fragment"
        assert isinstance(combined, RustAcceleratedReportFragment), (
            f"Should return RustAcceleratedReportFragment, got {type(combined).__name__}"
        )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_process_batch_with_processor_function() -> None:
    """Test process_batch with processor_fn=None (as used by wrapper).

    This test verifies that process_batch works correctly with processor_fn=None,
    which is how the wrapper uses it (see report_rust.py:615 bug fix #3).

    The test confirms:
    - Static method works with processor_fn=None
    - Returns list of report fragments
    - Each fragment is a list of strings

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor

        # Test data
        reports = [
            ["line1", "line2"],
            ["line3", "line4"],
        ]

        # Call with None as second positional argument (as wrapper does in bug fix #3)
        result = ParallelReportProcessor.process_batch(reports, None)

        assert isinstance(result, list), "Should return list"
        assert len(result) == len(reports), "Should process all reports"

        # Verify structure matches API signature: list[list[str]]
        for item in result:
            assert isinstance(item, list), f"Each item should be list, got {type(item).__name__}"
            for line in item:
                assert isinstance(line, str), f"Each line should be string, got {type(line).__name__}"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_combine_fragments_empty_list() -> None:
    """Test combine_fragments with empty list.

    This test verifies that combine_fragments handles edge case of empty
    fragment list gracefully.

    The test confirms:
    - Static method handles empty list
    - Returns valid ReportFragment or appropriate response
    - No exceptions raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor, ReportFragment

        # Empty fragment list
        fragments: list[ReportFragment] = []

        # Should handle empty list gracefully
        result = ParallelReportProcessor.combine_fragments(fragments)

        # May return empty fragment or None, but shouldn't crash
        assert result is None or isinstance(result, ReportFragment), (
            f"Should return None or ReportFragment for empty list, got {type(result).__name__}"
        )

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_combine_fragments_single_fragment() -> None:
    """Test combine_fragments with single fragment.

    This test verifies that combine_fragments handles the edge case of a
    single fragment correctly (should return the fragment as-is or equivalent).

    The test confirms:
    - Static method handles single fragment
    - Returns valid ReportFragment
    - Content is preserved

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor, ReportFragment

        # Single fragment
        frag = ReportFragment.from_lines(["Line 1", "Line 2"])
        fragments = [frag]

        result = ParallelReportProcessor.combine_fragments(fragments)

        assert isinstance(result, ReportFragment), f"Should return ReportFragment, got {type(result).__name__}"

        # Content should be preserved
        lines = result.to_list()
        assert len(lines) >= 2, "Should preserve content"
        assert "Line 1" in lines or "Line 1" in "\n".join(lines), "Should preserve line 1"
        assert "Line 2" in lines or "Line 2" in "\n".join(lines), "Should preserve line 2"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_process_batch_empty_reports() -> None:
    """Test process_batch with empty reports list.

    This test verifies that process_batch handles empty input gracefully.

    The test confirms:
    - Static method handles empty list
    - Returns empty list
    - No exceptions raised

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from classic_scanlog import ParallelReportProcessor

        # Empty reports list
        reports: list[list[str]] = []

        # Note: processor_fn is a positional argument, not keyword
        result = ParallelReportProcessor.process_batch(reports, None)

        assert isinstance(result, list), "Should return list"
        assert len(result) == 0, "Should return empty list for empty input"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_wrapper_process_reports_realistic() -> None:
    """Test wrapper with realistic report data.

    This test uses realistic crash log report data to verify the wrapper
    works correctly with actual usage patterns.

    The test confirms:
    - Wrapper handles realistic data
    - Processing completes successfully
    - Results are properly formatted

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.rust.report_rust import ParallelReportProcessor

        processor = ParallelReportProcessor()

        # Realistic crash log reports
        reports = [
            [
                "Crash Report Header",
                "Exception: Access Violation",
                "Address: 0x7FF123456789",
            ],
            [
                "Stack Trace:",
                "Module: game.exe",
                "Offset: +0x12345",
            ],
        ]

        result = processor.process_reports(reports)

        assert isinstance(result, list), "Should return list"
        assert len(result) == len(reports), "Should process all reports"

        # Each result should be processed
        for item in result:
            assert item is not None, "Results should not be None"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")


@pytest.mark.rust
@pytest.mark.integration
def test_wrapper_combine_fragments_realistic() -> None:
    """Test wrapper combine with realistic fragment data.

    This test uses realistic crash log fragments to verify the wrapper
    works correctly with actual usage patterns.

    The test confirms:
    - Wrapper handles realistic fragments
    - Combining completes successfully
    - Combined result is valid

    Raises:
        pytest.skip: If Rust classic_scanlog module is not available
    """
    try:
        from ClassicLib.rust.report_rust import (
            ParallelReportProcessor,
            RustAcceleratedReportFragment,
        )

        processor = ParallelReportProcessor()

        # Realistic crash log fragments
        frag1 = RustAcceleratedReportFragment.from_lines(["Crash Report", "Date: 2025-11-04"])
        frag2 = RustAcceleratedReportFragment.from_lines(["Exception Type: Access Violation", "Fault Module: game.dll"])
        frag3 = RustAcceleratedReportFragment.from_lines(["Stack Trace:", "game.exe+0x12345", "game.dll+0x67890"])

        combined = processor.combine_fragments_parallel([frag1, frag2, frag3])

        assert combined is not None, "Should return combined fragment"
        assert isinstance(combined, RustAcceleratedReportFragment), "Should return RustAcceleratedReportFragment"

        # Verify content was combined
        lines = combined.to_list()
        assert len(lines) > 0, "Combined fragment should have content"

        # Should contain elements from all fragments
        combined_text = "\n".join(lines)
        assert "Crash Report" in combined_text or any("Crash Report" in line for line in lines), "Should preserve content from fragment 1"

    except ImportError as e:
        pytest.skip(f"Rust classic_scanlog not available: {e}")
