#!/usr/bin/env python3
"""
Migrate all asyncio.run() calls to use AsyncBridge.

AsyncBridge provides thread-safe async execution with a persistent event loop,
which is essential for the project's architecture and prevents test pollution.
"""

import re
from pathlib import Path
from typing import List, Tuple


def find_asyncio_run_calls(content: str) -> List[Tuple[int, str]]:
    """Find all asyncio.run() calls in the content."""
    lines = content.split('\n')
    calls = []

    for i, line in enumerate(lines):
        if 'asyncio.run(' in line:
            calls.append((i, line))

    return calls


def replace_asyncio_run(content: str) -> Tuple[str, int]:
    """Replace asyncio.run() calls with AsyncBridge."""
    lines = content.split('\n')
    result = []
    replacements = 0
    import_added = False

    # Check if AsyncBridge is already imported
    has_asyncbridge_import = any('AsyncBridge' in line for line in lines)

    # Find where to add import if needed
    import_insert_index = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            if line.startswith('import') or line.startswith('from'):
                import_insert_index = i + 1
            else:
                break

    for i, line in enumerate(lines):
        # Add AsyncBridge import after other imports if not present
        if not import_added and not has_asyncbridge_import and i == import_insert_index:
            if lines[i-1].strip():  # If previous line has content
                result.append("")  # Add blank line
            result.append("from ClassicLib.AsyncBridge import AsyncBridge")
            result.append("")
            import_added = True

        # Replace asyncio.run() calls
        if 'asyncio.run(' in line:
            # Extract the async function call
            match = re.search(r'asyncio\.run\((.*?)\)(?:\s*#.*)?$', line)
            if match:
                async_call = match.group(1)
                indent = len(line) - len(line.lstrip())

                # Check if this is an assignment
                if '=' in line.split('asyncio.run(')[0]:
                    # Extract the assignment part
                    assignment_part = line.split('asyncio.run(')[0]
                    # Create the replacement
                    if not has_asyncbridge_import and not import_added:
                        # Will need the import
                        new_line = f"{' ' * indent}bridge = AsyncBridge.get_instance()"
                        result.append(new_line)
                        new_line = f"{' ' * indent}{assignment_part.strip()}bridge.run_async({async_call})"
                    else:
                        # Check if bridge variable exists in scope
                        new_line = f"{' ' * indent}bridge = AsyncBridge.get_instance()"
                        result.append(new_line)
                        new_line = f"{' ' * indent}{assignment_part.strip()}bridge.run_async({async_call})"
                else:
                    # No assignment, just a call
                    new_line = f"{' ' * indent}bridge = AsyncBridge.get_instance()"
                    result.append(new_line)
                    new_line = f"{' ' * indent}bridge.run_async({async_call})"

                result.append(new_line)
                replacements += 1
                print(f"    Replaced: asyncio.run({async_call[:50]}...)")
            else:
                # Multi-line asyncio.run call - needs manual review
                result.append(line)
                print(f"    ⚠️  Multi-line asyncio.run() detected - needs manual review")
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


def main():
    """Main function to migrate all asyncio.run() calls."""
    print("=" * 80)
    print("AsyncBridge Migration Tool")
    print("=" * 80)
    print("\nThis tool will replace asyncio.run() with AsyncBridge.get_instance().run_async()")
    print("AsyncBridge provides thread-safe async execution with persistent event loops.\n")

    # Files to migrate
    production_files = [
        'ClassicLib/ScanLog/AsyncIntegration.py',
        'ClassicLib/ScanLog/AsyncFileIO.py',
        'ClassicLib/Interface/Workers.py',
    ]

    test_files = [
        'tests/core/test_crash_log_processing_integration.py',
        'tests/core/test_crash_log_processing_unit.py',
        'tests/performance/test_async_performance_error_handling.py',
        'tests/performance/test_async_performance_memory.py',
    ]

    print("STEP 1: Analyzing Production Code")
    print("-" * 40)
    for file_path in production_files:
        path = Path(file_path)
        if path.exists():
            analyze_usage(path)

    print("\n\nSTEP 2: Analyzing Test Code")
    print("-" * 40)
    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            analyze_usage(path)

    # Ask for confirmation
    print("\n" + "=" * 80)
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Perform migration
    print("\n\nSTEP 3: Migrating Production Code")
    print("-" * 40)
    prod_count = 0
    for file_path in production_files:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                prod_count += 1

    print(f"\n✅ Migrated {prod_count} production files")

    print("\n\nSTEP 4: Migrating Test Code")
    print("-" * 40)
    test_count = 0
    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                test_count += 1

    print(f"\n✅ Migrated {test_count} test files")

    # Final check for any remaining asyncio.run calls
    print("\n\nSTEP 5: Final Verification")
    print("-" * 40)

    remaining_prod = []
    remaining_test = []

    # Check production code
    for file in Path('ClassicLib').rglob('*.py'):
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            remaining_prod.append(file)

    # Check test code
    for file in Path('tests').rglob('*.py'):
        content = file.read_text(encoding='utf-8')
        if 'asyncio.run(' in content:
            remaining_test.append(file)

    if remaining_prod or remaining_test:
        print("⚠️  Warning: Some files still contain asyncio.run() calls:")
        for file in remaining_prod:
            print(f"  Production: {file}")
        for file in remaining_test:
            print(f"  Test: {file}")
        print("\nThese may need manual review.")
    else:
        print("✅ All asyncio.run() calls have been successfully migrated!")

    print("\n" + "=" * 80)
    print("Migration Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the changes using: git diff")
    print("2. Run tests to ensure everything works: poetry run pytest tests/")
    print("3. For tests, ensure they have the async_bridge fixture")
    print("\nRemember: AsyncBridge.get_instance().run_async() is thread-safe")
    print("and maintains a persistent event loop per thread.")


if __name__ == '__main__':
    main()
