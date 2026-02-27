## Context

`DatabasePool` currently computes a max connection value and applies it to each SQLite pool created from the loaded database path set. With multiple DB files, effective total connection capacity can become higher than necessary for the host and workload.

A global budget model improves resource control and avoids per-pool overprovisioning.

## Goals / Non-Goals

**Goals:**
- Introduce global connection budgeting across active DB pools.
- Distribute per-pool limits deterministically from the global budget.
- Support recalculation when active DB paths change.
- Preserve existing lookup API behavior.

**Non-Goals:**
- Replacing `sqlx` pool implementation.
- Redesigning runtime orchestration outside database core.
- Making hard behavior changes to public API signatures.

## Decisions

1. **Global budget is first-class configuration**
   - Treat max connections as total budget for the pool instance, not per-db multiplier.
   - Keep existing auto-calculation as input to global budget, then distribute.

2. **Deterministic distribution with minimum floor**
   - Split budget by active db count using a documented policy and minimum-per-pool floor.
   - Handle edge cases where budget < ideal aggregate floor with deterministic fallback.

3. **Recompute allocations on topology change**
   - When database path set changes, recompute effective per-pool max connection values.
   - Keep recompute behavior explicit in lifecycle methods.

4. **Expose effective allocation metrics**
   - Surface global budget + effective per-pool allocation in stats to guide tuning.

## Risks / Trade-offs

- **[Risk] Too-low per-pool allocations hurt concurrency** → **Mitigation:** add sensible minimum floor and benchmark guidance.
- **[Risk] Reinitialization/recompute introduces complexity** → **Mitigation:** keep allocation logic isolated and covered with targeted tests.
- **[Risk] Runtime expectations differ for users who set explicit max values** → **Mitigation:** document semantic shift clearly as global budget behavior.
- **[Risk] Stats mismatch causes tuning confusion** → **Mitigation:** include explicit effective allocation fields in reported metrics.

## Migration Plan

1. Implement global budget allocation logic and policy.
2. Wire allocation into pool initialization and reinitialization paths.
3. Update stats surface and tests for allocation correctness.
4. Validate with benchmark scenarios using multi-db path configurations.

## Open Questions

- Should users be able to set both global budget and minimum-per-pool explicitly?
- Should dynamic rebalance be immediate or apply on next pool rebuild cycle?
