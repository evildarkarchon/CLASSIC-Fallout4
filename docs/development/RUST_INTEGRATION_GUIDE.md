# Rust Integration Guide

> Complete guide to CLASSIC's hybrid Python-Rust architecture

This guide covers how CLASSIC integrates Rust for performance-critical operations, achieving 10-150x speedups while maintaining full Python compatibility.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Available Rust Modules](#available-rust-modules)
4. [Using Rust Acceleration](#using-rust-acceleration)
5. [Creating New Rust Crates](#creating-new-rust-crates)
6. [PyO3 Patterns](#pyo3-patterns)
7. [Testing Rust Integration](#testing-rust-integration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

CLASSIC uses a three-tier Rust architecture:

1. **Foundation Layer** - Shared runtime and utilities
2. **Business Logic Layer** - Pure Rust algorithms (NO PyO3)
3. **Python Bindings Layer** - PyO3 adapters only

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Performance** | 10-150x speedups for critical operations |
| **Type Safety** | Rust's type system catches errors at compile time |
| **Memory Safety** | No memory leaks or buffer overflows |
| **Fallback** | Python implementations ensure compatibility |

### Performance Gains

| Operation | Python | Rust | Speedup |
|-----------|--------|------|---------|
| YAML Loading | 100ms | 4ms | **25x** |
| File I/O | 50ms | 5ms | **10x** |
| Log Parsing | 200ms | 13ms | **15x** |
| Database Ops | 60ms | 5ms | **12x** |
| Registry Ops | 10ms | 0.5ms | **20x** |

---

## Architecture

### Three-Tier Structure

```
rust/
├── foundation/                    # Layer 1: Shared infrastructure
│   ├── classic-shared-core/      # Runtime, errors, utilities
│   └── classic-shared-py/        # Python bindings for shared
│
├── business-logic/               # Layer 2: Pure Rust (NO PyO3)
│   ├── classic-yaml-core/        # YAML parsing
│   ├── classic-database-core/    # SQLite operations
│   ├── classic-scanlog-core/     # Log analysis
│   ├── classic-file-io-core/     # File operations
│   ├── classic-config-core/      # Configuration
│   └── ... (19 crates total)
│
├── python-bindings/              # Layer 3: PyO3 adapters
│   ├── classic-yaml-py/          # YAML Python bindings
│   ├── classic-database-py/      # Database Python bindings
│   ├── classic-scanlog-py/       # Scanlog Python bindings
│   └── ... (20 crates total)
│
└── ui-applications/              # Native applications
    ├── classic-cli/              # CLI application
    ├── classic-tui/              # TUI application
    └── classic-gui-slint/        # Slint GUI
```

### Architecture Rules

1. **ONE RUNTIME RULE**: All crates share global Tokio runtime via `classic_shared::get_runtime()`
2. **SEPARATION**: Business logic (`-core`) separate from PyO3 bindings (`-py`)
3. **NO MIXED CRATES**: Never combine business logic with PyO3 in same crate
4. **TYPE STUBS**: All `-py` crates must have `.pyi` stub files

### Crate Types

| Layer | Crate Type | PyO3 | Purpose |
|-------|------------|------|---------|
| Foundation | `rlib` | Minimal | Shared utilities |
| Business Logic | `rlib` | **None** | Pure Rust algorithms |
| Python Bindings | `cdylib + rlib` | Yes | PyO3 adapters |

---

## Available Rust Modules

### Core Modules

| Module | Python Import | Purpose | Speedup |
|--------|---------------|---------|---------|
| `classic_yaml` | `import classic_yaml` | YAML parsing | 15-30x |
| `classic_database` | `import classic_database` | SQLite operations | 12x |
| `classic_scanlog` | `import classic_scanlog` | Log analysis | 15x |
| `classic_file_io` | `import classic_file_io` | File I/O | 10x |
| `classic_config` | `import classic_config` | Configuration | 15x |
| `classic_registry` | `import classic_registry` | Global registry | 20x |
| `classic_perf` | `import classic_perf` | Performance monitoring | N/A |
| `classic_message` | `import classic_message` | Message formatting | 5x |
| `classic_settings` | `import classic_settings` | Settings cache | 25x |
| `classic_pybridge` | `import classic_pybridge` | Async bridging | N/A |

### Additional Modules

- `classic_scangame` - Game file scanning
- `classic_path` - Path operations
- `classic_constants` - Constants
- `classic_version` - Version parsing
- `classic_resource` - Resource loading
- `classic_xse` - Script Extender integration
- `classic_web` - Web operations
- `classic_update` - Update checking

---

## Using Rust Acceleration

### Automatic Detection

CLASSIC automatically uses Rust when available:

```python
from ClassicLib.integration.factory import get_parser, get_file_io, get_yaml_operations

# Automatically uses Rust if available, Python fallback otherwise
parser = get_parser()
file_io = get_file_io()
yaml_ops = get_yaml_operations()
```

### Checking Availability

```python
# Module-level flags
from ClassicLib import (
    RUST_REGISTRY_AVAILABLE,
    RUST_PERF_AVAILABLE,
    RUST_SETTINGS_AVAILABLE,
    RUST_MESSAGE_AVAILABLE,
)

if RUST_REGISTRY_AVAILABLE:
    print("Using Rust registry (20x faster)")

# Component detector
from ClassicLib.integration.detector import detect_component

is_available, module = detect_component("classic_yaml")
if is_available:
    yaml_ops = module.RustYamlOperations()

# Full status report
from ClassicLib.integration.status import print_rust_status
print_rust_status()
```

### Direct Module Usage

```python
# YAML operations
import classic_yaml

yaml_ops = classic_yaml.RustYamlOperations()
data = yaml_ops.load_file("config.yaml")
yaml_ops.save_file("output.yaml", data)
value = yaml_ops.get_value(data, "section.key")

# Database operations
import classic_database

db = classic_database.RustDatabase("classic.db")
result = db.execute("SELECT * FROM plugins")

# Log parsing
import classic_scanlog

parser = classic_scanlog.RustLogParser()
segments = parser.find_segments(log_content)
result = parser.parse_log(log_content)

# File I/O
import classic_file_io

file_io = classic_file_io.RustFileIO()
content = file_io.read_file("crash.log")
file_io.write_file("output.txt", content)
```

### Integration Patterns

#### Factory Pattern (Recommended)

```python
from ClassicLib.integration.factory import get_yaml_operations

# Automatically selects best available implementation
yaml_ops = get_yaml_operations()
data = yaml_ops.load_file("config.yaml")
```

#### Fallback Pattern

```python
try:
    import classic_yaml
    yaml_ops = classic_yaml.RustYamlOperations()
except ImportError:
    from ClassicLib.python.yaml_py import PythonYamlOperations
    yaml_ops = PythonYamlOperations()
```

#### Feature Detection Pattern

```python
from ClassicLib.integration.detector import detect_component

def process_logs(logs):
    is_rust, module = detect_component("classic_scanlog")

    if is_rust:
        # Use Rust for bulk processing (15x faster)
        parser = module.RustLogParser()
        return parser.batch_parse(logs)
    else:
        # Fall back to Python
        from ClassicLib.python.parser_py import PythonParser
        parser = PythonParser()
        return [parser.parse(log) for log in logs]
```

---

## Creating New Rust Crates

### Step 1: Create Business Logic Crate

```bash
cd rust/business-logic
cargo new classic-myfeature-core --lib
```

**`Cargo.toml`**:
```toml
[package]
name = "classic-myfeature-core"
version = "0.1.0"
edition = "2024"

[lib]
crate-type = ["rlib"]

[dependencies]
classic-shared-core = { path = "../../foundation/classic-shared-core" }
tokio = { workspace = true }
thiserror = { workspace = true }
```

**`src/lib.rs`**:
```rust
//! MyFeature - Description of the feature.
//!
//! This crate provides...

use classic_shared_core::{get_runtime, ClassicError};

/// Main feature struct.
pub struct MyFeature {
    // fields
}

impl MyFeature {
    /// Create a new instance.
    pub fn new() -> Self {
        Self {}
    }

    /// Async operation using shared runtime.
    pub async fn process(&self, data: &str) -> Result<String, ClassicError> {
        // Implementation
        Ok(data.to_uppercase())
    }

    /// Sync wrapper using global runtime.
    pub fn process_sync(&self, data: &str) -> Result<String, ClassicError> {
        get_runtime().block_on(self.process(data))
    }
}
```

### Step 2: Create Python Bindings Crate

```bash
cd rust/python-bindings
cargo new classic-myfeature-py --lib
```

**`Cargo.toml`**:
```toml
[package]
name = "classic-myfeature-py"
version = "0.1.0"
edition = "2024"

[lib]
name = "classic_myfeature"
crate-type = ["cdylib", "rlib"]

[dependencies]
classic-myfeature-core = { path = "../../business-logic/classic-myfeature-core" }
pyo3 = { workspace = true, features = ["extension-module"] }
```

**`src/lib.rs`**:
```rust
//! Python bindings for MyFeature.

use classic_myfeature_core::MyFeature;
use pyo3::prelude::*;

/// Python wrapper for MyFeature.
#[pyclass]
pub struct RustMyFeature {
    inner: MyFeature,
}

#[pymethods]
impl RustMyFeature {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: MyFeature::new(),
        }
    }

    /// Process data.
    pub fn process(&self, data: &str) -> PyResult<String> {
        self.inner
            .process_sync(data)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }
}

/// Module initialization.
#[pymodule]
fn classic_myfeature(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMyFeature>()?;
    Ok(())
}
```

### Step 3: Create Type Stub

**`classic_myfeature.pyi`**:
```python
"""Type stubs for classic_myfeature Rust module."""

class RustMyFeature:
    """Rust-accelerated MyFeature operations."""

    def __init__(self) -> None:
        """Create a new instance."""
        ...

    def process(self, data: str) -> str:
        """Process data.

        Args:
            data: Input data to process.

        Returns:
            Processed data.

        Raises:
            RuntimeError: If processing fails.
        """
        ...
```

### Step 4: Update Workspace

**`rust/Cargo.toml`**:
```toml
[workspace]
members = [
    # ... existing members ...

    # Business Logic
    "business-logic/classic-myfeature-core",

    # Python Bindings
    "python-bindings/classic-myfeature-py",
]
```

### Step 5: Update Build Scripts

**`rebuild_rust.ps1`**:
```powershell
# Add to the crate list
$crates = @(
    # ... existing crates ...
    "classic-myfeature-py"
)
```

### Step 6: Create Python Integration

**`ClassicLib/integration/myfeature_factory.py`**:
```python
"""Factory for MyFeature operations."""

from ClassicLib.integration.detector import detect_component


def get_myfeature():
    """Get best available MyFeature implementation.

    Returns:
        Rust implementation if available, Python fallback otherwise.
    """
    is_available, module = detect_component("classic_myfeature")

    if is_available:
        return module.RustMyFeature()
    else:
        from ClassicLib.python.myfeature_py import PythonMyFeature
        return PythonMyFeature()
```

---

## PyO3 Patterns

### Module Registration

```rust
use pyo3::prelude::*;

#[pymodule]
fn classic_myfeature(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add classes
    m.add_class::<RustMyFeature>()?;

    // Add functions
    m.add_function(wrap_pyfunction!(process_data, m)?)?;

    // Add constants
    m.add("VERSION", env!("CARGO_PKG_VERSION"))?;

    Ok(())
}
```

### Error Handling

```rust
use pyo3::prelude::*;
use pyo3::create_exception;

// Create custom exception
create_exception!(classic_myfeature, MyFeatureError, pyo3::exceptions::PyException);

impl From<classic_myfeature_core::Error> for PyErr {
    fn from(err: classic_myfeature_core::Error) -> Self {
        MyFeatureError::new_err(err.to_string())
    }
}

#[pymethods]
impl RustMyFeature {
    pub fn process(&self, data: &str) -> PyResult<String> {
        self.inner.process_sync(data).map_err(PyErr::from)
    }
}
```

### Async with Global Runtime

```rust
use classic_shared_core::get_runtime;

#[pymethods]
impl RustMyFeature {
    /// Async operation using global Tokio runtime.
    pub fn process(&self, py: Python<'_>, data: &str) -> PyResult<String> {
        let data = data.to_string();
        let inner = self.inner.clone();

        // Release GIL for CPU-bound work
        py.allow_threads(|| {
            get_runtime().block_on(async move {
                inner.process(&data).await
            })
        })
        .map_err(PyErr::from)
    }
}
```

### GIL Release Pattern

```rust
#[pymethods]
impl RustMyFeature {
    /// CPU-intensive operation with GIL release.
    pub fn heavy_computation(&self, py: Python<'_>, data: Vec<String>) -> PyResult<Vec<String>> {
        // Release GIL for parallel processing
        py.allow_threads(|| {
            data.par_iter()
                .map(|item| self.inner.process_item(item))
                .collect::<Result<Vec<_>, _>>()
        })
        .map_err(PyErr::from)
    }
}
```

---

## Testing Rust Integration

### Python Tests

```python
# tests/rust_integration/test_myfeature.py
import pytest

@pytest.mark.unit
def test_rust_myfeature_available():
    """Test Rust module imports."""
    try:
        import classic_myfeature
        assert hasattr(classic_myfeature, 'RustMyFeature')
    except ImportError:
        pytest.skip("Rust module not available")

@pytest.mark.unit
def test_myfeature_process():
    """Test basic processing."""
    from ClassicLib.integration.myfeature_factory import get_myfeature

    myfeature = get_myfeature()
    result = myfeature.process("hello")
    assert result == "HELLO"

@pytest.mark.integration
def test_myfeature_with_file(tmp_path):
    """Test with file I/O."""
    from ClassicLib.integration.myfeature_factory import get_myfeature

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    myfeature = get_myfeature()
    result = myfeature.process_file(str(test_file))
    assert result is not None
```

### Rust Tests

```rust
// rust/business-logic/classic-myfeature-core/src/lib.rs

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process() {
        let feature = MyFeature::new();
        let result = feature.process_sync("hello").unwrap();
        assert_eq!(result, "HELLO");
    }

    #[tokio::test]
    async fn test_process_async() {
        let feature = MyFeature::new();
        let result = feature.process("hello").await.unwrap();
        assert_eq!(result, "HELLO");
    }
}
```

### Running Tests

```bash
# Python tests
uv run pytest tests/rust_integration/ -v

# Rust tests
cd rust
cargo test --workspace

# All tests
uv run pytest -n auto && cargo test --workspace --manifest-path rust/Cargo.toml
```

---

## Troubleshooting

### Build Issues

#### "cannot find crate" error

```bash
# Clean and rebuild
cd rust
cargo clean
cargo build --release
```

#### Linking errors on Windows

```bash
# Install Visual Studio Build Tools
# Then restart terminal
./rebuild_rust.ps1 -Clean
```

#### maturin build fails

```bash
# Update maturin
uv pip install maturin --upgrade

# Try wheel build
cd rust/python-bindings/classic-myfeature-py
maturin build --release --out dist
uv pip install dist/*.whl --force-reinstall
```

### Runtime Issues

#### "Rust module not available"

```python
# Check if module exists
try:
    import classic_myfeature
except ImportError as e:
    print(f"Import error: {e}")

# Rebuild Rust modules
# ./rebuild_rust.ps1
```

#### "Runtime already initialized"

This happens when multiple Tokio runtimes are created. Solution:

```rust
// Always use shared runtime
use classic_shared_core::get_runtime;

// NEVER do this:
// let rt = tokio::runtime::Runtime::new().unwrap();
```

#### GIL deadlock

When calling Python from Rust threads:

```rust
// WRONG - can deadlock
let result = some_python_call();

// CORRECT - release GIL first
py.allow_threads(|| {
    // Rust work here
});
```

### Performance Issues

#### Not seeing expected speedup

1. Check if Rust is actually being used:
   ```python
   from ClassicLib.integration.status import print_rust_status
   print_rust_status()
   ```

2. Ensure GIL is released for parallel work:
   ```rust
   py.allow_threads(|| {
       // Parallel work here
   })
   ```

3. Profile to find bottlenecks:
   ```python
   from ClassicLib import TimedBlock

   with TimedBlock("rust_operation"):
       result = rust_function()
   ```

---

## See Also

- [Rust Workspace Architecture](rust_workspace_architecture.md)
- [PyO3 Integration Patterns](pyo3_integration_patterns.md)
- [Async Development Guide](async_development_guide.md)
- [PyO3 0.27 Migration Guide](../rust/PyO3-0.27-migration.md)
- [Rust Acceleration Guide](rust_acceleration_guide.md)

---

*Last updated: December 2025*
