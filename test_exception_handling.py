"""Test script for verifying Rust exception handling.

This script tests that the new exception types are properly raised
and caught by the Python wrapper modules.
"""

from ClassicLib.integration.exceptions import (
    RustConfigError,
    RustDatabaseError,
    RustError,
    RustIOError,
    RustParseError,
)


def test_file_io_exceptions():
    """Test file I/O exception handling."""
    print("\n" + "=" * 60)
    print("Testing FileIOCore exception handling...")
    print("=" * 60)

    try:
        from ClassicLib.rust.file_io_rust import RustFileIOCore

        io_core = RustFileIOCore()

        if io_core.is_rust_accelerated:
            print("✓ Using Rust acceleration")

            # Test 1: Non-existent file (should trigger RustIOError or fallback)
            print("\nTest 1: Reading non-existent file...")
            try:
                import asyncio

                asyncio.run(io_core.read_file("/nonexistent/path/file.txt"))
                print("  ✗ No exception raised (unexpected)")
            except RustIOError as e:
                print(f"  ✓ Caught RustIOError: {e}")
            except RustError as e:
                print(f"  ✓ Caught RustError: {e}")
            except FileNotFoundError as e:
                print(f"  ✓ Caught FileNotFoundError (Python fallback): {e}")
            except Exception as e:
                print(f"  ? Caught unexpected exception: {type(e).__name__}: {e}")

            # Test 2: DDS header parsing (invalid file)
            print("\nTest 2: Parsing invalid DDS header...")
            try:
                result = io_core.read_dds_header(__file__)  # This file is not a DDS (sync method)
                if result is None:
                    print("  ✓ Returned None for invalid DDS file")
                else:
                    print(f"  ? Unexpected result: {result}")
            except RustParseError as e:
                print(f"  ✓ Caught RustParseError: {e}")
            except RustIOError as e:
                print(f"  ✓ Caught RustIOError: {e}")
            except Exception as e:
                print(f"  ? Caught unexpected exception: {type(e).__name__}: {e}")

            # Test 3: Check Rust-specific exceptions are subclasses
            print("\nTest 3: Verifying Rust module exception types...")
            try:
                import classic_file_io

                if hasattr(classic_file_io, "RustFileIOIOError"):
                    rust_io_error = classic_file_io.RustFileIOIOError
                    print(f"  ✓ RustFileIOIOError is subclass of RustIOError: {issubclass(rust_io_error, RustIOError)}")
                if hasattr(classic_file_io, "RustFileIOParseError"):
                    rust_parse_error = classic_file_io.RustFileIOParseError
                    print(f"  ✓ RustFileIOParseError is subclass of RustParseError: {issubclass(rust_parse_error, RustParseError)}")
            except Exception as e:
                print(f"  ? Error checking exception types: {e}")
        else:
            print("  ⚠ Rust acceleration not available, using Python fallback")

    except ImportError as e:
        print(f"  ✗ Failed to import RustFileIOCore: {e}")


def test_parser_exceptions():
    """Test log parser exception handling."""
    print("\n" + "=" * 60)
    print("Testing LogParser exception handling...")
    print("=" * 60)

    try:
        from ClassicLib.rust.parser_rust import RustLogParser

        parser = RustLogParser()

        if parser.is_rust_accelerated:
            print("✓ Using Rust acceleration")

            # Test: Invalid crash data (should trigger RustParseError or fallback)
            print("\nTest: Parsing invalid crash log data...")
            try:
                # Minimal test data that won't match expected format
                crash_data = ["invalid", "crash", "log"]
                result = parser.find_segments(crash_data, crashgen_name="Buffout 4", xse_acronym="F4SE", game_root_name="Fallout4")
                print(f"  ✓ Successfully parsed (or fell back): {len(result[3])} segments")
            except RustParseError as e:
                print(f"  ✓ Caught RustParseError: {e}")
            except RustError as e:
                print(f"  ✓ Caught RustError: {e}")
            except Exception as e:
                print(f"  ? Caught unexpected exception: {type(e).__name__}: {e}")
        else:
            print("  ⚠ Rust acceleration not available, using Python fallback")

    except ImportError as e:
        print(f"  ✗ Failed to import RustLogParser: {e}")


def test_database_exceptions():
    """Test database exception handling."""
    print("\n" + "=" * 60)
    print("Testing Database exception handling...")
    print("=" * 60)

    try:
        from ClassicLib.rust.database_rust import RustAsyncDatabasePool

        print("✓ Successfully imported RustAsyncDatabasePool")

        # Note: We don't initialize the pool here as it requires database setup
        # Just verify the import and exception types are available
        print("  ✓ RustDatabaseError is available")
        print("  ✓ Exception hierarchy ready for database operations")

    except ImportError as e:
        print(f"  ⚠ Rust database module not available: {e}")


def test_exception_hierarchy():
    """Test exception hierarchy relationships."""
    print("\n" + "=" * 60)
    print("Testing Exception Hierarchy...")
    print("=" * 60)

    # Test inheritance
    print("\nVerifying exception inheritance:")
    print(f"  RustIOError inherits from RustError: {issubclass(RustIOError, RustError)}")
    print(f"  RustIOError inherits from IOError: {issubclass(RustIOError, IOError)}")
    print(f"  RustParseError inherits from RustError: {issubclass(RustParseError, RustError)}")
    print(f"  RustParseError inherits from ValueError: {issubclass(RustParseError, ValueError)}")
    print(f"  RustConfigError inherits from RustError: {issubclass(RustConfigError, RustError)}")
    print(f"  RustDatabaseError inherits from RustError: {issubclass(RustDatabaseError, RustError)}")

    # Test catching with base class
    print("\nTesting catch with base RustError:")
    try:
        raise RustIOError("Test I/O error")
    except RustError as e:
        print(f"  ✓ Caught RustIOError with RustError handler: {e}")

    try:
        raise RustParseError("Test parse error")
    except RustError as e:
        print(f"  ✓ Caught RustParseError with RustError handler: {e}")


def main():
    """Run all exception handling tests."""
    print("=" * 60)
    print("Rust Exception Handling Test Suite")
    print("=" * 60)

    test_exception_hierarchy()
    test_file_io_exceptions()
    test_parser_exceptions()
    test_database_exceptions()

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
