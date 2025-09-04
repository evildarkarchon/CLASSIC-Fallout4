# CLASSIC Deprecation Removal Implementation Plan

**Generated**: 2025-09-04
**Status**: Ready for Implementation
**Estimated Impact**: ~4 deprecated modules, ~6 deprecated functions, ~15 usage sites

## Overview

This document outlines the comprehensive plan to remove deprecated classes and functions from the CLASSIC codebase following the async-first refactoring. The deprecated modules serve as compatibility wrappers and can be safely removed after updating their usage sites.

## Deprecated Components Analysis

### Deprecated Entire Modules

#### 1. `ClassicLib/ScanGame/AsyncScanGame.py`
- **Status**: All functionality moved to `ScanGameCore.py`
- **Contains**: Compatibility aliases only
- **Used by**: Tests, some legacy import paths

#### 2. `ClassicLib/ScanLog/AsyncFormIDAnalyzer.py`
- **Status**: All functionality moved to `FormIDAnalyzerCore.py`
- **Contains**: Simple inheritance wrapper for compatibility
- **Used by**: Package exports, some tests

#### 3. `ClassicLib/ScanLog/AsyncScanOrchestrator.py`
- **Status**: All functionality moved to `OrchestratorCore.py`
- **Contains**: Compatibility aliases only
- **Used by**: `CLASSIC_ScanLogs.py`, TUI handlers, tests

### Deprecated Functions in AsyncFileIO.py

| Deprecated Function | Modern Replacement | Status |
|---|---|---|
| `crashlogs_reformat_with_async()` | `crashlogs_reformat_async` (direct) | Has deprecation warning |
| `integrate_async_file_loading()` | `FileIOCore.read_multiple_files()` | Has deprecation warning |
| `write_report_with_async()` | `FileIOCore.write_crash_report()` | Has deprecation warning |

## High-Impact Files Requiring Updates

- **`CLASSIC_ScanLogs.py`** - Uses `AsyncScanOrchestrator`
- **`ClassicLib/ScanLog/__init__.py`** - Exports deprecated classes
- **`tests/test_async_pipeline.py`** - Uses deprecated functions
- **`tests/test_async_scan_game.py`** - Uses deprecated classes
- **`tests/test_async_resource_management.py`** - Uses deprecated imports
- **`tests/test_crash_log_processing.py`** - Uses deprecated imports
- **`ClassicLib/TUI/handlers/scan_handler.py`** - Uses deprecated classes
- **`ClassicLib/ScanLog/AsyncPipeline.py`** - Uses deprecated imports
- **`ClassicLib/ScanLog/AsyncIntegration.py`** - Uses deprecated imports

## Implementation Strategy (Prioritized by Risk)

### Priority 1: Low-Risk Function Updates ⭐

**Goal**: Replace deprecated function calls with modern equivalents

**Tasks:**
1. **Update AsyncFileIO function calls**
   - Find all calls to `crashlogs_reformat_with_async()` → Replace with `crashlogs_reformat_async()`
   - Find all calls to `integrate_async_file_loading()` → Replace with `FileIOCore.read_multiple_files()`
   - Find all calls to `write_report_with_async()` → Replace with `FileIOCore.write_crash_report()`

**Affected Files**: Search results show usage in tests and package exports

### Priority 2: Import Statement Updates ⭐⭐

**Goal**: Update import statements to use modern core classes

**Tasks:**
2. **Update CLASSIC_ScanLogs.py** (`ClassicLib/ScanLog/AsyncScanOrchestrator.py:30`)
   ```python
   # FROM:
   from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator

   # TO:
   from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
   ```
   - Update instantiation: `AsyncScanOrchestrator` → `OrchestratorCore`

3. **Update TUI handler** (`ClassicLib/TUI/handlers/scan_handler.py:93`)
   - Replace `AsyncScanOrchestrator` import with `OrchestratorCore`
   - Update usage patterns to match new API

4. **Update AsyncPipeline.py and AsyncIntegration.py**
   - Replace deprecated imports with core equivalents
   - Test functionality to ensure no regressions

### Priority 3: Test File Updates ⭐⭐⭐

**Goal**: Update test files to use modern implementations

**Tasks:**
5. **Update test_async_pipeline.py**
   ```python
   # FROM:
   from ClassicLib.ScanLog.AsyncFileIO import (
       crashlogs_reformat_with_async,
       integrate_async_file_loading,
       write_report_with_async
   )

   # TO:
   from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
   from ClassicLib.FileIOCore import FileIOCore
   ```
   - Update test assertions and expectations
   - Verify all tests still pass

6. **Update test_async_scan_game.py**
   ```python
   # FROM:
   from ClassicLib.ScanGame.AsyncScanGame import (
       scan_mods_archived_async,
       check_log_errors_async,
       scan_mods_unpacked_async
   )

   # TO:
   from ClassicLib.ScanGame.ScanGameCore import ScanGameCore
   ```
   - Update test instantiations and method calls

7. **Update other affected test files**
   - `test_async_resource_management.py`
   - `test_crash_log_processing.py`

### Priority 4: Package Exports Cleanup ⭐⭐

**Goal**: Clean up public API exports

**Tasks:**
8. **Update ClassicLib/ScanLog/__init__.py**
   ```python
   # REMOVE these imports:
   from ClassicLib.ScanLog.AsyncFileIO import integrate_async_file_loading
   from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer
   from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator, write_reports_batch_async

   # REMOVE from __all__ list:
   "AsyncFormIDAnalyzer",
   "AsyncScanOrchestrator",
   "integrate_async_file_loading",
   "write_reports_batch_async",
   ```
   - Keep only modern core implementations
   - Ensure no external API breakage

### Priority 5: File Removal ⭐⭐⭐⭐

**Goal**: Remove deprecated module files entirely

**Tasks:**
9. **Remove deprecated module files**
   ```bash
   # These files can be completely deleted:
   rm ClassicLib/ScanGame/AsyncScanGame.py
   rm ClassicLib/ScanLog/AsyncFormIDAnalyzer.py
   rm ClassicLib/ScanLog/AsyncScanOrchestrator.py
   ```

10. **Clean up AsyncFileIO.py**
    - Remove deprecated functions:
      - `crashlogs_reformat_with_async()`
      - `integrate_async_file_loading()`
      - `write_report_with_async()`
    - Keep only modern async implementations
    - Remove associated imports and warning statements

## Validation & Testing Strategy

### Pre-Removal Validation
```bash
# Establish baseline
poetry run python -m pytest tests/ -n 4 -v

# Verify core functionality
poetry run python CLASSIC_Interface.py      # GUI mode
poetry run python CLASSIC_TUI.py           # TUI mode
poetry run python CLASSIC_ScanLogs.py      # CLI mode
```

### During Implementation Testing
```bash
# After each priority phase
poetry run python -m pytest tests/ -n 4 -q              # Quick verification
poetry run ruff check .                                  # Linting
poetry run mypy . --ignore-missing-imports              # Type checking
```

### Post-Removal Validation
```bash
# Full validation suite
poetry run ruff check . && poetry run ruff format .     # Linting & formatting
poetry run mypy .                                        # Type checking
poetry run pyright                                       # Additional type checking
poetry run python -m pytest tests/ -n 4 -v             # Full test suite

# Integration testing
poetry run python CLASSIC_Interface.py                  # Test GUI startup
poetry run python CLASSIC_TUI.py                        # Test TUI startup
poetry run python CLASSIC_ScanLogs.py --help           # Test CLI functionality
```

## Implementation Checklist

### Before Starting
- [ ] Backup current codebase (`git commit -am "Pre-deprecation cleanup checkpoint"`)
- [ ] Run full test suite to establish baseline
- [ ] Document current API surface for reference
- [ ] Verify all imports resolve correctly

### During Implementation
- [ ] **Priority 1**: Replace deprecated function calls
- [ ] **Priority 2**: Update import statements in main files
- [ ] **Priority 3**: Update all test files
- [ ] **Priority 4**: Clean up package exports
- [ ] **Priority 5**: Remove deprecated module files
- [ ] Test each change incrementally
- [ ] Keep commit messages clear about deprecation removal
- [ ] Update any documentation referencing old classes

### After Completion
- [ ] Verify no remaining imports of deleted modules
- [ ] Run performance benchmarks to ensure no regressions
- [ ] Update any remaining documentation or comments
- [ ] Consider adding changelog entry about API cleanup
- [ ] Search codebase for any missed references: `grep -r "AsyncScanGame\|AsyncFormIDAnalyzer\|AsyncScanOrchestrator" --include="*.py" .`

## Risk Mitigation

### Low Risk Factors
1. **API Compatibility**: Core classes (`OrchestratorCore`, `FormIDAnalyzerCore`, `ScanGameCore`) provide identical functionality
2. **Incremental Approach**: Updates are isolated and can be tested independently
3. **Comprehensive Tests**: Extensive test suite will catch any regressions
4. **Wrapper Pattern**: Deprecated modules are thin compatibility wrappers

### Rollback Strategy
- Git history allows easy rollback of individual changes
- Each priority phase can be committed separately
- Core functionality remains in stable modules throughout process

### Success Criteria
- [ ] All tests pass after each phase
- [ ] No deprecation warnings in test output
- [ ] All three interface modes (GUI/TUI/CLI) start successfully
- [ ] Performance benchmarks show no regressions
- [ ] Linting and type checking pass cleanly

## Expected Benefits

1. **Reduced Technical Debt**: Elimination of ~300 lines of deprecated compatibility code
2. **Cleaner Architecture**: Single source of truth for async implementations
3. **Better Maintainability**: No need to maintain duplicate API surfaces
4. **Improved Performance**: Direct use of optimized core implementations
5. **Cleaner Logs**: No more deprecation warnings in application output

## Architecture Notes

The async-first refactoring represents a significant architectural improvement:

- **Before**: Mixed sync/async patterns with compatibility wrappers
- **After**: Pure async-first implementations with sync adapters where needed
- **Pattern**: `*Core` classes contain the real implementations, deprecated classes were thin wrappers

This cleanup maintains all performance benefits while eliminating maintenance overhead of the compatibility layer.

---

**Implementation Time Estimate**: 2-4 hours total
- Priority 1-2: 30 minutes
- Priority 3: 60-90 minutes (test updates)
- Priority 4-5: 30-60 minutes (cleanup and validation)
