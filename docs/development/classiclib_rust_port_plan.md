# ClassicLib Full Rust Port - Implementation Plan

## Executive Summary

This document outlines a phased approach to port the remaining Python components of ClassicLib to Rust, creating a complete Rust foundation that:

1. **Enables pure Rust applications** (CLI, TUI, GUI) without Python dependencies
2. **Accelerates Python applications** through transparent Rust integration
3. **Maintains full backward compatibility** via Python bindings (PyO3)
4. **Reduces technical debt** by consolidating dual implementations

**Scope**: Port ~100 Python files (~167 total, ~67 already have Rust counterparts) across 8 major component groups.

**Timeline**: 6-9 months for full implementation, with incremental value delivery starting in Phase 1.

**Performance Target**: 10-150x speedups for critical paths (consistent with existing Rust acceleration results).

---

## Goals and Objectives

### Primary Goals

1. **Complete Rust Foundation**: Enable pure Rust applications without Python runtime
2. **Performance**: Achieve 10-150x performance improvements across all components
3. **Maintainability**: Single source of truth - Rust code with Python bindings
4. **Compatibility**: Zero breaking changes to existing Python API surface

### Secondary Goals

1. **Developer Experience**: Improved tooling, type safety, and error messages
2. **Distribution**: Smaller binary sizes, faster startup times
3. **Cross-platform**: Better portability across Windows, Linux, macOS
4. **Safety**: Memory safety guarantees from Rust ownership system

---

## Current State Analysis

### Already Ported (Estimated 40% of functionality)

| Component | Rust Crates | Status | Notes |
|-----------|-------------|--------|-------|
| YAML Operations | `classic-yaml-core` + `classic-yaml-py` | ✅ Complete | 15-30x faster |
| File I/O | `classic-file-io-core` + `classic-file-io-py` | ✅ Complete | 10x faster |
| Database | `classic-database-core` + `classic-database-py` | ✅ Complete | - |
| ScanLog | `classic-scanlog-core` + `classic-scanlog-py` | ✅ Complete | - |
| Config | `classic-config-core` + `classic-config-py` | ✅ Complete | - |
| Shared Runtime | `classic-shared-core` + `classic-shared-py` | ✅ Complete | Foundation |
| TUI | `classic-tui` | ✅ Complete | Pure Rust app |
| Slint GUI | `classic-gui-slint` | ✅ Complete | Pure Rust app |

### Components to Port (Estimated 60% remaining)

**Priority Breakdown** (167 total Python files - 67 already ported ≈ **100 files to port**):

#### **Tier 1 - Core Infrastructure** (Critical Path - ~15 files)
- `AsyncBridge.py` (28KB) - Async/sync coordination
- `GlobalRegistry.py` (8KB) - Singleton management
- `YamlSettingsCache.py` (21KB) - Settings caching layer
- `MessageHandler/` (7 files) - Central messaging system
- `PerformanceMonitor.py` (12KB) - Performance tracking

#### **Tier 2 - Game Path Management** (~10 files)
- `GamePath.py` (19KB) - Game installation detection
- `DocsPath.py` (21KB) - Documents folder management
- `PathValidator.py` (15KB) - Path validation logic
- `DocumentsChecker.py` (3KB) - Documents verification
- `BackupManager.py` (8KB) - Backup operations

#### **Tier 3 - Game Scanning** (ScanGame/ - ~20 files)
- `GameIntegrityOrchestrator.py` - Orchestration layer
- `ScanGameCore.py` - Core scanning logic
- `CheckCrashgen.py` - Crash Gen detection
- `CheckXsePlugins.py` - XSE plugin validation
- `GameFilesManager.py` - File management
- `ScanModInis.py` - INI file scanning
- `WryeCheck.py` - Wrye Bash integration
- `core/` subdirectory (8 files) - BA2, DDS, unpacked scanning

#### **Tier 4 - XSE & Extended Utilities** (~15 files)
- `XseCheck.py` (17KB) - XSE script extender checks
- `ResourceLoader.py` (32KB) - Resource management
- `Utils/` (7 files) - General utilities
- `Constants.py` (3KB) - Application constants

#### **Tier 5 - Application Coordination** (~10 files)
- `SetupCoordinator.py` (13KB) - Setup orchestration
- `Update.py` (32KB) - Auto-update functionality
- `FileGeneration.py` (8KB) - File generation
- `GameIntegrity.py` (6KB) - Integrity checks
- `PapyrusLog.py` (3KB) - Papyrus log handling
- `Logger.py` - Logging utilities

#### **Tier 6 - GUI Components** (~28 files - **Optional**)
Interface/ directory - PySide6-specific GUI code
- **Decision**: Keep in Python or port to Slint incrementally
- Not required for pure Rust apps (Slint GUI already exists)

#### **Remaining** (~2 files)
- Deprecated async utilities (AsyncUtil.py, AsyncUtilities.py)
- Legacy backup code

---

## Architecture Patterns and Constraints

### Mandatory Architectural Rules

1. **ONE RUNTIME RULE**: All crates share `classic_shared::get_runtime()` - no local Tokio runtimes
2. **SEPARATION OF CONCERNS**: Business logic in `-core` crates, Python bindings in `-py` crates
3. **NO MIXED CRATES**: Never combine business logic with PyO3 in the same crate
4. **ASYNC-FIRST**: All new Rust code uses async/await with Tokio runtime

### Naming Convention

```
Component: MessageHandler

Rust Crates:
├── classic-message-core/       # Business logic (pure Rust)
│   ├── Cargo.toml             # crate-type = ["rlib"]
│   └── src/
│       ├── lib.rs
│       ├── handler.rs
│       ├── models.rs
│       └── ...
│
└── classic-message-py/         # Python bindings (PyO3)
    ├── Cargo.toml             # crate-type = ["cdylib", "rlib"]
    └── src/
        ├── lib.rs             # #[pymodule]
        └── py_*.rs            # PyO3 wrappers

Python Import:
    from classic_core import message
    handler = message.MessageHandler()
```

### PyO3 Integration Pattern

```rust
// classic-message-core/src/lib.rs (Pure Rust)
pub struct MessageHandler {
    // Implementation
}

impl MessageHandler {
    pub async fn send_message(&self, msg: &str) -> Result<()> {
        // Async business logic
    }
}

// classic-message-py/src/lib.rs (PyO3 Bindings)
use pyo3::prelude::*;
use classic_message_core::MessageHandler as CoreHandler;

#[pyclass]
struct MessageHandler {
    inner: Arc<CoreHandler>,
}

#[pymethods]
impl MessageHandler {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(Self {
            inner: Arc::new(CoreHandler::new()),
        })
    }

    fn send_message(&self, py: Python, msg: String) -> PyResult<()> {
        let inner = self.inner.clone();
        py.allow_threads(|| {
            classic_shared::AsyncBridge::run_async(async move {
                inner.send_message(&msg).await
            })
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }
}

#[pymodule]
fn message(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MessageHandler>()?;
    Ok(())
}
```

### Async Bridge Pattern (Critical)

For **all async operations** in Slint/GUI contexts:

```rust
use classic_shared::AsyncBridge;

// In Slint callback
main_window.on_button_click({
    let window_weak = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            async_operation(),
            move |result| {
                if let Some(w) = window_weak.upgrade() {
                    w.set_result(result);
                }
            }
        );
    }
});
```

---

## Phased Implementation Plan

### Phase 1: Core Infrastructure (Months 1-2)

**Goal**: Establish foundation for all other components

**Components**:
1. **AsyncBridge (Python)** → `classic-pybridge-core` + `classic-pybridge-py`
   - Priority: CRITICAL
   - Python async/sync coordination (distinct from Slint's `AsyncBridge` in `classic-shared-core`)
   - Bridge Python asyncio with Qt/PySide6 event loop
   - Replace manual `asyncio.run()` patterns in Python code
   - Essential for PySide6 GUI and async CLI operations
   - Estimate: 1 week

2. **GlobalRegistry** → `classic-registry-core` + `classic-registry-py`
   - Priority: HIGH
   - Singleton management with DashMap
   - Thread-safe instance tracking
   - Estimate: 3 days

3. **YamlSettingsCache** → `classic-settings-core` + `classic-settings-py`
   - Priority: HIGH
   - Layer on top of existing `classic-yaml-core`
   - Caching with `quick_cache`
   - Batch loading support
   - Estimate: 1 week

4. **MessageHandler** → `classic-message-core` + `classic-message-py`
   - Priority: HIGH
   - Central messaging system
   - Multiple output modes (CLI, GUI, TUI)
   - Progress tracking
   - Estimate: 1.5 weeks

5. **PerformanceMonitor** → `classic-perf-core` + `classic-perf-py`
   - Priority: MEDIUM
   - Rationale: While `performance_core.rs` exists in `classic-shared-core`, creating dedicated crates provides:
     - **Python acceleration**: 10x memory efficiency (O(1) vs O(n)) + thread safety
     - **Rust applications**: Proper logging integration, formatted reports, JSON/CSV export
     - **Cross-language metrics**: Unified performance tracking across Python and Rust
     - **Better architecture**: Dedicated crate is more discoverable than embedded module
   - Features to add:
     - MessageHandler integration for logging
     - Formatted summary reports matching Python API
     - JSON/CSV export for analysis
     - Performance threshold warnings
     - Python decorator API (`@timed_operation`, `@async_timed_operation`)
   - Estimate: 1-1.5 weeks

**Deliverables**:
- ✅ Core infrastructure crates
- ✅ Python bindings with full API compatibility
- ✅ Integration tests for each component
- ✅ Documentation and migration guide

**Success Criteria**:
- All existing Python tests pass with Rust backend
- Performance: 5-10x improvement in registry/cache operations
- Zero breaking changes to Python API

---

### Phase 2: Path Management (Months 2-3)

**Goal**: Consolidate all path-related operations into a unified crate

**Components**: Single crate group `classic-path-core` + `classic-path-py`

**Modules within `classic-path-core`**:
1. **GamePath module** (`game_path.rs`)
   - Game installation detection
   - Registry queries (Windows)
   - Steam/GOG path resolution
   - Estimate: 1.5 weeks

2. **DocsPath module** (`docs_path.rs`)
   - Documents folder detection
   - Per-game document paths
   - Documents verification logic (DocumentsChecker)
   - Estimate: 1 week

3. **PathValidator module** (`validator.rs`)
   - Path validation and normalization
   - Safe path operations
   - Cross-platform path handling
   - Estimate: 1 week

4. **BackupManager module** (`backup.rs`)
   - Backup creation/restoration
   - Compression support
   - Estimate: 1 week

**Python Bindings** (`classic-path-py`):
- Unified Python module exposing all path operations
- Single import: `from classic_core import path`
- Classes: `GamePath`, `DocsPath`, `PathValidator`, `BackupManager`

**Deliverables**:
- ✅ Unified path management crate with modular structure
- ✅ Cross-platform path handling
- ✅ Windows registry integration (for game detection)
- ✅ Integration tests with real game paths
- ✅ Documentation

**Success Criteria**:
- Reliable game detection across all supported platforms
- 10-20x faster path validation
- Comprehensive error messages for invalid paths
- Single cohesive API for all path operations

---

### Phase 3: Game Scanning (Months 3-5)

**Goal**: Port ScanGame/ module for game integrity checking

**Components**:
1. **ScanGameCore** → `classic-scangame-core` + `classic-scangame-py`
   - Core scanning orchestration
   - Parallel file scanning
   - Estimate: 2 weeks

2. **GameIntegrityOrchestrator** → merge into `classic-scangame-core`
   - High-level orchestration
   - Report generation
   - Estimate: 1 week

3. **BA2Scanner** → `classic-ba2-core` + `classic-ba2-py`
   - BA2 archive parsing
   - Asset validation
   - Estimate: 2 weeks

4. **DDSAnalyzer** → Basic implementation already in `classic-file-io-core` + `classic-file-io-py`, expand here
   - DDS texture analysis
   - Format validation
   - Estimate: 1 week

5. **CheckCrashgen** → `classic-crashgen-core` + `classic-crashgen-py`
   - Crash Gen detection
   - Estimate: 3 days

6. **CheckXsePlugins** → merge into `classic-xse-core` (Phase 4)
   - XSE plugin validation
   - Estimate: 1 week

7. **GameFilesManager** → `classic-gamefiles-core` + `classic-gamefiles-py`
   - File management operations
   - Estimate: 1 week

8. **ScanModInis** → `classic-modini-core` + `classic-modini-py`
   - INI file scanning
   - Configuration validation
   - Estimate: 1 week

9. **WryeCheck** → `classic-wrye-core` + `classic-wrye-py`
   - Wrye Bash integration
   - Estimate: 1 week

**Deliverables**:
- ✅ Complete game scanning suite in Rust
- ✅ BA2 and DDS file format support
- ✅ Python bindings for all components
- ✅ Integration with existing ScanLog module
- ✅ Performance benchmarks

**Success Criteria**:
- 20-50x faster game integrity scans
- Support for all asset types (BA2, DDS, loose files)
- Accurate detection of all configuration issues
- FCX mode fully functional in Rust

---

### Phase 4: XSE & Extended Utilities (Months 5-6)

**Goal**: Port XSE checking and utility functions

**Components**:
1. **XseCheck** → `classic-xse-core` + `classic-xse-py`
   - Script extender detection
   - Version checking
   - Plugin validation
   - Estimate: 2 weeks

2. **ResourceLoader** → `classic-resource-core` + `classic-resource-py`
   - Resource management
   - Asset loading
   - Estimate: 1.5 weeks

3. **Utils/** → `classic-utils-core` + `classic-utils-py`
   - File utilities
   - String utilities
   - Path utilities
   - Version utilities
   - Web utilities
   - Logging utilities
   - Estimate: 2 weeks (parallelizable)

4. **Constants** → merge into `classic-shared-core`
   - Application constants
   - Estimate: 2 days

**Deliverables**:
- ✅ XSE checking infrastructure
- ✅ Consolidated utility library
- ✅ Python bindings
- ✅ Migration guide for utility functions

**Success Criteria**:
- Accurate XSE detection across F4SE/SKSE
- 5-15x faster utility operations
- Unified utility API across Python and Rust

---

### Phase 5: Application Coordination (Months 6-7)

**Goal**: Port high-level coordination and update logic

**Components**:
1. **SetupCoordinator** → `classic-setup-core` + `classic-setup-py`
   - Application setup orchestration
   - First-run initialization
   - Estimate: 1.5 weeks

2. **Update** → `classic-update-core` + `classic-update-py`
   - Auto-update functionality
   - Version checking
   - Update download and installation
   - Estimate: 2 weeks

3. **FileGeneration** → `classic-filegen-core` + `classic-filegen-py`
   - File generation utilities
   - Template processing
   - Estimate: 1 week

4. **GameIntegrity** → merge into `classic-scangame-core`
   - Integrity verification
   - Estimate: 3 days

5. **PapyrusLog** → `classic-papyrus-core` + `classic-papyrus-py`
   - Papyrus log parsing
   - Error extraction
   - Estimate: 1 week

6. **Logger** → merge into `classic-message-core`
   - Logging infrastructure
   - Estimate: 2 days

**Deliverables**:
- ✅ Complete application coordination in Rust
- ✅ Auto-update infrastructure
- ✅ Python bindings
- ✅ End-to-end integration tests

**Success Criteria**:
- Reliable auto-update functionality
- 10-30x faster file generation
- Seamless coordination between components

---

### Phase 6: GUI Integration & Polish (Months 7-9) (Deferred, Slint GUI is already mostly implemented)

**Goal**: Integrate Rust components with GUI, optimize, and finalize

#### Option A: Keep PySide6 GUI (Recommended for MVP)

**Components**:
- Update `Interface/` Python code to use Rust backends
- Optimize GUI responsiveness with async operations
- Comprehensive integration testing

**Estimate**: 1.5 months

**Pros**:
- Minimal disruption to existing GUI
- Faster delivery
- Proven UI/UX

**Cons**:
- Still requires Python runtime for GUI app
- Larger distribution size

#### Option B: Port to Slint (Long-term goal)

**Components**:
1. Port each `Interface/` module to Slint incrementally
2. Maintain feature parity with PySide6 GUI
3. Create unified Rust GUI application

**Estimate**: 3-4 months (beyond initial scope)

**Pros**:
- Pure Rust GUI application
- Smaller binary, faster startup
- Better cross-platform support
- Single codebase for all UIs

**Cons**:
- Significant development effort
- UI/UX redesign required
- Learning curve for Slint

#### Recommended Approach

**Phase 6A (Months 7-8)**: PySide6 Integration
1. Update all Python GUI code to use Rust backends
2. Add AsyncBridge integration for GUI operations
3. Optimize threading and async coordination
4. Comprehensive testing

**Phase 6B (Month 9)**: Polish & Documentation
1. Performance optimization
2. Error handling improvements
3. Comprehensive documentation
4. Migration guides
5. Release preparation

**Phase 6C (Future)**: Slint Migration (Optional)
- Incremental port to Slint UI
- Run in parallel with PySide6 GUI
- User feedback and iteration

**Deliverables**:
- ✅ PySide6 GUI fully integrated with Rust backends
- ✅ All tests passing
- ✅ Performance benchmarks
- ✅ Complete documentation
- ✅ Migration guides
- ✅ Release-ready pure Rust CLI/TUI apps

**Success Criteria**:
- GUI remains fully functional with Rust acceleration
- All 167 Python files have Rust implementations
- Performance improvements across all operations
- Zero regression in functionality
- Clear migration path documented

---

## Technical Approach

### Porting Methodology

For each component:

1. **Analysis**
   - Map Python dependencies
   - Identify async operations
   - Document API surface
   - List integration points

2. **Design**
   - Design Rust API (pure business logic)
   - Plan PyO3 wrapper strategy
   - Define error types
   - Document async patterns

3. **Implementation - Core (-core crate)**
   - Implement business logic in pure Rust
   - No PyO3 dependencies
   - Async-first design
   - Comprehensive doc comments
   - Unit tests

4. **Implementation - Bindings (-py crate)**
   - Create PyO3 wrappers
   - Implement `#[pyclass]` types
   - Handle GIL and async coordination
   - Integration tests with Python

5. **Integration**
   - Add to workspace
   - Update Python `__init__.py` for backward compatibility
   - End-to-end testing

6. **Documentation**
   - Rust API docs
   - Python API docs
   - Migration guide
   - Performance benchmarks

7. **Validation**
   - All existing Python tests pass
   - Performance benchmarks meet targets
   - No breaking changes

### Dependency Resolution

**Dependency Graph** (Port in this order):

```
Layer 1: Foundation
├── classic-shared (✅ exists)
├── PyAsyncBridge (Phase 1)
├── GlobalRegistry (Phase 1)
└── MessageHandler (Phase 1)

Layer 2: Configuration & Caching
├── YamlSettingsCache (Phase 1)
├── PerformanceMonitor (Phase 1)
└── Constants → classic-shared (Phase 4)

Layer 3: Path Management
└── classic-path (unified crate - Phase 2)
    ├── GamePath module
    ├── DocsPath module
    ├── PathValidator module
    └── BackupManager module

Layer 4: Utilities
├── Utils/* (Phase 4)
├── ResourceLoader (Phase 4)
└── Logger → MessageHandler (Phase 5)

Layer 5: Scanning & Analysis
├── XseCheck (Phase 4)
├── ScanGameCore (Phase 3)
├── GameIntegrityOrchestrator (Phase 3)
├── BA2Scanner (Phase 3)
├── DDSAnalyzer (Phase 3)
├── CheckCrashgen (Phase 3)
├── CheckXsePlugins (Phase 3)
├── GameFilesManager (Phase 3)
├── ScanModInis (Phase 3)
└── WryeCheck (Phase 3)

Layer 6: Application Coordination
├── SetupCoordinator (Phase 5)
├── Update (Phase 5)
├── FileGeneration (Phase 5)
├── PapyrusLog (Phase 5)
└── GameIntegrity → ScanGameCore (Phase 5)

Layer 7: UI Integration
└── Interface/* (Phase 6)
```

### Testing Strategy

**Test Pyramid**:

1. **Unit Tests** (Rust)
   - Test each Rust module in isolation
   - Mock dependencies
   - Property-based testing where applicable

2. **Integration Tests** (Rust ↔ Rust)
   - Test interactions between Rust crates
   - Async operation coordination
   - Error propagation

3. **FFI Tests** (Rust ↔ Python via PyO3)
   - Test Python bindings
   - GIL handling
   - Async bridge functionality
   - Type conversions

4. **End-to-End Tests** (Python)
   - Existing pytest suite
   - All tests must pass with Rust backend
   - Performance regression tests

5. **Performance Benchmarks**
   - Criterion.rs benchmarks (Rust)
   - Python benchmarks for comparison
   - Track regressions

### Migration Strategy (Backward Compatibility)

**Python API Compatibility Layer**:

```python
# ClassicLib/__init__.py
try:
    # Try Rust implementation first
    from classic_core import message
    MessageHandler = message.MessageHandler
    _USING_RUST = True
except ImportError:
    # Fallback to Python implementation
    from ClassicLib.MessageHandler import MessageHandler
    _USING_RUST = False

# Re-export with original path
from ClassicLib.MessageHandler import MessageHandler

__all__ = ["MessageHandler"]
```

**Deprecation Process**:
1. Rust implementation added (new import path available)
2. Python implementation marked deprecated (warnings)
3. Auto-fallback if Rust unavailable
4. After 2 releases: remove Python implementation

---

## Risk Mitigation

### Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking API changes | Medium | High | Comprehensive test suite; backward compatibility layer |
| Performance regression | Low | High | Continuous benchmarking; performance tests in CI |
| PyO3 async complexity | Medium | Medium | Thorough testing of AsyncBridge; existing patterns work |
| Platform-specific issues | Medium | Medium | CI testing on Windows/Linux/macOS |
| Extended timeline | High | Low | Phased delivery; incremental value |
| Resource constraints | Medium | Medium | Parallelizable work; clear priorities |

### Mitigation Strategies

1. **Incremental Delivery**: Each phase delivers standalone value
2. **Parallel Development**: Multiple components can be ported simultaneously
3. **Comprehensive Testing**: No component merged without full test coverage
4. **Documentation**: Clear migration guides at each phase
5. **Fallback Mechanism**: Python implementations remain until Rust proven stable
6. **Performance Monitoring**: Continuous tracking prevents regressions
7. **Code Reviews**: Rust expert review for each component

---

## Success Metrics

### Quantitative Metrics

1. **Performance**:
   - 10-150x speedup for accelerated operations
   - Sub-second application startup (Rust apps)
   - <100ms latency for common operations

2. **Code Quality**:
   - 100% test coverage for new Rust code
   - All existing Python tests pass
   - Zero Clippy warnings
   - Zero deprecated API usage

3. **Distribution**:
   - 50% reduction in binary size (Rust apps vs PyInstaller)
   - 80% reduction in startup time (Rust apps)

4. **Compatibility**:
   - 100% backward compatibility with Python API
   - Zero breaking changes

### Qualitative Metrics

1. **Developer Experience**:
   - Improved error messages
   - Better type safety
   - Clearer architecture

2. **Maintainability**:
   - Single source of truth (Rust)
   - Less code duplication
   - Clearer separation of concerns

3. **User Experience**:
   - Faster application responsiveness
   - Smaller download sizes
   - Faster installation

---

## Timeline Estimates

### Optimistic (6 months, 2 full-time developers)

| Phase | Duration | Completion |
|-------|----------|------------|
| Phase 1: Core Infrastructure | 1.5 months | Month 1.5 |
| Phase 2: Path Management | 1 month | Month 2.5 |
| Phase 3: Game Scanning | 1.5 months | Month 4 |
| Phase 4: XSE & Utilities | 1 month | Month 5 |
| Phase 5: App Coordination | 1 month | Month 6 |
| Phase 6: GUI Integration | 0.5 months | Month 6.5 |

### Realistic (9 months, 1 full-time + 1 part-time developer)

| Phase | Duration | Completion |
|-------|----------|------------|
| Phase 1: Core Infrastructure | 2 months | Month 2 |
| Phase 2: Path Management | 1.5 months | Month 3.5 |
| Phase 3: Game Scanning | 2.5 months | Month 6 |
| Phase 4: XSE & Utilities | 1.5 months | Month 7.5 |
| Phase 5: App Coordination | 1 month | Month 8.5 |
| Phase 6: GUI Integration | 1 month | Month 9.5 |

### Conservative (12 months, part-time development)

| Phase | Duration | Completion |
|-------|----------|------------|
| Phase 1: Core Infrastructure | 3 months | Month 3 |
| Phase 2: Path Management | 2 months | Month 5 |
| Phase 3: Game Scanning | 3 months | Month 8 |
| Phase 4: XSE & Utilities | 2 months | Month 10 |
| Phase 5: App Coordination | 1.5 months | Month 11.5 |
| Phase 6: GUI Integration | 1.5 months | Month 13 |

**Recommended Approach**: Start with realistic timeline, adjust based on velocity after Phase 1.

---

## Next Steps

### Immediate Actions (Week 1)

1. **Review and approval** of this implementation plan
2. **Set up project tracking** (GitHub Project board)
3. **Phase 1 kickoff meeting** - scope and assign tasks
4. **Create workspace structure** for new crates

### Phase 1 Preparation (Week 1-2)

1. **PyAsyncBridge design review**
   - Review Python `AsyncBridge.py` implementation
   - Design Rust API for Python async/sync coordination
   - Plan PyO3 integration with Python asyncio and Qt event loop
   - Set up `classic-pybridge-core` and `classic-pybridge-py` crates

2. **Testing infrastructure**
   - Set up Criterion.rs for benchmarks
   - Configure CI for new crates
   - Create test data fixtures

3. **Documentation templates**
   - Rust API doc templates
   - Migration guide templates
   - Performance benchmark report templates

### Phase 1 Kickoff (Week 2)

- Begin implementation of PyAsyncBridge (highest priority)
- Parallel work on GlobalRegistry and YamlSettingsCache
- Daily standups to track progress
- Weekly demos of completed components

---

## Appendix A: Workspace Structure

### Proposed New Crates

```
Workspace Root
├── classic-pybridge-core/         # Python AsyncBridge business logic (async/sync coordination)
├── classic-pybridge-py/           # Python AsyncBridge Python bindings
├── classic-registry-core/         # GlobalRegistry business logic
├── classic-registry-py/           # GlobalRegistry Python bindings
├── classic-settings-core/         # YamlSettingsCache business logic
├── classic-settings-py/           # YamlSettingsCache Python bindings
├── classic-message-core/          # MessageHandler business logic
├── classic-message-py/            # MessageHandler Python bindings
├── classic-perf-core/             # PerformanceMonitor business logic
├── classic-perf-py/               # PerformanceMonitor Python bindings
├── classic-path-core/             # Unified path management (GamePath, DocsPath, PathValidator, BackupManager)
├── classic-path-py/               # Path management Python bindings
├── classic-scangame-core/         # ScanGame business logic
├── classic-scangame-py/           # ScanGame Python bindings
├── classic-ba2-core/              # BA2 format support
├── classic-ba2-py/                # BA2 Python bindings
├── classic-dds-core/              # DDS format support
├── classic-dds-py/                # DDS Python bindings
├── classic-crashgen-core/         # CrashGen detection
├── classic-crashgen-py/           # CrashGen Python bindings
├── classic-gamefiles-core/        # GameFiles management
├── classic-gamefiles-py/          # GameFiles Python bindings
├── classic-modini-core/           # Mod INI scanning
├── classic-modini-py/             # Mod INI Python bindings
├── classic-wrye-core/             # Wrye Bash integration
├── classic-wrye-py/               # Wrye Bash Python bindings
├── classic-xse-core/              # XSE checking
├── classic-xse-py/                # XSE Python bindings
├── classic-resource-core/         # ResourceLoader business logic
├── classic-resource-py/           # ResourceLoader Python bindings
├── classic-utils-core/            # Utilities business logic
├── classic-utils-py/              # Utilities Python bindings
├── classic-setup-core/            # SetupCoordinator business logic
├── classic-setup-py/              # SetupCoordinator Python bindings
├── classic-update-core/           # Update business logic
├── classic-update-py/             # Update Python bindings
├── classic-filegen-core/          # FileGeneration business logic
├── classic-filegen-py/            # FileGeneration Python bindings
├── classic-papyrus-core/          # PapyrusLog business logic
└── classic-papyrus-py/            # PapyrusLog Python bindings


Existing Crates (unchanged):
├── classic-shared-core/           # Foundation
├── classic-shared-py/             # Foundation Python bindings
├── classic-yaml-core/             # YAML operations
├── classic-yaml-py/               # YAML Python bindings
├── classic-database-core/         # Database operations
├── classic-database-py/           # Database Python bindings
├── classic-file-io-core/          # File I/O
├── classic-file-io-py/            # File I/O Python bindings
├── classic-scanlog-core/          # ScanLog business logic
├── classic-scanlog-py/            # ScanLog Python bindings
├── classic-config-core/           # Config management
├── classic-config-py/             # Config Python bindings
├── classic-ui-shared/             # UI coordination
├── classic-cli/                   # CLI app (pure Rust)
├── classic-tui/                   # TUI app (pure Rust)
└── classic-gui-slint/             # Slint GUI (pure Rust)
```

**Total New Crates**: ~44 (22 -core + 22 -py)

**Note**: Path management consolidated into single `classic-path` crate group (reduces by 6 crates). PerformanceMonitor gets dedicated crates despite existing in `classic-shared-core` to provide Python acceleration (10x memory efficiency), unified cross-language metrics, and proper logging integration. Python AsyncBridge (`classic-pybridge`) is distinct from Slint's AsyncBridge in `classic-shared-core` - the former bridges Python asyncio with Qt, while the latter bridges Rust async with Slint's UI thread.

---

## Appendix B: Performance Targets

### Component-Specific Targets

| Component | Python Baseline | Rust Target | Expected Speedup |
|-----------|----------------|-------------|------------------|
| PyAsyncBridge | - | - | N/A (new pattern) |
| GlobalRegistry | ~1ms | <100μs | 10x |
| YamlSettingsCache | ~10ms | <1ms | 10x |
| MessageHandler | ~500μs | <50μs | 10x |
| PerformanceMonitor | ~100μs | <10μs | 10x |
| GamePath | ~50ms | <5ms | 10x |
| DocsPath | ~20ms | <2ms | 10x |
| PathValidator | ~1ms | <100μs | 10x |
| BackupManager | ~1s | <100ms | 10x |
| ScanGameCore | ~10s | <1s | 10x |
| BA2Scanner | ~5s | <500ms | 10x |
| DDSAnalyzer | ~2s | <200ms | 10x |
| XseCheck | ~100ms | <10ms | 10x |
| ResourceLoader | ~50ms | <5ms | 10x |
| Utils (aggregate) | ~1ms | <100μs | 10x |
| SetupCoordinator | ~500ms | <50ms | 10x |
| Update | ~2s | <200ms | 10x |
| FileGeneration | ~100ms | <10ms | 10x |
| PapyrusLog | ~50ms | <5ms | 10x |

**Aggregate Expected Performance**:
- Overall application startup: **5-10x faster** (Rust apps)
- Common operations: **10-30x faster**
- Scanning operations: **10-50x faster**
- I/O operations: **10-100x faster** (already achieved with file-io)

---

## Appendix C: Resource Requirements

### Development Resources

**Primary Developer** (full-time):
- Rust expert
- PyO3 experience
- Async/await proficiency
- 6-9 months commitment

**Secondary Developer** (part-time):
- Python expertise
- Testing focus
- Documentation
- 3-6 months commitment (20 hours/week)

### Infrastructure

- **CI/CD**: GitHub Actions (already configured)
- **Testing**: Windows/Linux/macOS runners
- **Benchmarking**: Dedicated benchmark runner
- **Documentation**: Rust docs, MkDocs for guides

### Optional

- **Code Review**: External Rust expert (consultant)
- **Performance Analysis**: Profiling tools (cargo-flamegraph, etc.)

---

## Appendix D: Open Questions

1. **GUI Strategy**: PySide6 vs. Slint for final GUI?
   - **Recommendation**: Keep PySide6 for Phase 6A, evaluate Slint in Phase 6C

2. **Distribution Strategy**: How to distribute Rust-accelerated Python packages?
   - Option A: PyInstaller with compiled Rust extensions (current approach)
   - Option B: Separate pure Rust binaries + Python package
   - Option C: Hybrid - Rust CLI/TUI/GUI + Python package for scripting
   - **Recommendation**: Option C - maximize flexibility

3. **Python Version Support**: Continue supporting Python 3.12+?
   - **Recommendation**: Yes - PyO3 `abi3-py312` already configured

4. **Async Runtime**: Continue with Tokio as global runtime?
   - **Recommendation**: Yes - proven approach, ONE RUNTIME RULE

5. **Error Handling**: Standardize error types across all crates?
   - **Recommendation**: Yes - define common error types in `classic-shared-core`

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-31 | Claude | Initial comprehensive plan |

---

**Document Status**: DRAFT - Awaiting Review and Approval

**Next Review Date**: TBD

**Owner**: TBD

**Approvers**: TBD
