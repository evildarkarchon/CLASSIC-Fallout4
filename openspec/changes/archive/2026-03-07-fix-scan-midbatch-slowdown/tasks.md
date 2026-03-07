## 1. Progress Event Model

- [x] 1.1 Define the coarse per-log batch progress phases and terminal states at the Rust/C++ bridge boundary.
- [x] 1.2 Update the batch scan callback payload and Rust bridge flow to emit monotonic queued, started, phase, and completed or failed progress events.
- [x] 1.3 Add focused tests or fixture-driven checks that verify per-log state transitions remain monotonic and batch progress never regresses.

## 2. GUI Progress Presentation

- [x] 2.1 Update GUI scan worker progress aggregation to derive visible progress from in-flight per-log states instead of completed-log counts alone.
- [x] 2.2 Preserve the existing simple status-bar messaging style while feeding it smoother progress derived from the richer internal event model.
- [x] 2.3 Validate mixed-size batch behavior so heavy mid-batch logs no longer appear frozen to the user.

## 3. Orchestrator Shared Context Reuse

- [x] 3.1 Introduce a shared per-log analysis context in `classic-scanlog-core` for derived callstack and plugin views reused across analyzer phases.
- [x] 3.2 Refactor `process_log()` to route analyzer phases through the shared context instead of rebuilding equivalent intermediate structures per phase.
- [x] 3.3 Preserve existing scan result behavior with parity-focused tests covering successful scans, failed scans, and representative heavy logs.

## 4. Analyzer Hot-Path Simplification

- [x] 4.1 Simplify the highest-cost plugin and callstack analysis paths to reduce repeated full-data scans while preserving current matching semantics.
- [x] 4.2 Review suspect and record analysis paths for repeated whole-callstack rebuilding and switch them to shared derived data where applicable.
- [x] 4.3 Re-run representative heavy-log validations to confirm analyzer changes improve throughput without altering report ordering or content expectations.

## 5. Diagnostics And Verification

- [x] 5.1 Add lightweight per-log phase timing instrumentation at orchestration boundaries for setup, parse, analyze, and finalize phases.
- [x] 5.2 Add batch-level diagnostic output sufficient to distinguish progress event behavior from analyzer hot-path regressions.
- [x] 5.3 Run targeted GUI and Rust scan validation on representative mixed-size log batches and document the observed progress and throughput outcome.
