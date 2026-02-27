## 1. Benchmark Scope and Fixtures

- [x] 1.1 Define the canonical Rust DB benchmark scenario matrix (single lookup cold/warm, batch lookup size classes, multi-db behavior, scan-path FormID resolution).
- [x] 1.2 Implement or consolidate reusable benchmark fixtures/dataset generation for Rust database benchmarks with deterministic inputs.
- [x] 1.3 Document benchmark metric fields and output schema used for baseline and comparison runs.

## 2. Rust Benchmark Implementation

- [x] 2.1 Add/extend `classic-database-core` benchmarks for single and batch lookup scenarios using the standardized fixtures.
- [x] 2.2 Add/extend `classic-scanlog-core` benchmark coverage for scan-time FormID value resolution paths.
- [x] 2.3 Provide a documented benchmark command set for local execution and repeatable baseline capture.

## 3. Baseline Artifact and Comparison Workflow

- [x] 3.1 Capture an initial baseline run artifact using the standardized metric schema and metadata.
- [x] 3.2 Add a comparison workflow (script or documented procedure) that reports per-scenario absolute and relative deltas.
- [x] 3.3 Define and document a regression-threshold policy (warning/fail classifications) for follow-up optimization changes.

## 4. Validation and Documentation

- [x] 4.1 Validate benchmark reproducibility with repeated local runs and ensure artifacts remain comparable.
- [x] 4.2 Document baseline refresh rules and required benchmark-delta reporting for subsequent Rust DB optimization changes.
