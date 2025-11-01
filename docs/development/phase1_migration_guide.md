# Phase 1 Migration Guide

**Version:** 1.0
**Date:** January 2025
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Component Reference](#component-reference)
4. [Migration Patterns](#migration-patterns)
5. [Performance Guide](#performance-guide)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Overview

### What is Phase 1?

Phase 1 of the ClassicLib Rust Port replaces 5 core infrastructure components with high-performance Rust implementations while maintaining full backward compatibility with existing Python code.

### Components

| Component | Rust Module | Purpose | Performance Gain |
|-----------|-------------|---------|------------------|
| GlobalRegistry | `classic_registry` | Thread-safe key-value store | 15-25x |
| PerformanceMonitor | `classic_perf` | Real-time metrics | Native Rust precision |
| AsyncBridge | `classic_pybridge` | Async/sync coordination | ONE RUNTIME RULE |
| YamlSettingsCache | `rust_settings` | Configuration cache | 15-30x (19x measured) |
| MessageHandler | `classic_message` | Message routing/formatting | 4x emoji stripping |

### Key Benefits

✅ **Backward Compatible** - All existing Python code works unchanged
✅ **Automatic Fallback** - Gracefully uses Python if Rust unavailable
✅ **Zero Config** - No code changes required for basic acceleration
✅ **Opt-In Optimization** - Use Rust directly for maximum performance
✅ **Type Safe** - PyO3 provides compile-time type safety

---

## Quick Start

### Installation

```bash
# Method 1: Build and install all Phase 1 wheels
cd classic-registry-py && maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
cd ../classic-perf-py && maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
cd ../classic-pybridge-py && maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
cd ../classic-settings-py && maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
cd ../classic-message-py && maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall

# Method 2: Editable install (development)
uv pip install -e . --force-reinstall
```

### Verification

```python
from ClassicLib import (
    RUST_REGISTRY_AVAILABLE,
    RUST_PERF_AVAILABLE,
    RUST_PYBRIDGE_AVAILABLE,
    RUST_SETTINGS_AVAILABLE,
    RUST_MESSAGE_AVAILABLE,
)

print(f"Registry:  {RUST_REGISTRY_AVAILABLE}")
print(f"Perf:      {RUST_PERF_AVAILABLE}")
print(f"Bridge:    {RUST_PYBRIDGE_AVAILABLE}")
print(f"Settings:  {RUST_SETTINGS_AVAILABLE}")
print(f"Message:   {RUST_MESSAGE_AVAILABLE}")
```

### Quick Test

```python
# Test Settings acceleration
from ClassicLib import rust_settings, RUST_SETTINGS_AVAILABLE
import tempfile
from pathlib import Path

if RUST_SETTINGS_AVAILABLE:
    # Create test YAML
    test_file = Path(tempfile.gettempdir()) / "test.yaml"
    test_file.write_text("test: value\\n")

    # Load with Rust (19x faster!)
    result = rust_settings.load_settings_sync("test_key", str(test_file))
    print(f"Loaded: {result}")

    test_file.unlink()
```

---

## Component Reference

### 1. GlobalRegistry (`classic_registry`)

**Purpose:** Thread-safe global key-value store with 15-25x performance improvement.

#### Python API (Existing - No Changes)

```python
from ClassicLib.GlobalRegistry import register, get, is_registered

# Register values
register("game_path", "/path/to/game")
register("debug_mode", True)

# Retrieve values
path = get("game_path")
debug = get("debug_mode", default=False)

# Check registration
if is_registered("game_path"):
    print(f"Game path: {get('game_path')}")
```

#### Direct Rust API (Opt-In for Maximum Performance)

```python
from ClassicLib import classic_registry, RUST_REGISTRY_AVAILABLE

if RUST_REGISTRY_AVAILABLE:
    registry = classic_registry.RustGlobalRegistry()

    # Set/Get operations (15-25x faster)
    registry.set("key", "value")
    value = registry.get("key")  # Returns str | None

    # Bulk operations
    items = registry.items()  # Returns list of (key, value) tuples
    registry.clear()
else:
    # Fallback to Python
    from ClassicLib.GlobalRegistry import GlobalRegistry
    registry = GlobalRegistry()
```

#### When to Use Rust Directly

- High-frequency key-value operations (>1000/second)
- Performance-critical initialization
- Bulk data loading

---

### 2. PerformanceMonitor (`classic_perf`)

**Purpose:** Real-time performance metrics with Rust precision timing.

#### Python API (Existing - No Changes)

```python
from ClassicLib.PerformanceMonitor import timed_operation, async_timed_operation

# Synchronous timing
with timed_operation("database_query"):
    result = execute_query()

# Asynchronous timing
async with async_timed_operation("api_call"):
    response = await fetch_data()
```

#### Direct Rust API (Opt-In)

```python
from ClassicLib import classic_perf, RUST_PERF_AVAILABLE

if RUST_PERF_AVAILABLE:
    # Record operation
    classic_perf.record_operation("operation_name", 0.123, success=True)

    # Get metrics
    metrics = classic_perf.get_all_metrics()
    for metric in metrics:
        print(f"{metric.name}: {metric.count} ops, avg {metric.average_duration_ms:.2f}ms")

    # Clear metrics
    classic_perf.clear_metrics()
```

#### When to Use Rust Directly

- Custom performance tracking
- Low-overhead profiling
- Real-time metrics dashboards

---

### 3. AsyncBridge (`classic_pybridge`)

**Purpose:** Async/sync coordination utilities following the ONE RUNTIME RULE.

#### Python API (Existing - No Changes)

```python
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()

# Run async code from sync context
result = bridge.run_async(async_function())

# With timeout
result = bridge.run_async(async_function(), timeout=5.0)
```

#### Direct Rust API (Metrics Only)

```python
from ClassicLib import classic_pybridge, RUST_PYBRIDGE_AVAILABLE

if RUST_PYBRIDGE_AVAILABLE:
    # Check runtime availability
    if classic_pybridge.is_runtime_available():
        info = classic_pybridge.get_runtime_info()
        print(f"Runtime active: {info.is_active}")
        print(f"Thread count: {info.thread_count}")

    # Record bridge operations
    classic_pybridge.record_operation(
        classic_pybridge.BridgeOperationType.RunAsync,
        duration_secs=0.123,
        success=True
    )

    # Get metrics
    metrics = classic_pybridge.get_metrics()
    print(f"Total operations: {metrics.total_operations}")
```

#### When to Use Rust Directly

- Diagnostics and monitoring
- Runtime introspection
- Performance debugging

---

### 4. YamlSettingsCache (`rust_settings`)

**Purpose:** High-performance YAML settings cache with 15-30x speedup (19x measured).

#### Python API (Existing - No Changes)

```python
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Load settings (automatically uses Rust if available)
debug_mode = classic_settings(bool, "Debug Messages")
game_name = classic_settings(str, "Game Name", default="Fallout 4")

# YAML data access
yaml_data = yaml_settings("CLASSIC.yaml")
```

#### Direct Rust API (Opt-In for Maximum Performance)

```python
from ClassicLib import rust_settings, RUST_SETTINGS_AVAILABLE
from pathlib import Path

if RUST_SETTINGS_AVAILABLE:
    # Synchronous loading (19x faster)
    settings = rust_settings.load_settings_sync("my_key", "config.yaml")

    # Asynchronous loading (for async contexts)
    settings = await rust_settings.load_settings_async("my_key", "config.yaml")

    # Batch loading (parallel I/O)
    paths = [Path("config1.yaml"), Path("config2.yaml")]
    results = rust_settings.load_batch_sync(paths)

    # Cache operations
    rust_settings.cache_set("my_key", settings)
    cached = rust_settings.cache_get("my_key")  # Returns None if not found
    rust_settings.cache_remove("my_key")
    rust_settings.cache_clear()
```

#### When to Use Rust Directly

- Application startup (load all configs at once)
- Dynamic configuration reloading
- Hot-path config access (>100 times/second)

---

### 5. MessageHandler (`classic_message`)

**Purpose:** Type-safe message routing with emoji stripping (4x faster).

#### Python API (Existing - No Changes)

```python
from ClassicLib.MessageHandler import msg_info, msg_error, msg_success

# Send messages (automatically uses Rust formatting if available)
msg_info("Loading configuration...")
msg_error("Failed to load file", details="File not found")
msg_success("Operation completed! ✅")
```

#### Direct Rust API (Opt-In)

```python
from ClassicLib import classic_message, RUST_MESSAGE_AVAILABLE

if RUST_MESSAGE_AVAILABLE:
    # Create messages with type safety
    msg = classic_message.Message(
        "Error occurred",
        classic_message.MessageType.Error
    )

    # Builder pattern
    msg = (classic_message.Message("Success", classic_message.MessageType.Success)
           .with_title("Operation Complete")
           .with_details("All tests passed"))

    # Message routing
    if msg.target().should_display_in_gui():
        show_gui_message(msg.content())

    # Emoji stripping (4x faster)
    clean_text = classic_message.strip_emoji("Hello 👋 World 🌍!")

    # Log formatting
    log_text = classic_message.format_log_message(
        "Success! ✅",
        "All tests passed 🎉"
    )
```

#### When to Use Rust Directly

- Message-intensive applications
- Windows console output (emoji stripping required)
- Type-safe message construction

---

## Migration Patterns

### Pattern 1: Zero Changes (Automatic Acceleration)

**Scenario:** Existing code using Python wrappers

**Before (Python only):**
```python
from ClassicLib.YamlSettingsCache import classic_settings

debug = classic_settings(bool, "Debug Messages")
```

**After (Rust acceleration automatic):**
```python
from ClassicLib.YamlSettingsCache import classic_settings

debug = classic_settings(bool, "Debug Messages")
# Now 19x faster if rust_settings installed!
```

**Action Required:** None! Just install Rust wheels.

---

### Pattern 2: Opt-In Direct Rust Usage

**Scenario:** Performance-critical hot path

**Before (Python):**
```python
from ClassicLib.GlobalRegistry import get

def hot_loop():
    for i in range(10000):
        value = get(f"key_{i}")
```

**After (Rust direct):**
```python
from ClassicLib import classic_registry, RUST_REGISTRY_AVAILABLE
from ClassicLib.GlobalRegistry import get

def hot_loop():
    if RUST_REGISTRY_AVAILABLE:
        registry = classic_registry.RustGlobalRegistry()
        for i in range(10000):
            value = registry.get(f"key_{i}")  # 15-25x faster
    else:
        # Fallback to Python
        for i in range(10000):
            value = get(f"key_{i}")
```

**Action Required:** Check availability, use direct Rust API.

---

### Pattern 3: Gradual Migration

**Scenario:** Large codebase with many registry calls

**Step 1: Identify Hot Paths**
```bash
# Profile existing code
uv run python -m cProfile -o profile.stats your_script.py
uv run python -m pstats profile.stats
# Look for GlobalRegistry.get() calls
```

**Step 2: Add Rust Availability Check**
```python
from ClassicLib import RUST_REGISTRY_AVAILABLE

if RUST_REGISTRY_AVAILABLE:
    print("✅ Rust acceleration available")
else:
    print("⚠️  Using Python fallback")
```

**Step 3: Migrate Hot Paths First**
```python
# Before: Python wrapper
from ClassicLib.GlobalRegistry import get

def process_items(items):
    for item in items:
        config = get(f"config_{item.id}")  # Called 10,000 times
        process(item, config)

# After: Direct Rust for hot path
from ClassicLib import classic_registry, RUST_REGISTRY_AVAILABLE
from ClassicLib.GlobalRegistry import get

def process_items(items):
    if RUST_REGISTRY_AVAILABLE and len(items) > 100:
        # Use Rust for large batches
        registry = classic_registry.RustGlobalRegistry()
        for item in items:
            config = registry.get(f"config_{item.id}")  # 15-25x faster
            process(item, config)
    else:
        # Python fallback for small batches
        for item in items:
            config = get(f"config_{item.id}")
            process(item, config)
```

**Step 4: Benchmark**
```python
import time

start = time.perf_counter()
process_items(large_item_list)
elapsed = time.perf_counter() - start
print(f"Processed {len(large_item_list)} items in {elapsed:.2f}s")
```

---

### Pattern 4: Conditional Rust Features

**Scenario:** Optional Rust features for power users

```python
from ClassicLib import (
    RUST_SETTINGS_AVAILABLE,
    rust_settings,
)
from ClassicLib.YamlSettingsCache import classic_settings

def load_configuration(fast_mode=False):
    if fast_mode and RUST_SETTINGS_AVAILABLE:
        # Power user mode: batch load all configs
        config_files = [
            "main.yaml",
            "plugins.yaml",
            "ui.yaml",
        ]
        settings = rust_settings.load_batch_sync(config_files)
        return settings
    else:
        # Normal mode: load as needed
        return {
            "main": classic_settings(dict, "main"),
            "plugins": classic_settings(list, "plugins"),
        }
```

---

## Performance Guide

### Expected Speedups

| Operation | Speedup | When to Use Rust |
|-----------|---------|------------------|
| Registry get/set | 15-25x | High-frequency access (>1000/s) |
| YAML loading | 15-30x | Startup, config reloading |
| Emoji stripping | 4x | Windows console output |
| Message creation | 0.5x* | Keep in Python (FFI overhead) |

\* *Simple operations are faster in Python due to FFI overhead*

### Performance Tuning Tips

#### 1. Batch Operations

**Bad (Many FFI calls):**
```python
for file in config_files:
    settings = rust_settings.load_settings_sync(file, file)
```

**Good (Single FFI call):**
```python
all_settings = rust_settings.load_batch_sync(config_files)
```

#### 2. Cache Reuse

**Bad (Re-load every time):**
```python
def get_config():
    return rust_settings.load_settings_sync("config", "config.yaml")

# Called 1000 times
for item in items:
    config = get_config()
```

**Good (Load once):**
```python
# Load once at startup
config = rust_settings.load_settings_sync("config", "config.yaml")

# Reuse cached value
for item in items:
    process(item, config)
```

#### 3. Avoid Trivial Rust Calls

**Bad (FFI overhead dominates):**
```python
msg = classic_message.Message("Hello", classic_message.MessageType.Info)
```

**Good (Use Python for simple operations):**
```python
from ClassicLib.MessageHandler import Message, MessageType

msg = Message("Hello", MessageType.INFO)
```

**When to Use Rust Message:**
- Emoji-heavy content needing stripping
- Type-safe routing logic
- Builder pattern for complex messages

---

## Troubleshooting

### Issue: "Module 'classic_registry' has no attribute 'RustGlobalRegistry'"

**Cause:** Wheel not built or installed correctly.

**Solution:**
```bash
cd classic-registry-py
maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
```

**Verify:**
```python
import classic_registry
print(dir(classic_registry))  # Should show RustGlobalRegistry
```

---

### Issue: "ImportError: DLL load failed"

**Cause:** Missing Rust runtime dependencies on Windows.

**Solution:**
1. Install Visual C++ Redistributable 2015-2022
2. Rebuild wheel:
   ```bash
   maturin build --release
   ```

---

### Issue: Slower than Python

**Cause:** Using Rust for trivial operations with FFI overhead.

**Diagnosis:**
```python
import time

# Bad: FFI overhead dominates
start = time.perf_counter()
for _ in range(10000):
    msg = classic_message.Message("Test", classic_message.MessageType.Info)
elapsed = time.perf_counter() - start
print(f"Rust: {elapsed:.4f}s")

# Compare to Python
from ClassicLib.MessageHandler import Message, MessageType
start = time.perf_counter()
for _ in range(10000):
    msg = Message("Test", MessageType.INFO)
elapsed = time.perf_counter() - start
print(f"Python: {elapsed:.4f}s")
```

**Solution:** Use Python for trivial operations, Rust for compute-intensive ones.

---

### Issue: "RuntimeError: no running event loop"

**Cause:** Calling async functions from sync context.

**Solution:** Use AsyncBridge:
```python
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())
```

---

## Best Practices

### 1. Check Availability First

```python
from ClassicLib import RUST_SETTINGS_AVAILABLE, rust_settings

if RUST_SETTINGS_AVAILABLE:
    # Use Rust
    settings = rust_settings.load_settings_sync("key", "config.yaml")
else:
    # Fallback to Python
    from ClassicLib.YamlSettingsCache import yaml_settings
    settings = yaml_settings("config.yaml")
```

### 2. Use Python Wrappers by Default

Python wrappers automatically use Rust when available:

```python
# ✅ Good: Automatic Rust acceleration
from ClassicLib.YamlSettingsCache import classic_settings
debug = classic_settings(bool, "Debug Messages")

# ⚠️  Only use direct Rust for hot paths
from ClassicLib import rust_settings
settings = rust_settings.load_settings_sync("key", "config.yaml")
```

### 3. Profile Before Optimizing

```python
from ClassicLib import classic_perf, RUST_PERF_AVAILABLE

if RUST_PERF_AVAILABLE:
    with classic_perf.TimedOperation("my_operation"):
        expensive_operation()

    metrics = classic_perf.get_all_metrics()
    print(f"Average duration: {metrics[0].average_duration_ms:.2f}ms")
```

### 4. Handle Errors Gracefully

```python
try:
    if RUST_SETTINGS_AVAILABLE:
        settings = rust_settings.load_settings_sync("key", "config.yaml")
    else:
        settings = python_load_settings("config.yaml")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    settings = get_default_settings()
```

### 5. Document Rust Dependencies

```python
def load_configuration():
    """Load application configuration.

    Uses Rust-accelerated YAML loading if available (19x faster),
    otherwise falls back to Python implementation.

    Returns:
        dict: Configuration settings

    Performance:
        - Rust: ~3ms for typical config
        - Python: ~60ms for typical config
    """
    if RUST_SETTINGS_AVAILABLE:
        return rust_settings.load_settings_sync("config", "config.yaml")
    return python_yaml_load("config.yaml")
```

---

## Summary

Phase 1 provides significant performance improvements while maintaining full backward compatibility. Key takeaways:

✅ **Install Phase 1 wheels** for automatic 19x YAML speedup
✅ **Use Python wrappers** by default (they use Rust automatically)
✅ **Opt-in to direct Rust** for hot paths and maximum performance
✅ **Check availability** before using Rust APIs directly
✅ **Profile first** - don't optimize prematurely
✅ **Keep simple operations in Python** - avoid FFI overhead

For more information:
- [Performance Benchmark Report](../performance/phase1_benchmark_report.md)
- [Rust Documentation Index](../RUST_DOCUMENTATION_INDEX.md)
- [PyO3 Integration Patterns](pyo3_integration_patterns.md)

---

**Document Version:** 1.0
**Last Updated:** January 2025
**Status:** Production Ready ✅
