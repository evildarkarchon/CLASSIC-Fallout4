# Python Test Suite Alignment Plan (v8.0.0+)

**Goal:** Align the Python test suite with the v8.0.0+ architecture (Post-Rust Migration) by systematically fixing failures across 5 phases.

**Status:**
- [x] Phase 1: Core Infrastructure & Mocking Foundation (Complete)
- [x] Phase 2: Async/Sync Alignment (Complete)
- [x] Phase 3: Module API & Type Coercion (Complete)
- [x] Phase 4: Rust Integration & Parity (Core checks passing, advanced property tests skipped/pending)
- [ ] Phase 5: Coverage Expansion & Cleanup (Future work)

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

## Phase 4: Rust Integration & Parity (Partially Done)
- **Goal:** Ensure Python tests align with Rust implementation details.
- **Key Actions:**
    - Updated `tests/test_rust_stubs.py` to point to correct stub locations and removed checks for non-existent classes (`RustFormIDAnalyzer`, `RustOrchestrator`).
    - Fixed `RecordScanner` usage in `tests/rust_integration/test_record_scanner_parity.py`.

## Phase 5: Coverage Expansion & Cleanup (TODO)
- **Goal:** Improve coverage and remove obsolete tests.
- **Tasks:**
    - Review skipped tests and decide on removal or reimplementation.
    - Check `tests/stress` folder.
    - Run full suite and ensure stability.