## Context

In the Rust scan pipeline, FormID analysis currently performs database lookups per FormID candidate in a loop. Even with a pool/cache, this pattern incurs avoidable per-call overhead on large logs where many FormIDs are analyzed.

The Rust database core already exposes `get_entries_batch`, so the integration gap is in `classic-scanlog-core` callsite behavior rather than in missing DB capability.

## Goals / Non-Goals

**Goals:**
- Replace per-entry FormID value queries in scan-time reporting with batched queries.
- Preserve current user-visible report behavior (format, ordering expectations, fallback semantics).
- Maintain case-insensitive plugin matching and existing duplicate-key behavior.
- Add parity-oriented tests to prevent behavioral regressions.

**Non-Goals:**
- Reworking `classic-database-core` query algorithms in this change.
- Redefining report output structure or introducing new user-facing fields.
- Changing orchestration APIs across bindings.

## Decisions

1. **Batch at FormIDAnalyzer integration boundary**
   - Keep extraction/matching pipeline intact, but gather eligible `(formid_suffix, plugin)` lookup pairs and resolve through batch APIs.
   - Rationale: minimizes blast radius and leverages proven DB core behavior.

2. **Use bounded chunking for large lookup sets**
   - Batch candidates in deterministic chunks (default size aligned with existing DB batch defaults) and merge results.
   - Rationale: prevents oversized query payloads while still reducing round-trips.

3. **Map results back using caller-visible keys**
   - Preserve current report key behavior and first-match-wins semantics for normalized duplicates.
   - Rationale: maintain output parity and avoid subtle user-facing regressions.

4. **Fail-soft behavior remains unchanged**
   - Missing entries and query failures continue to produce value-omitted output lines rather than hard-failing scan output.
   - Rationale: existing pipeline behavior prioritizes report completion over strict lookup success.

5. **Parity and edge-case tests are required**
   - Add tests for mixed plugin case, duplicate-normalization collisions, partial misses, and large candidate lists.
   - Rationale: optimization changes in hot paths need confidence in behavior equivalence.

## Risks / Trade-offs

- **[Risk] Batch mapping introduces subtle ordering/key regressions** → **Mitigation:** preserve existing line-generation order and add parity tests against current fixtures.
- **[Risk] Very large batches increase memory/query overhead** → **Mitigation:** use bounded chunking and documented batch-size defaults.
- **[Risk] Duplicate normalized keys produce ambiguous mappings** → **Mitigation:** explicitly preserve first-match-wins and test it.
- **[Risk] Error handling differences between single and batch paths** → **Mitigation:** standardize fail-soft behavior and verify via tests.

## Migration Plan

1. Introduce batch lookup integration path in `FormIDAnalyzerCore`.
2. Keep current output formatting path, only changing value-resolution backend.
3. Add regression/parity tests for key scenarios.
4. Compare behavior and performance against pre-change baseline before rollout.

## Open Questions

- Should batch size be fixed in scanlog-core or configurable via analysis config for advanced tuning?
- Do we want optional instrumentation to report per-log batch hit/miss ratios for tuning follow-up changes?
