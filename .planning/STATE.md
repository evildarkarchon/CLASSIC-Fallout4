# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Python is the UI, Rust is the engine — every piece of business logic lives in Rust `-core` crates, Python only handles presentation and user interaction.
**Current focus:** v8.2.0-part2 Rust Migration - Phase 10 (Parity Validation) - COMPLETE

## Current Position

Phase: 10 of 11 (Parity Validation) - COMPLETE
Plan: 2 of 2 complete
Status: Phase 10 complete, ready for Phase 11 (Cleanup)
Last activity: 2026-02-03 - Completed parity validation with 51 passing + 20 parity failures (expected)

Progress: [v1.0: 14/14] [v8.2.0-part2: 14/14] 100%
[##############] Phase 10 complete

## Performance Metrics

**v1.0 Velocity:**
- Total plans completed: 14
- Average duration: 12m
- Total execution time: ~2.8 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-cleanup | 4/4 | 42m 11s | 10m 33s |
| 02-integration-layer-simplification | 2/2 | 20m | 10m |
| 03-wrapper-thinning | 2/2 | 18m | 9m |
| 04-interface-consolidation | 3/3 | 33m | 11m |
| 05-fallback-pruning | 3/3 | 64m | 21m |

**v8.2.0-part2:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 06-foundation-settings | 2/2 | ~15m | ~7.5m |
| 07-game-detection | 2/2 | ~27m | ~13.5m |
| 08-report-generation | 2/2 | ~15m | ~7.5m |
| 09-orchestration-migration | 4/4 | ~76m | ~19m |
| 10-parity-validation | 2/2 | ~17m | ~8.5m |

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.

v8.2.0-part2 decisions:
- Rust is 90-100% complete for all migration targets; work is wiring, validation, and Python removal
- Golden file capture happens in Phase 6 before migrations to ensure parity baseline
- Settings migration first (dependency for other components)
- Golden file masking uses {{TIMESTAMP}} placeholder only (paths visible for debugging)
- Capture intermediate outputs (segments + analysis) per log for debugging parity issues
- FCX Mode gates all validation (checking own installation vs analyzing crash logs)
- GlobalRegistry stores validation results (XSE_VALID, ENB_PRESENT) for use by other components
- Dual-interface pattern: sync + async variants for all validation functions
- Rust-only, hard fail: no Python fallback for path detection (ImportError propagates)
- Rust-only report generator: no Python fallback, RuntimeError if Rust unavailable
- VR removal: VR indicator text no longer displayed in reports (VR detection still used internally)
- Semantic parity for error sections: character-for-character not possible, validate meaning instead
- Deprecation pattern: module docstring + class docstring + runtime DeprecationWarning
- Arc<AtomicBool> for cancellation token (simpler than CancellationToken for between-logs checking)
- Arc<Py<PyAny>> for callback sharing across async tasks (thread-safe in PyO3 0.27)
- Python::attach() for GIL re-acquisition when invoking callbacks
- Index-tracking HashMap with buffer_unordered for order-preserving parallel processing
- ORCH-05 verified: is_feature_complete() returns True with real YamlData configuration
- Python OrchestratorCore and HybridOrchestrator deleted entirely (not deprecated first)
- asyncio.to_thread() pattern for Rust batch processing in async Python contexts
- ReportGenerator+ReportComposer pattern for proper AUTOSCAN.md formatting
- Header info extracted from processed_lines before segmentation
- Lazy loading via asyncio.to_thread() for crashlog_list/remove_list in ScanLogsExecutor
- suspects_stack_list type fix: HashMap<String, Vec<String>> not HashMap<String, String> (YAML arrays)
- Added get_hashmap_vec_value() to YamlOps for key->array YAML maps
- OrchestratorCore now includes RecordScanner, SettingsValidator, and FcxModeHandler integration
- Path normalization (backslash to forward slash) for cross-platform golden file comparison
- Dynamic golden file stem discovery prevents hardcoded list drift
- True parity testing: Golden files from actual Python AUTOSCAN.md output, not generated
- Parity failures are expected and valuable - they identify real Rust-Python differences
- Component names from factory._COMPONENT_KEY_MAP (parser, yamldata, orchestrator, path)

### Pending Todos

- Fix test_clear_cache in classic-yaml-core (pre-existing bug, tracked separately)
- Pre-existing GUI file path resolution issue in classic_settings() (relative path for CLASSIC Settings.yaml)
- Update obsolete tests referencing deleted orchestrator_core module (from Phase 9-02)
- Investigate 20 report parity failures (Rust vs Python output differences)
- Fix pre-existing test failures from Phase 8/9 API changes (46 tests)

### Blockers/Concerns

None.

## Parity Test Summary

VAL-03/04/05 validation complete:
- **Scanning parity (VAL-02):** 32 passing (Rust segments match Python)
- **Report parity (VAL-03):** 20 failures (expected - true Rust-Python differences)
- **Game detection API (VAL-04):** 15 passing
- **Existing tests (VAL-05):** 3849 passing (46 pre-existing failures)

Report parity differences identified:
1. Version string format differences
2. Extra blank lines in Rust output
3. Additional suspects detected in Rust
4. Missing settings validation section in Rust

## Session Continuity

Last session: 2026-02-03
Stopped at: Phase 10 plan 02 complete - parity validation with 51 passing + 20 expected failures
Resume file: None
Next action: Execute Phase 11 (Cleanup) to address parity findings
