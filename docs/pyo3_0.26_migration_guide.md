# PyO3 0.26.0 Migration Guide for CLASSIC

This guide documents the migration of CLASSIC's Rust extensions from PyO3 0.22 to PyO3 0.26.0, completed on September 27, 2025. This migration prepares the codebase for Python's free-threaded builds and improves thread safety.

## Table of Contents

1. [Overview](#overview)
2. [Key API Changes](#key-api-changes)
3. [Migration Examples](#migration-examples)
4. [Building and Testing](#building-and-testing)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices for New Code](#best-practices-for-new-code)

## Overview

PyO3 0.26.0 introduces significant improvements to GIL (Global Interpreter Lock) handling and type safety in preparation for Python's free-threaded future. The migration maintains full backward compatibility at the Python API level while modernizing the Rust internals.

### What Changed

- **GIL Management**: Renamed methods for clarity (`with_gil` → `attach`)
- **Type Aliases**: Deprecated `PyObject` in favor of explicit `Py<PyAny>`
- **Collection Creation**: Simplified bound object creation APIs
- **Type Conversions**: New `IntoPyObject` trait replacing `IntoPy`
- **Thread Safety**: Replaced `GILOnceCell` and `GILProtected` with modern primitives

### What Stayed the Same

- **Python API**: No changes to Python-facing interfaces
- **Performance**: No performance regression
- **Business Logic**: All functionality preserved exactly
- **Build Process**: Same maturin workflow

## Key API Changes

### 1. GIL Attachment

The primary API change is renaming GIL attachment methods to better reflect their purpose.

#### Before (PyO3 0.22)
```rust
use pyo3::Python;

// Acquire the GIL
Python::with_gil(|py| {
    // Python operations here
})

// Release the GIL
py.allow_threads(|| {
    // Non-Python operations
})
```

#### After (PyO3 0.26.0)
```rust
use pyo3::Python;

// Attach to the Python interpreter
Python::attach(|py| {
    // Python operations here
})

// Detach from the Python interpreter
py.detach(|| {
    // Non-Python operations
})
```

**Why**: The new names better reflect PyO3's role in Python's free-threaded future, where GIL might not exist.

### 2. Type Alias Changes

The `PyObject` type alias is deprecated in favor of explicit `Py<PyAny>`.

#### Before (PyO3 0.22)
```rust
use pyo3::PyObject;

fn process_data(data: PyObject) -> PyResult<PyObject> {
    // Process Python object
}
```

#### After (PyO3 0.26.0)
```rust
use pyo3::Py;
use pyo3::types::PyAny;

fn process_data(data: Py<PyAny>) -> PyResult<Py<PyAny>> {
    // Process Python object
}
```

**Why**: Explicit types improve code clarity and prevent confusion about ownership semantics.

### 3. Collection Creation

Collection creation methods now return `Bound<T>` directly without the `_bound` suffix.

#### Before (PyO3 0.22)
```rust
use pyo3::types::{PyList, PyDict};

Python::with_gil(|py| {
    let list = PyList::new_bound(py, items);
    let dict = PyDict::new_bound(py);
    list.into()
})
```

#### After (PyO3 0.26.0)
```rust
use pyo3::types::{PyList, PyDict};

Python::attach(|py| {
    let list = PyList::new(py, items)?;
    let dict = PyDict::new(py);
    list.unbind().into()
})
```

**Why**: The `_bound` suffix was transitional. Now all methods return `Bound<T>` by default.

### 4. Type Conversions

Primitive type conversions now use the new `IntoPyObject` trait.

#### Before (PyO3 0.22)
```rust
use pyo3::IntoPy;

Python::with_gil(|py| {
    let py_int = value.into_py(py);
    py_int
})
```

#### After (PyO3 0.26.0)
```rust
use pyo3::IntoPyObject;

Python::attach(|py| {
    let py_int = value.into_pyobject(py)?.as_any().clone().unbind();
    py_int
})
```

**Why**: The new trait provides better error handling and type safety.

### 5. Bound to Py Conversion

Converting from `Bound<T>` to `Py<T>` now requires explicit `.unbind()`.

#### Before (PyO3 0.22)
```rust
let bound_obj = PyList::new_bound(py, items);
let py_obj: PyObject = bound_obj.into();
```

#### After (PyO3 0.26.0)
```rust
let bound_obj = PyList::new(py, items)?;
let py_obj: Py<PyAny> = bound_obj.unbind().into();
```

**Why**: Explicit conversion prevents accidental lifetime issues.

### 6. Module and Import

Module creation and import methods also lost their `_bound` suffix.

#### Before (PyO3 0.22)
```rust
let module = PyModule::new_bound(py, "name")?;
let imported = py.import_bound("sys")?;
```

#### After (PyO3 0.26.0)
```rust
let module = PyModule::new(py, "name")?;
let imported = py.import("sys")?;
```

## Migration Examples

### Example 1: YAML Parser

This example shows the complete migration of a complex component.

#### Before (PyO3 0.22)
```rust
use pyo3::{PyObject, Python};
use pyo3::types::PyDict;

pub fn parse_yaml(&self, content: &str) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let dict = PyDict::new_bound(py);
        dict.set_item("key", "value")?;
        Ok(dict.into())
    })
}
```

#### After (PyO3 0.26.0)
```rust
use pyo3::{Py, Python};
use pyo3::types::{PyAny, PyDict};

pub fn parse_yaml(&self, content: &str) -> PyResult<Py<PyAny>> {
    Python::attach(|py| {
        let dict = PyDict::new(py);
        dict.set_item("key", "value")?;
        Ok(dict.unbind().into())
    })
}
```

### Example 2: Test Code

Tests using PyO3 also need updates.

#### Before (PyO3 0.22)
```rust
#[test]
fn test_file_operations() {
    Python::with_gil(|py| {
        let file_io = RustFileIOCore::new().unwrap();
        let result = file_io.read_file_sync(py, "test.txt".to_string());
        assert!(result.is_ok());
    })
}
```

#### After (PyO3 0.26.0)
```rust
#[test]
fn test_file_operations() {
    Python::attach(|py| {
        let file_io = RustFileIOCore::new().unwrap();
        let result = file_io.read_file_sync(py, "test.txt".to_string());
        assert!(result.is_ok());
    })
}
```

### Example 3: Module Registration

Module registration with submodules.

#### Before (PyO3 0.22)
```rust
#[pymodule]
fn classic_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let utils_module = PyModule::new_bound(m.py(), "utils")?;
    utils::register_module(&utils_module)?;
    m.add_submodule(&utils_module)?;
    Ok(())
}
```

#### After (PyO3 0.26.0)
```rust
#[pymodule]
fn classic_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let utils_module = PyModule::new(m.py(), "utils")?;
    utils::register_module(&utils_module)?;
    m.add_submodule(&utils_module)?;
    Ok(())
}
```

## Building and Testing

### Building the Extension

```bash
# From project root (where Cargo.toml is located)
maturin build --release --out classic-rust/dist

# Install the wheel
uv pip install classic-rust/dist/classic-*.whl --force-reinstall
```

### Running Tests

```bash
# Rust unit tests
cargo test --all-features

# Python integration tests
uv run pytest tests/rust_integration/ -v

# Verify Rust is loaded
uv run python -c "import classic_core; print(f'Version: {classic_core.__version__}')"
```

### Expected Results

- **Rust Unit Tests**: 19/21 tests should pass (2 pre-existing failures in test data)
- **Python Integration**: Core file I/O and parser tests should pass
- **No API Changes**: Python code should work without modifications

## Troubleshooting

### Build Errors

#### Error: "no method named `with_gil`"
**Cause**: Code still using old API
**Solution**: Replace `Python::with_gil` with `Python::attach`

#### Error: "cannot find type `PyObject` in this scope"
**Cause**: `PyObject` type alias removed
**Solution**: Use `Py<PyAny>` explicitly

```rust
// Old
use pyo3::PyObject;

// New
use pyo3::Py;
use pyo3::types::PyAny;
```

#### Error: "no method named `new_bound`"
**Cause**: `_bound` suffix removed from collection methods
**Solution**: Use method name without suffix

```rust
// Old
PyList::new_bound(py, items)

// New
PyList::new(py, items)?
```

### Runtime Errors

#### Error: "ModuleNotFoundError: No module named 'classic_core'"
**Cause**: Wheel not installed or wrong environment
**Solution**: Reinstall wheel in correct environment

```bash
uv pip install classic-rust/dist/classic-*.whl --force-reinstall
```

#### Error: Type conversion failures
**Cause**: Incorrect usage of `IntoPyObject` trait
**Solution**: Use the full conversion chain

```rust
value.into_pyobject(py)?.as_any().clone().unbind()
```

### Performance Issues

If you notice performance degradation:

1. Check that Rust extensions are actually being used:
```python
from ClassicLib.integration.status import print_rust_status
print_rust_status()
```

2. Verify no GIL-intensive operations in hot paths
3. Profile with `py-spy` to identify bottlenecks

## Best Practices for New Code

When writing new PyO3 code for CLASSIC, follow these guidelines:

### 1. Use Modern API Consistently

```rust
// ✅ Good - Modern PyO3 0.26 API
Python::attach(|py| {
    let list = PyList::new(py, items)?;
    Ok(list.unbind().into())
})

// ❌ Bad - Old API (won't compile)
Python::with_gil(|py| {
    let list = PyList::new_bound(py, items);
    Ok(list.into())
})
```

### 2. Explicit Type Conversions

```rust
// ✅ Good - Explicit conversion steps
let py_obj: Py<PyAny> = bound_obj.unbind().into();

// ❌ Bad - Implicit conversion (may fail)
let py_obj = bound_obj.into();
```

### 3. Error Handling

```rust
// ✅ Good - Proper error handling
let list = PyList::new(py, items)?;

// ❌ Bad - Unwrapping (can panic)
let list = PyList::new(py, items).unwrap();
```

### 4. Consistent Naming

Use the new terminology consistently in comments and documentation:

```rust
// ✅ Good - Modern terminology
// Attach to Python interpreter for operations
Python::attach(|py| { /* ... */ })

// ❌ Bad - Old terminology
// Acquire the GIL
Python::attach(|py| { /* ... */ })
```

### 5. Module Structure

When creating new modules:

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule;

pub fn register_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(my_function, m)?)?;
    m.add_class::<MyClass>()?;
    Ok(())
}
```

### 6. Type Annotations

Be explicit about types, especially for `Py<T>`:

```rust
// ✅ Good - Clear type annotation
fn process(data: Py<PyAny>) -> PyResult<Py<PyAny>> {
    Python::attach(|py| {
        // Process data
        Ok(data)
    })
}

// ❌ Bad - Ambiguous return type
fn process(data: Py<PyAny>) -> PyResult<impl IntoPy<Py<PyAny>>> {
    // Harder to understand
}
```

## Additional Resources

- [PyO3 0.26.0 Migration Guide](https://pyo3.rs/v0.26.0/migration.html) - Official migration guide
- [PyO3 Documentation](https://pyo3.rs/v0.26.0/) - Complete API documentation
- [CLASSIC Rust Documentation Index](RUST_DOCUMENTATION_INDEX.md) - Project-specific Rust docs
- [Rust Usage Guide](rust_usage_guide.md) - How to use Rust components in CLASSIC

## Migration Checklist

Use this checklist when migrating code or reviewing PRs:

- [ ] Replace `Python::with_gil` with `Python::attach`
- [ ] Replace `Python::allow_threads` with `Python::detach`
- [ ] Replace `PyObject` with `Py<PyAny>`
- [ ] Remove `_bound` suffix from collection creation methods
- [ ] Add `.unbind()` before converting `Bound<T>` to `Py<T>`
- [ ] Update `IntoPy` to `IntoPyObject` where needed
- [ ] Test that Python API remains unchanged
- [ ] Verify performance benchmarks still meet targets
- [ ] Update any documentation referencing old API
- [ ] Run full test suite (Rust and Python)

## Version Compatibility

| PyO3 Version | CLASSIC Version | Status |
|--------------|-----------------|---------|
| 0.22.x       | 7.x             | Legacy (pre-migration) |
| 0.26.0       | 8.0.0+          | Current ✅ |

## Support

If you encounter issues with PyO3 0.26.0 in CLASSIC:

1. Check this migration guide for common solutions
2. Review the [Troubleshooting Rust Guide](troubleshooting_rust.md)
3. Check the [PyO3 GitHub Issues](https://github.com/PyO3/pyo3/issues)
4. File an issue in the CLASSIC repository with:
   - Your Rust and Python versions
   - Full error message and backtrace
   - Minimal reproduction example

---

**Migration completed**: September 27, 2025
**PyO3 version**: 0.26.0
**CLASSIC version**: 8.0.0