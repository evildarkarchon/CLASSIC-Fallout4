## 1. Query Shape Policy Definition

- [ ] 1.1 Define stable batch query shape strategy and documented size buckets.
- [ ] 1.2 Define behavior for partial/final batches that do not fill a nominal bucket.
- [ ] 1.3 Define observability fields for tracking selected shape behavior during runtime.

## 2. Batch Execution Refactor

- [ ] 2.1 Implement stable shape selection and query template reuse in Rust batch lookup flow.
- [ ] 2.2 Integrate shape selection with existing parameter binding and multi-database merge logic.
- [ ] 2.3 Preserve public API and result-mapping behavior while replacing variable-shape generation path.

## 3. Correctness and Edge-Case Validation

- [ ] 3.1 Add/extend tests for small, boundary, and large batch sizes across shape buckets.
- [ ] 3.2 Add/extend tests for partial final batches and mixed hit/miss result mapping correctness.
- [ ] 3.3 Validate behavior parity for existing callers and batch response formats.

## 4. Performance Validation and Tuning

- [ ] 4.1 Benchmark stable-shape implementation against baseline and record per-scenario deltas.
- [ ] 4.2 Tune default bucket policy based on observed statement reuse and throughput results.
