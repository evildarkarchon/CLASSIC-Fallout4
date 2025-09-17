#!/usr/bin/env python3
"""Test script to verify the FileGeneration await fix."""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_file_generation():
    """Test that the async file generation methods work correctly."""
    try:
        from ClassicLib.FileGeneration import FileGenerator

        print("Testing FileGenerator.generate_local_yaml_async()...")

        # This should not raise the "Class 'None' does not define '__await__'" error
        await FileGenerator.generate_local_yaml_async()

        print("✓ generate_local_yaml_async() completed without errors")

        # Test the main async method as well
        print("Testing FileGenerator.generate_all_files_async()...")
        await FileGenerator.generate_all_files_async()

        print("✓ generate_all_files_async() completed without errors")

        return True

    except Exception as e:
        print(f"✗ Error occurred: {e}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_file_generation())
    if success:
        print("\n✓ All tests passed - the await fix is working correctly!")
        sys.exit(0)
    else:
        print("\n✗ Tests failed - the fix may not be complete")
        sys.exit(1)
