#!/usr/bin/env python3
"""
Fix shadowed fixture definitions in test files.

Removes local fixture definitions that shadow the standardized fixtures
from tests/fixtures/registry_fixtures.py
"""

import re
from pathlib import Path
from typing import Set


def find_shadowing_fixtures(content: str) -> Set[str]:
    """Find fixture definitions that shadow standardized fixtures."""
    standardized_fixtures = {
        'init_message_handler_fixture',
        'message_handler',
        'gui_message_handler',
        'ensure_message_handler_cleanup',
        'async_bridge',
        'ensure_async_bridge_cleanup',
    }

    # Pattern to find fixture definitions
    fixture_pattern = r'@pytest\.fixture[^\n]*\ndef\s+(\w+)\('

    shadowing = set()
    for match in re.finditer(fixture_pattern, content):
        fixture_name = match.group(1)
        if fixture_name in standardized_fixtures:
            shadowing.add(fixture_name)

    return shadowing


def remove_shadowing_fixtures(content: str, fixtures_to_remove: Set[str]) -> str:
    """Remove fixture definitions that shadow standardized ones."""
    if not fixtures_to_remove:
        return content

    lines = content.split('\n')
    result = []
    skip_until_next_def = False
    in_fixture_def = False
    current_fixture = None
    indent_level = 0

    for i, line in enumerate(lines):
        # Check if this is a fixture decorator
        if '@pytest.fixture' in line:
            # Check next lines to find the fixture name
            for j in range(i + 1, min(i + 5, len(lines))):
                if match := re.match(r'def\s+(\w+)\(', lines[j]):
                    fixture_name = match.group(1)
                    if fixture_name in fixtures_to_remove:
                        skip_until_next_def = True
                        current_fixture = fixture_name
                        # Find the indentation level of the def line
                        indent_level = len(lines[j]) - len(lines[j].lstrip())
                        print(f"  Removing shadowing fixture: {fixture_name}")
                    break

        # Skip lines that are part of the fixture to remove
        if skip_until_next_def:
            # Check if we've reached the next function/class definition at the same or lower indent level
            if line and not line[0].isspace():  # Top-level definition
                skip_until_next_def = False
                current_fixture = None
                result.append(line)
            elif line.strip().startswith(('def ', 'class ', '@')) and line[:indent_level].isspace() and line[indent_level] not in ' \t':
                # Next definition at same indent level
                skip_until_next_def = False
                current_fixture = None
                result.append(line)
            # else: skip the line (it's part of the fixture being removed)
        else:
            result.append(line)

    # Clean up excess blank lines
    cleaned = []
    blank_count = 0
    for line in result:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    return '\n'.join(cleaned)


def fix_file(file_path: Path) -> bool:
    """Fix a single test file."""
    content = file_path.read_text(encoding='utf-8')

    # Find shadowing fixtures
    shadowing = find_shadowing_fixtures(content)

    if not shadowing:
        return False

    print(f"\n{file_path}:")

    # Remove shadowing fixtures
    updated = remove_shadowing_fixtures(content, shadowing)

    # Write back
    file_path.write_text(updated, encoding='utf-8')

    return True


def main():
    """Main function to fix all test files."""
    test_dir = Path('tests')

    # Files that our migration script touched and might have shadowing issues
    files_to_check = [
        'tests/async_resources/test_pipeline_resources.py',
        'tests/gui/settings/test_integration_e2e.py',
        'tests/settings/test_async_yaml_core.py',
        'tests/scanning/test_scan_mods_archived.py',
        'tests/gui/test_tab_setup_mixin_integration.py',
        'tests/gui/test_results_viewer_mixin_integration.py',
    ]

    fixed_count = 0

    print("Fixing shadowed fixture definitions...")

    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                fixed_count += 1

    # Also check any other test files that might have the issue
    for test_file in test_dir.rglob('test_*.py'):
        if str(test_file) not in files_to_check:
            if fix_file(test_file):
                fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files with shadowing fixtures")

    if fixed_count > 0:
        print("\n📝 Next steps:")
        print("  1. Run tests to verify fixes: poetry run pytest tests/ -n 4")
        print("  2. Check for any remaining fixture issues")


if __name__ == '__main__':
    main()
