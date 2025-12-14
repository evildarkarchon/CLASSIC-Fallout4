# Design: Refactor God Classes

## Context

The CLASSIC codebase has 7 files exceeding 750 lines that violate the "one class per file" convention and mix multiple responsibilities. This increases cognitive load and modification risk.

**Constraints:**
- Must preserve all public APIs (backward compatibility)
- Must integrate with existing factory pattern in `ClassicLib/integration/factory/`
- Must maintain Rust/Python fallback transparency
- Tests must continue passing without modification

## Goals / Non-Goals

**Goals:**
- Reduce file sizes through logical separation of concerns
- Improve code discoverability and navigation
- Align with existing project conventions (one class per file)
- Enable parallel development on separated modules

**Non-Goals:**
- Arbitrary line count targets (focus on logical separation)
- API changes or breaking changes
- Performance optimization (maintain current performance)
- Adding new functionality

## Decisions

### Decision 1: Directory-based organization for multi-class extractions

**What:** When extracting multiple classes from a single file, create a subdirectory with the same name as the original file (minus `.py`).

**Example:**
```
# Before
ClassicLib/rust/report_rust.py  (895 lines, 4 classes)

# After
ClassicLib/rust/report/
    __init__.py          (re-exports for backward compat)
    fragment.py          (RustAcceleratedReportFragment)
    composer.py          (RustAcceleratedReportComposer)
    generator.py         (RustAcceleratedReportGenerator)
    parallel.py          (ParallelReportProcessor)
```

**Why:** This pattern is already used in the codebase (e.g., `MessageHandler/`, `ScanLog/pipeline/`) and provides clear organization without breaking existing imports via `__init__.py` re-exports.

### Decision 2: Fallback code separation pattern

**What:** For Rust wrapper modules, extract Python fallback implementations to a `fallback/` subdirectory.

**Example:**
```
ClassicLib/rust/
    file_io_rust.py      (thin Rust wrapper only)
    fallback/
        __init__.py
        file_io_fallback.py  (pure Python implementation)
```

**Why:** This cleanly separates "Rust acceleration" from "Python fallback" concerns, making it obvious which code path is being used and simplifying maintenance of each.

### Decision 3: Strategy pattern for ResourceLoader

**What:** Extract path resolution strategies into a formal Strategy pattern.

**Why:** ResourceLoader currently has 5+ resource path strategies mixed together:
1. Frozen (PyInstaller) path resolution
2. Development path resolution
3. Installed package path resolution
4. Game-specific path resolution
5. User data path resolution

The Strategy pattern allows each to be tested, documented, and maintained independently.

### Decision 4: Preserve re-exports for backward compatibility

**What:** All extracted modules MUST have their public APIs re-exported from the original import location via `__init__.py`.

**Example:**
```python
# ClassicLib/rust/report/__init__.py
from .fragment import RustAcceleratedReportFragment
from .composer import RustAcceleratedReportComposer
from .generator import RustAcceleratedReportGenerator
from .parallel import ParallelReportProcessor

__all__ = [
    "RustAcceleratedReportFragment",
    "RustAcceleratedReportComposer",
    "RustAcceleratedReportGenerator",
    "ParallelReportProcessor",
]
```

**Why:** This ensures existing code continues to work without modification while enabling new code to use more specific imports.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Breaking existing imports | Re-exports in `__init__.py` maintain backward compat |
| Circular imports after split | Careful dependency ordering; use TYPE_CHECKING imports |
| Test coverage gaps | Run full test suite after each file split |
| Merge conflicts during refactor | Complete one file group before starting next |

## Migration Plan

1. **Phase 1: Rust wrappers** - Split `file_io_rust.py`, `report_rust.py`, `RustAcceleration.py`
2. **Phase 2: Core logic** - Split `OrchestratorCore.py`, `ResourceLoader.py`, `AsyncBridge.py`
3. **Phase 3: GUI** - Split `ResultsViewerWidgets.py`
4. **Rollback:** Each phase can be reverted independently via git

## Open Questions

None - this is a straightforward refactoring with well-established patterns.
