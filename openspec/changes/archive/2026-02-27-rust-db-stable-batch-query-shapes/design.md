## Context

Batch lookup SQL is currently generated based on exact batch length, which creates many unique SQL text shapes. This can reduce prepared statement reuse and add query-construction overhead in repeated workloads.

Stabilizing query shapes should improve consistency without altering lookup correctness.

## Goals / Non-Goals

**Goals:**
- Introduce stable query-shape selection policy for batch lookups.
- Preserve correctness and response mapping for all batch sizes, including final partial batches.
- Improve statement reuse potential and reduce query-shape churn.
- Keep existing public batch API unchanged.

**Non-Goals:**
- Replacing the batch lookup public contract.
- Altering caller-visible result formats or key conventions.
- Broad redesign of all SQL generation outside this batch path.

## Decisions

1. **Use documented shape buckets**
   - Define stable batch size buckets (or equivalent deterministic strategy) and select SQL shape by bucket.
   - Reuse SQL text per bucket to improve statement-level locality.

2. **Handle partial/final batches explicitly**
   - Ensure final chunks and smaller-than-bucket inputs map to correct execution path without losing entries.
   - Preserve existing first-match and merge semantics.

3. **Keep parameter binding semantics strict**
   - Maintain safe parameterized binding behavior and avoid dynamic interpolation of user-derived values in predicates.

4. **Add diagnostics for shape usage**
   - Surface enough instrumentation to correlate runtime behavior with selected shape buckets during tuning.

## Risks / Trade-offs

- **[Risk] Bucket policy may underperform for some distributions** → **Mitigation:** benchmark multiple realistic distributions and tune default bucket set.
- **[Risk] Complexity in partial-batch mapping causes subtle bugs** → **Mitigation:** add edge-case tests for small, boundary, and final chunks.
- **[Risk] Extra branching offsets gains for tiny batches** → **Mitigation:** include direct fast path for very small batches where appropriate.

## Migration Plan

1. Implement stable shape selection policy and query template handling.
2. Integrate into existing batch lookup execution path.
3. Add correctness tests for boundary and partial-batch behavior.
4. Run baseline comparison and record observed statement reuse/performance deltas.

## Open Questions

- Which default bucket set should be used initially for best practical coverage?
- Should bucket policy be internally fixed or externally configurable for advanced tuning?
