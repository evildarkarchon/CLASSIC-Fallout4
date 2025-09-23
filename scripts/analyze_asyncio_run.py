#!/usr/bin/env python3
"""
Analyze asyncio.run() usage in the codebase without making changes.
"""

import re
from pathlib import Path


def analyze_file(file_path: Path) -> list[tuple[int, str]]:
    """Analyze a file for asyncio.run() usage."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    calls = []

    for i, line in enumerate(lines):
        if 'asyncio.run(' in line:
            calls.append((i + 1, line.strip()))

    return calls


def scan_directory(directory: str, exclude_files: list[str] = None) -> list[Path]:
    """Scan directory for files containing asyncio.run()."""
    exclude_files = exclude_files or []
    matching_files = []

    for file in Path(directory).rglob('*.py'):
        if file.name in exclude_files:
            continue
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            matching_files.append(file)

    return matching_files


def print_file_analysis(files: list[Path], section_name: str) -> None:
    """Print analysis for a group of files."""
    print("\n" + "=" * 80)
    print(section_name)
    print("=" * 80)

    for file_path in files:
        calls = analyze_file(file_path)
        if not calls:
            continue

        print(f"\n{file_path}:")
        for line_num, line in calls:
            # Extract just the asyncio.run call
            match = re.search(r'(.*asyncio\.run\([^)]+\))', line)
            if match:
                print(f"  Line {line_num}: {match.group(1)[:100]}")


def print_summary(file_groups: dict) -> None:
    """Print summary of files needing migration."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for category, files in file_groups.items():
        print(f"\n{category} files that need migration:")
        for f in files:
            print(f"  - {f}")


def print_recommendations() -> None:
    """Print migration recommendations."""
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("\nAll asyncio.run() calls should be replaced with AsyncBridge for:")
    print("1. Thread-safe async execution")
    print("2. Persistent event loop management")
    print("3. Better test isolation")
    print("4. Consistent async patterns across the codebase")
    print("\nUse: AsyncBridge.get_instance().run_async() instead of asyncio.run()")


def main():
    """Main analysis function."""
    print("=" * 80)
    print("asyncio.run() Usage Analysis")
    print("=" * 80)

    # Scan directories for asyncio.run() usage
    file_groups = {
        "Production": scan_directory('ClassicLib'),
        "Test": scan_directory('tests', exclude_files=['README_async.md'])
    }

    # Print counts
    for category, files in file_groups.items():
        print(f"\nFound asyncio.run() in {len(files)} {category.lower()} files")

    # Analyze each group
    for category, files in file_groups.items():
        print_file_analysis(files, f"{category.upper()} CODE")

    # Print summary and recommendations
    print_summary(file_groups)
    print_recommendations()


if __name__ == '__main__':
    main()
