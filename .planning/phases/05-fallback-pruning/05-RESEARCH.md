# Phase 5: Fallback Pruning - Research

**Researched:** 2026-02-02
**Domain:** Python fallback removal, factory pattern refactoring, PyInstaller spec maintenance
**Confidence:** HIGH

## Summary

Phase 5 removes the 8 Python fallback implementation files in `ClassicLib/integration/python/` and updates the factory functions and rust wrapper modules that reference them. The research focused on mapping every import dependency on these files, understanding which rust wrappers have their own inline fallback logic (and thus only need import removal, not logic replacement), and identifying all spec files that need cleanup.

The key finding is that fallback references exist in three distinct locations: factory.py, rust wrapper modules, and the python `__init__.py`. Some rust wrapper files (formid_rust.py, record_rust.py, file_io_rust.py) already fall back to non-fallback Python code elsewhere in the codebase, so removing their corresponding fallback files requires no wrapper changes. Others (parser_rust.py, plugin_rust.py, mod_detector_rust.py) import directly from the fallback files and need their fallback paths removed or converted to errors.

**Primary recommendation:** Remove fallbacks in dependency order -- start with files that have zero rust-wrapper imports (database_py, formid_py, record_py, file_io_py, report_py), then tackle those with rust-wrapper imports (parser_py, plugin_py, mod_detector_py) which require more surgical edits to the wrapper modules.

## Standard Stack

Not applicable -- this phase uses no new libraries. It is purely a deletion and refactoring exercise within the existing codebase.

## Architecture Patterns

### Current Fallback Architecture

Each factory function in `factory.py` follows this pattern:
```python
def get_X():
    if not _is_rust_disabled():
        try:
            from ClassicLib.integration.rust.X_rust import RustX
            return RustX()
        except ImportError:
            pass
    from ClassicLib.integration.python.X_py import X  # FALLBACK
    return X()
```

### Target Architecture (Post-Phase-5)

Factory functions raise clear errors instead of falling back:
```python
def get_X():
    try:
        from ClassicLib.integration.rust.X_rust import RustX
        return RustX()
    except ImportError as e:
        raise RuntimeError(
            f"Required Rust module for X not available: {e}. "
            "Reinstall CLASSIC or check your installation."
        ) from e
```

### Recommended Startup Validation Pattern

Add a validation function called early in each entry point (CLASSIC_Interface.py, CLASSIC_ScanLogs.py):
```python
def validate_rust_modules() -> None:
    """Check all required Rust modules are importable. Fail fast with clear error."""
    required_modules = [
        ("classic_scanlog", "LogParser"),
        ("classic_scanlog", "FormIDAnalyzerCore"),
        ("classic_scanlog", "PluginAnalyzer"),
        ("classic_scanlog", "RecordScanner"),
        ("classic_scanlog", "ReportGenerator"),
        ("classic_scanlog", "detect_mods_single"),
        ("classic_file_io", "FileIOCore"),
        ("classic_yaml", "YamlOperations"),
        # ... etc
    ]
    for module_name, class_name in required_modules:
        available, _ = detect_component(module_name, class_name)
        if not available:
            raise RuntimeError(
                f"Required Rust component {module_name}.{class_name} not found. "
                "Please reinstall CLASSIC."
            )
```

### Removal Structure Per Fallback

Each fallback removal is atomic and includes:
1. Delete `ClassicLib/integration/python/X_py.py`
2. Remove the fallback import path in `factory.py` (the `from ClassicLib.integration.python.X_py import ...` line and surrounding try/except or if/else)
3. Remove any fallback imports in rust wrapper modules (`ClassicLib/integration/rust/X_rust.py`)
4. Update `ClassicLib/integration/python/__init__.py` to remove the deleted module's exports
5. Delete associated test file `tests/python_fallback/test_X_py_unit.py`
6. Run full test suite

### Anti-Patterns to Avoid

- **Removing all 8 at once**: Isolate breakage by removing one at a time and running tests between each removal.
- **Leaving dead imports in `__init__.py`**: Each removal must update `ClassicLib/integration/python/__init__.py`.
- **Forgetting rust wrapper inline fallbacks**: Some rust wrappers (`plugin_rust.py`, `parser_rust.py`, `mod_detector_rust.py`) import from the fallback files inside their method bodies, not just at module level. These lazy imports must also be removed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Startup validation | Custom import hook system | Simple loop over `detect_component()` calls | detect_component already exists and handles try/except |
| Error formatting | Custom error dialog system | `RuntimeError` with descriptive message | Keep it simple; GUI can catch and display later |

## Common Pitfalls

### Pitfall 1: Rust Wrapper Inline Fallbacks
**What goes wrong:** Deleting `plugin_py.py` without updating `plugin_rust.py` causes ImportError at runtime when Rust parse fails and Python fallback is attempted.
**Why it happens:** The rust wrapper modules (`plugin_rust.py`, `parser_rust.py`, `mod_detector_rust.py`) contain lazy imports from the fallback files inside method bodies (not just at module level).
**How to avoid:** For each fallback file, grep ALL references in the entire `ClassicLib/` tree, not just `factory.py`.
**Warning signs:** `from ClassicLib.integration.python.X_py import` appearing inside method bodies in rust wrapper files.

### Pitfall 2: The `file_io_py.py` vs `ClassicLib.io.files.core` Distinction
**What goes wrong:** Assuming `file_io_py.py` is used as fallback by `file_io_rust.py`.
**Why it happens:** `file_io_rust.py` actually falls back to `ClassicLib.io.files.core.FileIOCore`, NOT to `file_io_py.py`. But `factory.py` line 318 imports `FileIOCore` from `file_io_py.py` as its factory fallback.
**How to avoid:** Check both `factory.py` AND the rust wrapper for each component.
**Warning signs:** Different fallback paths in factory.py vs the rust wrapper module.

### Pitfall 3: The formid_rust.py Python Analyzer
**What goes wrong:** Assuming formid fallback is in `formid_py.py`.
**Why it happens:** `formid_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore`, not `formid_py.py`. But `factory.py` line 368 imports `FormIDAnalyzer` from `formid_py.py`.
**How to avoid:** Trace the actual runtime fallback path for each component.

### Pitfall 4: PythonParserWrapper in factory.py
**What goes wrong:** Removing `parser_py.py` breaks `PythonParserWrapper` which is defined inside `factory.py` itself.
**Why it happens:** `PythonParserWrapper.find_segments()` lazily imports from `parser_py.py` at line 189. The class is also in `__all__`.
**How to avoid:** Remove `PythonParserWrapper` class from `factory.py` entirely, or rewire it.

### Pitfall 5: The `CLASSIC_DISABLE_RUST` Environment Variable
**What goes wrong:** After removing fallbacks, setting `CLASSIC_DISABLE_RUST=1` causes crashes.
**Why it happens:** `_is_rust_disabled()` in `factory.py` is still checked, and code paths that returned Python fallbacks now have nothing to return.
**How to avoid:** Either remove `CLASSIC_DISABLE_RUST` support entirely, or make it emit a warning but still use Rust. The startup validation should run regardless.

### Pitfall 6: Test Files That Directly Import Fallbacks
**What goes wrong:** Tests in `tests/python_fallback/` and `tests/python/test_report_py_unit.py` fail because they directly import from the deleted modules.
**Why it happens:** These tests exist specifically to test the Python fallback implementations.
**How to avoid:** Delete the corresponding test files when deleting the fallback.

### Pitfall 7: Stale Spec File References
**What goes wrong:** PyInstaller build fails or warns about missing modules.
**Why it happens:** Spec files reference `ClassicLib.integration.config`, `ClassicLib.integration.status`, `ClassicLib.integration.detector` which already don't exist.
**How to avoid:** Clean up ALL stale references in spec files, not just the ones from this phase.

## Code Examples

### Example: Removing database_py.py (Simplest Case)

`database_py.py` is only referenced by:
- `ClassicLib/integration/python/__init__.py` (line 12)
- `tests/python_fallback/test_database_py_unit.py`
- `factory.py` does NOT import from it (database fallback goes to `ClassicLib.io.database.async_pool`)

Steps:
1. Delete `ClassicLib/integration/python/database_py.py`
2. Remove `PythonDatabasePool` from `__init__.py`
3. Delete `tests/python_fallback/test_database_py_unit.py`
4. Run tests

### Example: Removing plugin_py.py (Complex Case)

`plugin_py.py` is referenced by:
- `ClassicLib/integration/python/__init__.py` (line 26)
- `factory.py` line 393 (factory fallback)
- `plugin_rust.py` lines 116, 166, 207, 241, 270 (5 inline fallbacks!)
- `tests/python_fallback/test_plugin_py_unit.py`

Steps:
1. Delete `ClassicLib/integration/python/plugin_py.py`
2. Remove `PythonPluginAnalyzer` from `__init__.py`
3. In `factory.py` `get_plugin_analyzer()`: replace the fallback import with a `raise RuntimeError(...)`
4. In `plugin_rust.py`: remove all 5 lazy fallback imports and their associated code paths, converting to `raise RuntimeError(...)` on Rust failure
5. Delete `tests/python_fallback/test_plugin_py_unit.py`
6. Run tests

### Example: Startup Validation Integration

In `CLASSIC_Interface.py`, add before `QApplication` creation:
```python
from ClassicLib.integration.factory import detect_component

def _validate_rust_modules() -> None:
    required = [
        ("classic_scanlog", "LogParser"),
        ("classic_file_io", "FileIOCore"),
        ("classic_yaml", "YamlOperations"),
    ]
    for mod, cls in required:
        ok, _ = detect_component(mod, cls)
        if not ok:
            raise RuntimeError(f"Missing required Rust module: {mod}.{cls}")

_validate_rust_modules()
```

## Detailed Dependency Map

### Fallback File Reference Matrix

| Fallback File | factory.py | Rust Wrapper | `__init__.py` | Tests | Verdict |
|---|---|---|---|---|---|
| `database_py.py` | NO (uses `io.database.async_pool`) | NO | YES | `test_database_py_unit.py` | Easy removal |
| `file_io_py.py` | YES (line 318) | NO (uses `io.files.core`) | YES | `test_file_io_py_unit.py` | Easy: factory-only |
| `formid_py.py` | YES (line 368) | NO (uses `scanning.logs.analyzers`) | YES | `test_formid_py_unit.py` | Easy: factory-only |
| `record_py.py` | YES (line 418) | NO (uses `scanning.logs.analyzers`) | YES | `test_record_py_unit.py` | Easy: factory-only |
| `report_py.py` | YES (line 526) | NO (uses `rust.report` package) | YES | `test_report_py_unit.py` | Easy: factory-only |
| `parser_py.py` | YES (line 189, via PythonParserWrapper) | YES (`parser_rust.py` line 84) | YES | `test_parser_py_fallback_unit.py` | Medium: factory + 1 wrapper |
| `mod_detector_py.py` | YES (line 556) | YES (`mod_detector_rust.py` lines 105, 143, 193) | YES | `test_mod_detector_py_unit.py` | Medium: factory + 3 wrapper refs |
| `plugin_py.py` | YES (line 393) | YES (`plugin_rust.py` lines 116, 166, 207, 241, 270) | YES | `test_plugin_py_unit.py` | Hard: factory + 5 wrapper refs |

### Recommended Removal Order

1. `database_py.py` - Zero factory/wrapper refs, simplest
2. `file_io_py.py` - Factory-only, no wrapper refs
3. `formid_py.py` - Factory-only, no wrapper refs
4. `record_py.py` - Factory-only, no wrapper refs
5. `report_py.py` - Factory-only, no wrapper refs
6. `parser_py.py` - Factory + 1 wrapper ref + PythonParserWrapper class
7. `mod_detector_py.py` - Factory + 3 wrapper refs
8. `plugin_py.py` - Factory + 5 wrapper refs (most complex)

### Spec File Cleanup Needed

All 6 spec files have stale `hiddenimports` that reference modules deleted in prior phases:
- `ClassicLib.integration.config` (does not exist)
- `ClassicLib.integration.status` (does not exist)
- `ClassicLib.integration.detector` (does not exist)

Spec files: `CLASSIC.spec`, `CLASSIC-CLI.spec`, `CLASSIC-GUI-OneFile.spec`, `CLASSIC-QML.spec`, `CLASSIC-QML-Dir.spec`, `CLASSIC-Test.spec`

No spec files currently reference `ClassicLib.integration.python` modules (Python tracing resolves them automatically), so no fallback-specific removals are needed in specs.

### Files to Delete (Total)

Production files (8):
- `ClassicLib/integration/python/database_py.py`
- `ClassicLib/integration/python/file_io_py.py`
- `ClassicLib/integration/python/formid_py.py`
- `ClassicLib/integration/python/mod_detector_py.py`
- `ClassicLib/integration/python/parser_py.py`
- `ClassicLib/integration/python/plugin_py.py`
- `ClassicLib/integration/python/record_py.py`
- `ClassicLib/integration/python/report_py.py`

Directory (after all files removed):
- `ClassicLib/integration/python/` (including `__init__.py`)

Test files (7):
- `tests/python_fallback/test_database_py_unit.py`
- `tests/python_fallback/test_file_io_py_unit.py`
- `tests/python_fallback/test_formid_py_unit.py`
- `tests/python_fallback/test_mod_detector_py_unit.py`
- `tests/python_fallback/test_plugin_py_unit.py`
- `tests/python_fallback/test_record_py_unit.py`
- `tests/python/test_report_py_unit.py`

Directory:
- `tests/python_fallback/` (entire directory after all files removed)

### Files to Modify

- `ClassicLib/integration/factory.py` - Remove all fallback import paths, `PythonParserWrapper` class, potentially `_is_rust_disabled()` and `CLASSIC_DISABLE_RUST` support
- `ClassicLib/integration/rust/parser_rust.py` - Remove line 84 fallback import
- `ClassicLib/integration/rust/plugin_rust.py` - Remove 5 fallback import sites
- `ClassicLib/integration/rust/mod_detector_rust.py` - Remove 3 fallback import sites
- `CLASSIC.spec` - Remove stale hiddenimports
- `CLASSIC-CLI.spec` - Remove stale hiddenimports
- `CLASSIC-GUI-OneFile.spec` - Remove stale hiddenimports
- `CLASSIC-QML.spec` - Remove stale hiddenimports
- `CLASSIC-QML-Dir.spec` - Remove stale hiddenimports
- `CLASSIC-Test.spec` - Remove stale hiddenimports
- `CLASSIC_Interface.py` - Add startup validation
- `CLASSIC_ScanLogs.py` - Add startup validation

### CLASSIC_DISABLE_RUST Decision

The `_is_rust_disabled()` function and `CLASSIC_DISABLE_RUST` env var are referenced in:
- `factory.py` (definition + all factory functions)
- `tests/rust_integration/api/test_factory_integration.py`
- `tests/async_tests/test_async_bridge_failure_modes_integration.py`
- `tests/fixtures/yamldata_fixtures.py`
- `ClassicLib/support/setup.py`

After removing all fallbacks, `CLASSIC_DISABLE_RUST=1` would make every factory function fail since there's no fallback to fall to. Options:
1. **Remove it entirely** (cleanest -- Rust is now required)
2. **Keep but make it a no-op with warning** (backward compat for scripts)
3. **Keep for testing but skip startup validation when set** (testing flexibility)

Recommendation: Option 1 (remove entirely). It exists solely for the fallback era. Tests that set it should be updated.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Try Rust, fall back to Python | Rust required, error on missing | Phase 5 | Simpler code, smaller bundle, clear error messages |
| `CLASSIC_DISABLE_RUST` env var | Removed (Rust is required) | Phase 5 | Cannot run without Rust modules |
| `integration/python/` directory | Deleted | Phase 5 | ~2300 lines of fallback code removed |

## Open Questions

1. **What about `ClassicLib.io.files.core.FileIOCore`?**
   - This is the non-fallback Python FileIO used by `file_io_rust.py` as its own fallback (not in the `integration/python/` directory).
   - It is NOT being deleted in this phase. Only the `integration/python/file_io_py.py` wrapper is deleted.
   - The rust wrapper `file_io_rust.py` will still need its own fallback path updated if we want hard errors there too.
   - Recommendation: Leave `file_io_rust.py` internal fallback to `ClassicLib.io.files.core` alone for now -- it's a different Python implementation path, not part of the 8 target files.

2. **What about other rust wrapper internal fallbacks?**
   - `record_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.RecordScanner`
   - `formid_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore`
   - `settings_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.SettingsScanner`
   - `suspect_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.SuspectScanner`
   - `fcx_rust.py` falls back to `ClassicLib.scanning.logs.fcx_mode_handler`
   - `gpu_rust.py` falls back to `ClassicLib.scanning.logs.analyzers.GPUDetector`
   - These are NOT in the `integration/python/` directory and are NOT targets for this phase.
   - Recommendation: Out of scope. These are legitimate "production Python" fallbacks living alongside the code they wrap.

3. **PyInstaller build testing logistics**
   - The context says "PyInstaller build after all removals complete" with smoke test "GUI launches without ModuleNotFoundError"
   - The build requires `pyinstaller` and potentially UPX, which may need to be available in the dev environment
   - Recommendation: Verify pyinstaller is available via `uv run pyinstaller --version` before attempting builds

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all 8 fallback files, factory.py, all rust wrapper modules
- Grep results for all `integration.python` imports across the entire project
- All 6 .spec files examined for hiddenimports

### Confidence Assessment

| Area | Level | Reason |
|---|---|---|
| Dependency map | HIGH | Exhaustive grep of entire codebase |
| Removal order | HIGH | Based on concrete reference counts |
| Spec cleanup | HIGH | Direct inspection of all spec files |
| Startup validation | HIGH | Pattern follows existing `detect_component` API |
| CLASSIC_DISABLE_RUST | MEDIUM | Removal is clean but test impact needs verification |

## Metadata

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (stable -- internal codebase, no external dependencies)
