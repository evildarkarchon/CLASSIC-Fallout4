# Troubleshooting Guide for CLASSIC Rust Components

## Overview

This comprehensive guide helps diagnose and resolve issues with CLASSIC's Rust acceleration components. It covers everything from installation problems to performance issues and provides step-by-step solutions for common scenarios.

## Quick Diagnosis

### Step 1: Check Rust Status

```python
from ClassicLib.RustIntegration import print_rust_status
print_rust_status()
```

### Step 2: Verify Installation

```python
# Check if Rust module can be imported
try:
    import classic_core
    print(f"✅ Rust module available (version: {classic_core.__version__})")
except ImportError as e:
    print(f"❌ Rust module not found: {e}")
```

### Step 3: Environment Check

```bash
# Check if environment variable is disabling Rust
echo $CLASSIC_DISABLE_RUST

# Check Python environment
python -c "import sys; print(f'Python: {sys.version}')"
python -c "import sys; print(f'Python path: {sys.executable}')"
```

## Installation Issues

### Issue: "No module named 'classic_core'"

This is the most common issue - the Rust module isn't installed or isn't in the Python path.

**Diagnosis:**
```python
import sys
print("Python paths:")
for path in sys.path:
    print(f"  {path}")

# Check for .pyd file
import os
for path in sys.path:
    pyd_path = os.path.join(path, "classic_core.pyd")
    if os.path.exists(pyd_path):
        print(f"Found: {pyd_path}")
        stat = os.stat(pyd_path)
        print(f"  Size: {stat.st_size} bytes")
        print(f"  Modified: {stat.st_mtime}")
```

**Solutions:**

1. **Install from wheel (Recommended):**
```bash
cd classic-rust
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall
```

2. **Editable install:**
```bash
cd classic-rust
uv pip install -e . --force-reinstall
```

3. **Check build dependencies:**
```bash
# Ensure maturin is installed
uv pip install maturin

# Ensure Rust is installed
rustc --version
cargo --version
```

4. **Manual verification:**
```bash
# Check if wheel was created
ls classic-rust/dist/

# Check if installation worked
python -c "import classic_core; print('Success!')"
```

### Issue: "ImportError: DLL load failed" (Windows)

This indicates a problem loading the Rust dynamic library on Windows.

**Diagnosis:**
```python
import os
import sys

# Check architecture compatibility
print(f"Python architecture: {sys.maxsize > 2**32 and '64-bit' or '32-bit'}")

# Check for VC++ redistributables
try:
    import _ctypes
    print("✅ _ctypes module available")
except ImportError:
    print("❌ _ctypes module not available - may need VC++ redistributables")
```

**Solutions:**

1. **Install Visual C++ Redistributables:**
   - Download and install Microsoft Visual C++ Redistributable for Visual Studio
   - Both x64 and x86 versions if unsure

2. **Check architecture match:**
```bash
# Rebuild for correct architecture
cd classic-rust
cargo clean
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall
```

3. **Environment variables:**
```bash
# Add to PATH if needed
set PATH=%PATH%;C:\path\to\rust\lib
```

### Issue: "Symbol not found" (Linux/macOS)

**Diagnosis:**
```bash
# Check shared library dependencies (Linux)
ldd .venv/lib/python*/site-packages/classic_core*.so

# Check shared library dependencies (macOS)
otool -L .venv/lib/python*/site-packages/classic_core*.so

# Check for missing symbols
nm -D .venv/lib/python*/site-packages/classic_core*.so | grep UNDEFINED
```

**Solutions:**

1. **Rebuild with correct target:**
```bash
cd classic-rust
cargo clean
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall
```

2. **Check Rust toolchain:**
```bash
rustup show
rustup update
```

3. **Install system dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install build-essential

# macOS
xcode-select --install
```

## Performance Issues

### Issue: "Rust components active but no performance improvement"

**Diagnosis:**
```python
import time
from ClassicLib.RustIntegration import get_rust_component_status, is_rust_accelerated

# Check component status
status = get_rust_component_status()
print(f"Components active: {status['active_count']}/{status['total_count']}")

# Test specific component
if is_rust_accelerated("parser"):
    print("✅ Parser using Rust")

    # Simple performance test
    test_data = ["test line"] * 1000
    start_time = time.perf_counter()
    # Simulate processing
    result = [line.upper() for line in test_data]
    end_time = time.perf_counter()

    print(f"Processing time: {(end_time - start_time) * 1000:.2f}ms")
else:
    print("❌ Parser using Python fallback")
```

**Solutions:**

1. **Verify component initialization:**
```python
from ClassicLib.RustIntegration import RUST_STATUS
print("Initialization status:")
for component, status in RUST_STATUS["initialized"].items():
    print(f"  ✅ {component}: {status}")

print("\nFailure reasons:")
for component, reason in RUST_STATUS["failed"].items():
    print(f"  ❌ {component}: {reason}")
```

2. **Check for blocking operations:**
```python
# Make sure we're not in a blocking context
import os
if os.environ.get("CLASSIC_DISABLE_RUST"):
    print("⚠️ Rust disabled by environment variable")
    # Remove to re-enable:
    # del os.environ["CLASSIC_DISABLE_RUST"]
```

3. **Warm-up performance:**
```python
# Rust performance improves after JIT warm-up
# Run several iterations to see improvement
import time

def test_performance(iterations=10):
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        # Your operation here
        test_data = ["test"] * 1000
        result = [item.strip() for item in test_data]
        end = time.perf_counter()
        times.append(end - start)

        if i < 3:
            print(f"Iteration {i+1}: {(end-start)*1000:.2f}ms (warm-up)")
        elif i == iterations-1:
            avg = sum(times[3:]) / len(times[3:])
            print(f"Average (after warm-up): {avg*1000:.2f}ms")

test_performance()
```

### Issue: High memory usage despite Rust acceleration

**Diagnosis:**
```python
import psutil
import gc
from ClassicLib.RustIntegration import get_rust_component_status

# Force garbage collection
gc.collect()

# Check memory usage
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024

print(f"Current memory usage: {memory_mb:.1f} MB")

status = get_rust_component_status()
if status['acceleration_active']:
    print(f"Expected with Rust: 80-120 MB")
    print(f"Expected without Rust: 300-500 MB")

    if memory_mb > 200:
        print("⚠️ Higher than expected memory usage")
        print("Possible causes:")
        print("- Large datasets in memory")
        print("- Memory leak in Python code")
        print("- Multiple instances running")
```

**Solutions:**

1. **Check for Python memory leaks:**
```python
import gc
import tracemalloc

# Start tracing
tracemalloc.start()

# Your operations here
# ... perform memory-intensive operations ...

# Get memory statistics
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")

# Stop tracing
tracemalloc.stop()

# Force cleanup
gc.collect()
```

2. **Check for large object retention:**
```python
import gc

# Find large objects
large_objects = []
for obj in gc.get_objects():
    try:
        size = len(obj) if hasattr(obj, '__len__') else 0
        if size > 1000:  # Objects with >1000 elements
            large_objects.append((type(obj).__name__, size))
    except:
        pass

# Sort by size
large_objects.sort(key=lambda x: x[1], reverse=True)
print("Largest objects in memory:")
for obj_type, size in large_objects[:10]:
    print(f"  {obj_type}: {size} elements")
```

## Runtime Issues

### Issue: "AsyncBridge integration problems"

**Diagnosis:**
```python
import asyncio
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.RustIntegration import get_rust_component_status

async def test_async_integration():
    """Test async integration with Rust components."""
    try:
        from ClassicLib.FileIOCore import FileIOCore
        io_core = FileIOCore()

        # Test async operation
        result = await io_core.read_file_async("test.txt")
        return "✅ Async integration working"
    except Exception as e:
        return f"❌ Async integration failed: {e}"

# Test with AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(test_async_integration())
print(result)

# Check status
status = get_rust_component_status()
print(f"Rust components: {status['active_count']}/{status['total_count']}")
```

**Solutions:**

1. **Check event loop state:**
```python
import asyncio

try:
    loop = asyncio.get_running_loop()
    print(f"✅ Event loop running: {type(loop)}")
except RuntimeError:
    print("ℹ️ No event loop running (normal for sync context)")

# Test AsyncBridge
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
print(f"✅ AsyncBridge instance: {type(bridge)}")
```

2. **Test Rust async integration:**
```python
# Test that Rust components work with AsyncBridge
async def rust_async_test():
    """Test Rust components in async context."""
    try:
        # Import and test a Rust component
        from ClassicLib.RustIntegration import get_parser
        parser = get_parser()

        # This should work even in async context
        test_data = ["test data"] * 10
        result = parser.find_segments(test_data, "Test", "TEST", "Game")
        return f"✅ Rust parser in async context: {len(result)} segments"
    except Exception as e:
        return f"❌ Rust async test failed: {e}"

from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
async_result = bridge.run_async(rust_async_test())
print(async_result)
```

### Issue: "GIL-related performance problems"

**Diagnosis:**
```python
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from ClassicLib.RustIntegration import is_rust_accelerated

def cpu_intensive_task():
    """Test GIL handling in Rust components."""
    # This should release the GIL if Rust is working properly
    test_data = ["test"] * 10000
    return sum(len(item) for item in test_data)

def test_gil_release():
    """Test if Rust components properly release the GIL."""
    if not is_rust_accelerated("parser"):
        print("⚠️ Rust parser not active - GIL test not applicable")
        return

    # Single-threaded test
    start_time = time.perf_counter()
    result1 = cpu_intensive_task()
    single_time = time.perf_counter() - start_time

    # Multi-threaded test
    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(cpu_intensive_task)
        future2 = executor.submit(cpu_intensive_task)
        result2 = future1.result() + future2.result()
    multi_time = time.perf_counter() - start_time

    print(f"Single-threaded: {single_time*1000:.2f}ms")
    print(f"Multi-threaded:  {multi_time*1000:.2f}ms")
    print(f"Speedup ratio: {single_time/multi_time:.2f}x")

    if single_time / multi_time > 1.5:
        print("✅ Good parallelization - GIL likely released")
    else:
        print("⚠️ Poor parallelization - GIL may not be released")

test_gil_release()
```

**Solutions:**

1. **Verify Rust component usage:**
```python
from ClassicLib.RustIntegration import print_rust_status
print_rust_status()

# Make sure critical components are active
critical_components = ["parser", "formid_analyzer", "file_io_core"]
for component in critical_components:
    from ClassicLib.RustIntegration import is_rust_accelerated
    if is_rust_accelerated(component):
        print(f"✅ {component} using Rust (GIL released)")
    else:
        print(f"❌ {component} using Python (GIL held)")
```

## Development Issues

### Issue: "Changes not reflected after rebuild"

**Diagnosis:**
```python
import classic_core
import os
import time

# Check module timestamp
module_file = classic_core.__file__
stat = os.stat(module_file)
mod_time = time.ctime(stat.st_mtime)

print(f"Module file: {module_file}")
print(f"Modified: {mod_time}")
print(f"Size: {stat.st_size} bytes")
print(f"Version: {getattr(classic_core, '__version__', 'unknown')}")

# Check if this is a stale import
import sys
if 'classic_core' in sys.modules:
    print("⚠️ Module already imported - may need to restart Python")
```

**Solutions:**

1. **Force module reload:**
```python
import sys
import importlib

# Remove from cache
if 'classic_core' in sys.modules:
    del sys.modules['classic_core']

# Clear import cache
importlib.invalidate_caches()

# Reimport
try:
    import classic_core
    print(f"✅ Reloaded: {classic_core.__version__}")
except ImportError as e:
    print(f"❌ Reload failed: {e}")
```

2. **Clean rebuild:**
```bash
# Complete clean rebuild
cd classic-rust
cargo clean
rm -rf dist/
rm -rf target/
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall

# Verify rebuild
python -c "import classic_core; print(f'New version: {classic_core.__version__}')"
```

3. **Check for multiple installations:**
```python
import classic_core
import sys

# Find all potential locations
potential_paths = []
for path in sys.path:
    import os
    pyd_file = os.path.join(path, "classic_core.pyd")
    so_file = os.path.join(path, "classic_core.so")

    if os.path.exists(pyd_file):
        potential_paths.append(pyd_file)
    if os.path.exists(so_file):
        potential_paths.append(so_file)

print(f"Found {len(potential_paths)} Rust modules:")
for path in potential_paths:
    stat = os.stat(path)
    print(f"  {path} (modified: {time.ctime(stat.st_mtime)})")

if len(potential_paths) > 1:
    print("⚠️ Multiple Rust modules found - may cause conflicts")
    print("Remove old versions before installing new one")
```

### Issue: "Debug symbols not available"

**Solutions:**

1. **Build with debug symbols:**
```bash
cd classic-rust
maturin develop --debug
```

2. **Enable Rust logging:**
```bash
export RUST_LOG=debug
export RUST_BACKTRACE=1
python your_script.py
```

3. **Use GDB/LLDB for debugging:**
```bash
# Compile with debug info
cd classic-rust
cargo build --debug

# Debug with GDB
gdb python
(gdb) run your_script.py
```

## Environment-Specific Issues

### Windows-Specific Issues

**Issue: Path length limitations**

**Solution:**
```bash
# Enable long path support in Windows 10/11
# Or use shorter paths for development
cd C:\dev\classic
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git classic
cd classic
```

**Issue: Antivirus interference**

**Solution:**
- Add Python environment directory to antivirus exclusions
- Add development directory to exclusions
- Temporarily disable real-time protection during builds

### Linux-Specific Issues

**Issue: Missing system dependencies**

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# CentOS/RHEL/Fedora
sudo yum install gcc gcc-c++ python3-devel
# or
sudo dnf install gcc gcc-c++ python3-devel

# Arch Linux
sudo pacman -S base-devel python
```

### macOS-Specific Issues

**Issue: Xcode command line tools**

**Solution:**
```bash
xcode-select --install
```

**Issue: Apple Silicon compatibility**

**Solution:**
```bash
# Ensure correct Rust target
rustup target add aarch64-apple-darwin
cd classic-rust
maturin build --release --target aarch64-apple-darwin --out dist
uv pip install dist/classic-*.whl --force-reinstall
```

## Advanced Diagnostics

### Memory Leak Detection

```python
import gc
import weakref
from ClassicLib.RustIntegration import get_parser

def test_memory_leaks():
    """Test for memory leaks in Rust components."""
    # Create objects and track them
    objects = []
    weak_refs = []

    for i in range(10):
        parser = get_parser()
        objects.append(parser)
        weak_refs.append(weakref.ref(parser))

    # Clear references
    objects.clear()
    gc.collect()

    # Check if objects were cleaned up
    alive_count = sum(1 for ref in weak_refs if ref() is not None)
    print(f"Objects still alive: {alive_count}/10")

    if alive_count == 0:
        print("✅ No memory leaks detected")
    else:
        print("⚠️ Possible memory leak - objects not cleaned up")

test_memory_leaks()
```

### Performance Profiling

```python
import cProfile
import pstats
from ClassicLib.RustIntegration import get_parser

def profile_rust_components():
    """Profile Rust component performance."""
    parser = get_parser()
    test_data = ["test line"] * 1000

    # Profile the operation
    profiler = cProfile.Profile()
    profiler.enable()

    for i in range(100):
        result = parser.find_segments(test_data, "Test", "TEST", "Game")

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

# profile_rust_components()
```

### Thread Safety Testing

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ClassicLib.RustIntegration import get_parser

def test_thread_safety():
    """Test thread safety of Rust components."""
    parser = get_parser()
    test_data = ["test line"] * 100
    results = []
    errors = []

    def worker(thread_id):
        try:
            for i in range(10):
                result = parser.find_segments(
                    test_data + [f"thread-{thread_id}-{i}"],
                    "Test", "TEST", "Game"
                )
                results.append((thread_id, i, len(result)))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Run multiple threads
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, i) for i in range(4)]
        for future in futures:
            future.result()

    print(f"Completed operations: {len(results)}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("Thread safety issues detected:")
        for thread_id, error in errors:
            print(f"  Thread {thread_id}: {error}")
    else:
        print("✅ Thread safety test passed")

test_thread_safety()
```

## Getting Help

### Gathering Diagnostic Information

```python
def collect_diagnostic_info():
    """Collect comprehensive diagnostic information."""
    import sys
    import os
    import platform
    import psutil

    info = []
    info.append("# CLASSIC Rust Diagnostics")
    info.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    info.append("")

    # System info
    info.append("## System Information")
    info.append(f"- Platform: {platform.platform()}")
    info.append(f"- Python: {sys.version}")
    info.append(f"- CPU: {psutil.cpu_count()} cores")
    info.append(f"- RAM: {psutil.virtual_memory().total / 1024**3:.1f} GB")
    info.append("")

    # Rust status
    info.append("## Rust Component Status")
    try:
        from ClassicLib.RustIntegration import get_rust_component_status
        status = get_rust_component_status()
        info.append(f"- Active Components: {status['active_count']}/{status['total_count']}")
        info.append(f"- Mode: {status['mode']}")

        for component, active in status['available'].items():
            if active:
                gain = status['performance_gains'].get(component, 'N/A')
                info.append(f"  ✅ {component}: {gain}")
            else:
                reason = status['failed'].get(component, 'Unknown')
                info.append(f"  ❌ {component}: {reason}")
    except Exception as e:
        info.append(f"- Error getting status: {e}")

    info.append("")

    # Environment
    info.append("## Environment Variables")
    rust_vars = [k for k in os.environ.keys() if 'RUST' in k or 'CLASSIC' in k]
    for var in rust_vars:
        info.append(f"- {var}: {os.environ[var]}")
    info.append("")

    # Installation info
    info.append("## Installation Information")
    try:
        import classic_core
        info.append(f"- Rust module version: {classic_core.__version__}")
        info.append(f"- Module location: {classic_core.__file__}")

        stat = os.stat(classic_core.__file__)
        info.append(f"- Module size: {stat.st_size} bytes")
        info.append(f"- Modified: {time.ctime(stat.st_mtime)}")
    except ImportError as e:
        info.append(f"- Rust module not available: {e}")

    return "\n".join(info)

# Generate diagnostic report
diagnostic_report = collect_diagnostic_info()
print(diagnostic_report)

# Save to file
with open("rust_diagnostics.txt", "w") as f:
    f.write(diagnostic_report)

print("\n📄 Diagnostic report saved to rust_diagnostics.txt")
```

### Reporting Issues

When reporting Rust-related issues, please include:

1. **Diagnostic report** (use the function above)
2. **Reproduction steps** - exact commands that cause the issue
3. **Expected vs actual behavior**
4. **Error messages** with full stack traces
5. **Environment details** (OS, Python version, Rust version)

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the complete Rust documentation index
- **Performance Monitoring**: Use built-in monitoring tools
- **Discord/Forums**: Community support channels

## Summary

This troubleshooting guide covers the most common issues with CLASSIC's Rust acceleration:

1. **Installation Problems**: Module import errors, build failures
2. **Performance Issues**: No acceleration, memory problems
3. **Runtime Issues**: AsyncBridge integration, GIL problems
4. **Development Issues**: Changes not reflected, debugging difficulties
5. **Environment-Specific**: Platform-specific solutions

Use the diagnostic tools provided to gather information, and follow the step-by-step solutions for your specific issue. The Rust acceleration should provide 10-150x performance improvements when working correctly.
