#!/usr/bin/env python3
"""Clean up old Criterion baselines, keeping the 10 most recent.

Baselines are identified by naming pattern: baseline-YYYY-MM-DD-HHMMSS
Non-matching directories are left untouched.

Usage:
    python cleanup_baselines.py           # Dry run - show what would be deleted
    python cleanup_baselines.py --execute # Actually delete old baselines
    python cleanup_baselines.py --keep 5  # Keep only 5 most recent

Examples:
    # Preview cleanup (dry run)
    python cleanup_baselines.py

    # Keep only 5 baselines
    python cleanup_baselines.py --keep 5 --execute

    # Custom Criterion directory
    python cleanup_baselines.py --criterion-dir target/criterion --execute
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


# Pattern to match baseline directories: baseline-YYYY-MM-DD-HHMMSS
BASELINE_PATTERN = re.compile(r"^baseline-(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})$")


def parse_baseline_timestamp(name: str) -> datetime | None:
    """Parse timestamp from baseline directory name.

    Args:
        name: Directory name to parse.

    Returns:
        Datetime object if valid baseline name, None otherwise.
    """
    match = BASELINE_PATTERN.match(name)
    if not match:
        return None

    try:
        year, month, day, hour, minute, second = map(int, match.groups())
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        # Invalid date values (e.g., month 13)
        return None


def find_baselines(criterion_dir: Path) -> list[tuple[datetime, Path]]:
    """Find all baseline directories and their timestamps.

    Args:
        criterion_dir: Path to Criterion results directory.

    Returns:
        List of (timestamp, path) tuples, sorted by timestamp (oldest first).
    """
    baselines: list[tuple[datetime, Path]] = []

    if not criterion_dir.exists():
        return baselines

    for entry in criterion_dir.iterdir():
        if not entry.is_dir():
            continue

        timestamp = parse_baseline_timestamp(entry.name)
        if timestamp:
            baselines.append((timestamp, entry))

    # Sort by timestamp (oldest first)
    baselines.sort(key=lambda x: x[0])
    return baselines


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted size string.
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_dir_size(path: Path) -> int:
    """Calculate total size of a directory.

    Args:
        path: Directory path.

    Returns:
        Total size in bytes.
    """
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def cleanup_baselines(
    criterion_dir: Path,
    keep: int,
    execute: bool,
) -> tuple[list[Path], list[Path]]:
    """Clean up old baselines, keeping the most recent ones.

    Args:
        criterion_dir: Path to Criterion results directory.
        keep: Number of baselines to keep.
        execute: If True, actually delete; if False, dry run only.

    Returns:
        Tuple of (kept_paths, deleted_paths).
    """
    baselines = find_baselines(criterion_dir)

    if not baselines:
        return [], []

    # Split into keep and delete lists
    # Keep the N most recent (baselines are sorted oldest first)
    num_to_delete = max(0, len(baselines) - keep)
    to_delete = baselines[:num_to_delete]
    to_keep = baselines[num_to_delete:]

    deleted_paths: list[Path] = []
    kept_paths: list[Path] = [path for _, path in to_keep]

    for timestamp, path in to_delete:
        if execute:
            try:
                shutil.rmtree(path)
                deleted_paths.append(path)
            except (OSError, PermissionError) as e:
                print(f"Error: Failed to delete {path}: {e}", file=sys.stderr)
        else:
            deleted_paths.append(path)

    return kept_paths, deleted_paths


def main() -> int:
    """Main entry point for baseline cleanup.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    parser = argparse.ArgumentParser(
        description="Clean up old Criterion baselines, keeping the most recent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Baselines are identified by naming pattern: baseline-YYYY-MM-DD-HHMMSS
Non-matching directories (like 'base' or custom names) are left untouched.

Examples:
    python cleanup_baselines.py                    # Dry run
    python cleanup_baselines.py --execute          # Actually delete
    python cleanup_baselines.py --keep 5 --execute # Keep only 5
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete old baselines (default: dry run)",
    )
    parser.add_argument(
        "--keep",
        "-k",
        type=int,
        default=10,
        help="Number of baselines to keep (default: 10)",
    )
    parser.add_argument(
        "--criterion-dir",
        type=Path,
        default=Path("rust/target/criterion"),
        help="Path to Criterion results directory (default: rust/target/criterion)",
    )

    args = parser.parse_args()

    if args.keep < 0:
        print("Error: --keep must be non-negative", file=sys.stderr)
        return 1

    criterion_dir = args.criterion_dir.resolve()

    if not criterion_dir.exists():
        print(f"Criterion directory not found: {criterion_dir}")
        print("No baselines to clean up.")
        return 0

    # Find all baselines
    baselines = find_baselines(criterion_dir)

    if not baselines:
        print("No baselines found matching pattern: baseline-YYYY-MM-DD-HHMMSS")
        return 0

    print(f"Found {len(baselines)} baseline(s) in {criterion_dir}")
    print(f"Keeping the {args.keep} most recent\n")

    # Perform cleanup
    kept_paths, deleted_paths = cleanup_baselines(
        criterion_dir,
        args.keep,
        args.execute,
    )

    # Display results
    if kept_paths:
        print("Baselines to KEEP:")
        for path in kept_paths:
            size = get_dir_size(path)
            timestamp = parse_baseline_timestamp(path.name)
            ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "unknown"
            print(f"  [KEEP]   {path.name}  ({ts_str}, {format_size(size)})")
        print()

    if deleted_paths:
        action = "DELETED" if args.execute else "WOULD DELETE"
        print(f"Baselines to DELETE:")
        total_size = 0
        for path in deleted_paths:
            if not args.execute:
                # In dry run, directory still exists
                size = get_dir_size(path)
            else:
                # After execution, directory is gone
                size = 0
            total_size += size
            timestamp = parse_baseline_timestamp(path.name)
            ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "unknown"
            print(f"  [{action}] {path.name}  ({ts_str}, {format_size(size)})")

        print()
        if args.execute:
            print(f"Deleted {len(deleted_paths)} baseline(s)")
        else:
            print(f"Would delete {len(deleted_paths)} baseline(s) ({format_size(total_size)} total)")
            print("\nRun with --execute to actually delete these baselines.")
    else:
        print("No baselines need to be deleted.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
