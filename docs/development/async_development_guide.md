# Async Development Guide

This guide covers async patterns and best practices for CLASSIC's Rust crates and the C++ bridge.

The Python runtime and the Python and Node bindings are retired (ADR-0010, in [`docs/adr/`](../adr/)). Async guidance for the retired Python runtime (AsyncBridge and its async-first scripts) lives under [`docs/archive/python-era/`](../archive/python-era) as historical record only; earlier revisions of this guide also carried it.

## Native Async Solution

CLASSIC uses one shared Tokio runtime owned by `foundation/classic-shared-core`. The **ONE RUNTIME RULE** means crates and bindings must use `classic_shared_core::get_runtime()` or a surface-specific helper that wraps it; they must not create additional runtimes.

Clippy enforces the rule. The workspace `clippy.toml` disallows `tokio::runtime::Runtime::new`, `Builder::new_multi_thread`, `Builder::new_current_thread` and `#[tokio::main]`, so `cargo clippy --workspace --all-targets --all-features -- -D warnings` (ci-rust `lint`) fails on any runtime constructed outside `classic-shared-core`. Because `#[tokio::test]` expands to a runtime builder, every test file that uses it starts with an inner `#![allow(clippy::disallowed_methods)]` and a one-line reason; a new test file fails clippy until it opts in. The few test and bench sites that construct a runtime directly carry a targeted `#[allow(clippy::disallowed_methods)]` with a reason.

### The ONE RUNTIME RULE

**All Rust crates MUST use the shared runtime instead of constructing their own `tokio::runtime::Runtime`.**

```rust
// Shared owner: foundation/classic-shared-core/src/lib.rs
pub fn get_runtime() -> &'static tokio::runtime::Runtime {
    &RUNTIME
}

// Sync CXX bridge adapter: use the bridge helper.
fn bridge_call(arg: &str) -> Result<String, String> {
    crate::runtime_support::block_on_result(core_async_call(arg))
}
```

### Benefits of Native Async Solution

1. **Single runtime** - Prevents nested-runtime errors and cross-runtime deadlocks.
2. **Thin adapters** - Bindings centralize runtime handoff without reimplementing business logic.
3. **Better debugging** - Runtime ownership is explicit and process-wide.
4. **Full Rust async ecosystem** - All Tokio features remain available through the shared runtime.

## Common Async Patterns

### Pattern 1: Async Function with Error Handling

```rust
pub async fn process_file(path: &Path) -> Result<String> {
    let content = tokio::fs::read_to_string(path).await?;
    Ok(content)
}
```

### Pattern 2: Parallel Async Operations

```rust
pub async fn process_multiple_files(paths: &[PathBuf]) -> Result<Vec<String>> {
    let futures = paths.iter().map(|path| tokio::fs::read_to_string(path));
    let results = futures::future::try_join_all(futures).await?;
    Ok(results)
}
```

### Pattern 3: Sync Context Calling Async

```rust
// Use the shared runtime; never construct a second one.
pub fn sync_function() -> Result<String> {
    classic_shared_core::get_runtime().block_on(async {
        async_operation().await
    })
}
```

In the C++ bridge, prefer `crate::runtime_support::block_on(...)` or `block_on_result(...)` over a direct `get_runtime().block_on(...)`.

## Best Practices

### ✅ DO: Use the shared runtime through the surface helper

```rust
// ✅ CORRECT for a synchronous adapter
pub fn process_data(data: String) -> Result<String> {
    crate::runtime_support::block_on_result(async move {
        async_operation(data).await
    })
}
```

### ❌ DON'T: Create multiple runtimes

```rust
// ❌ WRONG - Violates ONE RUNTIME RULE
pub fn process_data(data: String) -> Result<String> {
    let runtime = tokio::runtime::Runtime::new()?;  // Don't do this!
    runtime.block_on(async move {
        async_operation(data).await
    })
}
```

### ❌ DON'T: Block on async from within async context

```rust
// ❌ WRONG - Causes nested runtime errors
pub async fn nested_async() -> Result<String> {
    classic_shared_core::get_runtime().block_on(async {  // Don't do this!
        async_operation().await
    })
}

// ✅ CORRECT - Just await directly
pub async fn nested_async() -> Result<String> {
    async_operation().await
}
```

## Troubleshooting

### Issue: "Cannot start a runtime from within a runtime"

**Cause**: Calling `block_on()` from within an async context
**Solution**: Use `.await` directly instead of `block_on()`

### Issue: Deadlocks in async code

**Cause**: Multiple runtimes or improper lock usage
**Solution**:
- Follow ONE RUNTIME RULE - use `classic_shared_core::get_runtime()`
- Use async-aware locks (`tokio::sync::Mutex` instead of `std::sync::Mutex`)

## Common Anti-Patterns to Avoid

- ❌ Multiple Tokio runtimes → ✅ `classic_shared_core::get_runtime()`
- ❌ `block_on()` in async context → ✅ Direct `.await`
