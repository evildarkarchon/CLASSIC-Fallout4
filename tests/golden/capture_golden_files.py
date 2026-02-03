"""Capture golden files for parity testing.

This script processes selected crash logs using the current Python implementation
and captures the output as golden files for comparison in Phase 10.

Usage:
    uv run python tests/golden/capture_golden_files.py

Per CONTEXT.md decisions:
- Capture intermediate outputs (parsed segments, analysis results)
- Mask timestamps and paths with placeholders before storage
- This satisfies VAL-01: "capture Python output for 10+ logs" in Phase 6
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.golden_fixtures import mask_dynamic_data, GOLDEN_DIR

# Sample logs directory
SAMPLE_LOGS_DIR = project_root / "sample_logs" / "FO4"

# Segment boundary names (matching parser output order)
SEGMENT_NAMES = [
    "compatibility",
    "system_specs",
    "call_stack",
    "modules",
    "xse_plugins",
    "plugins",
]

# Selected logs for golden file capture (from GOLDEN_LOG_SELECTION.md)
SELECTED_LOGS = [
    # Common cases (10)
    "crash-2022-06-05-12-52-17.log",
    "crash-2022-06-12-07-11-38.log",
    "crash-2022-06-24-07-23-35.log",
    "crash-2022-10-07-01-50-25 Lancer_Vance.log",
    "crash-2022-10-10-02-12-34 Bones.log",
    "crash-2022-06-17-07-04-05.log",
    "crash-2022-08-04-05-02-16.log",
    "crash-2022-09-22-04-55-18.log",
    "crash-2022-10-16-22-55-26 Arcanist.log",
    "crash-2022-06-09-04-44-04.log",
    # Edge cases (5)
    "crash-$123 1.log",
    "crash-0akensh1eld 1.log",
    "crash-0DB9300.log",
    "crash-12624.log",
    "crash-1D1777B.log",
    # Minimal content (1)
    "crash-2023-08-05-09-06-21.log",
]


def safe_filename(log_name: str) -> str:
    """Create safe filename from log name.

    Args:
        log_name: Original log filename.

    Returns:
        Safe filename with special chars removed and spaces replaced.
    """
    stem = Path(log_name).stem
    # Replace spaces and special chars
    safe = stem.replace(" ", "_").replace("$", "").replace("-", "_")
    # Remove any double underscores
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")


def capture_segments(log_path: Path) -> dict[str, Any]:
    """Parse crash log and return segments as dict.

    Uses the Rust parser via Python wrapper to extract segments.

    Args:
        log_path: Path to crash log file.

    Returns:
        Dict with parsed segments and metadata.
    """
    from ClassicLib.integration.factory import get_parser

    content = log_path.read_text(encoding="utf-8", errors="ignore")
    crash_data = content.splitlines()

    # Initialize parser
    parser = get_parser()

    # Parse with Fallout 4 settings
    game_version, crashgen_version, main_error, segments = parser.find_segments(
        crash_data,
        crashgen_name="Buffout 4",
        xse_acronym="F4SE",
        game_root_name="Fallout4",
    )

    # Build structured output
    result: dict[str, Any] = {
        "log_file": log_path.name,
        "parse_metadata": {
            "game_version": game_version,
            "crashgen_version": crashgen_version,
            "main_error": main_error,
        },
        "segments": {},
    }

    # Add each segment with line count and preview
    for i, (name, segment_lines) in enumerate(zip(SEGMENT_NAMES, segments, strict=False)):
        result["segments"][name] = {
            "line_count": len(segment_lines),
            "preview": segment_lines[:5] if segment_lines else [],
        }

    return result


def capture_analysis(log_path: Path) -> dict[str, Any]:
    """Capture analysis metadata for crash log.

    Args:
        log_path: Path to crash log file.

    Returns:
        Dict with file metadata and analysis summary.
    """
    content = log_path.read_text(encoding="utf-8", errors="ignore")

    return {
        "log_file": log_path.name,
        "file_size": log_path.stat().st_size,
        "line_count": content.count("\n") + 1,
        "char_count": len(content),
        "has_plugins_section": "PLUGINS:" in content,
        "has_f4se_section": "F4SE PLUGINS:" in content,
        "has_call_stack": "PROBABLE CALL STACK:" in content,
        "has_modules": "MODULES:" in content,
    }


def save_golden(data: dict[str, Any], name: str) -> Path:
    """Save golden file with dynamic data masked.

    Args:
        data: Data to save as JSON.
        name: Base filename (without extension).

    Returns:
        Path to saved golden file.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    formatted = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    masked = mask_dynamic_data(formatted)

    path = GOLDEN_DIR / f"{name}.json"
    path.write_text(masked, encoding="utf-8")
    return path


def main() -> int:
    """Capture golden files for all selected logs.

    Returns:
        0 if 10+ logs captured, 1 otherwise.
    """
    print(f"Capturing golden files to: {GOLDEN_DIR}")
    print(f"Sample logs from: {SAMPLE_LOGS_DIR}")
    print()

    captured = 0
    errors: list[tuple[str, str]] = []

    for log_name in SELECTED_LOGS:
        log_path = SAMPLE_LOGS_DIR / log_name

        if not log_path.exists():
            print(f"  SKIP: {log_name} (not found)")
            continue

        try:
            # Create safe filename from log name
            safe_name = safe_filename(log_name)

            # Capture segments
            segments = capture_segments(log_path)
            save_golden(segments, f"{safe_name}_segments")

            # Capture analysis
            analysis = capture_analysis(log_path)
            save_golden(analysis, f"{safe_name}_analysis")

            print(f"  OK: {log_name}")
            captured += 1

        except Exception as e:
            print(f"  ERROR: {log_name} - {e}")
            errors.append((log_name, str(e)))

    print()
    print(f"Captured: {captured} logs")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nError details:")
        for log_name, error in errors:
            print(f"  {log_name}: {error}")

    if captured < 10:
        print(f"\nWARNING: VAL-01 requires 10+ logs, only captured {captured}")
        return 1

    print(f"\nVAL-01 satisfied: {captured} logs captured (requirement: 10+)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
