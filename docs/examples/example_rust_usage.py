#!/usr/bin/env python
"""Example of using Rust extensions in CLASSIC-Fallout4.

This demonstrates how the ResourceLoader and rust_loader work together
to provide transparent access to Rust-accelerated functionality.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ClassicLib.ResourceLoader import ResourceLoader  # noqa: E402
from ClassicLib.rust_loader import is_rust_available  # noqa: E402


def main() -> None:
    """Demonstrate Rust extension loading and usage."""
    print("=" * 60)
    print("CLASSIC-Fallout4 Rust Extension Demo")
    print("=" * 60)
    print()

    # Load Rust extensions through ResourceLoader
    print("Loading Rust extensions via ResourceLoader...")
    rust_loaded = ResourceLoader.load_rust_extension()

    if rust_loaded:
        print("✓ Rust extensions loaded successfully!")
    else:
        print("✗ Rust extensions not available - using pure Python fallback")

    print()

    # Get detailed information about Rust loading
    rust_info = ResourceLoader.get_rust_extension_info()
    print("Rust Extension Information:")
    print(f"  Loaded: {rust_info.get('loaded', False)}")
    print(f"  In PyInstaller: {rust_info.get('in_pyinstaller', False)}")

    if rust_info.get("path"):
        print(f"  Extension Path: {rust_info['path']}")

    if rust_info.get("search_paths"):
        print("  Search Paths Checked:")
        for path in rust_info["search_paths"]:
            print(f"    - {path}")

    print()

    # Try to use Rust-accelerated components
    if is_rust_available():
        try:
            # Import Rust-accelerated modules
            from ClassicLib.integration.factory import get_rust_component_status

            components = get_rust_component_status().get("available", {})

            print("Available Rust-Accelerated Components:")
            if components.get("file_io_core"):
                print("  ✓ FileIOCore - High-speed file I/O operations")
            if components.get("formid_analyzer"):
                print("  ✓ FormIDAnalyzer - Fast FormID analysis")
            if components.get("parser"):
                print("  ✓ LogParser - Optimized crash log parsing")
            print()

            # Example: Using the Rust-accelerated FileIOCore
            print("Example: Using Rust FileIOCore for faster file operations")

            # This would use the Rust implementation if available,
            # or fall back to Python if not
            from ClassicLib.integration.factory import get_file_io

            io_core = get_file_io()
            print(f"  FileIOCore initialized: {io_core.__class__.__module__}")

        except ImportError as e:
            print(f"Could not import Rust components: {e}")
    else:
        print("Rust extensions not available - all operations will use Python implementation")
        print("This is perfectly fine - the application works without Rust!")
        print()
        print("To enable Rust acceleration:")
        print("  1. Build: maturin build --release")
        print("  2. Extract the .pyd from the wheel to rust_extensions/")
        print("  3. Run the application again")

    print()
    print("=" * 60)
    print("Demo complete!")


if __name__ == "__main__":
    main()
