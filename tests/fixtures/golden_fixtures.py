"""Golden file fixtures for parity testing.

Provides fixtures and utilities for capturing Python output and comparing
against stored golden files. Used for Rust-Python parity validation.

Per Phase 10 CONTEXT.md decisions:
- Character-exact matching (byte-for-byte identical after normalization)
- Mask timestamps with {{TIMESTAMP}} placeholder (timestamps change on every run)
- Paths are NOT masked - they provide valuable debugging information
- Path slashes are normalized (backslash -> forward slash) for cross-platform comparison
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

# Placeholder format for timestamps
TIMESTAMP_PLACEHOLDER = "{{TIMESTAMP}}"

# Regex patterns for timestamp masking only
# Note: Paths are NOT masked per Phase 10 decision - they provide debugging value
TIMESTAMP_PATTERNS = [
    # ISO 8601 full datetime with optional fractional seconds and timezone
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"),
    # Date only (YYYY-MM-DD)
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    # Time only (HH:MM:SS)
    re.compile(r"\d{2}:\d{2}:\d{2}"),
]


def mask_dynamic_data(text: str) -> str:
    """Replace timestamps with placeholders.

    Masks only timestamps, which change on every run and provide no debugging value.
    Paths are NOT masked - they provide valuable debugging information when
    parity tests fail.

    Args:
        text: Raw text potentially containing dynamic data.

    Returns:
        Text with timestamps replaced by {{TIMESTAMP}}.
    """
    result = text

    # Mask timestamps only (paths are kept visible for debugging)
    for pattern in TIMESTAMP_PATTERNS:
        result = pattern.sub(TIMESTAMP_PLACEHOLDER, result)

    return result


def normalize_paths(text: str) -> str:
    """Normalize path separators for cross-platform comparison.

    Replaces backslashes with forward slashes to ensure consistent
    comparison between Windows and Unix-style paths.

    Args:
        text: Text potentially containing file paths.

    Returns:
        Text with backslashes replaced by forward slashes.
    """
    return text.replace("\\", "/")


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

    diff = unified_diff(expected_lines, actual_lines, fromfile="expected (golden)", tofile="actual", lineterm="")
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

        Applies timestamp masking and path normalization before comparison
        per Phase 10 CONTEXT.md decisions.

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

        # Apply normalizations: timestamp masking + path slash normalization
        normalized = mask_dynamic_data(formatted)
        normalized = normalize_paths(normalized)

        # Check for update mode
        update_golden = self.request.config.getoption("--update-golden", default=False)

        if update_golden:
            golden_path.write_text(normalized, encoding="utf-8")
            return

        # Compare against existing golden file
        if not golden_path.exists():
            # Create golden file if it doesn't exist (first run)
            golden_path.write_text(normalized, encoding="utf-8")
            pytest.skip(f"Created new golden file: {golden_path.name}")

        expected = golden_path.read_text(encoding="utf-8")
        # Normalize expected content as well for consistent comparison
        expected_normalized = normalize_paths(expected)

        if normalized != expected_normalized:
            diff = generate_diff(expected_normalized, normalized)
            pytest.fail(f"Golden file mismatch for {name}:\n\n{diff}\n\nRun with --update-golden to update the golden file.")


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
