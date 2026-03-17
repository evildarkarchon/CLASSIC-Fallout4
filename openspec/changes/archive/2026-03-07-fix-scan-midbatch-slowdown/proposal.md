## Why

GUI batch scans currently present progress as whole-log completions, which makes the scan appear to stall in the middle when a few heavier logs occupy the worker slots and then suddenly speed up when shorter logs finish in a burst. At the same time, the Rust scan orchestrator appears to repeat work across analyzers and rebuild intermediate views of the same crash data, adding avoidable cost exactly where large logs are already the slowest.

## What Changes

- Define batch scan progress behavior that reflects active in-flight work instead of only completed logs so GUI users receive truthful, stable progress updates during multi-log scans.
- Add coarse internal scan-phase visibility for batch processing so the system can avoid frozen-looking mid-batch progress without requiring more detailed status-bar text.
- Reduce redundant scanlog orchestrator passes and repeated crash-data materialization while preserving existing analysis results, report content, and failure behavior.
- Add focused validation and instrumentation coverage for heavy-log batches so progress behavior and orchestrator throughput regressions are detectable in future work.

## Capabilities

### New Capabilities
- `scan-batch-progress-reporting`: Define user-visible batch scan progress behavior that represents in-flight work and long-running logs more accurately than completion-only updates.
- `scanlog-pipeline-efficiency`: Define performance-sensitive scan pipeline behavior that reuses shared derived log data across analyzers instead of repeatedly rebuilding equivalent intermediate views.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs`
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/suspect_scanner.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
  - `classic-gui/src/workers/scanworker.cpp`
  - `classic-gui/src/app/mainwindow.cpp`
- Systems:
  - Rust scanlog orchestration and analyzer hot paths
  - C++/Rust batch bridge progress callbacks
  - GUI batch progress presentation for crash-log scans
- Compatibility:
  - No intended breaking API changes for existing CLI/GUI/binding consumers; the change should preserve scan results while improving progress semantics and throughput.
