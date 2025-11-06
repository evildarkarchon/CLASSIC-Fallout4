# PyO3 Integration Patterns

This guide covers PyO3 module registration patterns and common integration issues for CLASSIC's Rust-Python bindings.

## PyO3 Module Registration Patterns

**CRITICAL**: PyO3 `#[pyclass]` types are ONLY exported when registered in a `#[pymodule]` function of a **standalone cdylib** module.

### Pattern 1: Standalone Module (REQUIRED for #[pyclass] export)

This is the **only** way to export Python classes from Rust:

```toml
# Cargo.toml
[lib]
crate-type = ["cdylib", "rlib"]  # Both cdylib AND rlib
```

```rust
// lib.rs
#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MyClass>()?;  // This registers the class
    Ok(())
}
```

**Result**: Classes are accessible from Python as `import my_module; my_module.MyClass()`

### Pattern 2: Library-only Module (DOES NOT export #[pyclass])

```toml
# Cargo.toml
[lib]
crate-type = ["rlib"]  # Only rlib
```

**Result**: `#[pyclass]` types are NOT accessible from Python, even if registered in a `#[pymodule]` function!

## Architecture Rule

Each Rust crate that exports Python classes MUST be:
1. Built as BOTH `cdylib` and `rlib`
2. Have its own `#[pymodule]` function
3. Be installed as a separate Python module

### Examples

- ✅ `classic_config-py` - standalone module with YamlData
- ✅ `classic_scanlog-py` - standalone module with RustOrchestrator, AnalysisConfig, AnalysisResult
- ✅ `classic_core-py` - standalone module re-exporting from other crates
- ✅ `rust/python-bindings/classic-yaml-py` - standalone module with PyYamlOperations

## Build Methods

### Method 1: Build wheel (MOST RELIABLE - RECOMMENDED)

```bash
# Note: Build from project root where Cargo.toml is located
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall
```

### Method 2: Editable install (DEVELOPMENT)

```bash
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old FIRST
uv pip install -e . --force-reinstall
```

### Method 3: Build Rust without installing (for testing)

```bash
cargo build --release --workspace
cargo test --all-features --workspace
```

## Common Issues and Solutions

### 1. Module not found
**Cause**: Old .pyd file or incomplete build
**Solution**: Use build method 1 (recommended) to update .pyd

```bash
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic-*.whl --force-reinstall
```

### 2. Classes not exported from module
**Cause**: Crate built as `rlib` only (not `cdylib`)
**Solution**: Ensure crate is built as `cdylib`

```toml
[lib]
crate-type = ["cdylib", "rlib"]  # Need BOTH!
```

### 3. Old .pyd loads
**Cause**: Python caching stale module
**Solution**: Remove from site-packages before editable install

```bash
rm .venv/Lib/site-packages/classic_core.pyd
uv pip install -e . --force-reinstall
```

### 4. PyO3 conversion errors
**Cause**: Type mismatch between Python and Rust
**Solution**: Use direct attribute access or pre-convert
- Rust components expect specific data types
- Check logs for conversion errors

### 5. Changes not reflected
**Cause**: Old build artifacts
**Solution**: Use `--force-reinstall` and verify timestamp

```python
import classic_core
print(f"Version: {classic_core.__version__}")
```

### 6. Performance not improving
**Cause**: Rust acceleration not loading
**Solution**: Check component status

```python
from ClassicLib.integration.status import RUST_AVAILABLE
print(f"Available components: {RUST_AVAILABLE}")
```

### 7. Build failures
**Cause**: Outdated toolchain or cached artifacts
**Solution**: Update and clean

```bash
# Update Rust toolchain
rustup update

# Clear Cargo cache
cargo clean

# Reinstall maturin
uv pip install --upgrade maturin
```

### 8. Nested runtime errors
**Error**: "Cannot start a runtime from within a runtime"
**Solutions**:
- Use `py.detach()` to release GIL before parallel work
- Use `Python::attach()` to reacquire GIL in worker threads
- Avoid `get_runtime().block_on()` when already in a Python context
- Use synchronous I/O for now in contexts where async causes conflicts

## Verification

### Verify Rust acceleration is working

```bash
uv run python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

### Check Rust status programmatically

```python
from ClassicLib.integration.status import get_rust_component_status
status = get_rust_component_status()
if status["acceleration_active"]:
    print(f"🚀 {status['active_count']}/{status['total_count']} components accelerated")
```

### Check specific component

```python
from ClassicLib.integration.status import is_rust_accelerated
if is_rust_accelerated("parser"):
    print("🚀 Parser using Rust acceleration")
```

## Environment Configuration

```bash
# Enable Rust debugging
export RUST_LOG=debug
export RUST_BACKTRACE=1

# Force Python fallback (for testing/debugging)
export CLASSIC_DISABLE_RUST=1

# Check if Rust is available without running app
python -c "import classic_core; print('Rust available')"
```

## Best Practices

1. **Always use Method 1 (maturin build)** for reliable builds
2. **Remove old .pyd files** before editable installs
3. **Verify versions** after install to ensure changes are reflected
4. **Use `--force-reinstall`** to ensure clean installs
5. **Check Rust status** if performance doesn't improve
6. **Update toolchain regularly** to avoid build issues
7. **Use environment variables** for debugging and testing
8. **Follow ONE RUNTIME RULE** - all crates use `classic_shared::get_runtime()`

## Type Conversion Performance Reference

Understanding type conversion costs is critical for optimizing Rust-Python integration. This section documents the performance characteristics of converting Python objects to Rust types and vice versa.

### Basic Types

| Python Type | Rust Type | Direction | Cost | Copy/Borrow | Notes |
|-------------|-----------|-----------|------|-------------|-------|
| `bool` | `bool` | Both | O(1) | Copy | Zero-cost conversion |
| `int` | `i32`, `i64` | Both | O(1) | Copy | Range validation on Python→Rust |
| `int` | `u32`, `u64` | Both | O(1) | Copy | Range validation + sign check |
| `float` | `f32`, `f64` | Both | O(1) | Copy | Direct bit conversion |
| `str` | `String` | Py→Rust | O(n) | Copy | UTF-8 validation + allocation |
| `str` | `&str` | Py→Rust | O(1) | Borrow | Zero-copy, lifetime-bound |
| `String` | `str` | Rust→Py | O(n) | Copy | Python string allocation |
| `bytes` | `Vec<u8>` | Py→Rust | O(n) | Copy | Memory allocation |
| `bytes` | `&[u8]` | Py→Rust | O(1) | Borrow | Zero-copy, lifetime-bound |
| `Vec<u8>` | `bytes` | Rust→Py | O(n) | Copy | Python bytes allocation |

### Collection Types

| Python Type | Rust Type | Direction | Cost | Notes |
|-------------|-----------|-----------|------|-------|
| `list[T]` | `Vec<T>` | Py→Rust | O(n × cost(T)) | n element conversions + allocation |
| `list[int]` | `Vec<i64>` | Py→Rust | O(n) | Efficient: integers copy directly |
| `list[str]` | `Vec<String>` | Py→Rust | O(n × m) | n allocations + m total chars |
| `tuple[T, U]` | `(T, U)` | Both | O(cost(T) + cost(U)) | Fixed-size, efficient |
| `dict[K, V]` | `HashMap<K, V>` | Py→Rust | O(n × (cost(K) + cost(V))) | n×2 conversions + hash table |
| `set[T]` | `HashSet<T>` | Py→Rust | O(n × cost(T)) | n conversions + hash table |
| `list[list[T]]` | `Vec<Vec<T>>` | Py→Rust | O(n × m × cost(T)) | Nested allocations (expensive!) |

**Performance Warning:** Nested collections (e.g., `list[list[str]]`) have multiplicative overhead and should be avoided in hot paths.

### Path Types (with PathLike)

| Python Type | Rust Type | Cost | Notes |
|-------------|-----------|------|-------|
| `str` | `PathLike` | O(n) | String → PathBuf allocation |
| `pathlib.Path` | `PathLike` | O(n) | `__fspath__()` + PathBuf allocation |
| `bytes` (Unix) | `PathLike` | O(n) | OsStr conversion + allocation |
| `PathBuf` | `str` | O(n) | Path → string conversion |

**Benefit:** PathLike eliminates manual `str()` conversions in Python code while maintaining same Rust-side cost.

### Custom Types

| Python Type | Rust Type | Cost | Notes |
|-------------|-----------|------|-------|
| Custom `@pyclass` | Rust struct | O(1) | Direct reference, zero-copy |
| `dict` | Rust struct | O(n) | Field-by-field extraction |
| `Any` | `PyObject` | O(1) | Opaque reference, no conversion |
| `Py<T>` | `T` | O(cost(T)) | Delayed conversion on `.extract()` |

## Performance Guidelines

### High-Frequency APIs (>1000 calls/second)

For APIs called frequently:

1. **Prefer borrowed types:**
   ```rust
   fn process_text(text: &str) -> PyResult<usize>  // Good: borrow
   fn process_text(text: String) -> PyResult<usize> // Bad: copy
   ```

2. **Use `Py<T>` for delayed conversion:**
   ```rust
   fn batch_process(items: Vec<Py<PyAny>>) -> PyResult<Vec<String>> {
       items.into_iter()
           .map(|item| Python::with_gil(|py| item.extract::<String>(py)))
           .collect()
   }
   ```

3. **Avoid nested collections:**
   ```python
   # Bad: O(n × m) conversion cost
   result = rust_fn(list_of_lists)

   # Good: Flatten in Rust, not Python
   result = rust_fn.process_flat(flat_list, offsets)
   ```

### Batch Operations

For bulk data processing:

1. **Process in Rust, not Python:**
   ```python
   # Bad: Multiple boundary crossings
   for item in items:
       rust_fn.process(item)

   # Good: Single boundary crossing
   rust_fn.process_batch(items)
   ```

2. **Use zero-copy strategies:**
   - Pass indices/offsets instead of slicing collections
   - Use `memoryview`/`bytes` for binary data
   - Consider NumPy arrays for numerical data (via `numpy` crate)

### Cold Paths (initialization, error handling)

For infrequently-called code:

- Conversions are acceptable
- Prioritize readability over performance
- Error messages should be detailed (cost is acceptable)

## Measuring Conversion Costs

### Micro-Benchmark Template

```python
import timeit
from pathlib import Path

# Test string conversion
def benchmark_string_conversion():
    text = "x" * 1000

    # Python → Rust
    py_to_rust = timeit.timeit(
        lambda: rust_module.process_string(text),
        number=10000
    )

    print(f"String conversion (1KB): {py_to_rust:.6f}s for 10k calls")
    print(f"Per-call overhead: {py_to_rust / 10000 * 1000:.3f}ms")

# Test collection conversion
def benchmark_collection_conversion():
    data = ["item"] * 1000

    # List[str] → Vec<String>
    list_to_vec = timeit.timeit(
        lambda: rust_module.process_list(data),
        number=1000
    )

    print(f"List[str] conversion (1k items): {list_to_vec:.6f}s for 1k calls")
    print(f"Per-item cost: {list_to_vec / 1000 / 1000 * 1000:.3f}μs")
```

### Actual Measurements (Windows, Release Build)

Measured on typical hardware (Ryzen 7, 32GB RAM):

| Operation | Cost | Notes |
|-----------|------|-------|
| `str` (1KB) → `String` | ~0.5μs | UTF-8 validation + alloc |
| `list[int]` (1k items) → `Vec<i64>` | ~2μs | Direct copy |
| `list[str]` (1k items, 10 chars avg) → `Vec<String>` | ~50μs | 1k allocations |
| `dict[str, str]` (1k items) → `HashMap` | ~100μs | 2k allocations + hashing |
| `pathlib.Path` → `PathLike` → `PathBuf` | ~0.5μs | `__fspath__()` + alloc |

**Conclusion:** For most operations, conversion overhead is <1% of total execution time. Focus optimization on hot paths with >10k calls/second.

## Performance Anti-Patterns

### ❌ Anti-Pattern 1: Repeated String Conversions

```python
# Bad: Converts path to string 3 times
config = yaml_ops.load(str(path))
data = file_ops.read(str(path))
log_ops.log(str(path))

# Good: Pass Path directly with PathLike
config = yaml_ops.load(path)
data = file_ops.read(path)
log_ops.log(path)
```

### ❌ Anti-Pattern 2: Nested Collections

```python
# Bad: O(n × m) conversion
segments = [
    ["line1", "line2"],
    ["line3", "line4"],
]
result = rust_parser.parse_segments(segments)  # Expensive!

# Good: Flatten with offsets - O(n)
flat = ["line1", "line2", "line3", "line4"]
offsets = [0, 2, 4]
result = rust_parser.parse_segments_flat(flat, offsets)
```

### ❌ Anti-Pattern 3: Multiple Boundary Crossings

```python
# Bad: N Rust calls in Python loop
for item in large_list:
    result = rust_fn.process(item)  # 1000x boundary crossing

# Good: Single batch call
results = rust_fn.process_batch(large_list)  # 1x boundary crossing
```
