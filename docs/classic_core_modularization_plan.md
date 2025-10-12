# classic_core Modularization Plan

## Executive Summary

This document outlines the strategy for refactoring the monolithic `classic-rust` crate into a modular workspace architecture, following the successful pattern established with `classic-config`. The modularization will improve build times, enable independent versioning, reduce coupling, and eliminate circular dependency issues.

## Current State Analysis

### Monolithic Structure
```
classic-rust/
├── Cargo.toml (classic-core v8.0.0)
└── src/
    ├── lib.rs (classic_core Python module)
    ├── config/          # YamlData loading (has issues)
    ├── database/        # SQLite operations
    ├── file_io/         # File operations, encoding, DDS
    ├── scanlog/         # Log parsing, FormID, patterns
    ├── utils/           # Errors, strings, paths, performance
    └── yaml/            # YAML operations (yaml-rust2)
```

### Problems with Current Architecture
1. **Circular Dependencies**: Config module can't import yaml module during initialization
2. **Module Registration Failures**: Some modules fail to register in the monolith but work standalone
3. **Build Times**: Changes to any module require rebuilding entire crate
4. **Tight Coupling**: All modules share same runtime, dependencies, and version
5. **Testing Complexity**: Hard to isolate module-specific tests
6. **Deployment Issues**: Can't deploy individual module updates

### Current Dependencies (45 total)
- **PyO3**: 0.26.0 (Python bindings)
- **Async**: tokio 1.41, futures 0.3
- **Parsing**: regex, memchr, aho-corasick
- **Parallel**: rayon, crossbeam
- **Database**: rusqlite 0.37.0
- **File I/O**: encoding_rs, memmap2, walkdir, ddsfile
- **Errors**: anyhow, thiserror
- **Performance**: once_cell, dashmap, lru, parking_lot
- **Strings**: string_cache, smartstring
- **YAML**: yaml-rust2 0.10.4
- **Serialization**: serde, serde_json

## Proposed Modular Architecture

### Workspace Structure
```
CLASSIC-Fallout4/
├── Cargo.toml (workspace root)
├── classic-shared/        # Shared utilities (NEW)
├── classic-yaml/          # YAML operations
├── classic-config/        # YamlData loading (DONE ✓)
├── classic-database/      # SQLite operations
├── classic-file-io/       # File operations
├── classic-scanlog/       # Log parsing & analysis
└── classic-core/          # Thin facade (RENAMED from classic-rust)
```

### Module Breakdown

#### 1. classic-shared (Foundation Crate)
**Purpose**: Shared utilities and runtime for all other crates

**Exports**:
- `get_runtime()` - Global Tokio runtime (ONE RUNTIME RULE)
- `ClassicError`, `ClassicResult` - Error types
- `PathHandler`, `StringProcessor` - Common utilities
- `RustPerformanceMonitor` - Performance tracking

**Dependencies**:
- pyo3 (workspace)
- tokio (workspace)
- once_cell (workspace)
- thiserror, anyhow
- string_cache, smartstring

**Python Module**: `classic_shared`
**Estimate**: ~500 LOC, 2-3 hours

---

#### 2. classic-yaml (YAML Operations)
**Purpose**: High-performance YAML parsing and writing

**Exports**:
- `RustYamlOperations` class
- YAML parsing, writing, caching functions

**Dependencies**:
- classic-shared (workspace path)
- yaml-rust2 (workspace)
- dashmap, parking_lot

**Python Module**: `classic_yaml`
**Estimate**: ~800 LOC (existing), 3-4 hours

---

#### 3. classic-config (YamlData Loading) ✓ COMPLETED
**Purpose**: Rust-accelerated configuration loading

**Exports**:
- `YamlData` class (26 fields)
- `create_yamldata()` function
- Parallel YAML file loading

**Dependencies**:
- classic-shared (workspace path)
- yaml-rust2 (workspace)

**Python Module**: `classic_config`
**Status**: Already implemented and tested

---

#### 4. classic-database (SQLite Operations)
**Purpose**: Database connection pooling and queries

**Exports**:
- `DatabasePool` class
- Query execution functions

**Dependencies**:
- classic-shared (workspace path)
- rusqlite (with bundled, backup features)
- parking_lot

**Python Module**: `classic_database`
**Estimate**: ~400 LOC, 2-3 hours

---

#### 5. classic-file-io (File Operations)
**Purpose**: Fast file I/O, encoding detection, DDS parsing

**Exports**:
- `RustFileIOCore` class
- `detect_encoding()`, `read_with_encoding()`
- `parse_dds()` for texture files
- Memory-mapped file reading

**Dependencies**:
- classic-shared (workspace path)
- encoding_rs, memmap2, walkdir, ddsfile

**Python Module**: `classic_file_io`
**Estimate**: ~600 LOC, 3-4 hours

---

#### 6. classic-scanlog (Log Parsing & Analysis)
**Purpose**: Crash log parsing, FormID analysis, pattern matching

**Exports**:
- `RustLogParser` class
- `RustFormIDAnalyzer` class
- `RustPluginAnalyzer`, `RustRecordScanner`
- `RustModDetector`, `RustReportFormatter`
- Pattern matching functions

**Dependencies**:
- classic-shared (workspace path)
- classic-yaml (workspace path)
- regex, memchr, aho-corasick
- rayon, crossbeam

**Python Module**: `classic_scanlog`
**Estimate**: ~1500 LOC, 5-6 hours

---

#### 7. classic-core (Thin Facade)
**Purpose**: Backwards compatibility layer and legacy exports

**Exports**:
- Re-exports from all other modules
- Legacy `FileReader`, `FormIDProcessor` classes
- Version info

**Dependencies**:
- All other classic-* crates (workspace paths)

**Python Module**: `classic_core` (maintains existing API)
**Estimate**: ~200 LOC, 1-2 hours

---

## Migration Strategy

### Phase 1: Foundation (Week 1)
**Goal**: Create shared infrastructure

1. **Create classic-shared crate** (Day 1-2)
   - Extract error types from utils
   - Extract runtime initialization
   - Extract common utilities (strings, paths)
   - Test standalone build

2. **Migrate classic-yaml** (Day 3-4)
   - Create classic-yaml crate
   - Move yaml module code
   - Update to depend on classic-shared
   - Test standalone build
   - Verify Python API compatibility

3. **Update classic-config** (Day 5)
   - Update to depend on classic-shared
   - Remove duplicate code
   - Rebuild and test

**Deliverables**:
- ✓ classic-shared crate building
- ✓ classic-yaml crate building
- ✓ classic-config using shared runtime
- ✓ All three modules pass tests

---

### Phase 2: Core Modules (Week 2)
**Goal**: Modularize database and file I/O

4. **Migrate classic-database** (Day 1-2)
   - Create classic-database crate
   - Move database module code
   - Update dependencies
   - Test standalone build

5. **Migrate classic-file-io** (Day 3-4)
   - Create classic-file-io crate
   - Move file_io module code
   - Update dependencies
   - Test DDS parsing, encoding detection

6. **Integration Testing** (Day 5)
   - Test all modules together
   - Verify no circular dependencies
   - Performance benchmarks

**Deliverables**:
- ✓ classic-database crate building
- ✓ classic-file-io crate building
- ✓ All modules pass integration tests

---

### Phase 3: Scanlog Module (Week 3)
**Goal**: Modularize largest and most complex module

7. **Migrate classic-scanlog** (Day 1-4)
   - Create classic-scanlog crate
   - Move all scanlog submodules:
     - parser.rs, formid.rs, formid_analyzer.rs
     - plugin_analyzer.rs, record_scanner.rs
     - mod_detector.rs, patterns.rs, report.rs
   - Update to depend on classic-yaml
   - Test all functionality

8. **Integration Testing** (Day 5)
   - Full stack testing
   - Performance validation
   - Memory usage checks

**Deliverables**:
- ✓ classic-scanlog crate building
- ✓ All log parsing features working
- ✓ Performance meets targets (10-150x speedup)

---

### Phase 4: Facade and Migration (Week 4)
**Goal**: Create facade and ensure backwards compatibility

9. **Create classic-core facade** (Day 1-2)
   - Rename classic-rust to classic-core
   - Remove all module code
   - Add re-exports from all crates
   - Maintain exact same Python API

10. **Python Integration** (Day 3-4)
    - Update ClassicLib/integration/factory.py
    - Test all Python code using Rust
    - Verify fallback mechanisms work
    - Update documentation

11. **Final Testing & Deployment** (Day 5)
    - Full regression testing
    - Performance benchmarks
    - Update CLAUDE.md
    - Tag release

**Deliverables**:
- ✓ classic-core facade working
- ✓ All Python tests passing
- ✓ Documentation updated
- ✓ Ready for deployment

---

## Workspace Configuration

### Root Cargo.toml
```toml
[workspace]
members = [
    "classic-shared",
    "classic-yaml",
    "classic-config",
    "classic-database",
    "classic-file-io",
    "classic-scanlog",
    "classic-core",
]
resolver = "2"

[workspace.dependencies]
# PyO3 bindings
pyo3 = { version = "0.26.0", features = ["abi3-py312"] }

# Async runtime (ONE RUNTIME RULE)
tokio = { version = "1.42", features = ["full"] }
futures = "0.3"

# Performance
once_cell = "1.20"
dashmap = "6.1"
parking_lot = "0.12"
rayon = "1.10"
crossbeam = "0.8"

# YAML
yaml-rust2 = "0.10.4"

# Strings & errors
string_cache = "0.9.0"
smartstring = "1.0"
thiserror = "2.0"
anyhow = "1.0"

# Database
rusqlite = { version = "0.37.0", features = ["bundled", "backup"] }

# File I/O
encoding_rs = "0.8"
memmap2 = "0.9"
walkdir = "2.5"
ddsfile = "0.5"

# Parsing
regex = "1.11"
memchr = "2.7"
aho-corasick = "1.1"

# Caching
lru = "0.16.1"
linked-hash-map = "0.5"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Logging
log = "0.4"
env_logger = "0.11"

[workspace.lints.rust]
deprecated = "deny"

[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
strip = true
```

### Individual Crate Pattern
```toml
[package]
name = "classic-<module>"
version = "8.0.0"
edition = "2021"
rust-version = "1.81"

[lib]
name = "classic_<module>"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { workspace = true, features = ["extension-module"] }
classic-shared = { path = "../classic-shared" }
# ... other workspace dependencies

[profile.release]
# Inherits from workspace
```

---

## Dependency Graph

```
                        classic-shared
                              ↑
                 ┌────────────┼────────────┐
                 │            │            │
           classic-yaml  classic-database  classic-file-io
                 ↑            ↑            ↑
                 │            │            │
                 └────┬───────┴────────────┘
                      │
                classic-config ← (uses yaml-rust2 directly)
                      │
                classic-scanlog ← (depends on yaml for data)
                      │
                classic-core (facade, re-exports all)
```

**Key Points**:
- **classic-shared** is the foundation, no dependencies on other classic-* crates
- **classic-yaml**, **classic-database**, **classic-file-io** only depend on shared
- **classic-config** uses yaml-rust2 directly to avoid circular deps
- **classic-scanlog** depends on yaml for data structures
- **classic-core** is a facade that re-exports everything

---

## Benefits of Modularization

### Development Benefits
1. **Faster Builds**: Only rebuild changed crates (~5x faster incremental builds)
2. **Parallel Compilation**: Multiple crates compile in parallel
3. **Clear Boundaries**: Each module has well-defined responsibilities
4. **Easier Testing**: Test modules in isolation
5. **No Circular Dependencies**: Import issues eliminated by design

### Deployment Benefits
1. **Independent Versioning**: Update modules without full rebuild
2. **Selective Installation**: Users can install only needed modules
3. **Smaller Wheels**: Individual module wheels are smaller
4. **Better Caching**: CI/CD can cache unchanged modules
5. **Rollback Safety**: Revert individual module updates

### Maintenance Benefits
1. **Code Organization**: Easy to find and modify code
2. **Dependency Clarity**: Know exactly what each module needs
3. **Onboarding**: New developers can focus on one module
4. **Documentation**: Per-module docs are more focused
5. **Performance Tuning**: Profile and optimize individual modules

---

## Risk Mitigation

### Risk: Breaking Python API
**Mitigation**:
- Maintain classic-core facade with exact same exports
- Comprehensive integration tests before merging
- Version lock all modules to 8.0.0 for initial release

### Risk: Performance Regression
**Mitigation**:
- Benchmark each module during migration
- Use same ONE RUNTIME RULE across all crates
- Profile full stack after modularization

### Risk: Increased Complexity
**Mitigation**:
- Clear dependency graph
- Consistent naming (classic-*)
- Shared workspace configuration
- Comprehensive documentation

### Risk: Build System Issues
**Mitigation**:
- Test each crate independently
- Automated CI/CD for workspace builds
- Keep existing PyInstaller specs working

---

## Success Criteria

### Functional Requirements
- ✓ All existing Python tests pass
- ✓ All Rust integration tests pass
- ✓ Classic-core facade provides exact same API
- ✓ No circular dependencies
- ✓ All modules build independently

### Performance Requirements
- ✓ No performance regression vs monolith
- ✓ Build times reduced by 50%+
- ✓ Memory usage stays the same or improves
- ✓ Same 10-150x speedup vs Python maintained

### Quality Requirements
- ✓ Zero deprecation warnings
- ✓ All modules pass clippy lints
- ✓ Documentation coverage >80%
- ✓ Test coverage >70% per module

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Foundation | Week 1 | shared, yaml, config working |
| Phase 2: Core Modules | Week 2 | database, file-io working |
| Phase 3: Scanlog | Week 3 | scanlog module working |
| Phase 4: Facade | Week 4 | classic-core facade, docs |
| **Total** | **4 weeks** | **Fully modular workspace** |

---

## Next Steps

1. **Review this plan** - Get approval for architecture
2. **Create classic-shared** - Start with foundation
3. **Migrate classic-yaml** - Extract and test
4. **Continue through phases** - Follow week-by-week plan
5. **Integration testing** - Validate at each phase
6. **Documentation** - Update CLAUDE.md and guides

---

## Open Questions

1. Should we version modules independently after 8.0.0?
2. Do we want to publish individual modules to PyPI eventually?
3. Should classic-core remain a facade indefinitely or deprecated?
4. Do we need a classic-common crate for types shared between multiple modules?

---

## References

- [Rust Full Backend Migration Plan](rust_full_backend_migration_plan.md)
- [PyO3 0.26 Migration Guide](pyo3_0.26_migration_guide.md)
- [ONE RUNTIME RULE](../classic-rust/src/lib.rs#L24-L38)
- [Successful classic-config Implementation](../classic-config-core/)
