# Rust-Python Integration Improvement Plan

**Status**: Active Development
**Priority**: High
**Estimated Duration**: 2 weeks
**Last Updated**: 2025-11-06

## Executive Summary

This document outlines a strategy to eliminate API discrepancies between Rust and Python components in the CLASSIC codebase. We'll make breaking changes directly without backward compatibility, resulting in cleaner, faster, and more maintainable integration.

## Problem Statement

Current integration issues:

1. **Type Conversion Overhead**: 30-50% performance loss in batch operations
2. **Async/Sync Confusion**: Misleading function signatures
3. **Inconsistent Error Handling**: Generic exceptions lose context
4. **Manual Stub Maintenance**: `.pyi` files drift from implementation
5. **Naming Inconsistencies**: Mix of prefixes and conventions

## Goals

1. **Eliminate friction** at the Rust-Python boundary
2. **Improve performance** by removing unnecessary conversions
3. **Enhance debugging** through proper error types
4. **Automate stub generation** to prevent drift
5. **Standardize naming** across all modules

## Implementation Phases

### Phase 1: Foundation (Week 1)

#### 1.1 Standardize Error Handling

**Problem**: Rust errors → generic `RuntimeError`, losing context.

**Solution**: Typed exception hierarchy mapping Rust errors to specific Python types.

**Implementation**:
```python
# ClassicLib/integration/exceptions.py
class RustError(Exception):
    """Base for all Rust errors."""

class RustIOError(RustError, IOError):
    """File I/O errors."""

class RustParseError(RustError, ValueError):
    """Parsing errors."""

class RustConfigError(RustError, ValueError):
    """Configuration errors."""

class RustDatabaseError(RustError):
    """Database errors."""
```

```rust
// In each -py crate
use pyo3::create_exception;

create_exception!(classic_yaml, RustYamlError, PyException);
create_exception!(classic_yaml, RustParseError, RustYamlError);

fn to_pyerr(err: CoreError) -> PyErr {
    match err {
        CoreError::Io(e) => RustIOError::new_err(format!("I/O: {}", e)),
        CoreError::Parse(e) => RustParseError::new_err(format!("Parse: {}", e)),
        _ => RustYamlError::new_err(err.to_string()),
    }
}
```

**Files**:
- New: `ClassicLib/integration/exceptions.py`
- Update: All `-py` crates error conversion
- Update: All wrapper modules exception handling

#### 1.2 Add pathlib.Path Support

**Problem**: Manual `str(path)` conversions everywhere.

**Solution**: PyO3 `FromPyObject` for `pathlib.Path`.

**Implementation**:
```rust
// classic-shared-py/src/path.rs
use pyo3::prelude::*;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct PathLike(pub PathBuf);

impl<'source> FromPyObject<'source> for PathLike {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        // Try __fspath__() protocol (pathlib.Path)
        if let Ok(path_obj) = ob.call_method0("__fspath__") {
            let path_str: String = path_obj.extract()?;
            return Ok(PathLike(PathBuf::from(path_str)));
        }

        // Fall back to str/bytes
        if let Ok(s) = ob.extract::<String>() {
            Ok(PathLike(PathBuf::from(s)))
        } else {
            Err(PyTypeError::new_err("Expected str or Path"))
        }
    }
}
```

**Files**:
- Update: `rust/foundation/classic-shared-py/src/lib.rs`
- Update: All `-py` crates to use `PathLike`
- Remove: `str()` calls from Python wrappers

#### 1.3 Integrate pyo3-stub-gen

**Problem**: Manual `.pyi` files drift from Rust.

**Solution**: Auto-generate stubs with `pyo3-stub-gen`.

**Implementation**:
```python
# scripts/generate_stubs.py
import subprocess
from pathlib import Path

CRATES = [
    "rust/python-bindings/classic-yaml-py",
    "rust/python-bindings/classic-scanlog-py",
    "rust/python-bindings/classic-file-io-py",
    # ... all -py crates
]

def generate_stub(crate_path: Path) -> None:
    module_name = crate_path.name.replace("-", "_")
    result = subprocess.run(
        ["cargo", "run", "--bin", "pyo3-stub-gen", "--",
         "--module", module_name],
        cwd=crate_path,
        capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Stub gen failed: {result.stderr}")
```

```powershell
# Update rebuild_rust.ps1
# ... build commands ...

Write-Host "Generating stubs..." -ForegroundColor Cyan
uv run python scripts/generate_stubs.py
```

**Files**:
- Update: All `-py` Cargo.toml (add pyo3-stub-gen dev-dep)
- New: `scripts/generate_stubs.py`
- Update: `rebuild_rust.ps1`
- Update: `.github/workflows/ci.yml` (validate stubs)
- Remove: Manual `.pyi` files

#### 1.4 Fix Async Signatures

**Problem**: `async def` functions that actually block.

**Solution**: Remove fake async, mark blocking operations.

**Example**:
```python
# BEFORE:
async def read_file(self, path: Path) -> str:
    return await self._rust_core.read_file(str(path))  # Actually blocks!

# AFTER:
def read_file(self, path: Path) -> str:
    """Read file (blocks on Tokio runtime)."""
    return self._rust_core.read_file(path)
```

**Files**:
- Update: `ClassicLib/rust/file_io_rust.py`
- Update: `ClassicLib/rust/yaml_rust.py`
- Update: All wrappers with misleading async

#### 1.5 Document Type Conversions

**Problem**: Unknown performance costs.

**Solution**: Comprehensive documentation.

**Content**:
```markdown
## Type Conversion Costs

| Python → Rust | Cost | Notes |
|---------------|------|-------|
| `str` → `String` | O(n) | UTF-8 validate + alloc |
| `Path` → `PathBuf` | O(n) | Via `__fspath__()` |
| `list[str]` → `Vec<String>` | O(n×m) | n allocs + m chars |
| `dict[str,str]` → `HashMap<String,String>` | O(n×m) | 2n allocs |

**Guidelines**:
- High-frequency APIs: Use borrowed types (`&str`)
- Batch operations: Process in Rust, not Python
- Avoid nested collections (`list[list[T]]`)
```

**Files**:
- Update: `docs/development/pyo3_integration_patterns.md`
- New: `benchmarks/type_conversion_overhead.py`

---

### Phase 2: Standardization (Week 2)

#### 2.1 Standardize Naming

**Problem**: Mix of `Rust` / `py_` prefixes.

**Solution**: Remove all prefixes, use module names for clarity.

**Changes**:
```python
# BEFORE:
from classic_yaml import RustYamlOperations
from classic_file_io import py_walk_directory

# AFTER:
from classic_yaml import YamlOperations
from classic_file_io import walk_directory
```

**Files**:
- Update: All `-py` crates (rename classes/functions)
- Update: All wrapper modules
- Update: All imports across codebase

#### 2.2 Enhance Cache APIs

**Problem**: No cache control.

**Solution**: Add invalidation, metrics, limits.

**API**:
```python
ops = YamlOperations()

# Configure
ops.configure_cache(max_size=1000, ttl_seconds=300)

# Metrics
stats = ops.get_cache_stats()  # hits, misses, size

# Invalidate
ops.clear_cache(path)  # Specific file
ops.clear_cache()      # All
```

**Files**:
- Update: `rust/business-logic/classic-yaml-core/src/cache.rs`
- Update: `rust/python-bindings/classic-yaml-py/src/lib.rs`

#### 2.3 Optimize Batch Operations

**Problem**: Nested collections = 30-50% overhead.

**Solution**: Zero-copy APIs with flat structures.

**Example**:
```python
# OLD (expensive):
segments: list[list[str]] = parser.extract_formids_batch([s1, s2, s3])

# NEW (efficient):
flat, offsets = parser.extract_formids_batch_flat([s1, s2, s3])
# flat = single list, offsets = [0, 10, 25, 40]
```

**Files**:
- Update: `rust/python-bindings/classic-scanlog-py/src/lib.rs`
- New: `benchmarks/batch_conversion_benchmark.py`

#### 2.4 Centralize Detection

**Problem**: Duplicate detection logic.

**Solution**: Single source in `detector.py`.

**Files**:
- Update: `ClassicLib/integration/detector.py`
- Simplify: All wrapper modules

#### 2.5 Add Runtime Diagnostics

**Problem**: No visibility into Tokio runtime.

**Solution**: Expose metrics.

**API**:
```python
from classic_shared import get_runtime_stats, is_runtime_healthy

if not is_runtime_healthy():
    print("Runtime stalled!")

stats = get_runtime_stats()
print(f"Tasks: {stats.active_tasks}, Threads: {stats.blocked_threads}")
```

**Files**:
- Update: `rust/foundation/classic-shared-py/src/lib.rs`
- New: `ClassicLib/integration/diagnostics.py`

---

## Testing Strategy

### Requirements

1. **Error Tests**: All exception types properly raised
2. **Path Tests**: `pathlib.Path` accepted everywhere
3. **Type Tests**: `mypy --strict` passes with generated stubs
4. **Performance Tests**: No regression from changes
5. **Stub Tests**: CI validates stubs match Rust

### Coverage Goals

- 100% of exception types tested
- 100% of path APIs tested with `Path` objects
- 100% of async/sync signatures validated
- 90%+ wrapper module coverage
- 100% stub accuracy (CI enforced)

### CI Validation

```yaml
# .github/workflows/integration.yml
- name: Build Rust
  run: ./rebuild_rust.ps1

- name: Generate stubs
  run: uv run python scripts/generate_stubs.py

- name: Verify stubs
  run: git diff --exit-code  # Fail if changed

- name: Type check
  run: uv run mypy ClassicLib/ --strict

- name: Integration tests
  run: uv run pytest tests/rust_integration/ -v
```

---

## Success Metrics

### Performance
- Type conversion overhead: 30-50% → <15%
- Overall Rust speedup: Maintain 10-150x
- Batch operations: >20% improvement

### Developer Experience
- Naming: 100% consistent (no prefixes)
- Type safety: 0 mypy errors (strict mode)
- Stub accuracy: 0 discrepancies (CI enforced)

### Quality
- Test coverage: >85%
- Error context: 100% preserved
- Stub maintenance: 0 manual edits

---

## Timeline

### Week 1: Foundation
- Day 1: Error handling + Path support
- Day 2: pyo3-stub-gen integration
- Day 3: Async signature fixes
- Day 4: Documentation
- Day 5: Testing

### Week 2: Standardization
- Day 1: Naming standardization
- Day 2: Cache APIs
- Day 3: Batch optimization
- Day 4: Detection + diagnostics
- Day 5: Final testing + docs

**Total: 10 business days (2 weeks)**

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Error handling hierarchy
  - [ ] Create `exceptions.py`
  - [ ] Update all `-py` crates
  - [ ] Update wrapper modules
  - [ ] Tests

- [ ] pathlib.Path support
  - [ ] Add `PathLike` to `classic-shared-py`
  - [ ] Update all `-py` crates
  - [ ] Remove `str()` from wrappers
  - [ ] Tests

- [ ] pyo3-stub-gen
  - [ ] Add dev dependencies
  - [ ] Create `generate_stubs.py`
  - [ ] Update build scripts
  - [ ] CI validation
  - [ ] Remove manual stubs

- [ ] Async fixes
  - [ ] Audit all wrappers
  - [ ] Remove fake async
  - [ ] Update docs
  - [ ] Tests

- [ ] Document conversions
  - [ ] Type conversion table
  - [ ] Benchmarks
  - [ ] Best practices

### Week 2: Standardization
- [ ] Naming
  - [ ] Remove prefixes from all APIs
  - [ ] Update imports everywhere
  - [ ] Update docs

- [ ] Cache APIs
  - [ ] Invalidation
  - [ ] Metrics
  - [ ] Configuration
  - [ ] Tests

- [ ] Batch optimization
  - [ ] Flat APIs
  - [ ] Benchmarks
  - [ ] Documentation

- [ ] Detection
  - [ ] Centralize logic
  - [ ] Simplify wrappers
  - [ ] Tests

- [ ] Diagnostics
  - [ ] Runtime metrics
  - [ ] Python API
  - [ ] Documentation

---

## References

- [PyO3 Documentation](https://pyo3.rs/v0.26.0/)
- [pyo3-stub-gen](https://github.com/PyO3/pyo3-stub-gen)
- [CLASSIC PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)
