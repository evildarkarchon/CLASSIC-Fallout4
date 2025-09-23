#!/usr/bin/env python3
"""
Migrate all asyncio.run() calls to use AsyncBridge.

AsyncBridge provides thread-safe async execution with a persistent event loop,
which is essential for the project's architecture and prevents test pollution.
"""

import re
from pathlib import Path


def find_asyncio_run_calls(content: str) -> list[tuple[int, str]]:
    """Find all asyncio.run() calls in the content."""
    lines = content.split('\n')
    calls = []

    for i, line in enumerate(lines):
        if 'asyncio.run(' in line:
            calls.append((i, line))

    return calls


def _find_import_position(lines: list[str]) -> int:
    """Find the position where imports should be added."""
    import_insert_index = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            if line.startswith('import') or line.startswith('from'):
                import_insert_index = i + 1
            else:
                break
    return import_insert_index


def _add_import_if_needed(result: list[str], lines: list[str], i: int,
                         has_import: bool, import_added: bool, import_index: int) -> bool:
    """Add AsyncBridge import if needed."""
    if not import_added and not has_import and i == import_index:
        if lines[i-1].strip():  # If previous line has content
            result.append("")  # Add blank line
        result.append("from ClassicLib.AsyncBridge import AsyncBridge")
        result.append("")
        return True
    return False


def _create_bridge_replacement(line: str, async_call: str, indent: int) -> list[str]:
    """Create the bridge replacement lines."""
    replacement = []
    replacement.append(f"{' ' * indent}bridge = AsyncBridge.get_instance()")

    # Check if this is an assignment
    if '=' in line.split('asyncio.run(', maxsplit=1)[0]:
        assignment_part = line.split('asyncio.run(', maxsplit=1)[0]
        replacement.append(f"{' ' * indent}{assignment_part.strip()}bridge.run_async({async_call})")
    else:
        replacement.append(f"{' ' * indent}bridge.run_async({async_call})")

    return replacement


def replace_asyncio_run(content: str) -> tuple[str, int]:
    """Replace asyncio.run() calls with AsyncBridge."""
    lines = content.split('\n')
    result = []
    replacements = 0
    import_added = False

    # Check if AsyncBridge is already imported
    has_asyncbridge_import = any('AsyncBridge' in line for line in lines)

    # Find where to add import if needed
    import_insert_index = _find_import_position(lines)

    for i, line in enumerate(lines):
        # Add AsyncBridge import after other imports if not present
        import_added = _add_import_if_needed(
            result, lines, i, has_asyncbridge_import, import_added, import_insert_index
        ) or import_added

        # Replace asyncio.run() calls
        if 'asyncio.run(' in line:
            # Extract the async function call
            match = re.search(r'asyncio\.run\((.*?)\)(?:\s*#.*)?$', line)
            if match:
                async_call = match.group(1)
                indent = len(line) - len(line.lstrip())

                # Create replacement lines
                replacement_lines = _create_bridge_replacement(line, async_call, indent)
                result.extend(replacement_lines)

                replacements += 1
                print(f"    Replaced: asyncio.run({async_call[:50]}...)")
            else:
                # Multi-line asyncio.run call - needs manual review
                result.append(line)
                print("    ⚠️  Multi-line asyncio.run() detected - needs manual review")
        else:
            result.append(line)

    return '\n'.join(result), replacements


def fix_file(file_path: Path) -> bool:
    """Fix a single file by replacing asyncio.run with AsyncBridge."""
    content = file_path.read_text(encoding='utf-8')

    # Skip if no asyncio.run calls
    if 'asyncio.run(' not in content:
        return False

    print(f"\n{file_path}:")

    # Find all asyncio.run calls for reporting
    calls = find_asyncio_run_calls(content)
    if calls:
        print(f"  Found {len(calls)} asyncio.run() call(s)")

    # Replace asyncio.run with AsyncBridge
    updated_content, replacements = replace_asyncio_run(content)

    if replacements > 0:
        # Write back the updated content
        file_path.write_text(updated_content, encoding='utf-8')
        print(f"  ✅ Replaced {replacements} call(s)")
        return True

    return False


def analyze_usage(file_path: Path) -> None:
    """Analyze asyncio.run usage in a file without modifying it."""
    content = file_path.read_text(encoding='utf-8')

    if 'asyncio.run(' not in content:
        return

    calls = find_asyncio_run_calls(content)
    if calls:
        print(f"\n{file_path}:")
        print(f"  Found {len(calls)} asyncio.run() call(s):")
        for line_num, line in calls:
            print(f"    Line {line_num + 1}: {line.strip()[:80]}...")


def _process_files(files: list[str], label: str, action: str = "analyze") -> int:
    """Process a list of files for analysis or migration."""
    count = 0
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            if action == "analyze":
                analyze_usage(path)
            elif action == "migrate":
                if fix_file(path):
                    count += 1
    return count


def _find_remaining_calls(directory: str) -> list[Path]:
    """Find files that still contain asyncio.run() calls."""
    remaining = []
    for file in Path(directory).rglob('*.py'):
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            remaining.append(file)
    return remaining


def _print_header(title: str, separator_char: str = "=") -> None:
    """Print a formatted header."""
    separator = separator_char * 80
    print(f"\n{separator}")
    print(title)
    print(separator)


def _print_step(step_num: int, title: str) -> None:
    """Print a step header."""
    print(f"\n\nSTEP {step_num}: {title}")
    print("-" * 40)


def main():
    """Main function to migrate all asyncio.run() calls."""
    _print_header("AsyncBridge Migration Tool")
    print("\nThis tool will replace asyncio.run() with AsyncBridge.get_instance().run_async()")
    print("AsyncBridge provides thread-safe async execution with persistent event loops.\n")

    # Files to migrate
    file_groups = {
        "production": [
            'ClassicLib/ScanLog/AsyncIntegration.py',
            'ClassicLib/ScanLog/AsyncFileIO.py',
            'ClassicLib/Interface/Workers.py',
        ],
        "test": [
            'tests/core/test_crash_log_processing_integration.py',
            'tests/core/test_crash_log_processing_unit.py',
            'tests/performance/test_async_performance_error_handling.py',
            'tests/performance/test_async_performance_memory.py',
        ]
    }

    # Analysis phase
    _print_step(1, "Analyzing Production Code")
    _process_files(file_groups["production"], "production", action="analyze")

    _print_step(2, "Analyzing Test Code")
    _process_files(file_groups["test"], "test", action="analyze")

    # Ask for confirmation
    _print_header("", "=")
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Migration phase
    _print_step(3, "Migrating Production Code")
    prod_count = _process_files(file_groups["production"], "production", action="migrate")
    print(f"\n✅ Migrated {prod_count} production files")

    _print_step(4, "Migrating Test Code")
    test_count = _process_files(file_groups["test"], "test", action="migrate")
    print(f"\n✅ Migrated {test_count} test files")

    # Verification phase
    _print_step(5, "Final Verification")

    remaining_prod = _find_remaining_calls('ClassicLib')
    remaining_test = _find_remaining_calls('tests')

    if remaining_prod or remaining_test:
        print("⚠️  Warning: Some files still contain asyncio.run() calls:")
        for file in remaining_prod:
            print(f"  Production: {file}")
        for file in remaining_test:
            print(f"  Test: {file}")
        print("\nThese may need manual review.")
    else:
        print("✅ All asyncio.run() calls have been successfully migrated!")

    _print_header("Migration Complete!")
    print("\nNext steps:")
    print("1. Review the changes using: git diff")
    print("2. Run tests to ensure everything works: poetry run pytest tests/")
    print("3. For tests, ensure they have the async_bridge fixture")
    print("\nRemember: AsyncBridge.get_instance().run_async() is thread-safe")
    print("and maintains a persistent event loop per thread.")


if __name__ == '__main__':
    main()
