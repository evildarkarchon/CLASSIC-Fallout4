#!/usr/bin/env python3
"""
Analyze asyncio.run() usage in the codebase without making changes.
"""

import re
from pathlib import Path
from typing import List, Tuple


def analyze_file(file_path: Path) -> List[Tuple[int, str]]:
    """Analyze a file for asyncio.run() usage."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    calls = []

    for i, line in enumerate(lines):
        if 'asyncio.run(' in line:
            calls.append((i + 1, line.strip()))

    return calls


def main():
    """Main analysis function."""
    print("=" * 80)
    print("asyncio.run() Usage Analysis")
    print("=" * 80)

    production_files = []
    test_files = []

    # Find all Python files
    for file in Path('ClassicLib').rglob('*.py'):
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            production_files.append(file)

    for file in Path('tests').rglob('*.py'):
        if file.name == 'README_async.md':
            continue
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            test_files.append(file)

    print(f"\nFound asyncio.run() in {len(production_files)} production files")
    print(f"Found asyncio.run() in {len(test_files)} test files")

    print("\n" + "=" * 80)
    print("PRODUCTION CODE")
    print("=" * 80)

    for file_path in production_files:
        calls = analyze_file(file_path)
        if calls:
            print(f"\n{file_path}:")
            for line_num, line in calls:
                # Extract just the asyncio.run call
                match = re.search(r'(.*asyncio\.run\([^)]+\))', line)
                if match:
                    print(f"  Line {line_num}: {match.group(1)[:100]}")

    print("\n" + "=" * 80)
    print("TEST CODE")
    print("=" * 80)

    for file_path in test_files:
        calls = analyze_file(file_path)
        if calls:
            print(f"\n{file_path}:")
            for line_num, line in calls:
                # Extract just the asyncio.run call
                match = re.search(r'(.*asyncio\.run\([^)]+\))', line)
                if match:
                    print(f"  Line {line_num}: {match.group(1)[:100]}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nProduction files that need migration:")
    for f in production_files:
        print(f"  - {f}")

    print("\nTest files that need migration:")
    for f in test_files:
        print(f"  - {f}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("\nAll asyncio.run() calls should be replaced with AsyncBridge for:")
    print("1. Thread-safe async execution")
    print("2. Persistent event loop management")
    print("3. Better test isolation")
    print("4. Consistent async patterns across the codebase")
    print("\nUse: AsyncBridge.get_instance().run_async() instead of asyncio.run()")


if __name__ == '__main__':
    main()
