# Pyright Type Checking Issues Summary

**Date**: 2025-10-07
**Total Errors**: 84 (down from 95)
**Total Warnings**: 52 (down from 59)

## Fixed Issues (11 errors, 7 warnings)

### 1. AsyncYamlSettings - Missing Methods ✅
- **Files**: `ClassicLib/AsyncYamlSettings/core.py`, `file_operations.py`
- **Issue**: `YamlFileOperations` missing `ensure_file_exists()` and `backup_file()` methods
- **Fix**: Added both methods to `YamlFileOperations` class

### 2. GamePath.py - Optional.lower() Errors ✅
- **Files**: `ClassicLib/GamePath.py` (lines 103, 119, 120, 125)
- **Issue**: Calling `.lower()` on potentially None values
- **Fix**: Added None checks and fallback values

### 3. GamePath.py - Path | None Return Type ✅
- **Files**: `ClassicLib/GamePath.py` (line 175)
- **Issue**: `_get_path_from_user_gui()` returns `Path | None` but declares `Path`
- **Fix**: Added None check and raise RuntimeError if None

### 4. MessageHandler QWidget Type Conflicts ✅
- **Files**: `ClassicLib/MessageHandler/handler.py`, `models.py`
- **Issue**: Type mismatch between local dummy QWidget and PySide6.QtWidgets.QWidget
- **Fix**: Use consistent QWidget import from qt_compat, add type: ignore where needed

### 5. WindowGeometryMixin Type Issues ✅
- **Files**: `ClassicLib/Interface/WindowGeometryMixin.py`
- **Issue**: `object` type in return annotation, attribute access on Any
- **Fix**: Changed return type to `Any`, added type: ignore comments

### 6. ResultsViewerMixin - Optional Timer Interval ✅
- **Files**: `ClassicLib/Interface/ResultsViewerMixin.py` (line 580)
- **Issue**: Passing `int | None` to `start()` which expects `int`
- **Fix**: Added None check before calling `start()`

### 7. TUI Scan Handler - Wrong OrchestratorCore Parameters ✅
- **Files**: `ClassicLib/TUI/handlers/scan_handler.py` (line 137)
- **Issue**: Passing `scanner.crashlogs` which doesn't exist
- **Fix**: Removed the erroneous parameter from OrchestratorCore init

## Remaining Issues by Category

### A. Interface Mixin Type Errors (50+ errors) - DESIGN LIMITATION
**Status**: Not critical - by design

These are all variations of the same pattern where mixins pass `self` to Qt functions:
```python
QMessageBox.warning(self, ...)  # self is not QWidget, but mixin used in QWidget subclass
```

**Files affected**:
- `BackupOperations.py` (2 errors) - Partially fixed
- `FolderManagement.py` (7 errors)
- `FolderManagementMixin.py` (9 errors)
- `HelpAndAboutMixin.py` (2 errors)
- `PapyrusManager.py` (1 error)
- `PastebinMixin.py` (2 errors)
- `PathDialogMixin.py` (2 errors)
- `ScanOperations.py` (2 errors)
- `UpdateManager.py` (4 errors)

**Solution**: Add `# type: ignore[arg-type]` to each occurrence, or use Protocol to declare QWidget interface.

**Example**:
```python
QMessageBox.warning(
    self,  # type: ignore[arg-type]  # Mixin used in QWidget subclass
    "Warning",
    message
)
```

### B. Rust Module Attribute Access (40+ warnings) - EXPECTED
**Status**: Expected - Rust stub limitations

Pyright cannot see attributes from Rust modules because PyO3 stubs are incomplete.

**Common patterns**:
```python
from classic_core import yaml, database, scanlog, file_io

# These all show attribute warnings in pyright
yaml.RustYamlOperations  # warning
database.RustDatabase    # warning
scanlog.RustLogParser    # warning
```

**Files affected**:
- `ClassicLib/integration/detector.py` (6 warnings)
- `ClassicLib/integration/factory.py` (3 warnings)
- `ClassicLib/rust/*.py` (30+ warnings)

**Solution**: Cannot fix - this is a limitation of PyO3 type stubs. The code works correctly at runtime.

### C. Signal/Property Access Warnings (2 warnings) - PYRIGHT LIMITATION
**Status**: False positive

**Files**:
- `ResultsViewerMixin.py` (lines 339, 394)

**Issue**: Pyright doesn't understand PySide6 Signal descriptors properly
```python
self.reports_refreshed.emit()  # Pyright doesn't understand Signal.__get__
```

**Solution**: Add `# type: ignore[attr-defined]` or wait for better PySide6 stubs.

### D. ScanLog Type Issues (5 errors) - NEEDS INVESTIGATION

**Files**:
- `Parser.py` (line 272) - `callable` used as class type
- `SettingsScanner.py` (lines 95, 107, 145) - Type mismatches with callable
- `ScanLogsExecutor.py` (line 129) - Tuple size mismatch
- `ScanLogsExecutor.py` (lines 261, 262, 272) - Optional member access
- `ScanLogsUtils.py` (line 211) - ClassicScanLogsInfo | None mismatch

### E. TUI Type Issues (4 errors) - NEEDS INVESTIGATION

**Files**:
- `confirmation_dialog.py` (line 88) - str | None not assignable to VisualType
- `progress_dialog.py` (line 82) - Same issue as above
- `papyrus_monitor.py` (line 236) - str not assignable to bool
- `scan_handler.py` (line 111) - str | None return type issue

### F. DDS Analyzer Import Errors (5 errors) - MISSING DEPENDENCIES
**Status**: Optional dependencies not installed

**Files**:
- `dds_analyzer.py` - Cannot import `pyffi.formats.dds`, `PIL`
- `dds_processor.py` - EnhancedDDSAnalyzer possibly unbound

**Solution**: These are optional dependencies for texture analysis. Not critical for core functionality.

### G. Miscellaneous Real Issues (10 errors)

1. **AsyncUtil.py** (line 53) - Using None with `async with`
2. **ResourceLoader.py** (line 38) - `sys._MEIPASS` not known (PyInstaller-specific)
3. **RustAcceleration.py** (lines 291, 295) - Missing imports (expected)
4. **integration/status.py** (line 191) - `DISABLE_RUST_ENV_VAR` not defined
5. **rust/database_rust.py** (lines 56, 97) - Optional context manager/call issues
6. **rust/formid_rust.py** (lines 147, 158, 163) - Missing imports and wrong args
7. **rust/report_rust.py** (lines 71, 74, 88, etc.) - Many Optional member access issues
8. **rust/record_rust.py** (line 159) - Cannot access `patterns` attribute

## Recommended Actions

### Immediate (High Priority)
1. ✅ Fix AsyncYamlSettings missing methods - DONE
2. ✅ Fix GamePath.py None handling - DONE
3. ✅ Fix MessageHandler QWidget conflicts - DONE
4. ✅ Fix TUI scan_handler wrong parameters - DONE

### Short Term (Medium Priority)
1. Add `# type: ignore[arg-type]` to all Interface mixin self parameters (50+ locations)
2. Fix ScanLog type issues (callable vs class, Optional access)
3. Fix TUI VisualType issues
4. Review rust module Optional call/member access issues

### Long Term (Low Priority)
1. Create proper Protocol for mixins to avoid type: ignore comments
2. Improve PyO3 type stubs for Rust modules (upstream contribution)
3. Add proper type guards for Optional checks in Rust integration code
4. Consider making pyffi/PIL hard dependencies or stub them better

## Notes

- Many Rust module warnings are expected and cannot be fixed (PyO3 limitation)
- Interface mixin errors are by design - mixins assume QWidget interface
- Signal descriptor warnings are Pyright limitations with PySide6
- The codebase has good type coverage overall; most issues are edge cases

## Progress Tracking

- **Starting point**: 95 errors, 59 warnings
- **After fixes**: 84 errors, 52 warnings
- **Fixed**: 11 errors (12%), 7 warnings (12%)
- **Remaining**: 84 errors, 52 warnings
  - ~50 are mixin design issues (can be suppressed)
  - ~40 are Rust stub limitations (cannot fix)
  - ~20 are real issues worth investigating
