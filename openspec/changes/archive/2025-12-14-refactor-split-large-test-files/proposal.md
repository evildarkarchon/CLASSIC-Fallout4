# Change: Split Large Test Files into Focused Modules

## Why

Four test files exceed 900 lines each (totaling 4,577 lines), making them difficult to maintain, slow to execute in isolation, and hard to debug when failures occur. Splitting these into focused modules improves test isolation, parallel execution efficiency, and developer productivity.

## What Changes

- **Split `test_hybrid_orchestrator.py`** (1,300 lines, 6 classes) into 3 focused files:
  - `test_hybrid_orchestrator_integration.py` - Core integration tests
  - `test_hybrid_orchestrator_factory.py` - Factory pattern and conversion tests
  - `test_hybrid_orchestrator_modes.py` - Feature-complete and batch-only mode tests

- **Split `test_update_network_comprehensive_unit.py`** (1,237 lines, 8 classes) into 4 focused files:
  - `test_update_version_parsing.py` - Version parsing tests
  - `test_update_github_api.py` - GitHub API interaction tests
  - `test_update_nexus_scraping.py` - Nexus version scraping tests
  - `test_update_check_logic.py` - Update checking and error handling

- **Split `test_data_volume_stress.py`** (1,073 lines, 4 classes) into 4 focused files:
  - `test_stress_formid_volume.py` - FormID processing at scale
  - `test_stress_plugin_volume.py` - Plugin load order stress
  - `test_stress_callstack_volume.py` - Call stack processing
  - `test_stress_batch_volume.py` - Batch processing at scale

- **Split `test_error_recovery_stress.py`** (967 lines, 4 classes) into 4 focused files:
  - `test_stress_malformed_data.py` - Malformed data handling
  - `test_stress_resource_failure.py` - Resource failure recovery
  - `test_stress_partial_failure.py` - Partial failure handling
  - `test_stress_cascading_failure.py` - Cascading failure recovery

- **Add test file size limit requirement** - New spec requirement to prevent future large file accumulation

## Impact

- **Affected specs**: `test-suite`
- **Affected code**:
  - `tests/rust_integration/test_hybrid_orchestrator.py` -> 3 files
  - `tests/utils/test_update_network_comprehensive_unit.py` -> 4 files
  - `tests/stress/test_data_volume_stress.py` -> 4 files
  - `tests/stress/test_error_recovery_stress.py` -> 4 files
- **Benefits**:
  - Faster failure isolation (run single focused file)
  - Better parallel execution (pytest-xdist can distribute smaller files)
  - Improved maintainability (each file has single responsibility)
  - Clearer test organization (file name indicates test scope)
