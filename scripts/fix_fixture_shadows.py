#!/usr/bin/env python3
"""
Fix shadowed fixture definitions in test files.

Removes local fixture definitions that shadow the standardized fixtures
from tests/fixtures/registry_fixtures.py
"""

import re
from pathlib import Path


def find_shadowing_fixtures(content: str) -> set[str]:
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


def check_fixture_to_remove(lines: list[str], index: int, fixtures_to_remove: set[str]) -> tuple[bool, str | None, int]:
    """Check if current fixture should be removed.

    Returns:
        Tuple of (should_remove, fixture_name, indent_level)
    """
    if '@pytest.fixture' not in lines[index]:
        return False, None, 0

    # Check next lines to find the fixture name
    for j in range(index + 1, min(index + 5, len(lines))):
        if match := re.match(r'def\s+(\w+)\(', lines[j]):
            fixture_name = match.group(1)
            if fixture_name in fixtures_to_remove:
                indent_level = len(lines[j]) - len(lines[j].lstrip())
                print(f"  Removing shadowing fixture: {fixture_name}")
                return True, fixture_name, indent_level
            break

    return False, None, 0


def is_next_definition(line: str, indent_level: int) -> bool:
    """Check if line is the next function/class definition."""
    # Top-level definition
    if line and not line[0].isspace():
        return True

    # Definition at same indent level
    if line.strip().startswith(('def ', 'class ', '@')):
        if line[:indent_level].isspace() and indent_level < len(line):
            if line[indent_level] not in ' \t':
                return True

    return False


def clean_blank_lines(lines: list[str]) -> list[str]:
    """Clean up excess blank lines."""
    cleaned = []
    blank_count = 0

    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    return cleaned


def remove_shadowing_fixtures(content: str, fixtures_to_remove: set[str]) -> str:
    """Remove fixture definitions that shadow standardized ones."""
    if not fixtures_to_remove:
        return content

    lines = content.split('\n')
    result = []
    skip_state = {
        'active': False,
        'fixture': None,
        'indent': 0
    }

    for i, line in enumerate(lines):
        # Check if this is a fixture to remove
        should_remove, fixture_name, indent_level = check_fixture_to_remove(lines, i, fixtures_to_remove)

        if should_remove:
            skip_state['active'] = True
            skip_state['fixture'] = fixture_name
            skip_state['indent'] = indent_level
            continue

        # Handle skipping logic
        if skip_state['active']:
            if is_next_definition(line, skip_state['indent']):
                skip_state['active'] = False
                skip_state['fixture'] = None
                result.append(line)
            # else: skip the line (it's part of the fixture being removed)
        else:
            result.append(line)

    # Clean up excess blank lines
    cleaned = clean_blank_lines(result)
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
        print("  1. Run tests to verify fixes: uv run pytest tests/ -n 4")
        print("  2. Check for any remaining fixture issues")


if __name__ == '__main__':
    main()
