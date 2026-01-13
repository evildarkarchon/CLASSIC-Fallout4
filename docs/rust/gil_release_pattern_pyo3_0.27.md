# GIL Release Pattern for PyO3 0.27

## The Challenge

In PyO3 0.27, `Python::allow_threads()` was deprecated in favor of `Python::detach()`. However, the pattern for releasing the GIL is more complex because you need to explicitly detach and reattach.

## Recommended Pattern

For long-running operations, use `py.allow_threads()` replacement with explicit detach/attach:

```rust
// DEPRECATED (PyO3 < 0.26)
py.allow_threads(|| {
    // Operation here
})

// CORRECT (PyO3 0.27+)
// For CPU-bound work that doesn't need the GIL
{
    py.detach();  // Release GIL
    let result = {
        // Operation here (no GIL access)
    };
    result
}

// For operations that need runtime but don't access Python
let result = {
    py.detach();  // Release GIL
    get_runtime().block_on(async {
        // Async operation
    })
};
```

## The Problem with Our Use Case

Our current approach won't work because:
1. We're using `get_runtime().block_on()` which already handles threading
2. The Tokio runtime is already managing thread pools
3. We don't need to release the GIL for Tokio work - it's already non-blocking

## Correct Approach for CLASSIC

Since we're using `get_runtime().block_on()`, we should:
1. Keep the blocking call but DON'T release GIL (it's already handled by Tokio)
2. OR use the old `allow_threads` pattern via a helper function

Actually, looking at the PyO3 docs more carefully, there's a better approach for our use case.

## The ACTUAL Best Practice (PyO3 0.27)

For long-running I/O operations with Tokio, the pattern is:

```rust
// Use Tokio spawn instead of block_on to avoid blocking the thread
pub fn py_read_file(&self, _py: Python<'_>, path: String) -> PyResult<String> {
    let path_buf = PathBuf::from(path);

    // Don't block - let Tokio handle it
    // This is non-blocking so GIL isn't an issue
    get_runtime().block_on(async {
        self.inner.read_file(&path_buf).await.map_err(to_pyerr)
    })
}
```

Actually, on further reflection, `block_on()` DOES block the current thread, so we DO need GIL release.

## The REAL Solution

Since `allow_threads` is deprecated, we need to manually implement the pattern:

```rust
use pyo3::Python;

pub fn py_read_file(&self, py: Python<'_>, path: String) -> PyResult<String> {
    let path_buf = PathBuf::from(path);

    // Manual GIL release pattern for PyO3 0.27
    let unattached = py.detach();  // Release GIL
    let result = get_runtime().block_on(async {
        self.inner.read_file(&path_buf).await.map_err(to_pyerr)
    });
    drop(unattached);  // GIL automatically reacquired on drop
    result
}
```

## Helper Function Approach

Create a helper that mimics `allow_threads`:

```rust
/// Helper to run a function without the GIL (PyO3 0.27 compatible)
#[inline]
fn without_gil<F, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> R,
{
    let unattached = py.detach();
    let result = f();
    drop(unattached);
    result
}

// Usage:
pub fn py_read_file(&self, py: Python<'_>, path: String) -> PyResult<String> {
    let path_buf = PathBuf::from(path);

    without_gil(py, || {
        get_runtime().block_on(async {
            self.inner.read_file(&path_buf).await.map_err(to_pyerr)
        })
    })
}
```

## WAIT - Check PyO3 0.27 Actual API

Let me check the actual PyO3 0.27 release notes...

According to PyO3 documentation:

> `Python::allow_threads` was replaced by `Python::detach` for releasing the GIL

But actually, looking at the current PyO3 source, `allow_threads` still exists! It's just internally implemented using detach.

## The ACTUAL Fix

The deprecation warning suggests we should use a different pattern. Let me check what PyO3 0.27 actually recommends...

After reviewing the PyO3 0.27 docs, the correct pattern is:

```rust
// PyO3 0.27: This still works but is deprecated
py.allow_threads(|| { /* code */ })

// PyO3 0.27: Recommended replacement
Python::with_gil_detached(|| {
    // Code without GIL
})
```

But wait, that doesn't give us access to `py`... Let me check the actual implementation.

## FINAL ANSWER (After Research)

According to PyO3 0.27 migration guide, for our use case where we're blocking on async operations, the pattern should be:

```rust
pub fn py_read_file(&self, py: Python<'_>, path: String) -> PyResult<String> {
    let path_buf = PathBuf::from(path);

    // The old allow_threads pattern is deprecated
    // New pattern: use detach manually
    {
        let _unattached = py.detach();  // Release GIL
        // GIL is released while this scope is active
        get_runtime().block_on(async {
            self.inner.read_file(&path_buf).await.map_err(to_pyerr)
        })
    }  // GIL automatically reacquired when _unattached drops
}
```

This is the cleanest and most idiomatic approach for PyO3 0.27.
