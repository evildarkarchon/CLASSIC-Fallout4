"""VAL-02: Rust scanning output matches Python golden files.

Tests that Rust segment parsing produces character-for-character identical
output (after timestamp masking and path normalization) compared to golden
files captured from Python implementation in Phase 6.

Per CONTEXT.md decisions:
- Timestamps: Masked with {{TIMESTAMP}} placeholder
- Paths: Normalized to forward slashes (not masked)
- Whitespace: Strict matching
- Ordering: Exact order required
- Comparison: Whole-file (not section-by-section)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.fixtures.golden_fixtures import (
    GOLDEN_DIR,
    generate_diff,
    mask_dynamic_data,
    normalize_paths,
)

if TYPE_CHECKING:
    from ClassicLib.integration.types import LogParserProtocol


def discover_golden_log_stems() -> list[str]:
    """Discover available golden file stems from captured directory.

    Returns list of stems (without _segments.json or _analysis.json suffix).
    This ensures test list matches actual files, avoiding hardcoded list drift.

    Returns:
        Sorted list of golden file stems.
    """
    stems = set()
    for f in GOLDEN_DIR.glob("*_segments.json"):
        stem = f.stem.replace("_segments", "")
        stems.add(stem)
    return sorted(stems)


# List of golden file stems (discovered dynamically)
GOLDEN_LOG_STEMS = discover_golden_log_stems()


def normalize_for_comparison(text: str) -> str:
    """Apply all normalization for parity comparison.

    Args:
        text: Raw text to normalize.

    Returns:
        Normalized text with timestamps masked and paths normalized.
    """
    result = mask_dynamic_data(text)
    result = normalize_paths(result)
    return result


def golden_stem_to_log_name(stem: str) -> str:
    """Convert golden file stem back to original log filename.

    The capture script uses safe_filename() which:
    - Replaces spaces with underscores
    - Removes $ character
    - Replaces dashes with underscores

    This function reverses that transformation using a mapping table
    for known special cases.

    Args:
        stem: Golden file stem (e.g., "crash_123_1").

    Returns:
        Original log filename (e.g., "crash-$123 1.log").
    """
    # Map known special cases that can't be reversed algorithmically
    special_cases = {
        "crash_123_1": "crash-$123 1.log",
        "crash_0akensh1eld_1": "crash-0akensh1eld 1.log",
        "crash_0DB9300": "crash-0DB9300.log",
        "crash_12624": "crash-12624.log",
        "crash_1D1777B": "crash-1D1777B.log",
        "crash_2022_10_07_01_50_25_Lancer_Vance": "crash-2022-10-07-01-50-25 Lancer_Vance.log",
        "crash_2022_10_10_02_12_34_Bones": "crash-2022-10-10-02-12-34 Bones.log",
        "crash_2022_10_16_22_55_26_Arcanist": "crash-2022-10-16-22-55-26 Arcanist.log",
    }

    if stem in special_cases:
        return special_cases[stem]

    # Standard case: replace underscores with dashes and add .log
    return stem.replace("_", "-") + ".log"


@pytest.mark.parity
@pytest.mark.integration
class TestScanningParity:
    """VAL-02: Rust segment parsing matches Python golden files."""

    @pytest.mark.parametrize("log_stem", GOLDEN_LOG_STEMS)
    def test_segments_parity(self, log_stem: str, rust_parser: LogParserProtocol, sample_logs_dir: Path) -> None:
        """Rust segment parsing matches golden segments.

        Args:
            log_stem: Golden file stem identifying the test case.
            rust_parser: Rust parser fixture from conftest.
            sample_logs_dir: Path to sample logs directory.
        """
        # Load golden segments
        golden_path = GOLDEN_DIR / f"{log_stem}_segments.json"
        if not golden_path.exists():
            pytest.skip(f"Golden file not found: {golden_path}")

        # Find corresponding log file
        log_name = golden_stem_to_log_name(log_stem)
        log_path = sample_logs_dir / log_name

        if not log_path.exists():
            pytest.skip(f"Sample log not found: {log_path}")

        # Parse with Rust
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        crash_data = content.splitlines()

        game_version, crashgen_version, main_error, segments = rust_parser.find_segments(
            crash_data,
            crashgen_name="Buffout 4",
            xse_acronym="F4SE",
            game_root_name="Fallout4",
        )

        # Build result in same format as capture script
        segment_names = [
            "compatibility",
            "system_specs",
            "call_stack",
            "modules",
            "xse_plugins",
            "plugins",
        ]

        actual_data = {
            "log_file": log_name,
            "parse_metadata": {
                "game_version": game_version,
                "crashgen_version": crashgen_version,
                "main_error": main_error,
            },
            "segments": {},
        }

        for name, segment_lines in zip(segment_names, segments, strict=False):
            actual_data["segments"][name] = {
                "line_count": len(segment_lines),
                "preview": segment_lines[:5] if segment_lines else [],
            }

        # Normalize both for comparison
        actual_json = json.dumps(actual_data, indent=2, sort_keys=True, ensure_ascii=False)
        expected_json = golden_path.read_text(encoding="utf-8")

        actual_normalized = normalize_for_comparison(actual_json)
        expected_normalized = normalize_for_comparison(expected_json)

        if actual_normalized != expected_normalized:
            diff = generate_diff(expected_normalized, actual_normalized)
            pytest.fail(f"Segment parity mismatch for {log_stem}:\n\n{diff}\n\nGolden files are authoritative - Rust must match them.")

    @pytest.mark.parametrize("log_stem", GOLDEN_LOG_STEMS)
    def test_analysis_metadata_parity(self, log_stem: str, sample_logs_dir: Path) -> None:
        """Analysis metadata matches golden analysis.

        Args:
            log_stem: Golden file stem identifying the test case.
            sample_logs_dir: Path to sample logs directory.
        """
        # Load golden analysis
        golden_path = GOLDEN_DIR / f"{log_stem}_analysis.json"
        if not golden_path.exists():
            pytest.skip(f"Golden file not found: {golden_path}")

        # Find corresponding log file
        log_name = golden_stem_to_log_name(log_stem)
        log_path = sample_logs_dir / log_name

        if not log_path.exists():
            pytest.skip(f"Sample log not found: {log_path}")

        # Compute actual analysis (same as capture script)
        content = log_path.read_text(encoding="utf-8", errors="ignore")

        actual_data = {
            "log_file": log_name,
            "file_size": log_path.stat().st_size,
            "line_count": content.count("\n") + 1,
            "char_count": len(content),
            "has_plugins_section": "PLUGINS:" in content,
            "has_f4se_section": "F4SE PLUGINS:" in content,
            "has_call_stack": "PROBABLE CALL STACK:" in content,
            "has_modules": "MODULES:" in content,
        }

        # Normalize both for comparison
        actual_json = json.dumps(actual_data, indent=2, sort_keys=True, ensure_ascii=False)
        expected_json = golden_path.read_text(encoding="utf-8")

        actual_normalized = normalize_for_comparison(actual_json)
        expected_normalized = normalize_for_comparison(expected_json)

        if actual_normalized != expected_normalized:
            diff = generate_diff(expected_normalized, actual_normalized)
            pytest.fail(f"Analysis metadata parity mismatch for {log_stem}:\n\n{diff}")
