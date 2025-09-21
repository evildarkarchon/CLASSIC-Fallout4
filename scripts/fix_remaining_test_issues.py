#!/usr/bin/env python3
"""
Fix remaining test issues after migration.

1. Add async_bridge fixture to tests that need it
2. Fix QApplication issues in GUI tests
3. Clean up any remaining shadowing fixtures
"""

import re
from pathlib import Path
from typing import Set, List, Tuple


def needs_async_bridge(content: str) -> bool:
    """Check if a test file needs async_bridge fixture."""
    # Check for YamlSettingsCache or yaml_cache usage
    if any(pattern in content for pattern in [
        'YamlSettingsCache',
        'yaml_cache',
        'yaml_settings',
        'classic_settings',
        'AsyncBridge',
    ]):
        return True
    return False


def add_async_bridge_fixture(content: str) -> str:
    """Add async_bridge fixture to test functions that need it."""
    lines = content.split('\n')
    result = []

    for i, line in enumerate(lines):
        # Check if this is a test function that needs async_bridge
        if line.strip().startswith('def test_') or line.strip().startswith('async def test_'):
            # Extract function signature
            match = re.search(r'def\s+(\w+)\((.*?)\):', line)
            if match:
                func_name = match.group(1)
                params = match.group(2)

                # Check if the function already has async_bridge
                if 'async_bridge' not in params:
                    # Check if this test uses YAML operations (look ahead in the function)
                    func_end = i + 1
                    while func_end < len(lines) and (lines[func_end].startswith(' ') or not lines[func_end].strip()):
                        func_end += 1

                    func_body = '\n'.join(lines[i:func_end])

                    if any(pattern in func_body for pattern in [
                        'YamlSettingsCache',
                        'yaml_cache',
                        'yaml_settings(',
                        'classic_settings(',
                        'AsyncBridge',
                        'bridge.run_async',
                    ]):
                        # Add async_bridge fixture
                        if params.strip():
                            # Add to existing parameters
                            if not params.strip().endswith(','):
                                params += ', async_bridge'
                            else:
                                params += 'async_bridge'
                        else:
                            params = 'async_bridge'

                        # Reconstruct the function signature
                        if 'async def' in line:
                            new_line = line.replace(f'async def {func_name}(', f'async def {func_name}({params}')
                        else:
                            new_line = line.replace(f'def {func_name}(', f'def {func_name}({params}')

                        # Fix the closing parenthesis
                        new_line = re.sub(r'\([^)]*\)', f'({params})', new_line)

                        print(f"  Added async_bridge to: {func_name}")
                        result.append(new_line)
                        continue

        result.append(line)

    return '\n'.join(result)


def fix_qapplication_cleanup(content: str) -> str:
    """Add proper QApplication cleanup in GUI tests."""
    if 'QApplication' not in content:
        return content

    # Check if cleanup is already present
    if 'QApplication.instance()' in content and 'quit()' in content:
        return content

    lines = content.split('\n')
    result = []

    # Add cleanup fixture if not present
    has_cleanup = False
    for line in lines:
        if 'ensure_qt_cleanup' in line or 'QApplication.quit()' in line:
            has_cleanup = True
            break

    if not has_cleanup:
        # Add after imports
        import_index = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#') and not line.startswith('import') and not line.startswith('from'):
                import_index = i
                break

        # Insert cleanup fixture
        lines.insert(import_index, """
@pytest.fixture(autouse=True)
def ensure_qt_cleanup():
    \"\"\"Ensure QApplication is properly cleaned up after each test.\"\"\"
    yield
    from PySide6.QtWidgets import QApplication
    if app := QApplication.instance():
        app.quit()
        app.deleteLater()
""")
        print("  Added QApplication cleanup fixture")

    return '\n'.join(lines)


def _find_fixture_end(lines: list[str], start_index: int, indent: int) -> int:
    """Find the end index of a fixture function."""
    end_j = start_index + 1
    while end_j < len(lines):
        check_line = lines[end_j]
        if check_line and not check_line[0].isspace():
            break
        if check_line.strip() and not check_line[:indent].isspace():
            break
        end_j += 1
    return end_j


def _should_skip_fixture(lines: list[str], i: int, standardized: set[str]) -> int:
    """Check if a fixture should be skipped and return lines to skip."""
    if '@pytest.fixture' not in lines[i]:
        return 0

    # Look for the function definition
    for j in range(1, min(5, len(lines) - i)):
        next_line = lines[i + j]
        if match := re.match(r'def\s+(\w+)\(', next_line):
            fixture_name = match.group(1)
            if fixture_name in standardized:
                # Find end of fixture function
                indent = len(next_line) - len(next_line.lstrip())
                end_j = _find_fixture_end(lines, j, indent)
                print(f"  Removed shadowing fixture: {fixture_name}")
                return end_j - 1
    return -1  # Signal to keep the line


def _clean_blank_lines(lines: list[str]) -> list[str]:
    """Clean up excessive blank lines."""
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


def remove_all_shadowing_fixtures(content: str) -> str:
    """Remove ALL shadowing fixture definitions."""
    standardized = {
        'init_message_handler_fixture',
        'message_handler',
        'gui_message_handler',
        'ensure_message_handler_cleanup',
        'async_bridge',
        'ensure_async_bridge_cleanup',
    }

    lines = content.split('\n')
    result = []
    skip_lines = 0

    for i, line in enumerate(lines):
        if skip_lines > 0:
            skip_lines -= 1
            continue

        skip_count = _should_skip_fixture(lines, i, standardized)
        if skip_count > 0:
            skip_lines = skip_count
        elif skip_count == -1:
            result.append(line)
        else:
            result.append(line)

    # Clean up extra blank lines
    cleaned = _clean_blank_lines(result)
    return '\n'.join(cleaned)


def fix_file(file_path: Path) -> bool:
    """Fix all issues in a single file."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding='utf-8')
    original = content

    print(f"\n{file_path}:")

    # Step 1: Remove all shadowing fixtures
    content = remove_all_shadowing_fixtures(content)

    # Step 2: Add async_bridge fixture where needed
    if needs_async_bridge(content):
        content = add_async_bridge_fixture(content)

    # Step 3: Fix QApplication cleanup in GUI tests
    if 'gui' in str(file_path) and 'QApplication' in content:
        content = fix_qapplication_cleanup(content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True

    print("  No changes needed")
    return False


def main():
    """Main function to fix all remaining test issues."""
    # Files that need fixes based on test errors
    problem_files = [
        'tests/settings/test_async_yaml_core.py',
        'tests/settings/test_yaml_sync_wrapper_unit.py',
        'tests/settings/test_yaml_sync_wrapper_integration.py',
        'tests/scanning/test_scan_mods_archived.py',
        'tests/scanning/test_scan_mods_unpacked.py',
        'tests/gui/test_tab_setup_mixin_integration.py',
        'tests/gui/test_results_viewer_mixin_integration.py',
        'tests/gui/settings/test_integration_e2e.py',
        'tests/tui/test_performance.py',
        'tests/tui/test_message_handler.py',
    ]

    fixed_count = 0

    print("Fixing remaining test issues...")

    for file_path in problem_files:
        path = Path(file_path)
        if fix_file(path):
            fixed_count += 1

    # Also check for any other test files with issues
    test_dir = Path('tests')
    for test_file in test_dir.rglob('test_*.py'):
        if str(test_file) not in problem_files:
            content = test_file.read_text(encoding='utf-8')
            # Quick check if file needs attention
            if '@pytest.fixture' in content and any(
                fixture in content for fixture in [
                    'init_message_handler_fixture',
                    'message_handler',
                    'gui_message_handler',
                ]
            ):
                if fix_file(test_file):
                    fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")

    if fixed_count > 0:
        print("\n📝 Next steps:")
        print("  1. Run tests: poetry run pytest tests/ -n 4 -q")
        print("  2. Check for any remaining errors")
        print("  3. If GUI tests still fail, may need to run them separately without parallelization")


if __name__ == '__main__':
    main()
