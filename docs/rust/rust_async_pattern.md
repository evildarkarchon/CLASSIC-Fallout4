# Native Async Solution for CLASSIC

This document describes the current async rule set for maintained CLASSIC Rust code.

## Core rule

CLASSIC uses one shared Tokio runtime in Rust core facilities. Do not create a separate runtime per binding or per consumer.

## Practical pattern

- Keep async I/O and concurrency inside Rust core crates.
- Expose simple synchronous or task-oriented wrapper APIs at the C++ bridge boundary when appropriate.

## Typical shape

```rust
// A synchronous bridge entry point over async Rust core work.
fn example_run(inner: &ExampleCore) -> Result<String, String> {
    let runtime = classic_shared_core::runtime::get_runtime();
    runtime.block_on(inner.run_async()).map_err(|error| error.to_string())
}
```

The exact helper used for runtime access may vary by crate, but the design rule does not: reuse the shared runtime.

## Why this pattern

- avoids per-binding runtime drift
- keeps async complexity in Rust core
- gives bindings a smaller surface to maintain
- aligns every consumer around the same implementation

## Related docs

- `docs/development/rust_workspace_architecture.md`
- `docs/rust/development_with_rust.md`
