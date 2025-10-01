# PyO3 0.26.0 Quick Reference for CLASSIC Developers

Quick reference guide for writing Rust-Python integration code with PyO3 0.26.0 in CLASSIC.

## Common Patterns

### Basic Python Interaction

```rust
use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict, PyAny};
use pyo3::Py;

// Attach to Python interpreter
Python::attach(|py| {
    // Your Python operations here
    Ok(())
})
```

### Creating Python Objects

```rust
// Lists
let list = PyList::new(py, vec![1, 2, 3])?;

// Dictionaries
let dict = PyDict::new(py);
dict.set_item("key", "value")?;

// Tuples
let tuple = (1, 2, 3).into_pyobject(py)?;

// Strings
let string = "hello".into_pyobject(py)?;
```

### Converting Types

```rust
// Rust → Python
let py_value = value.into_pyobject(py)?.as_any().clone().unbind();

// Python → Rust
let rust_value: String = py_obj.extract(py)?;

// Bound → Py
let py_obj: Py<PyAny> = bound_obj.unbind().into();
```

### Function Signatures

```rust
// Returning Python objects
fn process(data: Py<PyAny>) -> PyResult<Py<PyAny>> {
    Python::attach(|py| {
        // Process
        Ok(data)
    })
}

// With Python token
fn process_with_py(py: Python, data: Py<PyAny>) -> PyResult<Py<PyAny>> {
    // Use py directly
    Ok(data)
}

// Extracting to Rust
fn extract_string(data: Py<PyAny>) -> PyResult<String> {
    Python::attach(|py| {
        data.extract::<String>(py)
    })
}
```

### Classes and Methods

```rust
#[pyclass]
pub struct MyClass {
    data: String,
}

#[pymethods]
impl MyClass {
    #[new]
    fn new(data: String) -> PyResult<Self> {
        Ok(Self { data })
    }

    fn process(&self, input: String) -> PyResult<String> {
        Ok(format!("{}: {}", self.data, input))
    }

    #[getter]
    fn data(&self) -> PyResult<String> {
        Ok(self.data.clone())
    }
}
```

### Module Registration

```rust
use pyo3::types::PyModule;

#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add class
    m.add_class::<MyClass>()?;

    // Add function
    m.add_function(wrap_pyfunction!(my_function, m)?)?;

    // Add submodule
    let sub = PyModule::new(m.py(), "submodule")?;
    sub.add_function(wrap_pyfunction!(sub_function, &sub)?)?;
    m.add_submodule(&sub)?;

    // Add constants
    m.add("VERSION", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
```

### Error Handling

```rust
use pyo3::exceptions::*;

// Return Python exception
fn may_fail() -> PyResult<String> {
    if error_condition {
        return Err(PyValueError::new_err("Invalid input"));
    }
    Ok("success".to_string())
}

// Custom error messages
Python::attach(|py| {
    Err(PyRuntimeError::new_err(format!(
        "Failed to process {}", item
    )))
})
```

### Working with Files

```rust
use tokio::fs;

// Async file operations (using global runtime)
use once_cell::sync::Lazy;
use tokio::runtime::Runtime;

static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create runtime")
});

fn read_file_sync(path: String) -> PyResult<String> {
    RUNTIME.block_on(async move {
        tokio::fs::read_to_string(path).await
    }).map_err(|e| PyIOError::new_err(e.to_string()))
}
```

### Collections and Iteration

```rust
// Python list → Rust Vec
let py_list: &PyList = obj.downcast(py)?;
let items: Vec<String> = py_list.extract()?;

// Rust Vec → Python list
let vec = vec!["a", "b", "c"];
let py_list = PyList::new(py, vec)?;

// Dictionary iteration
let dict: &PyDict = obj.downcast(py)?;
for (key, value) in dict.iter() {
    let k: String = key.extract()?;
    let v: i32 = value.extract()?;
}
```

## API Migration Quick Reference

| Old (0.22) | New (0.26) | Notes |
|------------|------------|-------|
| `Python::with_gil` | `Python::attach` | Renamed |
| `Python::allow_threads` | `Python::detach` | Renamed |
| `PyObject` | `Py<PyAny>` | Type alias removed |
| `PyList::new_bound` | `PyList::new` | Returns `Bound<PyList>` |
| `PyDict::new_bound` | `PyDict::new` | Returns `Bound<PyDict>` |
| `PyModule::new_bound` | `PyModule::new` | Returns `Bound<PyModule>` |
| `py.import_bound` | `py.import` | Returns `Bound<PyModule>` |
| `obj.into()` | `obj.unbind().into()` | For `Bound<T>` → `Py<T>` |
| `.into_py(py)` | `.into_pyobject(py)?` | Primitive conversions |

## Testing Patterns

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;

    #[test]
    fn test_basic() {
        Python::attach(|py| {
            let result = my_function(py)?;
            assert!(result.is_some());
            Ok::<_, PyErr>(())
        }).unwrap();
    }
}
```

## Common Imports

```rust
// Always needed
use pyo3::prelude::*;

// For types
use pyo3::types::{PyAny, PyList, PyDict, PyTuple, PyString};

// For ownership
use pyo3::Py;

// For exceptions
use pyo3::exceptions::*;

// For module definition
use pyo3::types::PyModule;
```

## Performance Tips

1. **Release GIL for CPU-bound work**:
```rust
Python::attach(|py| {
    let result = py.detach(|| {
        // CPU-intensive work here
        expensive_computation()
    });
    Ok(result)
})
```

2. **Use parallel processing**:
```rust
use rayon::prelude::*;

let results: Vec<_> = items
    .par_iter()
    .map(|item| process(item))
    .collect();
```

3. **Cache Python objects**:
```rust
use once_cell::sync::Lazy;
use parking_lot::RwLock;

static CACHE: Lazy<RwLock<HashMap<String, Py<PyAny>>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));
```

## Debugging

### Enable Rust logging
```bash
export RUST_LOG=debug
export RUST_BACKTRACE=1
```

### Check if Rust is loaded
```python
import classic_core
print(f"Version: {classic_core.__version__}")
```

### Profile Rust code
```bash
cargo build --release
perf record target/release/classic_core
perf report
```

## See Also

- [PyO3 0.26.0 Migration Guide](pyo3_0.26_migration_guide.md) - Detailed migration documentation
- [PyO3 Documentation](https://pyo3.rs/v0.26.0/) - Official PyO3 documentation
- [Rust Usage Guide](rust_usage_guide.md) - Using Rust components in CLASSIC
- [Development with Rust](development_with_rust.md) - Development workflow