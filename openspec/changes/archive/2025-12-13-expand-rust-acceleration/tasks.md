# Tasks: Expand Rust Acceleration Usage

## 1. RecordScanner Factory Integration (High Priority)

- [x] 1.1 Update `OrchestratorCore.__init__` to use `get_record_scanner(yamldata)` instead of `RecordScanner(yamldata)`
- [x] 1.2 Add fallback handling if `get_record_scanner()` returns None (handled by factory pattern)
- [x] 1.3 Add test `test_orchestrator_uses_rust_record_scanner` in `tests/rust_integration/test_factory_integration.py`
- [x] 1.4 Verify existing `test_record_scanner_parity.py` tests pass

## 2. File I/O Factory Consistency (High Priority)

- [x] 2.1 Audit codebase for direct `FileIOCore()` instantiations (not via `get_file_io()`)
- [x] 2.2 Update any direct instantiations to use `get_file_io()` factory
  - Updated: `FileGeneration.py`, `YamlSettings/async_/file_operations.py`
  - Updated: `ScanGame/GameIntegrityOrchestrator.py`, `ScanGame/GameFilesManager.py`
- [x] 2.3 Add test verifying singleton behavior across codebase (`test_factory_integration.py`)
- [x] 2.4 Document factory pattern in code comments (added inline comments)

## 3. Path Operations Integration (Medium Priority)

- [x] 3.1 Verified existing inline Python fallbacks work correctly
- [x] 3.2 Note: `path_py.py` not created - existing inline fallbacks in GamePath.py, DocsPath.py, PathValidator.py are sufficient
- [x] 3.3 Verified `get_path_operations()` integration in game path detection code
- [x] 3.4 Path operations parity verified through existing inline fallback tests

**Decision**: Per design.md Decision 2, existing inline Python fallbacks are sufficient. No refactoring needed.

## 4. Phase 4 Utility Integration (Medium Priority)

- [x] 4.1-4.5 Investigated Phase 4 utilities (constants, version_utils, resource_mgmt, xse_utils, web_utils)

**Decision**: Per design.md Decision 3, Phase 4 utilities are "cold code paths" (startup/infrequent operations). Integration skipped as performance gains would be minimal. Future profiling can identify if any become hot paths.

## 5. Integration Testing (Required)

- [x] 5.1 Add performance test for RecordScanner Rust usage (part of `test_factory_integration.py`)
- [x] 5.2 Add integration test verifying factory fallback behavior (`test_factory_integration.py`)
- [x] 5.3 Verified `test_component_integration.py` works with new usage patterns (23 tests pass)
- [x] 5.4 Run full test suite to verify no regressions

## 6. Documentation & Validation

- [x] 6.1 `print_rust_status()` already comprehensive - no changes needed
- [x] 6.2 All implementation tasks complete, ready for openspec validation
- [x] 6.3 Test suite verified: 35 factory/record scanner tests pass, 23 component integration tests pass

## Dependencies

- Tasks 1.x can run in parallel with Tasks 2.x ✓
- Tasks 3.x and 4.x depend on understanding the existing factory patterns (can start after 1.1) ✓
- Tasks 5.x depend on completion of implementation tasks (1-4) ✓
- Task 6.x is final validation

## Summary of Changes

### Files Modified:
- `ClassicLib/ScanLog/OrchestratorCore.py` - Use `get_record_scanner()` factory
- `ClassicLib/FileGeneration.py` - Use `get_file_io()` factory
- `ClassicLib/YamlSettings/async_/file_operations.py` - Use `get_file_io()` factory
- `ClassicLib/ScanGame/GameIntegrityOrchestrator.py` - Use `get_file_io()` factory
- `ClassicLib/ScanGame/GameFilesManager.py` - Use `get_file_io()` factory

### Files Created:
- `tests/rust_integration/test_factory_integration.py` - Factory integration tests

### Test Results:
- All 23 component integration tests pass
- All 10 factory integration tests pass
