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
