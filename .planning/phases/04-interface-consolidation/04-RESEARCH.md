# Phase 4: Interface Consolidation - Research

**Researched:** 2026-02-02
**Domain:** Async/sync interface patterns in hybrid Python-Rust desktop application
**Confidence:** HIGH

## Summary

This phase removes deprecated synchronous wrappers and dual-interface patterns, consolidating the codebase to exactly two async patterns: native async (CLI/TUI) and AsyncBridge (GUI). The work splits into three independent sub-phases: removing the FormIDAnalyzer sync wrapper, eliminating the YAML sync/ directory, and removing the `create_sync_wrapper` utility and related transitional helpers.

Research shows the codebase is well-prepared for this consolidation. The FormIDAnalyzer sync wrapper (156 lines) is assigned but never called in the orchestrator -- only `_async_formid_analyzer` (FormIDAnalyzerCore) is used at runtime. The YAML sync layer is heavily used (60+ call sites across `support/`, `Interface/`, `TUI/`, and `scanning/game/`) but the sync convenience functions (`yaml_settings`, `classic_settings`) already use `AsyncBridge.run_async()` internally, not `create_sync_wrapper`. The `create_sync_wrapper` function itself has limited production usage: FormIDAnalyzer.py (2 calls), sync_adapters.py (9 calls), and executor.py (1 call).

**Primary recommendation:** Execute the three sub-phases in dependency order: (1) FormID sync wrapper removal, (2) bridge helper removal, (3) YAML sync/ consolidation (which is the most complex due to widespread callers).

## Standard Stack

Not applicable -- this phase is purely an internal refactoring of existing code patterns. No new libraries are introduced.

### Core Patterns Used
| Pattern | Location | Purpose |
|---------|----------|---------|
| AsyncBridge.run_async() | ClassicLib/core/async_bridge.py | Stable GUI sync-to-async bridge |
| Native async/await | CLI entry points, OrchestratorCore | Async-first CLI pattern |
| Singleton with reset() | YamlSettingsCache | Thread-safe settings access |

## Architecture Patterns

### Current State: Three Sync-to-Async Mechanisms

1. **AsyncBridge.run_async()** (STABLE, KEEP) -- Used in GUI contexts directly. YamlSettingsCache.sync methods use this internally.
2. **create_sync_wrapper()** (DEPRECATED, REMOVE) -- Creates per-call wrappers that auto-detect GUI vs CLI mode. Used in FormIDAnalyzer.py, sync_adapters.py, executor.py.
3. **asyncio.run()** (CLI fallback in create_sync_wrapper) -- Creates new event loop per call. Inefficient for repeated calls.

### Target State: Two Patterns Only

1. **AsyncBridge.run_async()** -- For GUI sync contexts (Qt workers, PySide6 slots)
2. **Native async/await** -- For CLI/TUI/async contexts

### Pattern: FormID Sync Wrapper Removal

The FormIDAnalyzer.py sync wrapper class (156 lines) wraps FormIDAnalyzerCore. Analysis of all callers:

| Caller | File | Current Usage | Required Change |
|--------|------|---------------|-----------------|
| OrchestratorCore.__init__ | orchestrator_core.py:112 | `self.formid_analyzer = FormIDAnalyzer(...)` | **Dead assignment** -- only `_async_formid_analyzer` is used at runtime (lines 485-488, 661-662). Remove entirely. |
| formid_rust.py:69 | integration/rust/formid_rust.py | Imports as `PyFormIDAnalyzer` for Python fallback | Change to import FormIDAnalyzerCore directly (sync `extract_formids` method exists on both) |
| scanning/logs/__init__.py:29 | Package re-export | `from ... import FormIDAnalyzer` | Remove re-export |
| scanning/logs/analyzers/__init__.py:13 | Package re-export | `from ... import FormIDAnalyzer` | Remove re-export |

**Key insight:** The orchestrator assigns `self.formid_analyzer` in `__init__` but only ever uses `self._async_formid_analyzer` (set in `__aenter__`). The sync wrapper is entirely dead code in the actual call path.

### Pattern: YAML Sync Directory Consolidation

The `ClassicLib/io/yaml/sync/` directory contains 3 files:
- `cache.py` (474 lines) -- YamlSettingsCache singleton with sync methods that use AsyncBridge.run_async() directly (NOT create_sync_wrapper)
- `convenience.py` (215 lines) -- `yaml_settings()`, `classic_settings()`, `yaml_cache` proxy
- `__init__.py` (47 lines) -- Re-exports

**Critical finding:** `yaml_settings()` and `classic_settings()` do NOT use `create_sync_wrapper`. They call `YamlSettingsCache.async_yaml_settings()` which uses `AsyncBridge.run_async()` internally. This means the sync convenience functions are already using the target pattern.

**Call site analysis for sync YAML functions:**

| Location | Count | Context |
|----------|-------|---------|
| ClassicLib/support/*.py | ~40 calls | Sync functions called from GUI context |
| ClassicLib/Interface/*.py | ~20 calls | GUI controllers and widgets |
| ClassicLib/TUI/widgets/*.py | 3 calls | TUI widgets (sync context) |
| ClassicLib/scanning/game/*.py | ~10 calls | Game scanning (sync context) |

The sync convenience functions are **not deprecated** -- they are the GUI entry point pattern the success criteria call for ("sync wrappers at GUI entry points only"). The real question is where to put them after removing the `sync/` directory.

**Recommended approach:** Move `YamlSettingsCache` and the convenience functions up to `ClassicLib/io/yaml/` directly (or keep them in a renamed submodule). The success criterion says "ClassicLib/io/yaml/sync/ directory does not exist" -- but the sync convenience functions (`yaml_settings`, `classic_settings`) must remain accessible since they ARE the "sync wrappers at GUI entry points."

### Pattern: Bridge Helper Removal

`_async_utils/bridge_helpers.py` (252 lines) contains 5 exports:
1. `run_async` -- Convenience wrapper for `AsyncBridge.run_async()`. No production callers found outside bridge_helpers itself.
2. `run_async_with_timeout` -- Convenience wrapper. No production callers found.
3. `context_aware_sync` -- Decorator. No production callers found (only in docs/comments).
4. `smart_await` -- Helper. No production callers found (only in docs/comments).
5. `create_sync_wrapper` -- **The main target.** Used in 3 production files.

**Production callers of create_sync_wrapper:**

| File | Usage | Migration Path |
|------|-------|----------------|
| FormIDAnalyzer.py:35, 129, 154 | Wraps FormIDAnalyzerCore methods | Remove file entirely (dead code) |
| sync_adapters.py:60, 108-116 | Wraps FileIOCore async methods | Remove file entirely |
| executor.py:16, 425 | Wraps execute_scan for GUI | Replace with `AsyncBridge.run_async()` directly |

**Re-export chain for create_sync_wrapper:**
- Defined in `_async_utils/bridge_helpers.py`
- Re-exported by `_async_utils/__init__.py`
- Re-exported by `core/async_bridge.py` (lines 104, 607)

### Pattern: sync_adapters.py Removal

`io/files/sync_adapters.py` (144 lines) provides 9 `*_sync` file I/O functions plus `stream_lines_sync`.

**Production callers of sync file I/O functions:**

| Function | Callers | Migration |
|----------|---------|-----------|
| `read_file_sync` | wrye_check.py, results_viewer.py, ClassicLib/__init__.py | GUI contexts: use `AsyncBridge.run_async(io.read_file(...))` |
| `read_lines_sync` | xse.py, docs_path.py | Same pattern |
| `read_bytes_sync` | xse.py | Same pattern |
| `write_file_sync` | docs_path.py, yaml/sync/convenience.py, ClassicLib/__init__.py | Same pattern |
| `append_file_sync` | docs_path.py | Same pattern |
| `stream_lines_sync` | papyrus.py | **Not async** -- already a pure sync iterator. Must be preserved elsewhere (e.g., on FileIOCore directly or in io/files/__init__.py) |

**Key finding:** `stream_lines_sync` is NOT built with `create_sync_wrapper` -- it's a regular sync generator that delegates to `io_core.stream_lines_sync()` or falls back to `open_file_with_encoding()`. It must survive the removal of sync_adapters.py.

### Anti-Patterns to Avoid

- **Breaking the TUI sync callers:** TUI widgets call `yaml_settings()` and `classic_settings()` from sync contexts. These work because they detect "no running loop" and use AsyncBridge. Do NOT remove these functions.
- **Removing stream_lines_sync:** This is a legitimate sync API (generator-based), not a sync wrapper around an async function. It must be preserved.
- **Forgetting test callers:** Many tests import `read_file_sync`, `write_file_sync`, etc. Tests need updating too, but they can use `create_sync_wrapper` locally or `asyncio.run()` directly.
- **Breaking import paths:** `yaml_settings`, `classic_settings`, and `yaml_cache` are imported from many paths. All paths must continue working or be updated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sync-to-async bridging | Custom event loop management | `AsyncBridge.run_async()` | Already handles Qt event loop integration, thread safety, metrics |
| File I/O sync access in GUI | Individual `create_sync_wrapper` calls | Direct `AsyncBridge.run_async(io.method())` at call site | Eliminates indirection layer |
| YAML settings sync access | Per-method sync wrappers | YamlSettingsCache methods (already use AsyncBridge internally) | Already implemented correctly |

## Common Pitfalls

### Pitfall 1: Circular Import from YAML Consolidation
**What goes wrong:** Moving `YamlSettingsCache` or convenience functions triggers circular imports because YAML modules import from `core/` and `core/` imports from YAML.
**Why it happens:** The `yaml_settings` lazy import pattern exists specifically to avoid this.
**How to avoid:** Preserve lazy import patterns. Move files but keep the same import guards. Test imports in isolation before bulk-updating callers.
**Warning signs:** `ImportError` during `uv run python -c "import ClassicLib"`.

### Pitfall 2: Event Loop Already Running
**What goes wrong:** Removing `create_sync_wrapper` CLI fallback (`asyncio.run()`) and replacing with `AsyncBridge.run_async()` fails when called from async contexts.
**Why it happens:** `AsyncBridge.run_async()` submits to a background thread's event loop, which works. But the removed `asyncio.run()` fallback was also used in tests.
**How to avoid:** In tests that previously relied on `create_sync_wrapper`'s CLI mode (`asyncio.run()`), use `await` directly or `asyncio.run()` explicitly.
**Warning signs:** `RuntimeError: This event loop is already running` in test output.

### Pitfall 3: Removing YamlSettingsCache sync methods prematurely
**What goes wrong:** The success criterion says "YAML access is async-only with sync wrappers at GUI entry points only." This does NOT mean removing YamlSettingsCache sync methods.
**Why it happens:** Misreading the success criterion. The sync methods on YamlSettingsCache ARE the "sync wrappers at GUI entry points."
**How to avoid:** The goal is removing the `sync/` DIRECTORY (restructuring), not removing sync access. `yaml_settings()`, `classic_settings()`, `YamlSettingsCache` all survive -- they just move out of the `sync/` subdirectory.
**Warning signs:** 60+ call sites breaking across `support/`, `Interface/`, and `TUI/`.

### Pitfall 4: formid_rust.py Circular Import
**What goes wrong:** formid_rust.py imports `FormIDAnalyzer` from `scanning/logs/analyzers/FormIDAnalyzer.py` for its Python fallback. After removing FormIDAnalyzer.py, the import breaks.
**Why it happens:** The Rust wrapper uses the sync FormIDAnalyzer as its Python fallback for `formid_match`.
**How to avoid:** Change formid_rust.py to import `FormIDAnalyzerCore` directly or `PythonFormIDAnalyzer` from `integration/python/formid_py.py`.
**Warning signs:** `ImportError` when Rust is unavailable and Python fallback is needed.

### Pitfall 5: executor.py GUI Deadlock
**What goes wrong:** executor.py uses `create_sync_wrapper(self.execute_scan, strict=True)` for GUI-only scan execution. Replacing incorrectly could cause GUI deadlock.
**Why it happens:** The `strict=True` flag prevents CLI usage. The replacement must preserve this GUI-only behavior.
**How to avoid:** Replace with direct `AsyncBridge.get_instance().run_async(self.execute_scan())` and add a GUI-mode guard.
**Warning signs:** GUI freezes during scan, or CLI silently creates nested event loops.

## Code Examples

### Example 1: Replacing create_sync_wrapper in executor.py
```python
# BEFORE (executor.py)
from ClassicLib.core.async_bridge import create_sync_wrapper

def execute_scan_sync(self):
    wrapper = create_sync_wrapper(self.execute_scan, strict=True)
    return wrapper()

# AFTER
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.registry import GlobalRegistry

def execute_scan_sync(self):
    if not GlobalRegistry.is_gui_mode():
        raise RuntimeError(
            "execute_scan_sync() is GUI-only. Use 'await execute_scan()' in CLI/TUI."
        )
    return AsyncBridge.get_instance().run_async(self.execute_scan())
```

### Example 2: Removing FormIDAnalyzer from orchestrator_core.py
```python
# BEFORE (orchestrator_core.py)
from ClassicLib.scanning.logs.analyzers.FormIDAnalyzer import FormIDAnalyzer
# ...
self.formid_analyzer = FormIDAnalyzer(yamldata, show_formid_values or False, formid_db_exists)

# AFTER -- just remove the import and the assignment entirely.
# Only _async_formid_analyzer (FormIDAnalyzerCore) is used at runtime.
```

### Example 3: Replacing sync file I/O callers
```python
# BEFORE (wrye_check.py)
from ClassicLib.io.files import read_file_sync
html_content = read_file_sync(report_path)

# AFTER -- use AsyncBridge directly for GUI, or make function async
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.integration.factory import get_file_io

def _read_file_gui(path):
    """Read file synchronously in GUI context."""
    io_core = get_file_io()
    return AsyncBridge.get_instance().run_async(io_core.read_file(path))

html_content = _read_file_gui(report_path)
```

### Example 4: Moving YAML sync convenience (preserving API)
```python
# The sync/ directory is removed, but the functions survive.
# Option A: Move to io/yaml/convenience.py (flat in yaml package)
# Option B: Move to io/yaml/__init__.py directly (merge)
# Either way, all import paths like:
#   from ClassicLib.io.yaml import yaml_settings
# must continue to work via __init__.py re-exports.
```

### Example 5: Preserving stream_lines_sync
```python
# stream_lines_sync is NOT a create_sync_wrapper product.
# It's a pure sync generator. Move to io/files/__init__.py or io/files/core.py
# Note: FileIOCore already has stream_lines_sync as a static method.
# The sync_adapters version just delegates to it.
# After removing sync_adapters.py, export directly from FileIOCore.

# io/files/__init__.py
from ClassicLib.io.files.core import FileIOCore

def stream_lines_sync(path):
    """Stream file lines synchronously."""
    return FileIOCore.stream_lines_sync(path)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync-first with async bolted on | Async-first with sync at GUI entry points | Phase 3 (completed) | All business logic is async |
| `create_sync_wrapper` per method | Direct `AsyncBridge.run_async()` | This phase (4) | Removes indirection layer |
| Separate sync/async YAML directories | Single YAML module with sync convenience | This phase (4) | Reduces file count and confusion |

## Open Questions

1. **Where to relocate YAML sync convenience functions?**
   - What we know: The `sync/` directory must not exist. The functions must survive. ~60 call sites import them.
   - What's unclear: Should they move to `io/yaml/convenience.py` (new flat file) or merge into `io/yaml/__init__.py`?
   - Recommendation: Create `io/yaml/convenience.py` for the functions and `io/yaml/cache.py` for YamlSettingsCache. Keep `io/yaml/__init__.py` as the re-export hub. This minimizes import path changes.

2. **Should `_async_utils/bridge_helpers.py` be deleted entirely or just pruned?**
   - What we know: `create_sync_wrapper`, `context_aware_sync`, `smart_await` are all targeted for removal. `run_async` and `run_async_with_timeout` are convenience wrappers with no production callers.
   - What's unclear: Whether `run_async`/`run_async_with_timeout` are used via the `core/async_bridge.py` re-export path.
   - Recommendation: Delete the entire file. The re-exports in `core/async_bridge.py` can import from `AsyncBridge` class methods directly or be removed. Verify no production callers exist first.

3. **How to handle test files that import sync adapters?**
   - What we know: Multiple test files import `read_file_sync`, `write_file_sync`, etc.
   - What's unclear: Should tests use `asyncio.run()` wrappers, or should a test-only sync utility be provided?
   - Recommendation: Tests should use `await` directly (most tests are already `@pytest.mark.asyncio`). For remaining sync tests, use `asyncio.run()` inline.

## Dependency and Ordering Analysis

### Sub-phase Dependencies

```
04-01: FormID sync wrapper removal
  - No dependencies on other sub-phases
  - Enables: nothing (standalone)

04-02: Bridge helper removal (create_sync_wrapper + sync_adapters)
  - Depends on: 04-01 (FormIDAnalyzer.py must be gone first, as it imports create_sync_wrapper)
  - Enables: 04-03 (after bridge_helpers is gone, yaml sync/ can be restructured cleanly)

04-03: YAML sync/ directory consolidation
  - Depends on: 04-02 (yaml/sync/convenience.py imports write_file_sync from sync_adapters)
  - Most callers, highest risk, do last
```

**Recommended execution order:** 04-01 -> 04-02 -> 04-03

### Cross-cutting Concerns

- `ClassicLib/__init__.py` re-exports `read_file_sync`, `write_file_sync`, `yaml_settings`, `classic_settings` -- all must be updated
- `ClassicLib/io/files/__init__.py` re-exports all sync adapters -- must be restructured
- `ClassicLib/io/yaml/__init__.py` re-exports from sync/ -- must be updated
- `ClassicLib/core/async_bridge.py` re-exports from bridge_helpers -- must be updated

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all files referenced above
- grep/read of all callers, imports, and re-export chains
- Line-by-line review of FormIDAnalyzer.py, bridge_helpers.py, sync_adapters.py, yaml/sync/*.py

### Secondary (MEDIUM confidence)
- OrchestratorCore runtime analysis (confirmed `self.formid_analyzer` is assigned but never called -- only `_async_formid_analyzer` is used)

## Metadata

**Confidence breakdown:**
- FormID wrapper removal: HIGH -- dead code path confirmed by grep
- Bridge helper removal: HIGH -- all callers traced, migration paths clear
- YAML sync/ consolidation: HIGH -- all callers traced, but execution is complex due to 60+ call sites
- Pitfalls: HIGH -- based on direct code analysis of import chains and runtime behavior

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable internal refactoring, no external dependencies)
