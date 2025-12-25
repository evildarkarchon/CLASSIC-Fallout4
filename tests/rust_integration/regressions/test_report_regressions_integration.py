"""
Regression tests for report generation functionality.

This module contains regression tests specifically for report generation to ensure
updates don't break existing functionality or parity between Rust and Python
implementations.

Test Categories:
- Baseline report format validation
- Established output pattern preservation
"""

from __future__ import annotations

import logging

import pytest

from tests.fixtures.parity_fixtures import normalize_markdown_content, skip_if_rust_unavailable
from tests.rust_integration.parity.test_report_parity import ReportParityValidator

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


@skip_if_rust_unavailable("report_generation")
class TestReportGenerationRegression:
    """
    Regression tests specifically for report generation to ensure
    updates don't break existing functionality or parity.
    """

    async def test_baseline_report_formats(self):
        """
        Test that established report formats continue to work identically
        between Rust and Python implementations.
        """
        # Load baseline report templates/formats
        baseline_formats = [
            {
                "name": "standard_crash_report",
                "template": "# {title}\n\n## Analysis\n{analysis_content}\n\n## Statistics\n{statistics}",
                "data": {
                    "title": "Fallout 4 Crash Analysis",
                    "analysis_content": "Analysis results here",
                    "statistics": "- Plugins: 150\n- FormIDs: 25",
                },
            },
            {
                "name": "error_report",
                "template": "### ❌ {error_type}\n\n**Message**: {message}\n\n{details}",
                "data": {
                    "error_type": "Critical Error",
                    "message": "System failure detected",
                    "details": "Detailed error information and resolution steps.",
                },
            },
        ]

        validator = ReportParityValidator()
        rust_impl = validator.create_rust_implementation()

        if not rust_impl:
            pytest.skip("Rust report generation not available")

        for format_test in baseline_formats:
            template = format_test["template"]
            data = format_test["data"]

            # Python template rendering
            python_result = template.format(**data)

            # Rust template rendering (if available)
            if hasattr(rust_impl, "render_template"):
                rust_result = rust_impl.render_template(template, data)  # type: ignore

                # Compare results
                python_normalized = normalize_markdown_content(python_result)
                rust_normalized = normalize_markdown_content(rust_result)

                assert python_normalized == rust_normalized, f"Baseline format regression in {format_test['name']}"

            else:
                logger.warning(f"Rust template rendering not available for {format_test['name']}")

    async def test_established_output_patterns(self):
        """Test that known output patterns are preserved between implementations."""
        import re as regex

        # Define established patterns that should be maintained
        patterns = [
            {
                "name": "plugin_list_pattern",
                "input": {"00": "Fallout4.esm", "01": "DLCRobot.esm"},
                "expected_pattern": r"## Plugin Load Order.*\[00\].*Fallout4\.esm.*\[01\].*DLCRobot\.esm",
            },
            {
                "name": "formid_pattern",
                "input": ["0x00000014", "0x01002A34"],
                "expected_pattern": r"## FormIDs Found.*1\..*0x00000014.*2\..*0x01002A34",
            },
            {
                "name": "statistics_pattern",
                "input": {"plugin_count": 150, "formid_count": 25},
                "expected_pattern": r"## Analysis Statistics.*Total Plugins.*150.*FormIDs Found.*25",
            },
        ]

        validator = ReportParityValidator()
        python_impl = validator.create_python_implementation()

        for pattern_test in patterns:
            pattern_name = pattern_test["name"]
            input_data = pattern_test["input"]
            expected_pattern = pattern_test["expected_pattern"]

            # Get appropriate formatter
            if "plugin" in pattern_name:
                formatter = python_impl["markdown_utils"]["format_plugin_list"]
            elif "formid" in pattern_name:
                formatter = python_impl["markdown_utils"]["format_formid_list"]
            elif "statistics" in pattern_name:
                formatter = python_impl["markdown_utils"]["generate_statistics"]
            else:
                continue

            # Generate output
            result = formatter(input_data)

            # Validate pattern
            assert regex.search(expected_pattern, result, regex.DOTALL), (
                f"Pattern regression in {pattern_name}: expected pattern not found in output"
            )
