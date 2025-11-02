# Rust Workspace Architecture

This guide covers the modular Cargo workspace structure for CLASSIC's Rust components.

## Architecture Rules (NEW - 2025-10-08)

**CRITICAL**: All new Rust code MUST follow the separated architecture pattern:

### 1. Business Logic Crates (`*-core`)
- `crate-type = ["rlib"]` - Pure Rust library only
- **NO PyO3 dependency** - Must compile without PyO3
- Contains all algorithms, data structures, and logic
- Can be used by CLI/TUI applications directly
- Example: `rust/business-logic/classic-yaml-core`, `rust/business-logic/classic-scanlog-core`

### 2. Python Binding Crates (`*-py`)
- `crate-type = ["cdylib"]` - Python extension only
- Depends on corresponding `-core` crate
- Thin adapter layer converting Python ↔ Rust types
- Should be **minimal** - only type conversions and `#[pyclass]`/`#[pymethods]` wrappers
- No business logic - all algorithms/data structures belong in `-core`
- Example: `rust/python-bindings/classic-yaml-py`, `rust/python-bindings/classic-scanlog-py`

### 3. Naming Convention
- Business logic: `classic-{name}-core`
- Python bindings: `classic-{name}-py`
- Python module name: `classic_{name}` (in Cargo.toml `[lib]` section)

### 4. Migration Status
- ✅ **New crates created**: All `-core` and `-py` crates exist as of Phase 0
- 🔄 **Legacy crates**: `classic-yaml`, `classic-database`, `classic-file-io`, `classic-scanlog` being phased out

## Example Structure

```toml
# rust/business-logic/classic-yaml-core/Cargo.toml (Business Logic)
[lib]
crate-type = ["rlib"]  # Pure Rust

[dependencies]
classic-shared = { path = "../classic-shared" }
yaml-rust2 = { workspace = true }
# NO pyo3!

# rust/python-bindings/classic-yaml-py/Cargo.toml (Python Bindings)
[lib]
name = "classic_yaml"  # Python module name
crate-type = ["cdylib"]

[dependencies]
rust/business-logic/classic-yaml-core = { path = "../rust/business-logic/classic-yaml-core" }
pyo3 = { workspace = true }
```

## Workspace Directory Structure

CLASSIC uses a modular Cargo workspace with separated business logic and Python bindings:

```
.
├── Cargo.toml                       # Workspace root with shared dependencies
│
├── classic-shared/                  # Foundation (runtime, errors, utilities)
│   └── src/runtime.rs              # Global Tokio runtime (ONE RUNTIME RULE)
│
├── rust/business-logic/classic-yaml-core/               # YAML business logic (pure Rust)
│   └── src/lib.rs                  # YamlOperations
├── rust/python-bindings/classic-yaml-py/                 # YAML Python bindings (PyO3)
│   └── src/lib.rs                  # PyYamlOperations wrapper
│
├── rust/business-logic/classic-database-core/           # Database business logic (pure Rust)
│   └── src/lib.rs                  # DatabasePool, FormID lookups
├── rust/python-bindings/classic-database-py/             # Database Python bindings (PyO3)
│   └── src/lib.rs                  # PyDatabasePool wrapper
│
├── rust/business-logic/classic-file-io-core/            # File I/O business logic (pure Rust)
│   └── src/lib.rs                  # FileIOCore, encoding, DDS
├── rust/python-bindings/classic-file-io-py/              # File I/O Python bindings (PyO3)
│   └── src/lib.rs                  # RustFileIOCore wrapper
│
├── rust/business-logic/classic-scanlog-core/            # Scanlog business logic (pure Rust)
│   └── src/lib.rs                  # LogParser, FormIDAnalyzer, etc.
├── rust/python-bindings/classic-scanlog-py/              # Scanlog Python bindings (PyO3)
│   └── src/lib.rs                  # Rust*Parser wrappers
│
├── rust/python-bindings/classic-config-py/               # Config Python bindings (PyO3)
│   └── src/lib.rs                  # YamlData wrapper
├── rust/business-logic/classic-config-core/             # Config business logic (pure Rust)
│   └── src/lib.rs                  # Configuration management
│
├── classic-core/                    # Facade (re-exports all -py modules)
│   └── src/lib.rs                  # Python entry point
│
└── [Legacy crates being phased out]
    ├── classic-yaml/                # To be replaced by rust/python-bindings/classic-yaml-py
    ├── classic-database/            # To be replaced by rust/python-bindings/classic-database-py
    ├── classic-file-io/             # To be replaced by rust/python-bindings/classic-file-io-py
    └── classic-scanlog/             # To be replaced by rust/python-bindings/classic-scanlog-py
```

## Dependency Hierarchy (New Architecture)

```
┌─────────────────────────────────────────────┐
│  Python Application Layer                   │
│  - Python imports classic_core              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Python Bindings Layer (-py crates)        │
│  rust/python-bindings/classic-yaml-py, rust/python-bindings/classic-database-py       │
│  rust/python-bindings/classic-file-io-py, rust/python-bindings/classic-scanlog-py    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Business Logic Layer (-core crates)       │
│  rust/business-logic/classic-yaml-core, rust/business-logic/classic-database-core   │
│  rust/business-logic/classic-file-io-core, rust/business-logic/classic-scanlog-core│
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Foundation Layer                           │
│  classic-shared (runtime, errors)          │
└─────────────────────────────────────────────┘
```

## Key Rules

- **NO circular dependencies** between crates
- **ONE RUNTIME RULE**: All crates use `classic_shared::get_runtime()`
- **SEPARATION OF CONCERNS**: `-core` crates have NO PyO3, `-py` crates are thin adapters
- **Workspace dependencies**: Centralized in root `Cargo.toml`
- **CLI/TUI applications**: Use `-core` crates directly (bypass Python bindings)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
