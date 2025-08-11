# Async-First Implementation Plan for CLASSIC

## Executive Summary

This document outlines a comprehensive plan to refactor the CLASSIC codebase to adopt an async-first approach, eliminating redundant sync/async code duplication and improving maintainability while preserving backwards compatibility.

## Current State Analysis

### Identified Sync/Async Duplications

The codebase currently maintains both synchronous and asynchronous versions of several key components:

#### 1. **ScanGame Module** (`CLASSIC_ScanGame.py` and `ClassicLib/ScanGame/AsyncScanGame.py`)
- **Sync Functions:**
  - `check_log_errors()` (line 99)
  - `scan_mods_unpacked()` (line 277)
  - `scan_mods_archived()` (line 430)
  
- **Async Wrappers:**
  - `check_log_errors_async_wrapper()` (line 66)
  - `scan_mods_unpacked_async_wrapper()` (line 76)
  - `scan_mods_archived_async_wrapper()` (line 86)
  
- **Async Implementations:**
  - `check_log_errors_async()` in AsyncScanGame.py
  - `scan_mods_unpacked_async()` in AsyncScanGame.py
  - `scan_mods_archived_async()` in AsyncScanGame.py

#### 2. **ScanLog Orchestrator** (`ClassicLib/ScanLog/`)
- **Sync Version:** `ScanOrchestrator` class
- **Async Version:** `AsyncScanOrchestrator` class (inherits from ScanOrchestrator)
- **Pattern:** Async version extends sync version with async methods

#### 3. **FormID Analyzer** (`ClassicLib/ScanLog/`)
- **Sync Version:** `FormIDAnalyzer` class with `formid_match()` method
- **Async Version:** `AsyncFormIDAnalyzer` class with `formid_match_async()` method

#### 4. **File I/O Operations** (`ClassicLib/ScanLog/AsyncFileIO.py`)
- **Bridge Functions:** Functions that use `asyncio.run()` to call async versions
  - `crashlogs_reformat_with_async()` → calls `asyncio.run(crashlogs_reformat_async())`
  - `load_crash_logs_optimized()` → calls `asyncio.run(load_crash_logs_async_optimized())`
  - `write_report()` → calls `asyncio.run(write_report_async())`

### Current Architecture Patterns

1. **Feature Flag Pattern**: The ScanGame module uses a feature flag (`Enable Async Scanning`) to toggle between sync/async
2. **Wrapper Pattern**: Sync functions check the feature flag and delegate to async wrappers
3. **Bridge Pattern**: Some modules use `asyncio.run()` to bridge sync callers to async implementations
4. **Inheritance Pattern**: AsyncScanOrchestrator inherits from ScanOrchestrator

## Proposed Async-First Architecture

### Core Principles

1. **Async as Primary**: All I/O-bound operations should be async by default
2. **Sync Adapters**: Provide thin sync wrappers only where absolutely necessary for backwards compatibility
3. **Single Implementation**: Maintain only one implementation (async) to avoid duplication
4. **Progressive Migration**: Allow gradual migration without breaking existing code

### Implementation Strategy

#### Phase 1: Core Infrastructure (Week 1) ✅ COMPLETED

1. **Create Async Base Classes**
   - Establish base async patterns for all major components
   - Define standard async/sync adapter patterns

2. **Unified Async Utilities**
   - Consolidate all async utilities into `ClassicLib/AsyncCore/`
   - Create standard sync-to-async bridges

3. **Error Handling Framework**
   - Implement consistent async error handling
   - Ensure proper cleanup in all async contexts

#### Phase 2: Module Refactoring (Weeks 2-3) ✅ COMPLETED

##### A. ScanGame Module Refactoring

**Current Structure:**
```
CLASSIC_ScanGame.py (sync with wrappers)
└── AsyncScanGame.py (async implementations)
```

**Proposed Structure:**
```
CLASSIC_ScanGame.py (thin sync adapters)
└── ScanGameCore.py (async-first implementations)
```

**Implementation:**
```python
# ScanGameCore.py - Async-first implementation
class ScanGameCore:
    async def check_log_errors(self, folder_path: Path) -> str:
        # Full async implementation
        ...
    
    async def scan_mods_unpacked(self) -> str:
        # Full async implementation
        ...
    
    async def scan_mods_archived(self) -> str:
        # Full async implementation
        ...

# CLASSIC_ScanGame.py - Sync adapters for backwards compatibility
def check_log_errors(folder_path: Path | str) -> str:
    """Sync adapter for async check_log_errors."""
    return asyncio.run(ScanGameCore().check_log_errors(folder_path))

def scan_mods_unpacked() -> str:
    """Sync adapter for async scan_mods_unpacked."""
    return asyncio.run(ScanGameCore().scan_mods_unpacked())

def scan_mods_archived() -> str:
    """Sync adapter for async scan_mods_archived."""
    return asyncio.run(ScanGameCore().scan_mods_archived())
```

##### B. ScanLog Orchestrator Refactoring

**Current Structure:**
```
ScanOrchestrator.py (sync base)
└── AsyncScanOrchestrator.py (async extension)
```

**Proposed Structure:**
```
OrchestratorCore.py (async-first)
├── ScanOrchestrator.py (sync adapter)
└── AsyncScanOrchestrator.py (deprecated, alias to OrchestratorCore)
```

**Implementation:**
```python
# OrchestratorCore.py - Async-first orchestrator
class OrchestratorCore:
    async def process_crash_log(self, crashlog_file: Path) -> tuple:
        # Full async implementation
        ...
    
    async def analyze_formids(self, formids: list[str]) -> dict:
        # Full async implementation
        ...

# ScanOrchestrator.py - Sync adapter
class ScanOrchestrator:
    def __init__(self, *args, **kwargs):
        self._core = OrchestratorCore(*args, **kwargs)
    
    def process_crash_log(self, crashlog_file: Path) -> tuple:
        return asyncio.run(self._core.process_crash_log(crashlog_file))
```

##### C. FormID Analyzer Refactoring

**Current Structure:**
```
FormIDAnalyzer.py (sync)
AsyncFormIDAnalyzer.py (async)
```

**Proposed Structure:**
```
FormIDAnalyzerCore.py (async-first)
├── FormIDAnalyzer.py (sync adapter)
└── AsyncFormIDAnalyzer.py (deprecated, alias)
```

#### Phase 3: File I/O Consolidation (Week 4) ✅ COMPLETED

1. **Eliminate Bridge Functions**
   - Remove functions that just call `asyncio.run()`
   - Replace with direct async calls or sync adapters

2. **Unified File Operations**
   ```python
   # FileIOCore.py - Async-first file operations
   class FileIOCore:
       async def read_crash_log(self, path: Path) -> list[str]:
           async with aiofiles.open(path, 'r') as f:
               return await f.readlines()
       
       async def write_report(self, path: Path, content: str) -> None:
           async with aiofiles.open(path, 'w') as f:
               await f.write(content)
   
   # Sync adapters (if needed)
   def read_crash_log_sync(path: Path) -> list[str]:
       return asyncio.run(FileIOCore().read_crash_log(path))
   ```

#### Phase 4: Testing and Migration (Week 5) ✅ COMPLETED

1. **Update Test Suite**
   - Convert all tests to use async patterns
   - Add compatibility tests for sync adapters
   - Ensure performance benchmarks pass

2. **Migration Utilities**
   - Create migration scripts for existing code
   - Document migration patterns
   - Provide code examples

## Migration Path

### For Existing Code

1. **No Breaking Changes**: All existing sync interfaces will continue to work
2. **Gradual Adoption**: New code should use async-first patterns
3. **Deprecation Warnings**: Add warnings to old patterns (after stabilization)

### For New Features

1. **Async by Default**: All new features must be async-first
2. **Sync Only When Necessary**: Add sync adapters only for specific use cases
3. **Document Patterns**: Clear documentation of async patterns

## Implementation Checklist

### Immediate Actions
- [x] Create `ClassicLib/AsyncCore/` directory structure
- [x] Establish async base patterns and utilities
- [x] Create standard sync adapter template

### Module Refactoring
- [x] Refactor ScanGame module to async-first
- [x] Refactor ScanLog orchestrator to async-first
- [x] Refactor FormIDAnalyzer to async-first
- [x] Consolidate File I/O operations

### Testing & Documentation
- [x] Update test suite for async-first patterns
- [x] Create migration documentation
- [x] Add performance benchmarks
- [x] Update CLAUDE.md with new patterns

### Cleanup
- [x] Remove redundant sync implementations
- [x] Remove unnecessary bridge functions (deprecated with warnings)
- [x] Deprecate old async wrappers
- [x] Clean up feature flags (documentation updated)

## Benefits

1. **Reduced Code Duplication**: ~40% reduction in code duplication
2. **Improved Performance**: Better resource utilization with async I/O
3. **Easier Maintenance**: Single implementation to maintain
4. **Better Testing**: Clearer test patterns without dual implementations
5. **Future-Proof**: Ready for async-first Python ecosystem

## Risks and Mitigations

### Risk 1: Breaking Existing Code
**Mitigation**: Maintain all existing interfaces with sync adapters

### Risk 2: Performance Regression
**Mitigation**: Comprehensive benchmarking before/after migration

### Risk 3: Increased Complexity
**Mitigation**: Clear documentation and consistent patterns

### Risk 4: Async Learning Curve
**Mitigation**: Provide training materials and code examples

## Success Metrics

1. **Code Reduction**: Measure lines of code reduced
2. **Performance**: No regression in benchmarks
3. **Test Coverage**: Maintain or improve test coverage
4. **Bug Reports**: Monitor for migration-related issues
5. **Developer Feedback**: Survey team on new patterns

## Timeline

- **Week 1**: Core infrastructure and patterns
- **Weeks 2-3**: Module refactoring
- **Week 4**: File I/O consolidation
- **Week 5**: Testing and documentation
- **Week 6**: Buffer for issues and refinement

## Conclusion

This async-first approach will significantly improve code maintainability while preserving backwards compatibility. The phased implementation allows for gradual migration with minimal risk to existing functionality.

## Appendix: Code Examples

### Example 1: Async-First Module Pattern

```python
# module_core.py - Async implementation
class ModuleCore:
    async def process_data(self, data: list) -> dict:
        results = await asyncio.gather(*[
            self._process_item(item) for item in data
        ])
        return dict(results)
    
    async def _process_item(self, item):
        # Async processing logic
        await asyncio.sleep(0)  # Yield control
        return item, processed_value

# module.py - Sync adapter
from .module_core import ModuleCore

def process_data(data: list) -> dict:
    """Backwards-compatible sync interface."""
    return asyncio.run(ModuleCore().process_data(data))
```

### Example 2: Unified Error Handling

```python
# async_core/error_handler.py
class AsyncErrorHandler:
    @staticmethod
    async def safe_execute(coro, default=None):
        try:
            return await coro
        except Exception as e:
            logger.error(f"Async execution failed: {e}")
            return default
```

### Example 3: Resource Management

```python
# async_core/resource_manager.py
class AsyncResourceManager:
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def __aenter__(self):
        await self.semaphore.acquire()
        return self
    
    async def __aexit__(self, *args):
        self.semaphore.release()
```