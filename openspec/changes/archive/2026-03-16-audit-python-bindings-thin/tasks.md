## 1. Remove Dead Code and Deprecated Shims

- [x] 1.1 Remove `PyParallelReportProcessor::process_batch()` stub from `classic-scanlog-py/src/report.rs` and update the `.pyi` stub
- [x] 1.2 Remove deprecated `parse_segments` method (marked `#[allow(deprecated)]`) from `classic-scanlog-py/src/parser.rs` and update the `.pyi` stub
- [x] 1.3 Remove unused `_segment_boundaries` and `_xse_acronym` parameters from `parse_complete` in `classic-scanlog-py/src/parser.rs` and update the `.pyi` stub
- [x] 1.4 Remove deprecated `crashgen_ignore` getter (returns empty Vec) from `classic-scanlog-py/src/orchestrator.rs` and update the `.pyi` stub
- [x] 1.5 Remove backward-compatibility `batch_lookup` wrapper from `classic-database-py/src/pool.rs` and update the `.pyi` stub
- [x] 1.6 Search the codebase for callers of removed APIs and update any found call sites

## 2. Relocate Business Logic to Core Crates

- [x] 2.1 Move adaptive concurrency selection logic (CPU-count-based worker calculation) from `classic-scanlog-py/src/orchestrator.rs` (lines ~966-977) into `classic-scanlog-core` as a public function
- [x] 2.2 Update `process_logs_batch()` in `classic-scanlog-py` to call the new core concurrency function instead of computing locally
- [x] 2.3 Remove the obsolete `classic-pybridge-py` crate from `ClassicLib-rs/Cargo.toml` and delete its source/stub files
- [x] 2.4 Remove `classic_pybridge` from Python binding CI/parity generation/runtime coverage inputs
- [x] 2.5 Update parity baselines, smoke tests, and docs to stop treating `classic_pybridge` as a maintained module
- [x] 2.6 Update or retire the old `openspec/specs/pybridge-self-contained/spec.md` guidance

## 3. Rewire fcx_handler to Rust Core

- [x] 3.1 Add `classic-scangame-core` as a dependency in `classic-scanlog-py/Cargo.toml`
- [x] 3.2 Replace the `PyModule::import(py, "ClassicLib.SetupCoordinator")` call in `fcx_handler.rs` `check_fcx_mode()` with a call to `classic_scangame_core::setup::run_combined_checks()`, mapping `SetupCheckResults` to the `FcxModeHandler` main-files state
- [x] 3.3 Replace the `PyModule::import(py, "ClassicLib.ScanGame")` call in `fcx_handler.rs` `check_fcx_mode()` with a call to `classic_scangame_core::orchestrator::detect_config_issues()`, mapping the returned `Vec<ConfigIssue>` to the handler's detected-issues state
- [x] 3.4 Remove all `PyModule::import` calls from `fcx_handler.rs` and verify no Python runtime dependency remains
- [x] 3.5 Verify the `GLOBAL_FCX_HANDLER` caching pattern still works correctly with the Rust-native call path

## 4. Create Audit Criteria Documentation

- [x] 4.1 Create a `ClassicLib-rs/python-bindings/BINDING_AUDIT_CRITERIA.md` file documenting the formal thin-binding definition from the spec (what is compliant, what is a violation, exemptions for PyO3 patterns)
- [x] 4.2 Include a per-crate audit checklist table showing each of the 19 binding crates and their compliance status

## 5. Update Parity Artifacts and Type Stubs

- [x] 5.1 Regenerate all affected `.pyi` type stub files for crates with removed or changed APIs (`classic-scanlog-py`, `classic-database-py`) and remove obsolete `classic_pybridge` stub artifacts
- [x] 5.2 Regenerate the parity diff report at `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md`
- [x] 5.3 Update parity gate tests under `ClassicLib-rs/python-bindings/tests/` to reflect removed APIs

## 6. Verification

- [x] 6.1 Run `cargo build` for all modified `-py` and `-core` crates to confirm compilation
- [x] 6.2 Run `cargo test` for all modified crates to confirm no regressions
- [x] 6.3 Run the parity gate check (`tools/python_api_parity/`) to confirm parity report is clean
- [x] 6.4 Verify each of the 19 binding crates against the audit criteria checklist and mark any remaining items
