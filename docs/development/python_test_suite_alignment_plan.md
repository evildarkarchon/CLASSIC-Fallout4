# Python Test Suite Alignment Plan (v8.0.0+)

**Goal:** Align the Python test suite with the v8.0.0+ architecture (Post-Rust Migration) by systematically fixing failures across 5 phases.

**Status:**
- [x] Phase 1: Core Infrastructure & Mocking Foundation (DONE)
- [x] Phase 2: Async/Sync Alignment (DONE)
- [x] Phase 3: Module API & Type Coercion (DONE)
- [x] Phase 4: Rust Integration & Parity (DONE)
- [ ] Phase 5: Coverage Expansion & Cleanup (IN PROGRESS)

## Phase 1: Core Infrastructure & Mocking Foundation (DONE)
- **Goal:** Fix core import errors, fixture scopes, and basic mocking issues.
- **Key Actions:**
    - Updated `tests/settings/test_yaml_batch_operations.py` to use `AsyncMock` for async context managers.
    - Updated `tests/settings/test_yaml_sync_wrapper_unit.py` to mock `_async_core`.
    - Fixed `tests/game/test_game_integrity_synthetic.py` import paths and mocking.
    - Fixed `tests/edge_cases/test_file_permission_errors.py` message handler usage.
    - Fixed `tests/setup/test_setup_initialization.py` mocking.

## Phase 2: Async/Sync Alignment (DONE)
- **Goal:** Eliminate `RuntimeError: yaml_settings() called from async context`.
- **Key Actions:**
    - Patched `yaml_settings` in `ClassicLib.ScanGame.Config` for `tests/scanning/test_scan_mod_inis_async.py` and `tests/scanlog/test_fcx_handler.py`.
    - Updated `LogProcessor.py` to use `yaml_settings_async` and `await` in `check_log_errors`.
    - Fixed `TestScanGameOptimizations` mock arguments.
    - Mocked `msg_error` in FCX handler tests to avoid `RuntimeError`.
    - Added `message_handler` fixture to async tests.

## Phase 3: Module API & Type Coercion (DONE)
- **Goal:** Fix API mismatches, missing modules, and type errors.
- **Key Actions:**
    - **Rust Bindings:** Updated `ClassicLib/rust/plugin_rust.py` to cast `crashgen_name` to string.
    - **Imports:** Fixed `ClassicLib.OrchestratorCore` import in `tests/integration/test_scan_pipeline_e2e.py`.
    - **Entry Points:** Updated `tests/entry_points/test_classic_scangame.py` to patch `ClassicLib.AsyncBridge.AsyncBridge` and mocked GUI mode.
    - **Rewritten:** Rewrote `tests/entry_points/test_classic_scanlogs.py` to match new CLI structure.
    - **Refactored Tests:** Updated `tests/mods/test_mod_detection_patterns.py` to use correct mock data structures and updated assertion logic.
    - **Skipped:** Skipped `test_game_scan_to_integrity_check_pipeline` as `GameScanner` is removed.

## Phase 4: Rust Integration & Parity (Complete)
- **Goal:** Ensure Python tests align with Rust implementation details.
- **Key Actions:**
    - Updated `tests/test_rust_stubs.py` to point to correct stub locations and removed checks for non-existent classes (`RustFormIDAnalyzer`, `RustOrchestrator`). *Complete*
    - Fixed `RecordScanner` usage in `tests/rust_integration/test_record_scanner_parity.py`. *Complete*
    - **Fixed `classic_config.YamlData` Rust API**: Modified `rust/business-logic/classic-config-core/src/yamldata.rs` to accept `[project_root, classic_data_dir]` for cleaner path resolution.
    - **Rebuilt Rust bindings**: Applied changes via `rebuild_rust.ps1`.
    - **Updated `ClassicLib/integration/factory.py`**: Adopted the new `YamlData` API by passing `[project_root, classic_data_dir]`.
    - **Created `tests/rust_integration/test_config_parity.py`**: Added comprehensive parity tests for `classic_config.YamlData`, which now pass (with one expected skip for unimplemented Skyrim support). *Complete*
    - Improve coverage of rust-integrated modules with new tests for all rust modules. *Complete*
    - Review and reimplement tests that were skipped. *Complete* (for `test_config_parity.py`, `test_different_game_instance` is now explicitly skipped due to unimplemented feature)
    - Clean up tests in `tests/rust_integration` that are no longer relevant. *Complete*

## Phase 5: Coverage Expansion & Cleanup (IN PROGRESS)
- **Goal:** Improve coverage and remove obsolete tests.
- **Tasks:**
    - Review skipped tests and decide on removal or reimplementation.
    - Check `tests/stress` folder.
    - **Fix ScanGameCore Async/Mocking Issues**:
        - Refactored `ScanGameCore` methods to use `await yaml_settings_async`.
        - Updated `tests/scanning/test_scan_game_wrappers.py` to correctly mock `ScanGameCore` and its methods.
    - **Address Remaining Failures:**
        - **Fixed `test_async_yaml_caching.py`**: 
            - Implemented `YamlFileOperations.clear_cache()` and updated `AsyncYamlSettingsCore.clear_cache()` to ensure underlying file caches are cleared.
        - **Fixed `test_dds_analyzer.py`**:
            - Updated assertions to reflect enhanced validation (4 issues detected instead of 1).
        - **Fixed `test_scan_mods_archived.py`**:
            - Updated assertion to match actual error message format.
            - Corrected patching target for `msg_error`.
        - **Fixed `test_initial_setup.py`**:
            - Corrected mock target to `yaml_cache` instance and used async `side_effect`.
        - `test_scan_mods_unpacked.py`: `AssertionError: F4SE FILES FOUND`
        - `test_async_utilities_unit.py`: `AssertionError: test_applies_backoff`
        - `test_string_utils.py`: `AssertionError: test_append_or_extend_single_values`
        - `test_rust_backend_performance.py`: `ZeroDivisionError`
        - `test_rust_database_pool.py`: `RustDatabaseIOError`
        - `test_report_parity.py`: `TypeError: Can't instantiate abstract class`
        - `test_ffi_error_conditions.py`: `Failed: DID NOT RAISE`
        - `test_formid_parity.py`: `AssertionError: FormID extraction parity too low`
    - Run full suite and ensure stability.