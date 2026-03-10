# `classic::scanner` Scan Progress Callback Contract

Contributor-facing notes for the current batch scan progress callback contract declared and used by:

- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/scan_progress_callback.h)

This page documents the callback behavior visible in source today for the active Rust/C++ scan path.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Current Frontend Consumer Note

One active Qt consumer path is split across:

- [`classic-gui/src/workers/scanworker_execution.cpp`](../../classic-gui/src/workers/scanworker_execution.cpp)
- [`classic-gui/src/workers/scanworker.cpp`](../../classic-gui/src/workers/scanworker.cpp)

`scanworker_execution.cpp` owns the bridge callback adapter and batch bridge call, while `scanworker.cpp` consumes returned `BatchScanResult` values and maps them back to original rows with `inputIndex`.

For the Qt-side consumer flow, see [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md). For the Qt-side result-ordering notes, see [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md).

---

## Ordering Notes For Consumers

- callback events can interleave across logs
- returned `BatchScanResult` items are in completion order at the batch level
- callers that care about original request identity must use `input_index`

The current Qt worker path does not clamp `inputIndex`; it validates the returned index against the original `QStringList` and treats an out-of-range value as an error.

These are current behavior notes, not a future callback design.
