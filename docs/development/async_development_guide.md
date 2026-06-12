# Async Development Guide

This guide covers async patterns and best practices for CLASSIC's Python and Rust codebases.

Note: the Python application-layer examples in this document refer to the legacy Python runtime/orchestration model. The active product path now centers on Rust core crates in `ClassicLib-rs/` plus the maintained C++ frontends and binding layers. Use this guide as historical reference for legacy Python runtime patterns, not as the default workflow for new product work.

## Python Async Patterns

### AsyncBridge Usage - When and Where

AsyncBridge provides sync-to-async bridging, but it should be used **ONLY in specific contexts**:

#### ✅ Appropriate AsyncBridge Usage

1. **GUI Workers** (Qt threads, PySide6 slots) - PRIMARY USE CASE
   ```python
   class CrashLogsScanWorker(QThread):
       def _perform_scan(self):
           bridge = AsyncBridge.get_instance()
           result = bridge.run_async(executor.execute_scan())
   ```

2. **Testing and Benchmarking** isolated async functions
   ```python
   def test_async_function():
       sync_wrapper = create_sync_wrapper(async_function)
       result = sync_wrapper()  # Works via asyncio.run() in CLI mode
   ```

3. **One-off operations** in sync initialization contexts
   ```python
   def __init__(self):
       bridge = AsyncBridge.get_instance()
       self._core = bridge.run_async(get_async_core())
   ```

#### ❌ Inappropriate AsyncBridge Usage

1. **Production CLI main flow** - Creates new event loop per call (inefficient)
   ```python
   # ❌ WRONG - Each call creates a new event loop
   def main():
       result1 = create_sync_wrapper(async_func1)()  # New loop
       result2 = create_sync_wrapper(async_func2)()  # New loop
   ```

2. **When already in async context** - Use await directly
   ```python
   # ❌ WRONG - Already in async context
   async def process():
       sync_wrapper = create_sync_wrapper(async_operation)
       result = sync_wrapper()  # Unnecessary wrapper

   # ✅ CORRECT
   async def process():
       result = await async_operation()
   ```

3. **Repeated operations in CLI** - Use async-first pattern instead
   ```python
   # ❌ WRONG - Multiple event loop creations
   for file in files:
       content = read_file_sync(file)  # New loop each iteration

   # ✅ CORRECT - Single event loop
   async def main():
       io_core = FileIOCore()
       for file in files:
           content = await io_core.read_file(file)  # Same loop
   ```

### Async-First Pattern for CLI

Production CLI code should use the **async-first pattern** with a single `asyncio.run()` call:

```python
# Example: CLASSIC_ScanLogs.py (CORRECT PATTERN)
async def main() -> None:
    """Main CLI entry point - Async-First."""
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    config = create_config_from_args(parse_arguments())
    executor = ScanLogsExecutor(config)

    # Direct async calls - single event loop
    result = await executor.execute_scan()

if __name__ == "__main__":
    # Single asyncio.run() at entry point only
    asyncio.run(main())
```

#### Why Async-First?
- **Performance**: Single event loop vs creating/destroying loops per call
- **Simplicity**: Natural async/await patterns
- **Efficiency**: No AsyncBridge overhead in CLI contexts
- **Best practice**: Follows Python async conventions

### Context-Aware Code - GUI vs CLI

For code used by both GUI and CLI, provide separate interfaces:

```python
# GUI interface - Uses sync wrapper
def game_combined_result() -> tuple[str, list]:
    """Sync adapter for GUI contexts."""
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(generate_game_combined_result_async())

# CLI interface - Direct async
async def generate_game_combined_result_async() -> tuple[str, list]:
    """Async method for CLI contexts."""
    core = get_game_integrity_orchestrator_core()
    return await core.generate_combined_result()

# Usage
# GUI:
result = game_combined_result()  # Uses AsyncBridge

# CLI:
result = await generate_game_combined_result_async()  # Direct async
```

### Use AsyncBridge for Sync Contexts (GUI Only)

```python
# Use AsyncBridge in GUI workers only
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# For CLI, use async-first pattern instead (see above)
```

### Use FileIOCore for File Operations

```python
# Use FileIOCore for file operations
from ClassicLib.FileIOCore import FileIOCore
io_core = FileIOCore()
content = await io_core.read_file(path)
```

### Batch Load Settings for Performance

```python
# Batch load settings for performance
from ClassicLib.YamlSettingsCache import yaml_cache
values = yaml_cache.batch_get_settings([
    (str, YAML.Settings, "key1"),
    (bool, YAML.Settings, "key2")
])
```

### Transparent Rust Acceleration

```python
# Transparent acceleration - automatic Rust usage
from ClassicLib.ScanLog.Parser import find_segments  # Uses Rust LogParser if available
from ClassicLib.FileIOCore import FileIOCore  # Uses RustFileIOCore if available

# Check Rust status programmatically
from ClassicLib.integration.status import get_rust_component_status, print_rust_status
status = get_rust_component_status()
if status["acceleration_active"]:
    print(f"🚀 {status['active_count']}/{status['total_count']} components accelerated")

# Force Python fallback (for debugging/testing)
import os
os.environ["CLASSIC_DISABLE_RUST"] = "1"

# Use integration factory functions
from ClassicLib.integration.factory import get_parser, get_formid_analyzer
parser = get_parser()  # RustLogParser with automatic fallback
analyzer = get_formid_analyzer(yamldata, show_values, db_exists)
```

## Native Async Solution

CLASSIC uses one shared Tokio runtime owned by `foundation/classic-shared-core`. The **ONE RUNTIME RULE** means crates and bindings must use `classic_shared_core::get_runtime()` or a surface-specific helper that wraps it; they must not create additional runtimes.

For the current decision table and helper snippets for CXX, PyO3, NAPI-RS, and UI/TUI surfaces, see [`runtime_gil_patterns.md`](runtime_gil_patterns.md).

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

// Sync PyO3 adapter: release the GIL while blocking on async Rust.
fn process_data(py: Python<'_>, data: String) -> PyResult<String> {
    classic_shared::without_gil_block_on(py, || async move {
        async_operation(data).await
    })
    .map_err(to_pyerr)
}
```

### Benefits of Native Async Solution

1. **Single runtime** - Prevents nested-runtime errors and cross-runtime deadlocks.
2. **Thin adapters** - Bindings centralize runtime handoff without reimplementing business logic.
3. **Better debugging** - Runtime ownership is explicit and process-wide.
4. **Full Rust async ecosystem** - All Tokio features remain available through the shared runtime.

## Common Async Patterns

### Pattern 1: Async Function with Error Handling

```python
# Python
async def process_file(path: Path) -> str:
    try:
        io_core = FileIOCore()
        content = await io_core.read_file(path)
        return content
    except Exception as e:
        msg_error(f"Failed to read file: {e}")
        raise
```

```rust
// Rust
pub async fn process_file(path: &Path) -> Result<String> {
    let content = tokio::fs::read_to_string(path).await?;
    Ok(content)
}
```

### Pattern 2: Parallel Async Operations

```python
# Python
async def process_multiple_files(paths: list[Path]) -> list[str]:
    io_core = FileIOCore()
    tasks = [io_core.read_file(path) for path in paths]
    results = await asyncio.gather(*tasks)
    return results
```

```rust
// Rust
pub async fn process_multiple_files(paths: &[PathBuf]) -> Result<Vec<String>> {
    let futures = paths.iter().map(|path| tokio::fs::read_to_string(path));
    let results = futures::future::try_join_all(futures).await?;
    Ok(results)
}
```

### Pattern 3: Sync Context Calling Async

```python
# Python - Use AsyncBridge
from ClassicLib.AsyncBridge import AsyncBridge

def sync_function():
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_operation())
    return result
```

```rust
// Rust - Use get_runtime()
pub fn sync_function() -> Result<String> {
    classic_shared::get_runtime().block_on(async {
        async_operation().await
    })
}
```

### Pattern 4: PyO3 Sync Function with Async Rust

```rust
// Rust PyO3 binding
#[pyfunction]
pub fn parse_log(py: Python<'_>, path: String) -> PyResult<AnalysisResult> {
    let path = PathBuf::from(path);
    classic_shared::without_gil_block_on(py, || async move {
        parse_log_async(&path).await
    })
    .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))
}
```

Use `future_into_py(py, async move { ... })` instead when the Python API should return a true coroutine.

## Best Practices

### ✅ DO: Use AsyncBridge in Python

```python
# ✅ CORRECT
from ClassicLib.AsyncBridge import AsyncBridge

def sync_wrapper():
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(async_operation())
```

### ❌ DON'T: Use asyncio.run() directly

```python
# ❌ WRONG - Can cause issues with existing event loops
def sync_wrapper():
    return asyncio.run(async_operation())
```

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

### ✅ DO: Release the GIL for blocking or parallel work

```rust
// ✅ CORRECT - Release GIL for CPU-intensive or blocking async work
#[pyfunction]
pub fn parallel_operation(py: Python<'_>, data: Vec<String>) -> PyResult<Vec<String>> {
    classic_shared::without_gil_block_on(py, || async move {
        process_in_parallel(data).await
    })
    .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))
}
```

### ❌ DON'T: Block on async from within async context

```rust
// ❌ WRONG - Causes nested runtime errors
pub async fn nested_async() -> Result<String> {
    classic_shared::get_runtime().block_on(async {  // Don't do this!
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
- Follow ONE RUNTIME RULE - use `classic_shared::get_runtime()`
- Use async-aware locks (`tokio::sync::Mutex` instead of `std::sync::Mutex`)

### Issue: GIL-related performance issues

**Cause**: Holding GIL during CPU-intensive operations
**Solution**: Use `classic_shared::without_gil(...)` or `classic_shared::without_gil_block_on(...)` after extracting Python data.

```rust
classic_shared::without_gil_block_on(py, || async {
    expensive_operation().await
})
```

## Common Anti-Patterns to Avoid

- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Multiple Tokio runtimes → ✅ `classic_shared::get_runtime()`
- ❌ Manual event loops → ✅ AsyncBridge or get_runtime()
- ❌ `block_on()` in async context → ✅ Direct `.await`
- ❌ Holding GIL during blocking async → ✅ `classic_shared::without_gil_block_on(...)`
