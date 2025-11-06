"""Test PathLike support in Rust modules.

This script verifies that both str and pathlib.Path objects work
seamlessly with Rust Python bindings without manual conversions.
"""

from pathlib import Path
import tempfile
import classic_yaml
import classic_file_io

print("=" * 60)
print("Testing PathLike Support in Rust Modules")
print("=" * 60)

# Test 1: classic_yaml with str
print("\n✓ Test 1: classic_yaml.RustYamlOperations with str path")
ops = classic_yaml.RustYamlOperations()
try:
    ops.load_yaml_file("nonexistent.yaml")
except Exception as e:
    print(f"  Expected error with str: {type(e).__name__}")
    assert "RustYamlIOError" in str(type(e).__name__)

# Test 2: classic_yaml with Path
print("\n✓ Test 2: classic_yaml.RustYamlOperations with Path object")
try:
    ops.load_yaml_file(Path("nonexistent.yaml"))
except Exception as e:
    print(f"  Expected error with Path: {type(e).__name__}")
    assert "RustYamlIOError" in str(type(e).__name__)

# Test 3: Actually load a file with both str and Path
print("\n✓ Test 3: classic_yaml load/save with actual file")
with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    test_yaml_path = f.name
    f.write("test_key: test_value\nnested:\n  key: value\n")

try:
    # Load with str
    data_str = ops.load_yaml_file(test_yaml_path)
    print(f"  Loaded with str path: {data_str}")

    # Load with Path
    data_path = ops.load_yaml_file(Path(test_yaml_path))
    print(f"  Loaded with Path object: {data_path}")

    # Save with str
    ops.save_yaml_file(test_yaml_path, data_str)
    print(f"  Saved with str path: OK")

    # Save with Path
    ops.save_yaml_file(Path(test_yaml_path), data_path)
    print(f"  Saved with Path object: OK")
finally:
    Path(test_yaml_path).unlink(missing_ok=True)

# Test 4: classic_file_io with async operations
print("\n✓ Test 4: classic_file_io.RustFileIOCore with str and Path")
import asyncio

async def test_file_io():
    io_core = classic_file_io.RustFileIOCore()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_file_path = f.name
        f.write("test content\n")

    try:
        # Read with str
        content_str = await io_core.read_file(test_file_path)
        print(f"  Read with str path: {content_str.strip()}")

        # Read with Path
        content_path = await io_core.read_file(Path(test_file_path))
        print(f"  Read with Path object: {content_path.strip()}")

        # Write with str
        await io_core.write_file(test_file_path, "new content\n")
        print(f"  Write with str path: OK")

        # Write with Path
        await io_core.write_file(Path(test_file_path), "final content\n")
        print(f"  Write with Path object: OK")

        # Verify sync methods work too
        exists_str = io_core.file_exists(test_file_path)
        exists_path = io_core.file_exists(Path(test_file_path))
        print(f"  file_exists with str: {exists_str}")
        print(f"  file_exists with Path: {exists_path}")

        size_str = io_core.get_file_size(test_file_path)
        size_path = io_core.get_file_size(Path(test_file_path))
        print(f"  get_file_size with str: {size_str}")
        print(f"  get_file_size with Path: {size_path}")

    finally:
        Path(test_file_path).unlink(missing_ok=True)

asyncio.run(test_file_io())

# Test 5: Path operations (composition with operators)
print("\n✓ Test 5: Path composition with operators")
base = Path(tempfile.gettempdir())
test_path = base / "classic_test.yaml"

try:
    # Write with composed Path
    test_data = ops.parse_yaml("test: value")
    ops.save_yaml_file(test_path, test_data)
    print(f"  Saved to composed path: {test_path}")

    # Read with composed Path
    loaded_data = ops.load_yaml_file(test_path)
    print(f"  Loaded from composed path: {loaded_data}")
finally:
    test_path.unlink(missing_ok=True)

print("\n" + "=" * 60)
print("✅ All PathLike tests passed!")
print("=" * 60)
print("\nSummary:")
print("  - classic_yaml accepts both str and Path objects")
print("  - classic_file_io accepts both str and Path objects")
print("  - Path composition with operators works seamlessly")
print("  - No manual str() conversions needed!")
