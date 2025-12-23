# Rust Optimization Audit Report
**Date:** 2025-12-22
**Track:** Optimize Python-Rust Integration Layer
**Focus:** `rust/python-bindings/`

## Executive Summary
An audit of the PyO3 bindings revealed no widespread use of `serde_json` for data passing, which is a positive baseline. However, significant overhead exists in string handling, specifically the conversion of `Arc<str>` (internal Rust storage) to `String` (intermediate) to `PyString` (Python). Additionally, error handling relies on string parsing, which is inefficient and brittle.

## Identified High-Overhead Patterns

### 1. Double Allocation in Log Parsing
**Location:** `classic-scanlog-py/src/parser.rs`
**Pattern:** `Vec<Arc<str>>` -> `Vec<String>` -> `PyList<PyString>`

The `parse_segments` method (and others returning collections of strings) converts shared string references to owned `String`s before PyO3 converts them to Python objects.

```rust
// Current Implementation
result
    .into_iter()
    .map(|segment| segment.into_iter().map(|s| s.to_string()).collect()) // Allocation 1: String
    .collect() // Allocation 2: Vec<String> -> PyList takes over
```

**Impact:**
- Creates a temporary heap-allocated `String` for every single line in a crash log.
- For a 10,000 line log, this is 10,000 unnecessary allocations and deallocations.

**Recommendation:**
- Use `PyString::new` directly on the `Arc<str>` or `&str` slice to create the Python object immediately, bypassing the intermediate `String`.

### 2. String-Based Error Classification
**Location:** `classic-scanlog-py/src/lib.rs` (`to_pyerr`)
**Pattern:** Error -> String -> Contains Check -> Exception

Errors are converted to strings, and then `contains()` is used to guess the correct Python exception type.

```rust
pub fn to_pyerr(err: impl std::fmt::Display) -> PyErr {
    let err_str = err.to_string().to_lowercase(); // Allocation + Lowercase
    if err_str.contains("config") ... { ... }
}
```

**Impact:**
- Performance penalty on error paths (less critical but noticeable in tight loops).
- Extremely brittle; changing an error message in Core breaks Exception type in Python.

**Recommendation:**
- Implement `From<CoreError> for PyErr` using distinct enum variants in `classic-shared-core` (Phase 2).

### 3. Recursive YAML Conversion
**Location:** `classic-yaml-py/src/lib.rs`
**Pattern:** Recursive Tree Traversal

The `yaml_to_python` and `python_to_yaml` functions perform a deep recursive copy of the entire data structure.

```rust
Yaml::Real(s) => s.parse::<f64>() // Parsing overhead
Yaml::Real(f.to_string()) // Formatting overhead
```

**Impact:**
- `yaml-rust2` stores reals as Strings, forcing parse/format roundtrips.
- Deep copying large config files is expensive.

**Recommendation:**
- For config files, this is likely acceptable as they are small.
- For large data, consider a zero-copy approach or lazy loading (Phase 3).

### 4. Excessive `to_string()` for PathBuf
**Location:** General usage across all modules
**Pattern:** `path.display().to_string()`

Many bindings convert `PathBuf` to `String` just to pass to an error message or return value.

**Recommendation:**
- Use `PyUnicode` creation from `OsStr` where possible to avoid UTF-8 validation overhead if not strictly needed, though PyO3 handles this well.

## Action Plan
1. **Benchmark**: Measure the cost of `parse_segments` with the current implementation.
2. **Standardize Errors**: Replace string matching with Enum matching (Phase 2).
3. **Optimize Strings**: Rewrite `classic-scanlog-py` iterators to use `PyString::new` (Phase 3).
