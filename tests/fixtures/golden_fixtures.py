"""Golden file fixtures for parity testing.

Provides fixtures and utilities for capturing Python output and comparing
against stored golden files. Used for Rust-Python parity validation.

Per Phase 6 CONTEXT.md decisions:
- Character-exact matching (byte-for-byte identical)
- Mask timestamps and paths with placeholders before comparison
- Full diff on failure for debugging
"""

from __future__ import annotations

import json
import re
from difflib import unified_diff
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    pass

# Directory for golden files
GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "captured"

# Placeholder formats per RESEARCH.md
TIMESTAMP_PLACEHOLDER = "{{TIMESTAMP}}"
PATH_PLACEHOLDER = "{{PATH}}"

# Regex patterns for dynamic data masking
TIMESTAMP_PATTERNS = [
    # ISO 8601 full datetime with optional fractional seconds and timezone
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"),
    # Date only (YYYY-MM-DD)
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    # Time only (HH:MM:SS)
    re.compile(r"\d{2}:\d{2}:\d{2}"),
]
PATH_PATTERNS = [
    # Windows paths (e.g., C:\Users\test\file.txt)
    re.compile(r"[A-Za-z]:\\(?:[^\s\"'<>|]+)"),
    # Unix common paths (/home, /tmp, /var, /usr, /Users, /mnt)
    re.compile(r"/(?:home|tmp|var|usr|Users|mnt)[^\s\"'<>|]*"),
]


def mask_dynamic_data(text: str) -> str:
    """Replace timestamps and paths with placeholders.

    Args:
        text: Raw text potentially containing dynamic data.

    Returns:
        Text with timestamps replaced by {{TIMESTAMP}} and paths by {{PATH}}.
    """
    result = text

    # Mask timestamps first (more specific patterns)
    for pattern in TIMESTAMP_PATTERNS:
        result = pattern.sub(TIMESTAMP_PLACEHOLDER, result)

    # Mask paths
    for pattern in PATH_PATTERNS:
        result = pattern.sub(PATH_PLACEHOLDER, result)

    return result


def generate_diff(expected: str, actual: str) -> str:
    """Generate unified diff for debugging parity failures.

    Args:
        expected: Expected (golden) content.
        actual: Actual (current) content.

    Returns:
        Unified diff string showing differences.
    """
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)

    diff = unified_diff(
        expected_lines,
        actual_lines,
        fromfile="expected (golden)",
        tofile="actual",
        lineterm=""
    )
    return "".join(diff)


class GoldenFileChecker:
    """Helper class for golden file comparison."""

    def __init__(self, request: pytest.FixtureRequest, golden_dir: Path = GOLDEN_DIR) -> None:
        """Initialize with pytest request for --update-golden option.

        Args:
            request: Pytest fixture request object.
            golden_dir: Directory to store golden files.
        """
        self.request = request
        self.golden_dir = golden_dir
        self.golden_dir.mkdir(parents=True, exist_ok=True)

    def check(self, output: str | dict[str, Any], name: str) -> None:
        """Compare output against golden file.

        Args:
            output: The output to check (string or dict for JSON).
            name: Base name for the golden file (without extension).

        Raises:
            pytest.skip.Exception: If golden file was created (first run).
            pytest.fail.Exception: If output doesn't match golden file (with diff).
        """
        # Determine file extension and format output
        if isinstance(output, dict):
            golden_path = self.golden_dir / f"{name}.json"
            formatted = json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False)
        else:
            golden_path = self.golden_dir / f"{name}.golden"
            formatted = str(output)

        # Mask dynamic data
        masked = mask_dynamic_data(formatted)

        # Check for update mode
        update_golden = self.request.config.getoption("--update-golden", default=False)

        if update_golden:
            golden_path.write_text(masked, encoding="utf-8")
            return

        # Compare against existing golden file
        if not golden_path.exists():
            # Create golden file if it doesn't exist (first run)
            golden_path.write_text(masked, encoding="utf-8")
            pytest.skip(f"Created new golden file: {golden_path.name}")

        expected = golden_path.read_text(encoding="utf-8")

        if masked != expected:
            diff = generate_diff(expected, masked)
            pytest.fail(
                f"Golden file mismatch for {name}:\n\n{diff}\n\n"
                f"Run with --update-golden to update the golden file."
            )


@pytest.fixture
def golden_file(request: pytest.FixtureRequest) -> GoldenFileChecker:
    """Fixture providing golden file comparison.

    Usage:
        def test_something(golden_file):
            result = my_function()
            golden_file.check(result, "test_something_output")

    Run with --update-golden to regenerate golden files.

    Args:
        request: Pytest fixture request object.

    Returns:
        GoldenFileChecker instance for comparing outputs.
    """
    return GoldenFileChecker(request)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden command line option.

    Args:
        parser: Pytest parser object for adding options.
    """
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden files instead of comparing",
    )
