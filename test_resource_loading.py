#!/usr/bin/env python
"""
Test script for verifying resource loading in both frozen and development modes.

This script tests that the ResourceLoader correctly finds and loads data files
whether running as a PyInstaller frozen executable or from source code.
"""

import sys
from pathlib import Path

# Add the project root to sys.path for development mode testing
project_root = Path(__file__).parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from ClassicLib.ResourceLoader import ResourceLoader, get_resource_path, is_frozen
from ClassicLib import GlobalRegistry


def test_resource_loading():
    """Test that resource loading works correctly."""
    print("=" * 60)
    print("CLASSIC Resource Loading Test")
    print("=" * 60)

    # Check if running as frozen executable
    frozen_state = is_frozen()
    print(f"\n✓ Execution Mode: {'FROZEN (PyInstaller)' if frozen_state else 'DEVELOPMENT (Source)'}")

    if frozen_state:
        print(f"  Bundle Directory: {sys._MEIPASS}")
    else:
        print(f"  Working Directory: {Path.cwd()}")

    # Test getting the data directory
    print("\n✓ Testing ResourceLoader.get_data_directory()...")
    try:
        data_dir = ResourceLoader.get_data_directory()
        print(f"  Data Directory: {data_dir}")
        print(f"  Exists: {data_dir.exists()}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test essential files
    print("\n✓ Testing Essential Files...")
    essential_files = [
        "CLASSIC Settings.yaml",
        "databases/CLASSIC Main.yaml",
        "databases/CLASSIC Fallout4.yaml",
        "databases/Fallout4 FormIDs Main.db",
        "graphics/CLASSIC.ico",
    ]

    all_found = True
    for file_path in essential_files:
        full_path = get_resource_path(file_path)
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        print(f"     Path: {full_path}")
        if exists:
            size = full_path.stat().st_size
            print(f"     Size: {size:,} bytes")
        else:
            all_found = False

    # Test ensuring data files exist
    print("\n✓ Testing ResourceLoader.ensure_data_files_exist()...")
    try:
        result_dir = ResourceLoader.ensure_data_files_exist()
        print(f"  Result Directory: {result_dir}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

    # Test cached path functions (won't find anything unless previously cached)
    print("\n✓ Testing Cached Path Functions...")
    game_name = "Fallout4"
    # GlobalRegistry doesn't have set_game, it's set through other means

    cached_game_path = ResourceLoader.get_cached_game_path(game_name)
    if cached_game_path:
        print(f"  Cached Game Path: {cached_game_path}")
    else:
        print(f"  No cached game path found (expected on first run)")

    cached_docs_path = ResourceLoader.get_cached_docs_path(game_name)
    if cached_docs_path:
        print(f"  Cached Docs Path: {cached_docs_path}")
    else:
        print(f"  No cached docs path found (expected on first run)")

    # Summary
    print("\n" + "=" * 60)
    if all_found:
        print("✓ All essential files found successfully!")
        print("  The resource loading system is working correctly.")
    else:
        print("✗ Some essential files were not found.")
        print("  This may indicate an issue with the PyInstaller bundling.")

    print("\nResource loading test completed.")
    print("=" * 60)

    return all_found


if __name__ == "__main__":
    success = test_resource_loading()

    # Keep console open if running as frozen executable
    if is_frozen():
        input("\nPress Enter to exit...")

    sys.exit(0 if success else 1)
