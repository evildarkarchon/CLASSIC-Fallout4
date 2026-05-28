# Runtime and GIL Call-Site Patterns

CLASSIC has exactly one Tokio runtime. Binding and frontend layers may adapt async Rust to synchronous or foreign-language APIs, but they must not create additional runtimes.

## Decision table

| Surface | Caller shape | Use | Avoid |
| --- | --- | --- | --- |
| Pure async Rust core | `async fn` already on Tokio | `.await` directly | `get_runtime().block_on(...)` inside async code |
| Shared runtime owner | `foundation/classic-shared-core` only | `classic_shared_core::get_runtime()` | Any second `Runtime::new()` / `Builder::new_*()` |
| C++ CXX sync bridge | sync FFI function wrapping async Rust | For new or migrated code, `crate::runtime_support::block_on(...)` or `block_on_result(...)` | adding more direct `get_runtime().block_on(...)` in bridge modules |
| Python sync PyO3 method | Python method blocks until Rust async completes | extract Python data, then `classic_shared::without_gil_block_on(py, || async { ... })` | holding the GIL while blocking; touching Python objects while detached |
| Python CPU/blocking sync method | sync Rust work with no async runtime need | extract Python data, then `classic_shared::without_gil(py, || work(...))` | `py.detach(...)` directly at each call site |
| Python true async PyO3 method | method returns an awaitable | `pyo3_async_runtimes::tokio::future_into_py(py, async move { ... })` | wrapping true async APIs in `block_on` |
| Node/Bun NAPI async method | `#[napi] async fn` wrapping async Rust | For new or migrated code, `crate::runtime::spawn_result(...)` when work must run on CLASSIC's shared runtime | adding more ad hoc `get_runtime().handle().clone().spawn(...)` boilerplate |
| TUI/UI background task | UI callback starts background Rust work | `classic_shared_core::AsyncBridge` for UI callbacks, or `get_runtime().spawn(...)` for non-UI background work | long `block_on` calls from UI/event-loop handlers |

## Canonical helper snippets

### C++ bridge sync wrapper

```rust
use crate::runtime_support::block_on_result;

fn bridge_call(arg: &str) -> Result<String, String> {
    block_on_result(core_async_call(arg))
}
```

Use `block_on(...)` only when the async operation does not return a `Result` or when the wrapper intentionally preserves existing sentinel/error behavior.

### Python sync wrapper backed by async Rust

```rust
use classic_shared::without_gil_block_on;

fn load(py: Python<'_>, path: String) -> PyResult<Self> {
    let path = PathBuf::from(path); // extract/convert while GIL is held
    let inner = without_gil_block_on(py, || async { CoreType::load(&path).await })
        .map_err(to_pyerr)?;
    Ok(Self { inner })
}
```

Rules:

1. Convert `PyAny`, `PyDict`, paths, callbacks, and other Python-owned values before detaching.
2. Do not access Python objects inside `without_gil(...)` or `without_gil_block_on(...)`.
3. If a detached async task needs to invoke a Python callback later, reacquire the GIL with `Python::attach(...)` for that callback only.

### Python true async wrapper

```rust
use pyo3_async_runtimes::tokio::future_into_py;

fn read_file<'py>(py: Python<'py>, path: PathLike) -> PyResult<Bound<'py, PyAny>> {
    let path = PathBuf::from(path);
    future_into_py(py, async move { core_read_file(&path).await.map_err(to_pyerr) })
}
```

Use this when Python callers should receive a coroutine immediately and `await` it without blocking the current Python thread.

### Node/Bun async wrapper

```rust
use crate::runtime::spawn_result;

#[napi]
pub async fn get_entry(&self, key: String) -> napi::Result<Option<String>> {
    let inner = self.inner.clone();
    spawn_result(
        async move { inner.get_entry(&key).await },
        |error| to_napi_err(format!("Runtime error: {error}")),
        to_napi_err,
    )
    .await
}
```

Pass call-site-specific error mappers. Do not normalize all binding errors globally: C++, Node, and Python intentionally expose different error shapes.

## Guard command

Run the source guard from the repo root:

```powershell
uv run --project python-bindings python tools/runtime_gil_patterns/check_runtime_gil_patterns.py --repo-root .
```

Default mode fails only on unauthorized runtime constructors. It reports raw call-site patterns while the migration is incremental. To make raw direct `block_on`, `py.detach`, and `future_into_py` findings fail locally, add:

```powershell
uv run --project python-bindings python tools/runtime_gil_patterns/check_runtime_gil_patterns.py --repo-root . --strict-call-sites
```

Intentional allowlists:

- the shared runtime owner in `foundation/classic-shared-core/src/lib.rs`;
- tests and benches that explicitly exercise runtime behavior;
- helper modules that encapsulate an approved pattern.

## Review checklist

- New code does not call `Runtime::new()`, `Builder::new_multi_thread()`, `Builder::new_current_thread()`, or `#[tokio::main]` outside the shared runtime owner or explicit tests/benches.
- Sync bridge/binding code uses a surface helper rather than open-coded runtime handoff.
- Python sync methods release the GIL for blocking or CPU-heavy work after extracting Python data.
- Python true async methods return a coroutine via `future_into_py` instead of blocking.
- Error mapping remains local to the binding surface and preserves existing public contracts.
