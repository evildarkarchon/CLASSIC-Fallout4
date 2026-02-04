"""Copy Python-generated AUTOSCAN.md files as golden baseline for parity testing.

The Crash Logs/ directory contains Python-generated AUTOSCAN.md reports paired
with their source crash logs. These are the TRUE golden baseline for VAL-03
Python-Rust parity validation.

Usage:
    uv run python tests/golden/capture_report_golden.py

This script:
1. Scans Crash Logs/ for *-AUTOSCAN.md files
2. Copies them to tests/golden/captured/ with normalized naming
3. Creates a manifest mapping golden files to source logs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures.golden_fixtures import (
    GOLDEN_DIR,
    mask_dynamic_data,
    normalize_paths,
)

# Source directories
CRASH_LOGS_DIR = project_root / "Crash Logs"

# Number of golden files to capture (representative sample)
MAX_GOLDEN_FILES = 20


def get_autoscan_pairs() -> list[tuple[Path, Path]]:
    """Find all AUTOSCAN.md files and their source logs.

    Returns:
        List of (log_path, autoscan_path) tuples.
    """
    pairs = []
    for autoscan in sorted(CRASH_LOGS_DIR.glob("*-AUTOSCAN.md")):
        # Extract log name from autoscan name
        # crash-2023-12-13-09-37-03-AUTOSCAN.md -> crash-2023-12-13-09-37-03.log
        log_name = autoscan.stem.replace("-AUTOSCAN", "") + ".log"
        log_path = CRASH_LOGS_DIR / log_name

        if log_path.exists():
            pairs.append((log_path, autoscan))

    return pairs


def safe_filename(log_name: str) -> str:
    """Create safe filename from log name.

    Args:
        log_name: Original log filename.

    Returns:
        Safe filename with special chars removed and dashes converted.
    """
    stem = Path(log_name).stem
    # Replace dashes and spaces with underscores
    safe = stem.replace("-", "_").replace(" ", "_").replace("$", "")
    # Remove any double underscores
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")


def copy_golden_report(autoscan_path: Path, golden_name: str) -> Path:
    """Copy Python AUTOSCAN.md to golden directory with normalization.

    Args:
        autoscan_path: Path to Python-generated AUTOSCAN.md file.
        golden_name: Base name for golden file (without extension).

    Returns:
        Path to saved golden file.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    # Read Python-generated report
    content = autoscan_path.read_text(encoding="utf-8", errors="ignore")

    # Apply normalization per CONTEXT.md
    # - Timestamps: Mask with {{TIMESTAMP}} (mask_dynamic_data handles ONLY timestamps now)
    # - Paths: Normalize to forward slashes (normalize_paths is separate function)
    normalized = mask_dynamic_data(content)  # Masks timestamps ONLY
    normalized = normalize_paths(normalized)  # Normalizes path slashes

    # Save as golden file
    golden_path = GOLDEN_DIR / f"{golden_name}_report.golden.md"
    golden_path.write_text(normalized, encoding="utf-8")
    return golden_path


def main() -> int:
    """Copy Python AUTOSCAN.md files as golden baseline.

    Returns:
        0 on success, 1 on failure.
    """
    print(f"Source: {CRASH_LOGS_DIR}")
    print(f"Destination: {GOLDEN_DIR}")
    print()

    if not CRASH_LOGS_DIR.exists():
        print(f"ERROR: Crash Logs directory not found: {CRASH_LOGS_DIR}")
        return 1

    pairs = get_autoscan_pairs()
    print(f"Found {len(pairs)} log/AUTOSCAN pairs")

    if len(pairs) == 0:
        print("ERROR: No AUTOSCAN.md files found in Crash Logs/")
        return 1

    # Select subset for golden files (spread across date range)
    # Take every Nth file to get diverse samples
    step = max(1, len(pairs) // MAX_GOLDEN_FILES)
    selected = pairs[::step][:MAX_GOLDEN_FILES]

    print(f"Selecting {len(selected)} representative files")
    print()

    manifest: dict[str, dict[str, str]] = {}
    captured = 0

    for log_path, autoscan_path in selected:
        try:
            golden_name = safe_filename(log_path.name)
            golden_path = copy_golden_report(autoscan_path, golden_name)

            manifest[golden_name] = {
                "source_log": log_path.name,
                "autoscan": autoscan_path.name,
                "golden": golden_path.name,
            }

            print(f"  OK: {log_path.name}")
            captured += 1

        except Exception as e:
            print(f"  ERROR: {log_path.name} - {e}")

    # Save manifest for test parametrization
    manifest_path = GOLDEN_DIR / "report_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8"
    )

    print()
    print(f"Captured: {captured} golden report files")
    print(f"Manifest: {manifest_path}")

    if captured < 10:
        print(f"\nWARNING: Only captured {captured} files (recommend 10+)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
