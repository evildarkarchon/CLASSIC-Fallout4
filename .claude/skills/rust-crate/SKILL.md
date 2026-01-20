---
name: rust-crate
description: Create new Rust crates following CLASSIC's three-layer architecture. Use when adding new Rust functionality with Python bindings.
---

This skill guides creation of new Rust crates in the CLASSIC project, following the three-layer architecture (foundation, business-logic, python-bindings).

## Architecture Overview

```
rust/
├── foundation/           # Shared runtime, errors, utilities
├── business-logic/       # Pure Rust (-core crates, NO PyO3)
├── python-bindings/      # PyO3 adapters (-py crates)
└── ui-applications/      # CLI, TUI, GUI apps
```

**Key Rules:**
- Business logic in `-core` crates (pure Rust, no PyO3)
- Python bindings in `-py` crates (thin PyO3 wrappers)
- ONE RUNTIME: Use `classic_shared::get_runtime()` for Tokio
- Never mix business logic with PyO3 in same crate

## Step 1: Create Business Logic Crate (-core)

### 1.1 Create Directory

```bash
mkdir -p rust/business-logic/classic-<name>-core/src
```

### 1.2 Create Cargo.toml

```toml
# rust/business-logic/classic-<name>-core/Cargo.toml
[package]
name = "classic-<name>-core"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
description = "Core <name> functionality for CLASSIC"

[lib]
crate-type = ["rlib"]

[dependencies]
classic-shared-core = { path = "../../foundation/classic-shared-core" }
thiserror = "2.0"
tokio = { version = "1.43", features = ["rt-multi-thread", "sync"] }

[dev-dependencies]
tokio = { version = "1.43", features = ["rt-multi-thread", "macros"] }
```

### 1.3 Create lib.rs with Documentation

```rust
//! Core <name> functionality for CLASSIC.
//!
//! This crate provides <description of functionality>.
//! It is designed to be used by the `classic-<name>-py` crate
//! for Python bindings.

mod error;
mod types;

pub use error::{Error, Result};
pub use types::*;
```

### 1.4 Add to Workspace

Edit `rust/Cargo.toml`:
```toml
members = [
    # ... existing members ...
    # Business Logic
    "business-logic/classic-<name>-core",
]
```

## Step 2: Create Python Bindings Crate (-py)

### 2.1 Create Directory

```bash
mkdir -p rust/python-bindings/classic-<name>-py/src
```

### 2.2 Create Cargo.toml

```toml
# rust/python-bindings/classic-<name>-py/Cargo.toml
[package]
name = "classic-<name>-py"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
description = "Python bindings for classic-<name>-core"

[lib]
name = "classic_<name>"
crate-type = ["cdylib", "rlib"]

[dependencies]
classic-<name>-core = { path = "../../business-logic/classic-<name>-core" }
classic-shared-core = { path = "../../foundation/classic-shared-core" }
pyo3 = { workspace = true }
tokio = { version = "1.43", features = ["rt-multi-thread"] }
```

### 2.3 Create lib.rs

```rust
//! Python bindings for classic-<name>-core.
//!
//! This crate provides Python access to <name> functionality
//! via PyO3 bindings.

use pyo3::prelude::*;
use pyo3::create_exception;

// Define module-specific exceptions
create_exception!(classic_<name>, Rust<Name>Error, pyo3::exceptions::PyException);

/// Python module initialization.
#[pymodule]
fn classic_<name>(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("Rust<Name>Error", m.py().get_type::<Rust<Name>Error>())?;
    // Add classes and functions here
    Ok(())
}
```

### 2.4 Create Type Stub (.pyi)

```python
# rust/python-bindings/classic-<name>-py/classic_<name>.pyi
"""Type stubs for classic_<name> Rust module."""

__version__: str

class Rust<Name>Error(Exception):
    """Base exception for <name> operations."""
    ...

# Add class and function stubs here
```

### 2.5 Add to Workspace

Edit `rust/Cargo.toml`:
```toml
members = [
    # ... existing members ...
    # Python Bindings
    "python-bindings/classic-<name>-py",
]
```

## Step 3: Create Python Integration

### 3.1 Create Wrapper in ClassicLib

```python
# ClassicLib/integration/<name>.py
"""Python wrapper for Rust <name> functionality.

This module provides a Python interface to the Rust <name>
implementation with automatic fallback to pure Python.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import classic_<name>

_rust_available: bool = False
_rust_module: "classic_<name> | None" = None

def _init_rust() -> bool:
    """Initialize Rust module if available."""
    global _rust_available, _rust_module
    try:
        import classic_<name>
        _rust_module = classic_<name>
        _rust_available = True
        return True
    except ImportError:
        return False

_init_rust()

def is_rust_available() -> bool:
    """Check if Rust acceleration is available."""
    return _rust_available
```

## Step 4: Write Tests

### 4.1 Rust Unit Tests

In `rust/business-logic/classic-<name>-core/src/lib.rs`:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_functionality() {
        // Test implementation
    }

    #[tokio::test]
    async fn test_async_functionality() {
        // Async test implementation
    }
}
```

### 4.2 Python Integration Tests

Create `tests/rust_integration/test_<name>_rust_integration.py`:
```python
"""Integration tests for Rust <name> bindings."""

import pytest

@pytest.mark.unit
def test_rust_module_loads():
    """Verify Rust module can be imported."""
    import classic_<name>
    assert hasattr(classic_<name>, "__version__")
```

## Checklist

- [ ] Business logic crate created in `rust/business-logic/`
- [ ] Python bindings crate created in `rust/python-bindings/`
- [ ] Both crates added to `rust/Cargo.toml` workspace
- [ ] `.pyi` stub file created for type hints
- [ ] Crate-level documentation (`//!`) in both crates
- [ ] All public items have `///` doc comments
- [ ] Unit tests in `-core` crate
- [ ] Integration tests in `tests/rust_integration/`
- [ ] Python wrapper in `ClassicLib/integration/`
