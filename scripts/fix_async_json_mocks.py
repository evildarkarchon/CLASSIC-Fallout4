#!/usr/bin/env python3
"""Fix AsyncMock issues in test files by properly mocking async json() methods."""

import re
from pathlib import Path


def fix_json_mocks(file_path):
    """Fix json mock assignments to use create_async_json_mock helper."""
    with Path(file_path).open(encoding='utf-8') as f:
        content = f.read()

    # Replace simple MagicMock json assignments
    content = re.sub(
        r'mock_response\.json = MagicMock\(return_value=([^)]+)\)',
        r'mock_response.json = create_async_json_mock(\1)',
        content
    )

    # Replace responses[n].json assignments
    content = re.sub(
        r'responses\[(\d+)\]\.json = MagicMock\(return_value=([^)]+)\)',
        r'responses[\1].json = create_async_json_mock(\2)',
        content
    )

    # Handle side_effect with list
    if 'mock_response.json = MagicMock(side_effect=[stable_data, prerelease_data])' in content:
        replacement = """        # Configure responses with different data for each call
        call_count = [0]
        async def multi_response_json():
            result = [stable_data, prerelease_data][call_count[0]]
            call_count[0] += 1
            return result
        mock_response.json = MagicMock(side_effect=multi_response_json)"""
        content = content.replace(
            '        mock_response.json = MagicMock(side_effect=[stable_data, prerelease_data])',
            replacement
        )

    with Path(file_path).open('w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed {file_path}")

# Fix all three test files
test_files = [
    'tests/utils/test_update_unit.py',
    'tests/utils/test_update_network_unit.py',
    'tests/utils/test_update_network_comprehensive_unit.py'
]

for test_file in test_files:
    file_path = Path(test_file)
    if file_path.exists():
        fix_json_mocks(file_path)
    else:
        print(f"File not found: {test_file}")
