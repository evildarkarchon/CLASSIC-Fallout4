# classic-gui scan result ordering test design

## Goal

Add a real Qt test that proves multi-log scan results are correlated back to the original `QStringList` rows with `result.input_index`, even when batch results arrive in completion order rather than input order.

## Why

Current docs now explain that the active GUI path depends on `result.input_index` when handling batch scan results, but the test suite does not yet execute that correlation path directly. Existing coverage is strongest in source-structure assertions and progress-model tests, not in a runtime test that exercises the worker-side mapping behavior.

## Current context

- `classic-gui/src/workers/scanworker.cpp` calls `classic::scanner::orchestrator_process_logs_batch_with_progress(...)` for multi-log scans.
- Returned `BatchScanResult` values are iterated in completion order.
- `ScanWorker` maps each result back to the original `QStringList` row with `result.input_index` before emitting `logScanned(index, success, resolvedPath)`.
- `MainWindow` and `ResultsController` do not receive `input_index` directly; they consume later Qt signals and file-discovery behavior.

## Options considered

### 1. Runtime Qt test around `ScanWorker` with an injectable seam

Recommended.

Introduce a narrow, test-oriented seam around the multi-log batch execution path so a Qt test can inject completion-ordered fake `BatchScanResult` values without invoking the real Rust scanner setup path. The test then verifies emitted `logScanned(...)` signals use the original row indices from `input_index`.

Pros:

- Proves real worker behavior instead of only proving source text.
- Keeps the test focused on the exact correlation contract.
- Avoids full Rust runtime/network/file-system coupling.

Trade-off:

- Requires a small production seam in `ScanWorker` or an adjacent helper.

### 2. Extract a pure helper and test it directly

Move the result-correlation loop into a pure helper and test the helper with fake results.

Pros:

- Very small and deterministic.

Trade-off:

- Does not prove the actual worker/signal path used by Qt.

### 3. Extend source-level guard tests only

Add more regex/text assertions to the existing wiring test.

Pros:

- Lowest implementation cost.

Trade-off:

- Does not close the real runtime coverage gap.

## Chosen design

Use option 1.

Add a narrow worker-level seam so tests can supply a fake batch execution path that returns out-of-order `BatchScanResult` values. Because `ScanWorker::doScan(...)` currently builds scan config and creates an orchestrator before the batch call, the seam should cover the full multi-log batch execution step used by the worker, not just the final bridge function invocation. The production code path still uses the existing bridge API by default.

The new Qt test should:

1. build a small multi-log input list
2. provide fake batch results in completion order that does not match input order
3. run the multi-log branch of `ScanWorker`
4. capture emitted `logScanned(index, success, logPath)` signals
5. assert the emitted signals are still observed in completion-result iteration order, not re-sorted to input order
6. assert the emitted indices correspond to `result.input_index`, not result position
7. assert fallback-path resolution still uses the original `QStringList` row for empty `result.log_path`

## Expected code shape

- Keep production behavior unchanged for normal callers.
- Introduce the smallest possible injection point that still covers the current config/orchestrator setup blocking isolated tests.
- Keep report-writing and unsolved-log side effects stubbed, bypassed, or otherwise controlled in the test so ordering assertions stay focused.
- Prefer a dedicated new Qt test file over expanding the existing grep-based wiring test.

## Files likely involved

- `classic-gui/src/workers/scanworker.cpp`
- `classic-gui/src/workers/scanworker.h`
- `classic-gui/src/workers/scanprogressmodel.cpp`
- `classic-gui/tests/CMakeLists.txt`
- new Qt test file under `classic-gui/tests/`

## Test strategy

- Add one executable Qt test that exercises the multi-log worker path with fake batch results.
- Keep current source-wiring tests as lightweight structural guards.
- Do not require the real Rust scanner, YAML loading, or orchestrator setup to produce controlled completion ordering in the test.

## Risks and caveats

- The seam must stay narrow so production code does not become test-shaped.
- The test should avoid accidentally asserting more than the current contract; it should prove correlation through `input_index`, not invent a stronger ordering guarantee.
- There is still no claim that Results-tab ordering follows scan input order; that remains a separate file-discovery concern.
