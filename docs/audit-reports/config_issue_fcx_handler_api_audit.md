# ConfigIssue & FcxModeHandler API Compliance Audit Report

**Phase 1.3 - Critical API Compliance Check**
**Date**: 2025-11-04
**Auditor**: Claude Code (Sonnet 4.5)
**Scope**: Python code compliance with Rust binding APIs for ConfigIssue and FcxModeHandler

---

## Executive Summary

### 🎯 Critical Finding: Python Wrapper Has Wrong Method Name

**SEVERITY: HIGH** - Runtime error will occur if Rust backend is available.

The Python wrapper `ClassicLib/rust/fcx_rust.py` calls **the wrong method name** on the Rust FcxModeHandler:

- **Line 110**: `self._handler.get_messages()` ❌ WRONG
- **Should be**: `self._handler.get_fcx_messages()` ✅ CORRECT

**Impact**: If Rust acceleration is available (`RUST_AVAILABLE = True`), calling `RustAcceleratedFcxModeHandler.get_fcx_messages()` will raise `AttributeError` because the wrapper tries to call `get_messages()` on a Rust object that only has `get_fcx_messages()`.

**Good News**: The .pyi stub file is **CORRECT** for both ConfigIssue and FcxModeHandler (my initial task context was outdated).

---

## Detailed Findings

### 1. ConfigIssue Class

#### 1.1 Import Analysis

**Python Implementation**: `ClassicLib/ScanGame/models/fcx_issue.py`
- Type: Python dataclass
- No Rust import dependency
- Export pattern: Re-exported from `ClassicLib.ScanGame.models.__init__.py`

**Rust Implementation**: `rust/python-bindings/classic-scanlog-py/src/fcx_handler.rs` (lines 7-98)
- Type: PyO3 PyClass wrapper around `classic_scanlog_core::ConfigIssue`
- Exported from `classic_scanlog` module

**Import Patterns Found**:
```python
# Pattern 1: Python implementation (MOST COMMON)
from ClassicLib.ScanGame.models.fcx_issue import ConfigIssue, ConfigIssueSeverity

# Pattern 2: Via models __init__ (COMMON)
from ClassicLib.ScanGame.models import ConfigIssue, ConfigIssueSeverity

# Pattern 3: Direct Rust import (NOT FOUND IN PRODUCTION CODE)
from classic_scanlog import ConfigIssue  # ❌ No production code uses this
```

**Files Using ConfigIssue**:
1. `ClassicLib/ScanGame/Config.py` - Lines 26, 468, 498, 513
2. `ClassicLib/ScanGame/CheckCrashgen.py` - Lines 16, 280, 291, 295, 306, 315, 321, 337, 374, 383, 405, 414
3. `ClassicLib/ScanGame/GameIntegrityOrchestrator.py` - Lines 19, 43, 53, 79, 242, 330, 339, 380, 402, 404
4. `ClassicLib/ScanGame/ScanModInis.py` - Lines 182, 198, 230, 236
5. `ClassicLib/ScanGame/core/ini_fallback.py` - Lines 11, 60, 64, 70

#### 1.2 ConfigIssue API Compliance

**Rust API** (from `fcx_handler.rs`):
```python
class ConfigIssue:
    def __init__(
        self,
        file_path: str,
        section: str | None,
        setting: str,
        current_value: str,
        recommended_value: str,
        description: str,
        severity: str = "warning"
    ) -> None: ...

    @property
    def file_path(self) -> str: ...
    @property
    def section(self) -> str | None: ...
    @property
    def setting(self) -> str: ...
    @property
    def current_value(self) -> str: ...
    @property
    def recommended_value(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def severity(self) -> str: ...

    def format_report(self) -> str: ...
    def __repr__(self) -> str: ...
```

**Python API** (from `fcx_issue.py`):
```python
@dataclass
class ConfigIssue:
    file_path: Path  # ⚠️ Different type (Path vs str)
    section: str | None
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: ConfigIssueSeverity = "warning"

    def __post_init__(self) -> None: ...  # ✅ Converts str to Path
    def format_report(self) -> str: ...
```

**API Compatibility Assessment**: ✅ **COMPATIBLE**

- Rust uses `str` for file_path, Python uses `Path` (converted in `__post_init__`)
- All properties match
- Both have `format_report()` method with same signature
- Python dataclass auto-generates `__repr__()` (compatible with Rust)

#### 1.3 ConfigIssue Usage Patterns

**Pattern 1: Direct Instantiation** (COMMON)
```python
# CheckCrashgen.py:295
issue = ConfigIssue(
    file_path=config_file,          # Path object
    section=setting["section"],     # str
    setting=setting["key"],         # str
    current_value=str(current_value),
    recommended_value=str(setting["desired_value"]),
    description=description,
    severity="warning",
)
```
✅ **Compatible** - Python `__post_init__` converts Path to Path, Rust accepts str

**Pattern 2: Property Access**
```python
# FCXModeHandler.py:193
lines.append(issue.format_report())
```
✅ **Compatible** - Both have `format_report()` method

**Pattern 3: Return Type**
```python
# CheckCrashgen.py:280
def _detect_toml_issue(...) -> ConfigIssue | None:
    return ConfigIssue(...)
```
✅ **Compatible** - Same return type signature

**Risk Assessment**: ✅ **LOW RISK**
- No direct imports from `classic_scanlog.ConfigIssue`
- All production code uses Python implementation
- APIs are structurally compatible
- Type difference (Path vs str) is handled by Python `__post_init__`

---

### 2. FcxModeHandler Class

#### 2.1 Import Analysis

**Python Implementation**: `ClassicLib/ScanLog/FCXModeHandler.py`
- Class: `FCXModeHandlerFragments`
- Type: Pure Python with class-level state management
- No Rust dependency

**Rust Wrapper**: `ClassicLib/rust/fcx_rust.py`
- Class: `RustAcceleratedFcxModeHandler` (alias `FCXModeHandler`, `FcxModeHandler`)
- Type: Wrapper that selects Rust or Python backend
- Import: `from classic_scanlog import FcxModeHandler as RustFcxModeHandlerType`

**Import Patterns Found**:
```python
# Pattern 1: Via Rust wrapper (PRODUCTION)
from ClassicLib.rust.fcx_rust import FCXModeHandler

# Pattern 2: Direct Python import (TESTS)
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
```

#### 2.2 FcxModeHandler API Comparison

**Rust API** (from `fcx_handler.rs` lines 107-261):
```python
class FcxModeHandler:
    def __init__(self, enabled: bool = False) -> None: ...
    def check_fcx_mode(self) -> None: ...
    def set_main_files_result(self, result: str) -> None: ...
    def set_game_files_result(self, result: str) -> None: ...
    def get_fcx_messages(self) -> list[str]: ...          # ✅ CORRECT NAME
    def get_fcx_status_message(self) -> str: ...
    def has_results(self) -> bool: ...

    @property
    def fcx_mode(self) -> bool: ...
    @fcx_mode.setter
    def fcx_mode(self, value: bool) -> None: ...

    def add_issue(self, issue: ConfigIssue) -> None: ...
    def set_detected_issues(self, issues: list[ConfigIssue]) -> None: ...
    def get_detected_issues(self) -> list[ConfigIssue]: ...
    def reset(self) -> None: ...
```

**Python API** (from `FCXModeHandler.py`):
```python
class FCXModeHandlerFragments:
    def __init__(self, fcx_mode: bool | None) -> None: ...
    def check_fcx_mode(self) -> None: ...
    async def check_fcx_mode_async(self) -> None: ...
    def get_fcx_messages(self) -> ReportFragment: ...     # ✅ Returns ReportFragment

    @classmethod
    def reset_fcx_checks(cls) -> None: ...

    # Class-level attributes (not in Rust)
    _fcx_checks_run: bool
    _main_files_result: str
    _game_files_result: str
    _detected_issues: list
```

**Wrapper API** (from `fcx_rust.py`):
```python
class RustAcceleratedFcxModeHandler:
    def __init__(self, fcx_mode: bool | None) -> None: ...
    def check_fcx_mode(self) -> None: ...
    def get_fcx_messages(self) -> ReportFragment: ...

    @classmethod
    def reset_fcx_checks(cls) -> None: ...
```

#### 2.3 CRITICAL API BUG IN WRAPPER

**File**: `ClassicLib/rust/fcx_rust.py`
**Location**: Line 110
**Severity**: 🔴 **HIGH - RUNTIME ERROR**

```python
# WRONG - Line 110
lines: list[str] = self._handler.get_messages()  # ❌ AttributeError

# CORRECT - Should be
lines: list[str] = self._handler.get_fcx_messages()  # ✅
```

**Root Cause**: The wrapper assumes Rust has a method named `get_messages()`, but Rust actually exports `get_fcx_messages()`.

**Impact**:
- When Rust is available: `AttributeError: 'FcxModeHandler' object has no attribute 'get_messages'`
- When Rust is unavailable: No error (falls back to Python)

**Evidence**:
1. Rust source (`fcx_handler.rs:209-211`):
   ```rust
   pub fn get_fcx_messages(&self) -> Vec<String> {
       self.inner.get_fcx_messages().to_list()
   }
   ```

2. .pyi stub (`classic_scanlog.pyi:1555-1560`):
   ```python
   def get_fcx_messages(self) -> list[str]:
       """Generate FCX mode messages."""
   ```

3. Wrapper code (`fcx_rust.py:108-111`):
   ```python
   if self._use_rust:
       # Rust has method named get_messages() and returns list[str]  # ❌ COMMENT IS WRONG
       # Need to convert to ReportFragment for API compatibility
       lines: list[str] = self._handler.get_messages()  # ❌ WRONG METHOD NAME
   ```

**Affected Code Paths**:
- `ClassicLib/ScanLog/OrchestratorCore.py:536` - Calls `self.fcx_handler.get_fcx_messages()`
- All Rust integration tests using `handler.get_fcx_messages()`
- Production usage when Rust is enabled

#### 2.4 Method Name Audit

**Method: `get_messages()` vs `get_fcx_messages()`**

**Search Results**:
```
get_messages() calls found: 1
  - fcx_rust.py:110 (IN WRAPPER - BUG)

get_fcx_messages() calls found: 34
  - OrchestratorCore.py:536 (PRODUCTION)
  - FCXModeHandler.py:161 (PYTHON IMPL)
  - 32 test files
```

**Conclusion**: All production code correctly calls `get_fcx_messages()`. Only the wrapper has the bug.

**Method: `is_enabled()` vs Property `fcx_mode`**

**Search Results**:
```
.is_enabled() calls found: 0 (NONE IN PRODUCTION)
```

**Conclusion**: No code calls `is_enabled()` method. All code should use `.fcx_mode` property.

#### 2.5 Missing Methods Usage Check

**Methods Checked**:
- `set_main_files_result()` - ❌ Only used in Rust internal code
- `set_game_files_result()` - ❌ Only used in Rust internal code
- `get_fcx_status_message()` - ❌ Only used in Rust internal code
- `has_results()` - ❌ Only used in Rust internal code
- `add_issue()` - ❌ Only used in Rust internal code
- `set_detected_issues()` - ❌ Only used in Rust internal code
- `get_detected_issues()` - ❌ Only used in Rust internal code (1 doc reference)
- `reset()` - ❌ Only used in Rust internal code

**Conclusion**: Python code does **NOT** call any of these methods. They are only used internally by the Rust implementation's `check_fcx_mode()` method.

**Risk Assessment**: ✅ **LOW RISK** for missing methods
- No production Python code calls these methods
- Methods exist in Rust for internal use only
- .pyi stub correctly documents all methods

---

## Risk Assessment Summary

### 🔴 CRITICAL RISK

**Issue**: Wrapper calls wrong method name `get_messages()` instead of `get_fcx_messages()`
**Location**: `ClassicLib/rust/fcx_rust.py:110`
**Impact**: Runtime error (`AttributeError`) when Rust is available
**Likelihood**: HIGH - Error occurs on every call when Rust acceleration is enabled
**Affected Paths**: Production code path in `OrchestratorCore.py`

### ✅ LOW RISKS

1. **ConfigIssue API**: Fully compatible, no imports from Rust in production
2. **Missing FcxModeHandler methods**: Not called by Python code
3. **Type differences**: Handled by Python `__post_init__` conversion

---

## Stub File Status

### .pyi File Assessment: ✅ **CORRECT**

**File**: `rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi`

**ConfigIssue** (lines 1457-1523): ✅ Complete and accurate
- Constructor matches Rust (lines 1464-1484)
- All 7 properties documented (lines 1486-1512)
- `format_report()` method documented (lines 1514-1519)
- `__repr__()` documented (line 1521)

**FcxModeHandler** (lines 1525-1607): ✅ Complete and accurate
- Constructor matches Rust (lines 1532-1537)
- `check_fcx_mode()` documented (lines 1539-1547)
- `set_main_files_result()` documented (line 1549-1550)
- `set_game_files_result()` documented (line 1552-1553)
- ✅ **`get_fcx_messages()` documented correctly** (lines 1555-1560)
- `get_fcx_status_message()` documented (lines 1562-1567)
- `has_results()` documented (lines 1569-1574)
- Property `fcx_mode` with getter/setter documented (lines 1576-1582)
- `add_issue()` documented (lines 1584-1589)
- `set_detected_issues()` documented (lines 1591-1596)
- `get_detected_issues()` documented (lines 1598-1603)
- `reset()` documented (lines 1605-1606)

**Conclusion**: The .pyi stub file is **fully up-to-date** and matches the Rust implementation perfectly. My initial task context was based on an outdated report.

---

## Recommendations

### 1. IMMEDIATE FIX REQUIRED (CRITICAL)

**File**: `ClassicLib/rust/fcx_rust.py`
**Line**: 110
**Current**:
```python
lines: list[str] = self._handler.get_messages()  # type: ignore[attr-defined]
```

**Fix To**:
```python
lines: list[str] = self._handler.get_fcx_messages()  # type: ignore[attr-defined]
```

**Also Fix Comment** (Line 108):
```python
# Current comment (WRONG):
# Rust has method named get_messages() and returns list[str]

# Corrected comment:
# Rust has method named get_fcx_messages() and returns list[str]
```

### 2. VERIFY FIX WITH TESTS

Run these tests to verify the fix:
```bash
# Test Rust acceleration
uv run pytest tests/rust_integration/test_fcx_handler_parity.py -v

# Test wrapper integration
uv run pytest tests/scanlog/test_fcx_handler.py -v

# Test production usage
uv run pytest tests/scanlog/test_orchestrator_core.py -v
```

### 3. NO STUB FILE UPDATES NEEDED

The .pyi stub file is already correct and complete. No changes required.

### 4. NO OTHER CODE CHANGES NEEDED

All other Python code correctly uses:
- Python ConfigIssue implementation (no Rust imports)
- Correct method names (`get_fcx_messages()`)
- Wrapper API that matches both backends

---

## Audit Conclusion

**Overall Assessment**: ✅ **ONE CRITICAL BUG FOUND**

This audit found exactly **ONE critical runtime error**:
- Wrapper calls wrong method name `get_messages()` instead of `get_fcx_messages()`

**Good News**:
1. .pyi stub file is **fully correct and up-to-date**
2. ConfigIssue API is fully compatible across Python/Rust
3. Production code uses correct method names everywhere
4. No missing method calls found in production
5. Type differences are properly handled

**Bad News**:
1. One-line bug will cause `AttributeError` when Rust is enabled
2. Error affects production code path in `OrchestratorCore.py`

**Fix Effort**: ⚡ **TRIVIAL** - Change one method name on line 110

**Post-Fix Confidence**: 🎯 **HIGH** - Comprehensive test coverage exists to verify fix

---

## Files Audited

### Production Files (5)
1. ✅ `ClassicLib/ScanLog/FCXModeHandler.py` - Python implementation
2. 🔴 `ClassicLib/rust/fcx_rust.py` - Rust wrapper (BUG FOUND)
3. ✅ `ClassicLib/ScanGame/Config.py` - ConfigIssue usage
4. ✅ `ClassicLib/ScanGame/CheckCrashgen.py` - ConfigIssue usage
5. ✅ `ClassicLib/ScanGame/models/fcx_issue.py` - ConfigIssue model

### Rust Sources (2)
1. ✅ `rust/python-bindings/classic-scanlog-py/src/fcx_handler.rs` - Rust implementation
2. ✅ `rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi` - Type stub (CORRECT)

### Supporting Files
- ✅ `ClassicLib/ScanLog/OrchestratorCore.py` - Production usage
- ✅ Multiple test files verified for correct usage patterns

---

**Audit Complete**: 2025-11-04
**Next Action**: Apply one-line fix to `fcx_rust.py:110`
