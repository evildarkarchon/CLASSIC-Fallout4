# classic-file-io-py Audit Summary

**Audit Date**: 2025-11-04
**Component**: `classic-file-io-py` (PyLogCollector)
**Status**: ✅ **COMPLIANT** (Python code) / ⚠️ **STUB FILE NEEDS FIXES**

---

## Quick Summary

### Python Code Status: ✅ COMPLIANT

All Python code using `PyLogCollector` correctly treats the methods as **synchronous** (not async).

**No runtime issues detected.**

### Stub File Status: ⚠️ NEEDS FIXES

The `.pyi` stub file has **2 CRITICAL issues** that could mislead developers:

1. **Issue 1**: Methods incorrectly marked as returning `Coroutine` (should be synchronous)
2. **Issue 2**: Missing `pastebin_dir()` method declaration

---

## Files Analyzed

| File | PyLogCollector Usage | Status |
|------|---------------------|---------|
| `ClassicLib/ScanLog/Util.py` | ✅ Uses `collect_all()` correctly (sync) | **COMPLIANT** |
| `ClassicLib/rust/file_io_rust.py` | ❌ Does not use PyLogCollector | N/A |
| `ClassicLib/ScanGame/core/dds_processor.py` | ❌ Does not use PyLogCollector | N/A |
| `ClassicLib/integration/factory.py` | ❌ Does not use PyLogCollector | N/A |

---

## Key Findings

### ✅ CORRECT Usage in ClassicLib/ScanLog/Util.py

```python
# Line 293: Import (note: imports from classic_core.file_io, not classic_file_io)
from classic_core import file_io

# Line 307-311: Create collector
collector = file_io.PyLogCollector(
    base_folder=base_folder_str,
    xse_folder=xse_folder_str,
    custom_folder=custom_folder_str
)

# Line 314: ✅ CORRECT - No await, synchronous call
log_paths: list[str] = collector.collect_all()
```

**Why this is correct**:
- No `await` keyword used
- Expects `list[str]` return type (not `Coroutine`)
- Matches Rust implementation (uses `get_runtime().block_on()` internally)

### ⚠️ Stub File Issues

**File**: `rust/python-bindings/classic-file-io-py/classic_file_io.pyi`

#### Issue 1: Incorrect Async Signatures (Lines 745-801)

```python
# ❌ INCORRECT (current stub):
def collect_all(self) -> Coroutine[Any, Any, list[str]]: ...
def move_from_base_folder(self) -> Coroutine[Any, Any, int]: ...
def copy_from_xse_folder(self) -> Coroutine[Any, Any, int]: ...
def collect_crash_logs(self) -> Coroutine[Any, Any, list[str]]: ...

# ✅ CORRECT (should be):
def collect_all(self) -> list[str]: ...
def move_from_base_folder(self) -> int: ...
def copy_from_xse_folder(self) -> int: ...
def collect_crash_logs(self) -> list[str]: ...
```

**Impact**:
- Developers may try to `await` these methods (based on stub)
- Runtime `TypeError`: "object list can't be used in 'await' expression"
- IDE autocomplete suggests incorrect async usage

#### Issue 2: Missing Method Declaration

```python
# ❌ MISSING from stub:
def pastebin_dir(self) -> str:
    """Get the path to the Pastebin subdirectory."""
```

**Impact**:
- IDE shows "method does not exist" error if called
- Type checkers (mypy, pyright) report errors
- Currently not called in codebase, but should be available

---

## Risk Assessment

| Category | Risk Level | Rationale |
|----------|-----------|-----------|
| **Current Runtime** | ✅ NONE | Python code uses synchronous API correctly |
| **Type Safety** | ⚠️ LOW | Stub errors only affect IDE, not runtime |
| **Future Development** | ⚠️ MEDIUM | Incorrect stub may mislead developers |
| **Maintainability** | ✅ LOW | Single usage point makes changes easy |

---

## Required Fixes

### Priority 1: Fix Stub File (HIGH PRIORITY)

**File**: `rust/python-bindings/classic-file-io-py/classic_file_io.pyi`

**Changes needed**:

```python
class PyLogCollector:
    """Crash log collection and organization.

    NOTE: All methods are SYNCHRONOUS (not async).
    They use Rust's block_on internally for I/O operations.
    """

    # Fix 1: Remove Coroutine return types (lines 745-801)
    def collect_all(self) -> list[str]:
        """Execute full log collection workflow (synchronous)."""

    def move_from_base_folder(self) -> int:
        """Move crash logs from base folder (synchronous)."""

    def copy_from_xse_folder(self) -> int:
        """Copy crash logs from XSE folder (synchronous)."""

    def collect_crash_logs(self) -> list[str]:
        """Collect all crash log file paths (synchronous)."""

    # Fix 2: Add missing method
    def pastebin_dir(self) -> str:
        """Get the path to the Pastebin subdirectory.

        Returns:
            Path to Pastebin directory as a string
        """
```

### Priority 2: Update Import Path (LOW PRIORITY - OPTIONAL)

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

**Note**: Only update if `classic_core` facade is deprecated. Verify before changing.

---

## Action Items Checklist

- [ ] **Fix stub file** (`rust/python-bindings/classic-file-io-py/classic_file_io.pyi`)
  - [ ] Remove `Coroutine` return types from PyLogCollector methods
  - [ ] Add `pastebin_dir()` method declaration
  - [ ] Update class docstring to clarify synchronous nature
- [ ] **Optional: Update imports** in `ClassicLib/ScanLog/Util.py`
  - [ ] Change from `classic_core.file_io` to `classic_file_io`
  - [ ] Verify `classic_core` facade status first
- [ ] **Add integration test** for PyLogCollector usage
  - [ ] Test synchronous API behavior
  - [ ] Verify no coroutine returns

---

## Testing Recommendations

### Test 1: Verify Synchronous Behavior

```python
import pytest
from classic_file_io import PyLogCollector

def test_pylogcollector_methods_are_sync():
    """Verify PyLogCollector methods return values, not coroutines."""
    collector = PyLogCollector(base_folder=".")

    # Should return list directly, not coroutine
    result = collector.collect_all()
    assert isinstance(result, list)
    assert not inspect.iscoroutine(result)
```

### Test 2: Integration Test

```python
import pytest
from pathlib import Path
from ClassicLib.ScanLog.Util import crashlogs_get_files

def test_crashlogs_get_files_no_await_needed():
    """Verify crashlogs_get_files uses synchronous PyLogCollector API."""
    # This will fail at runtime if code incorrectly awaits synchronous methods
    crash_files = crashlogs_get_files()
    assert isinstance(crash_files, list)
    assert all(isinstance(p, Path) for p in crash_files)
```

---

## Related Issues Discovered

### Import Path Discrepancy

**Finding**: Code imports from `classic_core.file_io` instead of `classic_file_io`:

```python
from classic_core import file_io  # Not classic_file_io!
collector = file_io.PyLogCollector(...)
```

**Investigation needed**:
1. Is `classic_core` a legacy facade pattern?
2. Does `classic_core.file_io` re-export `PyLogCollector` from `classic_file_io`?
3. Should imports be updated to use `classic_file_io` directly?

**Recommendation**:
- Check `ClassicLib/rust/orchestrator_api.py` for facade implementation
- If facade is deprecated, migrate imports to direct `classic_file_io`
- Document import path decisions in CLAUDE.md

---

## Conclusion

### Python Code: ✅ Approved for Production

All Python code correctly uses PyLogCollector's synchronous API. No runtime issues.

### Stub File: ⚠️ Requires Immediate Fix

Stub file has critical errors that could mislead future developers. Fix before adding new PyLogCollector usage.

### Overall Assessment: COMPLIANT with CAVEATS

- **Current usage**: Safe and correct
- **Future usage**: Risk of incorrect async usage due to stub errors
- **Action required**: Fix stub file (HIGH PRIORITY)

---

## Sign-off

**Auditor**: Claude (AI Assistant)
**Date**: 2025-11-04
**Review Status**: Complete
**Next Steps**: Fix stub file, then proceed with Phase 1.2 (Rust implementation audit)

---

## Document References

- **Detailed Report**: `classic_file_io_py_audit_report.md`
- **Main Audit Report**: `python_binding_audit_report.md`
- **Stub File**: `rust/python-bindings/classic-file-io-py/classic_file_io.pyi`
- **Production Code**: `ClassicLib/ScanLog/Util.py` (lines 284-317)
