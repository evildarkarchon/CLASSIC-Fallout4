# Change: Rust Orchestrator Feature Parity

## Why

The Rust `OrchestratorCore` implementation in `classic-scanlog-core` is incomplete compared to the Python `OrchestratorCore`. The existing `HybridOrchestrator` (`ClassicLib/ScanLog/HybridOrchestrator.py`) currently uses Python for single-log processing (full features) and only delegates to Rust for batch parallelism. This limits performance gains because:

1. Single-log processing always uses Python (no Rust acceleration)
2. Batch processing uses Rust for parallelism but still lacks feature parity
3. Result conversion between Rust and Python formats loses fidelity

The Rust implementation lacks critical functionality including settings validation, FCX mode handling, record scanning, async FormID database lookups, and proper report generation. Achieving feature parity will enable HybridOrchestrator to use Rust for **both** single-log and batch processing, delivering 5-10x speedups across all scenarios.

## What Changes

### Phase 1: Core Processing Pipeline
- **ADDED** Report header/footer generation in Rust orchestrator
- **ADDED** Version checking and error section generation
- **ADDED** Crash data reformatting (simplify logs support)
- **ADDED** Incomplete/failed log detection and statistics tracking

### Phase 2: Analysis Integration
- **ADDED** SettingsValidator integration in orchestrator pipeline
- **ADDED** RecordScanner integration for named record detection
- **ADDED** Plugin suspect scanning (plugins found in callstack)
- **ADDED** FCXModeHandler integration for configuration checking

### Phase 3: Advanced Features
- **ADDED** Async FormID database lookup support via connection pool
- **ADDED** LoadOrder.txt file support for plugin list override
- **ADDED** FOLON (Fallout: London) specific mod detection
- **ADDED** Report writing functionality (write_reports_batch)

### Phase 4: API Alignment & HybridOrchestrator Refactor
- **MODIFIED** AnalysisConfig to match ClassicScanLogsInfo fields
- **MODIFIED** AnalysisResult to include all Python statistics (incomplete, scanned, failed counters)
- **ADDED** Context manager support (async_enter, async_exit methods)
- **ADDED** Python-compatible return types for process_crash_log
- **MODIFIED** HybridOrchestrator to use Rust for single-log processing when feature-complete
- **MODIFIED** ClassicOrchestrator API to support new AnalysisResult fields
- **MODIFIED** Result conversion in HybridOrchestrator._convert_rust_results()

## Impact

- **Affected specs**: rust-orchestrator (new capability)
- **Affected code**:
  - `rust/business-logic/classic-scanlog-core/src/orchestrator.rs`
  - `rust/business-logic/classic-scanlog-core/src/lib.rs`
  - `rust/python-bindings/classic-scanlog-py/src/orchestrator.rs`
  - `ClassicLib/ScanLog/HybridOrchestrator.py` (refactor to use Rust for single-log)
  - `ClassicLib/rust/orchestrator_api.py` (update ClassicOrchestrator)
  - `ClassicLib/integration/factory.py` (update get_orchestrator)
- **Dependencies**:
  - `classic-database-core` (for FormID database pool)
  - Existing `SettingsValidator`, `SuspectScanner`, `FormIDAnalyzerCore`
- **Expected outcome**:
  - Rust orchestrator can replace Python OrchestratorCore for full crash log analysis
  - HybridOrchestrator uses Rust for both single-log and batch processing
  - Expected 5-10x speedup for single log processing
  - Expected 10-20x speedup for batch processing (unbounded parallelism)
  - Python OrchestratorCore retained as fallback only
