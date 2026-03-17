## Why

The Python bindings in `ClassicLib-rs/python-bindings/` were originally written as performance optimizations for a pure-Python CLASSIC application. As the project migrated to Rust-first architecture, these bindings were refactored to delegate to `-core` crates. However, no systematic audit has been performed to confirm that all 19 binding crates are genuinely thin wrappers with no residual business logic, stale compatibility shims, or binding-layer state management that should live in Rust core. An audit now ensures the architecture stays clean before further development compounds any violations.

## What Changes

- Audit all 19 `classic-*-py` binding crates and the `classic-shared-py` foundation crate for thin-wrapper compliance
- Remove or relocate any business logic found in the binding layer (validation, caching, transformation, concurrency strategy) into the appropriate `-core` crate
- Remove dead code: stub functions (e.g., `PyParallelReportProcessor::process_batch()`), deprecated shims kept only for backward compatibility, and unused parameters
- Rewire `fcx_handler.rs` `check_fcx_mode()` to call existing Rust core functions (`classic-scangame-core::setup::run_combined_checks()` and `classic-scangame-core::orchestrator::detect_config_issues()`) instead of calling back into legacy Python modules (`ClassicLib.SetupCoordinator`, `ClassicLib.ScanGame`)
- Move the `process_logs_batch()` adaptive concurrency strategy from `classic-scanlog-py` into `classic-scanlog-core`
- Remove obsolete `classic-pybridge-py` now that the Python app it served no longer exists, and clean up CI/parity/docs references that still treat it as maintained
- Remove deprecated API compatibility shims (`parse_segments`, unused `_segment_boundaries`/`_xse_acronym` parameters, `crashgen_ignore` returning empty Vec, `batch_lookup` wrapper)
- **BREAKING**: Deprecated Python APIs that were kept for backward compatibility will be removed

## Capabilities

### New Capabilities
- `binding-audit-criteria`: Formal criteria and checklist defining what constitutes a thin binding vs. a violation, applied uniformly across all 19 binding crates

### Modified Capabilities

## Impact

- **Python bindings**: All 19 `classic-*-py` crates under `ClassicLib-rs/python-bindings/` may have code removed or relocated
- **Rust core crates**: `classic-scanlog-core` and `classic-scangame-core` may gain small API additions to support thinner bindings
- **Python consumers**: Any Python code using deprecated APIs (`parse_segments`, `batch_lookup`, `crashgen_ignore`) will break
- **Parity artifacts**: `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md` and associated tests will need updates after API removals and `classic_pybridge` retirement
- **Type stubs**: `.pyi` files for affected crates must be regenerated
- **Workspace/CI/docs**: Python-binding workflow files and docs that still mention `classic-pybridge-py` will need cleanup
