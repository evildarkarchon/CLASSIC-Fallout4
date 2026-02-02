# Phase 2: Integration Layer Simplification - Research

**Researched:** 2026-02-01
**Domain:** Python module restructuring, type narrowing, dead code removal
**Confidence:** HIGH

## Summary

This phase restructures the Python-Rust integration boundary from a multi-layer architecture (factory subpackage + detector + status + acceleration coordinator) into a single flat `factory.py` module with direct try-import. The current codebase has three overlapping detection/caching layers and an unused acceleration coordinator package.

Research confirms that the acceleration package has **zero production code callers** outside its own directory -- only test code and internal cross-references import from it. The factory subpackage consists of 8 submodules that all follow the same pattern: call `get_components()` to check a cached dict, then try-import the Rust module. This can be collapsed into direct try-import in each factory function, relying on Python's `sys.modules` cache for performance.

**Primary recommendation:** Execute as two sequential plans (02-01: factory collapse, 02-02: acceleration removal + type narrowing) with full test suite verification between each.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typing.Protocol | stdlib (3.12+) | Define structural interfaces for factory return types | Standard approach for structural subtyping in Python |
| pyright | latest | Static type checking for factory module | Already configured in project, success criteria requires it |
| pytest | 9.x | Test verification after each plan | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing.runtime_checkable | stdlib | Make Protocols checkable at runtime with isinstance | Only if runtime Protocol checks are needed (not recommended for hot paths) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Protocol classes | ABC (Abstract Base Class) | Protocol is structural (duck typing), ABC requires explicit inheritance -- Protocol fits this use case since Rust types can't inherit from Python ABCs |
| Separate types.py module | Inline in factory.py | CONTEXT.md decided types.py lives in `integration/types.py`, not inline |

## Architecture Patterns

### Current Structure (BEFORE)
```
ClassicLib/integration/
├── __init__.py            # Re-exports detector + diagnostics + exceptions
├── config.py              # Component names, multipliers, categories
├── detector.py            # detect_rust_components(), detect_component(), _detection_cache
├── diagnostics.py         # Runtime diagnostics (Tokio health)
├── exceptions.py          # RustError hierarchy
├── scangame_factory.py    # Separate factory for ScanGame (already flat!)
├── status.py              # RUST_AVAILABLE dict, print_rust_status(), is_rust_accelerated()
├── factory/               # Subpackage with 8 modules
│   ├── __init__.py        # Re-exports all 23+ factory functions
│   ├── core.py            # _components_cache, get_components(), is_rust_disabled()
│   ├── analyzers.py       # 6 factory functions
│   ├── database.py        # 1 factory function
│   ├── file_io.py         # 2 factory functions (singleton pattern)
│   ├── game.py            # 2 factory functions
│   ├── parsers.py         # 1 factory function + PythonParserWrapper class
│   ├── scanlog.py         # 3 factory functions
│   └── utilities.py       # 6 factory functions
├── rust/                  # Rust wrapper modules (NOT touched in this phase)
└── python/                # Python fallback modules (NOT touched in this phase)

ClassicLib/acceleration/   # ~400 lines, zero production callers
├── __init__.py
├── coordinator.py         # RustAcceleration singleton
├── metrics.py             # ComponentMetrics dataclass
├── types.py               # ComponentType enum
└── workload.py            # WorkloadCharacteristics, OptimizationLevel
```

### Target Structure (AFTER)
```
ClassicLib/integration/
├── __init__.py            # Simplified: exceptions + diagnostics only
├── config.py              # KEEP: DISABLE_RUST_ENV_VAR only (strip categories/multipliers)
├── diagnostics.py         # KEEP: Runtime diagnostics (independent, useful)
├── exceptions.py          # KEEP: Exception hierarchy (used widely)
├── factory.py             # NEW: Single flat module with all factory functions
├── scangame_factory.py    # KEEP: Already flat, already uses try-import pattern
├── types.py               # NEW: Protocol classes for factory return types
├── rust/                  # UNCHANGED
└── python/                # UNCHANGED

# DELETED:
# ClassicLib/acceleration/  (entire directory)
# ClassicLib/integration/factory/  (subpackage, replaced by factory.py)
# ClassicLib/integration/detector.py  (absorbed into factory.py)
# ClassicLib/integration/status.py  (removed entirely)
```

### Pattern 1: Try-Import Factory Function
**What:** Each factory function directly tries to import its Rust module, no pre-detection layer.
**When to use:** Every factory function in the new flat factory.py.
**Example:**
```python
# Source: Modeled on existing scangame_factory.py pattern (already in codebase)
def get_yaml_operations() -> YamlOperationsProtocol | None:
    """Get YAML operations (Rust-accelerated if available)."""
    if _is_rust_disabled():
        return None
    try:
        import classic_yaml
        return classic_yaml.YamlOperations()
    except ImportError:
        return None
```

### Pattern 2: Protocol-Based Return Types
**What:** Define Protocol classes that describe the interface both Rust and Python implementations satisfy.
**When to use:** For factory functions that return objects with known method interfaces.
**Example:**
```python
# integration/types.py
from typing import Protocol

class FileIOProtocol(Protocol):
    """Interface for file I/O operations."""
    def read_text(self, path: str, encoding: str = "utf-8") -> str: ...
    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None: ...
```

### Pattern 3: Fail-Loud on Missing Components
**What:** Factory functions raise ImportError instead of returning None when a required component is completely unavailable (neither Rust nor Python fallback).
**When to use:** For components that have both Rust and Python implementations (parser, formid_analyzer, etc.).
**Example:**
```python
def get_parser() -> LogParserProtocol:
    """Get log parser (Rust or Python fallback)."""
    if not _is_rust_disabled():
        try:
            from ClassicLib.integration.rust.parser_rust import RustLogParser
            return RustLogParser()
        except ImportError:
            pass
    # Python fallback always available
    from ClassicLib.integration.factory import PythonParserWrapper
    return PythonParserWrapper()
```

### Anti-Patterns to Avoid
- **Don't add backward compatibility shims:** CONTEXT.md explicitly decided against re-export shims or deprecation wrappers. Update all call sites immediately.
- **Don't cache detection results:** Python's `sys.modules` already caches imports. Custom `_components_cache` and `_detection_cache` dicts add complexity without benefit.
- **Don't check component availability before calling factory:** Callers should just call the factory function and handle the result. No `is_rust_available()` / `is_component_available()` checks needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import caching | Custom `_components_cache` dict | Python's `sys.modules` | Built-in, thread-safe, zero overhead after first import |
| Structural typing | Manual duck-type checks | `typing.Protocol` | Standard, checked by pyright, self-documenting |
| Singleton detection state | Module-level mutable dicts | Fresh try-import per call | Eliminates stale state bugs, simpler to test |

**Key insight:** The existing three-layer detection system (detector -> factory/core -> status) exists because the original design tried to cache and track component availability. Python's import system already does this. The entire detection layer is solving a problem that doesn't exist.

## Common Pitfalls

### Pitfall 1: Breaking the integration/rust/ Wrappers
**What goes wrong:** The `integration/rust/` wrapper modules (14 files) all import `from ClassicLib.integration.detector import detect_component`. When detector.py is removed, these all break.
**Why it happens:** detector.py's `detect_component()` function is used by wrapper modules at module level to set `RUST_AVAILABLE` flags.
**How to avoid:** The `detect_component()` function must either be preserved somewhere (e.g., as a utility in factory.py or a thin helper) OR every wrapper module must be updated to use its own try-import pattern. Since CONTEXT.md says "no caching," the wrapper modules should each do their own try-import at module level.
**Warning signs:** Any test importing from `ClassicLib.integration.rust.*` will fail if this is missed.

**Files that import detect_component from detector.py (14 files):**
1. `ClassicLib/integration/rust/suspect_rust.py`
2. `ClassicLib/integration/rust/settings_rust.py`
3. `ClassicLib/integration/rust/orchestrator_api.py`
4. `ClassicLib/integration/rust/formid_rust.py`
5. `ClassicLib/integration/rust/mod_detector_rust.py`
6. `ClassicLib/integration/rust/fcx_rust.py`
7. `ClassicLib/integration/rust/gpu_rust.py`
8. `ClassicLib/integration/rust/report/__init__.py`
9. `ClassicLib/integration/rust/file_io_rust.py`
10. `ClassicLib/integration/rust/report/composer.py`
11. `ClassicLib/integration/rust/plugin_rust.py`
12. `ClassicLib/integration/rust/record_rust.py`
13. `ClassicLib/integration/rust/report/parallel.py`
14. `ClassicLib/integration/rust/report/fragment.py`
15. `ClassicLib/integration/rust/report/generator.py`
16. `ClassicLib/integration/rust/parser_rust.py`
17. `ClassicLib/io/database/rust_pool.py`
18. `ClassicLib/scanning/game/checks/dds_processor.py`
19. `ClassicLib/__init__.py`
20. `ClassicLib/core/rust_loader.py`

**Recommendation:** Keep `detect_component()` as a thin utility function in the new `factory.py`. It's a 20-line function that does try-import with optional attribute lookup. It's used by 20 files. Removing it would require touching all 20 files for no benefit. The key decision was to remove caching layers, not this utility.

### Pitfall 2: is_rust_accelerated() Callers in Production Code
**What goes wrong:** `is_rust_accelerated()` from `status.py` is called by 6 production code files for logging/diagnostics. Removing `status.py` breaks these.
**Why it happens:** Production code uses `is_rust_accelerated("parser")` to log which implementation is active.
**How to avoid:** These callers use it purely for logging. Replace with a simple utility: `try: import classic_scanlog; has_parser = True except ImportError: has_parser = False`. Or provide a thin `is_rust_accelerated()` in the new factory.py.
**Warning signs:** Workers.py, results_viewer.py, orchestrator_core.py, hybrid_orchestrator.py, parser.py, pool_manager.py all import from status.py.

**Production callers of is_rust_accelerated():**
- `ClassicLib/Interface/workers/Workers.py` (2 calls, logging only)
- `ClassicLib/Interface/controllers/results_viewer.py` (1 call, logging only)
- `ClassicLib/scanning/logs/orchestrator_core.py` (logging)
- `ClassicLib/scanning/logs/hybrid_orchestrator.py` (logging)
- `ClassicLib/scanning/logs/parser.py` (logging)
- `ClassicLib/io/database/pool_manager.py` (conditional logic)

**Production callers of get_rust_component_status():**
- `ClassicLib/support/setup.py` (diagnostic logging)

### Pitfall 3: CI Pipeline References
**What goes wrong:** `.github/workflows/ci.yml` line 348 has `from ClassicLib.integration.status import print_rust_status; print_rust_status()`. Multiple doc files and `01-project-overview.md` reference this too.
**Why it happens:** `print_rust_status()` was the diagnostic entry point.
**How to avoid:** Update CI workflow and all rule/doc references. Either remove the CI step or replace with a simpler diagnostic.
**Warning signs:** CI pipeline failure after merging.

### Pitfall 4: Singleton Reset Fixture Must Be Updated
**What goes wrong:** `tests/fixtures/singleton_fixtures.py` resets `RustAcceleration.reset_instance()`, `reset_cache()` from factory/core.py, and `_file_io_instance`. When these are restructured, the fixture breaks and tests leak state.
**Why it happens:** The fixture directly imports from module paths that will change.
**How to avoid:** Update singleton_fixtures.py in the same plan that changes the module paths.
**Warning signs:** State leakage between tests causing intermittent failures.

### Pitfall 5: config.py Constants Still Referenced
**What goes wrong:** `config.py` contains `DISABLE_RUST_ENV_VAR`, `ALL_COMPONENTS`, `COMPONENT_CATEGORIES`, `PERFORMANCE_MULTIPLIERS`, etc. Status.py and detector.py import from it.
**Why it happens:** config.py bundles env var name with display-only data.
**How to avoid:** Keep `DISABLE_RUST_ENV_VAR` (needed by factory for `is_rust_disabled()`). The rest (`PERFORMANCE_MULTIPLIERS`, `COMPONENT_CATEGORIES`, `ALL_COMPONENTS`, threshold constants) are only used by status.py and the acceleration package -- both being removed. Strip config.py down to just the env var constant.
**Warning signs:** ImportError if config.py is removed entirely.

### Pitfall 6: scangame_factory.py Already Has the Right Pattern
**What goes wrong:** Developer might try to merge scangame_factory.py into the new factory.py.
**Why it happens:** It looks like another factory module.
**How to avoid:** scangame_factory.py is a separate, already-flat factory for the ScanGame domain. It already uses try-import at module level. Leave it alone -- it's not part of the factory/ subpackage being collapsed.
**Warning signs:** Unnecessary code churn.

### Pitfall 7: PythonParserWrapper Class
**What goes wrong:** `PythonParserWrapper` lives in `factory/parsers.py` and is exported from the factory `__init__.py`. Tests import it. If factory/ is deleted, its home must be decided.
**Why it happens:** It's a Python fallback implementation that happens to live in the factory layer.
**How to avoid:** Move it into the new flat `factory.py` or to `integration/python/parser_py.py`. It's a small class (~30 lines) used by `get_parser()` as the fallback.
**Warning signs:** ImportError in tests that reference `PythonParserWrapper`.

## Code Examples

### Example 1: New Factory Function (Try-Import Pattern)
```python
# ClassicLib/integration/factory.py
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DISABLE_RUST_ENV_VAR = "CLASSIC_DISABLE_RUST"

def _is_rust_disabled() -> bool:
    return os.environ.get(_DISABLE_RUST_ENV_VAR, "").lower() in {"1", "true", "yes"}

def get_parser() -> Any:
    """Get log parser implementation (Rust-accelerated if available)."""
    if not _is_rust_disabled():
        try:
            from ClassicLib.integration.rust.parser_rust import RustLogParser
            return RustLogParser()
        except ImportError:
            pass
    from ClassicLib.integration.factory import PythonParserWrapper
    return PythonParserWrapper()
```

### Example 2: Protocol Class in types.py
```python
# ClassicLib/integration/types.py
from __future__ import annotations
from typing import Protocol

class LogParserProtocol(Protocol):
    """Interface for crash log parsers."""
    def find_segments(
        self,
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
    ) -> tuple[str, str, str, list[list[str]]]: ...

    def extract_section(
        self,
        crash_data: list[str],
        start_marker: str,
        end_marker: str,
    ) -> list[str] | None: ...
```

### Example 3: Preserving detect_component() Utility
```python
# In ClassicLib/integration/factory.py (or as a standalone utility)
def detect_component(module_name: str, class_name: str | None = None) -> tuple[bool, Any | None]:
    """Try-import a Rust module/class. No caching -- relies on sys.modules.

    Args:
        module_name: Python module name (e.g., "classic_yaml")
        class_name: Optional class name within module

    Returns:
        Tuple of (available: bool, component: class | module | None)
    """
    try:
        module = __import__(module_name)
        if class_name:
            if not hasattr(module, class_name):
                return (False, None)
            return (True, getattr(module, class_name))
        return (True, module)
    except ImportError:
        return (False, None)
```

### Example 4: FileIO Singleton Preservation
```python
# The FileIO singleton pattern must be preserved because FileIOCore instances
# hold configuration state (encoding, errors). Use threading.Lock pattern.
import threading
_file_io_instance: Any = None
_file_io_lock = threading.Lock()

def get_file_io(encoding: str = "utf-8", errors: str = "ignore") -> Any:
    global _file_io_instance
    if _file_io_instance is not None:
        return _file_io_instance
    with _file_io_lock:
        if _file_io_instance is not None:
            return _file_io_instance
        if not _is_rust_disabled():
            try:
                from ClassicLib.integration.rust.file_io_rust import FileIOCore
                _file_io_instance = FileIOCore(encoding, errors)
                return _file_io_instance
            except ImportError:
                pass
        from ClassicLib.integration.python.file_io_py import FileIOCore
        _file_io_instance = FileIOCore(encoding, errors)
        return _file_io_instance
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Three-layer detection (detector -> factory/core -> status) | Direct try-import in factory | This phase | Removes ~600 lines of detection/caching code |
| Mutable global dicts for caching (`_components_cache`, `_detection_cache`) | `sys.modules` for import caching | This phase | Eliminates stale state, simplifies testing |
| `Any` return types on factory functions | Protocol-based return types | This phase | Enables pyright to catch type errors |
| Acceleration coordinator (~400 lines) | Direct factory calls | This phase | Removes unused abstraction layer |

**Deprecated/outdated by this phase:**
- `ClassicLib/acceleration/` -- zero production callers, pure overhead
- `ClassicLib/integration/status.py` -- detection state tracking that duplicates detector.py
- `ClassicLib/integration/detector.py` -- complex detection with MODULE_CONFIGS dict, only `detect_component()` utility survives
- `ClassicLib/integration/factory/core.py` -- `_components_cache` and `get_components()` no longer needed
- `ClassicLib/core/rust_loader.py` -- Legacy wrapper around detector, should be evaluated for removal

## Quantitative Impact

### Files to Delete
| File/Directory | Lines | Reason |
|---------------|-------|--------|
| `ClassicLib/acceleration/__init__.py` | 53 | Zero production callers |
| `ClassicLib/acceleration/coordinator.py` | 593 | Zero production callers |
| `ClassicLib/acceleration/metrics.py` | 105 | Zero production callers |
| `ClassicLib/acceleration/types.py` | 41 | Zero production callers |
| `ClassicLib/acceleration/workload.py` | 170 | Zero production callers |
| `ClassicLib/integration/factory/__init__.py` | 124 | Replaced by flat factory.py |
| `ClassicLib/integration/factory/core.py` | 69 | Caching eliminated |
| `ClassicLib/integration/factory/analyzers.py` | 218 | Merged into factory.py |
| `ClassicLib/integration/factory/database.py` | 54 | Merged into factory.py |
| `ClassicLib/integration/factory/file_io.py` | 112 | Merged into factory.py |
| `ClassicLib/integration/factory/game.py` | 94 | Merged into factory.py |
| `ClassicLib/integration/factory/parsers.py` | 128 | Merged into factory.py |
| `ClassicLib/integration/factory/scanlog.py` | 206 | Merged into factory.py |
| `ClassicLib/integration/factory/utilities.py` | 234 | Merged into factory.py |
| `ClassicLib/integration/status.py` | 361 | Replaced by factory utilities |
| `ClassicLib/integration/detector.py` | 382 | detect_component() preserved in factory.py |
| **Total** | **~2,944** | |

### Files to Create
| File | Estimated Lines | Purpose |
|------|----------------|---------|
| `ClassicLib/integration/factory.py` | ~400 | All factory functions + detect_component utility |
| `ClassicLib/integration/types.py` | ~150 | Protocol classes for return types |
| **Total** | **~550** | |

### Net Reduction: ~2,400 lines

### Files to Modify (Import Path Updates)
| Category | Count | Nature of Change |
|----------|-------|-----------------|
| Production code (factory imports) | ~15 | `from ClassicLib.integration.factory import X` -- path unchanged if module re-exports match |
| Production code (status imports) | ~6 | `is_rust_accelerated()` callers need replacement |
| Production code (detector imports) | ~20 | `detect_component()` callers need new import path |
| Test files (factory) | ~8 | Test internal module paths change |
| Test files (status) | ~40+ | Many test files import from status.py |
| Test files (acceleration) | ~1 | Entire test file removed |
| Test files (detection) | ~1 | Test file for centralized detection |
| CI/docs | ~15+ | References to print_rust_status() and import paths |
| Singleton fixtures | 1 | Reset paths change |

## Open Questions

1. **Should detect_component() move to factory.py or stay as a separate utility?**
   - What we know: 20 files import it. It's a clean, simple function.
   - What's unclear: Whether putting it in factory.py creates a circular import risk (factory.py importing from integration/rust/ while rust/ imports detect_component from factory.py).
   - Recommendation: Keep it in factory.py -- the imports are lazy (inside functions or at module top-level for wrapper modules), not circular. Alternatively, a tiny `_utils.py` would work.

2. **Should config.py survive or be inlined?**
   - What we know: Only `DISABLE_RUST_ENV_VAR` is needed after removing status.py.
   - What's unclear: Whether other code references other config.py constants.
   - Recommendation: Inline `DISABLE_RUST_ENV_VAR = "CLASSIC_DISABLE_RUST"` in factory.py. Delete config.py. The constant is 1 line.

3. **What replaces is_rust_accelerated() for production callers?**
   - What we know: 6 production files use it for logging only.
   - What's unclear: Whether a thin replacement or direct try-import is better.
   - Recommendation: Provide a simple `is_component_available(name: str) -> bool` utility in factory.py that does try-import check. Or let callers use `detect_component()` directly.

4. **rust_loader.py disposition**
   - What we know: It's a legacy wrapper that delegates to detector.py. It auto-loads on import.
   - What's unclear: Whether anything imports from it besides `ClassicLib/__init__.py` (which doesn't).
   - Recommendation: Audit callers in plan. If only tests use it, mark for removal. If production code uses it, redirect to factory.py.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all 50+ files in the integration/acceleration layer
- `ClassicLib/integration/` -- full read of all modules
- `ClassicLib/acceleration/` -- full read of all modules
- `tests/fixtures/singleton_fixtures.py` -- singleton reset patterns
- Grep analysis of all import paths across entire codebase

### Secondary (MEDIUM confidence)
- Python `typing.Protocol` documentation (stdlib, well-established since Python 3.8+)
- Python import system `sys.modules` caching behavior (well-documented stdlib behavior)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only (Protocol, os, logging, threading)
- Architecture: HIGH - based on exhaustive codebase analysis with exact file counts and line numbers
- Pitfalls: HIGH - every pitfall identified by tracing actual import dependencies in the codebase
- Quantitative impact: MEDIUM - line counts are approximate (from file reads, not exact `wc -l`)

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable -- internal refactoring, no external dependencies)
