## Context

`classic-database-core` currently uses a query cache that can grow with workload diversity, and expired entries are primarily handled opportunistically during lookup. For long-running or high-cardinality workloads, this can increase memory footprint and reduce predictability.

We need bounded cache lifecycle behavior without changing lookup API semantics.

## Goals / Non-Goals

**Goals:**
- Add explicit max-capacity behavior for query cache storage.
- Define deterministic eviction behavior when capacity is exceeded.
- Add proactive expired-entry cleanup behavior.
- Preserve existing hit/miss semantics from caller perspective.

**Non-Goals:**
- Rewriting the full database query pipeline.
- Changing external lookup signatures.
- Introducing non-deterministic eviction policies.

## Decisions

1. **Capacity-bound cache policy**
   - Introduce a max entry limit with deterministic eviction path.
   - Keep policy explicit and testable (for example, oldest-expired-first then policy fallback).

2. **Proactive cleanup in addition to on-access expiry**
   - Add periodic cleanup path for expired entries to reduce stale accumulation.
   - Keep cleanup lightweight and safe under concurrent lookup traffic.

3. **Observability included in core stats**
   - Extend or expose cache lifecycle counters (evictions, cleanup removals) alongside existing hit/miss counters.
   - Keep stats retrieval cheap and thread-safe.

4. **Behavioral parity priority**
   - Lookup result semantics remain unchanged: same resolved/miss behavior and fail-soft handling.

## Risks / Trade-offs

- **[Risk] Eviction policy accidentally lowers hit rate in common workloads** → **Mitigation:** benchmark before/after and tune default capacity values.
- **[Risk] Cleanup contention affects lookup latency** → **Mitigation:** keep cleanup bounded and schedule conservatively.
- **[Risk] Additional counters increase atomic overhead** → **Mitigation:** use relaxed atomics and avoid expensive synchronization paths.
- **[Risk] Misconfigured capacity creates over-eviction** → **Mitigation:** document defaults and add guardrails around minimum capacity.

## Migration Plan

1. Add bounded capacity and eviction behavior to cache operations.
2. Add proactive cleanup path and metrics.
3. Validate behavior parity with existing tests.
4. Run benchmark comparison against baseline and tune defaults if needed.

## Open Questions

- Should capacity be static default-only or runtime configurable via public API?
- Should cleanup run on timer, lookup-count threshold, or hybrid trigger?
