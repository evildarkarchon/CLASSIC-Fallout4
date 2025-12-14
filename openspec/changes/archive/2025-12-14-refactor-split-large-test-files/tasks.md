# Tasks: Split Large Test Files

## 1. Split Hybrid Orchestrator Tests (Parallelizable)

- [x] 1.1 Create `test_hybrid_orchestrator_integration.py` with `TestHybridOrchestratorIntegration` class (lines 1-330)
- [x] 1.2 Create `test_hybrid_orchestrator_factory.py` with `TestFactoryPattern`, `TestRustConversion` classes (lines 331-566)
- [x] 1.3 Create `test_hybrid_orchestrator_modes.py` with `TestPythonFallback`, `TestFeatureCompleteMode`, `TestBatchOnlyMode` classes (lines 567-1300)
- [x] 1.4 Verify all tests pass: `uv run pytest tests/rust_integration/test_hybrid_orchestrator*.py -v`
- [x] 1.5 Delete original `test_hybrid_orchestrator.py` after verification

## 2. Split Update Network Tests (Parallelizable with 1)

- [x] 2.1 Create `test_update_version_parsing.py` with `TestTryParseVersion` class (lines 1-159)
- [x] 2.2 Create `test_update_github_api.py` with `TestGitHubStableVersionEndpoint`, `TestGitHubPrereleaseVersionList`, `TestGitHubReleaseDetails` classes (lines 160-564)
- [x] 2.3 Create `test_update_nexus_scraping.py` with `TestNexusVersionScraping` class (lines 565-733)
- [x] 2.4 Create `test_update_check_logic.py` with `TestUpdateChecking`, `TestUpdateCheckErrorHandling`, `TestUpdateCheckErrorClass` classes (lines 734-1237)
- [x] 2.5 Verify all tests pass: `uv run pytest tests/utils/test_update*.py -v`
- [x] 2.6 Delete original `test_update_network_comprehensive_unit.py` after verification

## 3. Split Data Volume Stress Tests (Parallelizable with 1, 2)

- [x] 3.1 Create `test_stress_formid_volume.py` with `TestMassiveFormIDProcessing` class (lines 1-268)
- [x] 3.2 Create `test_stress_plugin_volume.py` with `TestMassivePluginLoadOrders` class (lines 269-577)
- [x] 3.3 Create `test_stress_callstack_volume.py` with `TestMassiveCallStackProcessing` class (lines 578-818)
- [x] 3.4 Create `test_stress_batch_volume.py` with `TestBatchProcessingAtScale` class (lines 819-1073)
- [x] 3.5 Verify all tests pass: `uv run pytest tests/stress/test_stress_*_volume.py -v`
- [x] 3.6 Delete original `test_data_volume_stress.py` after verification

## 4. Split Error Recovery Stress Tests (Parallelizable with 1, 2, 3)

- [x] 4.1 Create `test_stress_malformed_data.py` with `TestMalformedDataHandling` class (lines 1-311)
- [x] 4.2 Create `test_stress_resource_failure.py` with `TestResourceFailureRecovery` class (lines 312-529)
- [x] 4.3 Create `test_stress_partial_failure.py` with `TestPartialFailureHandling` class (lines 530-712)
- [x] 4.4 Create `test_stress_cascading_failure.py` with `TestCascadingFailureRecovery` class (lines 713-967)
- [x] 4.5 Verify all tests pass: `uv run pytest tests/stress/test_stress_*_failure.py tests/stress/test_stress_malformed*.py -v`
- [x] 4.6 Delete original `test_error_recovery_stress.py` after verification

## 5. Validation

- [x] 5.1 Run full test suite: `uv run pytest -n auto -m "unit and not slow"`
- [x] 5.2 Run stress tests: `uv run pytest tests/stress/ -v`
- [x] 5.3 Run rust integration tests: `uv run pytest tests/rust_integration/ -v`
- [x] 5.4 Verify no test count regression (original 4 files should have same test count as new 15 files)

## Dependencies

- Tasks 1.1-1.3, 2.1-2.4, 3.1-3.4, 4.1-4.4 can all run in parallel (no interdependencies)
- Verification tasks (*.4, *.5, *.6) must wait for their respective creation tasks
- Task 5 (Validation) must wait for all deletions (1.5, 2.6, 3.6, 4.6)

## Notes

- Each new file should include the same imports and fixtures as needed from the original
- Preserve all pytest markers on test classes
- Shared fixtures should be extracted to `tests/fixtures/` if not already there
- File docstrings should reflect the focused scope of each new file

## Implementation Summary

All 15 new test files were created successfully:

**Hybrid Orchestrator Tests (29 tests):**
- `tests/rust_integration/test_hybrid_orchestrator_integration.py`
- `tests/rust_integration/test_hybrid_orchestrator_factory.py`
- `tests/rust_integration/test_hybrid_orchestrator_modes.py`

**Update Tests (54 tests):**
- `tests/utils/test_update_version_parsing.py`
- `tests/utils/test_update_github_api.py`
- `tests/utils/test_update_nexus_scraping.py`
- `tests/utils/test_update_check_logic.py`

**Data Volume Stress Tests (10 tests):**
- `tests/stress/test_stress_formid_volume.py`
- `tests/stress/test_stress_plugin_volume.py`
- `tests/stress/test_stress_callstack_volume.py`
- `tests/stress/test_stress_batch_volume.py`

**Error Recovery Stress Tests (10 tests):**
- `tests/stress/test_stress_malformed_data.py`
- `tests/stress/test_stress_resource_failure.py`
- `tests/stress/test_stress_partial_failure.py`
- `tests/stress/test_stress_cascading_failure.py`

Original files deleted:
- `tests/rust_integration/test_hybrid_orchestrator.py`
- `tests/utils/test_update_network_comprehensive_unit.py`
- `tests/stress/test_data_volume_stress.py`
- `tests/stress/test_error_recovery_stress.py`
