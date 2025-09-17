#!/usr/bin/env python3
"""
Add proper pytest markers to GUI test files based on their naming convention.
"""

import re
from pathlib import Path


def add_markers_to_file(filepath: Path) -> bool:
    """Add appropriate pytest markers to a test file."""
    content = filepath.read_text(encoding='utf-8')

    # Determine test type from filename
    filename = filepath.name
    if '_unit.py' in filename:
        test_type = 'unit'
    elif '_integration.py' in filename:
        test_type = 'integration'
    elif '_e2e.py' in filename:
        test_type = 'e2e'
    else:
        print(f"Unknown test type for {filename}")
        return False

    # Check if markers already exist
    if f'@pytest.mark.{test_type}' in content:
        print(f"Markers already exist in {filename}")
        return False

    # Find all class definitions
    class_pattern = re.compile(r'^class\s+Test\w+.*?:', re.MULTILINE)

    # Track if we made changes
    modified = False

    # Process each class
    for match in reversed(list(class_pattern.finditer(content))):
        class_line_start = match.start()

        # Check if this class already has markers (look back up to 100 chars)
        check_start = max(0, class_line_start - 100)
        check_text = content[check_start:class_line_start]

        if '@pytest.mark' in check_text:
            continue  # Skip if already has markers

        # Find the indentation of the class
        line_start = content.rfind('\n', 0, class_line_start) + 1
        indent = class_line_start - line_start
        indent_str = ' ' * indent

        # Build marker string
        markers = [f"{indent_str}@pytest.mark.{test_type}"]

        # Add @pytest.mark.gui for all GUI tests
        markers.append(f"{indent_str}@pytest.mark.gui")

        # Add markers before the class definition
        marker_str = '\n'.join(markers) + '\n'
        content = content[:class_line_start] + marker_str + content[class_line_start:]
        modified = True

    if modified:
        # Write the modified content
        filepath.write_text(content, encoding='utf-8')
        print(f"Added markers to {filename}")
        return True

    return False


def main():
    """Process all GUI test files."""
    gui_test_dir = Path('tests/gui')

    if not gui_test_dir.exists():
        print(f"Directory {gui_test_dir} does not exist!")
        return

    # Process all test files
    test_files = list(gui_test_dir.glob('test_*.py'))
    print(f"Found {len(test_files)} test files in {gui_test_dir}")

    modified_count = 0
    for test_file in sorted(test_files):
        if add_markers_to_file(test_file):
            modified_count += 1

    print(f"\nModified {modified_count} files")

    # Show summary
    if modified_count > 0:
        print("\nYou can now run tests with markers like:")
        print("  poetry run pytest -m 'gui and unit' -n auto")
        print("  poetry run pytest -m 'gui and integration' -v")
        print("  poetry run pytest -m 'gui and not slow' -n 4")


if __name__ == '__main__':
    main()
