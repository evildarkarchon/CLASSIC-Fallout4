# Native Async Solution for CLASSIC

This document describes the current async rule set for maintained CLASSIC Rust code.

## Core rule

CLASSIC uses one shared Tokio runtime in Rust core facilities. Do not create a separate runtime per binding or per consumer.

## Practical pattern

- Keep async I/O and concurrency inside Rust core crates.
- Expose simple synchronous or task-oriented wrapper APIs at Python, Node, and C++ boundaries when appropriate.
- Do not use `pyo3-asyncio`.

## Typical shape

```rust
use pyo3::prelude::*;

#[pyclass]
struct ExampleBinding {
    inner: ExampleCore,
}

#[pymethods]
impl ExampleBinding {
    fn run(&self) -> PyResult<String> {
        let runtime = classic_shared_core::runtime::get_runtime();
        runtime.block_on(self.inner.run_async())
    }
}
```

The exact helper used for runtime access may vary by crate, but the design rule does not: reuse the shared runtime.

## Why this pattern

- avoids per-binding runtime drift
- keeps async complexity in Rust core
- gives bindings a smaller surface to maintain
- aligns Python, Node, and C++ consumers around the same implementation

## Related docs

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
- `docs/development/pyo3_integration_patterns.md`
