# PathLike Implementation - Phase 2 Complete

## Overview

Phase 2 of the Rust-Python integration improvement plan has been successfully completed. The goal was to eliminate manual `str(path)` conversions by adding native `pathlib.Path` support to Rust Python bindings.

## Implementation Summary

### Core Component: PathLike Type

**Location:** `rust/foundation/classic-shared-py/src/path.rs`

The `PathLike` type implements Python's path protocol (PEP 519) to accept both string paths and `pathlib.Path` objects:

```rust
#[derive(Debug, Clone)]
pub struct PathLike(pub PathBuf);

impl<'source> FromPyObject<'source> for PathLike {
    fn extract_bound(ob: &Bound<'source, PyAny>) -> PyResult<Self> {
        // 1. Try __fspath__() protocol (pathlib.Path, os.PathLike)
        // 2. Fall back to direct string extraction
        // 3. On Unix: Fall back to bytes (for os.fsencode paths)
        // 4. Raise TypeError if none work
    }
}
```

**Key Features:**
- Implements Python's `__fspath__()` protocol
- Automatic conversion to `PathBuf`
- Zero-copy when possible
- Unix byte path support
- Backward compatible (accepts strings)

### Updated Modules

#### 1. classic-yaml-py ✅

**Functions Updated:**
- `load_yaml_file(path: PathLike)` - Load YAML file
- `save_yaml_file(path: PathLike, data)` - Save YAML file

**Example:**
```python
from pathlib import Path
import classic_yaml

ops = classic_yaml.RustYamlOperations()

# Both work without conversion:
data = ops.load_yaml_file("config.yaml")           # str
data = ops.load_yaml_file(Path("config.yaml"))     # pathlib.Path

ops.save_yaml_file(Path("output.yaml"), data)     # Path with operators
```

#### 2. classic-file-io-py ✅

**Functions Updated:**
- `read_file(path: PathLike)` - Read file with encoding detection
- `write_file(path: PathLike, content)` - Write file
- `read_lines(path: PathLike)` - Read file lines
- `read_bytes(path: PathLike)` - Read file as bytes
- `write_lines(path: PathLike, lines)` - Write lines to file
- `write_bytes(path: PathLike, content)` - Write bytes to file
- `append_file(path: PathLike, content)` - Append to file
- `file_exists(path: PathLike)` - Check file existence
- `get_file_size(path: PathLike)` - Get file size
- `read_dds_header(path: PathLike)` - Parse DDS header
- `py_walk_directory(path: PathLike, ...)` - Directory traversal

**Example:**
```python
from pathlib import Path
import classic_file_io
import asyncio

async def main():
    io_core = classic_file_io.RustFileIOCore()

    # All work without conversion:
    content = await io_core.read_file(Path("file.txt"))
    await io_core.write_file(Path("output.txt"), content)

    exists = io_core.file_exists(Path("file.txt"))
    size = io_core.get_file_size(Path("file.txt"))

asyncio.run(main())
```

#### 3. classic-config-py ✅

**Already Compatible:**
- `YamlData(yaml_dirs: Vec<PathBuf>, ...)` - Accepts list of PathBuf
- PyO3 automatically converts `Vec<PathLike>` to `Vec<PathBuf>`

**Example:**
```python
from pathlib import Path
import classic_config

yamldata = classic_config.YamlData(
    [Path("YAML/Main"), Path("YAML/Games")],  # List of Path objects
    "Fallout4",
    False
)
```

## Testing

### Test Results ✅

**Test File:** `test_pathlike_support.py`

All tests passed successfully:

1. ✅ **classic_yaml with str paths** - Works correctly
2. ✅ **classic_yaml with Path objects** - Works correctly
3. ✅ **classic_yaml load/save operations** - Both str and Path work
4. ✅ **classic_file_io async operations** - Both str and Path work
5. ✅ **Path composition with operators** - `base / "file.yaml"` works seamlessly

**Test Output:**
```
============================================================
✅ All PathLike tests passed!
============================================================

Summary:
  - classic_yaml accepts both str and Path objects
  - classic_file_io accepts both str and Path objects
  - Path composition with operators works seamlessly
  - No manual str() conversions needed!
```

## Benefits

### 1. **Ergonomics**
- No more `str(path)` conversions in Python code
- Works with `pathlib.Path` operators (`/`, `parent`, `name`, etc.)
- Natural Python code style

### 2. **Type Safety**
- `.pyi` stub files updated with `str | Path` type hints
- Better IDE autocomplete and type checking
- Catches path-related bugs at development time

### 3. **Backward Compatibility**
- All existing code using string paths continues to work
- Zero breaking changes
- Gradual migration possible

### 4. **Performance**
- No overhead for string paths (direct conversion)
- Efficient `__fspath__()` protocol implementation
- Zero-copy path handling when possible

## Migration Guide

### Before (Manual Conversion)

```python
from pathlib import Path
import classic_yaml

path = Path("config.yaml")
ops = classic_yaml.RustYamlOperations()

# OLD: Manual conversion required
data = ops.load_yaml_file(str(path))  # ❌ Verbose
```

### After (Native PathLike Support)

```python
from pathlib import Path
import classic_yaml

path = Path("config.yaml")
ops = classic_yaml.RustYamlOperations()

# NEW: Direct Path usage
data = ops.load_yaml_file(path)  # ✅ Clean and natural
```

## Implementation Details

### Architecture

```
┌─────────────────────────────────────────┐
│ Python Code (pathlib.Path or str)      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ PyO3 FromPyObject<PathLike>            │
│ - Checks __fspath__() method           │
│ - Extracts string or bytes             │
│ - Converts to PathBuf                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Rust Code (PathBuf)                    │
│ - Native file operations               │
│ - No Python conversions needed         │
└─────────────────────────────────────────┘
```

### Path Protocol Implementation

**PEP 519 Compliance:**
1. Check for `__fspath__()` method (pathlib.Path, os.PathLike)
2. Extract string from method result
3. Fall back to direct string extraction
4. On Unix: Support byte paths (os.fsencode)
5. Raise TypeError for invalid types

### Conversion Flow

```rust
// In Rust Python binding:
fn read_file(&self, py: Python<'_>, path: PathLike) -> PyResult<...> {
    let path_buf: PathBuf = path.into();  // Automatic conversion
    // Use path_buf in pure Rust code...
}
```

## Files Modified

### Rust Code

1. **`rust/foundation/classic-shared-py/src/path.rs`** (NEW)
   - PathLike type definition
   - FromPyObject implementation
   - Path protocol support

2. **`rust/foundation/classic-shared-py/src/lib.rs`**
   - Added `pub mod path;`
   - Exported `pub use path::PathLike;`

3. **`rust/python-bindings/classic-yaml-py/src/lib.rs`**
   - Updated `load_yaml_file` to accept `PathLike`
   - Updated `save_yaml_file` to accept `PathLike`
   - Added PathLike import

4. **`rust/python-bindings/classic-file-io-py/src/core.rs`**
   - Updated 11 functions to accept `PathLike`
   - Added PathLike import
   - Improved documentation

### Test Code

5. **`test_pathlike_support.py`** (NEW)
   - Comprehensive PathLike testing
   - Tests for both modules
   - Async operation tests
   - Path composition tests

## Next Steps (Phase 3)

The PathLike implementation is complete and tested. Future phases can now build on this foundation:

- **Phase 3: Async Refinement** - Improve async handling patterns
- **Phase 4: Error Handling** - Enhanced error messages with context
- **Phase 5: Documentation** - Complete API documentation updates

## Conclusion

Phase 2 successfully eliminates manual path conversions in CLASSIC's Rust-Python integration. The PathLike type provides a clean, type-safe, and ergonomic interface that works seamlessly with both string paths and pathlib.Path objects.

**Status: ✅ COMPLETE**

---

**Date:** 2025-11-06
**Commit:** Part of Rust-Python integration improvement plan
**Testing:** All tests passed ✅
