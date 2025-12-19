# Rust Acceleration & Troubleshooting Guide

This guide covers monitoring, debugging, and troubleshooting Rust acceleration in CLASSIC.

## Performance Monitoring

### Check Rust Status

```python
# Check Rust status
from ClassicLib.integration.status import print_rust_status
print_rust_status()  # Detailed component status

# Programmatic status check
from ClassicLib.integration.status import get_rust_component_status
status = get_rust_component_status()
print(f"Active: {status['active_count']}/{status['total_count']}")

# Check specific component
from ClassicLib.integration.status import is_rust_accelerated
if is_rust_accelerated("parser"):
    print("🚀 Parser using Rust acceleration")
```

### Performance Benefits

| Component | Python Time | Rust Time | Speedup |
|-----------|-------------|-----------|---------|
| Log Parsing | 2-3 seconds | 200-300ms | 10x |
| FormID Analysis | 250ms/1000 IDs | 10ms/1000 IDs | 25x |
| Pattern Matching | 100ms/scan | 5ms/scan | 20x |
| File I/O | 50ms/file | 5ms/file | 10x |
| DDS Processing | 20ms/file | 0.5ms/file | 40x |
| Record Scanning | 150ms/scan | 3-4ms/scan | 40x |

## Environment Configuration

### Enable Rust Debugging

```bash
# Enable Rust debugging
export RUST_LOG=debug
export RUST_BACKTRACE=1

# Force Python fallback (for testing/debugging)
export CLASSIC_DISABLE_RUST=1

# Check if Rust is available without running app
python -c "import classic_core; print('Rust available')"
```

### Verify Rust Acceleration

```bash
# Verify Rust is working
uv run python -c "import classic_core; print(f'Rust version: {classic_core.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

## Common Issues and Solutions

### 1. Module not found

**Symptom**: `ModuleNotFoundError: No module named 'classic_core'`

**Cause**: Rust extension not built or installed

**Solution**: Use build method 1 (recommended) to update .pyd

```bash
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall
```

### 2. Classes not exported from module

**Symptom**: `AttributeError: module 'classic_core' has no attribute 'MyClass'`

**Cause**: Crate built as `rlib` only (not `cdylib`)

**Solution**: Ensure crate is built as `cdylib`

```toml
[lib]
crate-type = ["cdylib", "rlib"]  # Need BOTH!
```

### 3. Old .pyd loads

**Symptom**: Changes not reflected, old code runs

**Cause**: Python caching stale module

**Solution**: Remove from site-packages before editable install

```bash
rm .venv/Lib/site-packages/classic_core.pyd
uv pip install -e . --force-reinstall
```

### 4. PyO3 conversion errors

**Symptom**: `TypeError: argument must be X, not Y`

**Cause**: Type mismatch between Python and Rust

**Solution**: Use direct attribute access or pre-convert
- Rust components expect specific data types
- Check logs for conversion errors
- Use explicit type conversions

### 5. Changes not reflected

**Symptom**: Code changes don't appear after rebuild

**Cause**: Old build artifacts

**Solution**: Use `--force-reinstall` and verify timestamp

```python
import classic_core
print(f"Version: {classic_core.__version__}")
```

### 6. Performance not improving

**Symptom**: No speedup with Rust acceleration

**Cause**: Rust acceleration not loading

**Solution**: Check component status

```python
from ClassicLib.integration.status import RUST_AVAILABLE
print(f"Available components: {RUST_AVAILABLE}")
```

### 7. Build failures

**Symptom**: `cargo build` or `maturin build` fails

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

**Symptom**: "Cannot start a runtime from within a runtime"

**Cause**: Multiple Tokio runtimes or improper async patterns

**Solutions**:
- Use `py.detach()` to release GIL before parallel work
- Use `Python::attach()` to reacquire GIL in worker threads
- Avoid `get_runtime().block_on()` when already in a Python context
- Use synchronous I/O for now in contexts where async causes conflicts
- Follow **ONE RUNTIME RULE** - all crates use `classic_shared::get_runtime()`

## Debugging Techniques

### 1. Enable Rust Logging

```bash
export RUST_LOG=debug
uv run python CLASSIC_Interface.py
```

### 2. Enable Backtraces

```bash
export RUST_BACKTRACE=1
uv run python CLASSIC_Interface.py
```

### 3. Check Module Import

```python
import sys
import classic_core

print(f"Module path: {classic_core.__file__}")
print(f"Version: {classic_core.__version__}")
print(f"Attributes: {dir(classic_core)}")
```

### 4. Test Individual Components

```python
# Test YAML operations
from classic_core import yaml
ops = yaml.RustYamlOperations()
result = ops.parse_yaml("key: value")
print(f"YAML parsed: {result}")

# Test file I/O
from classic_core import file_io
io_core = file_io.RustFileIOCore()
content = io_core.read_file_sync("/path/to/file")
print(f"File read: {len(content)} bytes")
```

### 5. Compare Python vs Rust Performance

```python
import time
from ClassicLib.ScanLog.Parser import find_segments
from ClassicLib.integration.status import is_rust_accelerated

# Check if using Rust
if is_rust_accelerated("parser"):
    print("Using Rust parser")
else:
    print("Using Python parser")

# Time the operation
start = time.time()
result = find_segments(log_content)
elapsed = time.time() - start
print(f"Parse time: {elapsed:.3f}s")
```

## Best Practices

### 1. Always Use Recommended Build Method

Use maturin build for reliable builds:

```bash
maturin build --release --out classic-core/dist
uv pip install classic-core/dist/classic_*.whl --force-reinstall
```

### 2. Clean Before Building

```bash
cargo clean
maturin build --release --out classic-core/dist
```

### 3. Verify After Install

```python
import classic_core
print(f"Version: {classic_core.__version__}")

from ClassicLib.integration.status import print_rust_status
print_rust_status()
```

### 4. Use Environment Variables for Testing

```bash
# Test with Rust disabled
export CLASSIC_DISABLE_RUST=1
uv run python CLASSIC_Interface.py

# Test with Rust enabled (default)
unset CLASSIC_DISABLE_RUST
uv run python CLASSIC_Interface.py
```

### 5. Check Logs for Errors

```bash
# Enable verbose logging
export RUST_LOG=debug
export RUST_BACKTRACE=full
uv run python CLASSIC_Interface.py 2>&1 | tee debug.log
```

## Performance Profiling

### Profile Rust Code

```bash
# Build with profiling symbols
cargo build --release --profile profiling

# Run with profiler
cargo flamegraph --bin classic-cli
```

### Profile Python-Rust Integration

```python
import cProfile
import pstats

# Profile a function that uses Rust
profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = process_with_rust_acceleration()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Additional Resources

- **[Rust Usage Guide](../rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](../performance_monitoring.md)** - Detailed performance monitoring
- **[Troubleshooting Guide](../troubleshooting_rust.md)** - Comprehensive troubleshooting
- **[Development Guide](../development_with_rust.md)** - Develop with Rust components
- **[PyO3 Integration](pyo3_integration_patterns.md)** - PyO3 patterns and best practices
