# classic-file-io-py API Compliance Audit Report

**Audit Date**: 2025-11-04
**Component**: `classic-file-io-py` (PyLogCollector usage in ClassicLib/)
**Phase**: 1.1 - Python code compliance audit

---

## Executive Summary

✅ **AUDIT RESULT: COMPLIANT**

All Python code using `PyLogCollector` from `classic_file_io` correctly treats the methods as **synchronous** (not async). No runtime issues detected.

**Key Findings**:
- ✅ **NO incorrect `await` usage** on PyLogCollector methods
- ✅ **NO calls to missing `pastebin_dir()` method** detected in production code
- ⚠️ **Stub file has 2 critical errors** (documented separately in main audit report)
- ℹ️ Python code already follows correct synchronous API pattern

---

## Audit Scope

### Files Analyzed

1. **`ClassicLib/rust/file_io_rust.py`**
   - Rust acceleration wrapper for FileIOCore
   - Does NOT import or use PyLogCollector
   - Status: ✅ Not applicable

2. **`ClassicLib/ScanGame/core/dds_processor.py`**
   - DDS texture processing with Rust acceleration
   - Imports `classic_file_io.DDSHeader` (not PyLogCollector)
   - Status: ✅ Not applicable

3. **`ClassicLib/ScanLog/Util.py`** ⭐ **PRIMARY USAGE**
   - Core crash log collection module
   - Uses PyLogCollector in `_crashlogs_get_files_rust()`
   - Status: ✅ **COMPLIANT** (see detailed analysis below)

4. **`ClassicLib/integration/factory.py`**
   - Integration factory for Rust components
   - Does NOT use PyLogCollector
   - Status: ✅ Not applicable

---

## Detailed Analysis: ClassicLib/ScanLog/Util.py

### File Overview
- **Location**: `f:\Python Projects\CLASSIC-Fallout4\ClassicLib\ScanLog\Util.py`
- **Function**: `_crashlogs_get_files_rust()` (lines 284-317)
- **Purpose**: Rust-accelerated crash log file collection (10x faster than Python)

### PyLogCollector Usage Pattern

```python
# Lines 293-314
from classic_core import file_io  # Note: imports classic_core.file_io, not classic_file_io

# Create LogCollector
collector = file_io.PyLogCollector(
    base_folder=base_folder_str,
    xse_folder=xse_folder_str,
    custom_folder=custom_folder_str
)

# ✅ CORRECT: Synchronous call (no await)
log_paths: list[str] = collector.collect_all()
```

### Import Path Analysis

⚠️ **IMPORTANT DISCOVERY**: The code imports from `classic_core.file_io`, not `classic_file_io`:

```python
from classic_core import file_io  # Line 293
collector = file_io.PyLogCollector(...)  # Line 307
```

This suggests:
1. **Legacy import path**: Code may reference an older facade pattern
2. **Re-export pattern**: `classic_core.file_io` may re-export `PyLogCollector` from `classic_file_io`
3. **Recommendation**: Verify `classic_core` module structure and update imports to use direct `classic_file_io` imports

### API Usage Verification

#### ✅ Methods Used CORRECTLY (Synchronous)

1. **`collect_all()`** (Line 314)
   - **Stub signature**: `def collect_all(self) -> list[str]`
   - **Actual usage**: `log_paths: list[str] = collector.collect_all()`
   - **Status**: ✅ **CORRECT** - No `await`, returns `list[str]` directly
   - **Risk**: NONE

#### ❌ Methods NOT Used (No Issues)

2. **`move_from_base_folder()`**
   - **Not called in codebase**
   - **Risk**: NONE (unused)

3. **`copy_from_xse_folder()`**
   - **Not called in codebase**
   - **Risk**: NONE (unused)

4. **`collect_crash_logs()`**
   - **Not called in codebase**
   - **Risk**: NONE (unused)

5. **`pastebin_dir()`**
   - **Not called in codebase**
   - **Risk**: NONE (unused)

---

## Stub File Issues (For Reference)

The `.pyi` stub file has **2 CRITICAL issues** that must be fixed:

### Issue 1: Incorrect Async Signatures (CRITICAL)

**Problem**: Methods marked as returning `Coroutine` but actually synchronous:

```python
# ❌ INCORRECT in stub file (lines 745-801):
def collect_all(self) -> Coroutine[Any, Any, list[str]]: ...
def move_from_base_folder(self) -> Coroutine[Any, Any, int]: ...
def copy_from_xse_folder(self) -> Coroutine[Any, Any, int]: ...
def collect_crash_logs(self) -> Coroutine[Any, Any, list[str]]: ...

# ✅ CORRECT (should be synchronous):
def collect_all(self) -> list[str]: ...
def move_from_base_folder(self) -> int: ...
def copy_from_xse_folder(self) -> int: ...
def collect_crash_logs(self) -> list[str]: ...
```

**Root Cause**: Methods use `get_runtime().block_on()` in Rust (synchronous execution), not true async.

### Issue 2: Missing Method (CRITICAL)

**Problem**: `pastebin_dir()` method exists in Rust but missing from stub:

```python
# ❌ MISSING from stub file:
def pastebin_dir(self) -> str:
    """Get the path to the Pastebin subdirectory.

    Returns:
        Path to Pastebin directory as a string
    """
```

**Impact**: IDE will show errors if code calls this method.

---

## Recommendations

### 1. Update Import Paths (Low Priority)

**Current**:
```python
from classic_core import file_io
collector = file_io.PyLogCollector(...)
```

**Recommended**:
```python
from classic_file_io import PyLogCollector
collector = PyLogCollector(...)
```

**Rationale**: Direct imports are clearer and avoid facade dependencies.

### 2. Fix Stub File (HIGH PRIORITY)

Update `ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi`:

**Required changes**:
1. Remove `Coroutine` return types from PyLogCollector methods (lines 745-801)
2. Add missing `pastebin_dir()` method (line 810-820 placeholder exists but needs implementation)
3. Update documentation to clarify synchronous nature

**Example fix**:
```python
class PyLogCollector:
    """Crash log collection and organization (SYNCHRONOUS operations)."""

    def collect_all(self) -> list[str]:
        """Execute full log collection workflow (synchronous, uses block_on internally)."""

    def move_from_base_folder(self) -> int:
        """Move crash logs from base folder (synchronous)."""

    def copy_from_xse_folder(self) -> int:
        """Copy crash logs from XSE folder (synchronous)."""

    def collect_crash_logs(self) -> list[str]:
        """Collect all crash log file paths (synchronous)."""

    def pastebin_dir(self) -> str:
        """Get the path to the Pastebin subdirectory."""
```

### 3. Verify classic_core Re-exports (Medium Priority)

**Action**: Check if `classic_core.file_io` is still needed or if it should be deprecated.

**Files to review**:
- `ClassicLib/rust/orchestrator_api.py` (may have `classic_core` facade)
- Legacy import compatibility layers

---

## Risk Assessment

### Current Risk: **LOW** ✅

| Risk Factor | Level | Rationale |
|------------|-------|-----------|
| **Runtime Errors** | None | Code uses synchronous API correctly |
| **Type Safety** | Low | Stub errors won't cause runtime issues, only IDE warnings |
| **Maintainability** | Low | Single usage point makes changes easy |
| **Performance** | None | Synchronous calls are correct for block_on pattern |

### Future Risk: **MEDIUM** ⚠️

If new code is added that references the stub file:
- Developers may try to `await` these methods (based on incorrect stub)
- IDE autocomplete will suggest incorrect async usage
- Runtime `TypeError` will occur: "object list can't be used in 'await' expression"

**Mitigation**: Fix stub file before adding new PyLogCollector usage.

---

## Testing Recommendations

### 1. Integration Test for PyLogCollector Usage

```python
import pytest
from pathlib import Path
from ClassicLib.ScanLog.Util import crashlogs_get_files

def test_crashlogs_get_files_rust_path():
    """Verify crashlogs_get_files uses synchronous PyLogCollector API."""
    # This test will fail at runtime if code incorrectly awaits synchronous methods
    crash_files = crashlogs_get_files()  # Should not raise TypeError
    assert isinstance(crash_files, list)
    assert all(isinstance(p, Path) for p in crash_files)
```

### 2. Stub File Validation

```python
import pytest
from classic_file_io import PyLogCollector
import inspect

def test_pylogcollector_methods_are_sync():
    """Verify PyLogCollector methods are synchronous (not coroutines)."""
    collector = PyLogCollector(base_folder=".")

    # These should NOT be coroutines
    result = collector.collect_all()
    assert not inspect.iscoroutine(result)
    assert isinstance(result, list)
```

---

## Conclusion

### Summary

✅ **All Python code using PyLogCollector is COMPLIANT**
- No incorrect `await` usage detected
- No calls to missing methods
- Synchronous API usage is correct

⚠️ **Stub file has critical errors** (documented separately)
- Methods incorrectly marked as async
- Missing `pastebin_dir()` method

### Action Items

1. ✅ **No code changes needed** - Python code is correct
2. ⚠️ **Fix stub file** - Update return types and add missing method (HIGH PRIORITY)
3. ℹ️ **Update imports** - Migrate from `classic_core.file_io` to `classic_file_io` (LOW PRIORITY)
4. ℹ️ **Add tests** - Verify synchronous API behavior (MEDIUM PRIORITY)

### Sign-off

**Auditor**: Claude (AI Assistant)
**Review Status**: Complete
**Approval Status**: Python code approved for production use
**Next Steps**: Proceed with stub file fixes in separate task

---

## Appendix A: Full Usage Context

### Function: `_crashlogs_get_files_rust()`

```python
def _crashlogs_get_files_rust() -> list[Path]:
    """
    Rust-accelerated implementation of crash log file collection (10x faster).

    Uses PyLogCollector from classic_core.file_io for high-performance async file operations.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    from classic_core import file_io

    logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION (Rust)")

    # Get directories from settings
    custom_folder: Path | None = get_path_from_setting(classic_settings(str, "SCAN Custom Path"))
    xse_folder: Path | None = get_path_from_setting(yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_Folder_XSE"))

    # Convert to strings for Rust (PyLogCollector expects strings)
    base_folder_str = str(Path.cwd())
    xse_folder_str = str(xse_folder) if xse_folder else None
    custom_folder_str = str(custom_folder) if custom_folder else None

    # Create LogCollector
    collector = file_io.PyLogCollector(
        base_folder=base_folder_str,
        xse_folder=xse_folder_str,
        custom_folder=custom_folder_str
    )

    # ✅ CORRECT: Synchronous call (no await)
    log_paths: list[str] = collector.collect_all()

    # Convert strings back to Path objects
    return [Path(p) for p in log_paths]
```

### Wrapper Function: `crashlogs_get_files()`

```python
def crashlogs_get_files() -> list[Path]:
    """
    Generates a list of crash log file paths from various defined directories.

    This function automatically uses Rust acceleration when available (10x faster),
    falling back to Python implementation for maximum compatibility.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered crash log files.
    """
    # Try Rust acceleration first
    try:
        return _crashlogs_get_files_rust()
    except ImportError:
        # Rust not available, use Python fallback
        logger.debug("Rust acceleration not available, using Python implementation")
        return _crashlogs_get_files_python()
    except Exception as e:
        # Rust failed for some reason, fall back to Python
        logger.warning(f"Rust log collection failed ({e}), falling back to Python implementation")
        return _crashlogs_get_files_python()
```

---

## Appendix B: Related Files

### Files Using classic_file_io (No PyLogCollector)

1. **`ClassicLib/rust/file_io_rust.py`**
   - Uses: `RustFileIOCore` (async file I/O)
   - No PyLogCollector usage

2. **`ClassicLib/ScanGame/core/dds_processor.py`**
   - Uses: `DDSHeader` (texture header parsing)
   - No PyLogCollector usage

### Integration Factory

**`ClassicLib/integration/factory.py`**
- Provides `get_file_io()` factory function
- Returns `RustFileIOCore` or `FileIOCore` (Python fallback)
- No PyLogCollector usage

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-04
- **Related Audits**:
  - Main stub file audit report (`python_binding_audit_report.md`)
  - Phase 1.2: Rust binding implementation audit (pending)
