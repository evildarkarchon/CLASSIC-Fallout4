# Tasks: Refactor God Classes

## 1. Rust Wrapper Modules

### 1.1 file_io_rust.py (931 lines)
- [x] 1.1.1 Assessed: File is already well-structured with single `FileIOCore` class
- [x] 1.1.2 Fallback is already delegated to `ClassicLib/FileIO/core.py` (PythonFileIOCore)
- [x] 1.1.3 No changes needed - file follows good patterns already
- [x] 1.1.4 N/A - no structural changes needed
- [x] 1.1.5 Imports verified working

### 1.2 report_rust.py (895 lines → 35 lines re-export wrapper)
- [x] 1.2.1 Extract `RustAcceleratedReportFragment` to `rust/report/fragment.py`
- [x] 1.2.2 Extract `RustAcceleratedReportComposer` to `rust/report/composer.py`
- [x] 1.2.3 Extract `RustAcceleratedReportGenerator` to `rust/report/generator.py`
- [x] 1.2.4 Extract `ParallelReportProcessor` to `rust/report/parallel.py`
- [x] 1.2.5 Create `rust/report/__init__.py` with re-exports
- [x] 1.2.6 Import tests passed: all classes import correctly

### 1.3 RustAcceleration.py (841 lines → package structure)
- [x] 1.3.1 Extract `ComponentMetrics` to `RustAcceleration/metrics.py`
- [x] 1.3.2 Extract `WorkloadCharacteristics` to `RustAcceleration/workload.py`
- [x] 1.3.3 Extract `ComponentType` enum to `RustAcceleration/types.py`
- [x] 1.3.4 Extract `RustAcceleration` class and helper functions to `RustAcceleration/coordinator.py`
- [x] 1.3.5 Updated `RustAcceleration/__init__.py` with re-exports for backward compatibility
- [x] 1.3.6 Deleted original `RustAcceleration.py` (was shadowed by package directory)
- [x] 1.3.7 Import tests passed

## 2. Core Logic Modules

### 2.1 OrchestratorCore.py (872 lines)
- [x] 2.1.1 Assessed: Already well-structured orchestrator with clear method boundaries
- [x] 2.1.2 No extraction needed - methods are tightly coupled orchestration logic
- [x] 2.1.3 Uses composition pattern (composer, analyzers, scanners)
- [x] 2.1.4 Well-documented with Google-style docstrings
- [x] 2.1.5 No changes needed
- [x] 2.1.6 Tests continue to pass

### 2.2 ResourceLoader.py (867 lines)
- [x] 2.2.1 Assessed: Utility class with static methods - appropriate structure
- [x] 2.2.2 Strategy extraction would add complexity without benefit
- [x] 2.2.3 Current organization with well-named methods is maintainable
- [x] 2.2.4 N/A - no changes needed
- [x] 2.2.5 N/A - no changes needed
- [x] 2.2.6 N/A - no changes needed
- [x] 2.2.7 Tests continue to pass

### 2.3 AsyncBridge.py (776 lines → 614 lines)
- [x] 2.3.1 Extract standalone helper functions to `_async_utils/bridge_helpers.py`:
  - `run_async()`, `run_async_with_timeout()`, `context_aware_sync()`
  - `smart_await()`, `create_sync_wrapper()`
- [x] 2.3.2 Keep `AsyncBridge` class with singleton pattern in main file
- [x] 2.3.3 Created `_async_utils/__init__.py` with re-exports (placed under ClassicLib to avoid circular imports)
- [x] 2.3.4 Import tests passed

## 3. GUI Components

### 3.1 ResultsViewerWidgets.py (766 lines → 352 lines)
- [x] 3.1.1 Analyzed: Contains ReportListWidget, MarkdownViewer, ReportMetadataWidget
- [x] 3.1.2 Extract MarkdownViewer to `Interface/ResultsViewer/markdown_viewer.py`
- [x] 3.1.2 Extract ReportMetadataWidget to `Interface/ResultsViewer/metadata_widget.py`
- [x] 3.1.3 Create `Interface/ResultsViewer/__init__.py` with re-exports
- [x] 3.1.4 Updated ResultsViewerWidgets.py with re-exports for backward compatibility
- [x] 3.1.5 Import tests passed

## 4. Validation

- [x] 4.1 Run import validation: All refactored modules import correctly
- [x] 4.2 Run test suite: Tests passing (2209 passed, 73 skipped)
- [x] 4.3 Verify no import errors: `python -c "from ClassicLib.rust.report_rust import *"` passes
- [x] 4.4 No documentation updates needed (re-exports maintain backward compatibility)
- [x] 4.5 RustAcceleration package shadowing issue resolved

## Summary

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| file_io_rust.py | 931 | 931 (no change needed) | 0% |
| report_rust.py | 895 | 35 (re-export wrapper) | 96% |
| RustAcceleration.py | 841 | 54 (__init__.py only) | 94% |
| OrchestratorCore.py | 872 | 872 (no change needed) | 0% |
| ResourceLoader.py | 867 | 867 (no change needed) | 0% |
| AsyncBridge.py | 776 | 614 | 21% |
| ResultsViewerWidgets.py | 766 | 352 | 54% |

**Total lines refactored**: report_rust (-860), RustAcceleration (-787), AsyncBridge (-162), ResultsViewerWidgets (-414)
**New modular files created**: 12 files in organized package structures

## Dependencies

- Tasks 1.x (Rust wrappers) ✅ Completed
- Tasks 2.x (Core logic) ✅ Completed (with assessment-based decisions)
- Task 3.x (GUI) ✅ Completed
- Task 4.x (Validation) ✅ Completed
