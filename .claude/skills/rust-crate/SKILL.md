---
name: rust-crate
description: Create new Rust crates following CLASSIC's layered architecture. Use when adding new Rust functionality that needs to reach the C++, Node, or Python binding surfaces.
---

This skill guides creation of new Rust crates in the CLASSIC project, following the repo-root layered architecture.

## Architecture Overview

```
<repo root>/
├── foundation/           # Shared runtime, errors, utilities
├── business-logic/       # Pure Rust (-core crates, NO PyO3)
├── cpp-bindings/         # CXX bridge to the C++ frontends
├── node-bindings/        # NAPI-RS bindings
├── python-bindings/      # PyO3 adapters (-py crates)
└── ui-applications/      # TUI app
```

The Cargo workspace root is the repo root — there is no nested Rust workspace directory.

**Key Rules:**
- Business logic in `-core` crates (pure Rust, no PyO3)
- Bindings are thin wrappers; never reimplement logic in a binding layer
- ONE RUNTIME: use the shared runtime from `classic-shared-core`; never create another
- Never mix business logic with PyO3 in the same crate
- Parity is one change surface: a new public `-core` API is not done until the C++, Node, **and** Python surfaces are updated (AGENTS.md rule 4). See `docs/api/binding-parity-policy.md`.

## Step 1: Create Business Logic Crate (-core)

### 1.1 Create Directory

```bash
mkdir -p business-logic/classic-<name>-core/src
```

### 1.2 Create Cargo.toml

Match the conventions in the existing `-core` crates: workspace-inherited dependency
versions, the current workspace version, and the shared lint block.

```toml
# business-logic/classic-<name>-core/Cargo.toml
[package]
name = "classic-<name>-core"
version = "9.1.0"
edition = "2024"
rust-version = "1.96.0"
authors = ["CLASSIC Development Team"]
description = "Core <name> functionality for CLASSIC (no PyO3)"
repository = "https://github.com/evildarkarchon/CLASSIC-Fallout4"

[lib]
crate-type = ["rlib"]  # Pure Rust library only - no PyO3

[dependencies]
classic-shared-core = { path = "../../foundation/classic-shared-core" }
thiserror = { workspace = true }
anyhow = { workspace = true }
serde = { workspace = true, features = ["derive"] }

[dev-dependencies]
tempfile = { workspace = true }

[lints.rust]
deprecated = "deny"
rust_2024_compatibility = "warn"
unsafe_code = "deny"
missing_docs = "warn"
unused = "deny"
```

Check the workspace root `Cargo.toml` `[workspace.dependencies]` before hardcoding any
version — most common crates are already pinned there.

### 1.3 Create lib.rs with Documentation

```rust
//! Core <name> functionality for CLASSIC.
//!
//! This crate provides <description of functionality>.
//! It is consumed by the binding layers under `cpp-bindings/`,
//! `node-bindings/`, and `python-bindings/`.

mod error;
mod types;

pub use error::{Error, Result};
pub use types::*;

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
```

Also create `src/lib_tests.rs` with a trivial smoke test in the sibling layout
(see `openspec/specs/rust-test-module-layout/spec.md`):

```rust
use super::*;

#[test]
fn crate_compiles_and_loads() {
    // Trivial smoke test proving the crate links.
}
```

### 1.4 Add to Workspace

Edit the repo-root `Cargo.toml`:
```toml
members = [
    # ... existing members ...
    # Business Logic (Pure Rust - no PyO3)
    "business-logic/classic-<name>-core",
]
```

## Step 2: Create Python Bindings Crate (-py)

### 2.1 Create Directory

```bash
mkdir -p python-bindings/classic-<name>-py/src
```

### 2.2 Create Cargo.toml

```toml
# python-bindings/classic-<name>-py/Cargo.toml
[package]
name = "classic-<name>-py"
version = "9.1.0"
edition = "2024"
rust-version = "1.96.0"
description = "Python bindings for classic-<name>-core"

[lib]
name = "classic_<name>"
crate-type = ["cdylib", "rlib"]

[dependencies]
classic-<name>-core = { path = "../../business-logic/classic-<name>-core" }
classic-shared-core = { path = "../../foundation/classic-shared-core" }
pyo3 = { workspace = true }
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

Python errors are typed exceptions, not sentinels — see `docs/api/error-contract.md`
for how this differs from the C++ and Node surfaces.

### 2.4 Create Type Stub (.pyi)

```python
# python-bindings/classic-<name>-py/classic_<name>.pyi
"""Type stubs for classic_<name> Rust module."""

__version__: str

class Rust<Name>Error(Exception):
    """Base exception for <name> operations."""
    ...

# Add class and function stubs here
```

### 2.5 Add to Workspace

Edit the repo-root `Cargo.toml`:
```toml
members = [
    # ... existing members ...
    # Python Bindings
    "python-bindings/classic-<name>-py",
]
```

## Step 3: Extend The Other Binding Surfaces

A `-core` crate exposing new public API is not complete when only Python is wired up.
Rule 4 treats Rust core and all supported bindings as one change surface, and this holds
even when no current consumer uses the capability yet.

- `cpp-bindings/classic-cpp-bridge/` — add the `#[cxx::bridge]` items, then run the CXX
  parity gate and refresh `docs/implementation/cxx_api_parity/baseline/`.
- `node-bindings/classic-node/` — add the NAPI-RS exports, refresh `index.d.ts`, and run
  the Node parity gate.
- `python-bindings/` — run the Python parity gate and stub validation.

The `classic-project-guide` skill holds the exact gate commands for all three.

## Step 4: Write Tests

### 4.1 Rust Unit Tests

Unit tests live in a sibling `<stem>_tests.rs` file, not inside an inline
`mod tests { ... }` block. See `openspec/specs/rust-test-module-layout/spec.md`
for the workspace-wide rule.

In `business-logic/classic-<name>-core/src/lib.rs`, declare the sibling module:
```rust
#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
```

Then put the test bodies in `business-logic/classic-<name>-core/src/lib_tests.rs`:
```rust
use super::*;

#[test]
fn test_basic_functionality() {
    // Test implementation
}

#[tokio::test]
async fn test_async_functionality() {
    // Async test implementation
}
```

For additional modules with tests (`src/foo.rs`), follow the same pattern:
declare `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;` in `foo.rs` and
put the test bodies in a sibling `foo_tests.rs`. Do NOT create fresh inline
`#[cfg(test)] mod tests { ... }` blocks in new source files.

Cargo integration tests under the crate's own `tests/` directory are out of scope
for this rule and stay where they are.

### 4.2 Python Binding Tests

Add tests under `python-bindings/tests/`. They run against maturin-built wheels, so
follow the build-then-test order in `CLAUDE.md` — pytest collection fails with
`ModuleNotFoundError` if the `-py` crate has not been rebuilt into the venv.

```python
"""Tests for the classic_<name> Rust module."""

def test_rust_module_loads():
    """Verify the Rust module can be imported."""
    import classic_<name>
    assert hasattr(classic_<name>, "__version__")
```

## Checklist

- [ ] Business logic crate created in `business-logic/`
- [ ] Python bindings crate created in `python-bindings/`
- [ ] Both crates added to the repo-root `Cargo.toml` workspace
- [ ] Dependency versions inherited from `[workspace.dependencies]` where available
- [ ] `.pyi` stub file created for type hints
- [ ] Crate-level documentation (`//!`) in both crates
- [ ] All public items have `///` doc comments
- [ ] Unit tests in sibling `_tests.rs` files in the `-core` crate
- [ ] C++ bridge and Node surfaces updated for any new public API (rule 4)
- [ ] All three parity gates run; affected baselines refreshed
- [ ] `docs/api/` page added or updated for the new public contract (rule 8)
