#!/usr/bin/env python3
"""
Fix @pytest.mark.usefixtures issues in test files.

Replaces usefixtures decorators with proper fixture parameters.
"""

import re
from pathlib import Path


def fix_usefixtures_decorators(content: str) -> str:
    """Replace @pytest.mark.usefixtures with fixture parameters."""
    lines = content.split('\n')
    result = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        # Check for usefixtures decorator
        if '@pytest.mark.usefixtures' in line and 'init_message_handler_fixture' in line:
            # Skip this line - we'll handle fixtures through parameters
            skip_next = False
            print("  Removed @pytest.mark.usefixtures decorator")
            continue

        result.append(line)

    return '\n'.join(result)


def ensure_message_handler_param(content: str) -> str:
    """Ensure test functions have message_handler parameter."""
    lines = content.split('\n')
    result = []

    for i, line in enumerate(lines):
        # Check if this is a test function
        if line.strip().startswith('def test_') or line.strip().startswith('async def test_'):
            match = re.search(r'def\s+(\w+)\((.*?)\):', line)
            if match:
                func_name = match.group(1)
                params = match.group(2)

                # Check if message_handler is already present
                if 'message_handler' not in params:
                    # Add message_handler parameter
                    if params.strip():
                        if not params.strip().endswith(','):
                            params = params.strip() + ', message_handler'
                        else:
                            params = params.strip() + 'message_handler'
                    else:
                        params = 'message_handler'

                    # Reconstruct the function signature
                    if 'async def' in line:
                        new_line = re.sub(r'async def \w+\([^)]*\)', f'async def {func_name}({params})', line)
                    else:
                        new_line = re.sub(r'def \w+\([^)]*\)', f'def {func_name}({params})', line)

                    result.append(new_line)
                    continue

        result.append(line)

    return '\n'.join(result)


def fix_file(file_path: Path) -> bool:
    """Fix a single test file."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding='utf-8')
    original = content

    print(f"\n{file_path}:")

    # Step 1: Remove @pytest.mark.usefixtures decorators
    content = fix_usefixtures_decorators(content)

    # Step 2: Ensure message_handler parameter is present
    content = ensure_message_handler_param(content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True

    print("  No changes needed")
    return False


def main():
    """Main function to fix usefixtures issues."""
    # Find all test files
    test_dir = Path('tests')
    fixed_count = 0

    print("Fixing @pytest.mark.usefixtures issues...")

    for test_file in test_dir.rglob('test_*.py'):
        content = test_file.read_text(encoding='utf-8')
        # Only process files with usefixtures
        if '@pytest.mark.usefixtures' in content and 'init_message_handler_fixture' in content:
            if fix_file(test_file):
                fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")

    if fixed_count > 0:
        print("\n📝 Next steps:")
        print("  1. Run tests: uv run pytest tests/ -n 4 -q")
        print("  2. All tests should now have proper fixture parameters")


if __name__ == '__main__':
    main()
