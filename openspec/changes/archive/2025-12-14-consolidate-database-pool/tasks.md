# Tasks: consolidate-database-pool

## Phase 1: Create New Package Structure

### Task 1.1: Create ClassicLib/Database package
- [x] Create `ClassicLib/Database/` directory
- [x] Create `ClassicLib/Database/__init__.py` with re-exports
- **Verification**: `from ClassicLib.Database import DatabasePoolManager` succeeds ✓

### Task 1.2: Extract AsyncDatabasePool to dedicated module
- [x] Create `ClassicLib/Database/async_pool.py`
- [x] Move `AsyncDatabasePool` class from `ClassicLib/ScanLog/AsyncUtil.py`
- [x] Add module docstring documenting pure Python implementation
- **Verification**: `from ClassicLib.Database.async_pool import AsyncDatabasePool` works ✓

### Task 1.3: Extract RustAsyncDatabasePool to dedicated module
- [x] Create `ClassicLib/Database/rust_pool.py`
- [x] Move `RustAsyncDatabasePool` class from `ClassicLib/rust/database_rust.py`
- [x] Preserve all Rust exception handling and compatibility attributes
- **Verification**: `from ClassicLib.Database.rust_pool import RustAsyncDatabasePool` works ✓

### Task 1.4: Create unified DatabasePoolManager
- [x] Create `ClassicLib/Database/pool_manager.py`
- [x] Implement single `DatabasePoolManager` that:
  - Uses Rust pool when available (via factory check)
  - Falls back to Python pool automatically
  - Maintains singleton pattern with thread-safe creation
- [x] Remove `DatabasePoolManager` from both source files
- **Verification**: `DatabasePoolManager().get_pool()` returns correct implementation ✓

## Phase 2: Update Integration Layer

### Task 2.1: Update factory to use new locations
- [x] Modify `ClassicLib/integration/factory/database.py`
- [x] Import from `ClassicLib.Database` instead of `ClassicLib.rust.database_rust` and `ClassicLib.ScanLog.AsyncUtil`
- **Verification**: `get_database_pool()` returns correct implementation type ✓

### Task 2.2: Add backward compatibility re-exports
- [x] Update `ClassicLib/ScanLog/AsyncUtil.py`:
  - Keep file operations (`read_file_async`, `write_file_async`, etc.)
  - Add deprecation warning for `AsyncDatabasePool` import
  - Re-export from new location
- [x] Update `ClassicLib/rust/database_rust.py`:
  - Add deprecation warning for direct imports
  - Re-export from new location
- **Verification**: Existing import paths work with deprecation warnings ✓

## Phase 3: Migrate Callers

### Task 3.1: Update direct imports in production code
- [x] `ClassicLib/ScanLog/OrchestratorCore.py`
- [x] `ClassicLib/ScanLog/FormIDAnalyzerCore.py`
- [x] `ClassicLib/ScanLog/ScanLogsExecutor.py`
- [x] `ClassicLib/python/formid_py.py`
- [x] `ClassicLib/ScanLog/__init__.py`
- [x] `ClassicLib/rust/__init__.py`
- **Verification**: `uv run ruff check ClassicLib/` passes ✓

### Task 3.2: Update test imports
- [x] `tests/rust_integration/test_rust_database_pool.py`
- [x] `tests/rust_integration/test_formid_parity.py`
- [x] `tests/async_tests/test_async_database.py`
- [x] `tests/async_resources/test_database_pool.py`
- [x] `tests/fixtures/database_pool_fixtures.py`
- [x] `tests/integration/test_phase3_technical_debt.py`
- **Verification**: `uv run pytest tests/async_tests/test_async_database.py -v` passes ✓

### Task 3.3: Update remaining callers
- [x] `tests/performance/test_orchestrator_performance.py`
- [x] `tests/core/test_formid_analyzer.py`
- [x] `tests/unit/test_singleton_isolation.py`
- **Verification**: `uv run pytest -n auto -m "not slow"` passes ✓

## Phase 4: Cleanup

### Task 4.1: Remove deprecated re-exports
- [x] Remove `AsyncDatabasePool` and `DatabasePoolManager` from `AsyncUtil.py`
- [x] Remove `DatabasePoolManager` and `RustAsyncDatabasePool` from `database_rust.py`
- [x] Keep only re-export shim with deprecation warning if needed for external compatibility
- **Verification**: Line counts reduced: AsyncUtil.py = 195 lines, database_rust.py = 79 lines ✓

### Task 4.2: Final verification
- [x] Run database-related tests: All pass
- [x] Run linting: `uv run ruff check .` passes
- [x] Verify Rust integration tests pass
- **Verification**: All checks pass, no import errors ✓

## Dependencies
- Task 1.2, 1.3 can run in parallel
- Task 1.4 depends on 1.2, 1.3
- Task 2.1, 2.2 depend on Phase 1
- Phase 3 depends on Phase 2
- Phase 4 depends on Phase 3 completion and test verification
