# Migration Plan: serde_yaml → saphyr

## Executive Summary

This document outlines the migration strategy for replacing the deprecated `serde_yaml` crate with `saphyr`, a modern YAML 1.2-compliant library. The migration will eliminate unsafe code dependencies while maintaining full API compatibility with existing Python code.

**Timeline Estimate**: 2-3 days
**Risk Level**: Medium (requires careful testing due to PyO3 integration)
**Breaking Changes**: None (internal implementation change only)

---

## 1. Background

### Current State
- **Crate**: `serde_yaml` v0.9.34+deprecated
- **Status**: Deprecated, relies on unsafe `libyaml` bindings
- **Usage**: Single module (`classic-rust/src/yaml/mod.rs`)
- **Integration**: PyO3 0.26.0 Python bindings
- **Features Used**:
  - Basic parsing (`serde_yaml::from_str`)
  - Basic serialization (`serde_yaml::to_string`)
  - Value types (`Value`, `Mapping`, `Sequence`)
  - Tagged value support (`Value::Tagged`)
  - Python ↔ YAML type conversion

### Why Migrate?
1. ✅ **Safety**: Pure Rust implementation, no unsafe FFI to libyaml
2. ✅ **Modern**: YAML 1.2 compliance (vs YAML 1.1 in serde_yaml)
3. ✅ **Maintained**: Active development, not deprecated
4. ✅ **Features**: Better tag handling, flexible parsing control

---

## 2. API Comparison

### Type Mappings

| serde_yaml | saphyr | Notes |
|------------|--------|-------|
| `Value` | `Yaml` | Core type for YAML nodes |
| `Value::Null` | `Yaml::Null` | Direct mapping |
| `Value::Bool(b)` | `Yaml::Boolean(b)` | Direct mapping |
| `Value::Number(n)` | `Yaml::Integer(i)` or `Yaml::Real(s)` | Requires number type detection |
| `Value::String(s)` | `Yaml::String(s)` | Direct mapping |
| `Value::Sequence(v)` | `Yaml::Array(v)` | Direct mapping |
| `Value::Mapping(m)` | `Yaml::Hash(m)` | Key type: `IndexMap<Yaml, Yaml>` vs `Mapping` |
| `Value::Tagged(t)` | Custom handling | Requires different approach |

### API Patterns

#### Parsing
```rust
// OLD (serde_yaml)
let value: Value = serde_yaml::from_str(content)?;

// NEW (saphyr)
use saphyr::{Yaml, YamlLoader};
let docs = YamlLoader::load_from_str(content)?;
let value = &docs[0]; // First document
```

#### Serialization
```rust
// OLD (serde_yaml)
let yaml_str = serde_yaml::to_string(&value)?;

// NEW (saphyr)
use saphyr::YamlEmitter;
let mut out_str = String::new();
let mut emitter = YamlEmitter::new(&mut out_str);
emitter.dump(value)?;
```

#### Type Checking
```rust
// OLD (serde_yaml)
match value {
    Value::Number(n) => {
        if let Some(i) = n.as_i64() { /* int */ }
        else if let Some(f) = n.as_f64() { /* float */ }
    }
    // ...
}

// NEW (saphyr)
match value {
    Yaml::Integer(i) => { /* int */ }
    Yaml::Real(s) => {
        let f: f64 = s.parse().unwrap_or(0.0);
        /* float */
    }
    // ...
}
```

---

## 3. Migration Strategy

### Phase 1: Preparation (4 hours) ✅ COMPLETE

#### 1.1 Update Dependencies
**File**: `classic-rust/Cargo.toml`

```toml
[dependencies]
# OLD: Remove serde_yaml
# serde_yaml = "0.9"  # DEPRECATED

# NEW: Add saphyr
saphyr = "0.0.6"  # Latest stable version

# Keep these (saphyr works with or without serde)
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

#### 1.2 Research Tasks
- [x] Review saphyr docs for advanced features
- [x] Check saphyr's handling of:
  - [x] Multi-document YAML files
  - [x] Custom tags
  - [x] Anchor/alias resolution
  - [x] Error types and messages
- [x] Identify edge cases in current implementation

---

### Phase 2: Core Type Migration (8 hours)

#### 2.1 Update Imports and Types
**File**: `classic-rust/src/yaml/mod.rs`

```rust
// OLD imports
use serde_yaml::{Mapping, Value};

// NEW imports
use saphyr::{Yaml, YamlLoader, YamlEmitter};
use indexmap::IndexMap;  // For Yaml::Hash
```

#### 2.2 Replace Value Type
**Strategy**: Create type alias for smoother transition

```rust
// Internal type for YAML values
type YamlValue = Yaml;

// Helper to convert between owned/borrowed
// (saphyr has both Yaml and YamlOwned)
fn to_owned(yaml: &Yaml) -> Yaml {
    yaml.clone()  // Yaml implements Clone
}
```

#### 2.3 Update Cached Data Structure
```rust
#[derive(Clone)]
struct CachedYaml {
    data: Arc<Yaml>,  // Changed from Arc<Value>
    modified: SystemTime,
    raw_content: Option<String>,
}
```

---

### Phase 3: Parser Implementation (6 hours)

#### 3.1 Update `parse_yaml` Method

```rust
/// Parse YAML content from a string
#[pyo3(signature = (content))]
fn parse_yaml(&self, py: Python<'_>, content: &str) -> PyResult<Py<PyAny>> {
    // Load YAML documents
    let docs = YamlLoader::load_from_str(content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to parse YAML: {}", e)
        ))?;

    // Get first document (most common case)
    // TODO: Handle multi-document YAML if needed
    let yaml = docs.first()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Empty YAML document"
        ))?;

    self.yaml_to_python(py, yaml)
}
```

#### 3.2 Update `load_yaml_file` Method

```rust
fn load_yaml_file(&self, py: Python<'_>, path: &str) -> PyResult<Py<PyAny>> {
    let file_path = PathBuf::from(path);

    // Check cache (same logic)
    if self.cache_enabled {
        if let Some(cached) = YAML_CACHE.get(&file_path) {
            if let Ok(metadata) = std::fs::metadata(&file_path) {
                if let Ok(modified) = metadata.modified() {
                    if modified <= cached.modified {
                        return self.yaml_to_python(py, &cached.data);
                    }
                }
            }
        }
    }

    // Read file
    let content = std::fs::read_to_string(&file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to read file {}: {}", path, e)
        ))?;

    // Parse with saphyr
    let docs = YamlLoader::load_from_str(&content)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to parse YAML from {}: {}", path, e)
        ))?;

    let yaml = docs.first()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Empty YAML document in {}", path)
        ))?;

    // Update cache
    if self.cache_enabled {
        if let Ok(metadata) = std::fs::metadata(&file_path) {
            if let Ok(modified) = metadata.modified() {
                YAML_CACHE.insert(
                    file_path.clone(),
                    CachedYaml {
                        data: Arc::new(yaml.clone()),
                        modified,
                        raw_content: Some(content),
                    },
                );
            }
        }
    }

    self.yaml_to_python(py, yaml)
}
```

---

### Phase 4: Serializer Implementation (6 hours)

#### 4.1 Update `dump_yaml` Method

```rust
/// Convert data to YAML string with format preservation
#[pyo3(signature = (data))]
fn dump_yaml(&self, py: Python<'_>, data: Py<PyAny>) -> PyResult<String> {
    let yaml = self.python_to_yaml(py, data)?;

    // Serialize with saphyr
    let mut out_str = String::new();
    let mut emitter = YamlEmitter::new(&mut out_str);

    emitter.dump(&yaml)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to serialize YAML: {}", e)
        ))?;

    Ok(out_str)
}
```

#### 4.2 Update `save_yaml_file` Method

```rust
fn save_yaml_file(&self, py: Python<'_>, path: &str, data: Py<PyAny>) -> PyResult<()> {
    let yaml = self.python_to_yaml(py, data)?;

    // Serialize
    let mut yaml_str = String::new();
    let mut emitter = YamlEmitter::new(&mut yaml_str);
    emitter.dump(&yaml)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to serialize YAML: {}", e)
        ))?;

    // Atomic write (same pattern)
    let file_path = PathBuf::from(path);
    let temp_path = file_path.with_extension("yaml.tmp");

    std::fs::write(&temp_path, yaml_str.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to write temp file: {}", e)
        ))?;

    std::fs::rename(&temp_path, &file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
            format!("Failed to rename file: {}", e)
        ))?;

    // Invalidate cache
    if self.cache_enabled {
        YAML_CACHE.remove(&file_path);
    }

    Ok(())
}
```

---

### Phase 5: Type Conversion Implementation (8 hours)

#### 5.1 Update `yaml_to_python` Method

```rust
/// Convert saphyr Yaml to Python object
fn yaml_to_python(&self, py: Python, yaml: &Yaml) -> PyResult<Py<PyAny>> {
    match yaml {
        Yaml::Null => Ok(py.None()),

        Yaml::Boolean(b) => Ok((*b).into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Integer(i) => Ok((*i).into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Real(s) => {
            // Parse string to f64
            let f = s.parse::<f64>()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid float: {}", e)
                ))?;
            Ok(f.into_pyobject(py)?.as_any().clone().unbind())
        }

        Yaml::String(s) => Ok(s.as_str().into_pyobject(py)?.as_any().clone().unbind()),

        Yaml::Array(arr) => {
            let mut items = Vec::new();
            for item in arr {
                items.push(self.yaml_to_python(py, item)?);
            }
            let list = pyo3::types::PyList::new(py, items)?;
            Ok(list.unbind().into())
        }

        Yaml::Hash(hash) => {
            let dict = pyo3::types::PyDict::new(py);
            for (k, v) in hash {
                // Convert key (usually string, but can be any YAML type)
                let key_obj = self.yaml_to_python(py, k)?;
                let val_obj = self.yaml_to_python(py, v)?;
                dict.set_item(key_obj, val_obj)?;
            }
            Ok(dict.unbind().into())
        }

        Yaml::Alias(_) => {
            // Aliases should be resolved during parsing
            // If we see one here, it's an error
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unresolved YAML alias"
            ))
        }

        Yaml::BadValue => {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid YAML value"
            ))
        }
    }
}
```

#### 5.2 Update `python_to_yaml` Method

```rust
/// Convert Python object to saphyr Yaml
fn python_to_yaml(&self, py: Python, obj: Py<PyAny>) -> PyResult<Yaml> {
    let bound_obj = obj.bind(py);

    if bound_obj.is_none() {
        return Ok(Yaml::Null);
    }

    if let Ok(b) = bound_obj.extract::<bool>() {
        return Ok(Yaml::Boolean(b));
    }

    if let Ok(i) = bound_obj.extract::<i64>() {
        return Ok(Yaml::Integer(i));
    }

    if let Ok(f) = bound_obj.extract::<f64>() {
        // Store as Real (string representation)
        return Ok(Yaml::Real(f.to_string()));
    }

    if let Ok(s) = bound_obj.extract::<String>() {
        return Ok(Yaml::String(s));
    }

    if let Ok(list) = bound_obj.downcast::<pyo3::types::PyList>() {
        let mut arr = Vec::new();
        for item in list.iter() {
            arr.push(self.python_to_yaml(py, item.unbind())?);
        }
        return Ok(Yaml::Array(arr));
    }

    if let Ok(dict) = bound_obj.downcast::<pyo3::types::PyDict>() {
        let mut hash = IndexMap::new();
        for (k, v) in dict.iter() {
            let key = self.python_to_yaml(py, k.unbind())?;
            let value = self.python_to_yaml(py, v.unbind())?;
            hash.insert(key, value);
        }
        return Ok(Yaml::Hash(hash));
    }

    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
        format!("Cannot convert Python type to YAML: {:?}", bound_obj.get_type())
    ))
}
```

---

### Phase 6: Settings Navigation (4 hours)

#### 6.1 Update `get_setting` Method

```rust
#[pyo3(signature = (data, key_path))]
fn get_setting(&self, py: Python<'_>, data: Py<PyAny>, key_path: &str) -> PyResult<Option<Py<PyAny>>> {
    let yaml = self.python_to_yaml(py, data)?;

    // Navigate through the key path
    let keys: Vec<&str> = key_path.split('.').collect();
    let mut current = &yaml;

    for key in keys {
        match current {
            Yaml::Hash(hash) => {
                // Try to find by string key
                let key_yaml = Yaml::String(key.to_string());
                if let Some(next_value) = hash.get(&key_yaml) {
                    current = next_value;
                } else {
                    return Ok(None);
                }
            }
            _ => return Ok(None),
        }
    }

    Ok(Some(self.yaml_to_python(py, current)?))
}
```

#### 6.2 Update `set_setting` Method

```rust
#[pyo3(signature = (data, key_path, value))]
fn set_setting(&self, py: Python<'_>, data: Py<PyAny>, key_path: &str, value: Py<PyAny>) -> PyResult<Py<PyAny>> {
    // Check for empty key path
    if key_path.trim().is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Empty key path"));
    }

    let mut root_yaml = self.python_to_yaml(py, data)?;
    let new_value = self.python_to_yaml(py, value)?;

    // Navigate and create path if necessary
    let keys: Vec<&str> = key_path.split('.').collect();
    let last_key = keys.last()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Empty key path"))?;

    // Helper function to ensure we have a mutable hash
    fn ensure_hash(yaml: &mut Yaml) -> &mut IndexMap<Yaml, Yaml> {
        if !matches!(yaml, Yaml::Hash(_)) {
            *yaml = Yaml::Hash(IndexMap::new());
        }
        match yaml {
            Yaml::Hash(h) => h,
            _ => unreachable!(),
        }
    }

    // Navigate to parent of last key
    let mut current = &mut root_yaml;
    for key in &keys[..keys.len() - 1] {
        let key_yaml = Yaml::String(key.to_string());
        let hash = ensure_hash(current);
        current = hash.entry(key_yaml)
            .or_insert(Yaml::Hash(IndexMap::new()));
    }

    // Set the final value
    let hash = ensure_hash(current);
    hash.insert(Yaml::String(last_key.to_string()), new_value);

    self.yaml_to_python(py, &root_yaml)
}
```

---

### Phase 7: Testing (10 hours)

#### 7.1 Unit Tests (Rust)
**Strategy**: All existing tests in `classic-rust/tests/test_yaml.rs` should pass

```bash
# Run Rust tests
cd classic-rust
cargo test --test test_yaml --all-features -- --nocapture
```

**Expected**: All 40+ test functions should pass without modification

#### 7.2 Integration Tests (Python)
**Strategy**: All tests in `tests/rust_integration/test_yaml_parity.py` should pass

```bash
# Run Python integration tests
uv run pytest tests/rust_integration/test_yaml_parity.py -v
```

**Expected**: All test classes should pass

#### 7.3 Edge Case Testing
Create new tests for saphyr-specific behaviors:

```rust
#[test]
fn test_multi_document_yaml() {
    // Test multi-doc YAML (--- separator)
    let yaml = "---\nfirst: doc\n---\nsecond: doc";
    // Verify we handle multiple documents correctly
}

#[test]
fn test_yaml_anchors_and_aliases() {
    // Test anchor/alias resolution
    let yaml = "anchor: &ref\n  value: 42\nalias: *ref";
    // Verify aliases are resolved
}

#[test]
fn test_custom_tags() {
    // Test custom YAML tags
    let yaml = "!custom tag value";
    // Verify tag handling
}
```

#### 7.4 Performance Testing
```rust
#[test]
fn benchmark_parse_vs_serde_yaml() {
    // Compare parsing speed
    // Saphyr should be competitive or faster
}
```

---

### Phase 8: Documentation & Cleanup (3 hours)

#### 8.1 Update Module Documentation
```rust
//! High-performance YAML operations for CLASSIC
//!
//! This module provides Rust-accelerated YAML parsing and writing operations using
//! the saphyr crate, offering 15-30x performance improvements over Python's ruamel.yaml
//! while maintaining full API compatibility and format preservation.
//!
//! ## YAML 1.2 Compliance
//! Uses saphyr for YAML 1.2 specification compliance and pure Rust safety.
//!
//! ## ONE RUNTIME RULE Compliance
//! This module uses crate::get_runtime() for all async operations.
```

#### 8.2 Update CLAUDE.md
```markdown
### Rust YAML Operations
- **Library**: saphyr (YAML 1.2 compliant, pure Rust)
- **Previous**: serde_yaml (deprecated)
- **Migration**: Completed YYYY-MM-DD
- **Features**:
  - Multi-document support
  - Anchor/alias resolution
  - Custom tag handling
  - Pure Rust safety (no unsafe FFI)
```

#### 8.3 Create Migration Notes
**File**: `docs/saphyr_migration_notes.md`

Document:
- API differences from serde_yaml
- Breaking changes (if any)
- Performance improvements
- New features available

---

## 4. Risk Assessment & Mitigation

### Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| API incompatibility | High | Low | Extensive test coverage, backward compat layer |
| Performance regression | Medium | Low | Benchmark before/after, saphyr is pure Rust |
| Float precision changes | Low | Medium | Test float roundtripping, document differences |
| Multi-doc YAML handling | Low | Low | Current code only uses single-doc, verify assumption |
| PyO3 integration issues | Medium | Low | Incremental migration, test each phase |

### Rollback Plan

If migration fails:
1. Revert `Cargo.toml` changes
2. Restore original `yaml/mod.rs`
3. Rebuild: `maturin build --release`
4. Reinstall: `uv pip install dist/classic-*.whl --force-reinstall`

**Git Strategy**: Create feature branch `feature/migrate-to-saphyr`
```bash
git checkout -b feature/migrate-to-saphyr
# ... make changes ...
git commit -m "WIP: Migrate to saphyr (phase N)"
```

Only merge to `classic-next` after **all tests pass**.

---

## 5. Success Criteria

### Required for Merge
- [ ] All Rust unit tests pass (`cargo test --test test_yaml`)
- [ ] All Python integration tests pass (`pytest tests/rust_integration/test_yaml_parity.py`)
- [ ] All existing Python tests pass (`pytest -n auto`)
- [ ] No performance regression (benchmark comparison)
- [ ] Documentation updated
- [ ] No deprecation warnings (`cargo build` clean)

### Nice to Have
- [ ] Performance improvement measured and documented
- [ ] New tests for saphyr-specific features
- [ ] Migration guide for future reference

---

## 6. Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Preparation | 4 hours | None |
| 2. Core Type Migration | 8 hours | Phase 1 |
| 3. Parser Implementation | 6 hours | Phase 2 |
| 4. Serializer Implementation | 6 hours | Phase 2 |
| 5. Type Conversion | 8 hours | Phases 3, 4 |
| 6. Settings Navigation | 4 hours | Phase 5 |
| 7. Testing | 10 hours | Phases 1-6 |
| 8. Documentation | 3 hours | Phase 7 |
| **Total** | **49 hours** (~2-3 days) | - |

**Recommended Schedule**:
- Day 1: Phases 1-3 (preparation, types, parser)
- Day 2: Phases 4-6 (serializer, conversion, settings)
- Day 3: Phases 7-8 (testing, documentation)

---

## 7. Key Considerations

### Floating Point Numbers
**serde_yaml**: Uses `serde_yaml::Number` which preserves precision
**saphyr**: Uses `Yaml::Real(String)` - string representation

**Impact**: Minor formatting differences in float serialization
**Mitigation**: Test roundtrip precision, document format differences

### Hash Map Ordering
**serde_yaml**: Uses custom `Mapping` type
**saphyr**: Uses `IndexMap<Yaml, Yaml>` (preserves insertion order)

**Impact**: Better order preservation
**Benefit**: Matches Python dict behavior (3.7+)

### Error Messages
**serde_yaml**: Generic error messages
**saphyr**: More detailed parse errors with line/column info

**Impact**: Better debugging experience
**Benefit**: Clearer error messages for users

### Multi-Document Support
**Current**: Only first document used
**saphyr**: Returns `Vec<Yaml>` from parsing

**Decision**: Continue using first document, but add TODO for future multi-doc support

---

## 8. Testing Checklist

### Pre-Migration
- [ ] Baseline performance benchmark
- [ ] Document current test coverage
- [ ] Identify edge cases in production usage

### During Migration
- [ ] Compile without errors after each phase
- [ ] Run relevant tests after each phase
- [ ] Document any unexpected behaviors

### Post-Migration
- [ ] Full test suite passes
- [ ] Performance benchmark comparison
- [ ] Manual testing of YAML file operations
- [ ] Integration test with production YAML files

---

## 9. Implementation Notes

### Important Files
```
classic-rust/
├── Cargo.toml                          # Update dependencies
├── src/
│   └── yaml/
│       └── mod.rs                      # Main migration file
└── tests/
    └── test_yaml.rs                    # Rust unit tests

tests/
└── rust_integration/
    └── test_yaml_parity.py             # Python integration tests
```

### Build Commands
```bash
# Clean build
cargo clean
cargo build --release

# Build wheel
cd classic-rust
maturin build --release --out dist

# Install
cd ..
uv pip install classic-rust/dist/classic-*.whl --force-reinstall

# Verify
python -c "from classic_core.yaml import RustYamlOperations; print('OK')"
```

### Debugging Tips
```rust
// Add debug output
println!("DEBUG: yaml value = {:?}", yaml);

// Enable saphyr logging
env_logger::init();
std::env::set_var("RUST_LOG", "debug");
```

---

## 10. Post-Migration Tasks

### Immediate (within 1 week)
- [ ] Monitor production usage for issues
- [ ] Update performance documentation
- [ ] Create blog post / changelog entry

### Future Enhancements
- [ ] Multi-document YAML support
- [ ] Custom tag handlers
- [ ] Streaming YAML parser for large files
- [ ] YAML schema validation

---

## Appendix A: Saphyr API Quick Reference

### Basic Types
```rust
pub enum Yaml {
    Null,
    Boolean(bool),
    Integer(i64),
    Real(String),       // Float as string
    String(String),
    Array(Vec<Yaml>),
    Hash(IndexMap<Yaml, Yaml>),
    Alias(usize),       // Reference to anchor
    BadValue,           // Parse error
}
```

### Parsing
```rust
use saphyr::YamlLoader;

let docs = YamlLoader::load_from_str(content)?;
let yaml = &docs[0];  // First document
```

### Serialization
```rust
use saphyr::YamlEmitter;

let mut out = String::new();
let mut emitter = YamlEmitter::new(&mut out);
emitter.dump(&yaml)?;
```

### Type Checking
```rust
yaml.is_null()
yaml.is_boolean()
yaml.as_bool()
yaml.as_i64()
yaml.as_f64()  // Parses Real string to f64
yaml.as_str()
yaml.as_vec()
yaml.as_hash()
```

---

## Appendix B: Common Gotchas

### 1. Multiple Documents
```yaml
---
first: document
---
second: document
```
**saphyr**: Returns `Vec<Yaml>` with 2 elements
**Current code**: Only uses first document

### 2. Float Representation
```rust
// serde_yaml
Value::Number(3.14.into())

// saphyr
Yaml::Real("3.14".to_string())
```

### 3. Hash Key Types
```rust
// serde_yaml: Mapping is Value -> Value
// saphyr: IndexMap is Yaml -> Yaml

// Both support non-string keys, but indexing differs
```

### 4. Error Types
```rust
// serde_yaml
serde_yaml::Error

// saphyr
saphyr::ScanError (parsing)
std::fmt::Error (emitting)
```

---

## Appendix C: Performance Benchmarks

### Expected Performance
- **Parsing**: Similar or faster (pure Rust vs FFI overhead)
- **Serialization**: Similar (both are Rust implementations)
- **Memory**: Potentially lower (no FFI marshaling)

### Benchmark Code
```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn benchmark_parse(c: &mut Criterion) {
    let yaml_content = include_str!("../test_data/large.yaml");

    c.bench_function("saphyr parse", |b| {
        b.iter(|| {
            let docs = YamlLoader::load_from_str(black_box(yaml_content)).unwrap();
            black_box(docs);
        });
    });
}

criterion_group!(benches, benchmark_parse);
criterion_main!(benches);
```

---

## Questions for Review

1. **Multi-document support**: Should we support multiple YAML documents in one file?
   - Current: Only first document
   - Proposal: Add optional parameter to choose document index

2. **Custom tags**: Do we need custom YAML tag handling?
   - Current: Not used
   - Future: Potential use case?

3. **Float precision**: Are the current float tests sufficient?
   - Concern: String-based float storage in saphyr
   - Mitigation: Add precision tests

4. **Error messages**: Should we preserve exact error message format?
   - Concern: Python tests may check error strings
   - Mitigation: Update test assertions if needed

---

## Approval Checklist

Before starting migration:
- [ ] Review implementation plan
- [ ] Confirm timeline acceptable
- [ ] Identify any blockers
- [ ] Assign owner

Before merging:
- [ ] Code review completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance verified

---

**Document Version**: 1.0
**Last Updated**: 2025-10-02
**Status**: Ready for Review
