# PyO3-Async-Runtimes Usage Guide

## Overview

This guide demonstrates how to use `pyo3-async-runtimes` to create **true async Python functions** backed by Rust's Tokio runtime. This eliminates blocking and enables native async/await integration between Python and Rust.

## Table of Contents

1. [Basic Concepts](#basic-concepts)
2. [Setup and Dependencies](#setup-and-dependencies)
3. [Creating Async Python Functions from Rust](#creating-async-python-functions-from-rust)
4. [Converting Python Coroutines to Rust Futures](#converting-python-coroutines-to-rust-futures)
5. [Working with Classes](#working-with-classes)
6. [Error Handling](#error-handling)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

## Basic Concepts

### The Problem with Blocking

**Traditional PyO3 (Blocking):**
```rust
#[pyfunction]
fn blocking_function(py: Python) -> PyResult<String> {
    without_gil(py, || {
        // This BLOCKS the thread!
        get_runtime().block_on(async {
            expensive_async_operation().await
        })
    })
}
```

**Python side:**
```python
# Looks async, but actually blocks!
async def wrapper():
    result = rust_module.blocking_function()  # Thread blocked here
    return result
```

### The Solution: True Async

**PyO3-Async-Runtimes (Non-Blocking):**
```rust
use pyo3_async_runtimes::tokio::future_into_py;

#[pyfunction]
fn async_function<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
    // Returns Python coroutine immediately - no blocking!
    future_into_py(py, async {
        expensive_async_operation().await
    })
}
```

**Python side:**
```python
# True async - returns immediately, awaitable!
async def wrapper():
    result = await rust_module.async_function()  # Real coroutine
    return result
```

## Setup and Dependencies

### Cargo.toml

```toml
[dependencies]
pyo3 = { version = "0.26", features = ["extension-module", "abi3-py312"] }
pyo3-async-runtimes = { version = "0.26", features = ["tokio-runtime"] }
tokio = { version = "1", features = ["full"] }

[lib]
name = "my_module"
crate-type = ["cdylib"]
```

### Rust Imports

```rust
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::{future_into_py, into_future};
```

## Creating Async Python Functions from Rust

### Simple Async Function

```rust
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;
use tokio::time::{sleep, Duration};

#[pyfunction]
fn sleep_async<'py>(py: Python<'py>, seconds: u64) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        sleep(Duration::from_secs(seconds)).await;
        Ok(())
    })
}
```

**Python usage:**
```python
import asyncio
import my_module

async def main():
    await my_module.sleep_async(2)  # Sleeps 2 seconds without blocking
    print("Done!")

asyncio.run(main())
```

### Async Function with Return Value

```rust
#[pyfunction]
fn fetch_data<'py>(py: Python<'py>, url: String) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let response = reqwest::get(&url).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        let text = response.text().await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Ok(text)
    })
}
```

**Python usage:**
```python
async def main():
    data = await my_module.fetch_data("https://example.com")
    print(f"Fetched: {data}")
```

### Async Function with Complex Return Types

```rust
use pyo3::types::{PyDict, PyList};

#[pyfunction]
fn process_batch<'py>(
    py: Python<'py>,
    items: Vec<String>
) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let mut results = Vec::new();

        for item in items {
            let processed = process_item(&item).await;
            results.push(processed);
        }

        // Return as Python dict
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("count", results.len())?;
            dict.set_item("items", results)?;
            Ok(dict.into())
        })
    })
}
```

## Converting Python Coroutines to Rust Futures

### Calling Python Async Functions from Rust

```rust
use pyo3_async_runtimes::tokio::into_future;

#[pyfunction]
fn call_python_async<'py>(
    py: Python<'py>,
    python_coro: Bound<'py, PyAny>
) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        // Convert Python coroutine to Rust future
        let result = into_future(python_coro).await?;
        Ok(result)
    })
}
```

**Python usage:**
```python
async def my_python_async():
    await asyncio.sleep(1)
    return "Hello from Python!"

async def main():
    result = await my_module.call_python_async(my_python_async())
    print(result)  # "Hello from Python!"
```

## Working with Classes

### Async Methods in PyO3 Classes

```rust
use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;
use std::sync::Arc;
use tokio::sync::RwLock;

#[pyclass]
struct AsyncDatabase {
    inner: Arc<RwLock<DatabaseInner>>,
}

struct DatabaseInner {
    connection_string: String,
    // ... other fields
}

#[pymethods]
impl AsyncDatabase {
    #[new]
    fn new(connection_string: String) -> Self {
        Self {
            inner: Arc::new(RwLock::new(DatabaseInner {
                connection_string,
            })),
        }
    }

    // Async method
    fn query<'py>(
        &self,
        py: Python<'py>,
        sql: String
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();

        future_into_py(py, async move {
            let db = inner.read().await;
            // Perform query
            let result = perform_query(&db.connection_string, &sql).await?;
            Ok(result)
        })
    }

    // Another async method
    fn insert<'py>(
        &self,
        py: Python<'py>,
        table: String,
        data: String
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();

        future_into_py(py, async move {
            let mut db = inner.write().await;
            // Perform insert
            insert_data(&db.connection_string, &table, &data).await?;
            Ok(())
        })
    }
}

async fn perform_query(conn: &str, sql: &str) -> PyResult<String> {
    // Implementation
    Ok("query result".to_string())
}

async fn insert_data(conn: &str, table: &str, data: &str) -> PyResult<()> {
    // Implementation
    Ok(())
}
```

**Python usage:**
```python
import asyncio

async def main():
    db = my_module.AsyncDatabase("postgresql://localhost/mydb")

    # Query
    result = await db.query("SELECT * FROM users")
    print(result)

    # Insert
    await db.insert("users", '{"name": "Alice"}')
```

### Key Points for Classes:

1. **Clone Arc for Move:** `let inner = self.inner.clone();`
2. **Move into Async Block:** Data must be `'static` or cloned
3. **Thread Safety:** Use `Arc<RwLock<T>>` or `Arc<Mutex<T>>`

## Error Handling

### Converting Rust Errors to Python Exceptions

```rust
use pyo3::exceptions::{PyRuntimeError, PyValueError};

#[pyfunction]
fn may_fail<'py>(py: Python<'py>, value: i32) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        if value < 0 {
            // Return Python exception
            return Err(PyValueError::new_err("Value must be non-negative"));
        }

        let result = risky_operation(value).await
            .map_err(|e| PyRuntimeError::new_err(format!("Operation failed: {}", e)))?;

        Ok(result)
    })
}

async fn risky_operation(value: i32) -> Result<i32, Box<dyn std::error::Error>> {
    // May fail
    Ok(value * 2)
}
```

**Python usage:**
```python
async def main():
    try:
        result = await my_module.may_fail(-5)
    except ValueError as e:
        print(f"Error: {e}")  # "Value must be non-negative"
```

### Custom Error Types

```rust
use thiserror::Error;

#[derive(Error, Debug)]
enum MyError {
    #[error("Database error: {0}")]
    Database(String),
    #[error("Network error: {0}")]
    Network(String),
}

fn to_pyerr(error: MyError) -> PyErr {
    match error {
        MyError::Database(msg) => {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("DB: {}", msg))
        }
        MyError::Network(msg) => {
            PyErr::new::<pyo3::exceptions::PyConnectionError, _>(format!("Net: {}", msg))
        }
    }
}

#[pyfunction]
fn complex_operation<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let result = perform_complex_op().await
            .map_err(to_pyerr)?;
        Ok(result)
    })
}
```

## Common Patterns

### Pattern 1: Database Connection Pool

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

#[pyclass]
struct DatabasePool {
    pool: Arc<RwLock<sqlx::Pool<sqlx::Postgres>>>,
}

#[pymethods]
impl DatabasePool {
    #[new]
    fn new(connection_string: String) -> PyResult<Self> {
        // Synchronous initialization
        Ok(Self {
            pool: Arc::new(RwLock::new(create_pool_sync(&connection_string)?)),
        })
    }

    fn initialize<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let pool = self.pool.clone();

        future_into_py(py, async move {
            // Async initialization
            let mut p = pool.write().await;
            initialize_pool(&mut p).await?;
            Ok(())
        })
    }

    fn query<'py>(
        &self,
        py: Python<'py>,
        sql: String
    ) -> PyResult<Bound<'py, PyAny>> {
        let pool = self.pool.clone();

        future_into_py(py, async move {
            let p = pool.read().await;
            let result = sqlx::query(&sql)
                .fetch_all(&*p)
                .await
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

            // Convert to Python list
            Ok(result.len())  // Simplified
        })
    }
}

fn create_pool_sync(conn: &str) -> PyResult<sqlx::Pool<sqlx::Postgres>> {
    // Sync pool creation
    todo!()
}

async fn initialize_pool(pool: &mut sqlx::Pool<sqlx::Postgres>) -> PyResult<()> {
    // Async initialization
    Ok(())
}
```

### Pattern 2: File I/O Operations

```rust
use tokio::fs;
use tokio::io::AsyncReadExt;

#[pyfunction]
fn read_file_async<'py>(
    py: Python<'py>,
    path: String
) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let mut file = fs::File::open(&path).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(e.to_string()))?;

        let mut contents = String::new();
        file.read_to_string(&mut contents).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(contents)
    })
}

#[pyfunction]
fn write_file_async<'py>(
    py: Python<'py>,
    path: String,
    contents: String
) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        fs::write(&path, contents).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        Ok(())
    })
}
```

### Pattern 3: Concurrent Operations

```rust
use tokio::task::JoinSet;

#[pyfunction]
fn process_concurrent<'py>(
    py: Python<'py>,
    items: Vec<String>
) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async move {
        let mut set = JoinSet::new();

        // Spawn concurrent tasks
        for item in items {
            set.spawn(async move {
                process_item(&item).await
            });
        }

        // Collect results
        let mut results = Vec::new();
        while let Some(res) = set.join_next().await {
            results.push(res.map_err(|e| PyRuntimeError::new_err(e.to_string()))?);
        }

        Ok(results.len())
    })
}

async fn process_item(item: &str) -> String {
    format!("Processed: {}", item)
}
```

## Troubleshooting

### Issue: "Type not 'static"

**Error:**
```
error[E0759]: `py` has lifetime `'py` but it needs to satisfy a `'static` lifetime requirement
```

**Solution:** Clone or convert data before moving into async block:

```rust
// ❌ BAD
fn bad_example<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    future_into_py(py, async {
        use_data(data).await  // Error: data is borrowed
    })
}

// ✅ GOOD
fn good_example<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    let data = data.to_string();  // Clone to owned
    future_into_py(py, async move {
        use_data(&data).await
    })
}
```

### Issue: "Cannot move out of shared reference"

**Solution:** Use `Arc` for shared ownership:

```rust
use std::sync::Arc;

#[pyclass]
struct MyClass {
    data: Arc<SomeData>,  // Use Arc
}

#[pymethods]
impl MyClass {
    fn async_method<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let data = self.data.clone();  // Clone Arc (cheap)
        future_into_py(py, async move {
            use_data(&data).await
        })
    }
}
```

### Issue: "Future cannot be sent between threads"

**Solution:** Ensure all types in the future are `Send`:

```rust
// ❌ BAD: Rc is not Send
use std::rc::Rc;

// ✅ GOOD: Arc is Send + Sync
use std::sync::Arc;
```

## Best Practices

1. **Always Clone Before Move:**
   ```rust
   let data = self.data.clone();
   future_into_py(py, async move { ... })
   ```

2. **Use Arc for Shared State:**
   ```rust
   struct MyClass {
       data: Arc<RwLock<Data>>,
   }
   ```

3. **Convert Errors Properly:**
   ```rust
   .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
   ```

4. **Return Correct Type:**
   ```rust
   fn my_func<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyAny>>
   ```

5. **Test with Python:**
   ```python
   assert asyncio.iscoroutine(rust_func())
   ```

## Summary

**Key Takeaways:**

✅ Use `future_into_py(py, async { ... })` to create Python coroutines
✅ Clone Arc-wrapped data before moving into async blocks
✅ Return type must be `PyResult<Bound<'py, PyAny>>`
✅ No more `block_on()` - functions return immediately
✅ True async concurrency with Python's event loop
✅ Full Tokio power with Python's async/await syntax

**The Result:** Clean, fast, non-blocking async integration between Python and Rust! 🚀
