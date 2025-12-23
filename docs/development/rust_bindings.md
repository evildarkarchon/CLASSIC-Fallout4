# Rust Bindings & FFI Patterns

**Last Updated:** 2025-12-22

This document outlines the standard patterns for creating high-performance Python bindings for Rust components in the CLASSIC project.

## 1. Error Handling

We use a standardized error handling schema to ensure Rust errors map cleanly to native Python exceptions.

### Schema Definition
The `ClassicError` enum (in `classic-shared-core`) is the source of truth.

| Rust Error | Python Exception |
| :--- | :--- |
| `ClassicError::Io` | `IOError` |
| `ClassicError::Validation` | `ValueError` |
| `ClassicError::Parse` | `ValueError` |
| `ClassicError::Database` | `RuntimeError` |
| `ClassicError::NotFound` | `FileNotFoundError` |

### Implementation Pattern
Binding crates must implement the `ToPyErr` trait for their local error type (or a wrapper struct).

```rust
use classic_shared::{ToPyErr, ResultExt};
use pyo3::exceptions::{PyIOError, PyValueError, PyRuntimeError};

struct PyModuleError(ModuleError);

impl ToPyErr for PyModuleError {
    type BaseException = PyRuntimeError;
    type IOException = PyIOError;
    type ParseException = PyValueError;

    fn to_pyerr(self) -> PyErr {
        match self.0 {
            ModuleError::Io(e) => Self::io_err(e.to_string()),
            ModuleError::Parse(e) => Self::parse_err(e.to_string()),
            _ => Self::base_err(self.0.to_string()),
        }
    }
}

// Usage in pymethods:
#[pymethods]
impl PyClass {
    fn method(&self) -> PyResult<()> {
        self.inner.operation().map_err(PyModuleError).map_pyerr()
    }
}
```

## 2. Zero-Copy & Low-Overhead Patterns

To maximize performance at the FFI boundary, avoid intermediate allocations.

### Returning Lists of Strings
Instead of returning `Vec<String>` (which allocates Rust strings, then converts to Python strings), construct the `PyList` directly from references.

**Bad (Double Allocation):**
```rust
fn get_strings() -> Vec<String> {
    vec_of_arc_str.iter().map(|s| s.to_string()).collect()
}
```

**Good (Direct Construction):**
```rust
use pyo3::types::{PyList, PyString};

fn get_strings<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
    let mut items = Vec::with_capacity(size);
    for s in &self.inner_data {
        // Create PyString directly from reference
        let py_str = PyString::new(py, s); 
        // PyList::new expects items that implement ToPyObject
        // Since 0.26, PyList::new takes an iterator. 
        // For efficiency, we can collect Bound<'py, PyString> into a Vec 
        // and pass that to PyList::new.
    }
    // Or efficiently map iterator:
    PyList::new(py, self.inner_data.iter().map(|s| PyString::new(py, s)))
}
```

### Returning Complex Structures
Avoid returning large Tuples or Dicts if the structure is known. Use `#[pyclass]` structs.

**Bad (Tuple Unpacking):**
```rust
fn get_data() -> (String, String, Vec<String>) { ... }
```

**Good (Struct Mapping):**
```rust
#[pyclass]
struct DataResult {
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    items: Py<PyList>,
}

fn get_data<'py>(&self, py: Python<'py>) -> PyResult<DataResult> {
    // ... construct optimized list ...
    Ok(DataResult { name, items })
}
```

This allows lazy access to fields in Python and avoids creating tuple objects for every return.

## 3. Thread Safety & GIL
- Use `classic_shared::without_gil` for any operation taking >1ms.
- Ensure Rust structs inside `#[pyclass]` are `Send + Sync` (e.g. use `Arc`, `RwLock`).
