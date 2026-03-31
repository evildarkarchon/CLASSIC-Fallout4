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

## Native Async Solution (No PyO3-asyncio)

CLASSIC uses a native async solution that's more reliable and performant. The **ONE RUNTIME RULE** ensures all crates share a single global Tokio runtime to prevent deadlocks.

### The ONE RUNTIME RULE

**All Rust crates MUST use `classic_shared::get_runtime()` to access the shared Tokio runtime.**

```rust
// In classic-shared/src/runtime.rs - shared across all crates
pub(crate) static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    let worker_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(worker_threads)
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime")
});

pub fn get_runtime() -> &'static Runtime {
    &RUNTIME
}

// In other crates - use classic_shared::get_runtime()
#[pyfunction]
fn process_data(data: String) -> PyResult<String> {
    classic_shared::get_runtime().block_on(async move {
        // Full async Rust operations here
        async_operation(data).await
    })
}
```

### Benefits of Native Async Solution

1. **No PyO3-asyncio dependency** - Simpler, more maintainable
2. **Single runtime** - Prevents deadlocks and nested runtime errors
3. **Better performance** - Direct access to Tokio runtime
4. **Easier debugging** - No complex macro expansions
5. **Full Rust async ecosystem** - All Tokio features available

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

### Pattern 4: PyO3 Function with Async Rust

```rust
// Rust PyO3 binding
#[pyfunction]
pub fn parse_log(py: Python<'_>, path: String) -> PyResult<AnalysisResult> {
    py.allow_threads(|| {
        classic_shared::get_runtime()
            .block_on(async move {
                parse_log_async(&PathBuf::from(path)).await
            })
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))
    })
}
```

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

### ✅ DO: Use get_runtime() in Rust

```rust
// ✅ CORRECT
pub fn process_data(data: String) -> Result<String> {
    classic_shared::get_runtime().block_on(async move {
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

### ✅ DO: Release GIL for parallel work

```rust
// ✅ CORRECT - Release GIL for CPU-intensive work
#[pyfunction]
pub fn parallel_operation(py: Python<'_>, data: Vec<String>) -> PyResult<Vec<String>> {
    py.allow_threads(|| {
        classic_shared::get_runtime()
            .block_on(async move {
                // Parallel async operations here
                process_in_parallel(data).await
            })
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))
    })
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
**Solution**: Use `py.allow_threads()` to release GIL

```rust
py.allow_threads(|| {
    // CPU-intensive work here without GIL
    classic_shared::get_runtime().block_on(async {
        expensive_operation().await
    })
})
```

## Common Anti-Patterns to Avoid

- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Multiple Tokio runtimes → ✅ `classic_shared::get_runtime()`
- ❌ Manual event loops → ✅ AsyncBridge or get_runtime()
- ❌ `block_on()` in async context → ✅ Direct `.await`
- ❌ Holding GIL during async → ✅ `py.allow_threads()`
