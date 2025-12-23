# Plan: Optimize Python-Rust Integration Layer

## Phase 1: Analysis & Benchmarking
- [x] Task: Audit existing PyO3 bindings in `rust/python-bindings/` to identify high-overhead patterns (e.g., excessive JSON serialization). [91e2298]
- [x] Task: Create a benchmark suite in `tests/benchmarks/` to measure current FFI call overhead for key functions (`scan_log`, `validate_file`). [25bcfb6]
- [ ] Task: Conductor - User Manual Verification 'Analysis & Benchmarking' (Protocol in workflow.md)

## Phase 2: Error Handling Standardization
- [ ] Task: Define a shared error schema in Rust (`classic-shared-core`) that maps cleanly to Python exceptions.
- [ ] Task: Implement `From<RustError> for PyErr` conversions in a shared utility crate.
- [ ] Task: Update one low-risk module (e.g., `classic-config-py`) to use the new error handling pattern.
- [ ] Task: Verify error propagation with Python unit tests.
- [ ] Task: Conductor - User Manual Verification 'Error Handling Standardization' (Protocol in workflow.md)

## Phase 3: Type Safety & Zero-Copy Optimization
- [ ] Task: Refactor `classic-scanlog-py` to use direct struct mapping instead of JSON strings where feasible.
- [ ] Task: Update Python type stubs (`.pyi`) to reflect stricter types.
- [ ] Task: Implement `#[pyclass]` for complex data structures returned by the scanner to avoid recreation in Python.
- [ ] Task: Conductor - User Manual Verification 'Type Safety & Zero-Copy Optimization' (Protocol in workflow.md)

## Phase 4: Verification & Cleanup
- [ ] Task: Run the benchmark suite again to quantify performance improvements.
- [ ] Task: Run the full test suite (`pytest` and `cargo test`) to ensure no regressions.
- [ ] Task: Document the new FFI patterns in `docs/development/rust_bindings.md`.
- [ ] Task: Conductor - User Manual Verification 'Verification & Cleanup' (Protocol in workflow.md)
